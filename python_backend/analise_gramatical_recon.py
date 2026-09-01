"""Camada Marco 3 para análise gramatical evidencial sobre ``recon_*``.

O módulo recebe um banco Marco 2 somente em leitura e produz outro SQLite por
staging atômico. Ele não reescreve árvores nem reutiliza os bancos legados, o
transdutor NLTK ou o tokenizador spaCy. Em vez de transformar o PSD, espelha
os nós de origem como âncoras e registra decisões versionadas sobre núcleos,
projeções que já existem na fonte, relações locais e evidência cartográfica
lexical. Cada decisão possui regra, evidência, confiança heurística e estado
de revisão pendente.

A separação é deliberada: um rótulo teórico do catálogo cartográfico não é
tratado como fato do corpus. Nesta primeira versão, uma projeção como
``MoodP_evaluative`` pode aparecer apenas como *evidência lexical* de um ADVP
cujo rendimento coincide com o léxico congelado; nenhum nó invisível é
injetado e nenhuma ``ForceP``/``FinP`` é afirmada a partir de um CP fonte.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import string
import sys
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import zip_longest
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

from cartografia_schema import HIERARQUIA_CARTOGRAFICA_COMPLETA, PROJECOES_MAP
from controle_artefatos import sha256_file
from importador_rastreavel import digest_tokens, validate_reconstruction_database


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RULESET_PATH = Path(__file__).with_name("regras_gramatica_expandida_v1.json")
ANALYSIS_SCHEMA_VERSION = 1
ANALYSIS_ENGINE_VERSION = "m3-gramatica-evidencial@1"
RULESET_SCHEMA_VERSION = 1

STATUS_ANALISADA = "ANALISADA"
STATUS_FORA_ESCOPO_REJEITADA = "FORA_ESCOPO_REJEITADA"
REVIEW_STATUS_PENDING = "PENDENTE"

SOURCE_PHRASE_BASES = frozenset({"CP", "IP", "PP", "NP", "VP", "ADJP", "ADVP", "CONJP"})
PUNCTUATION_BASES = frozenset({"PUNC", "PON", "PU", "PCT", "OPEN", "CLOSE", ",", ".", ":", ";"})
EMPTY_TOKEN_PREFIX = "*"


class AnalysisError(RuntimeError):
    """Falha controlada da construção ou validação Marco 3."""


class AnalysisSourceMismatch(AnalysisError):
    """A base Marco 2 não corresponde à âncora esperada."""


@dataclass(frozen=True)
class Rule:
    """Regra declarada no bundle congelado do Marco 3."""

    code: str
    kind: str
    confidence: float
    description: str
    definition: dict[str, Any]
    sha256: str


@dataclass(frozen=True)
class Ruleset:
    """Bundle de regras, léxico e hashes necessários para uma execução."""

    path: Path
    version: str
    bundle_sha256: str
    rules: tuple[Rule, ...]
    rules_by_code: dict[str, Rule]
    review_status_default: str


@dataclass(frozen=True)
class SourceNode:
    """Nó fonte materializado durante a análise de uma sentença."""

    no_id: int
    sentence_id: int
    parent_id: int | None
    sibling_order: int | None
    preorder: int
    lft: int
    rgt: int
    depth: int
    label: str
    base: str
    function: str | None
    is_leaf: bool
    leaf_ordinal: int | None
    token: str | None


@dataclass(frozen=True)
class SourceSentence:
    """Metadados de uma sentença Marco 2 usados como âncora externa."""

    sentence_id: int
    block_id: int
    document_id: int
    relative_path: str
    external_id: str | None
    root_label: str
    structure_class: str
    tree_sha256: str
    leaves_sha256: str
    leaf_count: int
    node_count: int
    block_sha256: str


@dataclass(frozen=True)
class AnalysisBuildReport:
    """Resumo estável de uma compilação Marco 3 promovida."""

    output_path: str
    source_database_path: str
    source_database_sha256: str
    source_manifest_path: str | None
    ruleset_path: str
    ruleset_version: str
    ruleset_sha256: str
    validation: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": bool(self.validation.get("ok")),
            "output_path": self.output_path,
            "source_database_path": self.source_database_path,
            "source_database_sha256": self.source_database_sha256,
            "source_manifest_path": self.source_manifest_path,
            "ruleset_path": self.ruleset_path,
            "ruleset_version": self.ruleset_version,
            "ruleset_sha256": self.ruleset_sha256,
            "validation": self.validation,
        }


def _canonical_json(value: Any) -> str:
    """Serializa uma estrutura de regras ou evidência de forma estável."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _normalise_lexical_text(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold().strip()


def _connect_readonly(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)


def _read_meta(connection: sqlite3.Connection, table: str) -> dict[str, str]:
    return {
        str(row[0]): str(row[1])
        for row in connection.execute(f"SELECT chave, valor FROM {table}")
    }


def _append_error(errors: list[str], message: str, limit: int = 32) -> None:
    if len(errors) < limit:
        errors.append(message)


def _counts_template() -> dict[str, int]:
    return {
        "scope_candidate_count": 0,
        "analysis_sentence_count": 0,
        "anchor_node_count": 0,
        "decision_count": 0,
        "entity_count": 0,
        "relation_count": 0,
        "evidence_count": 0,
        "excluded_count": 0,
        "cartographic_evidence_count": 0,
    }


def _validate_ruleset_payload(payload: Any, path: Path) -> Ruleset:
    if not isinstance(payload, dict):
        raise AnalysisError(f"bundle de regras inválido (objeto esperado): {path}")
    if payload.get("schema_version") != RULESET_SCHEMA_VERSION:
        raise AnalysisError(
            f"schema do bundle de regras incompatível em {path}: {payload.get('schema_version')!r}"
        )
    version = payload.get("ruleset_version")
    review_status = payload.get("review_status_default")
    raw_rules = payload.get("rules")
    if not isinstance(version, str) or not version.strip():
        raise AnalysisError(f"bundle sem ruleset_version válido: {path}")
    if review_status != REVIEW_STATUS_PENDING:
        raise AnalysisError(f"bundle deve iniciar revisões como {REVIEW_STATUS_PENDING}: {path}")
    if not isinstance(raw_rules, list) or not raw_rules:
        raise AnalysisError(f"bundle sem regras: {path}")

    rules: list[Rule] = []
    seen_codes: set[str] = set()
    for raw_rule in raw_rules:
        if not isinstance(raw_rule, dict):
            raise AnalysisError(f"regra não é objeto em {path}")
        code = raw_rule.get("id")
        kind = raw_rule.get("kind")
        confidence = raw_rule.get("confidence")
        description = raw_rule.get("description")
        if not isinstance(code, str) or not code or code in seen_codes:
            raise AnalysisError(f"identificador de regra inválido ou repetido: {code!r}")
        if not isinstance(kind, str) or not kind:
            raise AnalysisError(f"tipo inválido na regra {code}")
        if not isinstance(confidence, (int, float)) or not 0.0 <= float(confidence) <= 1.0:
            raise AnalysisError(f"confiança inválida na regra {code}")
        if not isinstance(description, str) or not description:
            raise AnalysisError(f"descrição ausente na regra {code}")
        if code == "E_ADV":
            lexicon = raw_rule.get("lexicon")
            if not isinstance(lexicon, dict) or not lexicon:
                raise AnalysisError("E_ADV deve declarar um léxico não vazio")
            for trigger, projection in lexicon.items():
                if not isinstance(trigger, str) or not trigger.strip():
                    raise AnalysisError("E_ADV contém gatilho lexical inválido")
                if projection not in PROJECOES_MAP:
                    raise AnalysisError(
                        f"E_ADV referencia projeção ausente do catálogo: {projection!r}"
                    )
        rule_definition = dict(raw_rule)
        rule_sha = _sha256_text(_canonical_json(rule_definition))
        rules.append(
            Rule(
                code=code,
                kind=kind,
                confidence=float(confidence),
                description=description,
                definition=rule_definition,
                sha256=rule_sha,
            )
        )
        seen_codes.add(code)

    required_codes = {
        "N0_VAZIO",
        "N0_PONT",
        "L_N",
        "L_PRO",
        "L_ADJ",
        "L_ADV",
        "L_VB",
        "F_C",
        "F_D",
        "F_P",
        "F_OP",
        "V_AUX",
        "P_FONTE",
        "H_LOCAL",
        "E_ADV",
    }
    missing = sorted(required_codes - seen_codes)
    if missing:
        raise AnalysisError("bundle sem regra(s) obrigatória(s): " + ", ".join(missing))
    canonical_payload = _canonical_json(payload)
    return Ruleset(
        path=path.resolve(),
        version=version,
        bundle_sha256=_sha256_text(canonical_payload),
        rules=tuple(rules),
        rules_by_code={rule.code: rule for rule in rules},
        review_status_default=review_status,
    )


def load_ruleset(path: Path | None = None) -> Ruleset:
    """Carrega e valida o bundle declarativo de regras sem bibliotecas NLP."""
    resolved = (path or DEFAULT_RULESET_PATH).resolve()
    if not resolved.is_file():
        raise AnalysisError(f"bundle de regras não encontrado: {resolved}")
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AnalysisError(f"não foi possível carregar o bundle de regras: {error}") from error
    return _validate_ruleset_payload(payload, resolved)


def _catalog_payload() -> list[dict[str, Any]]:
    return [
        {
            "codigo": projection.nome,
            "dominio": projection.dominio,
            "nome_dominio": projection.nome_dominio,
            "rank_hierarquia": projection.rank_hierarquia,
            "recursiva": projection.recursivo,
            "descricao": projection.descricao,
        }
        for projection in HIERARQUIA_CARTOGRAFICA_COMPLETA
    ]


