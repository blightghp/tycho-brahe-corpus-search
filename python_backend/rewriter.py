"""
rewriter.py
===========
Motor 3 – Transdutor Algorítmico de Árvores (Tree Rewriter Cartográfico).

Aplica o "Modelo Leque" (Fan Expansion) para transmutar as árvores sintáticas do Corpus
Tycho Brahe nas projeções cartográficas estritas dos 5 Grandes Domínios Universais:
  1. Domínio do Ato de Fala (SAP, VocP, EvalP)
  2. Domínio Complementizador (ForceP, TopP, IntP, FocP, ModP, QembP, FinP)
  3. Domínio Flexional (Cinque 1999 - Split-IP)
  4. Baixa Periferia Esquerda (TopP_low, FocP_low)
  5. Domínio Temático e Argumental (VoiceP_agent, InitP, ApplP_high, ProcP, ApplP_low, ResP, √Root)
"""

from typing import List, Tuple, Optional, Set, Union, Dict, Any
from nltk.tree import ParentedTree, Tree

from cartografia_schema import PROJECOES_RANKS, PROJECOES_MAP
from oracle import (
    extrair_evidencias_dominio1_e_3,
    diagnosticar_baixa_periferia_e_vP,
    EvidenciaCartografica,
    AnaliseFirstPhasevP
)


class CartographicAnomalyError(Exception):
    """Exceção levantada quando a árvore apresenta anomalias sintáticas ou ordem não-canônica."""
    def __init__(self, motivo: str, tipo_anomalia: str, arvore_sugerida: Optional[Tree] = None):
        super().__init__(motivo)
        self.motivo = motivo
        self.tipo_anomalia = tipo_anomalia
        self.arvore_sugerida = arvore_sugerida


def _clone_child(child: Union[str, Tree, ParentedTree]) -> Union[str, Tree]:
    """Clona profundamente um nó para desanexá-lo de ponteiros anteriores."""
    if isinstance(child, (Tree, ParentedTree)):
        return Tree(child.label(), [_clone_child(c) for c in child])
    return str(child)


def expandir_split_cp_completo(cp_node: Union[Tree, ParentedTree]) -> Tuple[Tree, List[str]]:
    """
    Expande um nó CP nos Domínios 1 (Ato de Fala) e 2 (Split-CP de Rizzi).
    Sequência descendente: SAP -> VocP -> EvalP -> ForceP -> TopP -> IntP -> FocP -> ModP -> QembP -> FinP
    """
    cp_label = cp_node.label() if hasattr(cp_node, "label") else "CP"
    projecoes_injetadas: List[str] = []

    vocatives = []
    evaluatives = []
    shift_topics = []
    int_nodes = []
    familiar_topics = []
    focus_nodes = []
    modifiers = []
    qemb_nodes = []
    ip_children = []
    c_children = []
    other_children = []

    force_type = "DECLARATIVA"
    if "QUE" in cp_label or "INTERROG" in cp_label:
        force_type = "INTERROGATIVA"
    elif "EXC" in cp_label:
        force_type = "EXCLAMATIVA"
    elif "IMP" in cp_label:
        force_type = "IMPERATIVA"

    for ch in cp_node:
        cloned = _clone_child(ch)
        if not isinstance(ch, (Tree, ParentedTree)):
            other_children.append(cloned)
            continue

        lbl = ch.label()

        # Domínio 1: Vocativo e Avaliação
        if lbl.startswith("NP-VOC") or lbl.startswith("VOC"):
            vocatives.append(cloned)
        elif lbl.startswith("ADVP-EVAL") or lbl.startswith("CP-EVAL"):
            evaluatives.append(cloned)

        # Domínio 2: Operadores Wh / Foco
        elif lbl.startswith("WNP") or lbl.startswith("WPP") or lbl.startswith("WADVP"):
            if force_type == "INTERROGATIVA" and ("EMB" in cp_label or "SUB" in cp_label):
                qemb_nodes.append(cloned)
            else:
                focus_nodes.append(cloned)

        # Interrogativo estrutural puro (ex: 'se')
        elif lbl == "C" and any(w.lower() in ("se", "si") for w in ch.leaves()):
            int_nodes.append(cloned)

        # Tópicos
        elif lbl.startswith("NP-TOP") or lbl.startswith("PP-TOP"):
            shift_topics.append(cloned)
        elif lbl.startswith("NP-FAM") or lbl.startswith("PP-FAM"):
            familiar_topics.append(cloned)

        # Modificadores
        elif lbl.startswith("ADVP-MOD") or lbl.startswith("PP-MOD"):
            modifiers.append(cloned)

        elif lbl.startswith("IP"):
            ip_children.append(cloned)
        elif lbl == "C" or lbl.startswith("C-"):
            c_children.append(cloned)
        else:
            other_children.append(cloned)

    # Constrói a cascata funcional de baixo para cima (bottom-up):
    # 1. FinP
    fin_children = c_children + ip_children + other_children
    current_head = Tree("FinP", fin_children)
    projecoes_injetadas.append("FinP")

    # 2. QembP (se houver interrogativa embutida)
    if qemb_nodes:
        current_head = Tree("QembP", qemb_nodes + [current_head])
        projecoes_injetadas.append("QembP")

    # 3. ModP (modificadores pré-postos)
    if modifiers:
        current_head = Tree("ModP", modifiers + [current_head])
        projecoes_injetadas.append("ModP")

    # 4. FocP (foco contrastivo ou wh principal)
    if focus_nodes:
        current_head = Tree("FocP", focus_nodes + [current_head])
        projecoes_injetadas.append("FocP")

    # 5. TopP Familiar
    if familiar_topics:
        current_head = Tree("TopP_fam", familiar_topics + [current_head])
        projecoes_injetadas.append("TopP_fam")

    # 6. IntP (interrogativa pura como 'se')
    if int_nodes:
        current_head = Tree("IntP", int_nodes + [current_head])
        projecoes_injetadas.append("IntP")

    # 7. TopP Shift (Tópico Deslocado principal)
    if shift_topics:
        current_head = Tree("TopP", shift_topics + [current_head])
        projecoes_injetadas.append("TopP")

    # 8. ForceP (Força ilocucionária)
    current_head = Tree("ForceP", [current_head])
    projecoes_injetadas.append("ForceP")

    # 9. Domínio 1: EvalP / AttP (se houver avaliação de atitude)
    if evaluatives:
        current_head = Tree("EvalP", evaluatives + [current_head])
        projecoes_injetadas.append("EvalP")

    # 10. Domínio 1: VocP (se houver vocativo de chamamento)
    if vocatives:
        current_head = Tree("VocP", vocatives + [current_head])
        projecoes_injetadas.append("VocP")

    # 11. Domínio 1: SAP (Speech Act Phrase no topo da raiz)
    sap_head = Tree("SAP", [current_head])
    projecoes_injetadas.append("SAP")

    new_cp = Tree(cp_node.label(), [sap_head])
    return new_cp, projecoes_injetadas


