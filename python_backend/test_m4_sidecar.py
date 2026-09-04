"""Testes ponta a ponta do contrato do sidecar dedicado Marco 4."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from analise_gramatical_recon import build_analysis  # noqa: E402
from importador_rastreavel import build_reconstruction  # noqa: E402


FIXTURE = b"""( (CP-QUE
  (C que)
  (IP-MAT
    (ADVP (ADV felizmente))
    (NP-SBJ (N rei))
    (VP (VB viu) (NP-ACC (N rainha)))))
  (ID A_001_PSD,01.1))"""


class TestM4Sidecar(unittest.TestCase):
    """Executa a mesma entrada que o binário PyInstaller encaminha ao M4."""

    sidecar = Path(__file__).resolve().with_name("m4_sidecar.py")

    def _build_m3(self, root: Path) -> Path:
        corpus = root / "corpus_data"
        corpus.mkdir()
        (corpus / "a_001_psd.txt").write_bytes(FIXTURE)

        source = root / "marco2.sqlite"
        self.assertTrue(build_reconstruction(corpus, source).validation["ok"])

        analysis = root / "marco3.sqlite"
        self.assertTrue(build_analysis(source, analysis).validation["ok"])
        return analysis

    def _run(self, *arguments: str) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [sys.executable, str(self.sidecar), *arguments],
            capture_output=True,
            check=False,
        )

    def test_sidecar_forwards_a_search_response_as_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            analysis = self._build_m3(Path(temp_dir))
            result = self._run(
                "search",
                "--db",
                str(analysis),
                "--entity-type",
                "EVIDENCIA_CARTOGRAFICA",
                "--projection",
                "MoodP_evaluative",
                "--rule",
                "E_ADV",
            )

        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))
        payload = json.loads(result.stdout.decode("utf-8"))
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["result_count"], 1)
        self.assertEqual(payload["results"][0]["decision"]["rule_id"], "E_ADV")

    def test_sidecar_errors_are_json_encoded_as_utf8(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing_database = Path(temp_dir) / "ausente.sqlite"
            result = self._run(
                "search",
                "--db",
                str(missing_database),
                "--token",
                "teste",
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("não".encode("utf-8"), result.stdout)
        payload = json.loads(result.stdout.decode("utf-8"))
        self.assertFalse(payload["ok"])
        self.assertIn("não encontrado", payload["error"])


if __name__ == "__main__":
    unittest.main()