def _catalog_sha256() -> str:
    return _sha256_text(_canonical_json(_catalog_payload()))


def _engine_sha256() -> str:
    return sha256_file(Path(__file__))


def _create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE m3_meta (
            chave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
        );

        CREATE TABLE m3_base_origem (
            singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
            caminho_banco_m2 TEXT NOT NULL,
            sha256_banco_m2 TEXT NOT NULL CHECK (length(sha256_banco_m2) = 64),
            caminho_manifesto_m2 TEXT NOT NULL,
            sha256_manifesto_m2 TEXT NOT NULL,
            snapshot_manifesto_m2 TEXT NOT NULL,
            versao_schema_m2 TEXT NOT NULL,
            sha256_semantico_sentencas_m2 TEXT NOT NULL CHECK (length(sha256_semantico_sentencas_m2) = 64),
            quantidade_candidatos_m2 INTEGER NOT NULL CHECK (quantidade_candidatos_m2 >= 0),
            quantidade_importadas_m2 INTEGER NOT NULL CHECK (quantidade_importadas_m2 >= 0),
            quantidade_rejeitadas_m2 INTEGER NOT NULL CHECK (quantidade_rejeitadas_m2 >= 0),
            quantidade_nos_m2 INTEGER NOT NULL CHECK (quantidade_nos_m2 >= 0),
            validado_em_utc TEXT NOT NULL
        );

        CREATE TABLE m3_conjuntos_regras (
            ruleset_id INTEGER PRIMARY KEY CHECK (ruleset_id = 1),
            caminho TEXT NOT NULL,
            versao TEXT NOT NULL,
            sha256_bundle TEXT NOT NULL CHECK (length(sha256_bundle) = 64),
            sha256_catalogo_projecoes TEXT NOT NULL CHECK (length(sha256_catalogo_projecoes) = 64),
            sha256_implementacao TEXT NOT NULL CHECK (length(sha256_implementacao) = 64),
            criado_em_utc TEXT NOT NULL
        );

        CREATE TABLE m3_regras (
            codigo TEXT PRIMARY KEY,
            ruleset_id INTEGER NOT NULL REFERENCES m3_conjuntos_regras(ruleset_id),
            tipo TEXT NOT NULL,
            confianca_base REAL NOT NULL CHECK (confianca_base >= 0.0 AND confianca_base <= 1.0),
            descricao TEXT NOT NULL,
            definicao_json TEXT NOT NULL,
            sha256_definicao TEXT NOT NULL CHECK (length(sha256_definicao) = 64)
        );

        CREATE TABLE m3_catalogo_projecoes (
            codigo TEXT PRIMARY KEY,
            ruleset_id INTEGER NOT NULL REFERENCES m3_conjuntos_regras(ruleset_id),
            dominio INTEGER NOT NULL CHECK (dominio BETWEEN 1 AND 5),
            nome_dominio TEXT NOT NULL,
            rank_hierarquia INTEGER NOT NULL CHECK (rank_hierarquia > 0),
            recursiva INTEGER NOT NULL CHECK (recursiva IN (0, 1)),
            descricao TEXT NOT NULL
        );

        CREATE TABLE m3_execucoes (
            analysis_id INTEGER PRIMARY KEY CHECK (analysis_id = 1),
            ruleset_id INTEGER NOT NULL REFERENCES m3_conjuntos_regras(ruleset_id),
            versao_engine TEXT NOT NULL,
            sha256_engine TEXT NOT NULL CHECK (length(sha256_engine) = 64),
            estado TEXT NOT NULL CHECK (estado = 'PROMOVIDA'),
            iniciado_em_utc TEXT NOT NULL,
            concluido_em_utc TEXT NOT NULL,
            resumo_json TEXT NOT NULL DEFAULT '{}'
        );

        CREATE TABLE m3_escopo_blocos (
            analysis_id INTEGER NOT NULL REFERENCES m3_execucoes(analysis_id),
            bloco_id_m2 INTEGER NOT NULL,
            documento_id_m2 INTEGER NOT NULL,
            caminho_relativo TEXT NOT NULL,
            ordinal_bloco_m2 INTEGER NOT NULL CHECK (ordinal_bloco_m2 > 0),
            ordinal_candidato_m2 INTEGER NOT NULL CHECK (ordinal_candidato_m2 > 0),
            sha256_bloco_m2 TEXT NOT NULL CHECK (length(sha256_bloco_m2) = 64),
            resultado_m2 TEXT NOT NULL CHECK (resultado_m2 IN ('IMPORTADO', 'REJEITADO')),
            sentenca_id_m2 INTEGER,
            codigo_motivo_m2 TEXT,
            status_analise TEXT NOT NULL CHECK (status_analise IN ('ANALISADA', 'FORA_ESCOPO_REJEITADA')),
            PRIMARY KEY (analysis_id, bloco_id_m2),
            UNIQUE (analysis_id, sentenca_id_m2),
            CHECK (
                (resultado_m2 = 'IMPORTADO' AND sentenca_id_m2 IS NOT NULL AND status_analise = 'ANALISADA')
                OR
                (resultado_m2 = 'REJEITADO' AND sentenca_id_m2 IS NULL AND status_analise = 'FORA_ESCOPO_REJEITADA')
            )
        );

        CREATE TABLE m3_sentencas_escopo (
            analysis_id INTEGER NOT NULL,
            sentenca_id_m2 INTEGER NOT NULL,
            bloco_id_m2 INTEGER NOT NULL,
            documento_id_m2 INTEGER NOT NULL,
            caminho_relativo TEXT NOT NULL,
            id_externo TEXT,
            rotulo_raiz TEXT NOT NULL,
            classe_estrutura TEXT NOT NULL,
            sha256_arvore_m2 TEXT NOT NULL CHECK (length(sha256_arvore_m2) = 64),
            sha256_folhas_m2 TEXT NOT NULL CHECK (length(sha256_folhas_m2) = 64),
            quantidade_folhas_m2 INTEGER NOT NULL CHECK (quantidade_folhas_m2 >= 0),
            quantidade_nos_m2 INTEGER NOT NULL CHECK (quantidade_nos_m2 > 0),
            sha256_folhas_ancoradas TEXT NOT NULL CHECK (length(sha256_folhas_ancoradas) = 64),
            quantidade_folhas_ancoradas INTEGER NOT NULL CHECK (quantidade_folhas_ancoradas >= 0),
            PRIMARY KEY (analysis_id, sentenca_id_m2),
            FOREIGN KEY (analysis_id, bloco_id_m2)
                REFERENCES m3_escopo_blocos(analysis_id, bloco_id_m2)
        );

        CREATE TABLE m3_nos_ancora (
            analysis_id INTEGER NOT NULL,
            no_id_m2 INTEGER NOT NULL,
            sentenca_id_m2 INTEGER NOT NULL,
            pai_no_id_m2 INTEGER,
            ordem_irmao_m2 INTEGER,
            preordem INTEGER NOT NULL CHECK (preordem > 0),
            lft INTEGER NOT NULL CHECK (lft > 0),
            rgt INTEGER NOT NULL CHECK (rgt > lft),
            profundidade INTEGER NOT NULL CHECK (profundidade >= 0),
            rotulo_origem TEXT NOT NULL,
            rotulo_base TEXT NOT NULL,
            funcao TEXT,
            eh_folha INTEGER NOT NULL CHECK (eh_folha IN (0, 1)),
            ordem_folha INTEGER,
            token_origem TEXT,
            PRIMARY KEY (analysis_id, no_id_m2),
            UNIQUE (analysis_id, sentenca_id_m2, no_id_m2),
            UNIQUE (analysis_id, sentenca_id_m2, preordem),
            UNIQUE (analysis_id, sentenca_id_m2, ordem_folha),
            FOREIGN KEY (analysis_id, sentenca_id_m2)
                REFERENCES m3_sentencas_escopo(analysis_id, sentenca_id_m2),
            FOREIGN KEY (analysis_id, pai_no_id_m2)
                REFERENCES m3_nos_ancora(analysis_id, no_id_m2),
            CHECK (
                (eh_folha = 1 AND token_origem IS NOT NULL AND ordem_folha IS NOT NULL)
                OR
                (eh_folha = 0 AND token_origem IS NULL AND ordem_folha IS NULL)
            )
        );

        CREATE TABLE m3_decisoes (
            decision_id INTEGER PRIMARY KEY,
            analysis_id INTEGER NOT NULL REFERENCES m3_execucoes(analysis_id),
            sentenca_id_m2 INTEGER NOT NULL,
            no_ancora_id_m2 INTEGER NOT NULL,
            regra_id TEXT NOT NULL REFERENCES m3_regras(codigo),
            tipo_decisao TEXT NOT NULL CHECK (tipo_decisao IN ('ENTIDADE', 'RELACAO')),
            confianca REAL NOT NULL CHECK (confianca >= 0.0 AND confianca <= 1.0),
            metodo_confianca TEXT NOT NULL CHECK (metodo_confianca = 'HEURISTICA'),
            status_evidencia TEXT NOT NULL CHECK (status_evidencia IN ('DIRETA_FONTE', 'CANDIDATO_LOCAL', 'AMBIGUO', 'EVIDENCIA_LEXICAL', 'NAO_APLICAVEL')),
            estado_revisao TEXT NOT NULL CHECK (estado_revisao = 'PENDENTE'),
            justificativa TEXT NOT NULL,
            FOREIGN KEY (analysis_id, sentenca_id_m2, no_ancora_id_m2)
                REFERENCES m3_nos_ancora(analysis_id, sentenca_id_m2, no_id_m2)
        );

        CREATE TABLE m3_entidades (
            entity_id INTEGER PRIMARY KEY,
            decision_id INTEGER NOT NULL UNIQUE REFERENCES m3_decisoes(decision_id),
            analysis_id INTEGER NOT NULL,
            sentenca_id_m2 INTEGER NOT NULL,
            no_ancora_id_m2 INTEGER NOT NULL,
            tipo TEXT NOT NULL CHECK (tipo IN ('EXCLUSAO', 'NUCLEO_LEXICAL', 'NUCLEO_FUNCIONAL', 'NUCLEO_FRONTEIRA', 'EVIDENCIA_AUXILIAR', 'PROJECAO_FONTE', 'EVIDENCIA_CARTOGRAFICA')),
            rotulo_analitico TEXT NOT NULL,
            projecao_fonte TEXT,
            projecao_evidenciada TEXT,
            ordem INTEGER NOT NULL CHECK (ordem >= 0),
            detalhes_json TEXT NOT NULL,
            FOREIGN KEY (analysis_id, sentenca_id_m2, no_ancora_id_m2)
                REFERENCES m3_nos_ancora(analysis_id, sentenca_id_m2, no_id_m2),
            CHECK (
                (tipo = 'EVIDENCIA_CARTOGRAFICA' AND projecao_evidenciada IS NOT NULL)
                OR
                (tipo <> 'EVIDENCIA_CARTOGRAFICA' AND projecao_evidenciada IS NULL)
            )
        );

        CREATE TABLE m3_relacoes (
            relation_id INTEGER PRIMARY KEY,
            decision_id INTEGER NOT NULL UNIQUE REFERENCES m3_decisoes(decision_id),
            analysis_id INTEGER NOT NULL,
            sentenca_id_m2 INTEGER NOT NULL,
            no_sintagma_id_m2 INTEGER NOT NULL,
            no_nucleo_id_m2 INTEGER NOT NULL,
            tipo TEXT NOT NULL CHECK (tipo = 'CANDIDATO_NUCLEO_LOCAL'),
            ordem_candidato INTEGER NOT NULL CHECK (ordem_candidato >= 0),
            detalhes_json TEXT NOT NULL,
            FOREIGN KEY (analysis_id, sentenca_id_m2, no_sintagma_id_m2)
                REFERENCES m3_nos_ancora(analysis_id, sentenca_id_m2, no_id_m2),
            FOREIGN KEY (analysis_id, sentenca_id_m2, no_nucleo_id_m2)
                REFERENCES m3_nos_ancora(analysis_id, sentenca_id_m2, no_id_m2),
            CHECK (no_sintagma_id_m2 <> no_nucleo_id_m2),
            UNIQUE (analysis_id, no_sintagma_id_m2, no_nucleo_id_m2)
        );

        CREATE TABLE m3_evidencias (
            evidence_id INTEGER PRIMARY KEY,
            decision_id INTEGER NOT NULL REFERENCES m3_decisoes(decision_id),
            analysis_id INTEGER NOT NULL,
            no_ancora_id_m2 INTEGER NOT NULL,
            tipo TEXT NOT NULL CHECK (tipo IN ('ROTULO_PSD', 'TOKEN', 'RELACAO_ORIGEM', 'ORDEM_IRMAO', 'LEXICO_CONGELADO')),
            ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
            valor_json TEXT NOT NULL,
            sha256_valor TEXT NOT NULL CHECK (length(sha256_valor) = 64),
            descricao TEXT NOT NULL,
            FOREIGN KEY (analysis_id, no_ancora_id_m2)
                REFERENCES m3_nos_ancora(analysis_id, no_id_m2),
            UNIQUE (decision_id, ordinal)
        );

        CREATE TABLE m3_revisoes (
            revision_id INTEGER PRIMARY KEY,
            decision_id INTEGER NOT NULL REFERENCES m3_decisoes(decision_id),
            sequencia INTEGER NOT NULL CHECK (sequencia > 0),
            acao TEXT NOT NULL CHECK (acao IN ('APROVAR', 'REJEITAR', 'SUPERAR', 'CORRIGIR')),
            revisor_id TEXT NOT NULL,
            justificativa TEXT NOT NULL,
            evidencia_textual TEXT NOT NULL,
            criado_em_utc TEXT NOT NULL,
            UNIQUE (decision_id, sequencia)
        );

        CREATE INDEX idx_m3_escopo_status ON m3_escopo_blocos(analysis_id, status_analise, caminho_relativo);
        CREATE INDEX idx_m3_ancoras_base ON m3_nos_ancora(analysis_id, rotulo_base, funcao);
        CREATE INDEX idx_m3_ancoras_token ON m3_nos_ancora(analysis_id, token_origem);
        CREATE INDEX idx_m3_ancoras_intervalo ON m3_nos_ancora(analysis_id, sentenca_id_m2, lft, rgt);
        CREATE INDEX idx_m3_decisoes_regra ON m3_decisoes(analysis_id, regra_id, status_evidencia);
        CREATE INDEX idx_m3_entidades_tipo ON m3_entidades(analysis_id, tipo, projecao_evidenciada, sentenca_id_m2);
        CREATE INDEX idx_m3_relacoes_sintagma ON m3_relacoes(analysis_id, no_sintagma_id_m2, ordem_candidato);
        CREATE INDEX idx_m3_evidencias_decisao ON m3_evidencias(decision_id, ordinal);
        """
    )


def _put_meta(connection: sqlite3.Connection, key: str, value: str) -> None:
    connection.execute(
        "INSERT INTO m3_meta(chave, valor) VALUES (?, ?) "
        "ON CONFLICT(chave) DO UPDATE SET valor=excluded.valor",
        (key, value),
    )


def _source_semantic_digest(connection: sqlite3.Connection) -> str:
    digest = hashlib.sha256()
    for row in connection.execute(
        """
        SELECT sentenca_id, bloco_id, sha256_folhas, quantidade_folhas, quantidade_nos
        FROM recon_sentencas
        ORDER BY sentenca_id
        """
    ):
        digest.update(
            f"{row[0]}\0{row[1]}\0{row[2]}\0{row[3]}\0{row[4]}\n".encode("utf-8")
        )
    return digest.hexdigest()


def _source_summary(connection: sqlite3.Connection) -> dict[str, Any]:
    meta = _read_meta(connection, "recon_meta")
    counts = {
        "candidate_count": int(
            connection.execute("SELECT COUNT(*) FROM recon_blocos_origem WHERE eh_candidato_historico_fisico=1").fetchone()[0]
        ),
        "imported_count": int(
            connection.execute("SELECT COUNT(*) FROM recon_ledger_importacao WHERE resultado='IMPORTADO'").fetchone()[0]
        ),
        "rejected_count": int(
            connection.execute("SELECT COUNT(*) FROM recon_ledger_importacao WHERE resultado='REJEITADO'").fetchone()[0]
        ),
        "node_count": int(connection.execute("SELECT COUNT(*) FROM recon_nos").fetchone()[0]),
    }
    return {
        "meta": meta,
        "semantic_digest": _source_semantic_digest(connection),
        **counts,
    }


def _iter_scope_blocks(connection: sqlite3.Connection) -> Iterator[sqlite3.Row]:
    connection.row_factory = sqlite3.Row
    cursor = connection.execute(
        """
        SELECT b.bloco_id, b.documento_id, d.caminho_relativo, b.ordinal_bloco,
               b.ordinal_candidato, b.sha256_bloco, l.resultado, l.codigo_motivo,
               s.sentenca_id
        FROM recon_ledger_importacao AS l
        JOIN recon_blocos_origem AS b ON b.bloco_id = l.bloco_id
        JOIN recon_documentos AS d ON d.documento_id = b.documento_id
        LEFT JOIN recon_sentencas AS s ON s.bloco_id = b.bloco_id
        ORDER BY b.bloco_id
        """
    )
    yield from cursor


def _iter_source_sentences(connection: sqlite3.Connection) -> Iterator[tuple[SourceSentence, list[SourceNode]]]:
    connection.row_factory = sqlite3.Row
    cursor = connection.execute(
        """
        SELECT s.sentenca_id, s.bloco_id, s.documento_id, s.caminho_relativo,
               s.id_externo, s.rotulo_raiz, s.classe_estrutura,
               l.sha256_arvore_normalizada, s.sha256_folhas,
               s.quantidade_folhas, s.quantidade_nos, b.sha256_bloco,
               n.no_id, n.preordem, n.lft, n.rgt, n.profundidade,
               n.rotulo_origem, n.rotulo_base, n.funcao, n.eh_folha,
               n.ordem_folha, n.token_origem,
               r.pai_no_id, r.ordem_irmao
        FROM recon_sentencas AS s
        JOIN recon_ledger_importacao AS l ON l.bloco_id = s.bloco_id
        JOIN recon_blocos_origem AS b ON b.bloco_id = s.bloco_id
        JOIN recon_nos AS n ON n.sentenca_id = s.sentenca_id
        LEFT JOIN recon_relacoes AS r
          ON r.sentenca_id = n.sentenca_id AND r.filho_no_id = n.no_id
        ORDER BY s.sentenca_id, n.preordem
        """
    )
    current_sentence_id: int | None = None
    current_sentence: SourceSentence | None = None
    nodes: list[SourceNode] = []
    for row in cursor:
        sentence_id = int(row["sentenca_id"])
        if current_sentence_id is not None and sentence_id != current_sentence_id:
            if current_sentence is None:
                raise AnalysisError("iterador de sentença sem metadados")
            yield current_sentence, nodes
            nodes = []
        if sentence_id != current_sentence_id:
            current_sentence_id = sentence_id
            current_sentence = SourceSentence(
                sentence_id=sentence_id,
                block_id=int(row["bloco_id"]),
                document_id=int(row["documento_id"]),
                relative_path=str(row["caminho_relativo"]),
                external_id=str(row["id_externo"]) if row["id_externo"] is not None else None,
                root_label=str(row["rotulo_raiz"]),
                structure_class=str(row["classe_estrutura"]),
                tree_sha256=str(row["sha256_arvore_normalizada"]),
                leaves_sha256=str(row["sha256_folhas"]),
                leaf_count=int(row["quantidade_folhas"]),
                node_count=int(row["quantidade_nos"]),
                block_sha256=str(row["sha256_bloco"]),
            )
        nodes.append(
            SourceNode(
                no_id=int(row["no_id"]),
                sentence_id=sentence_id,
                parent_id=int(row["pai_no_id"]) if row["pai_no_id"] is not None else None,
                sibling_order=int(row["ordem_irmao"]) if row["ordem_irmao"] is not None else None,
                preorder=int(row["preordem"]),
                lft=int(row["lft"]),
                rgt=int(row["rgt"]),
                depth=int(row["profundidade"]),
                label=str(row["rotulo_origem"]),
                base=str(row["rotulo_base"]),
                function=str(row["funcao"]) if row["funcao"] is not None else None,
                is_leaf=bool(row["eh_folha"]),
                leaf_ordinal=int(row["ordem_folha"]) if row["ordem_folha"] is not None else None,
                token=str(row["token_origem"]) if row["token_origem"] is not None else None,
            )
        )
    if current_sentence is not None:
        yield current_sentence, nodes


def _node_evidence(node: SourceNode) -> dict[str, Any]:
    return {
        "no_id_m2": node.no_id,
        "preordem": node.preorder,
        "rotulo_origem": node.label,
        "rotulo_base": node.base,
        "funcao": node.function,
        "ordem_folha": node.leaf_ordinal,
        "token_origem": node.token,
    }


def _record_evidence(
    cursor: sqlite3.Cursor,
    decision_id: int,
    node_id: int,
    evidence_type: str,
    ordinal: int,
    value: Any,
    description: str,
) -> None:
    canonical_value = _canonical_json(value)
    cursor.execute(
        """
        INSERT INTO m3_evidencias(
            decision_id, analysis_id, no_ancora_id_m2, tipo, ordinal,
            valor_json, sha256_valor, descricao
        ) VALUES (?, 1, ?, ?, ?, ?, ?, ?)
        """,
        (
            decision_id,
            node_id,
            evidence_type,
            ordinal,
            canonical_value,
            _sha256_text(canonical_value),
            description,
        ),
    )


def _record_entity(
    cursor: sqlite3.Cursor,
    ruleset: Ruleset,
    sentence: SourceSentence,
    node: SourceNode,
    rule_code: str,
    entity_type: str,
    label: str,
    status_evidence: str,
    *,
    confidence: float | None = None,
    source_projection: str | None = None,
    evidenced_projection: str | None = None,
    details: dict[str, Any] | None = None,
    evidence_type: str = "ROTULO_PSD",
    evidence_value: Any | None = None,
) -> None:
    rule = ruleset.rules_by_code[rule_code]
    effective_confidence = rule.confidence if confidence is None else confidence
    payload = details or {}
    cursor.execute(
        """
        INSERT INTO m3_decisoes(
            analysis_id, sentenca_id_m2, no_ancora_id_m2, regra_id, tipo_decisao,
            confianca, metodo_confianca, status_evidencia, estado_revisao, justificativa
        ) VALUES (1, ?, ?, ?, 'ENTIDADE', ?, 'HEURISTICA', ?, ?, ?)
        """,
        (
            sentence.sentence_id,
            node.no_id,
            rule_code,
            effective_confidence,
            status_evidence,
            ruleset.review_status_default,
            rule.description,
        ),
    )
    decision_id = int(cursor.lastrowid)
    cursor.execute(
        """
        INSERT INTO m3_entidades(
            decision_id, analysis_id, sentenca_id_m2, no_ancora_id_m2, tipo,
            rotulo_analitico, projecao_fonte, projecao_evidenciada, ordem, detalhes_json
        ) VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            decision_id,
            sentence.sentence_id,
            node.no_id,
            entity_type,
            label,
            source_projection,
            evidenced_projection,
            node.preorder,
            _canonical_json(payload),
        ),
    )
    _record_evidence(
        cursor,
        decision_id,
        node.no_id,
        evidence_type,
        0,
        _node_evidence(node) if evidence_value is None else evidence_value,
        "evidência observada na árvore PSD de origem",
    )


