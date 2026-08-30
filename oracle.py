"""
oracle.py
=========
Motor 2 – Classificador Léxico-Semântico e Topológico (O Oráculo Cartográfico).

Mapeia evidências léxicas e estruturais no português (Corpus Tycho Brahe) para
as projeções funcionais universais de:
  • Rizzi (1997, 2004) – Periferia Esquerda (Split-CP)
  • Cinque (1999, 2002) – Hierarquia Adverbial e Flexional (Split-IP)
"""

from typing import Dict, List, Optional, Tuple, Set, NamedTuple
from nltk.tree import ParentedTree, Tree


# ── Hierarquia de Cinque (Ordem Rígida Universal) ────────────────────────────
# Ranks menores dominam ranks maiores: Rank 1 domina Rank 2, etc.
CINQUE_HIERARCHY: List[Tuple[str, int, str]] = [
    ("MoodP_speech_act",   1,  "Modo Ilocucionário / Ato de Fala"),
    ("MoodP_evaluative",   2,  "Modo Avaliativo"),
    ("MoodP_evidential",   3,  "Modo Evidencial"),
    ("ModP_epistemic",     4,  "Modalidade Epistêmica"),
    ("T_past",             5,  "Tempo Passado"),
    ("T_future",           6,  "Tempo Futuro"),
    ("MoodP_irrealis",     7,  "Modo Irrealis / Dúvida"),
    ("ModP_necessity",     8,  "Modalidade Deôntica de Necessidade"),
    ("ModP_possibility",   9,  "Modalidade Deôntica de Possibilidade"),
    ("AspP_habitual",     10,  "Aspecto Habitual"),
    ("AspP_repetitive",   11,  "Aspecto Repetitivo"),
    ("AspP_frequentative", 12,  "Aspecto Frequentativo"),
    ("ModP_volitional",   13,  "Modalidade Volitiva"),
    ("AspP_celerative",   14,  "Aspecto Celerativo / Velocidade"),
    ("T_anterior",        15,  "Tempo Anterior"),
    ("AspP_terminative",  16,  "Aspecto Terminativo"),
    ("AspP_continuative", 17,  "Aspecto Continuativo"),
    ("AspP_perfect",      18,  "Aspecto Perfeito"),
    ("AspP_retrospective",19,  "Aspecto Retrospectivo"),
    ("AspP_proximative",  20,  "Aspecto Proximativo"),
    ("AspP_durative",     21,  "Aspecto Durativo"),
    ("AspP_generic",      22,  "Aspecto Genérico"),
    ("AspP_prospective",  23,  "Aspecto Prospetivo"),
    ("AspP_completive",   24,  "Aspecto Completivo"),
    ("VoiceP",            25,  "Voz Passiva / Médio-Passiva"),
]

CINQUE_RANK_MAP: Dict[str, int] = {proj: rank for proj, rank, _ in CINQUE_HIERARCHY}


