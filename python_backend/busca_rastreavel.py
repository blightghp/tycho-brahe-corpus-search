"""Busca determinística e somente-leitura sobre a camada evidencial Marco 3.

Este módulo não consulta os bancos legados nem transforma árvores PSD. Ele
recebe um SQLite ``m3_*`` que já foi promovido pelo Marco 3, executa filtros
exatos exclusivamente por parâmetros SQLite e devolve cada correspondência com
sua âncora de origem, decisão, regra e evidências. A revalidação integral da
ligação M3--M2 pode ser solicitada explicitamente antes da consulta; o caminho
normal usa uma pré-condição estrutural leve para que uma consulta interativa
não precise reexaminar milhões de evidências a cada chamada.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from analise_gramatical_recon import (
    ANALYSIS_SCHEMA_VERSION,
    AnalysisError,
    validate_analysis_database,
)


DEFAULT_LIMIT = 50
MAX_LIMIT = 500
ENTITY_TYPES = frozenset(
    {
        "EXCLUSAO",
        "NUCLEO_LEXICAL",
        "NUCLEO_FUNCIONAL",
        "NUCLEO_FRONTEIRA",
        "EVIDENCIA_AUXILIAR",
        "PROJECAO_FONTE",
        "EVIDENCIA_CARTOGRAFICA",
    }
)
_REQUIRED_TABLES = frozenset(
    {
        "m3_meta",
        "m3_base_origem",
        "m3_conjuntos_regras",
        "m3_execucoes",
        "m3_escopo_blocos",
        "m3_sentencas_escopo",
        "m3_nos_ancora",
        "m3_decisoes",
        "m3_entidades",
        "m3_evidencias",
    }
)


class SearchError(RuntimeError):
    """Falha de pré-condição ou de contrato da busca Marco 4."""


@dataclass(frozen=True)
class SearchCriteria:
    """Filtros exatos e conjuntivos da busca por entidades Marco 3.

    ``projection`` consulta tanto ``projecao_fonte`` quanto
    ``projecao_evidenciada``. Assim, ``CP`` encontra a estrutura observada na
    fonte, enquanto ``MoodP_evaluative`` encontra somente a evidência lexical
    que a referência; nenhum dos dois filtros cria uma projeção nova.
    """

    entity_type: str | None = None
    analytical_label: str | None = None
    projection: str | None = None
    token: str | None = None
    rule_id: str | None = None
    limit: int = DEFAULT_LIMIT

    def validated(self) -> "SearchCriteria":
        """Valida limites e valores sem interpolá-los em SQL."""
        values = {
            "entity_type": self.entity_type,
            "analytical_label": self.analytical_label,
            "projection": self.projection,
            "token": self.token,
            "rule_id": self.rule_id,
        }
        for name, value in values.items():
            if value is None:
                continue
            if not isinstance(value, str) or not value or len(value) > 512 or "\x00" in value:
                raise SearchError(f"filtro inválido para {name}")
        if all(value is None for value in values.values()):
            raise SearchError("informe ao menos um filtro antes de consultar o Marco 4")
        if self.entity_type is not None and self.entity_type not in ENTITY_TYPES:
            valid_types = ", ".join(sorted(ENTITY_TYPES))
            raise SearchError(f"tipo de entidade desconhecido: {self.entity_type!r}; use: {valid_types}")
        if isinstance(self.limit, bool) or not isinstance(self.limit, int):
            raise SearchError("limit deve ser um inteiro")
        if not 1 <= self.limit <= MAX_LIMIT:
            raise SearchError(f"limit deve estar entre 1 e {MAX_LIMIT}")
        return self

    def as_dict(self) -> dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "label": self.analytical_label,
            "projection": self.projection,
            "token": self.token,
            "rule": self.rule_id,
            "limit": self.limit,
        }


@dataclass(frozen=True)
class AnalysisIdentity:
    """Identidade versionada do artefato M3 que respondeu à busca."""

    analysis_id: int
    schema_version: str
    engine_version: str
    engine_sha256: str
    ruleset_version: str
    ruleset_sha256: str
    source_database_sha256: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "analysis_id": self.analysis_id,
            "schema_version": self.schema_version,
            "engine_version": self.engine_version,
            "engine_sha256": self.engine_sha256,
            "ruleset_version": self.ruleset_version,
            "ruleset_sha256": self.ruleset_sha256,
            "source_database_sha256": self.source_database_sha256,
        }


@dataclass(frozen=True)
class SearchReport:
    """Resultado serializável da busca, sempre acompanhado da proveniência."""

    identity: AnalysisIdentity
    criteria: SearchCriteria
    results: tuple[dict[str, Any], ...]
    full_validation_performed: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": True,
            "analysis": self.identity.as_dict(),
            "query": self.criteria.as_dict(),
            "validation": {
                "mode": "integral_m3_m2" if self.full_validation_performed else "precondicao_m3_promovido",
                "full_source_validation": self.full_validation_performed,
            },
            "result_count": len(self.results),
            "results": list(self.results),
        }


def _connect_readonly(path: Path) -> sqlite3.Connection:
    resolved = path.resolve()
    if not resolved.is_file():
        raise SearchError(f"banco Marco 3 não encontrado: {resolved}")
    connection = sqlite3.connect(f"{resolved.as_uri()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    return connection


def _load_identity(connection: sqlite3.Connection) -> AnalysisIdentity:
    """Confere a pré-condição leve de um artefato M3 já promovido.

    A prova integral M3--M2 é deliberadamente separada em
    :func:`validate_analysis_database`; ela pode ser solicitada em
    :func:`search_analysis` quando o banco fonte estiver disponível.
    """
    try:
        tables = {
            str(row[0])
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    except sqlite3.DatabaseError as error:
        raise SearchError(f"não foi possível ler o esquema Marco 3: {error}") from error
    missing = sorted(_REQUIRED_TABLES - tables)
    if missing:
        raise SearchError("artefato não possui o esquema Marco 3 exigido: " + ", ".join(missing))

    try:
        meta = {
            str(row[0]): str(row[1])
            for row in connection.execute("SELECT chave, valor FROM m3_meta")
        }
        execution_rows = connection.execute(
            "SELECT analysis_id, versao_engine, sha256_engine, estado FROM m3_execucoes ORDER BY analysis_id"
        ).fetchall()
        ruleset_rows = connection.execute(
            "SELECT ruleset_id, versao, sha256_bundle FROM m3_conjuntos_regras ORDER BY ruleset_id"
        ).fetchall()
        base_rows = connection.execute(
            "SELECT singleton, sha256_banco_m2 FROM m3_base_origem ORDER BY singleton"
        ).fetchall()
    except sqlite3.DatabaseError as error:
        raise SearchError(f"não foi possível consultar a pré-condição Marco 3: {error}") from error

    if meta.get("analysis_schema_version") != str(ANALYSIS_SCHEMA_VERSION):
        raise SearchError("versão de schema Marco 3 incompatível para busca")
    if len(execution_rows) != 1 or int(execution_rows[0]["analysis_id"]) != 1:
        raise SearchError("artefato Marco 3 deve ter exatamente uma execução de análise")
    execution = execution_rows[0]
    if str(execution["estado"]) != "PROMOVIDA":
        raise SearchError("artefato Marco 3 não foi promovido após validação")
    if len(ruleset_rows) != 1 or int(ruleset_rows[0]["ruleset_id"]) != 1:
        raise SearchError("artefato Marco 3 deve ter exatamente um conjunto de regras")
    if len(base_rows) != 1 or int(base_rows[0]["singleton"]) != 1:
        raise SearchError("artefato Marco 3 deve ter exatamente uma âncora Marco 2")

    ruleset = ruleset_rows[0]
    source_sha = str(base_rows[0]["sha256_banco_m2"])
    required_meta = {
        "analysis_engine_version": str(execution["versao_engine"]),
        "source_database_sha256": source_sha,
        "ruleset_version": str(ruleset["versao"]),
        "ruleset_sha256": str(ruleset["sha256_bundle"]),
        "engine_sha256": str(execution["sha256_engine"]),
    }
    mismatches = [key for key, value in required_meta.items() if meta.get(key) != value]
    if mismatches:
        raise SearchError("metadados de identidade Marco 3 divergentes: " + ", ".join(mismatches))
    return AnalysisIdentity(
        analysis_id=int(execution["analysis_id"]),
        schema_version=str(meta["analysis_schema_version"]),
        engine_version=str(execution["versao_engine"]),
        engine_sha256=str(execution["sha256_engine"]),
        ruleset_version=str(ruleset["versao"]),
        ruleset_sha256=str(ruleset["sha256_bundle"]),
        source_database_sha256=source_sha,
    )


def _decode_json(raw: str, field_name: str, identifier: int) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError as error:
        raise SearchError(f"JSON inválido em {field_name} para registro {identifier}") from error


def _query_rows(connection: sqlite3.Connection, criteria: SearchCriteria) -> list[sqlite3.Row]:
    conditions = ["e.analysis_id=1", "d.analysis_id=1", "n.analysis_id=1", "s.analysis_id=1", "b.analysis_id=1"]
    parameters: list[Any] = []
    if criteria.entity_type is not None:
        conditions.append("e.tipo=?")
        parameters.append(criteria.entity_type)
    if criteria.analytical_label is not None:
        conditions.append("e.rotulo_analitico=?")
        parameters.append(criteria.analytical_label)
    if criteria.projection is not None:
        conditions.append("(e.projecao_fonte=? OR e.projecao_evidenciada=?)")
        parameters.extend((criteria.projection, criteria.projection))
    if criteria.token is not None:
        conditions.append("n.token_origem=?")
        parameters.append(criteria.token)
    if criteria.rule_id is not None:
        conditions.append("d.regra_id=?")
        parameters.append(criteria.rule_id)
    parameters.append(criteria.limit)
    where_clause = " AND ".join(conditions)
    return connection.execute(
        f"""
        SELECT
            e.entity_id, e.decision_id, e.sentenca_id_m2, e.no_ancora_id_m2,
            e.tipo AS entity_type, e.rotulo_analitico, e.projecao_fonte,
            e.projecao_evidenciada, e.ordem AS entity_order, e.detalhes_json,
            d.regra_id, d.confianca, d.metodo_confianca, d.status_evidencia,
            d.estado_revisao, d.justificativa,
            n.rotulo_origem, n.rotulo_base, n.funcao, n.preordem,
            n.ordem_folha, n.token_origem,
            s.bloco_id_m2, s.documento_id_m2, s.caminho_relativo, s.id_externo,
            s.rotulo_raiz, s.classe_estrutura, s.sha256_arvore_m2,
            s.sha256_folhas_m2,
            b.ordinal_bloco_m2, b.ordinal_candidato_m2, b.sha256_bloco_m2,
            b.status_analise, b.resultado_m2
        FROM m3_entidades AS e
        JOIN m3_decisoes AS d
          ON d.decision_id=e.decision_id AND d.analysis_id=e.analysis_id
        JOIN m3_nos_ancora AS n
          ON n.analysis_id=e.analysis_id
         AND n.sentenca_id_m2=e.sentenca_id_m2
         AND n.no_id_m2=e.no_ancora_id_m2
        JOIN m3_sentencas_escopo AS s
          ON s.analysis_id=e.analysis_id AND s.sentenca_id_m2=e.sentenca_id_m2
        JOIN m3_escopo_blocos AS b
          ON b.analysis_id=s.analysis_id AND b.bloco_id_m2=s.bloco_id_m2
        WHERE {where_clause}
        ORDER BY
            s.caminho_relativo COLLATE BINARY ASC,
            b.ordinal_bloco_m2 ASC,
            s.sentenca_id_m2 ASC,
            n.preordem ASC,
            e.entity_id ASC
        LIMIT ?
        """,
        parameters,
    ).fetchall()


def _load_evidence(
    connection: sqlite3.Connection,
    decision_ids: Iterable[int],
) -> dict[int, list[dict[str, Any]]]:
    ids = tuple(decision_ids)
    if not ids:
        return {}
    placeholders = ", ".join("?" for _ in ids)
    evidence_by_decision: dict[int, list[dict[str, Any]]] = {decision_id: [] for decision_id in ids}
    rows = connection.execute(
        f"""
        SELECT evidence_id, decision_id, tipo, ordinal, valor_json, sha256_valor, descricao
        FROM m3_evidencias
        WHERE decision_id IN ({placeholders})
        ORDER BY decision_id ASC, ordinal ASC, evidence_id ASC
        """,
        ids,
    ).fetchall()
    for row in rows:
        evidence_id = int(row["evidence_id"])
        evidence_by_decision[int(row["decision_id"])].append(
            {
                "evidence_id": evidence_id,
                "type": str(row["tipo"]),
                "ordinal": int(row["ordinal"]),
                "value": _decode_json(str(row["valor_json"]), "m3_evidencias.valor_json", evidence_id),
                "sha256": str(row["sha256_valor"]),
                "description": str(row["descricao"]),
            }
        )
    missing = [str(decision_id) for decision_id, evidence in evidence_by_decision.items() if not evidence]
    if missing:
        raise SearchError("resultado Marco 3 sem evidência obrigatória: " + ", ".join(missing))
    return evidence_by_decision


def _materialise_results(
    rows: Iterable[sqlite3.Row],
    identity: AnalysisIdentity,
    evidence_by_decision: dict[int, list[dict[str, Any]]],
) -> tuple[dict[str, Any], ...]:
    results: list[dict[str, Any]] = []
    for row in rows:
        entity_id = int(row["entity_id"])
        decision_id = int(row["decision_id"])
        results.append(
            {
                "analysis": identity.as_dict(),
                "origin": {
                    "relative_path": str(row["caminho_relativo"]),
                    "document_id": int(row["documento_id_m2"]),
                    "block_id": int(row["bloco_id_m2"]),
                    "block_ordinal": int(row["ordinal_bloco_m2"]),
                    "candidate_ordinal": int(row["ordinal_candidato_m2"]),
                    "block_sha256": str(row["sha256_bloco_m2"]),
                    "import_result": str(row["resultado_m2"]),
                    "analysis_scope_status": str(row["status_analise"]),
                    "sentence_id": int(row["sentenca_id_m2"]),
                    "external_id": str(row["id_externo"]) if row["id_externo"] is not None else None,
                    "root_label": str(row["rotulo_raiz"]),
                    "structure_class": str(row["classe_estrutura"]),
                    "tree_sha256": str(row["sha256_arvore_m2"]),
                    "leaves_sha256": str(row["sha256_folhas_m2"]),
                },
                "anchor": {
                    "node_id": int(row["no_ancora_id_m2"]),
                    "source_label": str(row["rotulo_origem"]),
                    "source_base": str(row["rotulo_base"]),
                    "source_function": str(row["funcao"]) if row["funcao"] is not None else None,
                    "preorder": int(row["preordem"]),
                    "leaf_ordinal": int(row["ordem_folha"]) if row["ordem_folha"] is not None else None,
                    "token": str(row["token_origem"]) if row["token_origem"] is not None else None,
                },
                "entity": {
                    "entity_id": entity_id,
                    "type": str(row["entity_type"]),
                    "analytical_label": str(row["rotulo_analitico"]),
                    "source_projection": str(row["projecao_fonte"])
                    if row["projecao_fonte"] is not None
                    else None,
                    "evidenced_projection": str(row["projecao_evidenciada"])
                    if row["projecao_evidenciada"] is not None
                    else None,
                    "order": int(row["entity_order"]),
                    "details": _decode_json(str(row["detalhes_json"]), "m3_entidades.detalhes_json", entity_id),
                },
                "decision": {
                    "decision_id": decision_id,
                    "rule_id": str(row["regra_id"]),
                    "confidence": float(row["confianca"]),
                    "confidence_method": str(row["metodo_confianca"]),
                    "evidence_status": str(row["status_evidencia"]),
                    "review_status": str(row["estado_revisao"]),
                    "justification": str(row["justificativa"]),
                },
                "evidence": evidence_by_decision[decision_id],
            }
        )
    return tuple(results)


def search_analysis(
    analysis_database: Path,
    criteria: SearchCriteria | None = None,
    *,
    source_database: Path | None = None,
    source_manifest_path: Path | None = None,
    ruleset_path: Path | None = None,
    require_full_validation: bool = False,
) -> SearchReport:
    """Executa uma busca de entidades do Marco 3 sem modificar o artefato.

    Quando ``require_full_validation`` é verdadeiro, ``source_database`` é
    obrigatório e o validador Marco 3 confere antes a âncora M3--M2, o
    manifesto, as regras, as folhas e as evidências. Sem essa opção, a função
    requer um M3 já promovido e verifica apenas sua identidade e estrutura
    essencial, preservando um caminho de consulta adequado à interface.
    """
    effective_criteria = (criteria or SearchCriteria()).validated()
    if require_full_validation:
        if source_database is None:
            raise SearchError("source_database é obrigatório para validação integral M3--M2")
        validation = validate_analysis_database(
            analysis_database,
            source_database,
            source_manifest_path,
            ruleset_path,
        )
        if not validation["ok"]:
            raise SearchError("validação integral Marco 3 falhou: " + "; ".join(validation["errors"]))

    connection: sqlite3.Connection | None = None
    try:
        connection = _connect_readonly(analysis_database)
        identity = _load_identity(connection)
        rows = _query_rows(connection, effective_criteria)
        evidence_by_decision = _load_evidence(connection, (int(row["decision_id"]) for row in rows))
        results = _materialise_results(rows, identity, evidence_by_decision)
        return SearchReport(
            identity=identity,
            criteria=effective_criteria,
            results=results,
            full_validation_performed=require_full_validation,
        )
    except (sqlite3.DatabaseError, OSError, ValueError) as error:
        raise SearchError(f"falha ao consultar o artefato Marco 3: {error}") from error
    finally:
        if connection is not None:
            connection.close()


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Consulta entidades rastreáveis de um banco Marco 3 já promovido."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    search_parser = subparsers.add_parser("search", help="executa filtros exatos e retorna proveniência completa")
    search_parser.add_argument("--db", required=True, help="SQLite Marco 3 promovido")
    search_parser.add_argument("--entity-type", choices=sorted(ENTITY_TYPES), help="tipo de entidade Marco 3")
    search_parser.add_argument("--label", dest="analytical_label", help="rótulo analítico exato")
    search_parser.add_argument("--projection", help="projeção fonte ou evidenciada exata")
    search_parser.add_argument("--token", help="token de origem exato")
    search_parser.add_argument("--rule", dest="rule_id", help="identificador de regra exato")
    search_parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help=f"máximo de resultados (1-{MAX_LIMIT})")
    search_parser.add_argument(
        "--verify-source",
        action="store_true",
        help="revalida integralmente M3 contra M2 antes de consultar (mais custoso)",
    )
    search_parser.add_argument("--source-db", help="SQLite Marco 2 exigido por --verify-source")
    search_parser.add_argument("--source-manifest", help="manifesto externo Marco 2 para --verify-source")
    search_parser.add_argument("--ruleset", help="bundle de regras para --verify-source")
    args = parser.parse_args(argv)
    try:
        criteria = SearchCriteria(
            entity_type=args.entity_type,
            analytical_label=args.analytical_label,
            projection=args.projection,
            token=args.token,
            rule_id=args.rule_id,
            limit=args.limit,
        )
        report = search_analysis(
            Path(args.db),
            criteria,
            source_database=Path(args.source_db) if args.source_db else None,
            source_manifest_path=Path(args.source_manifest) if args.source_manifest else None,
            ruleset_path=Path(args.ruleset) if args.ruleset else None,
            require_full_validation=bool(args.verify_source),
        )
        _print_json(report.as_dict())
        return 0
    except (AnalysisError, SearchError) as error:
        _print_json({"ok": False, "error": str(error)})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