def _record_local_relation(
    cursor: sqlite3.Cursor,
    ruleset: Ruleset,
    sentence: SourceSentence,
    phrase: SourceNode,
    core: SourceNode,
    candidate_order: int,
    status_evidence: str,
    confidence: float,
    candidate_count: int,
) -> None:
    rule = ruleset.rules_by_code["H_LOCAL"]
    cursor.execute(
        """
        INSERT INTO m3_decisoes(
            analysis_id, sentenca_id_m2, no_ancora_id_m2, regra_id, tipo_decisao,
            confianca, metodo_confianca, status_evidencia, estado_revisao, justificativa
        ) VALUES (1, ?, ?, 'H_LOCAL', 'RELACAO', ?, 'HEURISTICA', ?, ?, ?)
        """,
        (
            sentence.sentence_id,
            phrase.no_id,
            confidence,
            status_evidence,
            ruleset.review_status_default,
            rule.description,
        ),
    )
    decision_id = int(cursor.lastrowid)
    details = {
        "numero_candidatos": candidate_count,
        "ordem_irmao_m2": core.sibling_order,
        "rotulo_sintagma": phrase.label,
        "rotulo_candidato": core.label,
    }
    cursor.execute(
        """
        INSERT INTO m3_relacoes(
            decision_id, analysis_id, sentenca_id_m2, no_sintagma_id_m2,
            no_nucleo_id_m2, tipo, ordem_candidato, detalhes_json
        ) VALUES (?, 1, ?, ?, ?, 'CANDIDATO_NUCLEO_LOCAL', ?, ?)
        """,
        (
            decision_id,
            sentence.sentence_id,
            phrase.no_id,
            core.no_id,
            candidate_order,
            _canonical_json(details),
        ),
    )
    _record_evidence(
        cursor,
        decision_id,
        phrase.no_id,
        "RELACAO_ORIGEM",
        0,
        {"pai_no_id_m2": phrase.no_id, "filho_no_id_m2": core.no_id},
        "relação pai-filho imediata registrada em recon_relacoes",
    )
    _record_evidence(
        cursor,
        decision_id,
        core.no_id,
        "ORDEM_IRMAO",
        1,
        {"ordem_irmao_m2": core.sibling_order, "no_id_m2": core.no_id},
        "ordem de irmãos da relação fonte",
    )


