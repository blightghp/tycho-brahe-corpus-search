"""Testes puros do importador PSD rastreável do Marco 2."""

from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from controle_artefatos import (  # noqa: E402
    build_manifest,
    physical_record_fingerprint,
    write_manifest,
)
from importador_rastreavel import (  # noqa: E402
    BuildRejectedError,
    SourceManifestMismatch,
    build_reconstruction,
    parse_psd_tree,
    split_physical_blocks,
    tree_leaves,
    validate_reconstruction_database,
)


VALID_IP = b"""( (IP-MAT
  (NP-SBJ (PRO *pro*))
  (VB viu)
  (NP-ACC (NPR Juiz,))
  (NP-ACC (D @os))
  (NP-ACC (WNP 0))
  (NP-ACC (WPRO *T*-1)))
  (ID A_001_PSD,01.1))"""

VALID_CP = b"""( (CP-QUE
  (C que)
  (IP-SUB (NP-SBJ (N rei)) (VB falou)))
  (ID A_001_PSD,01.1))"""

FRAGMENT = b"""( (FRAG (NP (D o) (N registro)))
  (ID FRAGMENTO,1))"""

CODE = b"( (CODE <P_01>))"

BROKEN_CANDIDATE = b"""( (IP-MAT (NP-SBJ (N falhou)) (VB caiu))
  (ID A_001_PSD,99.1)
  (EXTRA x))"""


