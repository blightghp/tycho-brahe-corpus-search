"""Testes da auditoria de cobertura e pendências Marco 6."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from analise_gramatical_recon import build_analysis  # noqa: E402
from auditar_cobertura_m3 import (  # noqa: E402
    MAX_SAMPLE_LIMIT,
    AuditError,
    audit_analysis,
)
from importador_rastreavel import build_reconstruction  # noqa: E402


FIXTURE = b"""( (CP-QUE
  (C que)
  (IP-MAT
    (ADVP (ADV felizmente))
    (NP-SBJ (N rei))
    (VP (VB viu) (NP-ACC (N rainha)))))
  (ID A_001_PSD,01.1))"""

SECOND_FIXTURE = b"""( (IP-MAT
  (NP-SBJ (N rainha))
  (VP (VB viu) (NP-ACC (N rei))))
  (ID A_001_PSD,02.1))"""


class TestAuditoriaCoberturaM3(unittest.TestCase):
    def _build_m3(self, root: Path) -> tuple[Path, Path]:
        corpus = root / "corpus_data"
        corpus.mkdir()
        (corpus / "a_001_psd.txt").write_bytes(b"\r\n\r\n".join((FIXTURE, SECOND_FIXTURE)))
        source = root / "marco2.sqlite"
        self.assertTrue(build_reconstruction(corpus, source).validation["ok"])
        analysis = root / "marco3.sqlite"
        self.assertTrue(build_analysis(source, analysis).validation["ok"])
        return source, analysis

    def test_report_is_read_only_and_exposes_coverage_and_backlog(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _, analysis = self._build_m3(Path(temp_dir))
            before = hashlib.sha256(analysis.read_bytes()).hexdigest()

            report = audit_analysis(analysis, sample_limit=3).as_dict()

            self.assertTrue(report["ok"])
            self.assertEqual(report["validation"]["mode"], "precondicao_m3_promovido")
            self.assertEqual(report["coverage"]["sentence_count"], 2)
            self.assertGreater(report["coverage"]["anchor_count"], 0)
            self.assertEqual(
                sum(row["count"] for row in report["coverage"]["decisions"]),
                report["curation"]["pending_decision_count"],
            )
            entity_counts = {row["entity_type"]: row["count"] for row in report["coverage"]["entities"]}
            self.assertGreater(entity_counts["NUCLEO_LEXICAL"], 0)
            self.assertEqual(entity_counts["EVIDENCIA_CARTOGRAFICA"], 1)
            self.assertEqual(report["curation"]["pending_cartographic_evidence_count"], 1)
            self.assertEqual(report["curation"]["registered_review_event_count"], 0)
            sample = report["curation"]["cartographic_evidence_samples"][0]
            self.assertEqual(sample["origin"]["relative_path"], "corpus_data/a_001_psd.txt")
            self.assertEqual(sample["evidenced_projection"], "MoodP_evaluative")
            self.assertEqual(sample["rule_id"], "E_ADV")
            self.assertEqual(before, hashlib.sha256(analysis.read_bytes()).hexdigest())

    def test_full_validation_and_cli_emit_deterministic_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source, analysis = self._build_m3(Path(temp_dir))
            report = audit_analysis(
                analysis,
                sample_limit=0,
                source_database=source,
                require_full_validation=True,
            ).as_dict()
            self.assertTrue(report["validation"]["full_source_validation"])
            self.assertEqual(report["curation"]["cartographic_evidence_samples"], [])

            module = Path(__file__).resolve().with_name("auditar_cobertura_m3.py")
            result = subprocess.run(
                [
                    sys.executable,
                    str(module),
                    "report",
                    "--db",
                    str(analysis),
                    "--sample-limit",
                    "1",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["ok"])
            self.assertFalse(payload["validation"]["full_source_validation"])
            self.assertEqual(len(payload["curation"]["cartographic_evidence_samples"]), 1)

    def test_invalid_limits_and_artifacts_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _, analysis = self._build_m3(root)
            with self.assertRaises(AuditError):
                audit_analysis(analysis, sample_limit=MAX_SAMPLE_LIMIT + 1)
            invalid = root / "not-m3.sqlite"
            invalid.touch()
            with self.assertRaises(AuditError):
                audit_analysis(invalid)

            connection = sqlite3.connect(analysis)
            try:
                connection.execute("DROP TABLE m3_revisoes")
                connection.commit()
            finally:
                connection.close()
            with self.assertRaises(AuditError):
                audit_analysis(analysis)


if __name__ == "__main__":
    unittest.main()