def _is_empty_token(node: SourceNode) -> bool:
    return bool(node.is_leaf and node.token and (node.token == "0" or node.token.startswith(EMPTY_TOKEN_PREFIX)))


def _is_punctuation(node: SourceNode) -> bool:
    if not node.is_leaf:
        return False
    if node.base in PUNCTUATION_BASES:
        return True
    token = node.token or ""
    return bool(token) and all(character in string.punctuation for character in token)


def _is_lexical_verb(base: str) -> bool:
    return base == "V" or base.startswith("VB")


def _is_auxiliary_or_copula(base: str) -> bool:
    return base.startswith(("HV", "TR", "SR", "ET"))


def _is_local_head_candidate(phrase_base: str, child: SourceNode) -> bool:
    if not child.is_leaf or _is_empty_token(child) or _is_punctuation(child):
        return False
    if phrase_base == "NP":
        return child.base in {"N", "NPR", "PRO", "WPRO", "Q", "ADJ"}
    if phrase_base == "PP":
        return child.base == "P"
    if phrase_base == "CP":
        return child.base == "C"
    if phrase_base in {"IP", "VP"}:
        return _is_lexical_verb(child.base) or _is_auxiliary_or_copula(child.base)
    if phrase_base == "ADJP":
        return child.base == "ADJ"
    if phrase_base == "ADVP":
        return child.base == "ADV"
    if phrase_base == "CONJP":
        return child.base == "CONJ"
    return False


def _build_children(nodes: Sequence[SourceNode]) -> dict[int, list[SourceNode]]:
    children: dict[int, list[SourceNode]] = {}
    for node in nodes:
        if node.parent_id is not None:
            children.setdefault(node.parent_id, []).append(node)
    for siblings in children.values():
        siblings.sort(key=lambda child: (child.sibling_order if child.sibling_order is not None else -1, child.preorder))
    return children