def expandir_split_ip_cinque(ip_node: Union[Tree, ParentedTree]) -> Tuple[Tree, List[str]]:
    """
    Expande o Domínio 3 (Hierarquia Flexional de Cinque 1999) sob o nó IP.
    """
    p_node = ParentedTree.convert(ip_node) if not isinstance(ip_node, ParentedTree) else ip_node
    evidencias = extrair_evidencias_dominio1_e_3(p_node)

    ev_d3 = [e for e in evidencias if e.dominio == 3]

    if not ev_d3:
        return _clone_child(ip_node), []

    for i in range(len(ev_d3) - 1):
        if ev_d3[i].rank > ev_d3[i+1].rank:
            raise CartographicAnomalyError(
                motivo=f"Violação da Ordem Universal Cinque: '{ev_d3[i].trigger_word}' precede '{ev_d3[i+1].trigger_word}'",
                tipo_anomalia="HIERARQUIA_CINQUE_VIOLADA"
            )

    projecoes_injetadas = []
    ev_ordenadas = sorted(ev_d3, key=lambda x: x.rank)
    adverb_paths = {ev.tree_path for ev in ev_ordenadas}

    adverb_nodes = []
    core_children = []

    for i, ch in enumerate(ip_node):
        cloned = _clone_child(ch)
        if (i,) in adverb_paths or any(p[0] == i for p in adverb_paths):
            adverb_nodes.append((i, cloned))
        else:
            core_children.append(cloned)

    inner_core = Tree("CoreIP", core_children) if core_children else Tree("VP", [])
    current_layer = inner_core

    for ev in reversed(ev_ordenadas):
        matching_adv = None
        for idx, adv in adverb_nodes:
            if any(ev.trigger_word in l.lower() for l in adv.leaves()):
                matching_adv = adv
                break
        if matching_adv is None and adverb_nodes:
            matching_adv = adverb_nodes[0][1]

        proj_name = ev.projecao
        projecoes_injetadas.insert(0, proj_name)
        layer_children = [matching_adv, current_layer] if matching_adv else [current_layer]
        current_layer = Tree(proj_name, layer_children)

    new_ip = Tree(ip_node.label(), [current_layer])
    return new_ip, projecoes_injetadas


