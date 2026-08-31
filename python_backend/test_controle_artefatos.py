"""Testes independentes de dependências NLP para o controle de artefatos."""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from controle_artefatos import (  # noqa: E402
    SCHEMA_VERSION,
    build_manifest,
    inspect_sqlite_file,
    verify_manifest,
    write_manifest,
)


class TestControleArtefatos(unittest.TestCase):
    def _make_project(self, directory: Path) -> Path:
        corpus_dir = directory / "corpus_data"
        corpus_dir.mkdir()
        (corpus_dir / "a_001_psd.txt").write_text(
            "( (IP-MAT (NP-SBJ (N Rei)) (VB falou)) (ID A_001_PSD,01.1))\n",
            encoding="utf-8",
        )
        return directory

    def test_manifest_verifies_canonical_source_and_allows_missing_optional_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self._make_project(Path(temp_dir))
            manifest = build_manifest(root)

            result = verify_manifest(manifest, root)

            self.assertTrue(result["ok"])
            self.assertEqual(result["integrity_status"], "PASS")
            self.assertFalse(result["publication_approved"])
            self.assertEqual(manifest["canonical_sources"]["summary"]["file_count"], 1)
            self.assertEqual(manifest["canonical_sources"]["summary"]["id_record_count"], 1)
            self.assertTrue(manifest["canonical_sources"]["files"][0]["eligible_as_build_input"])
            self.assertEqual(
                manifest["canonical_sources"]["identity_scheme"]["name"],
                "relative_path_ordinal_block_sha256",
            )

    def test_unbalanced_source_is_reported_without_rewriting_the_source(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self._make_project(Path(temp_dir))
            source = root / "corpus_data" / "a_001_psd.txt"
            source.write_text("( (IP-MAT (NP-SBJ (N Rei)) (VB falou))\n", encoding="utf-8")

            manifest = build_manifest(root)

            self.assertEqual(manifest["canonical_sources"]["summary"]["unbalanced_file_count"], 1)
            self.assertTrue(
                any(finding["artifact"] == "canonical_sources" for finding in manifest["findings"])
            )

    def test_verification_detects_source_mutation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self._make_project(Path(temp_dir))
            manifest = build_manifest(root)
            source = root / "corpus_data" / "a_001_psd.txt"
            source.write_text("conteúdo alterado", encoding="utf-8")

            result = verify_manifest(manifest, root)

            self.assertFalse(result["ok"])
            self.assertTrue(any("SHA-256 divergente" in error for error in result["errors"]))

    def test_sqlite_snapshot_reports_cartographic_duplicate_and_yield_signals(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            db_path = root / "cartografia.db"
            connection = sqlite3.connect(db_path)
            connection.executescript(
                """
                CREATE TABLE tb_arvores_expandidas (
                    arquivo TEXT,
                    sent_id_externo TEXT,
                    arvore_original TEXT,
                    arvore_expandida TEXT
                );
                CREATE TABLE tb_quarentena (status TEXT);
                INSERT INTO tb_arvores_expandidas VALUES
                    ('a_001_psd.txt', 'A,1', '(IP (N rei) (V falou))', '(IP (V falou) (N rei))'),
                    ('a_001_psd.txt', 'A,1', '(IP (N rei) (V falou))', '(IP (V falou) (N rei))');
                INSERT INTO tb_quarentena VALUES ('PENDENTE');
                """
            )
            connection.commit()
            connection.close()

            record = inspect_sqlite_file(db_path, root)
            summary = record["sqlite"]["cartographic_database"]

            self.assertEqual(summary["expanded_tree_count"], 2)
            self.assertEqual(summary["duplicate_original_tree_rows"], 1)
            self.assertEqual(summary["surface_yield_mismatches"], 2)
            self.assertEqual(summary["pending_quarantine_count"], 1)

    def test_written_manifest_is_json_and_can_be_loaded_without_side_effects(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self._make_project(Path(temp_dir))
            manifest = build_manifest(root)
            output = root / "docs" / "manifest.json"

            write_manifest(manifest, output)

            loaded = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(loaded["schema_version"], SCHEMA_VERSION)
            self.assertTrue(output.exists())

    def test_optional_artifact_becomes_required_only_in_strict_verification(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self._make_project(Path(temp_dir))
            manifest = build_manifest(root)
            manifest["experimental_artifacts"].append(
                {
                    "path": "release/artefato_ausente.zip",
                    "bytes": 1,
                    "sha256": "0" * 64,
                    "category": "experimental_release",
                    "required": False,
                    "eligible_as_build_input": False,
                }
            )

            optional_result = verify_manifest(manifest, root)
            strict_result = verify_manifest(manifest, root, require_experimental=True)

            self.assertTrue(optional_result["ok"])
            self.assertEqual(optional_result["warning_count"], 1)
            self.assertFalse(strict_result["ok"])
            self.assertEqual(strict_result["error_count"], 1)

    def test_legacy_database_is_never_marked_as_build_input(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self._make_project(Path(temp_dir))
            database = root / "corpus_data" / "corpus_fase1.db"
            sqlite3.connect(database).close()

            manifest = build_manifest(root)
            record = next(
                artifact
                for artifact in manifest["experimental_artifacts"]
                if artifact["path"] == "corpus_data/corpus_fase1.db"
            )

            self.assertEqual(record["status"], "LEGACY_REFERENCE")
            self.assertFalse(record["eligible_as_build_input"])


if __name__ == "__main__":
    unittest.main()