def _analyse_sentence(
    cursor: sqlite3.Cursor,
    ruleset: Ruleset,
    sentence: SourceSentence,
    nodes: Sequence[SourceNode],
) -> dict[str, int]:
    """Materializa âncoras e decisões estritamente derivadas de uma sentença."""
    leaves = [node.token or "" for node in nodes if node.is_leaf]
    if digest_tokens(leaves) != sentence.leaves_sha256 or len(leaves) != sentence.leaf_count:
        raise AnalysisError(f"folhas fonte divergentes antes da análise: sentença {sentence.sentence_id}")
    if len(nodes) != sentence.node_count:
        raise AnalysisError(f"nós fonte divergentes antes da análise: sentença {sentence.sentence_id}")

    cursor.execute(
        """
        INSERT INTO m3_sentencas_escopo(
            analysis_id, sentenca_id_m2, bloco_id_m2, documento_id_m2, caminho_relativo,
            id_externo, rotulo_raiz, classe_estrutura, sha256_arvore_m2,
            sha256_folhas_m2, quantidade_folhas_m2, quantidade_nos_m2,
            sha256_folhas_ancoradas, quantidade_folhas_ancoradas
        ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            sentence.sentence_id,
            sentence.block_id,
            sentence.document_id,
            sentence.relative_path,
            sentence.external_id,
            sentence.root_label,
            sentence.structure_class,
            sentence.tree_sha256,
            sentence.leaves_sha256,
            sentence.leaf_count,
            sentence.node_count,
            digest_tokens(leaves),
            len(leaves),
        ),
    )
    cursor.executemany(
        """
        INSERT INTO m3_nos_ancora(
            analysis_id, no_id_m2, sentenca_id_m2, pai_no_id_m2, ordem_irmao_m2,
            preordem, lft, rgt, profundidade, rotulo_origem, rotulo_base, funcao,
            eh_folha, ordem_folha, token_origem
        ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                node.no_id,
                sentence.sentence_id,
                node.parent_id,
                node.sibling_order,
                node.preorder,
                node.lft,
                node.rgt,
                node.depth,
                node.label,
                node.base,
                node.function,
                int(node.is_leaf),
                node.leaf_ordinal,
                node.token,
            )
            for node in nodes
        ],
    )

    counts = {"decisions": 0, "entities": 0, "relations": 0, "evidence": 0, "excluded": 0, "cartographic": 0}
    children = _build_children(nodes)
    nodes_by_id = {node.no_id: node for node in nodes}

    for node in nodes:
        if not node.is_leaf and node.base in SOURCE_PHRASE_BASES:
            _record_entity(
                cursor,
                ruleset,
                sentence,
                node,
                "P_FONTE",
                "PROJECAO_FONTE",
                f"PROJECAO_FONTE_{node.base}",
                "DIRETA_FONTE",
                source_projection=node.base,
                details={"fonte": "rotulo_base", "rotulo_base": node.base},
            )
            counts["decisions"] += 1
            counts["entities"] += 1
            counts["evidence"] += 1

        if not node.is_leaf:
            continue
        if _is_empty_token(node):
            _record_entity(
                cursor,
                ruleset,
                sentence,
                node,
                "N0_VAZIO",
                "EXCLUSAO",
                "EXCLUIDO_VAZIO",
                "DIRETA_FONTE",
                details={"motivo": "categoria_vazia_ou_marcador_zero"},
                evidence_type="TOKEN",
            )
            counts["decisions"] += 1
            counts["entities"] += 1
            counts["evidence"] += 1
            counts["excluded"] += 1
            continue
        if _is_punctuation(node):
            _record_entity(
                cursor,
                ruleset,
                sentence,
                node,
                "N0_PONT",
                "EXCLUSAO",
                "EXCLUIDO_PONTUACAO",
                "DIRETA_FONTE",
                details={"motivo": "pontuacao"},
                evidence_type="TOKEN",
            )
            counts["decisions"] += 1
            counts["entities"] += 1
            counts["evidence"] += 1
            counts["excluded"] += 1
            continue

        parent = nodes_by_id.get(node.parent_id) if node.parent_id is not None else None
        if node.base in {"N", "NPR"}:
            _record_entity(cursor, ruleset, sentence, node, "L_N", "NUCLEO_LEXICAL", "NUCLEO_LEXICAL_NOMINAL", "DIRETA_FONTE")
        elif node.base in {"PRO", "WPRO"}:
            _record_entity(cursor, ruleset, sentence, node, "L_PRO", "NUCLEO_LEXICAL", "NUCLEO_LEXICAL_PRONOMINAL", "DIRETA_FONTE")
        elif node.base == "ADJ":
            _record_entity(cursor, ruleset, sentence, node, "L_ADJ", "NUCLEO_LEXICAL", "NUCLEO_LEXICAL_ADJETIVAL", "DIRETA_FONTE")
        elif node.base == "ADV":
            _record_entity(cursor, ruleset, sentence, node, "L_ADV", "NUCLEO_LEXICAL", "NUCLEO_LEXICAL_ADVERBIAL", "DIRETA_FONTE")
        elif _is_lexical_verb(node.base):
            _record_entity(cursor, ruleset, sentence, node, "L_VB", "NUCLEO_LEXICAL", "NUCLEO_LEXICAL_VERBAL", "DIRETA_FONTE")
        elif node.base == "C" and parent is not None and parent.base == "CP":
            _record_entity(cursor, ruleset, sentence, node, "F_C", "NUCLEO_FUNCIONAL", "NUCLEO_FUNCIONAL_C", "DIRETA_FONTE", source_projection="CP")
        elif node.base == "D" and parent is not None and parent.base == "NP":
            _record_entity(cursor, ruleset, sentence, node, "F_D", "NUCLEO_FUNCIONAL", "NUCLEO_FUNCIONAL_D", "DIRETA_FONTE", source_projection="NP")
        elif node.base == "P" and parent is not None and parent.base == "PP":
            _record_entity(cursor, ruleset, sentence, node, "F_P", "NUCLEO_FRONTEIRA", "NUCLEO_P_FONTE", "DIRETA_FONTE", source_projection="PP")
        elif node.base in {"NEG", "CL", "SE", "CONJ"}:
            _record_entity(cursor, ruleset, sentence, node, "F_OP", "NUCLEO_FUNCIONAL", "OPERADOR_FUNCIONAL", "DIRETA_FONTE")
        elif _is_auxiliary_or_copula(node.base):
            _record_entity(cursor, ruleset, sentence, node, "V_AUX", "EVIDENCIA_AUXILIAR", "EVIDENCIA_AUX_COPULA", "DIRETA_FONTE")
        else:
            continue
        counts["decisions"] += 1
        counts["entities"] += 1
        counts["evidence"] += 1

    yield_cache: dict[int, tuple[str, ...]] = {}

    def source_yield(node_id: int) -> tuple[str, ...]:
        cached = yield_cache.get(node_id)
        if cached is not None:
            return cached
        current = nodes_by_id[node_id]
        if current.is_leaf:
            result = (current.token or "",)
        else:
            result = tuple(token for child in children.get(node_id, []) for token in source_yield(child.no_id))
        yield_cache[node_id] = result
        return result

    adverb_rule = ruleset.rules_by_code["E_ADV"]
    lexical_map = {
        _normalise_lexical_text(str(trigger)): str(projection)
        for trigger, projection in dict(adverb_rule.definition["lexicon"]).items()
    }
    for node in nodes:
        if node.base != "ADVP" or node.is_leaf:
            continue
        lexical_yield = " ".join(_normalise_lexical_text(token) for token in source_yield(node.no_id)).strip()
        projection = lexical_map.get(lexical_yield)
        if projection is None:
            continue
        _record_entity(
            cursor,
            ruleset,
            sentence,
            node,
            "E_ADV",
            "EVIDENCIA_CARTOGRAFICA",
            f"EVIDENCIA_CINQUE_{projection}",
            "EVIDENCIA_LEXICAL",
            source_projection="ADVP",
            evidenced_projection=projection,
            details={"gatilho_normalizado": lexical_yield, "projecao_catalogo": projection},
            evidence_type="LEXICO_CONGELADO",
            evidence_value={
                "gatilho_normalizado": lexical_yield,
                "projecao_catalogo": projection,
                "regra": "E_ADV",
            },
        )
        counts["decisions"] += 1
        counts["entities"] += 1
        counts["evidence"] += 1
        counts["cartographic"] += 1

    for phrase in nodes:
        if phrase.is_leaf or phrase.base not in SOURCE_PHRASE_BASES:
            continue
        candidates = [
            child for child in children.get(phrase.no_id, []) if _is_local_head_candidate(phrase.base, child)
        ]
        if not candidates:
            continue
        direct_source = phrase.base in {"CP", "PP"} and len(candidates) == 1
        status = "DIRETA_FONTE" if direct_source else ("AMBIGUO" if len(candidates) > 1 else "CANDIDATO_LOCAL")
        confidence = 1.0 if direct_source else (0.5 if len(candidates) > 1 else ruleset.rules_by_code["H_LOCAL"].confidence)
        for candidate_order, core in enumerate(candidates):
            _record_local_relation(
                cursor,
                ruleset,
                sentence,
                phrase,
                core,
                candidate_order,
                status,
                confidence,
                len(candidates),
            )
            counts["decisions"] += 1
            counts["relations"] += 1
            counts["evidence"] += 2
    return counts