# ── Léxico de Advérbios do Português Ancorados em Cinque ──────────────────────
# Mapeia lemas e palavras para seus respectivos núcleos funcionais
ADVERB_CINQUE_LEXICON: Dict[str, str] = {
    # MoodP_speech_act (Rank 1)
    "francamente": "MoodP_speech_act",
    "honestamente": "MoodP_speech_act",
    "sinceramente": "MoodP_speech_act",
    "verdadeiramente": "MoodP_speech_act",

    # MoodP_evaluative (Rank 2)
    "felizmente": "MoodP_evaluative",
    "infelizmente": "MoodP_evaluative",
    "lamentavelmente": "MoodP_evaluative",
    "desgraçadamente": "MoodP_evaluative",
    "afortunadamente": "MoodP_evaluative",
    "curiosamente": "MoodP_evaluative",

    # MoodP_evidential (Rank 3)
    "evidentemente": "MoodP_evidential",
    "claramente": "MoodP_evidential",
    "aparentemente": "MoodP_evidential",
    "visivelmente": "MoodP_evidential",
    "notoriamente": "MoodP_evidential",
    "manifestamente": "MoodP_evidential",

    # ModP_epistemic (Rank 4)
    "provavelmente": "ModP_epistemic",
    "talvez": "ModP_epistemic",
    "quiçá": "ModP_epistemic",
    "quiça": "ModP_epistemic",
    "porventura": "ModP_epistemic",
    "possivelmente": "ModP_epistemic",

    # T_past (Rank 5)
    "outrora": "T_past",
    "dantes": "T_past",
    "antigamente": "T_past",
    "ontem": "T_past",

    # T_future (Rank 6)
    "amanhã": "T_future",
    "amanha": "T_future",
    "depois": "T_future",
    "logo": "T_future",

    # MoodP_irrealis (Rank 7)
    "acaso": "MoodP_irrealis",

    # ModP_necessity (Rank 8)
    "necessariamente": "ModP_necessity",
    "forçosamente": "ModP_necessity",
    "impreterivelmente": "ModP_necessity",

    # ModP_possibility (Rank 9)
    # possivelmente atua em epistêmico/possibilidade

    # AspP_habitual (Rank 10)
    "habitualmente": "AspP_habitual",
    "costumadamente": "AspP_habitual",
    "ordinariamente": "AspP_habitual",
    "comumente": "AspP_habitual",

    # AspP_repetitive (Rank 11)
    "novamente": "AspP_repetitive",
    "outra vez": "AspP_repetitive",
    "de novo": "AspP_repetitive",

    # AspP_frequentative (Rank 12)
    "frequentemente": "AspP_frequentative",
    "frequentissimamente": "AspP_frequentative",
    "amiúde": "AspP_frequentative",
    "amiude": "AspP_frequentative",
    "amiudadamente": "AspP_frequentative",
    "reiteradamente": "AspP_frequentative",
    "muitas vezes": "AspP_frequentative",

    # ModP_volitional (Rank 13)
    "voluntariamente": "ModP_volitional",
    "deliberadamente": "ModP_volitional",
    "intencionalmente": "ModP_volitional",
    "de propósito": "ModP_volitional",

    # AspP_celerative (Rank 14)
    "rapidamente": "AspP_celerative",
    "depressa": "AspP_celerative",
    "prestes": "AspP_celerative",
    "velozmente": "AspP_celerative",
    "prontamente": "AspP_celerative",
    "ligeiramente": "AspP_celerative",

    # T_anterior (Rank 15)
    "já": "T_anterior",
    "ja": "T_anterior",
    "antes": "T_anterior",

    # AspP_terminative (Rank 16)
    "não mais": "AspP_terminative",
    "nao mais": "AspP_terminative",

    # AspP_continuative (Rank 17)
    "ainda": "AspP_continuative",
    "todavia": "AspP_continuative",

    # AspP_retrospective (Rank 19)
    "recentemente": "AspP_retrospective",
    "ultimamente": "AspP_retrospective",
    "há pouco": "AspP_retrospective",
    "ha pouco": "AspP_retrospective",

    # AspP_proximative (Rank 20)
    "quase": "AspP_proximative",

    # AspP_durative (Rank 21)
    "longamente": "AspP_durative",
    "brevemente": "AspP_durative",
    "demoradamente": "AspP_durative",

    # AspP_generic (Rank 22)
    "geralmente": "AspP_generic",
    "em geral": "AspP_generic",

    # AspP_completive (Rank 24)
    "completamente": "AspP_completive",
    "inteiramente": "AspP_completive",
    "totalmente": "AspP_completive",
    "de todo": "AspP_completive",
}


class CinqueEvidence(NamedTuple):
    projection: str
    rank: int
    trigger_word: str
    tree_path: Tuple[int, ...]
    node_label: str


class RizziEvidence(NamedTuple):
    cp_type: str            # 'CP-ADV', 'CP-REL', 'CP-QUE', 'CP-THT', etc.
    has_wh: bool            # WNP, WPP, WADVP
    wh_node: Optional[Tree]
    topic_nodes: List[Tree]
    focus_nodes: List[Tree]
    fin_type: str           # 'finite' vs 'non-finite'


def classificar_adverbio_cinque(token: str, lemma: Optional[str] = None) -> Optional[str]:
    """Retorna a projeção de Cinque correspondente a um advérbio ou lema."""
    t_clean = token.lower().strip()
    if t_clean in ADVERB_CINQUE_LEXICON:
        return ADVERB_CINQUE_LEXICON[t_clean]
    
    if lemma:
        l_clean = lemma.lower().strip()
        if l_clean in ADVERB_CINQUE_LEXICON:
            return ADVERB_CINQUE_LEXICON[l_clean]
            
    return None


