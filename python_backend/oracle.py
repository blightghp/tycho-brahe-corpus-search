"""
oracle.py
=========
Motor 2 – Classificador Léxico-Semântico e Topológico (O Oráculo Cartográfico Universal).

Mapeia evidências léxicas, morfológicas e estruturais no português (Corpus Tycho Brahe)
para a hierarquia cartográfica universal estrita de 5 Domínios:
  1. Domínio do Ato de Fala (Speas & Tenny 2003, Hill 2007): SAP, VocP, EvalP/AttP
  2. Domínio Complementizador (Rizzi 1997, 2004): ForceP, TopP, IntP, FocP, ModP, QembP, FinP
  3. Domínio Flexional (Cinque 1999): 23 Projeções Funcionais de Modo, Tempo e Aspecto
  4. Baixa Periferia Esquerda (Belletti 2004): TopP_low, FocP_low (Sujeito Pós-Verbal)
  5. Domínio Temático e Argumental (Ramchand 2008, Pylkkänen 2008, Harley 2013):
     VoiceP_agent, InitP, ApplP_high, ProcP, ApplP_low, ResP, √Root
"""

import re
from typing import Dict, List, Optional, Tuple, Set, NamedTuple, Any
from nltk.tree import ParentedTree, Tree

from cartografia_schema import (
    HIERARQUIA_CARTOGRAFICA_COMPLETA,
    PROJECOES_MAP,
    PROJECOES_RANKS
)

# ── Léxico Extensivo de Advérbios e Marcadores do Português Histórico ──────────
ADVERB_CINQUE_LEXICON: Dict[str, str] = {
    # ── Domínio 1 & 3: Speech Act & Evaluative ───────────────────────────────
    "francamente": "MoodP_speech_act",
    "honestamente": "MoodP_speech_act",
    "sinceramente": "MoodP_speech_act",
    "verdadeiramente": "MoodP_speech_act",
    "em verdade": "MoodP_speech_act",

    "felizmente": "MoodP_evaluative",
    "infelizmente": "MoodP_evaluative",
    "lamentavelmente": "MoodP_evaluative",
    "desgraçadamente": "MoodP_evaluative",
    "afortunadamente": "MoodP_evaluative",
    "curiosamente": "MoodP_evaluative",
    "louvado seja deus": "MoodP_evaluative",
    "graças a deus": "MoodP_evaluative",

    # ── Evidencial ───────────────────────────────────────────────────────────
    "evidentemente": "MoodP_evidential",
    "claramente": "MoodP_evidential",
    "aparentemente": "MoodP_evidential",
    "visivelmente": "MoodP_evidential",
    "notoriamente": "MoodP_evidential",
    "manifestamente": "MoodP_evidential",
    "ao que parece": "MoodP_evidential",

    # ── Epistêmico ───────────────────────────────────────────────────────────
    "provavelmente": "ModP_epistemic",
    "talvez": "ModP_epistemic",
    "quiçá": "ModP_epistemic",
    "quiça": "ModP_epistemic",
    "porventura": "ModP_epistemic",
    "possivelmente": "ModP_epistemic",
    "por certo": "ModP_epistemic",
    "com certeza": "ModP_epistemic",

    # ── Tempo Absoluto (T_Past / T_Future) ───────────────────────────────────
    "outrora": "T_past_future",
    "dantes": "T_past_future",
    "antigamente": "T_past_future",
    "ontem": "T_past_future",
    "então": "T_past_future",
    "entao": "T_past_future",
    "amanhã": "T_past_future",
    "amanha": "T_past_future",
    "depois": "T_past_future",
    "logo": "T_past_future",

    # ── Irrealis ─────────────────────────────────────────────────────────────
    "acaso": "MoodP_irrealis",
    "oxalá": "MoodP_irrealis",
    "oxala": "MoodP_irrealis",

    # ── Necessidade & Obrigação ──────────────────────────────────────────────
    "necessariamente": "ModP_necessity",
    "forçosamente": "ModP_necessity",
    "impreterivelmente": "ModP_necessity",
    "obrigatoriamente": "ModP_obligation",
    "por obrigação": "ModP_obligation",

    # ── Volitivo ─────────────────────────────────────────────────────────────
    "voluntariamente": "ModP_volitional",
    "deliberadamente": "ModP_volitional",
    "intencionalmente": "ModP_volitional",
    "de propósito": "ModP_volitional",

    # ── Aspecto Habitual ─────────────────────────────────────────────────────
    "habitualmente": "AspP_habitual",
    "costumadamente": "AspP_habitual",
    "ordinariamente": "AspP_habitual",
    "comumente": "AspP_habitual",
    "geralmente": "AspP_habitual",
    "em geral": "AspP_habitual",

    # ── Tempo Relativo / Anterioridade (T_Anterior) ──────────────────────────
    "já": "T_anterior",
    "ja": "T_anterior",
    "antes": "T_anterior",

    # ── Aspecto Terminativo & Continuativo ───────────────────────────────────
    "não mais": "AspP_terminative",
    "nao mais": "AspP_terminative",
    "ainda": "AspP_continuative",
    "todavia": "AspP_continuative",
    "sempre": "AspP_continuative",

    # ── Aspecto Retrospectivo, Proximativo e Durativo ────────────────────────
    "recentemente": "AspP_retrospective",
    "ultimamente": "AspP_retrospective",
    "há pouco": "AspP_retrospective",
    "ha pouco": "AspP_retrospective",
    "recém": "AspP_retrospective",
    "recem": "AspP_retrospective",
    "quase": "AspP_proximative",
    "prestes": "AspP_proximative",
    "longamente": "AspP_durative",
    "brevemente": "AspP_durative",
    "demoradamente": "AspP_durative",

    # ── Aspecto Celerativo / Velocidade ───────────────────────────────────────
    "rapidamente": "AspP_proximative",
    "depressa": "AspP_proximative",
    "velozmente": "AspP_proximative",
    "prontamente": "AspP_proximative",

    # ── Aspecto Completivo ───────────────────────────────────────────────────
    "completamente": "AspP_completive",
    "inteiramente": "AspP_completive",
    "totalmente": "AspP_completive",
    "de todo": "AspP_completive",
}