def _insert_scope(cursor: sqlite3.Cursor, source_connection: sqlite3.Connection) -> None:
    for row in _iter_scope_blocks(source_connection):
        result = str(row["resultado"])
        cursor.execute(
            """
            INSERT INTO m3_escopo_blocos(
                analysis_id, bloco_id_m2, documento_id_m2, caminho_relativo,
                ordinal_bloco_m2, ordinal_candidato_m2, sha256_bloco_m2,
                resultado_m2, sentenca_id_m2, codigo_motivo_m2, status_analise
            ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(row["bloco_id"]),
                int(row["documento_id"]),
                str(row["caminho_relativo"]),
                int(row["ordinal_bloco"]),
                int(row["ordinal_candidato"]),
                str(row["sha256_bloco"]),
                result,
                int(row["sentenca_id"]) if row["sentenca_id"] is not None else None,
                str(row["codigo_motivo"]) if row["codigo_motivo"] is not None else None,
                STATUS_ANALISADA if result == "IMPORTADO" else STATUS_FORA_ESCOPO_REJEITADA,
            ),
        )


def _assert_safe_output(source_database: Path, output_path: Path, replace: bool) -> None:
    if source_database.resolve() == output_path.resolve():
        raise AnalysisError("o banco Marco 3 não pode substituir o banco Marco 2 de origem")
    if output_path.exists() and not replace:
        raise AnalysisError(
            f"destino já existe: {output_path}. Use --replace somente após revisar o artefato atual."
        )


def build_analysis(
    source_database: Path,
    output_path: Path,
    source_manifest_path: Path | None = None,
    ruleset_path: Path | None = None,
    *,
    replace: bool = False,
) -> AnalysisBuildReport:
    """Compila a sobrecamada Marco 3 e a promove somente após validação total."""
    source_database = source_database.resolve()
    output_path = output_path.resolve()
    source_manifest_path = source_manifest_path.resolve() if source_manifest_path is not None else None
    _assert_safe_output(source_database, output_path, replace)
    if not source_database.is_file():
        raise AnalysisError(f"banco Marco 2 não encontrado: {source_database}")
    source_validation = validate_reconstruction_database(source_database, source_manifest_path)
    if not source_validation["ok"]:
        raise AnalysisSourceMismatch("base Marco 2 inválida: " + "; ".join(source_validation["errors"]))
    ruleset = load_ruleset(ruleset_path)
    source_sha_before = sha256_file(source_database)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    staging_path = output_path.with_name(f".{output_path.name}.{uuid.uuid4().hex}.staging")
    source_connection: sqlite3.Connection | None = None
    target_connection: sqlite3.Connection | None = None
    try:
        source_connection = _connect_readonly(source_database)
        source_summary = _source_summary(source_connection)
        source_meta = dict(source_summary["meta"])
        source_manifest_sha = str(source_meta.get("source_manifest_sha256", ""))
        if source_manifest_path is not None and source_manifest_sha != sha256_file(source_manifest_path):
            raise AnalysisSourceMismatch("SHA-256 do manifesto Marco 2 diverge dos metadados do banco fonte")

        target_connection = sqlite3.connect(staging_path)
        target_connection.execute("PRAGMA foreign_keys=ON")
        target_connection.execute("PRAGMA journal_mode=DELETE")
        target_connection.execute("PRAGMA synchronous=FULL")
        _create_schema(target_connection)
        started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        _put_meta(target_connection, "analysis_schema_version", str(ANALYSIS_SCHEMA_VERSION))
        _put_meta(target_connection, "analysis_engine_version", ANALYSIS_ENGINE_VERSION)
        _put_meta(target_connection, "source_database_sha256", source_sha_before)
        _put_meta(target_connection, "source_semantic_digest", str(source_summary["semantic_digest"]))
        _put_meta(target_connection, "ruleset_sha256", ruleset.bundle_sha256)
        _put_meta(target_connection, "ruleset_version", ruleset.version)
        _put_meta(target_connection, "catalog_sha256", _catalog_sha256())
        _put_meta(target_connection, "engine_sha256", _engine_sha256())
        cursor = target_connection.cursor()
        cursor.execute(
            """
            INSERT INTO m3_base_origem(
                singleton, caminho_banco_m2, sha256_banco_m2, caminho_manifesto_m2,
                sha256_manifesto_m2, snapshot_manifesto_m2, versao_schema_m2,
                sha256_semantico_sentencas_m2, quantidade_candidatos_m2,
                quantidade_importadas_m2, quantidade_rejeitadas_m2, quantidade_nos_m2,
                validado_em_utc
            ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(source_database),
                source_sha_before,
                str(source_manifest_path) if source_manifest_path is not None else "",
                source_manifest_sha,
                str(source_meta.get("source_manifest_snapshot_id", "")),
                str(source_meta.get("schema_version", "")),
                str(source_summary["semantic_digest"]),
                int(source_summary["candidate_count"]),
                int(source_summary["imported_count"]),
                int(source_summary["rejected_count"]),
                int(source_summary["node_count"]),
                started_at,
            ),
        )
        cursor.execute(
            """
            INSERT INTO m3_conjuntos_regras(
                ruleset_id, caminho, versao, sha256_bundle, sha256_catalogo_projecoes,
                sha256_implementacao, criado_em_utc
            ) VALUES (1, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(ruleset.path),
                ruleset.version,
                ruleset.bundle_sha256,
                _catalog_sha256(),
                _engine_sha256(),
                started_at,
            ),
        )
        cursor.executemany(
            """
            INSERT INTO m3_regras(
                codigo, ruleset_id, tipo, confianca_base, descricao,
                definicao_json, sha256_definicao
            ) VALUES (?, 1, ?, ?, ?, ?, ?)
            """,
            [
                (
                    rule.code,
                    rule.kind,
                    rule.confidence,
                    rule.description,
                    _canonical_json(rule.definition),
                    rule.sha256,
                )
                for rule in ruleset.rules
            ],
        )
        cursor.executemany(
            """
            INSERT INTO m3_catalogo_projecoes(
                codigo, ruleset_id, dominio, nome_dominio, rank_hierarquia,
                recursiva, descricao
            ) VALUES (?, 1, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item["codigo"],
                    item["dominio"],
                    item["nome_dominio"],
                    item["rank_hierarquia"],
                    int(bool(item["recursiva"])),
                    item["descricao"],
                )
                for item in _catalog_payload()
            ],
        )
        cursor.execute(
            """
            INSERT INTO m3_execucoes(
                analysis_id, ruleset_id, versao_engine, sha256_engine, estado,
                iniciado_em_utc, concluido_em_utc
            ) VALUES (1, 1, ?, ?, 'PROMOVIDA', ?, ?)
            """,
            (ANALYSIS_ENGINE_VERSION, _engine_sha256(), started_at, started_at),
        )
        _insert_scope(cursor, source_connection)

        totals = _counts_template()
        for sentence, nodes in _iter_source_sentences(source_connection):
            sentence_counts = _analyse_sentence(cursor, ruleset, sentence, nodes)
            totals["analysis_sentence_count"] += 1
            totals["anchor_node_count"] += len(nodes)
            totals["decision_count"] += sentence_counts["decisions"]
            totals["entity_count"] += sentence_counts["entities"]
            totals["relation_count"] += sentence_counts["relations"]
            totals["evidence_count"] += sentence_counts["evidence"]
            totals["excluded_count"] += sentence_counts["excluded"]
            totals["cartographic_evidence_count"] += sentence_counts["cartographic"]
        totals["scope_candidate_count"] = int(source_summary["candidate_count"])
        completed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        cursor.execute(
            "UPDATE m3_execucoes SET resumo_json=?, concluido_em_utc=? WHERE analysis_id=1",
            (_canonical_json(totals), completed_at),
        )
        for key, value in totals.items():
            _put_meta(target_connection, key, str(value))
        target_connection.commit()
        target_connection.close()
        target_connection = None
        source_connection.close()
        source_connection = None

        if sha256_file(source_database) != source_sha_before:
            raise AnalysisSourceMismatch("o banco Marco 2 foi alterado durante a análise")
        validation = validate_analysis_database(
            staging_path,
            source_database,
            source_manifest_path,
            ruleset.path,
        )
        if not validation["ok"]:
            raise AnalysisError("validação do staging Marco 3 falhou: " + "; ".join(validation["errors"]))
        os.replace(staging_path, output_path)
        return AnalysisBuildReport(
            output_path=str(output_path),
            source_database_path=str(source_database),
            source_database_sha256=source_sha_before,
            source_manifest_path=str(source_manifest_path) if source_manifest_path else None,
            ruleset_path=str(ruleset.path),
            ruleset_version=ruleset.version,
            ruleset_sha256=ruleset.bundle_sha256,
            validation=validation,
        )
    finally:
        if source_connection is not None:
            source_connection.close()
        if target_connection is not None:
            target_connection.close()
        if staging_path.exists():
            staging_path.unlink()


def _table_count(connection: sqlite3.Connection, table: str) -> int:
    return int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _validate_anchor_rows(
    analysis_connection: sqlite3.Connection,
    source_connection: sqlite3.Connection,
    errors: list[str],
) -> None:
    source_cursor = source_connection.execute(
        """
        SELECT n.no_id, n.sentenca_id, r.pai_no_id, r.ordem_irmao,
               n.preordem, n.lft, n.rgt, n.profundidade, n.rotulo_origem,
               n.rotulo_base, n.funcao, n.eh_folha, n.ordem_folha, n.token_origem
        FROM recon_nos AS n
        LEFT JOIN recon_relacoes AS r
          ON r.sentenca_id=n.sentenca_id AND r.filho_no_id=n.no_id
        ORDER BY n.no_id
        """
    )
    analysis_cursor = analysis_connection.execute(
        """
        SELECT no_id_m2, sentenca_id_m2, pai_no_id_m2, ordem_irmao_m2,
               preordem, lft, rgt, profundidade, rotulo_origem, rotulo_base,
               funcao, eh_folha, ordem_folha, token_origem
        FROM m3_nos_ancora
        WHERE analysis_id=1
        ORDER BY no_id_m2
        """
    )
    for source_row, analysis_row in zip_longest(source_cursor, analysis_cursor):
        if source_row is None or analysis_row is None:
            _append_error(errors, "quantidade de âncoras M3 diverge de recon_nos")
            return
        if tuple(source_row) != tuple(analysis_row):
            _append_error(errors, f"âncora M3 divergente do nó Marco 2 {source_row[0]}")
            return


