"""
rewriter.py
===========
Motor 3 – Transdutor Algorítmico de Árvores (Tree Rewriter).

Aplica o "Modelo Leque" (Fan Expansion) para transmutar as árvores do Corpus
Tycho Brahe nas projeções cartográficas finas de Rizzi (Split-CP) e Cinque (Split-IP),
preservando a compatibilidade integral com a anotação clássica.
"""

from typing import List, Tuple, Optional, Set, Union
from nltk.tree import ParentedTree, Tree

from oracle import (
    CINQUE_RANK_MAP,
    extrair_evidencias_cinque,
    validar_ordem_cinque,
    analisar_periferia_rizzi,
    CinqueEvidence,
    RizziEvidence
)


class CartographicAnomalyError(Exception):
    """Exceção levantada quando a árvore apresenta anomalias sintáticas ou ordem não-canônica."""
    def __init__(self, motivo: str, tipo_anomalia: str, arvore_sugerida: Optional[Tree] = None):
        super().__init__(motivo)
        self.motivo = motivo
        self.tipo_anomalia = tipo_anomalia
        self.arvore_sugerida = arvore_sugerida


def _clone_child(child: Union[str, Tree, ParentedTree]) -> Union[str, Tree]:
    """Clona profundamente um nó para desanexá-lo de ponteiros de pai anteriores."""
    if isinstance(child, (Tree, ParentedTree)):
        # Converte para Tree padrão desanexada
        return Tree(child.label(), [_clone_child(c) for c in child])
    return str(child)


def expandir_split_cp(cp_node: Union[Tree, ParentedTree]) -> Tuple[Tree, List[str]]:
    """
    Expande um nó CP no modelo Split-CP de Rizzi:
      (CP-XYZ ...) -> (CP-XYZ (ForceP (TopP* (FocP (FinP ...)))))
    Retorna a subárvore transformada e a lista de projeções injetadas.
    """
    p_node = ParentedTree.convert(cp_node) if not isinstance(cp_node, ParentedTree) else cp_node
    rizzi_ev = analisar_periferia_rizzi(p_node)
    projecoes_injetadas = []
    
    # Separa complementizadores (C), elementos-wh, tópicos e orações subordinadas (IP)
    wh_children = []
    topic_children = []
    c_children = []
    ip_children = []
    other_children = []
    
    for ch in cp_node:
        cloned = _clone_child(ch)
        if not isinstance(ch, (Tree, ParentedTree)):
            other_children.append(cloned)
            continue
        lbl = ch.label()
        if lbl.startswith("WNP") or lbl.startswith("WPP") or lbl.startswith("WADVP"):
            wh_children.append(cloned)
        elif lbl.startswith("NP-TOP") or lbl.startswith("PP-TOP"):
            topic_children.append(cloned)
        elif lbl == "C" or lbl.startswith("C-"):
            c_children.append(cloned)
        elif lbl.startswith("IP"):
            ip_children.append(cloned)
        else:
            other_children.append(cloned)
            
    # Constrói a cascata de dentro para fora (bottom-up: FinP -> FocP -> TopP -> ForceP)
    
    # 1. FinP (contém complementizador C e/ou a oração IP)
    fin_children = c_children + ip_children + other_children
    fin_p = Tree("FinP", fin_children)
    projecoes_injetadas.append("FinP")
    
    current_head = fin_p
    
    # 2. FocP (se houver operador wh ou foco)
    if wh_children:
        foc_children = wh_children + [current_head]
        current_head = Tree("FocP", foc_children)
        projecoes_injetadas.append("FocP")
        
    # 3. TopP (se houver tópicos deslocados)
    if topic_children:
        top_children = topic_children + [current_head]
        current_head = Tree("TopP", top_children)
        projecoes_injetadas.append("TopP")
        
    # 4. ForceP (topo da periferia esquerda)
    force_p = Tree("ForceP", [current_head])
    projecoes_injetadas.append("ForceP")
    
    # Cria o novo CP preservando o rótulo original ("Modelo Leque")
    new_cp = Tree(cp_node.label(), [force_p])
    return new_cp, projecoes_injetadas