class EvidenciaCartografica(NamedTuple):
    dominio: int
    projecao: str
    rank: int
    trigger_word: str
    tree_path: Tuple[int, ...]
    node_label: str
    detalhes: Dict[str, Any]


class AnalisePeriferiaCompleta(NamedTuple):
    # Domínio 1: Ato de Fala
    has_speech_act: bool
    vocative_nodes: List[Tree]
    evaluative_nodes: List[Tree]
    
    # Domínio 2: Split-CP
    force_type: str        # DECLARATIVA, INTERROGATIVA, EXCLAMATIVA, IMPERATIVA
    shift_topics: List[Tree]
    int_nodes: List[Tree]
    familiar_topics: List[Tree]
    focus_nodes: List[Tree]
    modifier_nodes: List[Tree]
    qemb_nodes: List[Tree]
    fin_type: str          # FINITA vs NAO_FINITA


class AnaliseFirstPhasevP(NamedTuple):
    # Domínio 5: Split-vP First Phase
    agent_node: Optional[Tree]      # VoiceP_agent (Argumento Externo / Sujeito Agente)
    initiator_node: Optional[Tree]  # InitP (Causador)
    high_appl_node: Optional[Tree]  # ApplP_high (Beneficiário / Dativo Ético)
    proc_node: Optional[Tree]       # ProcP (Núcleo do Verbo Lexical)
    low_appl_node: Optional[Tree]   # ApplP_low (Meta / Objeto Indireto)
    result_node: Optional[Tree]     # ResP (Resultado / Partícula Télica)
    root_theme_node: Optional[Tree] # √Root + Tema (Argumento Interno Direto)