def _validate_sentence_rows(
    analysis_connection: sqlite3.Connection,
    source_connection: sqlite3.Connection,
    errors: list[str],
) -> None:
    source_cursor = source_connection.execute(
        """
        SELECT s.sentenca_id, s.bloco_id, s.documento_id, s.caminho_relativo,
               s.id_externo, s.rotulo_raiz, s.classe_estrutura,
               l.sha256_arvore_normalizada, s.sha256_folhas,
               s.quantidade_folhas, s.quantidade_nos
        FROM recon_sentencas AS s
        JOIN recon_ledger_importacao AS l ON l.bloco_id=s.bloco_id
        ORDER BY s.sentenca_id
        """
    )
    analysis_cursor = analysis_connection.execute(
        """
        SELECT sentenca_id_m2, bloco_id_m2, documento_id_m2, caminho_relativo,
               id_externo, rotulo_raiz, classe_estrutura, sha256_arvore_m2,
               sha256_folhas_m2, quantidade_folhas_m2, quantidade_nos_m2
        FROM m3_sentencas_escopo
        WHERE analysis_id=1
        ORDER BY sentenca_id_m2
        """
    )
    for source_row, analysis_row in zip_longest(source_cursor, analysis_cursor):
        if source_row is None or analysis_row is None:
            _append_error(errors, "escopo de sentenças M3 diverge de recon_sentencas")
            return
        if tuple(source_row) != tuple(analysis_row):
            _append_error(errors, f"escopo M3 divergente da sentença Marco 2 {source_row[0]}")
            return


def _validate_scope_rows(
    analysis_connection: sqlite3.Connection,
    source_connection: sqlite3.Connection,
    errors: list[str],
) -> None:
    source_cursor = source_connection.execute(
        """
        SELECT b.bloco_id, b.documento_id, d.caminho_relativo, b.ordinal_bloco,
               b.ordinal_candidato, b.sha256_bloco, l.resultado, s.sentenca_id,
               l.codigo_motivo
        FROM recon_ledger_importacao AS l
        JOIN recon_blocos_origem AS b ON b.bloco_id=l.bloco_id
        JOIN recon_documentos AS d ON d.documento_id=b.documento_id
        LEFT JOIN recon_sentencas AS s ON s.bloco_id=b.bloco_id
        ORDER BY b.bloco_id
        """
    )
    analysis_cursor = analysis_connection.execute(
        """
        SELECT bloco_id_m2, documento_id_m2, caminho_relativo, ordinal_bloco_m2,
               ordinal_candidato_m2, sha256_bloco_m2, resultado_m2, sentenca_id_m2,
               codigo_motivo_m2
        FROM m3_escopo_blocos
        WHERE analysis_id=1
        ORDER BY bloco_id_m2
        """
    )
    for source_row, analysis_row in zip_longest(source_cursor, analysis_cursor):
        if source_row is None or analysis_row is None:
            _append_error(errors, "escopo de blocos M3 diverge do ledger Marco 2")
            return
        if tuple(source_row) != tuple(analysis_row):
            _append_error(errors, f"escopo M3 divergente do bloco Marco 2 {source_row[0]}")
            return


def _validate_leaf_digests(connection: sqlite3.Connection, errors: list[str]) -> None:
    expected = {
        int(row[0]): (str(row[1]), int(row[2]), str(row[3]), int(row[4]))
        for row in connection.execute(
            """
            SELECT sentenca_id_m2, sha256_folhas_m2, quantidade_folhas_m2,
                   sha256_folhas_ancoradas, quantidade_folhas_ancoradas
            FROM m3_sentencas_escopo WHERE analysis_id=1
            """
        )
    }
    current_sentence: int | None = None
    tokens: list[str] = []

    def check_current() -> bool:
        if current_sentence is None:
            return True
        expected_digest, expected_count, anchored_digest, anchored_count = expected[current_sentence]
        observed_digest = digest_tokens(tokens)
        if (
            observed_digest != expected_digest
            or len(tokens) != expected_count
            or anchored_digest != expected_digest
            or anchored_count != expected_count
        ):
            _append_error(errors, f"folhas ancoradas divergentes na sentença Marco 2 {current_sentence}")
            return False
        return True

    for row in connection.execute(
        """
        SELECT sentenca_id_m2, token_origem
        FROM m3_nos_ancora
        WHERE analysis_id=1 AND eh_folha=1
        ORDER BY sentenca_id_m2, ordem_folha
        """
    ):
        sentence_id = int(row[0])
        if current_sentence is not None and sentence_id != current_sentence:
            if not check_current():
                return
            tokens = []
        current_sentence = sentence_id
        tokens.append(str(row[1]))
    check_current()


def _validate_ruleset_tables(connection: sqlite3.Connection, ruleset: Ruleset, errors: list[str]) -> None:
    ruleset_row = connection.execute(
        """
        SELECT caminho, versao, sha256_bundle, sha256_catalogo_projecoes, sha256_implementacao
        FROM m3_conjuntos_regras WHERE ruleset_id=1
        """
    ).fetchone()
    expected = (str(ruleset.path), ruleset.version, ruleset.bundle_sha256, _catalog_sha256(), _engine_sha256())
    if ruleset_row is None or tuple(ruleset_row) != expected:
        _append_error(errors, "âncora do conjunto de regras Marco 3 divergente")
    stored_rules = {
        str(row[0]): (str(row[1]), float(row[2]), str(row[3]), str(row[4]), str(row[5]))
        for row in connection.execute(
            "SELECT codigo, tipo, confianca_base, descricao, definicao_json, sha256_definicao FROM m3_regras"
        )
    }
    expected_rules = {
        rule.code: (
            rule.kind,
            rule.confidence,
            rule.description,
            _canonical_json(rule.definition),
            rule.sha256,
        )
        for rule in ruleset.rules
    }
    if stored_rules != expected_rules:
        _append_error(errors, "tabela de regras Marco 3 diverge do bundle congelado")
    catalog_rows = [
        tuple(row)
        for row in connection.execute(
            "SELECT codigo, dominio, nome_dominio, rank_hierarquia, recursiva, descricao FROM m3_catalogo_projecoes ORDER BY rank_hierarquia"
        )
    ]
    expected_catalog = [
        (
            item["codigo"],
            item["dominio"],
            item["nome_dominio"],
            item["rank_hierarquia"],
            int(bool(item["recursiva"])),
            item["descricao"],
        )
        for item in _catalog_payload()
    ]
    if catalog_rows != expected_catalog:
        _append_error(errors, "catálogo cartográfico congelado diverge da definição versionada")


