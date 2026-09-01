"""Testes da busca Marco 4 sobre uma camada M3 construída por APIs públicas."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from analise_gramatical_recon import build_analysis  # noqa: E402
from busca_rastreavel import (  # noqa: E402
    DEFAULT_LIMIT,
    MAX_LIMIT,
    SearchCriteria,
    SearchError,
    search_analysis,
)
from importador_rastreavel import build_reconstruction  # noqa: E402


GRAMMAR_FIXTURE = b"""( (CP-QUE
  (C que)
  (IP-MAT
    (ADVP (ADV felizmente))
    (NP-SBJ (N rei) (N senhor))
    (VP (VB viu) (NP-ACC (D @o) (N livro))
        (PP-DAT (P a) (NP (N rainha))))))
  (ID A_001_PSD,01.1))"""

SECOND_FIXTURE = b"""( (IP-MAT
  (NP-SBJ (N rainha))
  (VP (VB viu) (NP-ACC (N rei))))
  (ID A_001_PSD,02.1))"""


class TestBuscaRastreavel(unittest.TestCase):
    def _build_m3(self, root: Path) -> tuple[Path, Path]:
        corpus = root / "corpus_data"
        corpus.mkdir()
        (corpus / "a_001_psd.txt").write_bytes(b"\r\n\r\n".join((GRAMMAR_FIXTURE, SECOND_FIXTURE)))
        source = root / "marco2.sqlite"
        source_report = build_reconstruction(corpus, source)
        self.assertTrue(source_report.validation["ok"])
        output = root / "marco3.sqlite"
        analysis_report = build_analysis(source, output)
        self.assertTrue(analysis_report.validation["ok"])
        return source, output

    def test_module_import_does_not_require_nltk_or_spacy(self):
        module_dir = str(Path(__file__).resolve().parent)
        script = """