def extrair_evidencias_cinque(tree: ParentedTree) -> List[CinqueEvidence]:
    """
    Varre a árvore em busca de nós que contenham advérbios da hierarquia de Cinque.
    Retorna a lista de evidências encontradas em ordem linear, evitando duplicação
    entre sintagmas e seus nós filhos.
    """
    evidencias = []
    caminhos_processados = set()
    
    for subtree in tree.subtrees():
        if not hasattr(subtree, "label"):
            continue
        path = subtree.treeposition()
        
        # Se este nó é descendente de um nó já classificado, pula para evitar duplicação
        if any(path[:len(p)] == p for p in caminhos_processados):
            continue
            
        label = subtree.label()
        
        # Procura advérbios em ADVP ou nós ADV
        if label.startswith("ADVP") or label.startswith("ADV"):
            words = subtree.leaves()
            phrase = " ".join(words).lower()
            
            # Testa a frase inteira ou palavras isoladas
            proj = classificar_adverbio_cinque(phrase)
            word_match = phrase
            
            if not proj:
                for w in words:
                    proj = classificar_adverbio_cinque(w)
                    if proj:
                        word_match = w
                        break
                        
            if proj:
                caminhos_processados.add(path)
                rank = CINQUE_RANK_MAP.get(proj, 99)
                evidencias.append(CinqueEvidence(
                    projection=proj,
                    rank=rank,
                    trigger_word=word_match,
                    tree_path=path,
                    node_label=label
                ))
                
    return evidencias


def validar_ordem_cinque(evidencias: List[CinqueEvidence]) -> Tuple[bool, Optional[str]]:
    """
    Verifica se a sequência linear de advérbios respeita a ordem rígida universal.
    Se um advérbio de rank maior (mais baixo na árvore) aparecer antes de um de rank menor,
    uma violação de ordem canônica é detectada!
    """
    if len(evidencias) <= 1:
        return True, None
        
    for i in range(len(evidencias) - 1):
        curr = evidencias[i]
        nxt = evidencias[i+1]
        
        # Em ordem canônica linear: advérbios mais altos (menor rank) aparecem antes
        if curr.rank > nxt.rank:
            motivo = (
                f"Violação de Ordem Cinque: '{curr.trigger_word}' ({curr.projection}, rank {curr.rank}) "
                f"precede '{nxt.trigger_word}' ({nxt.projection}, rank {nxt.rank})"
            )
            return False, motivo
            
    return True, None


def analisar_periferia_rizzi(cp_tree: ParentedTree) -> RizziEvidence:
    """
    Analisa um nó CP do Tycho Brahe e diagnostica os componentes da periferia esquerda:
      - ForceP: derivado da função do CP (REL, QUE, ADV, THT, CAR, etc.)
      - FocP: presenças de operadores-Wh (WNP, WPP, WADVP) ou traços *T*
      - TopP: sintagmas deslocados à esquerda antes do sujeito ou separados por pontuação
      - FinP: complementizador (C) ou adjacente ao IP imediatamente embutido
    """
    cp_label = cp_tree.label()
    wh_node = None
    focus_nodes = []
    topic_nodes = []
    
    # Procura filhos imediatos do CP
    for child in cp_tree:
        if not isinstance(child, (Tree, ParentedTree)):
            continue
        lbl = child.label()
        
        # Operador Wh -> Projeção de FocP
        if lbl.startswith("WNP") or lbl.startswith("WPP") or lbl.startswith("WADVP"):
            wh_node = child
            focus_nodes.append(child)
            
        # Tópicos deslocados (geralmente sintagmas pré-IP não-wh marcados com função ou adjunção)
        elif lbl.startswith("NP-TOP") or lbl.startswith("PP-TOP"):
            topic_nodes.append(child)
            
    # Determina finitude
    fin_type = "finite"
    for st in cp_tree.subtrees():
        if st.label().startswith("IP-INF") or st.label().startswith("IP-GER") or st.label().startswith("IP-PPL"):
            fin_type = "non-finite"
            break

    return RizziEvidence(
        cp_type=cp_label,
        has_wh=(wh_node is not None),
        wh_node=wh_node,
        topic_nodes=topic_nodes,
        focus_nodes=focus_nodes,
        fin_type=fin_type
    )
