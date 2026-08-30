"""
test_e2e_pipeline.py
====================
Suíte de Testes de Integração Ponta a Ponta (End-to-End Test Suite).

Valida todos os estágios do sistema:
  1. Leitura e deserialização de árvores sintáticas do Corpus Tycho Brahe.
  2. Transmutação algorítmica pelos 5 Grandes Domínios Cartográficos.
  3. Tokenização e etiquetagem termo a termo com extração de traços.
  4. Detecção e captura de anomalias/quarentena.
  5. Comunicação IPC via CLI com formato JSON para consumo pelo Tauri/React.
"""

import unittest
import json
import subprocess
import sys
import os

from tree_io import deserialize_tree, serialize_tree
from rewriter import transmutar_arvore_completa, CartographicAnomalyError
from tokenizador_cartografico import processar_sentenca_texto


class TestE2EPipeline(unittest.TestCase):

    def test_01_arvore_simples_5_dominios(self):
        """Valida que uma árvore com domínios 1, 2, 3 e 5 é gerada e anotada perfeitamente."""
        psd = "( (IP-MAT (NP-VOC (N Senhor)) (ADVP (ADV felizmente)) (NP-SBJ (N rei)) (ADVP (ADV já)) (VP (V deu) (NP-ACC (N livro)))))"
        tree = deserialize_tree(psd)
        self.assertIsNotNone(tree)

        res_tokens = processar_sentenca_texto(psd)
        self.assertEqual(res_tokens["total_tokens"], 6)

        # Mapeamento termo -> projeção
        proj_map = {t["termo"]: t["projecao"] for t in res_tokens["tokens"]}
        
        self.assertEqual(proj_map["Senhor"], "VocP")
        self.assertEqual(proj_map["felizmente"], "MoodP_evaluative")
        self.assertEqual(proj_map["rei"], "VoiceP_agent")
        self.assertEqual(proj_map["já"], "T_anterior")
        self.assertEqual(proj_map["deu"], "ProcP")
        self.assertEqual(proj_map["livro"], "Root")

    def test_02_violacao_cinque_quarentena(self):
        """Valida que uma inversão adverbial gera CartographicAnomalyError."""
        # 'já' (rank 25) colocado antes de 'felizmente' (rank 13)
        psd = "(IP-MAT (ADVP (ADV já)) (ADVP (ADV felizmente)) (VB chegou))"
        tree = deserialize_tree(psd)
        
        with self.assertRaises(CartographicAnomalyError) as ctx:
            transmutar_arvore_completa(tree)
            
        self.assertEqual(ctx.exception.tipo_anomalia, "HIERARQUIA_CINQUE_VIOLADA")

    def test_03_ipc_cli_tokenizar_json(self):
        """Valida que o CLI pesquisa_sintatica.py --acao tokenizar retorna JSON parseável."""
        cmd = [
            sys.executable,
            os.path.join(os.path.dirname(__file__), "pesquisa_sintatica.py"),
            "--acao", "tokenizar",
            "--token", "(CP (NP-VOC (N Rei)) (IP (ADVP (ADV francamente)) (VP (V falou))))",
            "--formato", "json"
        ]
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        self.assertEqual(res.returncode, 0, f"Erro stderr: {res.stderr}")
        
        data = json.loads(res.stdout.strip())
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 3)
        self.assertEqual(data[0]["termo"], "Rei")
        self.assertEqual(data[0]["projecao"], "VocP")
        self.assertEqual(data[1]["termo"], "francamente")
        self.assertEqual(data[1]["projecao"], "MoodP_speech_act")

    def test_04_ipc_cli_busca_db(self):
        """Valida busca no banco SQLite gerando JSON válido."""
        db_candidates = [
            os.path.join(os.path.dirname(__file__), "../corpus_data/corpus_fase3.db"),
            os.path.join(os.path.dirname(__file__), "../corpus_data/corpus_fase1.db"),
            "corpus_data/corpus_fase3.db",
        ]
        db_path = next((p for p in db_candidates if os.path.exists(p)), None)
        if not db_path:
            self.skipTest("Banco SQLite de teste não encontrado para consulta.")

        cmd = [
            sys.executable,
            os.path.join(os.path.dirname(__file__), "pesquisa_sintatica.py"),
            "--db", db_path,
            "--acao", "busca",
            "--label", "ForceP",
            "--limite", "5",
            "--formato", "json"
        ]
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        self.assertEqual(res.returncode, 0, f"Erro stderr: {res.stderr}")
        data = json.loads(res.stdout.strip())
        self.assertIsInstance(data, list)


if __name__ == "__main__":
    unittest.main()
