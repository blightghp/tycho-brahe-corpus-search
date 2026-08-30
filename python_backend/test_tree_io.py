"""
test_tree_io.py
===============
Testes unitários para tree_io.py
"""

import unittest
from tree_io import deserialize_tree, serialize_tree, extract_sent_id


class TestTreeIO(unittest.TestCase):
    
    def test_roundtrip_simple(self):
        sample = "(IP-MAT (NP-SBJ (NPR Pedro)) (VB-D comeu) (NP-ACC (D a) (N maca)))"
        tree = deserialize_tree(sample)
        self.assertIsNotNone(tree)
        self.assertEqual(tree.label(), "IP-MAT")
        self.assertEqual(len(tree), 3)
        
        serialized = serialize_tree(tree)
        tree2 = deserialize_tree(serialized)
        self.assertIsNotNone(tree2)
        self.assertEqual(tree, tree2)
        
    def test_extract_id(self):
        sample = "( (IP-MAT (NP-SBJ *pro*) (VB chegou))\n  (ID A_001_PSD,03.1))"
        sent_id = extract_sent_id(sample)
        self.assertEqual(sent_id, "A_001_PSD,03.1")
        tree = deserialize_tree(sample)
        self.assertIsNotNone(tree)
        self.assertEqual(tree.label(), "IP-MAT")


if __name__ == "__main__":
    unittest.main()
