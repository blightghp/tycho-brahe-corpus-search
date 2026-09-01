"""Testes puros da camada evidencial e não destrutiva do Marco 3."""

from __future__ import annotations

import hashlib
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from analise_gramatical_recon import (  # noqa: E402
    ANALYSIS_ENGINE_VERSION,
    AnalysisError,
    build_analysis,
    load_ruleset,
    validate_analysis_database,
)
from importador_rastreavel import build_reconstruction, digest_tokens  # noqa: E402


GRAMMAR_FIXTURE = b"""( (CP-QUE
  (C que)
  (IP-MAT
    (ADVP (ADV felizmente))
    (NP-SBJ (N rei) (N senhor))
    (VP (VB viu) (NP-ACC (D @o) (N livro))
        (PP-DAT (P a) (NP (N rainha))))))
  (ID A_001_PSD,01.1))"""

EMPTY_AND_PUNCTUATION = b"""( (IP-MAT
  (NP-SBJ (PRO *pro*))
  (VB viu)
  (NP-ACC (N livro) (PUNC ,))
  (NP-ACC (WNP 0))
  (NP-ACC (WPRO *T*-1)))
  (ID A_001_PSD,02.1))"""

BROKEN_CANDIDATE = b"""( (IP-MAT (NP-SBJ (N falhou)) (VB caiu))
  (ID A_001_PSD,99.1)
  (EXTRA x))"""


