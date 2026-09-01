"""Reconstrói um banco PSD auditável sem reutilizar os derivados legados.

O importador trabalha somente com a biblioteca padrão. Cada grupo físico do
arquivo fonte (delimitado por uma linha em branco) é preservado; cada candidato
histórico IP/CP recebe, além disso, uma decisão no *ledger*. Assim, não há
``continue`` silencioso: todo candidato termina como ``IMPORTADO`` ou
``REJEITADO`` com motivo, e ``CODE``/outros registros seguem auditáveis na
tabela física.

O banco é escrito em staging no mesmo diretório do destino, validado por
inteiro e promovido com ``os.replace``. Os PSD e os bancos congelados nunca
são alterados por este módulo.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Sequence

from controle_artefatos import (
    PHYSICAL_SEPARATOR_RE,
    PHYSICAL_SEGMENTATION_VERSION,
    PHYSICAL_TRIM_BYTES,
    candidate_tree_fingerprint,
    is_historical_candidate_physical_block,
    load_manifest,
    physical_psd_fingerprint,
    physical_record_fingerprint,
    sha256_file,
    split_terminal_dos_trailer,
)
from metadata_tycho import extrair_metadados_arquivo


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PARSER_VERSION = "psd-physical-ledger@1"
RECONSTRUCTION_SCHEMA_VERSION = 1
STATUS_IMPORTED = "IMPORTADO"
STATUS_REJECTED = "REJEITADO"
ID_RECORD_RE = re.compile(r"\(ID\s+([^)]+)\)")
# Alias local para tornar explícito que a normalização serve exclusivamente à
# detecção de blocos vazios/marker; o BLOB persistido nunca é normalizado.
TRIM_BYTES = PHYSICAL_TRIM_BYTES


class ReconstructionError(RuntimeError):
    """Erro controlado de compilação do banco reconstruído."""


class SourceManifestMismatch(ReconstructionError):
    """As fontes não correspondem ao manifesto canônico informado."""


class BuildRejectedError(ReconstructionError):
    """A política do chamador não permite promover blocos rejeitados."""


class PsdParseError(ValueError):
    """Erro estruturado de parsing, persistido como motivo de rejeição."""

    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class SourceBlock:
    """Unidade física de uma fonte PSD, com offsets em bytes (fim exclusivo)."""

    ordinal: int
    start_byte: int
    end_byte: int
    raw_bytes: bytes


@dataclass(frozen=True)
class PsdNode:
    """Árvore PSD mínima e fiel ao texto fonte, sem normalização linguística."""

    label: str
    children: tuple["PsdNode | str", ...]


@dataclass(frozen=True)
class NumberedNode:
    """Nó com coordenadas determinísticas para persistência e busca futura."""

    node: PsdNode
    preorder: int
    lft: int
    rgt: int
    depth: int
    leaf_ordinal: int | None
    children: tuple["NumberedNode", ...]


@dataclass(frozen=True)
class BuildReport:
    output_path: str
    document_count: int
    block_count: int
    candidate_count: int
    imported_count: int
    rejected_count: int
    node_count: int
    validation: dict[str, Any]
    manifest_path: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": bool(self.validation.get("ok")),
            "output_path": self.output_path,
            "document_count": self.document_count,
            "block_count": self.block_count,
            "candidate_count": self.candidate_count,
            "imported_count": self.imported_count,
            "rejected_count": self.rejected_count,
            "node_count": self.node_count,
            "manifest_path": self.manifest_path,
            "validation": self.validation,
        }


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def digest_tokens(tokens: Sequence[str]) -> str:
    """Digest sensível à ordem e às repetições da sequência superficial."""
    digest = hashlib.sha256()
    for token in tokens:
        digest.update(token.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def split_physical_blocks(payload: bytes) -> list[SourceBlock]:
    """Separa blocos físicos sem depender de balanço de parênteses.

    O corpus usa linhas em branco como fronteira de registro. Diferentemente
    de uma varredura de S-expressões, esse método consegue registrar um bloco
    defeituoso e seguir para o próximo, como ocorre em ``va_013_psd.txt``.
    """
    blocks: list[SourceBlock] = []
    cursor = 0

    def append_segment(segment: bytes, segment_start: int) -> None:
        # A checagem usa uma cópia normalizada, mas o BLOB persistido mantém
        # cada byte do registro físico (inclusive espaços significativos).
        if not segment.strip(TRIM_BYTES):
            return
        blocks.append(
            SourceBlock(
                ordinal=len(blocks) + 1,
                start_byte=segment_start,
                end_byte=segment_start + len(segment),
                raw_bytes=segment,
            )
        )

    for match in PHYSICAL_SEPARATOR_RE.finditer(payload):
        append_segment(payload[cursor : match.start()], cursor)
        cursor = match.end()
    append_segment(payload[cursor:], cursor)
    return blocks


def split_dos_trailer(payload: bytes) -> tuple[bytes, bytes]:
    """Separa o marcador DOS ``0x1A`` permitido somente no fim do arquivo.

    O byte continua registrado no documento e integra o hash do arquivo; ele
    apenas não é entregue ao parser da última árvore física.
    """
    return split_terminal_dos_trailer(payload)


def _tokenize(expression: str) -> list[str]:
    tokens: list[str] = []
    index = 0
    while index < len(expression):
        character = expression[index]
        if character.isspace():
            index += 1
            continue
        if character in "()":
            tokens.append(character)
            index += 1
            continue
        start = index
        while index < len(expression) and not expression[index].isspace() and expression[index] not in "()":
            index += 1
        tokens.append(expression[start:index])
    return tokens


def parse_sexpression(expression: str) -> list[Any]:
    """Analisa uma S-expressão sem NLTK e sem transformar rótulos da fonte."""
    tokens = _tokenize(expression)
    if not tokens:
        raise PsdParseError("EXPRESSAO_VAZIA", "o bloco não contém tokens")
    position = 0

    def parse_list() -> list[Any]:
        nonlocal position
        if position >= len(tokens) or tokens[position] != "(":
            raise PsdParseError("ABERTURA_ESPERADA", "esperado '(' para iniciar uma lista")
        position += 1
        result: list[Any] = []
        while position < len(tokens):
            token = tokens[position]
            if token == "(":
                result.append(parse_list())
            elif token == ")":
                position += 1
                return result
            else:
                result.append(token)
                position += 1
        raise PsdParseError("FECHAMENTO_AUSENTE", "uma lista foi aberta sem ')' correspondente")

    if tokens[position] != "(":
        raise PsdParseError("EXPRESSAO_SEM_LISTA", "o bloco não começa por uma S-expressão")
    parsed = parse_list()
    if position != len(tokens):
        raise PsdParseError("TOKENS_APOS_EXPRESSAO", "há conteúdo após a primeira S-expressão")
    return parsed


def _is_external_metadata(value: Any) -> bool:
    """Reconhece metadados externos que não pertencem à árvore sintática."""
    return bool(
        isinstance(value, list)
        and value
        and isinstance(value[0], str)
        and value[0] in {"ID", "STYPE"}
    )


def _unwrap_tree(value: Any) -> list[Any]:
    """Remove apenas wrappers sem rótulo e metadados ``(ID ...)`` externos."""
    current = value
    while True:
        if not isinstance(current, list) or not current:
            raise PsdParseError("WRAPPER_INVALIDO", "a árvore não contém um nó rotulado")
        if isinstance(current[0], str):
            if current[0] == "ID":
                raise PsdParseError("SOMENTE_METADADO", "o bloco contém somente metadados ID")
            return current

        payload = [item for item in current if not _is_external_metadata(item)]
        nested = [item for item in payload if isinstance(item, list)]
        atoms = [item for item in payload if isinstance(item, str)]
        if len(nested) > 1:
            raise PsdParseError(
                "MULTIPLAS_RAIZES",
                "o registro físico contém mais de uma árvore após remover metadados externos",
            )
        if atoms or len(nested) != 1:
            raise PsdParseError(
                "WRAPPER_AMBIGUO",
                "o wrapper externo não contém exatamente uma árvore e metadados opcionais",
            )
        current = nested[0]


def _node_from_expression(value: list[Any]) -> PsdNode:
    if not value or not isinstance(value[0], str):
        raise PsdParseError("ROTULO_AUSENTE", "um nó não possui rótulo atômico")
    label = value[0]
    raw_children = value[1:]
    if not raw_children:
        raise PsdParseError("NO_SEM_FILHOS", f"o nó '{label}' não possui filhos")

    atom_children = [child for child in raw_children if isinstance(child, str)]
    list_children = [child for child in raw_children if isinstance(child, list)]
    if atom_children and list_children:
        raise PsdParseError(
            "ESTRUTURA_MISTA",
            f"o nó '{label}' mistura tokens e subárvores no mesmo nível",
        )
    if atom_children:
        if len(atom_children) != 1:
            raise PsdParseError(
                "PRETERMINAL_MULTIPLO",
                f"o nó pré-terminal '{label}' possui {len(atom_children)} tokens",
            )
        return PsdNode(label=label, children=(atom_children[0],))
    return PsdNode(
        label=label,
        children=tuple(_node_from_expression(child) for child in list_children),
    )


def parse_psd_tree(expression: str) -> PsdNode:
    """Converte o bloco bruto em AST própria ou lança ``PsdParseError``."""
    return _node_from_expression(_unwrap_tree(parse_sexpression(expression)))


def extract_external_id(expression: str) -> str | None:
    match = ID_RECORD_RE.search(expression)
    return match.group(1).strip() if match else None


def tree_leaves(node: PsdNode) -> list[str]:
    leaves: list[str] = []
    for child in node.children:
        if isinstance(child, str):
            leaves.append(child)
        else:
            leaves.extend(tree_leaves(child))
    return leaves


def serialize_tree(node: PsdNode) -> str:
    children = [child if isinstance(child, str) else serialize_tree(child) for child in node.children]
    return f"({node.label} {' '.join(children)})"


def split_label(label: str) -> tuple[str, str | None]:
    parts = label.split("-", 1)
    return parts[0], parts[1] if len(parts) == 2 else None


def classify_structure(root_label: str) -> str:
    if root_label == "CODE":
        return "METADADO"
    if root_label.startswith(("IP", "CP")):
        return "ORACAO"
    if root_label.startswith("FRAG"):
        return "FRAGMENTO"
    return "CONSTITUINTE"


def number_tree(node: PsdNode) -> tuple[NumberedNode, int, int]:
    """Produz preordem, nested-set e ordem de folhas de modo determinístico."""
    state = {"preorder": 0, "boundary": 0, "leaf": 0, "nodes": 0}

    def visit(current: PsdNode, depth: int) -> NumberedNode:
        state["preorder"] += 1
        state["boundary"] += 1
        state["nodes"] += 1
        preorder = state["preorder"]
        lft = state["boundary"]
        if len(current.children) == 1 and isinstance(current.children[0], str):
            state["leaf"] += 1
            numbered_children: tuple[NumberedNode, ...] = ()
            leaf_ordinal: int | None = state["leaf"]
        else:
            numbered_children = tuple(
                visit(child, depth + 1)
                for child in current.children
                if isinstance(child, PsdNode)
            )
            leaf_ordinal = None
        state["boundary"] += 1
        return NumberedNode(
            node=current,
            preorder=preorder,
            lft=lft,
            rgt=state["boundary"],
            depth=depth,
            leaf_ordinal=leaf_ordinal,
            children=numbered_children,
        )

    root = visit(node, 0)
    return root, int(state["nodes"]), int(state["leaf"])


def _create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE recon_meta (
            chave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
        );

        CREATE TABLE recon_documentos (
            documento_id INTEGER PRIMARY KEY,
            caminho_relativo TEXT NOT NULL UNIQUE,
            sha256 TEXT NOT NULL CHECK (length(sha256) = 64),
            tamanho_bytes INTEGER NOT NULL CHECK (tamanho_bytes >= 0),
            quantidade_blocos INTEGER NOT NULL DEFAULT 0 CHECK (quantidade_blocos >= 0),
            quantidade_candidatos_historicos_fisicos INTEGER NOT NULL DEFAULT 0 CHECK (quantidade_candidatos_historicos_fisicos >= 0),
            versao_segmentador TEXT NOT NULL,
            sha256_identidade_blocos_fisicos TEXT NOT NULL CHECK (length(sha256_identidade_blocos_fisicos) = 64),
            sha256_identidade_candidatos_fisicos TEXT NOT NULL CHECK (length(sha256_identidade_candidatos_fisicos) = 64),
            trailer_dos BLOB NOT NULL DEFAULT X'',
            metadados_json TEXT NOT NULL DEFAULT '{}'
        );

        CREATE TABLE recon_blocos_origem (
            bloco_id INTEGER PRIMARY KEY,
            documento_id INTEGER NOT NULL REFERENCES recon_documentos(documento_id),
            ordinal_bloco INTEGER NOT NULL CHECK (ordinal_bloco > 0),
            inicio_byte INTEGER NOT NULL CHECK (inicio_byte >= 0),
            fim_byte INTEGER NOT NULL CHECK (fim_byte > inicio_byte),
            eh_candidato_historico_fisico INTEGER NOT NULL CHECK (eh_candidato_historico_fisico IN (0, 1)),
            ordinal_candidato INTEGER,
            id_externo TEXT,
            conteudo_bruto BLOB NOT NULL,
            sha256_bloco TEXT NOT NULL CHECK (length(sha256_bloco) = 64),
            UNIQUE (documento_id, ordinal_bloco),
            UNIQUE (documento_id, ordinal_candidato),
            CHECK (
                (eh_candidato_historico_fisico = 1 AND ordinal_candidato IS NOT NULL)
                OR
                (eh_candidato_historico_fisico = 0 AND ordinal_candidato IS NULL)
            )
        );

        CREATE TABLE recon_ledger_importacao (
            bloco_id INTEGER PRIMARY KEY REFERENCES recon_blocos_origem(bloco_id),
            resultado TEXT NOT NULL CHECK (resultado IN ('IMPORTADO', 'REJEITADO')),
            codigo_motivo TEXT,
            detalhe_motivo TEXT,
            versao_parser TEXT NOT NULL,
            rotulo_raiz TEXT,
            classe_estrutura TEXT NOT NULL,
            sha256_arvore_normalizada TEXT,
            sha256_folhas TEXT,
            quantidade_folhas INTEGER NOT NULL DEFAULT 0 CHECK (quantidade_folhas >= 0),
            registrado_em_utc TEXT NOT NULL,
            CHECK (
                (resultado = 'IMPORTADO' AND codigo_motivo IS NULL AND sha256_arvore_normalizada IS NOT NULL)
                OR
                (resultado = 'REJEITADO' AND codigo_motivo IS NOT NULL AND sha256_arvore_normalizada IS NULL)
            )
        );

        CREATE TABLE recon_sentencas (
            sentenca_id INTEGER PRIMARY KEY,
            bloco_id INTEGER NOT NULL UNIQUE REFERENCES recon_blocos_origem(bloco_id),
            documento_id INTEGER NOT NULL REFERENCES recon_documentos(documento_id),
            caminho_relativo TEXT NOT NULL,
            id_externo TEXT,
            rotulo_raiz TEXT NOT NULL,
            classe_estrutura TEXT NOT NULL,
            arvore_normalizada TEXT NOT NULL,
            texto_superficial TEXT NOT NULL,
            sha256_folhas TEXT NOT NULL CHECK (length(sha256_folhas) = 64),
            quantidade_folhas INTEGER NOT NULL CHECK (quantidade_folhas >= 0),
            quantidade_nos INTEGER NOT NULL CHECK (quantidade_nos > 0)
        );

        CREATE TABLE recon_nos (
            no_id INTEGER PRIMARY KEY,
            sentenca_id INTEGER NOT NULL REFERENCES recon_sentencas(sentenca_id),
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
            UNIQUE (sentenca_id, no_id),
            UNIQUE (sentenca_id, preordem),
            UNIQUE (sentenca_id, lft),
            UNIQUE (sentenca_id, rgt),
            UNIQUE (sentenca_id, ordem_folha),
            CHECK (
                (eh_folha = 1 AND token_origem IS NOT NULL AND ordem_folha IS NOT NULL)
                OR
                (eh_folha = 0 AND token_origem IS NULL AND ordem_folha IS NULL)
            )
        );

        CREATE TABLE recon_relacoes (
            sentenca_id INTEGER NOT NULL,
            pai_no_id INTEGER NOT NULL,
            filho_no_id INTEGER NOT NULL,
            ordem_irmao INTEGER NOT NULL CHECK (ordem_irmao >= 0),
            tipo TEXT NOT NULL DEFAULT 'DOMINANCIA_IMEDIATA'
                CHECK (tipo = 'DOMINANCIA_IMEDIATA'),
            PRIMARY KEY (sentenca_id, pai_no_id, filho_no_id),
            UNIQUE (sentenca_id, filho_no_id),
            UNIQUE (sentenca_id, pai_no_id, ordem_irmao),
            FOREIGN KEY (sentenca_id, pai_no_id)
                REFERENCES recon_nos(sentenca_id, no_id),
            FOREIGN KEY (sentenca_id, filho_no_id)
                REFERENCES recon_nos(sentenca_id, no_id),
            CHECK (pai_no_id <> filho_no_id)
        );

        CREATE INDEX idx_recon_blocos_documento_ordem
            ON recon_blocos_origem(documento_id, ordinal_bloco);
        CREATE INDEX idx_recon_ledger_resultado
            ON recon_ledger_importacao(resultado, codigo_motivo);
        CREATE INDEX idx_recon_nos_rotulo
            ON recon_nos(rotulo_origem);
        CREATE INDEX idx_recon_nos_base_funcao
            ON recon_nos(rotulo_base, funcao);
        CREATE INDEX idx_recon_nos_token
            ON recon_nos(token_origem);
        CREATE INDEX idx_recon_nos_intervalo
            ON recon_nos(sentenca_id, lft, rgt);
        CREATE INDEX idx_recon_relacoes_pai
            ON recon_relacoes(sentenca_id, pai_no_id);
        """
    )


