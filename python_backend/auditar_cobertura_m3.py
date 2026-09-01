"""Audita cobertura e pendências do Marco 3 sem alterar o artefato.

O Marco 3 guarda fatos de origem, classificações heurísticas e evidências;
este módulo transforma essas contagens em um relatório determinístico para
planejar curadoria. Ele abre exclusivamente um SQLite ``m3_*`` promovido em
modo somente leitura, não reescreve o PSD/M2/M3 e não converte uma decisão
``PENDENTE`` em conclusão científica.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from analise_gramatical_recon import validate_analysis_database
from busca_rastreavel import AnalysisIdentity, SearchError, _connect_readonly, _load_identity


DEFAULT_SAMPLE_LIMIT = 20
MAX_SAMPLE_LIMIT = 200
_AUDIT_REQUIRED_TABLES = frozenset(
    {
        "m3_escopo_blocos",
        "m3_sentencas_escopo",
        "m3_nos_ancora",
        "m3_decisoes",
        "m3_entidades",
        "m3_relacoes",
        "m3_evidencias",
        "m3_revisoes",
    }
)


class AuditError(RuntimeError):
    """Falha de pré-condição ou de leitura da auditoria Marco 6."""


@dataclass(frozen=True)
class CoverageAuditReport:
    """Relatório serializável de cobertura e fila de curadoria."""

    identity: AnalysisIdentity
    coverage: dict[str, Any]
    curation: dict[str, Any]
    full_validation_performed: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": True,
            "analysis": self.identity.as_dict(),
            "validation": {
                "mode": "integral_m3_m2"
                if self.full_validation_performed
                else "precondicao_m3_promovido",
                "full_source_validation": self.full_validation_performed,
            },
            "coverage": self.coverage,
            "curation": self.curation,
        }


def _scalar(connection: sqlite3.Connection, statement: str, parameters: tuple[Any, ...] = ()) -> int:
    row = connection.execute(statement, parameters).fetchone()
    if row is None:
        raise AuditError("consulta de auditoria não retornou uma contagem")
    return int(row[0])


def _require_audit_tables(connection: sqlite3.Connection) -> None:
    tables = {
        str(row[0])
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    missing = sorted(_AUDIT_REQUIRED_TABLES - tables)
    if missing:
        raise AuditError("artefato M3 não contém tabelas exigidas para auditoria: " + ", ".join(missing))


def _grouped_counts(connection: sqlite3.Connection, statement: str) -> list[dict[str, Any]]:
    return [
        {
            key: int(value) if key == "count" else str(value)
            for key, value in dict(row).items()
        }
        for row in connection.execute(statement).fetchall()
    ]


def _coverage(connection: sqlite3.Connection) -> dict[str, Any]:
    """Agrupa fatos M3 por categorias auditáveis, sem inferir nova análise."""
    return {
        "scope": _grouped_counts(
            connection,
            """
            SELECT resultado_m2 AS import_result, status_analise AS analysis_status, COUNT(*) AS count
            FROM m3_escopo_blocos
            WHERE analysis_id=1
            GROUP BY resultado_m2, status_analise
            ORDER BY resultado_m2, status_analise
            """,
        ),
        "sentence_count": _scalar(
            connection, "SELECT COUNT(*) FROM m3_sentencas_escopo WHERE analysis_id=1"
        ),
        "anchor_count": _scalar(
            connection, "SELECT COUNT(*) FROM m3_nos_ancora WHERE analysis_id=1"
        ),
        "decisions": _grouped_counts(
            connection,
            """
            SELECT tipo_decisao AS decision_type, status_evidencia AS evidence_status,
                   estado_revisao AS review_status, COUNT(*) AS count
            FROM m3_decisoes
            WHERE analysis_id=1
            GROUP BY tipo_decisao, status_evidencia, estado_revisao
            ORDER BY tipo_decisao, evidence_status, review_status
            """,
        ),
        "entities": _grouped_counts(
            connection,
            """
            SELECT tipo AS entity_type, COUNT(*) AS count
            FROM m3_entidades
            WHERE analysis_id=1
            GROUP BY tipo
            ORDER BY tipo
            """,
        ),
        "rules": _grouped_counts(
            connection,
            """
            SELECT d.regra_id AS rule_id, d.tipo_decisao AS decision_type,
                   d.status_evidencia AS evidence_status, COUNT(*) AS count
            FROM m3_decisoes AS d
            WHERE d.analysis_id=1
            GROUP BY d.regra_id, d.tipo_decisao, d.status_evidencia
            ORDER BY d.regra_id, d.tipo_decisao, d.status_evidencia
            """,
        ),
        "relations": _grouped_counts(
            connection,
            """
            SELECT tipo AS relation_type, COUNT(*) AS count
            FROM m3_relacoes
            WHERE analysis_id=1
            GROUP BY tipo
            ORDER BY tipo
            """,
        ),
        "evidences": _grouped_counts(
            connection,
            """
            SELECT tipo AS evidence_type, COUNT(*) AS count
            FROM m3_evidencias
            WHERE analysis_id=1
            GROUP BY tipo
            ORDER BY tipo
            """,
        ),
        "source_projections": _grouped_counts(
            connection,
            """
            SELECT projecao_fonte AS projection, COUNT(*) AS count
            FROM m3_entidades
            WHERE analysis_id=1 AND projecao_fonte IS NOT NULL
            GROUP BY projecao_fonte
            ORDER BY projecao_fonte
            """,
        ),
        "evidenced_projections": _grouped_counts(
            connection,
            """
            SELECT projecao_evidenciada AS projection, COUNT(*) AS count
            FROM m3_entidades
            WHERE analysis_id=1 AND projecao_evidenciada IS NOT NULL
            GROUP BY projecao_evidenciada
            ORDER BY projecao_evidenciada
            """,
        ),
    }


def _cartographic_samples(connection: sqlite3.Connection, sample_limit: int) -> list[dict[str, Any]]:
    if sample_limit == 0:
        return []
    rows = connection.execute(
        """
        SELECT
            e.entity_id, d.decision_id, d.regra_id, d.status_evidencia,
            d.estado_revisao, e.rotulo_analitico, e.projecao_evidenciada,
            n.rotulo_origem, n.rotulo_base, n.preordem, n.token_origem,
            s.caminho_relativo, s.sentenca_id_m2, s.id_externo,
            b.ordinal_bloco_m2, b.ordinal_candidato_m2, b.sha256_bloco_m2
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
        WHERE e.analysis_id=1
          AND e.tipo='EVIDENCIA_CARTOGRAFICA'
          AND d.estado_revisao='PENDENTE'
        ORDER BY
            s.caminho_relativo COLLATE BINARY,
            b.ordinal_bloco_m2,
            s.sentenca_id_m2,
            n.preordem,
            e.entity_id
        LIMIT ?
        """,
        (sample_limit,),
    ).fetchall()
    return [
        {
            "entity_id": int(row["entity_id"]),
            "decision_id": int(row["decision_id"]),
            "rule_id": str(row["regra_id"]),
            "evidence_status": str(row["status_evidencia"]),
            "review_status": str(row["estado_revisao"]),
            "analytical_label": str(row["rotulo_analitico"]),
            "evidenced_projection": str(row["projecao_evidenciada"]),
            "origin": {
                "relative_path": str(row["caminho_relativo"]),
                "block_ordinal": int(row["ordinal_bloco_m2"]),
                "candidate_ordinal": int(row["ordinal_candidato_m2"]),
                "sentence_id": int(row["sentenca_id_m2"]),
                "external_id": str(row["id_externo"]) if row["id_externo"] is not None else None,
                "block_sha256": str(row["sha256_bloco_m2"]),
            },
            "anchor": {
                "source_label": str(row["rotulo_origem"]),
                "source_base": str(row["rotulo_base"]),
                "preorder": int(row["preordem"]),
                "token": str(row["token_origem"]) if row["token_origem"] is not None else None,
            },
        }
        for row in rows
    ]


def _curation(connection: sqlite3.Connection, sample_limit: int) -> dict[str, Any]:
    """Expõe o backlog sem atribuir prioridade ou aprovação automática."""
    pending_decisions = _scalar(
        connection,
        "SELECT COUNT(*) FROM m3_decisoes WHERE analysis_id=1 AND estado_revisao='PENDENTE'",
    )
    return {
        "baseline": (
            "As decisões do Marco 3 são heurísticas e iniciam em PENDENTE. "
            "Este relatório não aprova, rejeita nem grava revisões."
        ),
        "pending_decision_count": pending_decisions,
        "pending_entity_count": _scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM m3_entidades AS e
            JOIN m3_decisoes AS d ON d.decision_id=e.decision_id
            WHERE e.analysis_id=1 AND d.estado_revisao='PENDENTE'
            """,
        ),
        "pending_relation_count": _scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM m3_relacoes AS r
            JOIN m3_decisoes AS d ON d.decision_id=r.decision_id
            WHERE r.analysis_id=1 AND d.estado_revisao='PENDENTE'
            """,
        ),
        "pending_cartographic_evidence_count": _scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM m3_entidades AS e
            JOIN m3_decisoes AS d ON d.decision_id=e.decision_id
            WHERE e.analysis_id=1
              AND e.tipo='EVIDENCIA_CARTOGRAFICA'
              AND d.estado_revisao='PENDENTE'
            """,
        ),
        "registered_review_event_count": _scalar(
            connection, "SELECT COUNT(*) FROM m3_revisoes"
        ),
        "pending_by_evidence_status": _grouped_counts(
            connection,
            """
            SELECT status_evidencia AS evidence_status, COUNT(*) AS count
            FROM m3_decisoes
            WHERE analysis_id=1 AND estado_revisao='PENDENTE'
            GROUP BY status_evidencia
            ORDER BY status_evidencia
            """,
        ),
        "cartographic_evidence_samples": _cartographic_samples(connection, sample_limit),
    }