class TestAnaliseGramaticalRecon(unittest.TestCase):
    def _build_source(self, root: Path) -> Path:
        corpus = root / "corpus_data"
        corpus.mkdir()
        (corpus / "a_001_psd.txt").write_bytes(
            b"\r\n\r\n".join((GRAMMAR_FIXTURE, EMPTY_AND_PUNCTUATION, BROKEN_CANDIDATE))
        )
        source = root / "marco2.sqlite"
        report = build_reconstruction(corpus, source)
        self.assertTrue(report.validation["ok"])
        self.assertEqual(report.imported_count, 2)
        self.assertEqual(report.rejected_count, 1)
        return source

    def _build_analysis(self, root: Path):
        source = self._build_source(root)
        output = root / "marco3.sqlite"
        report = build_analysis(source, output)
        self.assertTrue(report.validation["ok"])
        return source, output, report

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
import analise_gramatical_recon
print(analise_gramatical_recon.ANALYSIS_ENGINE_VERSION)
"""
        result = subprocess.run(
            [sys.executable, "-c", script, module_dir],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(ANALYSIS_ENGINE_VERSION, result.stdout)

    def test_ruleset_is_versioned_and_has_canonical_digest(self):
        ruleset = load_ruleset()

        self.assertEqual(ruleset.version, "gramatica-expandida-evidencial@1")
        self.assertEqual(len(ruleset.bundle_sha256), 64)
        self.assertEqual(len(ruleset.rules), 15)
        self.assertEqual(ruleset.rules_by_code["E_ADV"].definition["lexicon"]["felizmente"], "MoodP_evaluative")

    def test_build_anchors_every_imported_node_and_preserves_source_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source, output, _ = self._build_analysis(Path(temp_dir))
            before = hashlib.sha256(source.read_bytes()).hexdigest()

            result = validate_analysis_database(output, source)

            self.assertTrue(result["ok"], result["errors"])
            self.assertEqual(before, hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertEqual(result["counts"]["analysis_sentence_count"], 2)
            self.assertGreater(result["counts"]["anchor_node_count"], 0)
            self.assertEqual(result["counts"]["scope_candidate_count"], 3)

    def test_records_source_structure_local_heads_and_cartographic_evidence_without_injection(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _, output, _ = self._build_analysis(Path(temp_dir))
            connection = sqlite3.connect(output)
            try:
                entities = connection.execute(
                    """
                    SELECT tipo, rotulo_analitico, projecao_fonte, projecao_evidenciada
                    FROM m3_entidades
                    ORDER BY entity_id
                    """
                ).fetchall()
                relations = connection.execute(
                    "SELECT status_evidencia FROM m3_decisoes WHERE tipo_decisao='RELACAO'"
                ).fetchall()
                evidence = connection.execute(
                    """
                    SELECT d.regra_id, d.confianca, d.estado_revisao, e.tipo
                    FROM m3_decisoes AS d
                    JOIN m3_entidades AS n ON n.decision_id=d.decision_id
                    JOIN m3_evidencias AS e ON e.decision_id=d.decision_id
                    WHERE n.tipo='EVIDENCIA_CARTOGRAFICA'
                    """
                ).fetchone()
            finally:
                connection.close()

            self.assertIn(("PROJECAO_FONTE", "PROJECAO_FONTE_CP", "CP", None), entities)
            self.assertIn(("NUCLEO_FUNCIONAL", "NUCLEO_FUNCIONAL_C", "CP", None), entities)
            self.assertIn(("NUCLEO_FRONTEIRA", "NUCLEO_P_FONTE", "PP", None), entities)
            self.assertIn(
                ("EVIDENCIA_CARTOGRAFICA", "EVIDENCIA_CINQUE_MoodP_evaluative", "ADVP", "MoodP_evaluative"),
                entities,
            )
            self.assertFalse(any("ForceP" in row[1] or "FinP" in row[1] for row in entities))
            self.assertIn(("AMBIGUO",), relations)
            self.assertEqual(evidence, ("E_ADV", 0.9, "PENDENTE", "LEXICO_CONGELADO"))

    def test_leaf_sequence_and_empty_categories_are_preserved_exactly(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source, output, _ = self._build_analysis(Path(temp_dir))
            source_connection = sqlite3.connect(source)
            analysis_connection = sqlite3.connect(output)
            try:
                source_rows = source_connection.execute(
                    "SELECT sentenca_id, sha256_folhas, quantidade_folhas FROM recon_sentencas ORDER BY sentenca_id"
                ).fetchall()
                analysis_rows = analysis_connection.execute(
                    """
                    SELECT sentenca_id_m2, sha256_folhas_ancoradas, quantidade_folhas_ancoradas
                    FROM m3_sentencas_escopo ORDER BY sentenca_id_m2
                    """
                ).fetchall()
                leaves = analysis_connection.execute(
                    """
                    SELECT token_origem FROM m3_nos_ancora
                    WHERE sentenca_id_m2=2 AND eh_folha=1
                    ORDER BY ordem_folha
                    """
                ).fetchall()
                exclusions = analysis_connection.execute(
                    "SELECT rotulo_analitico FROM m3_entidades WHERE tipo='EXCLUSAO' ORDER BY entity_id"
                ).fetchall()
            finally:
                source_connection.close()
                analysis_connection.close()

            self.assertEqual(source_rows, analysis_rows)
            tokens = [row[0] for row in leaves]
            self.assertEqual(tokens, ["*pro*", "viu", "livro", ",", "0", "*T*-1"])
            self.assertEqual(digest_tokens(tokens), source_rows[1][1])
            self.assertIn(("EXCLUIDO_VAZIO",), exclusions)
            self.assertIn(("EXCLUIDO_PONTUACAO",), exclusions)

    def test_validation_detects_anchor_and_evidence_tampering(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source, output, _ = self._build_analysis(Path(temp_dir))
            connection = sqlite3.connect(output)
            try:
                connection.execute(
                    "UPDATE m3_nos_ancora SET token_origem='alterado' "
                    "WHERE no_id_m2=(SELECT MIN(no_id_m2) FROM m3_nos_ancora WHERE eh_folha=1)"
                )
                connection.execute("UPDATE m3_evidencias SET valor_json='{}' WHERE evidence_id=1")
                connection.commit()
            finally:
                connection.close()

            result = validate_analysis_database(output, source)

            self.assertFalse(result["ok"])
            self.assertTrue(any("âncora M3 divergente" in error for error in result["errors"]))
            self.assertTrue(any("hash de evidência" in error for error in result["errors"]))

    def test_rebuild_is_deterministic_and_destination_is_protected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = self._build_source(root)
            first = root / "first.sqlite"
            second = root / "second.sqlite"
            build_analysis(source, first)
            build_analysis(source, second)
            first_connection = sqlite3.connect(first)
            second_connection = sqlite3.connect(second)
            try:
                first_rows = first_connection.execute(
                    "SELECT regra_id, tipo_decisao, confianca, status_evidencia FROM m3_decisoes ORDER BY decision_id"
                ).fetchall()
                second_rows = second_connection.execute(
                    "SELECT regra_id, tipo_decisao, confianca, status_evidencia FROM m3_decisoes ORDER BY decision_id"
                ).fetchall()
            finally:
                first_connection.close()
                second_connection.close()
            self.assertEqual(first_rows, second_rows)

            protected = root / "protected.sqlite"
            protected.write_bytes(b"artefato-anterior")
            with self.assertRaises(AnalysisError):
                build_analysis(source, protected)
            self.assertEqual(protected.read_bytes(), b"artefato-anterior")


if __name__ == "__main__":
    unittest.main()