def _put_meta(connection: sqlite3.Connection, key: str, value: str) -> None:
    connection.execute(
        "INSERT INTO recon_meta(chave, valor) VALUES (?, ?) "
        "ON CONFLICT(chave) DO UPDATE SET valor=excluded.valor",
        (key, value),
    )


def _persist_numbered_tree(
    cursor: sqlite3.Cursor,
    numbered: NumberedNode,
    sentence_id: int,
    parent_id: int | None = None,
    sibling_order: int = 0,
) -> int:
    label_base, function = split_label(numbered.node.label)
    is_leaf = int(numbered.leaf_ordinal is not None)
    token = numbered.node.children[0] if is_leaf else None
    cursor.execute(
        """
        INSERT INTO recon_nos(
            sentenca_id, preordem, lft, rgt, profundidade, rotulo_origem,
            rotulo_base, funcao, eh_folha, ordem_folha, token_origem
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            sentence_id,
            numbered.preorder,
            numbered.lft,
            numbered.rgt,
            numbered.depth,
            numbered.node.label,
            label_base,
            function,
            is_leaf,
            numbered.leaf_ordinal,
            token,
        ),
    )
    node_id = int(cursor.lastrowid)
    if parent_id is not None:
        cursor.execute(
            """
            INSERT INTO recon_relacoes(sentenca_id, pai_no_id, filho_no_id, ordem_irmao)
            VALUES (?, ?, ?, ?)
            """,
            (sentence_id, parent_id, node_id, sibling_order),
        )
    for child_order, child in enumerate(numbered.children):
        _persist_numbered_tree(cursor, child, sentence_id, node_id, child_order)
    return node_id


def _record_rejection(
    cursor: sqlite3.Cursor,
    block_id: int,
    code: str,
    detail: str,
    root_label: str | None = None,
    structure_class: str = "NAO_PARSEADO",
    leaves: Sequence[str] = (),
) -> None:
    cursor.execute(
        """
        INSERT INTO recon_ledger_importacao(
            bloco_id, resultado, codigo_motivo, detalhe_motivo, versao_parser,
            rotulo_raiz, classe_estrutura, sha256_arvore_normalizada,
            sha256_folhas, quantidade_folhas, registrado_em_utc
        ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?)
        """,
        (
            block_id,
            STATUS_REJECTED,
            code,
            detail,
            PARSER_VERSION,
            root_label,
            structure_class,
            digest_tokens(leaves) if leaves else None,
            len(leaves),
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
        ),
    )


def _record_import(
    cursor: sqlite3.Cursor,
    block_id: int,
    document_id: int,
    relative_path: str,
    external_id: str | None,
    tree: PsdNode,
) -> int:
    leaves = tree_leaves(tree)
    normalized = serialize_tree(tree)
    normalized_digest = sha256_bytes(normalized.encode("utf-8"))
    leaves_digest = digest_tokens(leaves)
    structure_class = classify_structure(tree.label)
    numbered, node_count, leaf_count = number_tree(tree)
    if leaf_count != len(leaves):
        raise ReconstructionError("inconsistência interna: número de folhas divergente")

    cursor.execute(
        """
        INSERT INTO recon_ledger_importacao(
            bloco_id, resultado, codigo_motivo, detalhe_motivo, versao_parser,
            rotulo_raiz, classe_estrutura, sha256_arvore_normalizada,
            sha256_folhas, quantidade_folhas, registrado_em_utc
        ) VALUES (?, ?, NULL, NULL, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            block_id,
            STATUS_IMPORTED,
            PARSER_VERSION,
            tree.label,
            structure_class,
            normalized_digest,
            leaves_digest,
            len(leaves),
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
        ),
    )
    cursor.execute(
        """
        INSERT INTO recon_sentencas(
            bloco_id, documento_id, caminho_relativo, id_externo, rotulo_raiz,
            classe_estrutura, arvore_normalizada, texto_superficial,
            sha256_folhas, quantidade_folhas, quantidade_nos
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            block_id,
            document_id,
            relative_path,
            external_id,
            tree.label,
            structure_class,
            normalized,
            " ".join(leaves),
            leaves_digest,
            len(leaves),
            node_count,
        ),
    )
    sentence_id = int(cursor.lastrowid)
    _persist_numbered_tree(cursor, numbered, sentence_id)
    return node_count


def validate_sources_against_manifest(source_dir: Path, manifest_path: Path) -> dict[str, Any]:
    """Confere fonte congelada e a identidade física exigida pelo Marco 2."""
    manifest = load_manifest(manifest_path)
    expected_records = manifest.get("canonical_sources", {}).get("files", [])
    expected_by_name = {Path(str(record["path"])).name: record for record in expected_records}
    actual_paths = sorted(source_dir.glob("*_psd.txt"))
    actual_by_name = {path.name: path for path in actual_paths}
    errors: list[str] = []
    source_records: dict[str, dict[str, Any]] = {}

    if set(expected_by_name) != set(actual_by_name):
        missing = sorted(set(expected_by_name) - set(actual_by_name))
        unexpected = sorted(set(actual_by_name) - set(expected_by_name))
        if missing:
            errors.append(f"fontes ausentes em relação ao manifesto: {', '.join(missing)}")
        if unexpected:
            errors.append(f"fontes não previstas no manifesto: {', '.join(unexpected)}")

    for name in sorted(set(expected_by_name) & set(actual_by_name)):
        expected = expected_by_name[name]
        path = actual_by_name[name]
        raw_content = path.read_bytes()
        if path.stat().st_size != expected.get("bytes"):
            errors.append(f"tamanho divergente da fonte: {name}")
        if sha256_file(path) != expected.get("sha256"):
            errors.append(f"SHA-256 divergente da fonte: {name}")
        text = raw_content.decode("utf-8", errors="replace")
        actual_fingerprint = candidate_tree_fingerprint(text)
        expected_fingerprint = expected.get("parse_fingerprint", {})
        for field in ("candidate_tree_count", "candidate_identity_sha256"):
            if actual_fingerprint.get(field) != expected_fingerprint.get(field):
                errors.append(f"fingerprint histórico divergente em {name}: {field}")

        expected_physical = expected.get("physical_fingerprint")
        if not isinstance(expected_physical, dict):
            errors.append(
                f"manifesto não contém fingerprint físico Marco 2 para a fonte: {name}"
            )
        else:
            canonical_path = str(expected["path"])
            actual_physical = physical_psd_fingerprint(raw_content, canonical_path)
            for field in (
                "segmentation_version",
                "physical_block_count",
                "historical_candidate_count",
                "terminal_dos_trailer_bytes",
                "physical_block_identity_sha256",
                "historical_candidate_identity_sha256",
            ):
                if actual_physical.get(field) != expected_physical.get(field):
                    errors.append(f"fingerprint físico Marco 2 divergente em {name}: {field}")
        source_records[name] = expected

    return {
        "ok": not errors,
        "errors": errors,
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "snapshot_id": manifest.get("snapshot_id"),
        "source_records": source_records,
    }


def _read_counts(connection: sqlite3.Connection) -> dict[str, int]:
    return {
        "document_count": int(connection.execute("SELECT COUNT(*) FROM recon_documentos").fetchone()[0]),
        "block_count": int(connection.execute("SELECT COUNT(*) FROM recon_blocos_origem").fetchone()[0]),
        "candidate_count": int(
            connection.execute(
                "SELECT COUNT(*) FROM recon_blocos_origem WHERE eh_candidato_historico_fisico=1"
            ).fetchone()[0]
        ),
        "imported_count": int(
            connection.execute(
                "SELECT COUNT(*) FROM recon_ledger_importacao WHERE resultado=?", (STATUS_IMPORTED,)
            ).fetchone()[0]
        ),
        "rejected_count": int(
            connection.execute(
                "SELECT COUNT(*) FROM recon_ledger_importacao WHERE resultado=?", (STATUS_REJECTED,)
            ).fetchone()[0]
        ),
        "node_count": int(connection.execute("SELECT COUNT(*) FROM recon_nos").fetchone()[0]),
    }


def _empty_counts() -> dict[str, int]:
    """Formato estável de contagens, inclusive quando a abertura falha."""
    return {
        "document_count": 0,
        "block_count": 0,
        "candidate_count": 0,
        "imported_count": 0,
        "rejected_count": 0,
        "node_count": 0,
    }


def validate_reconstruction_database(
    database_path: Path, manifest_path: Path | None = None
) -> dict[str, Any]:
    """Executa invariantes de proveniência, árvore e integridade SQLite.

    Quando recebe um manifesto Marco 2, a validação também ancora o banco na
    identidade externa das fontes. A verificação interna continua útil para
    fixtures, mas não substitui essa âncora em uma reconstrução publicável.
    """
    errors: list[str] = []
    counts = _empty_counts()
    connection: sqlite3.Connection | None = None
    database_path = database_path.resolve()
    expected_manifest_records: dict[str, dict[str, Any]] | None = None
    manifest_sha256: str | None = None
    manifest_snapshot_id: str | None = None
    if manifest_path is not None:
        try:
            manifest_path = manifest_path.resolve()
            manifest = load_manifest(manifest_path)
            expected_manifest_records = {
                str(record["path"]): record
                for record in manifest.get("canonical_sources", {}).get("files", [])
            }
            manifest_sha256 = sha256_file(manifest_path)
            manifest_snapshot_id = str(manifest.get("snapshot_id") or "")
            if not expected_manifest_records:
                errors.append("manifesto não contém fontes canônicas para ancorar o banco")
        except (OSError, ValueError, json.JSONDecodeError) as error:
            errors.append(f"não foi possível carregar manifesto Marco 2: {error}")
    if not database_path.is_file():
        return {
            "ok": False,
            "errors": [f"banco reconstruído não encontrado: {database_path}"],
            "counts": counts,
        }
    try:
        connection = sqlite3.connect(f"{database_path.as_uri()}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        integrity = [str(row[0]) for row in connection.execute("PRAGMA integrity_check")]
        if integrity != ["ok"]:
            errors.append(f"integrity_check falhou: {integrity}")
        foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
        if foreign_keys:
            errors.append(f"foreign_key_check encontrou {len(foreign_keys)} erro(s)")

        counts = _read_counts(connection)
        if expected_manifest_records is not None:
            documents = list(
                connection.execute(
                    """
                    SELECT documento_id, caminho_relativo, sha256, tamanho_bytes,
                           quantidade_blocos, quantidade_candidatos_historicos_fisicos,
                           versao_segmentador, sha256_identidade_blocos_fisicos,
                           sha256_identidade_candidatos_fisicos, trailer_dos
                    FROM recon_documentos
                    """
                )
            )
            documents_by_path = {str(document["caminho_relativo"]): document for document in documents}
            expected_paths = set(expected_manifest_records)
            database_paths = set(documents_by_path)
            if expected_paths != database_paths:
                missing = sorted(expected_paths - database_paths)
                unexpected = sorted(database_paths - expected_paths)
                if missing:
                    errors.append("documento(s) ausente(s) em relação ao manifesto: " + ", ".join(missing))
                if unexpected:
                    errors.append("documento(s) inesperado(s) no banco: " + ", ".join(unexpected))
            for relative_path in sorted(expected_paths & database_paths):
                document = documents_by_path[relative_path]
                expected = expected_manifest_records[relative_path]
                expected_physical = expected.get("physical_fingerprint")
                if not isinstance(expected_physical, dict):
                    errors.append(f"manifesto sem fingerprint físico Marco 2: {relative_path}")
                    continue
                expected_values: dict[str, Any] = {
                    "sha256": expected.get("sha256"),
                    "tamanho_bytes": expected.get("bytes"),
                    "quantidade_blocos": expected_physical.get("physical_block_count"),
                    "quantidade_candidatos_historicos_fisicos": expected_physical.get(
                        "historical_candidate_count"
                    ),
                    "versao_segmentador": expected_physical.get("segmentation_version"),
                    "sha256_identidade_blocos_fisicos": expected_physical.get(
                        "physical_block_identity_sha256"
                    ),
                    "sha256_identidade_candidatos_fisicos": expected_physical.get(
                        "historical_candidate_identity_sha256"
                    ),
                }
                for field, expected_value in expected_values.items():
                    if document[field] != expected_value:
                        errors.append(
                            f"documento divergente do manifesto Marco 2: {relative_path} ({field})"
                        )
                if len(bytes(document["trailer_dos"])) != int(
                    expected_physical.get("terminal_dos_trailer_bytes", -1)
                ):
                    errors.append(
                        f"documento divergente do manifesto Marco 2: {relative_path} (trailer_dos)"
                    )

            stored_manifest_hash = connection.execute(
                "SELECT valor FROM recon_meta WHERE chave='source_manifest_sha256'"
            ).fetchone()
            if stored_manifest_hash is None or stored_manifest_hash["valor"] != manifest_sha256:
                errors.append("hash do manifesto Marco 2 divergente no banco")
            stored_snapshot_id = connection.execute(
                "SELECT valor FROM recon_meta WHERE chave='source_manifest_snapshot_id'"
            ).fetchone()
            if stored_snapshot_id is None or stored_snapshot_id["valor"] != manifest_snapshot_id:
                errors.append("snapshot_id do manifesto Marco 2 divergente no banco")

        ledger_count = int(connection.execute("SELECT COUNT(*) FROM recon_ledger_importacao").fetchone()[0])
        if ledger_count != counts["candidate_count"]:
            errors.append("cada candidato histórico deve possuir exatamente uma decisão no ledger")
        if counts["imported_count"] + counts["rejected_count"] != counts["candidate_count"]:
            errors.append("importados + rejeitados não cobre todos os candidatos históricos")
        ledger_for_non_candidates = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM recon_ledger_importacao ledger
                JOIN recon_blocos_origem block ON block.bloco_id = ledger.bloco_id
                WHERE block.eh_candidato_historico_fisico = 0
                """
            ).fetchone()[0]
        )
        if ledger_for_non_candidates:
            errors.append("há decisão de parser vinculada a bloco fora do escopo histórico")

        raw_hash_mismatches = 0
        for block in connection.execute(
            "SELECT conteudo_bruto, sha256_bloco FROM recon_blocos_origem"
        ):
            if sha256_bytes(bytes(block["conteudo_bruto"])) != str(block["sha256_bloco"]):
                raw_hash_mismatches += 1
        if raw_hash_mismatches:
            errors.append(
                f"há {raw_hash_mismatches} bloco(s) cujo SHA-256 não confere com o conteúdo bruto"
            )

        physical_fingerprint_mismatches = 0
        physical_segmentation_version_mismatches = 0
        for document in connection.execute(
            """
            SELECT documento_id, caminho_relativo, versao_segmentador,
                   sha256_identidade_blocos_fisicos, sha256_identidade_candidatos_fisicos
            FROM recon_documentos
            """
        ):
            records = [
                (int(row["ordinal_bloco"]), row["ordinal_candidato"], str(row["sha256_bloco"]))
                for row in connection.execute(
                    """
                    SELECT ordinal_bloco, ordinal_candidato, sha256_bloco
                    FROM recon_blocos_origem
                    WHERE documento_id=?
                    ORDER BY ordinal_bloco
                    """,
                    (document["documento_id"],),
                )
            ]
            fingerprint = physical_record_fingerprint(str(document["caminho_relativo"]), records)
            if document["versao_segmentador"] != PHYSICAL_SEGMENTATION_VERSION:
                physical_segmentation_version_mismatches += 1
            if (
                fingerprint["physical_block_identity_sha256"]
                != document["sha256_identidade_blocos_fisicos"]
                or fingerprint["historical_candidate_identity_sha256"]
                != document["sha256_identidade_candidatos_fisicos"]
            ):
                physical_fingerprint_mismatches += 1
        if physical_segmentation_version_mismatches:
            errors.append(
                f"há {physical_segmentation_version_mismatches} documento(s) com versão de segmentador divergente"
            )
        if physical_fingerprint_mismatches:
            errors.append(
                f"há {physical_fingerprint_mismatches} documento(s) com fingerprint físico divergente"
            )

        missing_sentences = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM recon_ledger_importacao ledger
                LEFT JOIN recon_sentencas sentence ON sentence.bloco_id = ledger.bloco_id
                WHERE ledger.resultado = ? AND sentence.sentenca_id IS NULL
                """,
                (STATUS_IMPORTED,),
            ).fetchone()[0]
        )
        rejected_sentences = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM recon_ledger_importacao ledger
                JOIN recon_sentencas sentence ON sentence.bloco_id = ledger.bloco_id
                WHERE ledger.resultado = ?
                """,
                (STATUS_REJECTED,),
            ).fetchone()[0]
        )
        if missing_sentences:
            errors.append(f"há {missing_sentences} bloco(s) importado(s) sem sentença")
        if rejected_sentences:
            errors.append(f"há {rejected_sentences} bloco(s) rejeitado(s) com sentença persistida")

        sentences_without_import_ledger = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM recon_sentencas sentence
                LEFT JOIN recon_ledger_importacao ledger ON ledger.bloco_id = sentence.bloco_id
                WHERE ledger.bloco_id IS NULL OR ledger.resultado != ?
                """,
                (STATUS_IMPORTED,),
            ).fetchone()[0]
        )
        if sentences_without_import_ledger:
            errors.append(
                f"há {sentences_without_import_ledger} sentença(s) sem decisão IMPORTADO no ledger"
            )

        sentence_provenance_mismatches = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM recon_sentencas sentence
                JOIN recon_blocos_origem block ON block.bloco_id = sentence.bloco_id
                JOIN recon_documentos document ON document.documento_id = block.documento_id
                JOIN recon_ledger_importacao ledger ON ledger.bloco_id = sentence.bloco_id
                WHERE sentence.documento_id != block.documento_id
                   OR sentence.caminho_relativo != document.caminho_relativo
                   OR sentence.id_externo IS NOT block.id_externo
                   OR sentence.rotulo_raiz != ledger.rotulo_raiz
                   OR sentence.classe_estrutura != ledger.classe_estrutura
                """
            ).fetchone()[0]
        )
        if sentence_provenance_mismatches:
            errors.append(
                f"há {sentence_provenance_mismatches} sentença(s) com proveniência divergente do bloco/ledger"
            )

        document_mismatches = connection.execute(
            """
            SELECT document.documento_id
            FROM recon_documentos document
            LEFT JOIN recon_blocos_origem block ON block.documento_id = document.documento_id
            GROUP BY document.documento_id
            HAVING document.quantidade_blocos != COUNT(block.bloco_id)
            """
        ).fetchall()
        if document_mismatches:
            errors.append("contagem de blocos divergente em documento(s)")

        candidate_document_mismatches = connection.execute(
            """
            SELECT document.documento_id
            FROM recon_documentos document
            LEFT JOIN recon_blocos_origem block ON block.documento_id = document.documento_id
            GROUP BY document.documento_id
            HAVING document.quantidade_candidatos_historicos_fisicos
                 != COALESCE(SUM(block.eh_candidato_historico_fisico), 0)
            """
        ).fetchall()
        if candidate_document_mismatches:
            errors.append("contagem de marcadores históricos divergente em documento(s)")

        meta_expectations = {
            "quantidade_blocos": counts["block_count"],
            "quantidade_candidatos_historicos_fisicos": counts["candidate_count"],
            "quantidade_importados": counts["imported_count"],
            "quantidade_rejeitados": counts["rejected_count"],
        }
        for key, expected in meta_expectations.items():
            metadata = connection.execute(
                "SELECT valor FROM recon_meta WHERE chave=?", (key,)
            ).fetchone()
            if metadata is None or metadata["valor"] != str(expected):
                errors.append(f"metadado agregado divergente: {key}")

        bad_nodes = int(
            connection.execute(
                """
                SELECT COUNT(*) FROM recon_nos
                WHERE (eh_folha = 1 AND (token_origem IS NULL OR ordem_folha IS NULL))
                   OR (eh_folha = 0 AND (token_origem IS NOT NULL OR ordem_folha IS NOT NULL))
                """
            ).fetchone()[0]
        )
        if bad_nodes:
            errors.append(f"há {bad_nodes} nó(s) com estado de folha inválido")

        bad_relations = int(
            connection.execute(
                """
                SELECT COUNT(*)
                FROM recon_relacoes relation
                JOIN recon_nos parent ON parent.no_id = relation.pai_no_id
                JOIN recon_nos child ON child.no_id = relation.filho_no_id
                WHERE parent.sentenca_id != relation.sentenca_id
                   OR child.sentenca_id != relation.sentenca_id
                   OR child.profundidade != parent.profundidade + 1
                   OR child.lft <= parent.lft
                   OR child.rgt >= parent.rgt
                """
            ).fetchone()[0]
        )
        if bad_relations:
            errors.append(f"há {bad_relations} relação(ões) de árvore inválida(s)")

        normalized_tree_hash_mismatches = 0
        ledger_leaf_mismatches = 0
        normalized_tree_content_mismatches = 0
        normalized_tree_parse_failures = 0
        for sentence in connection.execute(
            """
            SELECT sentence.sentenca_id, sentence.rotulo_raiz, sentence.arvore_normalizada,
                   sentence.sha256_folhas, sentence.quantidade_folhas,
                   ledger.sha256_arvore_normalizada, ledger.sha256_folhas AS sha256_folhas_ledger,
                   ledger.quantidade_folhas AS quantidade_folhas_ledger
            FROM recon_sentencas sentence
            JOIN recon_ledger_importacao ledger ON ledger.bloco_id = sentence.bloco_id
            WHERE ledger.resultado=?
            """,
            (STATUS_IMPORTED,),
        ):
            normalized = str(sentence["arvore_normalizada"])
            if sha256_bytes(normalized.encode("utf-8")) != str(sentence["sha256_arvore_normalizada"]):
                normalized_tree_hash_mismatches += 1
            if (
                sentence["sha256_folhas"] != sentence["sha256_folhas_ledger"]
                or sentence["quantidade_folhas"] != sentence["quantidade_folhas_ledger"]
            ):
                ledger_leaf_mismatches += 1
            try:
                normalized_tree = parse_psd_tree(normalized)
            except PsdParseError:
                normalized_tree_parse_failures += 1
                continue
            if (
                normalized_tree.label != sentence["rotulo_raiz"]
                or digest_tokens(tree_leaves(normalized_tree)) != sentence["sha256_folhas"]
            ):
                normalized_tree_content_mismatches += 1
        if normalized_tree_hash_mismatches:
            errors.append(
                f"há {normalized_tree_hash_mismatches} árvore(s) normalizada(s) com SHA-256 divergente"
            )
        if ledger_leaf_mismatches:
            errors.append(
                f"há {ledger_leaf_mismatches} registro(s) de folhas divergente(s) entre ledger e sentença"
            )
        if normalized_tree_parse_failures:
            errors.append(
                f"há {normalized_tree_parse_failures} árvore(s) normalizada(s) que não podem ser reanalisadas"
            )
        if normalized_tree_content_mismatches:
            errors.append(
                f"há {normalized_tree_content_mismatches} árvore(s) normalizada(s) divergente(s) das folhas/raiz"
            )

        surface_text_mismatches = 0
        for sentence in connection.execute(
            """
            SELECT sentenca_id, quantidade_nos, quantidade_folhas, sha256_folhas, texto_superficial
            FROM recon_sentencas
            """
        ):
            sentence_id = int(sentence["sentenca_id"])
            node_count = int(sentence["quantidade_nos"])
            relation_count = int(
                connection.execute(
                    "SELECT COUNT(*) FROM recon_relacoes WHERE sentenca_id=?", (sentence_id,)
                ).fetchone()[0]
            )
            if relation_count != node_count - 1:
                errors.append(f"sentença {sentence_id}: nós != relações + 1")
            root_count = int(
                connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM recon_nos node
                    LEFT JOIN recon_relacoes relation
                      ON relation.sentenca_id = node.sentenca_id
                     AND relation.filho_no_id = node.no_id
                    WHERE node.sentenca_id=? AND relation.filho_no_id IS NULL
                    """,
                    (sentence_id,),
                ).fetchone()[0]
            )
            if root_count != 1:
                errors.append(f"sentença {sentence_id}: esperado uma raiz, obtidas {root_count}")
            coordinates = [
                int(value)
                for row in connection.execute(
                    "SELECT lft, rgt FROM recon_nos WHERE sentenca_id=?", (sentence_id,)
                )
                for value in (row[0], row[1])
            ]
            if sorted(coordinates) != list(range(1, node_count * 2 + 1)):
                errors.append(f"sentença {sentence_id}: coordenadas nested-set inválidas")
            tokens = [
                str(row[0])
                for row in connection.execute(
                    """
                    SELECT token_origem FROM recon_nos
                    WHERE sentenca_id=? AND eh_folha=1
                    ORDER BY ordem_folha
                    """,
                    (sentence_id,),
                )
            ]
            if len(tokens) != int(sentence["quantidade_folhas"]):
                errors.append(f"sentença {sentence_id}: quantidade de folhas divergente")
            if digest_tokens(tokens) != str(sentence["sha256_folhas"]):
                errors.append(f"sentença {sentence_id}: sequência superficial divergente")
            if " ".join(tokens) != str(sentence["texto_superficial"]):
                surface_text_mismatches += 1
        if surface_text_mismatches:
            errors.append(
                f"há {surface_text_mismatches} texto(s) superficial(is) divergente(s) das folhas"
            )

        for suffix in ("-wal", "-shm"):
            if Path(f"{database_path}{suffix}").exists():
                errors.append(f"artefato SQLite pendente: {database_path.name}{suffix}")
    except (sqlite3.Error, OSError, ValueError) as error:
        errors.append(f"erro SQLite durante validação: {error}")
    finally:
        if connection is not None:
            connection.close()

    return {"ok": not errors, "errors": errors, "counts": counts}


def _assert_safe_output(source_dir: Path, output_path: Path, replace: bool) -> None:
    if output_path.exists() and not replace:
        raise ReconstructionError(
            f"destino já existe: {output_path}. Use --replace somente após revisar o artefato atual."
        )
    try:
        output_path.relative_to(source_dir)
    except ValueError:
        return
    raise ReconstructionError("o banco reconstruído não pode ser criado dentro do diretório de fontes PSD")


def build_reconstruction(
    source_dir: Path,
    output_path: Path,
    manifest_path: Path | None = None,
    *,
    replace: bool = False,
    fail_on_rejections: bool = False,
) -> BuildReport:
    """Constrói e promove um banco novo após validação completa.

    ``manifest_path`` é opcional apenas para fixtures locais. O comando CLI
    sempre fornece o manifesto canônico; construções reais não devem omiti-lo.
    """
    source_dir = source_dir.resolve()
    output_path = output_path.resolve()
    if not source_dir.is_dir():
        raise ReconstructionError(f"diretório de fontes não encontrado: {source_dir}")
    _assert_safe_output(source_dir, output_path, replace)
    source_files = sorted(source_dir.glob("*_psd.txt"))
    if not source_files:
        raise ReconstructionError(f"nenhuma fonte '*_psd.txt' encontrada em {source_dir}")

    manifest_info: dict[str, Any] | None = None
    if manifest_path is not None:
        manifest_path = manifest_path.resolve()
        manifest_info = validate_sources_against_manifest(source_dir, manifest_path)
        if not manifest_info["ok"]:
            raise SourceManifestMismatch("; ".join(manifest_info["errors"]))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    staging_path = output_path.with_name(f".{output_path.name}.{uuid.uuid4().hex}.staging")
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(staging_path)
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("PRAGMA synchronous=FULL")
        _create_schema(connection)
        _put_meta(connection, "schema_version", str(RECONSTRUCTION_SCHEMA_VERSION))
        _put_meta(connection, "parser_version", PARSER_VERSION)
        _put_meta(connection, "built_at_utc", datetime.now(timezone.utc).isoformat(timespec="seconds"))
        _put_meta(connection, "source_directory", str(source_dir))
        _put_meta(connection, "source_manifest_path", str(manifest_path) if manifest_path else "")
        _put_meta(
            connection,
            "source_manifest_sha256",
            str(manifest_info["manifest_sha256"]) if manifest_info else "",
        )
        _put_meta(
            connection,
            "source_manifest_snapshot_id",
            str(manifest_info.get("snapshot_id") or "") if manifest_info else "",
        )

        cursor = connection.cursor()
        total_blocks = total_candidates = total_imported = total_rejected = total_nodes = 0
        for source_path in source_files:
            raw_file = source_path.read_bytes()
            if manifest_info is not None:
                source_record = manifest_info["source_records"][source_path.name]
                relative_path = str(source_record["path"])
            else:
                relative_path = (Path(source_dir.name) / source_path.name).as_posix()
            physical_fingerprint = physical_psd_fingerprint(raw_file, relative_path)
            parser_payload, dos_trailer = split_dos_trailer(raw_file)
            blocks = split_physical_blocks(parser_payload)
            if len(blocks) != int(physical_fingerprint["physical_block_count"]):
                raise ReconstructionError(
                    f"inventário físico interno divergente para {relative_path}"
                )
            metadata = extrair_metadados_arquivo(source_path.name)
            cursor.execute(
                """
                INSERT INTO recon_documentos(
                    caminho_relativo, sha256, tamanho_bytes, versao_segmentador,
                    sha256_identidade_blocos_fisicos, sha256_identidade_candidatos_fisicos,
                    trailer_dos, metadados_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    relative_path,
                    sha256_bytes(raw_file),
                    len(raw_file),
                    str(physical_fingerprint["segmentation_version"]),
                    str(physical_fingerprint["physical_block_identity_sha256"]),
                    str(physical_fingerprint["historical_candidate_identity_sha256"]),
                    dos_trailer,
                    json.dumps(metadata, ensure_ascii=False, sort_keys=True),
                ),
            )
            document_id = int(cursor.lastrowid)
            candidate_ordinal = 0
            for block in blocks:
                marker = int(is_historical_candidate_physical_block(block.raw_bytes))
                if marker:
                    candidate_ordinal += 1
                try:
                    expression = block.raw_bytes.decode("utf-8")
                    external_id = extract_external_id(expression)
                except UnicodeDecodeError:
                    expression = ""
                    external_id = None
                cursor.execute(
                    """
                    INSERT INTO recon_blocos_origem(
                        documento_id, ordinal_bloco, inicio_byte, fim_byte,
                        eh_candidato_historico_fisico, ordinal_candidato, id_externo,
                        conteudo_bruto, sha256_bloco
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        document_id,
                        block.ordinal,
                        block.start_byte,
                        block.end_byte,
                        marker,
                        candidate_ordinal if marker else None,
                        external_id,
                        block.raw_bytes,
                        sha256_bytes(block.raw_bytes),
                    ),
                )
                block_id = int(cursor.lastrowid)
                total_blocks += 1
                if not marker:
                    # Unidades CODE e demais registros continuam preservados
                    # em recon_blocos_origem, mas não pertencem ao conjunto
                    # histórico de sentenças a ser parseado nesta etapa.
                    continue
                total_candidates += 1
                try:
                    if not expression:
                        raise PsdParseError("UTF8_INVALIDO", "o bloco não é UTF-8 válido")
                    tree = parse_psd_tree(expression)
                    total_nodes += _record_import(
                        cursor,
                        block_id,
                        document_id,
                        relative_path,
                        external_id,
                        tree,
                    )
                    total_imported += 1
                except PsdParseError as error:
                    _record_rejection(cursor, block_id, error.code, error.detail)
                    total_rejected += 1
            if candidate_ordinal != int(physical_fingerprint["historical_candidate_count"]):
                raise ReconstructionError(
                    f"contagem de candidatos físicos divergente para {relative_path}"
                )
            cursor.execute(
                """
                UPDATE recon_documentos
                SET quantidade_blocos=?, quantidade_candidatos_historicos_fisicos=?
                WHERE documento_id=?
                """,
                (len(blocks), candidate_ordinal, document_id),
            )

        _put_meta(connection, "quantidade_blocos", str(total_blocks))
        _put_meta(connection, "quantidade_candidatos_historicos_fisicos", str(total_candidates))
        _put_meta(connection, "quantidade_importados", str(total_imported))
        _put_meta(connection, "quantidade_rejeitados", str(total_rejected))
        connection.commit()
        connection.close()
        connection = None

        validation = validate_reconstruction_database(staging_path, manifest_path)
        if not validation["ok"]:
            raise ReconstructionError("validação do staging falhou: " + "; ".join(validation["errors"]))
        if fail_on_rejections and total_rejected:
            raise BuildRejectedError(
                f"a política fail_on_rejections bloqueou {total_rejected} bloco(s) rejeitado(s)"
            )
        os.replace(staging_path, output_path)
        counts = validation["counts"]
        return BuildReport(
            output_path=str(output_path),
            document_count=int(counts["document_count"]),
            block_count=int(counts["block_count"]),
            candidate_count=int(counts["candidate_count"]),
            imported_count=int(counts["imported_count"]),
            rejected_count=int(counts["rejected_count"]),
            node_count=int(counts["node_count"]),
            validation=validation,
            manifest_path=str(manifest_path) if manifest_path else None,
        )
    finally:
        if connection is not None:
            connection.close()
        if staging_path.exists():
            staging_path.unlink()


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Importa fontes PSD em um banco novo com ledger de proveniência por bloco."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser("build", help="constrói um banco novo por staging atômico")
    build_parser.add_argument(
        "--source-dir",
        default=str(PROJECT_ROOT / "corpus_data"),
        help="diretório que contém os PSD canônicos",
    )
    build_parser.add_argument(
        "--manifest",
        default=str(
            PROJECT_ROOT
            / "docs"
            / "manifests"
            / "marco2_importacao_rastreavel_2026-08-31.json"
        ),
        help="manifesto Marco 2 cuja fonte e identidade física devem coincidir exatamente",
    )
    build_parser.add_argument("--output", required=True, help="novo arquivo SQLite fora de corpus_data/")
    build_parser.add_argument("--replace", action="store_true", help="substitui somente o destino após validação")
    build_parser.add_argument(
        "--fail-on-rejections",
        action="store_true",
        help="não promove staging se qualquer bloco for rejeitado",
    )
    verify_parser = subparsers.add_parser("verify", help="valida um banco reconstruído existente")
    verify_parser.add_argument("--db", required=True, help="arquivo SQLite reconstruído")
    verify_parser.add_argument(
        "--manifest",
        default=str(
            PROJECT_ROOT
            / "docs"
            / "manifests"
            / "marco2_importacao_rastreavel_2026-08-31.json"
        ),
        help="manifesto Marco 2 que ancora a proveniência externa do banco",
    )

    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            report = build_reconstruction(
                Path(args.source_dir),
                Path(args.output),
                Path(args.manifest),
                replace=args.replace,
                fail_on_rejections=args.fail_on_rejections,
            )
            _print_json(report.as_dict())
            return 0
        result = validate_reconstruction_database(Path(args.db), Path(args.manifest))
        _print_json(result)
        return 0 if result["ok"] else 1
    except ReconstructionError as error:
        _print_json({"ok": False, "error": str(error)})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
