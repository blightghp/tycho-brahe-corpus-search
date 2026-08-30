"""
test_cartografia.py
===================
Testes unitários para oracle.py e rewriter.py
"""

import unittest
from tree_io import deserialize_tree, serialize_tree
from oracle import (
    classificar_adverbio_cinque,
    extrair_evidencias_cinque,
    validar_ordem_cinque
)
from rewriter import (
    transmutar_arvore_completa,
    expandir_split_cp,
    expandir_split_ip,
    CartographicAnomalyError
)


class TestCartografia(unittest.TestCase):

    def test_classificacao_adverbios(self):
        self.assertEqual(classificar_adverbio_cinque("francamente"), "MoodP_speech_act")
        self.assertEqual(classificar_adverbio_cinque("infelizmente"), "MoodP_evaluative")
        self.assertEqual(classificar_adverbio_cinque("provavelmente"), "ModP_epistemic")
        self.assertEqual(classificar_adverbio_cinque("rapidamente"), "AspP_celerative")
        self.assertEqual(classificar_adverbio_cinque("já"), "T_anterior")

    def test_split_cp_simples(self):
        psd = "(CP-ADV (C que) (IP-SUB (NP-SBJ *pro*) (VB chegou)))"
        tree = deserialize_tree(psd)
        new_tree, injected = expandir_split_cp(tree)
        
        self.assertEqual(new_tree.label(), "CP-ADV")
        self.assertIn("ForceP", injected)
        self.assertIn("FinP", injected)
        # Verifica estrutura
        self.assertEqual(new_tree[0].label(), "ForceP")
        self.assertEqual(new_tree[0][0].label(), "FinP")

    def test_split_cp_com_wh(self):
        psd = "(CP-REL (WNP-1 que) (IP-SUB (NP-SBJ *T*-1) (VB viu)))"
        tree = deserialize_tree(psd)
        new_tree, injected = expandir_split_cp(tree)
        
        self.assertIn("ForceP", injected)
        self.assertIn("FocP", injected)
        self.assertIn("FinP", injected)
        # FocP deve conter o operador WNP
        self.assertEqual(new_tree[0][0].label(), "FocP")
        self.assertEqual(new_tree[0][0][0].label(), "WNP-1")

    def test_split_ip_cinque_canonico(self):
        # Ordem canônica: infelizmente (rank 2) precede provavelmente (rank 4)
        psd = "(IP-MAT (ADVP (ADV infelizmente)) (ADVP (ADV provavelmente)) (VB chegou))"
        tree = deserialize_tree(psd)
        new_tree, injected = expandir_split_ip(tree)
        
        self.assertEqual(new_tree.label(), "IP-MAT")
        self.assertIn("MoodP_evaluative", injected)
        self.assertIn("ModP_epistemic", injected)

    def test_split_ip_cinque_anomalia(self):
        # Ordem invertida: provavelmente (rank 4) antes de infelizmente (rank 2)
        psd = "(IP-MAT (ADVP (ADV provavelmente)) (ADVP (ADV infelizmente)) (VB chegou))"
        tree = deserialize_tree(psd)
        
        with self.assertRaises(CartographicAnomalyError) as ctx:
            expandir_split_ip(tree)
        self.assertEqual(ctx.exception.tipo_anomalia, "HIERARQUIA_CINQUE_VIOLADA")

    def test_transmutacao_completa(self):
        psd = "( (IP-MAT (NP-SBJ (NPR Pedro)) (ADVP (ADV felizmente)) (CP-ADV (C que) (IP-SUB (VB venceu)))))"
        tree = deserialize_tree(psd)
        transformed, injected = transmutar_arvore_completa(tree)
        
        self.assertIn("MoodP_evaluative", injected)
        self.assertIn("ForceP", injected)
        self.assertIn("FinP", injected)


if __name__ == "__main__":
    unittest.main()