def expandir_split_vp_first_phase(vp_node: Union[Tree, ParentedTree]) -> Tuple[Tree, List[str]]:
    """
    Expande os Domínios 4 (Baixa Periferia) e 5 (Split-vP First Phase):
    VoiceP_agent -> InitP -> ApplP_high -> ProcP -> ApplP_low -> ResP -> Root
    """
    p_node = ParentedTree.convert(vp_node) if not isinstance(vp_node, ParentedTree) else vp_node
    low_topics, low_focus, first_phase = diagnosticar_baixa_periferia_e_vP(p_node)
    projecoes_injetadas: List[str] = []

    root_children = []
    if first_phase.root_theme_node:
        root_children.append(_clone_child(first_phase.root_theme_node))
    current_vp = Tree("Root", root_children) if root_children else Tree("Root", [])
    projecoes_injetadas.append("Root")

    if first_phase.result_node:
        current_vp = Tree("ResP", [_clone_child(first_phase.result_node), current_vp])
        projecoes_injetadas.append("ResP")

    if first_phase.low_appl_node:
        current_vp = Tree("ApplP_low", [_clone_child(first_phase.low_appl_node), current_vp])
        projecoes_injetadas.append("ApplP_low")

    if first_phase.proc_node:
        current_vp = Tree("ProcP", [_clone_child(first_phase.proc_node), current_vp])
        projecoes_injetadas.append("ProcP")

    if first_phase.high_appl_node:
        current_vp = Tree("ApplP_high", [_clone_child(first_phase.high_appl_node), current_vp])
        projecoes_injetadas.append("ApplP_high")

    if first_phase.initiator_node:
        current_vp = Tree("InitP", [_clone_child(first_phase.initiator_node), current_vp])
        projecoes_injetadas.append("InitP")

    if first_phase.agent_node:
        current_vp = Tree("VoiceP_agent", [_clone_child(first_phase.agent_node), current_vp])
        projecoes_injetadas.append("VoiceP_agent")

    if low_focus:
        current_vp = Tree("FocP_low", [_clone_child(low_focus), current_vp])
        projecoes_injetadas.append("FocP_low")

    new_vp = Tree(vp_node.label(), [current_vp])
    return new_vp, projecoes_injetadas


def transmutar_arvore_completa(tree: Union[Tree, ParentedTree]) -> Tuple[Tree, List[str]]:
    """
    Executa a transmutação algorítmica completa de uma árvore sintática abrangendo os 5 Domínios:
      1. Clona a árvore original em Tree pura.
      2. Expande nós CP (Domínios 1 e 2: Ato de Fala e Split-CP).
      3. Expande nós IP (Domínio 3: Split-IP de Cinque).
      4. Expande nós VP / orações temáticas (Domínios 4 e 5: Baixa Periferia e Split-vP).
    """
    tree_pure = _clone_child(tree)
    projecoes_totais = []

    def _transformar_recursivo(node: Tree) -> Tree:
        if not isinstance(node, Tree) or len(node) == 0:
            return node

        label = node.label()

        # Domínio 1 e 2: Split-CP
        if label.startswith("CP") and not any(isinstance(ch, Tree) and (ch.label() == "SAP" or ch.label() == "ForceP") for ch in node):
            try:
                new_cp, injected = expandir_split_cp_completo(node)
                projecoes_totais.extend(injected)
                new_children = [_transformar_recursivo(ch) for ch in new_cp]
                return Tree(new_cp.label(), new_children)
            except Exception as e:
                raise CartographicAnomalyError(
                    motivo=f"Erro no Split-CP (Domínios 1 e 2): {e}",
                    tipo_anomalia="SPLIT_CP_ERRO"
                )

        # Domínio 3: Split-IP
        elif label.startswith("IP") and not any(isinstance(ch, Tree) and ("MoodP" in ch.label() or "ModP" in ch.label() or "AspP" in ch.label() or "CoreIP" in ch.label()) for ch in node):
            try:
                new_ip, injected = expandir_split_ip_cinque(node)
                if injected:
                    projecoes_totais.extend(injected)
                    new_children = [_transformar_recursivo(ch) for ch in new_ip]
                    return Tree(new_ip.label(), new_children)
            except CartographicAnomalyError:
                raise
            except Exception as e:
                raise CartographicAnomalyError(
                    motivo=f"Erro no Split-IP (Domínio 3): {e}",
                    tipo_anomalia="SPLIT_IP_ERRO"
                )

        new_children = [_transformar_recursivo(ch) for ch in node]
        return Tree(node.label(), new_children)

    result_tree = _transformar_recursivo(tree_pure)
    return result_tree, projecoes_totais


# Aliases para retrocompatibilidade
expandir_split_cp = expandir_split_cp_completo
expandir_split_ip = expandir_split_ip_cinque