def classificar_adverbio_cinque(token: str, lemma: Optional[str] = None) -> Optional[str]:
    """Classifica um advérbio ou lema na hierarquia funcional de Cinque."""
    t = token.lower().strip()
    if t in ADVERB_CINQUE_LEXICON:
        return ADVERB_CINQUE_LEXICON[t]
    if lemma:
        l = lemma.lower().strip()
        if l in ADVERB_CINQUE_LEXICON:
            return ADVERB_CINQUE_LEXICON[l]
    return None


def extrair_evidencias_dominio1_e_3(tree: ParentedTree) -> List[EvidenciaCartografica]:
    """
    Varre a árvore em busca de nós funcionais do Domínio 1 (Ato de Fala) e Domínio 3 (Split-IP).
    """
    evidencias = []
    caminhos_processados = set()

    for subtree in tree.subtrees():
        if not hasattr(subtree, "label"):
            continue
        path = subtree.treeposition()
        if any(path[:len(p)] == p for p in caminhos_processados):
            continue

        label = subtree.label()

        # Domínio 1: Vocativos (VocP)
        if label.startswith("NP-VOC") or label.startswith("VOC"):
            caminhos_processados.add(path)
            evidencias.append(EvidenciaCartografica(
                dominio=1,
                projecao="VocP",
                rank=PROJECOES_RANKS.get("VocP", 2),
                trigger_word=" ".join(subtree.leaves()),
                tree_path=path,
                node_label=label,
                detalhes={"tipo": "vocativo"}
            ))
            continue

        # Domínio 3: Advérbios funcionais
        if label.startswith("ADVP") or label.startswith("ADV"):
            words = subtree.leaves()
            phrase = " ".join(words).lower()
            proj = classificar_adverbio_cinque(phrase)
            matched = phrase

            if not proj:
                for w in words:
                    proj = classificar_adverbio_cinque(w)
                    if proj:
                        matched = w
                        break

            if proj:
                caminhos_processados.add(path)
                rank = PROJECOES_RANKS.get(proj, 99)
                dom = 3
                evidencias.append(EvidenciaCartografica(
                    dominio=dom,
                    projecao=proj,
                    rank=rank,
                    trigger_word=matched,
                    tree_path=path,
                    node_label=label,
                    detalhes={"adverbio": matched}
                ))

    return evidencias


def diagnosticar_periferia_completa(cp_tree: ParentedTree) -> AnalisePeriferiaCompleta:
    """
    Diagnostica minuciosamente os Domínios 1 e 2 na periferia esquerda da sentença.
    """
    cp_label = cp_tree.label()
    vocatives = []
    evaluatives = []
    shift_topics = []
    int_nodes = []
    familiar_topics = []
    focus_nodes = []
    modifiers = []
    qemb_nodes = []

    force_type = "DECLARATIVA"
    if "QUE" in cp_label or "INTERROG" in cp_label:
        force_type = "INTERROGATIVA"
    elif "EXC" in cp_label:
        force_type = "EXCLAMATIVA"
    elif "IMP" in cp_label:
        force_type = "IMPERATIVA"

    for child in cp_tree:
        if not isinstance(child, (Tree, ParentedTree)):
            continue
        lbl = child.label()

        # Domínio 1: Vocativo e Avaliação
        if lbl.startswith("NP-VOC") or lbl.startswith("VOC"):
            vocatives.append(child)
        elif lbl.startswith("ADVP-EVAL") or lbl.startswith("CP-EVAL"):
            evaluatives.append(child)

        # Domínio 2: Operadores Wh / Foco
        elif lbl.startswith("WNP") or lbl.startswith("WPP") or lbl.startswith("WADVP"):
            if force_type == "INTERROGATIVA" and ("EMB" in cp_label or "SUB" in cp_label):
                qemb_nodes.append(child)
            else:
                focus_nodes.append(child)

        # Interrogativo estrutural puro (ex: 'se')
        elif lbl == "C" and any(w.lower() in ("se", "si") for w in child.leaves()):
            int_nodes.append(child)

        # Tópicos
        elif lbl.startswith("NP-TOP") or lbl.startswith("PP-TOP"):
            shift_topics.append(child)
        elif lbl.startswith("NP-FAM") or lbl.startswith("PP-FAM"):
            familiar_topics.append(child)

        # Modificadores
        elif lbl.startswith("ADVP-MOD") or lbl.startswith("PP-MOD"):
            modifiers.append(child)

    fin_type = "FINITA"
    for st in cp_tree.subtrees():
        if st.label().startswith("IP-INF") or st.label().startswith("IP-GER") or st.label().startswith("IP-PPL"):
            fin_type = "NAO_FINITA"
            break

    return AnalisePeriferiaCompleta(
        has_speech_act=True,
        vocative_nodes=vocatives,
        evaluative_nodes=evaluatives,
        force_type=force_type,
        shift_topics=shift_topics,
        int_nodes=int_nodes,
        familiar_topics=familiar_topics,
        focus_nodes=focus_nodes,
        modifier_nodes=modifiers,
        qemb_nodes=qemb_nodes,
        fin_type=fin_type
    )