import builtins
import sys
sys.path.insert(0, sys.argv[1])
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name == 'nltk' or name.startswith('nltk.') or name == 'spacy' or name.startswith('spacy.'):
        raise AssertionError(name)
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
import busca_rastreavel
print(busca_rastreavel.DEFAULT_LIMIT)
"""
        result = subprocess.run(
            [sys.executable, "-c", script, module_dir],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(str(DEFAULT_LIMIT), result.stdout)

    def test_cartographic_result_carries_origin_rule_and_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _, analysis = self._build_m3(Path(temp_dir))

            report = search_analysis(
                analysis,
                SearchCriteria(
                    entity_type="EVIDENCIA_CARTOGRAFICA",
                    projection="MoodP_evaluative",
                    rule_id="E_ADV",
                ),
            )

            self.assertFalse(report.full_validation_performed)
            self.assertEqual(len(report.results), 1)
            result = report.results[0]
            self.assertEqual(result["analysis"]["analysis_id"], 1)
            self.assertEqual(result["origin"]["relative_path"], "corpus_data/a_001_psd.txt")
            self.assertEqual(result["origin"]["block_ordinal"], 1)
            self.assertEqual(result["origin"]["candidate_ordinal"], 1)
            self.assertEqual(result["origin"]["import_result"], "IMPORTADO")
            self.assertEqual(result["origin"]["analysis_scope_status"], "ANALISADA")
            self.assertEqual(result["anchor"]["source_base"], "ADVP")
            self.assertIsNone(result["anchor"]["token"])
            self.assertEqual(result["entity"]["evidenced_projection"], "MoodP_evaluative")
            self.assertEqual(result["decision"]["rule_id"], "E_ADV")
            self.assertEqual(result["decision"]["confidence_method"], "HEURISTICA")
            self.assertEqual(result["decision"]["review_status"], "PENDENTE")
            self.assertEqual(result["evidence"][0]["type"], "LEXICO_CONGELADO")
            self.assertEqual(result["evidence"][0]["value"]["gatilho_normalizado"], "felizmente")
            self.assertEqual(len(result["evidence"][0]["sha256"]), 64)

    def test_filters_are_conjunctive_and_results_are_deterministic(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _, analysis = self._build_m3(Path(temp_dir))
            criteria = SearchCriteria(entity_type="NUCLEO_LEXICAL", token="rei", rule_id="L_N")

            first = search_analysis(analysis, criteria).as_dict()
            second = search_analysis(analysis, criteria).as_dict()

            self.assertEqual(first, second)
            self.assertEqual(first["result_count"], 2)
            self.assertEqual([item["origin"]["sentence_id"] for item in first["results"]], [1, 2])
            self.assertTrue(all(item["entity"]["analytical_label"] == "NUCLEO_LEXICAL_NOMINAL" for item in first["results"]))
            self.assertTrue(all(item["anchor"]["token"] == "rei" for item in first["results"]))

    def test_sql_injection_text_is_a_literal_filter(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _, analysis = self._build_m3(Path(temp_dir))
            ordinary = search_analysis(analysis, SearchCriteria(entity_type="NUCLEO_LEXICAL", token="rei"))
            injected = search_analysis(
                analysis,
                SearchCriteria(token="rei' OR 1=1 --", analytical_label="NUCLEO_LEXICAL_NOMINAL"),
            )
            ordinary_after = search_analysis(analysis, SearchCriteria(entity_type="NUCLEO_LEXICAL", token="rei"))

            self.assertGreater(len(ordinary.results), 0)
            self.assertEqual(injected.results, ())
            self.assertEqual(ordinary.as_dict(), ordinary_after.as_dict())

    def test_limit_and_invalid_criteria_are_bounded(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _, analysis = self._build_m3(Path(temp_dir))
            limited = search_analysis(analysis, SearchCriteria(entity_type="NUCLEO_LEXICAL", limit=1))
            self.assertEqual(len(limited.results), 1)

            with self.assertRaises(SearchError):
                search_analysis(analysis, SearchCriteria(limit=0))
            with self.assertRaises(SearchError):
                search_analysis(analysis, SearchCriteria(limit=MAX_LIMIT + 1))
            with self.assertRaises(SearchError):
                search_analysis(analysis, SearchCriteria(entity_type="QUALQUER_COISA"))
            with self.assertRaises(SearchError):
                search_analysis(analysis, SearchCriteria(token=""))
            with self.assertRaises(SearchError):
                search_analysis(analysis, SearchCriteria())

    def test_optional_full_validation_checks_source_before_search(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source, analysis = self._build_m3(Path(temp_dir))
            before = hashlib.sha256(analysis.read_bytes()).hexdigest()

            report = search_analysis(
                analysis,
                SearchCriteria(token="felizmente", entity_type="NUCLEO_LEXICAL"),
                source_database=source,
                require_full_validation=True,
            )

            self.assertTrue(report.full_validation_performed)
            self.assertEqual(len(report.results), 1)
            self.assertEqual(before, hashlib.sha256(analysis.read_bytes()).hexdigest())
            with self.assertRaises(SearchError):
                search_analysis(analysis, require_full_validation=True)

    def test_cli_emits_json_and_can_request_full_validation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source, analysis = self._build_m3(Path(temp_dir))
            module = Path(__file__).resolve().with_name("busca_rastreavel.py")

            result = subprocess.run(
                [
                    sys.executable,
                    str(module),
                    "search",
                    "--db",
                    str(analysis),
                    "--entity-type",
                    "EVIDENCIA_CARTOGRAFICA",
                    "--projection",
                    "MoodP_evaluative",
                    "--rule",
                    "E_ADV",
                    "--limit",
                    "3",
                    "--verify-source",
                    "--source-db",
                    str(source),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["query"]["limit"], 3)
            self.assertTrue(payload["validation"]["full_source_validation"])
            self.assertEqual(payload["result_count"], 1)
            self.assertEqual(payload["results"][0]["decision"]["rule_id"], "E_ADV")

    def test_rejects_database_without_promoted_m3_contract(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            invalid = Path(temp_dir) / "not-m3.sqlite"
            invalid.touch()
            with self.assertRaises(SearchError):
                search_analysis(invalid)


if __name__ == "__main__":
    unittest.main()
