"""
test_cartografia.py
===================
Testes unitários para oracle.py, rewriter.py e tokenizador_cartografico.py (5 Domínios).
"""

import unittest
from tree_io import deserialize_tree, serialize_tree
from oracle import (
    classificar_adverbio_cinque,
    extrair_evidencias_dominio1_e_3,
    validar_ordem_cinque
)
from rewriter import (
    transmutar_arvore_completa,
    expandir_split_cp_completo,
    expandir_split_ip_cinque,
    CartographicAnomalyError
)
from tokenizador_cartografico import tokenizar_e_etiquetar_arvore, processar_sentenca_texto


class TestCartografia5Dominios(unittest.TestCase):

    def test_classificacao_adverbios(self):
        self.assertEqual(classificar_adverbio_cinque("francamente"), "MoodP_speech_act")
        self.assertEqual(classificar_adverbio_cinque("infelizmente"), "MoodP_evaluative")
        self.assertEqual(classificar_adverbio_cinque("provavelmente"), "ModP_epistemic")
        self.assertEqual(classificar_adverbio_cinque("rapidamente"), "AspP_proximative")
        self.assertEqual(classificar_adverbio_cinque("já"), "T_anterior")

    def test_split_cp_dominio1_e_2(self):
        psd = "(CP-ADV (C que) (IP-SUB (NP-SBJ *pro*) (VB chegou)))"
        tree = deserialize_tree(psd)
        new_tree, injected = expandir_split_cp_completo(tree)
        
        self.assertEqual(new_tree.label(), "CP-ADV")
        self.assertIn("SAP", injected)
        self.assertIn("ForceP", injected)
        self.assertIn("FinP", injected)
        
        # Sequência no topo: SAP -> ForceP -> FinP
        self.assertEqual(new_tree[0].label(), "SAP")
        self.assertEqual(new_tree[0][0].label(), "ForceP")
        self.assertEqual(new_tree[0][0][0].label(), "FinP")

    def test_split_cp_com_vocativo_e_wh(self):
        psd = "(CP-REL (NP-VOC (N Senhor)) (WNP-1 que) (IP-SUB (NP-SBJ *T*-1) (VB viu)))"
        tree = deserialize_tree(psd)
        new_tree, injected = expandir_split_cp_completo(tree)
        
        self.assertIn("SAP", injected)
        self.assertIn("VocP", injected)
        self.assertIn("ForceP", injected)
        self.assertIn("FocP", injected)
        self.assertIn("FinP", injected)
        
        # Verifica aninhamento: SAP -> VocP -> ForceP -> FocP
        self.assertEqual(new_tree[0].label(), "SAP")
        self.assertEqual(new_tree[0][0].label(), "VocP")
        self.assertEqual(new_tree[0][0][1].label(), "ForceP")
        self.assertEqual(new_tree[0][0][1][0].label(), "FocP")

    def test_split_ip_cinque_canonico(self):
        # Ordem canônica: infelizmente (rank 13) precede provavelmente (rank 15)
        psd = "(IP-MAT (ADVP (ADV infelizmente)) (ADVP (ADV provavelmente)) (VB chegou))"
        tree = deserialize_tree(psd)
        new_tree, injected = expandir_split_ip_cinque(tree)
        
        self.assertEqual(new_tree.label(), "IP-MAT")
        self.assertIn("MoodP_evaluative", injected)
        self.assertIn("ModP_epistemic", injected)

    def test_split_ip_cinque_anomalia(self):
        # Ordem invertida: provavelmente antes de infelizmente
        psd = "(IP-MAT (ADVP (ADV provavelmente)) (ADVP (ADV infelizmente)) (VB chegou))"
        tree = deserialize_tree(psd)
        
        with self.assertRaises(CartographicAnomalyError) as ctx:
            expandir_split_ip_cinque(tree)
        self.assertEqual(ctx.exception.tipo_anomalia, "HIERARQUIA_CINQUE_VIOLADA")

    def test_tokenizador_termo_a_termo_5_dominios(self):
        psd = "(CP (ForceP (IP (ADVP (ADV felizmente)) (NP-SBJ (N rei)) (ADVP (ADV já)) (VP (V deu) (NP-ACC (N livro)) (PP-DAT (P a) (NP (N rainha)))))))"
        res = processar_sentenca_texto(psd)
        
        self.assertEqual(res["total_tokens"], 7)
        tokens = res["tokens"]
        
        # Verifica etiquetas dos 5 domínios
        tok_dict = {t["termo"]: t for t in tokens}
        self.assertEqual(tok_dict["felizmente"]["projecao"], "MoodP_evaluative")
        self.assertEqual(tok_dict["já"]["projecao"], "T_anterior")
        self.assertEqual(tok_dict["rei"]["projecao"], "VoiceP_agent")
        self.assertEqual(tok_dict["deu"]["projecao"], "ProcP")
        self.assertEqual(tok_dict["livro"]["projecao"], "Root")
        self.assertEqual(tok_dict["rainha"]["projecao"], "ApplP_low")


if __name__ == "__main__":
    unittest.main()