class TestImportadorRastreavel(unittest.TestCase):
    def _make_project(self, directory: Path, payload: bytes | None = None) -> Path:
        corpus = directory / "corpus_data"
        corpus.mkdir()
        content = payload or b"\r\n\r\n".join(
            (CODE, VALID_IP, VALID_CP, FRAGMENT, BROKEN_CANDIDATE)
        )
        (corpus / "a_001_psd.txt").write_bytes(content)
        return corpus

    def _build_fixture(self, directory: Path, **kwargs: object):
        corpus = self._make_project(directory)
        output = directory / "build" / "marco2.sqlite"
        report = build_reconstruction(corpus, output, **kwargs)
        return corpus, output, report

    def test_split_uses_only_literal_blank_lines(self):
        payload = b"(IP-MAT\r\n \r\n  (N rei))\r\n\r\n(CP-QUE (C que))"

        blocks = split_physical_blocks(payload)

        self.assertEqual(len(blocks), 2)
        self.assertIn(b"\r\n \r\n", blocks[0].raw_bytes)
        self.assertEqual(blocks[0].start_byte, 0)
        self.assertEqual(blocks[1].ordinal, 2)

    def test_parser_accepts_nested_wrapper_and_stype_metadata(self):
        tree = parse_psd_tree(
            "(( (IP-MAT (NP-SBJ (N Rei)) (VB falou)) "
            "(STYPE .p) (ID A_001_PSD,01.1)))"
        )

        self.assertEqual(tree.label, "IP-MAT")
        self.assertEqual(tree_leaves(tree), ["Rei", "falou"])

    def test_build_records_all_physical_blocks_and_decides_every_candidate(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _, output, report = self._build_fixture(Path(temp_dir))

            self.assertEqual(report.document_count, 1)
            self.assertEqual(report.block_count, 5)
            self.assertEqual(report.candidate_count, 3)
            self.assertEqual(report.imported_count, 2)
            self.assertEqual(report.rejected_count, 1)
            self.assertTrue(report.validation["ok"])

            connection = sqlite3.connect(output)
            try:
                physical = connection.execute("SELECT COUNT(*) FROM recon_blocos_origem").fetchone()[0]
                ledger = connection.execute("SELECT COUNT(*) FROM recon_ledger_importacao").fetchone()[0]
                code_ledger = connection.execute(
                    """
                    SELECT COUNT(*) FROM recon_ledger_importacao ledger
                    JOIN recon_blocos_origem block ON block.bloco_id = ledger.bloco_id
                    WHERE block.eh_candidato_historico_fisico=0
                    """
                ).fetchone()[0]
                rejection = connection.execute(
                    "SELECT codigo_motivo FROM recon_ledger_importacao WHERE resultado='REJEITADO'"
                ).fetchone()[0]
            finally:
                connection.close()

            self.assertEqual(physical, 5)
            self.assertEqual(ledger, 3)
            self.assertEqual(code_ledger, 0)
            self.assertEqual(rejection, "MULTIPLAS_RAIZES")

    def test_identity_uses_candidate_ordinal_not_external_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            corpus = self._make_project(
                Path(temp_dir), b"\n\n".join((VALID_IP, VALID_CP, VALID_IP.replace(b"(ID A_001_PSD,01.1)", b""))),
            )
            output = Path(temp_dir) / "out.sqlite"
            report = build_reconstruction(corpus, output)

            self.assertEqual(report.candidate_count, 3)
            connection = sqlite3.connect(output)
            try:
                rows = connection.execute(
                    """
                    SELECT ordinal_candidato, id_externo, sha256_bloco
                    FROM recon_blocos_origem
                    ORDER BY ordinal_bloco
                    """
                ).fetchall()
            finally:
                connection.close()

            self.assertEqual([row[0] for row in rows], [1, 2, 3])
            self.assertEqual(rows[0][1], rows[1][1])
            self.assertIsNone(rows[2][1])
            self.assertNotEqual(rows[0][2], rows[1][2])
            connection = sqlite3.connect(output)
            try:
                source_path = connection.execute(
                    "SELECT caminho_relativo FROM recon_documentos"
                ).fetchone()[0]
            finally:
                connection.close()
            self.assertEqual(source_path, "corpus_data/a_001_psd.txt")

    def test_leaf_sequence_is_preserved_exactly(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _, output, _ = self._build_fixture(Path(temp_dir))
            connection = sqlite3.connect(output)
            try:
                tokens = [
                    row[0]
                    for row in connection.execute(
                        """
                        SELECT node.token_origem
                        FROM recon_nos node
                        JOIN recon_sentencas sentence ON sentence.sentenca_id=node.sentenca_id
                        WHERE sentence.rotulo_raiz='IP-MAT' AND node.eh_folha=1
                        ORDER BY node.ordem_folha
                        """
                    )
                ]
            finally:
                connection.close()

            self.assertEqual(tokens, ["*pro*", "viu", "Juiz,", "@os", "0", "*T*-1"])

    def test_manifest_mismatch_blocks_publication_before_staging(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            corpus = self._make_project(root, VALID_IP)
            manifest = build_manifest(root)
            manifest_path = root / "manifest.json"
            write_manifest(manifest, manifest_path)
            source = corpus / "a_001_psd.txt"
            source.write_bytes(VALID_CP)
            output = root / "out.sqlite"

            with self.assertRaises(SourceManifestMismatch):
                build_reconstruction(corpus, output, manifest_path)

            self.assertFalse(output.exists())

    def test_physical_manifest_fingerprint_blocks_publication(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            corpus = self._make_project(root, VALID_IP)
            manifest = build_manifest(root)
            manifest["canonical_sources"]["files"][0]["physical_fingerprint"][
                "physical_block_identity_sha256"
            ] = "0" * 64
            manifest_path = root / "manifest.json"
            write_manifest(manifest, manifest_path)
            output = root / "out.sqlite"

            with self.assertRaises(SourceManifestMismatch):
                build_reconstruction(corpus, output, manifest_path)

            self.assertFalse(output.exists())

    def test_rejections_do_not_overwrite_existing_destination(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            corpus = self._make_project(root)
            output = root / "out.sqlite"
            output.write_bytes(b"artefato-anterior")

            with self.assertRaises(BuildRejectedError):
                build_reconstruction(corpus, output, replace=True, fail_on_rejections=True)

            self.assertEqual(output.read_bytes(), b"artefato-anterior")

    def test_validation_detects_tampered_surface_yield(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _, output, _ = self._build_fixture(Path(temp_dir))
            connection = sqlite3.connect(output)
            try:
                connection.execute(
                    "UPDATE recon_nos SET token_origem='alterado' WHERE no_id=(SELECT MIN(no_id) FROM recon_nos WHERE eh_folha=1)"
                )
                connection.commit()
            finally:
                connection.close()

            result = validate_reconstruction_database(output)

            self.assertFalse(result["ok"])
            self.assertTrue(any("sequência superficial" in error for error in result["errors"]))

    def test_validation_detects_tampered_raw_block_and_normalized_tree(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _, output, _ = self._build_fixture(Path(temp_dir))
            connection = sqlite3.connect(output)
            try:
                connection.execute(
                    "UPDATE recon_blocos_origem SET conteudo_bruto=? WHERE bloco_id=1",
                    (b"bloco alterado",),
                )
                connection.execute(
                    "UPDATE recon_sentencas SET arvore_normalizada='(IP-MAT (N alterado))' "
                    "WHERE sentenca_id=(SELECT MIN(sentenca_id) FROM recon_sentencas)",
                )
                connection.commit()
            finally:
                connection.close()

            result = validate_reconstruction_database(output)

            self.assertFalse(result["ok"])
            self.assertTrue(any("conteúdo bruto" in error for error in result["errors"]))
            self.assertTrue(any("árvore(s) normalizada(s) com SHA-256" in error for error in result["errors"]))

    def test_validation_detects_tampered_physical_identity(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _, output, _ = self._build_fixture(Path(temp_dir))
            replacement = b"bloco alterado mas com hash atualizado"
            from hashlib import sha256

            connection = sqlite3.connect(output)
            try:
                connection.execute(
                    "UPDATE recon_blocos_origem SET conteudo_bruto=?, sha256_bloco=? WHERE bloco_id=1",
                    (replacement, sha256(replacement).hexdigest()),
                )
                connection.commit()
            finally:
                connection.close()

            result = validate_reconstruction_database(output)

            self.assertFalse(result["ok"])
            self.assertTrue(any("fingerprint físico" in error for error in result["errors"]))

    def test_manifest_anchor_detects_coordinated_internal_tampering(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            corpus = self._make_project(root)
            manifest_path = root / "manifest.json"
            write_manifest(build_manifest(root), manifest_path)
            output = root / "out.sqlite"
            build_reconstruction(corpus, output, manifest_path)

            replacement = b"( (CODE bloco-alterado))"
            from hashlib import sha256

            connection = sqlite3.connect(output)
            try:
                code_block = connection.execute(
                    "SELECT bloco_id FROM recon_blocos_origem WHERE eh_candidato_historico_fisico=0 LIMIT 1"
                ).fetchone()[0]
                connection.execute(
                    "UPDATE recon_blocos_origem SET conteudo_bruto=?, sha256_bloco=? WHERE bloco_id=?",
                    (replacement, sha256(replacement).hexdigest(), code_block),
                )
                records = connection.execute(
                    """
                    SELECT ordinal_bloco, ordinal_candidato, sha256_bloco
                    FROM recon_blocos_origem ORDER BY ordinal_bloco
                    """
                ).fetchall()
                fingerprint = physical_record_fingerprint(
                    "corpus_data/a_001_psd.txt",
                    [(row[0], row[1], row[2]) for row in records],
                )
                connection.execute(
                    """
                    UPDATE recon_documentos
                    SET sha256_identidade_blocos_fisicos=?,
                        sha256_identidade_candidatos_fisicos=?
                    """,
                    (
                        fingerprint["physical_block_identity_sha256"],
                        fingerprint["historical_candidate_identity_sha256"],
                    ),
                )
                connection.execute(
                    "UPDATE recon_meta SET valor=? WHERE chave='source_manifest_sha256'",
                    ("0" * 64,),
                )
                connection.commit()
            finally:
                connection.close()

            internal_only = validate_reconstruction_database(output)
            anchored = validate_reconstruction_database(output, manifest_path)

            self.assertTrue(internal_only["ok"])
            self.assertFalse(anchored["ok"])
            self.assertTrue(any("sha256_identidade_blocos_fisicos" in error for error in anchored["errors"]))
            self.assertTrue(any("hash do manifesto Marco 2" in error for error in anchored["errors"]))

    def test_validation_rejects_sentence_without_import_ledger(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _, output, _ = self._build_fixture(Path(temp_dir))
            connection = sqlite3.connect(output)
            try:
                code_block = connection.execute(
                    "SELECT bloco_id FROM recon_blocos_origem WHERE eh_candidato_historico_fisico=0 LIMIT 1"
                ).fetchone()[0]
                source_sentence = connection.execute(
                    "SELECT sentenca_id FROM recon_sentencas LIMIT 1"
                ).fetchone()[0]
                connection.execute(
                    """
                    INSERT INTO recon_sentencas(
                        bloco_id, documento_id, caminho_relativo, id_externo, rotulo_raiz,
                        classe_estrutura, arvore_normalizada, texto_superficial,
                        sha256_folhas, quantidade_folhas, quantidade_nos
                    )
                    SELECT ?, documento_id, caminho_relativo, id_externo, rotulo_raiz,
                           classe_estrutura, arvore_normalizada, texto_superficial,
                           sha256_folhas, quantidade_folhas, quantidade_nos
                    FROM recon_sentencas WHERE sentenca_id=?
                    """,
                    (code_block, source_sentence),
                )
                connection.commit()
            finally:
                connection.close()

            result = validate_reconstruction_database(output)

            self.assertFalse(result["ok"])
            self.assertTrue(any("sem decisão IMPORTADO" in error for error in result["errors"]))

    def test_validation_reports_missing_database_without_traceback(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = validate_reconstruction_database(Path(temp_dir) / "ausente.sqlite")

            self.assertFalse(result["ok"])
            self.assertTrue(any("não encontrado" in error for error in result["errors"]))

    def test_dos_trailer_is_preserved_outside_last_tree(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            corpus = self._make_project(root, VALID_IP + b"\x1a")
            output = root / "out.sqlite"
            report = build_reconstruction(corpus, output)
            self.assertEqual(report.imported_count, 1)

            connection = sqlite3.connect(output)
            try:
                trailer = connection.execute("SELECT trailer_dos FROM recon_documentos").fetchone()[0]
            finally:
                connection.close()
            self.assertEqual(trailer, b"\x1a")


if __name__ == "__main__":
    unittest.main()