def audit_analysis(
    analysis_database: Path,
    *,
    sample_limit: int = DEFAULT_SAMPLE_LIMIT,
    source_database: Path | None = None,
    source_manifest_path: Path | None = None,
    ruleset_path: Path | None = None,
    require_full_validation: bool = False,
) -> CoverageAuditReport:
    """Cria um retrato reprodutível de cobertura e pendências do M3.

    A validação integral é opcional pelo mesmo motivo da busca Marco 4: ela é
    apropriada para uma auditoria de liberação, mas não para toda inspeção
    interativa. Sem ela, a identidade e a pré-condição de promoção do M3 ainda
    são verificadas antes de qualquer consulta agregada.
    """
    if isinstance(sample_limit, bool) or not isinstance(sample_limit, int):
        raise AuditError("sample_limit deve ser um inteiro")
    if not 0 <= sample_limit <= MAX_SAMPLE_LIMIT:
        raise AuditError(f"sample_limit deve estar entre 0 e {MAX_SAMPLE_LIMIT}")
    if require_full_validation:
        if source_database is None:
            raise AuditError("source_database é obrigatório para validação integral M3--M2")
        validation = validate_analysis_database(
            analysis_database,
            source_database,
            source_manifest_path,
            ruleset_path,
        )
        if not validation["ok"]:
            raise AuditError("validação integral Marco 3 falhou: " + "; ".join(validation["errors"]))

    connection: sqlite3.Connection | None = None
    try:
        connection = _connect_readonly(analysis_database)
        identity = _load_identity(connection)
        _require_audit_tables(connection)
        return CoverageAuditReport(
            identity=identity,
            coverage=_coverage(connection),
            curation=_curation(connection, sample_limit),
            full_validation_performed=require_full_validation,
        )
    except (SearchError, sqlite3.DatabaseError, OSError, ValueError) as error:
        raise AuditError(f"falha ao auditar o artefato Marco 3: {error}") from error
    finally:
        if connection is not None:
            connection.close()


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audita cobertura e pendências de curadoria de um banco Marco 3 promovido."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    report_parser = subparsers.add_parser("report", help="emite um relatório JSON somente leitura")
    report_parser.add_argument("--db", required=True, help="SQLite Marco 3 promovido")
    report_parser.add_argument(
        "--sample-limit",
        type=int,
        default=DEFAULT_SAMPLE_LIMIT,
        help=f"amostras cartográficas pendentes, entre 0 e {MAX_SAMPLE_LIMIT}",
    )
    report_parser.add_argument(
        "--verify-source",
        action="store_true",
        help="revalida integralmente M3--M2 antes da auditoria",
    )
    report_parser.add_argument("--source-db", help="SQLite Marco 2 exigido com --verify-source")
    report_parser.add_argument("--source-manifest", help="manifesto externo Marco 2")
    report_parser.add_argument("--ruleset", help="bundle de regras Marco 3")
    args = parser.parse_args(argv)
    try:
        report = audit_analysis(
            Path(args.db),
            sample_limit=args.sample_limit,
            source_database=Path(args.source_db) if args.source_db else None,
            source_manifest_path=Path(args.source_manifest) if args.source_manifest else None,
            ruleset_path=Path(args.ruleset) if args.ruleset else None,
            require_full_validation=bool(args.verify_source),
        )
    except AuditError as error:
        _print_json({"ok": False, "error": str(error)})
        return 2
    _print_json(report.as_dict())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
