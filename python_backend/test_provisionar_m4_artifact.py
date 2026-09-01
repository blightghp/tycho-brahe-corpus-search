"""Testes do provisionamento controlado do artefato desktop Marco 4."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from analise_gramatical_recon import build_analysis  # noqa: E402
from importador_rastreavel import build_reconstruction  # noqa: E402
from controle_artefatos import inspect_psd_file  # noqa: E402
from provisionar_m4_artifact import (  # noqa: E402
    ARTIFACT_RELATIVE_PATH,
    ProvisionError,
    provision_artifact,
)


FIXTURE = b"""( (IP-MAT
  (ADVP (ADV felizmente))
  (NP-SBJ (N rei))
  (VP (VB viu) (NP-ACC (N rainha))))
  (ID A_001_PSD,01.1))"""


class TestProvisionamentoM4(unittest.TestCase):
    def _build_m2_m3(self, root: Path) -> tuple[Path, Path, Path]:
        corpus = root / "corpus_data"
        corpus.mkdir()
        psd = corpus / "a_001_psd.txt"
        psd.write_bytes(FIXTURE)
        manifest = root / "manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "snapshot_id": "fixture-m4-provision",
                    "canonical_sources": {"files": [inspect_psd_file(psd, root)]},
                }
            ),
            encoding="utf-8",
        )
        source = root / "marco2.sqlite"
        self.assertTrue(build_reconstruction(corpus, source, manifest).validation["ok"])
        analysis = root / "marco3.sqlite"
        self.assertTrue(build_analysis(source, analysis, manifest).validation["ok"])
        return source, analysis, manifest

    def test_provision_validates_before_installing_and_preserves_hash(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source, analysis, manifest = self._build_m2_m3(root)
            app_data = root / "app-data"

            receipt = provision_artifact(
                analysis,
                source,
                manifest,
                app_data_dir=app_data,
            )

            installed = app_data / ARTIFACT_RELATIVE_PATH
            self.assertTrue(installed.is_file())
            self.assertEqual(receipt["artifact_sha256"], hashlib.sha256(analysis.read_bytes()).hexdigest())
            self.assertEqual(receipt["artifact_sha256"], hashlib.sha256(installed.read_bytes()).hexdigest())
            self.assertTrue((installed.parent / "provisionamento_m4.json").is_file())
            self.assertIn(receipt["installation_method"], {"hardlink", "copy"})

    def test_existing_destination_requires_explicit_replace(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source, analysis, manifest = self._build_m2_m3(root)
            app_data = root / "app-data"
            provision_artifact(analysis, source, manifest, app_data_dir=app_data)

            with self.assertRaises(ProvisionError):
                provision_artifact(analysis, source, manifest, app_data_dir=app_data)
            replacement = provision_artifact(analysis, source, manifest, app_data_dir=app_data, replace=True)
            self.assertEqual(replacement["artifact_sha256"], hashlib.sha256(analysis.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