def _validate_decisions(connection: sqlite3.Connection, errors: list[str]) -> None:
    # SQLite devolve uma linha por decisão na consulta interna; o SELECT externo
    # conta o conjunto inteiro sem depender de um comportamento de ``fetchone``.
    missing_evidence = int(
        connection.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT d.decision_id
                FROM m3_decisoes AS d
                LEFT JOIN m3_evidencias AS e ON e.decision_id=d.decision_id
                GROUP BY d.decision_id
                HAVING COUNT(e.evidence_id)=0
            )
            """
        ).fetchone()[0]
    )
    if missing_evidence:
        _append_error(errors, f"{missing_evidence} decisão(ões) M3 sem evidência")
    for row in connection.execute("SELECT evidence_id, valor_json, sha256_valor FROM m3_evidencias ORDER BY evidence_id"):
        if _sha256_text(str(row[1])) != str(row[2]):
            _append_error(errors, f"hash de evidência M3 divergente: {row[0]}")
            break
    orphan_entity = int(
        connection.execute(
            """
            SELECT COUNT(*) FROM m3_entidades AS e
            JOIN m3_decisoes AS d ON d.decision_id=e.decision_id
            WHERE d.tipo_decisao <> 'ENTIDADE'
            """
        ).fetchone()[0]
    )
    orphan_relation = int(
        connection.execute(
            """
            SELECT COUNT(*) FROM m3_relacoes AS r
            JOIN m3_decisoes AS d ON d.decision_id=r.decision_id
            WHERE d.tipo_decisao <> 'RELACAO'
            """
        ).fetchone()[0]
    )
    unmaterialized = int(
        connection.execute(
            """
            SELECT COUNT(*) FROM m3_decisoes AS d
            LEFT JOIN m3_entidades AS e ON e.decision_id=d.decision_id
            LEFT JOIN m3_relacoes AS r ON r.decision_id=d.decision_id
            WHERE (d.tipo_decisao='ENTIDADE' AND e.entity_id IS NULL)
               OR (d.tipo_decisao='RELACAO' AND r.relation_id IS NULL)
            """
        ).fetchone()[0]
    )
    if orphan_entity or orphan_relation or unmaterialized:
        _append_error(errors, "decisões M3 não correspondem a entidades ou relações do mesmo tipo")
    invalid_projection = int(
        connection.execute(
            """
            SELECT COUNT(*)
            FROM m3_entidades AS e
            LEFT JOIN m3_catalogo_projecoes AS c ON c.codigo=e.projecao_evidenciada
            WHERE e.tipo='EVIDENCIA_CARTOGRAFICA' AND c.codigo IS NULL
            """
        ).fetchone()[0]
    )
    if invalid_projection:
        _append_error(errors, "evidência cartográfica referencia projeção fora do catálogo")
    forbidden_source_projection = int(
        connection.execute(
            """
            SELECT COUNT(*) FROM m3_entidades
            WHERE tipo='PROJECAO_FONTE'
              AND (projecao_evidenciada IS NOT NULL OR rotulo_analitico LIKE '%ForceP%'
                   OR rotulo_analitico LIKE '%FinP%' OR rotulo_analitico LIKE '%MoodP%'
                   OR rotulo_analitico LIKE '%AspP%' OR rotulo_analitico LIKE '%VoiceP%'
                   OR rotulo_analitico LIKE '%Root%')
            """
        ).fetchone()[0]
    )
    if forbidden_source_projection:
        _append_error(errors, "projeção cartográfica foi materializada indevidamente como estrutura-fonte")
    invalid_relation = int(
        connection.execute(
            """
            SELECT COUNT(*)
            FROM m3_relacoes AS r
            JOIN m3_nos_ancora AS core
              ON core.analysis_id=r.analysis_id AND core.no_id_m2=r.no_nucleo_id_m2
            WHERE core.pai_no_id_m2 <> r.no_sintagma_id_m2
               OR core.ordem_irmao_m2 IS NULL
            """
        ).fetchone()[0]
    )
    if invalid_relation:
        _append_error(errors, "relação local M3 não corresponde a pai-filho imediato da fonte")
    invalid_excluded_core = int(
        connection.execute(
            """
            SELECT COUNT(*)
            FROM m3_entidades AS e
            JOIN m3_nos_ancora AS n
              ON n.analysis_id=e.analysis_id AND n.no_id_m2=e.no_ancora_id_m2
            WHERE e.tipo IN ('NUCLEO_LEXICAL', 'NUCLEO_FUNCIONAL', 'NUCLEO_FRONTEIRA')
              AND (n.token_origem='0' OR n.token_origem LIKE '*%'
                   OR n.rotulo_base IN ('PUNC', 'PON', 'PU', 'PCT', 'OPEN', 'CLOSE', ',', '.', ':', ';'))
            """
        ).fetchone()[0]
    )
    if invalid_excluded_core:
        _append_error(errors, "categoria vazia ou pontuação recebeu núcleo M3")


def validate_analysis_database(
    analysis_database: Path,
    source_database: Path,
    source_manifest_path: Path | None = None,
    ruleset_path: Path | None = None,
) -> dict[str, Any]:
    """Confere a âncora Marco 2, as regras e toda a camada derivada Marco 3."""
    analysis_database = analysis_database.resolve()
    source_database = source_database.resolve()
    source_manifest_path = source_manifest_path.resolve() if source_manifest_path is not None else None
    errors: list[str] = []
    counts = _counts_template()
    if not analysis_database.is_file():
        return {"ok": False, "errors": [f"banco Marco 3 não encontrado: {analysis_database}"], "counts": counts}
    if not source_database.is_file():
        return {"ok": False, "errors": [f"banco Marco 2 não encontrado: {source_database}"], "counts": counts}
    try:
        ruleset = load_ruleset(ruleset_path)
    except AnalysisError as error:
        return {"ok": False, "errors": [str(error)], "counts": counts}
    source_validation = validate_reconstruction_database(source_database, source_manifest_path)
    if not source_validation["ok"]:
        for error in source_validation["errors"]:
            _append_error(errors, f"base Marco 2 inválida: {error}")

    source_connection: sqlite3.Connection | None = None
    analysis_connection: sqlite3.Connection | None = None
    try:
        source_connection = _connect_readonly(source_database)
        analysis_connection = _connect_readonly(analysis_database)
        analysis_connection.row_factory = sqlite3.Row
        integrity = [str(row[0]) for row in analysis_connection.execute("PRAGMA integrity_check")]
        if integrity != ["ok"]:
            _append_error(errors, f"integrity_check Marco 3 falhou: {integrity}")
        foreign_keys = analysis_connection.execute("PRAGMA foreign_key_check").fetchall()
        if foreign_keys:
            _append_error(errors, f"foreign_key_check Marco 3 encontrou {len(foreign_keys)} erro(s)")
        try:
            meta = _read_meta(analysis_connection, "m3_meta")
            base = analysis_connection.execute("SELECT * FROM m3_base_origem WHERE singleton=1").fetchone()
        except sqlite3.DatabaseError as error:
            _append_error(errors, f"esquema Marco 3 indisponível: {error}")
            return {"ok": False, "errors": errors, "counts": counts}
        if base is None or _table_count(analysis_connection, "m3_base_origem") != 1:
            _append_error(errors, "m3_base_origem deve conter exatamente uma âncora")
            return {"ok": False, "errors": errors, "counts": counts}

        source_summary = _source_summary(source_connection)
        source_meta = dict(source_summary["meta"])
        source_sha = sha256_file(source_database)
        expected_manifest_sha = sha256_file(source_manifest_path) if source_manifest_path is not None else str(source_meta.get("source_manifest_sha256", ""))
        base_values = dict(base)
        expected_base = {
            "sha256_banco_m2": source_sha,
            "sha256_manifesto_m2": expected_manifest_sha,
            "snapshot_manifesto_m2": str(source_meta.get("source_manifest_snapshot_id", "")),
            "versao_schema_m2": str(source_meta.get("schema_version", "")),
            "sha256_semantico_sentencas_m2": str(source_summary["semantic_digest"]),
            "quantidade_candidatos_m2": int(source_summary["candidate_count"]),
            "quantidade_importadas_m2": int(source_summary["imported_count"]),
            "quantidade_rejeitadas_m2": int(source_summary["rejected_count"]),
            "quantidade_nos_m2": int(source_summary["node_count"]),
        }
        for field, expected_value in expected_base.items():
            if base_values.get(field) != expected_value:
                _append_error(errors, f"âncora Marco 2 divergente: {field}")
        if meta.get("analysis_schema_version") != str(ANALYSIS_SCHEMA_VERSION):
            _append_error(errors, "versão de schema Marco 3 divergente")
        if meta.get("analysis_engine_version") != ANALYSIS_ENGINE_VERSION:
            _append_error(errors, "versão do motor Marco 3 divergente")
        if meta.get("source_database_sha256") != source_sha:
            _append_error(errors, "SHA-256 do banco fonte Marco 2 divergente")
        if meta.get("source_semantic_digest") != str(source_summary["semantic_digest"]):
            _append_error(errors, "digest semântico da fonte Marco 2 divergente")
        _validate_ruleset_tables(analysis_connection, ruleset, errors)
        _validate_scope_rows(analysis_connection, source_connection, errors)
        _validate_sentence_rows(analysis_connection, source_connection, errors)
        _validate_anchor_rows(analysis_connection, source_connection, errors)
        _validate_leaf_digests(analysis_connection, errors)
        _validate_decisions(analysis_connection, errors)

        counts = {
            "scope_candidate_count": _table_count(analysis_connection, "m3_escopo_blocos"),
            "analysis_sentence_count": _table_count(analysis_connection, "m3_sentencas_escopo"),
            "anchor_node_count": _table_count(analysis_connection, "m3_nos_ancora"),
            "decision_count": _table_count(analysis_connection, "m3_decisoes"),
            "entity_count": _table_count(analysis_connection, "m3_entidades"),
            "relation_count": _table_count(analysis_connection, "m3_relacoes"),
            "evidence_count": _table_count(analysis_connection, "m3_evidencias"),
            "excluded_count": int(
                analysis_connection.execute("SELECT COUNT(*) FROM m3_entidades WHERE tipo='EXCLUSAO'").fetchone()[0]
            ),
            "cartographic_evidence_count": int(
                analysis_connection.execute("SELECT COUNT(*) FROM m3_entidades WHERE tipo='EVIDENCIA_CARTOGRAFICA'").fetchone()[0]
            ),
        }
        execution = analysis_connection.execute("SELECT resumo_json FROM m3_execucoes WHERE analysis_id=1").fetchone()
        if execution is None:
            _append_error(errors, "execução Marco 3 ausente")
        else:
            try:
                stored_counts = json.loads(str(execution[0]))
            except json.JSONDecodeError:
                stored_counts = None
            if stored_counts != counts:
                _append_error(errors, "resumo de contagens da execução Marco 3 divergente")
    except (OSError, sqlite3.DatabaseError, ValueError) as error:
        _append_error(errors, f"falha ao validar Marco 3: {error}")
    finally:
        if source_connection is not None:
            source_connection.close()
        if analysis_connection is not None:
            analysis_connection.close()
    return {"ok": not errors, "errors": errors, "counts": counts}


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Cria e verifica a camada Marco 3 de análise gramatical evidencial."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    default_manifest = PROJECT_ROOT / "docs" / "manifests" / "marco2_importacao_rastreavel_2026-08-31.json"
    build_parser = subparsers.add_parser("build", help="cria um banco Marco 3 novo por staging atômico")
    build_parser.add_argument("--source-db", required=True, help="banco Marco 2 validado, aberto somente em leitura")
    build_parser.add_argument("--output", required=True, help="novo SQLite Marco 3")
    build_parser.add_argument("--source-manifest", default=str(default_manifest), help="manifesto externo que ancora o Marco 2")
    build_parser.add_argument("--ruleset", default=str(DEFAULT_RULESET_PATH), help="bundle JSON de regras versionadas")
    build_parser.add_argument("--replace", action="store_true", help="substitui o destino somente após validação")
    verify_parser = subparsers.add_parser("verify", help="valida uma camada Marco 3 existente")
    verify_parser.add_argument("--db", required=True, help="SQLite Marco 3")
    verify_parser.add_argument("--source-db", required=True, help="banco Marco 2 que deve coincidir com a âncora")
    verify_parser.add_argument("--source-manifest", default=str(default_manifest), help="manifesto externo que ancora o Marco 2")
    verify_parser.add_argument("--ruleset", default=str(DEFAULT_RULESET_PATH), help="bundle JSON de regras versionadas")
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            report = build_analysis(
                Path(args.source_db),
                Path(args.output),
                Path(args.source_manifest),
                Path(args.ruleset),
                replace=bool(args.replace),
            )
            _print_json(report.as_dict())
            return 0
        result = validate_analysis_database(
            Path(args.db),
            Path(args.source_db),
            Path(args.source_manifest),
            Path(args.ruleset),
        )
        _print_json(result)
        return 0 if result["ok"] else 1
    except AnalysisError as error:
        _print_json({"ok": False, "error": str(error)})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