def diagnosticar_baixa_periferia_e_vP(ip_tree: ParentedTree) -> Tuple[List[Tree], Optional[Tree], AnaliseFirstPhasevP]:
    """
    Diagnostica o Domínio 4 (Baixa Periferia Belletti) e Domínio 5 (Split-vP Ramchand/Harley).
    Retorna (low_topics, low_focus_sujeito_posposto, first_phase_vp).
    """
    low_topics = []
    low_focus = None
    agent = None
    initiator = None
    high_appl = None
    proc = None
    low_appl = None
    res = None
    root_theme = None

    encontrou_verbo = False

    for child in ip_tree:
        if not isinstance(child, (Tree, ParentedTree)):
            continue
        lbl = child.label()

        if lbl.startswith("V") or lbl.startswith("HV") or lbl.startswith("ET") or lbl.startswith("TR"):
            encontrou_verbo = True
            proc = child
            continue

        # Sujeito posposto (Domínio 4: FocP_low - Belletti 2004)
        if encontrou_verbo and lbl.startswith("NP-SBJ"):
            low_focus = child
            continue

        # Sujeito pré-verbal agente (Domínio 5: VoiceP_agent)
        if not encontrou_verbo and lbl.startswith("NP-SBJ"):
            agent = child
            continue

        # Objeto indireto / Meta / Aplicativo Baixo (Domínio 5: ApplP_low)
        if lbl.startswith("PP-DAT") or lbl.startswith("NP-DAT") or (lbl.startswith("PP") and any(w.lower() in ("a", "ao", "aos", "para") for w in child.leaves())):
            low_appl = child
            continue

        # Objeto direto / Tema (Domínio 5: √Root)
        if lbl.startswith("NP-ACC") or lbl.startswith("NP"):
            root_theme = child
            continue

    first_phase = AnaliseFirstPhasevP(
        agent_node=agent,
        initiator_node=initiator,
        high_appl_node=high_appl,
        proc=proc,
        low_appl_node=low_appl,
        result_node=res,
        root_theme_node=root_theme
    )

    return low_topics, low_focus, first_phase


def validar_ordem_cinque(evidencias: List[Any]) -> Tuple[bool, Optional[str]]:
    """Verifica se a ordem linear dos advérbios respeita os ranks estritos de Cinque."""
    ev_d3 = [e for e in evidencias if getattr(e, "dominio", 3) == 3]
    for i in range(len(ev_d3) - 1):
        if ev_d3[i].rank > ev_d3[i+1].rank:
            motivo = f"Violação de Ordem Cinque: '{ev_d3[i].trigger_word}' precede '{ev_d3[i+1].trigger_word}'"
            return False, motivo
    return True, None


# Aliases para retrocompatibilidade
extrair_evidencias_cinque = extrair_evidencias_dominio1_e_3
analisar_periferia_rizzi = diagnosticar_periferia_completa

