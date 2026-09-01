"""Controle de proveniência dos artefatos do Tycho Brahe Search.

Este utilitário usa somente a biblioteca padrão do Python. Ele cria e verifica
manifestações de integridade para separar o corpus PSD versionado dos bancos,
binários e pacotes de distribuição ainda experimentais.

Ele é deliberadamente somente leitura: ``snapshot`` grava apenas o manifesto
solicitado e nunca altera os artefatos inspecionados.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 2
PROJECT_ROOT = Path(__file__).resolve().parents[1]
ID_RECORD_RE = re.compile(r"\(ID\s+[^)]+\)")
TERMINAL_RE = re.compile(r"\([^()\s]+\s+([^()\s]+)\)")
# A segmentação do Marco 2 é deliberadamente binária: apenas uma linha
# literalmente vazia separa registros. Linhas compostas por espaços pertencem
# a árvores reais e não podem ser tratadas como fronteira.
PHYSICAL_SEGMENTATION_VERSION = "literal-blank-line-bytes@1"
PHYSICAL_SEPARATOR_RE = re.compile(rb"(?:\r?\n\r?\n)+")
PHYSICAL_TRIM_BYTES = b" \t\r\n"

EXPERIMENTAL_DATABASES = (
    "corpus_data/corpus.db",
    "corpus_data/corpus_fase1.db",
    "corpus_data/corpus_cartografia.db",
    "corpus_data/corpus_fase3.db",
)
OPTIONAL_RUNTIME_ARTIFACTS = (
    "python_backend/dist/tycho_backend.exe",
    "tycho-desktop/src-tauri/bin/tycho_backend-x86_64-pc-windows-msvc.exe",
)


def _relative_path(path: Path, root: Path) -> str:
    """Retorna um caminho portátil, relativo à raiz do projeto."""
    return path.resolve().relative_to(root.resolve()).as_posix()


def sha256_file(path: Path) -> str:
    """Calcula SHA-256 sem carregar arquivos grandes inteiros em memória."""
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    """Calcula o checksum de um fragmento bruto, sem decodificá-lo."""
    return hashlib.sha256(payload).hexdigest()


def split_terminal_dos_trailer(payload: bytes) -> tuple[bytes, bytes]:
    """Separa o ``0x1A`` terminal, que não integra a última árvore PSD."""
    if payload.endswith(b"\x1a"):
        return payload[:-1], payload[-1:]
    return payload, b""


def is_historical_candidate_physical_block(raw_block: bytes) -> bool:
    """Aplica o marcador IP/CP histórico à unidade física, sem parseá-la."""
    normalized = raw_block.lstrip(PHYSICAL_TRIM_BYTES)
    return bool(
        normalized.startswith(b"(")
        and (b"(IP-" in normalized or b"(CP-" in normalized)
    )


def physical_record_fingerprint(
    source_relative_path: str,
    records: Iterable[tuple[int, int | None, str]],
) -> dict[str, str]:
    """Resume identidades físicas ordenadas por origem.

    Cada registro contém ``ordinal_fisico``, ``ordinal_candidato`` (ou
    ``None``) e o SHA-256 do BLOB bruto. Os dois digests distinguem o inventário
    completo da visão histórica IP/CP, que pode divergir do scanner de
    S-expressões em arquivos malformados ou grupos mistos.
    """
    physical_lines: list[str] = []
    candidate_lines: list[str] = []
    for physical_ordinal, candidate_ordinal, raw_sha256 in records:
        physical_lines.append(
            f"{source_relative_path}\0{physical_ordinal}\0{raw_sha256}\n"
        )
        if candidate_ordinal is not None:
            candidate_lines.append(
                f"{source_relative_path}\0{physical_ordinal}\0{candidate_ordinal}\0{raw_sha256}\n"
            )
    return {
        "physical_block_identity_sha256": _digest_lines(physical_lines),
        "historical_candidate_identity_sha256": _digest_lines(candidate_lines),
    }


def physical_psd_fingerprint(payload: bytes, source_relative_path: str) -> dict[str, Any]:
    """Inventaria blocos físicos com o mesmo contrato do importador Marco 2."""
    parser_payload, trailer_dos = split_terminal_dos_trailer(payload)
    records: list[tuple[int, int | None, str]] = []
    cursor = 0
    candidate_ordinal = 0

    def append_segment(segment: bytes) -> None:
        nonlocal candidate_ordinal
        if not segment.strip(PHYSICAL_TRIM_BYTES):
            return
        physical_ordinal = len(records) + 1
        candidate = is_historical_candidate_physical_block(segment)
        if candidate:
            candidate_ordinal += 1
        records.append(
            (
                physical_ordinal,
                candidate_ordinal if candidate else None,
                sha256_bytes(segment),
            )
        )

    for match in PHYSICAL_SEPARATOR_RE.finditer(parser_payload):
        append_segment(parser_payload[cursor : match.start()])
        cursor = match.end()
    append_segment(parser_payload[cursor:])

    return {
        "segmentation_version": PHYSICAL_SEGMENTATION_VERSION,
        "physical_block_count": len(records),
        "historical_candidate_count": candidate_ordinal,
        "terminal_dos_trailer_bytes": len(trailer_dos),
        **physical_record_fingerprint(source_relative_path, records),
    }


def _paren_balance(text: str) -> int:
    """Retorna o saldo bruto de parênteses como sinal diagnóstico barato."""
    return text.count("(") - text.count(")")


def extract_top_level_blocks(text: str) -> list[str]:
    """Extrai S-expressões de topo sem depender de NLTK.

    O corpus contém blocos ``CODE`` e árvores sintáticas. Esta rotina é usada
    somente para criar uma identidade estável de bloco; o parser linguístico
    continuará responsável pela validação sintática em uma etapa posterior.
    """
    blocks: list[str] = []
    depth = 0
    start: int | None = None
    for index, character in enumerate(text):
        if character == "(":
            if depth == 0:
                start = index
            depth += 1
        elif character == ")":
            depth -= 1
            if depth == 0 and start is not None:
                blocks.append(text[start : index + 1])
                start = None
            elif depth < 0:
                # O saldo final continua no manifesto; não tentamos recuperar
                # silenciosamente um arquivo estruturalmente corrompido.
                depth = 0
                start = None
    return blocks


def extract_candidate_blocks(text: str) -> list[str]:
    """Retorna o subconjunto histórico de blocos com marcador IP/CP.

    O filtro é mantido para compatibilidade com o retrato legado. A
    reconstrução rastreável usa uma segmentação física mais abrangente e não
    descarta fragmentos por este critério.
    """
    return [
        block
        for block in extract_top_level_blocks(text)
        if "(IP-" in block or "(CP-" in block
    ]


def _digest_lines(lines: Iterable[str]) -> str:
    digest = hashlib.sha256()
    for line in lines:
        digest.update(line.encode("utf-8"))
    return digest.hexdigest()


def candidate_tree_fingerprint(content: str) -> dict[str, Any]:
    """Resume a identidade canônica ``arquivo + ordinal + hash do bloco``."""
    top_level = extract_top_level_blocks(content)
    candidates = extract_candidate_blocks(content)
    external_ids: list[str] = []
    lines: list[str] = []

    for ordinal, block in enumerate(candidates, start=1):
        match = ID_RECORD_RE.search(block)
        external_id = match.group(0)[3:-1].strip() if match else ""
        external_ids.append(external_id)
        block_digest = hashlib.sha256(block.encode("utf-8")).hexdigest()
        # O ID externo é apenas metadado: há valores ausentes e repetidos no
        # corpus. A identidade reprodutível é posição no arquivo + conteúdo.
        lines.append(f"{ordinal}\0{block_digest}\n")

    nonempty_ids = [identifier for identifier in external_ids if identifier]
    repetitions = Counter(nonempty_ids)
    return {
        "top_level_block_count": len(top_level),
        "candidate_tree_count": len(candidates),
        "candidate_without_external_id_count": len(candidates) - len(nonempty_ids),
        "reused_external_id_rows": sum(count - 1 for count in repetitions.values() if count > 1),
        "candidate_identity_sha256": _digest_lines(lines),
    }


# Aliases privados preservados para qualquer automação local que já os use.
_top_level_blocks = extract_top_level_blocks
_candidate_tree_fingerprint = candidate_tree_fingerprint


def inspect_psd_file(path: Path, root: Path) -> dict[str, Any]:
    """Resume um PSD sem depender do parser ou das bibliotecas NLP."""
    raw_content = path.read_bytes()
    content = raw_content.decode("utf-8", errors="replace")
    relative_path = _relative_path(path, root)
    fingerprint = candidate_tree_fingerprint(content)
    return {
        "path": relative_path,
        "category": "canonical_psd_source",
        "status": "CANONICAL_INPUT",
        "required": True,
        "eligible_as_build_input": True,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "id_records": len(ID_RECORD_RE.findall(content)),
        "parentheses_balance": _paren_balance(content),
        "parse_fingerprint": fingerprint,
        "physical_fingerprint": physical_psd_fingerprint(raw_content, relative_path),
    }


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _table_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    rows = connection.execute(f"PRAGMA table_info({_quote_identifier(table)})").fetchall()
    return {str(row[1]) for row in rows}


def _count(connection: sqlite3.Connection, sql: str, parameters: tuple[Any, ...] = ()) -> int:
    row = connection.execute(sql, parameters).fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def _surface_yield_mismatches(
    connection: sqlite3.Connection,
    table: str,
    original_column: str,
    expanded_column: str,
) -> int:
    """Conta mudanças de ordem/valor das folhas pré-terminais.

    A expressão regular é um diagnóstico independente do NLTK; ela é usada
    apenas para comparar a sequência superficial armazenada em duas árvores.
    """
    query = (
        f"SELECT {_quote_identifier(original_column)}, {_quote_identifier(expanded_column)} "
        f"FROM {_quote_identifier(table)}"
    )
    mismatches = 0
    for original, expanded in connection.execute(query):
        original_leaves = TERMINAL_RE.findall(original or "")
        expanded_leaves = TERMINAL_RE.findall(expanded or "")
        if original_leaves != expanded_leaves:
            mismatches += 1
    return mismatches


def inspect_sqlite_file(path: Path, root: Path) -> dict[str, Any]:
    """Coleta integridade, tabelas e sinais conhecidos dos bancos atuais."""
    record: dict[str, Any] = {
        "path": _relative_path(path, root),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "sqlite": {},
    }

    try:
        connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
    except sqlite3.Error as error:
        record["sqlite"] = {"open_error": str(error)}
        return record

    try:
        table_rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
        ).fetchall()
        tables = [str(row[0]) for row in table_rows]
        user_tables = [table for table in tables if not table.startswith("sqlite_")]
        table_counts = {
            table: _count(connection, f"SELECT COUNT(*) FROM {_quote_identifier(table)}")
            for table in user_tables
        }
        integrity_rows = connection.execute("PRAGMA integrity_check").fetchall()
        foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()

        sqlite_info: dict[str, Any] = {
            "integrity_check": [str(row[0]) for row in integrity_rows],
            "foreign_key_error_count": len(foreign_key_errors),
            "table_counts": table_counts,
        }

        table_set = set(tables)
        if {"tb_sentencas", "tb_nos", "tb_relacoes"}.issubset(table_set):
            sentence_columns = _table_columns(connection, "tb_sentencas")
            node_columns = _table_columns(connection, "tb_nos")
            phase_summary: dict[str, Any] = {
                "sentence_count": table_counts["tb_sentencas"],
                "node_count": table_counts["tb_nos"],
                "relation_count": table_counts["tb_relacoes"],
            }
            if "arquivo" in sentence_columns:
                phase_summary["distinct_source_files"] = _count(
                    connection, "SELECT COUNT(DISTINCT arquivo) FROM tb_sentencas"
                )
            if "eh_cartografico" in node_columns:
                phase_summary["cartographic_node_count"] = _count(
                    connection, "SELECT COUNT(*) FROM tb_nos WHERE eh_cartografico = 1"
                )
            if {"sent_original", "sent_expandida"}.issubset(sentence_columns):
                phase_summary["surface_yield_mismatches"] = _surface_yield_mismatches(
                    connection, "tb_sentencas", "sent_original", "sent_expandida"
                )
            if "sent_id_externo" in sentence_columns:
                phase_summary["missing_external_id_count"] = _count(
                    connection,
                    "SELECT COUNT(*) FROM tb_sentencas "
                    "WHERE sent_id_externo IS NULL OR TRIM(sent_id_externo) = ''",
                )
                phase_summary["reused_external_id_rows"] = _count(
                    connection,
                    "SELECT COALESCE(SUM(occurrences - 1), 0) FROM ("
                    "SELECT COUNT(*) AS occurrences FROM tb_sentencas "
                    "GROUP BY arquivo, sent_id_externo HAVING COUNT(*) > 1"
                    ")",
                )
            sqlite_info["phase_database"] = phase_summary

        if "tb_arvores_expandidas" in table_set:
            expanded_columns = _table_columns(connection, "tb_arvores_expandidas")
            cartographic_summary: dict[str, Any] = {
                "expanded_tree_count": table_counts["tb_arvores_expandidas"],
            }
            if "arquivo" in expanded_columns:
                cartographic_summary["distinct_source_files"] = _count(
                    connection,
                    "SELECT COUNT(DISTINCT arquivo) FROM tb_arvores_expandidas",
                )
                cartographic_summary["duplicate_original_tree_rows"] = _count(
                    connection,
                    "SELECT COALESCE(SUM(occurrences - 1), 0) FROM ("
                    "SELECT COUNT(*) AS occurrences FROM tb_arvores_expandidas "
                    "GROUP BY arquivo, arvore_original HAVING COUNT(*) > 1"
                    ")",
                )
            if {"arvore_original", "arvore_expandida"}.issubset(expanded_columns):
                cartographic_summary["surface_yield_mismatches"] = _surface_yield_mismatches(
                    connection,
                    "tb_arvores_expandidas",
                    "arvore_original",
                    "arvore_expandida",
                )
            if "sent_id_externo" in expanded_columns:
                cartographic_summary["missing_external_id_count"] = _count(
                    connection,
                    "SELECT COUNT(*) FROM tb_arvores_expandidas "
                    "WHERE sent_id_externo IS NULL OR TRIM(sent_id_externo) = ''",
                )
            if "tb_quarentena" in table_set:
                cartographic_summary["quarantine_count"] = table_counts["tb_quarentena"]
                quarantine_columns = _table_columns(connection, "tb_quarentena")
                if "status" in quarantine_columns:
                    cartographic_summary["pending_quarantine_count"] = _count(
                        connection,
                        "SELECT COUNT(*) FROM tb_quarentena WHERE status = 'PENDENTE'",
                    )
            sqlite_info["cartographic_database"] = cartographic_summary

        record["sqlite"] = sqlite_info
    except sqlite3.Error as error:
        record["sqlite"] = {"read_error": str(error)}
    finally:
        connection.close()

    return record


def inspect_artifact(path: Path, root: Path, category: str, required: bool) -> dict[str, Any]:
    """Gera um registro de checksum, delegando estatísticas para SQLite."""
    if path.suffix.lower() == ".db":
        record = inspect_sqlite_file(path, root)
    else:
        record = {
            "path": _relative_path(path, root),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
    record["category"] = category
    if category == "pipeline_snapshot":
        record["status"] = "PIPELINE_SNAPSHOT"
    elif category == "experimental_release":
        record["status"] = "RETIRED_DISTRIBUTION"
    elif category == "runtime_binary_snapshot":
        record["status"] = "RUNTIME_SNAPSHOT"
    elif path.name == "corpus_fase1.db":
        record["status"] = "LEGACY_REFERENCE"
    elif path.name == "corpus.db":
        record["status"] = "UNKNOWN_PRE_MANIFEST"
    else:
        record["status"] = "LEGACY_EXPERIMENTAL"
    record["required"] = required
    # Bancos, binários e pacotes só são evidência observacional neste marco;
    # nenhum deles pode voltar a alimentar uma reconstrução por acidente.
    record["eligible_as_build_input"] = False
    return record


def _iter_existing(paths: Iterable[Path]) -> list[Path]:
    return sorted({path.resolve() for path in paths if path.is_file()})


def collect_experimental_artifacts(root: Path, include_release: bool) -> list[dict[str, Any]]:
    """Lista bancos e binários observáveis, sem pressupor que são versionados."""
    records: list[dict[str, Any]] = []

    for relative in EXPERIMENTAL_DATABASES:
        path = root / relative
        if path.is_file():
            records.append(inspect_artifact(path, root, "experimental_database", required=False))

    for relative in OPTIONAL_RUNTIME_ARTIFACTS:
        path = root / relative
        if path.is_file():
            records.append(inspect_artifact(path, root, "runtime_binary_snapshot", required=False))

    if include_release:
        release_files = _iter_existing((root / "release").rglob("*") if (root / "release").exists() else [])
        for path in release_files:
            records.append(inspect_artifact(path, root, "experimental_release", required=False))

    return sorted(records, key=lambda record: record["path"])


def collect_pipeline_snapshot(root: Path) -> list[dict[str, Any]]:
    """Registra o código/configuração que produziu este retrato legado."""
    paths: list[Path] = []
    backend = root / "python_backend"
    desktop = root / "tycho-desktop"

    paths.extend(backend.glob("*.py"))
    paths.extend(backend.glob("*.ps1"))
    paths.extend(backend.glob("*.spec"))
    paths.extend(
        path
        for path in (backend / "requirements.txt",)
        if path.is_file()
    )
    paths.extend(desktop.glob("package*.json"))
    paths.extend(
        path
        for path in (
            desktop / "tsconfig.json",
            desktop / "tsconfig.node.json",
            desktop / "vite.config.ts",
            desktop / "index.html",
        )
        if path.is_file()
    )
    paths.extend((desktop / "src").rglob("*.ts"))
    paths.extend((desktop / "src").rglob("*.tsx"))
    paths.extend((desktop / "src-tauri" / "src").rglob("*.rs"))
    paths.extend(
        path
        for path in (
            desktop / "src-tauri" / "Cargo.toml",
            desktop / "src-tauri" / "Cargo.lock",
            desktop / "src-tauri" / "tauri.conf.json",
            desktop / "src-tauri" / "build.rs",
        )
        if path.is_file()
    )

    return [
        inspect_artifact(path, root, "pipeline_snapshot", required=True)
        for path in _iter_existing(paths)
    ]


def _findings(
    source_summary: dict[str, Any], artifacts: list[dict[str, Any]]
) -> list[dict[str, str]]:
    """Aponta evidências objetivas; não faz inferências linguísticas automáticas."""
    findings: list[dict[str, str]] = []
    source_files = int(source_summary["file_count"])
    source_candidates = int(source_summary["candidate_tree_count"])

    unbalanced_files = int(source_summary["unbalanced_file_count"])
    if unbalanced_files:
        findings.append({
            "level": "ATENCAO",
            "artifact": "canonical_sources",
            "message": (
                f"há {unbalanced_files} arquivo(s) PSD com saldo bruto de parênteses diferente de zero; "
                "a próxima etapa deve registrar o resultado do parser por bloco"
            ),
        })

    for artifact in artifacts:
        sqlite_info = artifact.get("sqlite", {})
        phase = sqlite_info.get("phase_database")
        cartographic = sqlite_info.get("cartographic_database")
        path = artifact["path"]

        if phase:
            distinct = phase.get("distinct_source_files")
            if distinct is not None and distinct < source_files:
                findings.append({
                    "level": "ALERTA",
                    "artifact": path,
                    "message": (
                        f"cobre {distinct} de {source_files} arquivos PSD versionados; "
                        "não pode ser tratado como corpus completo"
                    ),
                })
            sentence_count = phase.get("sentence_count")
            if sentence_count is not None and sentence_count < source_candidates:
                findings.append({
                    "level": "ATENCAO",
                    "artifact": path,
                    "message": (
                        f"contém {sentence_count} sentenças para {source_candidates} blocos candidatos; "
                        "cada diferença deve ter um resultado explícito de importação ou rejeição"
                    ),
                })
            mismatches = phase.get("surface_yield_mismatches", 0)
            if mismatches:
                findings.append({
                    "level": "ALERTA",
                    "artifact": path,
                    "message": f"apresenta {mismatches} árvores com sequência superficial divergente",
                })
            reused_external_ids = phase.get("reused_external_id_rows", 0)
            if reused_external_ids:
                findings.append({
                    "level": "ATENCAO",
                    "artifact": path,
                    "message": (
                        f"reutiliza {reused_external_ids} IDs externos; "
                        "o próximo importador deve usar arquivo, ordinal e hash do bloco como identidade"
                    ),
                })

        if cartographic:
            distinct = cartographic.get("distinct_source_files")
            if distinct is not None and distinct < source_files:
                findings.append({
                    "level": "ALERTA",
                    "artifact": path,
                    "message": (
                        f"cobre {distinct} de {source_files} arquivos PSD versionados; "
                        "a expansão cartográfica está incompleta"
                    ),
                })
            duplicates = cartographic.get("duplicate_original_tree_rows", 0)
            if duplicates:
                findings.append({
                    "level": "ALERTA",
                    "artifact": path,
                    "message": f"apresenta {duplicates} árvores originais duplicadas",
                })
            mismatches = cartographic.get("surface_yield_mismatches", 0)
            if mismatches:
                findings.append({
                    "level": "ALERTA",
                    "artifact": path,
                    "message": f"apresenta {mismatches} árvores expandidas com sequência superficial divergente",
                })

    return findings


def build_manifest(root: Path, include_release: bool = False) -> dict[str, Any]:
    """Monta o retrato imutável da fonte e dos artefatos presentes."""
    root = root.resolve()
    psd_files = sorted((root / "corpus_data").glob("*_psd.txt"))
    sources = [inspect_psd_file(path, root) for path in psd_files]
    source_summary = {
        "file_count": len(sources),
        "byte_count": sum(record["bytes"] for record in sources),
        "id_record_count": sum(record["id_records"] for record in sources),
        "candidate_tree_count": sum(
            record["parse_fingerprint"]["candidate_tree_count"] for record in sources
        ),
        "physical_block_count": sum(
            record["physical_fingerprint"]["physical_block_count"] for record in sources
        ),
        "physical_historical_candidate_count": sum(
            record["physical_fingerprint"]["historical_candidate_count"] for record in sources
        ),
        "candidate_without_external_id_count": sum(
            record["parse_fingerprint"]["candidate_without_external_id_count"]
            for record in sources
        ),
        "reused_external_id_rows": sum(
            record["parse_fingerprint"]["reused_external_id_rows"] for record in sources
        ),
        "unbalanced_file_count": sum(record["parentheses_balance"] != 0 for record in sources),
        "set_sha256": _digest_lines(
            f"{record['path']}\0{record['sha256']}\n" for record in sources
        ),
        "physical_block_set_sha256": _digest_lines(
            f"{record['path']}\0{record['physical_fingerprint']['physical_block_identity_sha256']}\n"
            for record in sources
        ),
        "physical_historical_candidate_set_sha256": _digest_lines(
            f"{record['path']}\0{record['physical_fingerprint']['historical_candidate_identity_sha256']}\n"
            for record in sources
        ),
    }
    artifacts = collect_experimental_artifacts(root, include_release)
    pipeline_snapshot = collect_pipeline_snapshot(root)

    created_at = datetime.now(timezone.utc)
    return {
        "schema_version": SCHEMA_VERSION,
        "format": "tycho-brahe/artifact-provenance@2",
        "manifest_kind": "tycho_brahe_experimental_artifact_snapshot",
        "snapshot_id": f"experimental-baseline-{created_at.date().isoformat()}",
        "created_at_utc": created_at.isoformat(timespec="seconds"),
        "repository_root": ".",
        "verification": {
            "algorithm": "sha256",
            "paths": "repository-relative-posix",
            "set_digest_format": "path + NUL + sha256 + LF, sorted by path",
        },
        "status": {
            "classification": "EXPERIMENTAL_NOT_FOR_RESEARCH_OR_DISTRIBUTION",
            "canonical_source": "corpus_data/*_psd.txt",
            "derived_databases": "observed_only_not_canonical",
            "release_artifacts": "observed_only_not_approved",
        },
        "policy": {
            "do_not_overwrite_sources": True,
            "rebuild_from": "canonical PSD sources after parser and transducer validation",
            "canonical_sources_are_only_build_input": True,
            "experimental_artifacts_are_optional_in_git_clone": True,
        },
        "canonical_sources": {
            "identity_scheme": {
                "name": "relative_path_ordinal_block_sha256",
                "fields": ["source_relative_path", "candidate_ordinal", "block_sha256"],
                "external_id": "metadata_only_not_unique",
            },
            "physical_import_identity_scheme": {
                "name": "relative_path_physical_ordinal_candidate_ordinal_raw_sha256",
                "fields": [
                    "source_relative_path",
                    "physical_ordinal",
                    "candidate_ordinal",
                    "raw_block_sha256",
                ],
                "segmentation_version": PHYSICAL_SEGMENTATION_VERSION,
                "external_id": "metadata_only_not_unique",
            },
            "summary": source_summary,
            "files": sources,
        },
        "pipeline_snapshot": {
            "file_count": len(pipeline_snapshot),
            "set_sha256": _digest_lines(
                f"{record['path']}\0{record['sha256']}\n" for record in pipeline_snapshot
            ),
            "files": pipeline_snapshot,
        },
        "experimental_artifacts": artifacts,
        "findings": _findings(source_summary, artifacts),
    }


def write_manifest(manifest: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_manifest(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file_handle:
        manifest = json.load(file_handle)
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(
            f"Versão de manifesto incompatível: {manifest.get('schema_version')!r}"
        )
    return manifest


def verify_manifest(
    manifest: dict[str, Any], root: Path, require_experimental: bool = False
) -> dict[str, Any]:
    """Verifica tamanho e checksum, sem alterar arquivos ou bancos."""
    errors: list[str] = []
    warnings: list[str] = []
    verified = 0
    records = list(manifest.get("canonical_sources", {}).get("files", []))
    records.extend(manifest.get("pipeline_snapshot", {}).get("files", []))
    records.extend(manifest.get("experimental_artifacts", []))

    for record in records:
        relative = record["path"]
        path = root / relative
        required = bool(record.get("required")) or require_experimental
        if not path.is_file():
            message = f"ausente: {relative}"
            (errors if required else warnings).append(message)
            continue

        actual_size = path.stat().st_size
        actual_hash = sha256_file(path)
        if actual_size != record["bytes"]:
            errors.append(
                f"tamanho divergente: {relative} (esperado {record['bytes']}, obtido {actual_size})"
            )
        if actual_hash != record["sha256"]:
            errors.append(f"SHA-256 divergente: {relative}")
        if actual_size == record["bytes"] and actual_hash == record["sha256"]:
            verified += 1

    return {
        "ok": not errors,
        "integrity_status": "PASS" if not errors else "FAIL",
        "publication_approved": False,
        "publication_status": "EXPERIMENTAL_NOT_FOR_RESEARCH_OR_DISTRIBUTION",
        "verified_file_count": verified,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
    }


def _print_json(data: dict[str, Any]) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Cria e verifica o manifesto de proveniência dos artefatos Tycho Brahe."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    snapshot_parser = subparsers.add_parser("snapshot", help="gera um manifesto somente leitura")
    snapshot_parser.add_argument(
        "--output",
        required=True,
        help="caminho do JSON de saída, relativo à raiz ou absoluto",
    )
    snapshot_parser.add_argument(
        "--include-release",
        action="store_true",
        help="inclui arquivos encontrados em release/ no retrato experimental",
    )

    verify_parser = subparsers.add_parser("verify", help="valida um manifesto existente")
    verify_parser.add_argument("--manifest", required=True, help="caminho do manifesto JSON")
    verify_parser.add_argument(
        "--require-experimental",
        action="store_true",
        help="trata bancos e pacotes experimentais ausentes como erro",
    )

    args = parser.parse_args(argv)
    root = PROJECT_ROOT

    if args.command == "snapshot":
        output = Path(args.output)
        if not output.is_absolute():
            output = root / output
        manifest = build_manifest(root, include_release=args.include_release)
        write_manifest(manifest, output)
        _print_json(
            {
                "status": "CRIADO",
                "manifest": _relative_path(output, root),
                "canonical_source_files": manifest["canonical_sources"]["summary"]["file_count"],
                "experimental_artifact_files": len(manifest["experimental_artifacts"]),
                "finding_count": len(manifest["findings"]),
            }
        )
        return 0

    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = root / manifest_path
    try:
        manifest = load_manifest(manifest_path)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        _print_json({"ok": False, "errors": [str(error)]})
        return 2

    result = verify_manifest(manifest, root, require_experimental=args.require_experimental)
    _print_json(result)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
