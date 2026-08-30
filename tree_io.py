"""
tree_io.py
==========
Módulo de E/S de Árvores Sintáticas (Motores 1 e 5 do Protocolo Cartográfico).

Responsável por:
  • Deserializar blocos de texto (.psd) em estruturas de árvore NLTK (ParentedTree / Tree).
  • Serializar árvores sintáticas em S-expressions formatadas (estilo Penn Treebank).
  • Validar a integridade estrutural e parênteses.
  • Extrair blocos de sentenças de arquivos brutos do Corpus Tycho Brahe.
"""

import re
from typing import List, Optional, Union
from nltk.tree import ParentedTree, Tree


def limpar_indices_coref(block: str) -> str:
    """
    Remove índices de co-referência superficiais de rótulos não-terminais (ex: NP-SBJ-1 -> NP-SBJ)
    mantendo traços e categorias vazias como *pro*, *T*-1, etc.
    """
    return re.sub(r"(\b[A-Z][A-Z0-9$@\-]+)-\d+\b(?!\*)", r"\1", block)


def limpar_bloco_psd(block: str) -> str:
    """
    Higieniza um bloco de texto PSD bruto do Tycho Brahe:
      - Remove nós de metadados externos (ID ...)
      - Remove delimitadores duplos de topo (( ... ))
    """
    block = re.sub(r"\(ID [^\)]+\)", "", block).strip()
    if block.startswith("( (") and block.endswith(")"):
        block = block[2:-1].strip()
    return block


def deserialize_tree(block: str, strip_coref: bool = False) -> Optional[ParentedTree]:
    """
    Converte uma string de S-expression em uma ParentedTree do NLTK.
    Retorna None se a árvore for inválida ou não puder ser parseada.
    """
    if not block or not block.strip():
        return None
    
    cleaned = limpar_bloco_psd(block)
    if strip_coref:
        cleaned = limpar_indices_coref(cleaned)
        
    try:
        return ParentedTree.fromstring(cleaned)
    except Exception:
        # Fallback para Tree padrão se ParentedTree falhar por algum edge case
        try:
            standard_tree = Tree.fromstring(cleaned)
            return ParentedTree.convert(standard_tree)
        except Exception:
            return None


def serialize_tree(tree: Union[Tree, ParentedTree], indent: int = 0, step: int = 2) -> str:
    """
    Serializa uma árvore NLTK de volta para string S-expression (.psd)
    com indentação hierárquica legível e consistente.
    """
    if isinstance(tree, str):
        return tree

    label = tree.label() if hasattr(tree, "label") else str(tree)
    
    # Se for nó pré-terminal (folha com uma palavra)
    if len(tree) == 1 and isinstance(tree[0], str):
        return f"({label} {tree[0]})"
    
    # Se contiver filhos complexos
    spaces = " " * indent
    child_spaces = " " * (indent + step)
    
    children_strs = []
    for child in tree:
        if isinstance(child, str):
            children_strs.append(child)
        else:
            children_strs.append(serialize_tree(child, indent=indent + step, step=step))
            
    if all(isinstance(child, (Tree, ParentedTree)) and len(child) == 1 and isinstance(child[0], str) for child in tree) and len(tree) <= 3:
        # Sintagmas curtos podem ser compactados em uma linha
        inner = " ".join(children_strs)
        return f"({label} {inner})"
    
    inner = f"\n{child_spaces}".join(children_strs)
    return f"({label}\n{child_spaces}{inner})"


def format_psd_file_entry(tree: Union[Tree, ParentedTree], sent_id: str = "") -> str:
    """
    Formata uma árvore para gravação em arquivo físico .psd com wrapper duplo e metadados ID.
    """
    tree_str = serialize_tree(tree, indent=2, step=2)
    id_line = f"  (ID {sent_id})\n" if sent_id else ""
    return f"( (\n{tree_str}\n{id_line}))\n\n"


def extract_blocks(filepath: str) -> List[str]:
    """
    Lê um arquivo .psd do Tycho Brahe e separa os blocos de sentenças válidos.
    """
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    
    blocos = [b.strip() for b in content.split("\n\n") if b.strip()]
    return [b for b in blocos if b.startswith("(") and ("(IP-" in b or "(CP-" in b)]


def extract_sent_id(block: str) -> str:
    """
    Extrai o ID da sentença se presente no bloco, ex: 'A_001_PSD,03.1'.
    """
    match = re.search(r"\(ID\s+([^\)]+)\)", block)
    return match.group(1).strip() if match else ""
