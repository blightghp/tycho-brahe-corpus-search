"""Provisiona um artefato Marco 3 validado para a ponte desktop Marco 5.

O aplicativo Tauri não recebe caminhos de banco da interface e não embute o
SQLite M3 no instalador. Este utilitário é a rota explícita para colocar uma
análise já validada no local controlado pelo aplicativo. Antes de criar o
destino, ele revalida integralmente a relação M3--M2. O arquivo é instalado
por hard link quando possível (sem duplicar gigabytes no mesmo volume) ou por
cópia em staging com SHA-256 conferido; uma instalação existente só é trocada
com ``--replace``.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from analise_gramatical_recon import validate_analysis_database
from controle_artefatos import sha256_file


APP_IDENTIFIER = "br.unicamp.iel.tycho-brahe"
ARTIFACT_RELATIVE_PATH = Path("artifacts") / "marco3" / "corpus_marco3_evidencial.sqlite"
RECEIPT_FILENAME = "provisionamento_m4.json"


class ProvisionError(RuntimeError):
    """Falha segura de validação ou instalação do artefato M4."""


def default_app_data_dir() -> Path:
    app_data = os.environ.get("APPDATA")
    if not app_data:
        raise ProvisionError("APPDATA não está definido; informe --app-data-dir explicitamente")
    return Path(app_data) / APP_IDENTIFIER


def controlled_artifact_path(app_data_dir: Path) -> Path:
    return app_data_dir.resolve() / ARTIFACT_RELATIVE_PATH


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _install_staging(source: Path, destination: Path) -> tuple[Path, str]:
    """Cria um staging com link físico preferido e cópia verificada como fallback."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = destination.with_name(f".{destination.name}.staging-{uuid.uuid4().hex}")
    method = "hardlink"
    try:
        try:
            os.link(source, staging)
        except OSError:
            method = "copy"
            shutil.copy2(source, staging)
        if sha256_file(staging) != sha256_file(source):
            raise ProvisionError("o staging do artefato Marco 3 não preservou o SHA-256 da fonte")
        return staging, method
    except Exception:
        if staging.exists():
            staging.unlink()
        raise


def provision_artifact(
    analysis_database: Path,
    source_database: Path,
    source_manifest_path: Path,
    *,
    app_data_dir: Path | None = None,
    ruleset_path: Path | None = None,
    replace: bool = False,
) -> dict[str, Any]:
    """Valida M3--M2 e instala a análise no local fixo do aplicativo."""
    analysis = analysis_database.resolve()
    source = source_database.resolve()
    manifest = source_manifest_path.resolve()
    if not analysis.is_file():
        raise ProvisionError(f"banco Marco 3 não encontrado: {analysis}")
    if not source.is_file():
        raise ProvisionError(f"banco Marco 2 não encontrado: {source}")
    if not manifest.is_file():
        raise ProvisionError(f"manifesto Marco 2 não encontrado: {manifest}")

    validation = validate_analysis_database(analysis, source, manifest, ruleset_path)
    if not validation["ok"]:
        raise ProvisionError("validação integral M3--M2 falhou: " + "; ".join(validation["errors"]))

    app_root = (app_data_dir or default_app_data_dir()).resolve()
    destination = controlled_artifact_path(app_root)
    if destination.exists() and not replace:
        raise ProvisionError(
            "já existe um artefato M3 provisionado; use --replace somente após "
            "revisar a origem e a validação"
        )

    staging, method = _install_staging(analysis, destination)
    try:
        if destination.exists() and replace:
            os.replace(staging, destination)
        elif not destination.exists():
            os.replace(staging, destination)
        else:
            raise ProvisionError("destino Marco 3 foi alterado durante o provisionamento")
    except Exception:
        if staging.exists():
            staging.unlink()
        raise

    receipt = {
        "schema_version": 1,
        "provisioned_at_utc": datetime.now(timezone.utc).isoformat(),
        "installation_method": method,
        "artifact_path": str(destination),
        "artifact_sha256": sha256_file(destination),
        "source_m2_path": str(source),
        "source_m2_sha256": sha256_file(source),
        "source_manifest_path": str(manifest),
        "validation_counts": validation["counts"],
    }
    receipt_path = destination.parent / RECEIPT_FILENAME
    receipt_path.write_text(_canonical_json(receipt) + "\n", encoding="utf-8")
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Valida e provisiona um SQLite Marco 3 para a busca desktop Marco 4."
    )
    parser.add_argument("--analysis-db", required=True, help="SQLite Marco 3 promovido")
    parser.add_argument("--source-db", required=True, help="SQLite Marco 2 de origem")
    parser.add_argument("--source-manifest", required=True, help="manifesto externo Marco 2")
    parser.add_argument("--ruleset", help="bundle de regras Marco 3, se não for o padrão")
    parser.add_argument("--app-data-dir", help="diretório de dados controlado; padrão: APPDATA do identificador Tauri")
    parser.add_argument("--replace", action="store_true", help="substitui o artefato provisionado somente após validação integral")
    args = parser.parse_args(argv)
    try:
        receipt = provision_artifact(
            Path(args.analysis_db),
            Path(args.source_db),
            Path(args.source_manifest),
            app_data_dir=Path(args.app_data_dir) if args.app_data_dir else None,
            ruleset_path=Path(args.ruleset) if args.ruleset else None,
            replace=bool(args.replace),
        )
    except (ProvisionError, OSError, ValueError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps({"ok": True, "provisioning": receipt}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