def expandir_split_ip(ip_node: Union[Tree, ParentedTree]) -> Tuple[Tree, List[str]]:
    """
    Expande um nó IP no modelo Split-IP de Cinque:
    Identifica advérbios ancorados, verifica a hierarquia estrita e insere os núcleos funcionais.
    """
    p_node = ParentedTree.convert(ip_node) if not isinstance(ip_node, ParentedTree) else ip_node
    evidencias = extrair_evidencias_cinque(p_node)
    
    if not evidencias:
        # Nenhum advérbio cartográfico encontrado; mantém o IP intacto
        return _clone_child(ip_node), []
        
    # Valida a ordem rígida de Cinque
    valido, motivo = validar_ordem_cinque(evidencias)
    if not valido:
        raise CartographicAnomalyError(
            motivo=motivo or "Violação da ordem universal de Cinque",
            tipo_anomalia="HIERARQUIA_CINQUE_VIOLADA"
        )
        
    projecoes_injetadas = []
    
    # Ordena as evidências por rank (1, 2, 3...)
    evidencias_ordenadas = sorted(evidencias, key=lambda x: x.rank)
    
    # Mapeia quais caminhos pertencem a advérbios
    adverb_paths = {ev.tree_path for ev in evidencias}
    
    # Separa filhos do IP: advérbios vs outros constituintes (sujeito, verbo, objetos, etc.)
    adverb_nodes = []
    core_children = []
    
    for i, ch in enumerate(ip_node):
        cloned = _clone_child(ch)
        if (i,) in adverb_paths or any(p[0] == i for p in adverb_paths):
            adverb_nodes.append((i, cloned))
        else:
            core_children.append(cloned)
            
    # Constrói a cascata funcional de baixo para cima
    inner_core = Tree("CoreIP", core_children) if core_children else Tree("VP", [])
    
    current_layer = inner_core
    for ev in reversed(evidencias_ordenadas):
        # Encontra o nó do advérbio correspondente
        matching_adv = None
        for idx, adv in adverb_nodes:
            if any(ev.trigger_word in l.lower() for l in adv.leaves()):
                matching_adv = adv
                break
        if matching_adv is None and adverb_nodes:
            matching_adv = adverb_nodes[0][1]
            
        proj_name = ev.projection
        projecoes_injetadas.insert(0, proj_name)
        
        layer_children = [matching_adv, current_layer] if matching_adv else [current_layer]
        current_layer = Tree(proj_name, layer_children)
        
    # Insere tudo sob o IP original (Modelo Leque)
    new_ip = Tree(ip_node.label(), [current_layer])
    return new_ip, projecoes_injetadas


def transmutar_arvore_completa(tree: Union[Tree, ParentedTree]) -> Tuple[Tree, List[str]]:
    """
    Executa a transmutação algorítmica completa de uma árvore sintática:
      1. Clona a árvore original em Tree pura.
      2. Expande recursivamente nós CP (Split-CP).
      3. Expande nós IP contendo ancoragem adverbial (Split-IP).
      4. Retorna a árvore transformada e o catálogo de todas as projeções inseridas.
    """
    tree_pure = _clone_child(tree)
    projecoes_totais = []
    
    def _transformar_recursivo(node: Tree) -> Tree:
        if not isinstance(node, Tree) or len(node) == 0:
            return node
            
        label = node.label()
        
        # 1. Split-CP
        if label.startswith("CP") and not any(isinstance(ch, Tree) and ch.label().startswith("ForceP") for ch in node):
            try:
                new_cp, injected = expandir_split_cp(node)
                projecoes_totais.extend(injected)
                # Transforma recursivamente os filhos da nova subárvore
                new_children = [_transformar_recursivo(ch) for ch in new_cp]
                return Tree(new_cp.label(), new_children)
            except Exception as e:
                raise CartographicAnomalyError(
                    motivo=f"Erro no Split-CP: {e}",
                    tipo_anomalia="SPLIT_CP_ERRO"
                )
                
        # 2. Split-IP
        elif label.startswith("IP") and not any(isinstance(ch, Tree) and ("MoodP" in ch.label() or "ModP" in ch.label() or "AspP" in ch.label()) for ch in node):
            try:
                new_ip, injected = expandir_split_ip(node)
                if injected:
                    projecoes_totais.extend(injected)
                    new_children = [_transformar_recursivo(ch) for ch in new_ip]
                    return Tree(new_ip.label(), new_children)
            except CartographicAnomalyError:
                raise
            except Exception as e:
                raise CartographicAnomalyError(
                    motivo=f"Erro no Split-IP: {e}",
                    tipo_anomalia="SPLIT_IP_ERRO"
                )
                
        # Continua recursivamente nos filhos existentes
        new_children = [_transformar_recursivo(ch) for ch in node]
        return Tree(node.label(), new_children)

    result_tree = _transformar_recursivo(tree_pure)
    return result_tree, projecoes_totais
