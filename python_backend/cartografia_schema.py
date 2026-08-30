"""
cartografia_schema.py
=====================
Definição Formal da Hierarquia Universal Cartográfica em 5 Grandes Domínios.

Base Teórica:
  1. Domínio do Ato de Fala: Speas & Tenny (2003), Hill (2007)
  2. Domínio Complementizador (Split-CP): Rizzi (1997, 2004)
  3. Domínio Flexional (Split-IP / TP): Cinque (1999, 2002)
  4. Baixa Periferia Esquerda: Belletti (2004)
  5. Domínio Temático e Argumental (Split-vP): Ramchand (2008), Pylkkänen (2008), Harley (2013)
"""

from typing import Dict, List, Tuple, NamedTuple, Optional


class ProjecaoCartografica(NamedTuple):
    nome: str
    dominio: int            # 1 a 5
    nome_dominio: str
    rank_hierarquia: int    # 1 a N dentro da hierarquia universal
    recursivo: bool
    descricao: str


# ── TABELA UNIVERSAL DAS PROJEÇÕES CARTOGRÁFICAS (DESCENDENTE) ────────────────
HIERARQUIA_CARTOGRAFICA_COMPLETA: List[ProjecaoCartografica] = [
    # ── 1. O DOMÍNIO DO ATO DE FALA (Extrema Periferia Esquerda) ─────────────
    ProjecaoCartografica("SAP", 1, "Ato de Fala", 1, False, "Speech Act Phrase (Codifica relação Falante-Ouvinte)"),
    ProjecaoCartografica("VocP", 1, "Ato de Fala", 2, True, "Vocative Phrase (Ancoragem de vocativos e chamamentos)"),
    ProjecaoCartografica("EvalP", 1, "Ato de Fala", 3, False, "Evaluative/Attitude Phrase (Avaliação global do falante)"),

    # ── 2. O DOMÍNIO COMPLEMENTIZADOR (Split-CP) ─────────────────────────────
    ProjecaoCartografica("ForceP", 2, "Split-CP", 4, False, "Força Ilocucionária (Declarativa, Interrogativa, etc.)"),
    ProjecaoCartografica("TopP_shift", 2, "Split-CP", 5, True, "Tópico Deslocado (Shift Topic / Mudança de assunto)"),
    ProjecaoCartografica("IntP", 2, "Split-CP", 6, False, "Interrogativa Pura (Elementos interrogativos como 'se')"),
    ProjecaoCartografica("TopP_fam", 2, "Split-CP", 7, True, "Tópico Familiar (Retomada de informação conhecida)"),
    ProjecaoCartografica("FocP", 2, "Split-CP", 8, False, "Foco Contrastivo / Informação Nova rígida / Wh"),
    ProjecaoCartografica("ModP_cp", 2, "Split-CP", 9, True, "Modificador (Advérbios pré-postos e adjunções frontais)"),
    ProjecaoCartografica("QembP", 2, "Split-CP", 10, False, "Interrogativa Embutida (Pronomes wh- subordinados)"),
    ProjecaoCartografica("FinP", 2, "Split-CP", 11, False, "Finitude (Interface inferior do CP, finita ou infinitiva)"),

    # ── 3. O DOMÍNIO FLEXIONAL (Split-IP / TP - Cinque 1999) ─────────────────
    ProjecaoCartografica("MoodP_speech_act", 3, "Split-IP", 12, False, "Modo de Ato de Fala (francamente, sinceramente)"),
    ProjecaoCartografica("MoodP_evaluative", 3, "Split-IP", 13, False, "Modo Avaliativo (felizmente, infelizmente)"),
    ProjecaoCartografica("MoodP_evidential", 3, "Split-IP", 14, False, "Modo Evidencial (supostamente, visivelmente)"),
    ProjecaoCartografica("ModP_epistemic", 3, "Split-IP", 15, False, "Modalidade Epistêmica (provavelmente, talvez)"),
    ProjecaoCartografica("T_past_future", 3, "Split-IP", 16, False, "Tempo Absoluto (Passado ou Futuro)"),
    ProjecaoCartografica("MoodP_irrealis", 3, "Split-IP", 17, False, "Modo Irrealis / Dúvida (acaso, quiçá)"),
    ProjecaoCartografica("ModP_necessity", 3, "Split-IP", 18, False, "Modalidade de Necessidade (necessariamente, forçosamente)"),
    ProjecaoCartografica("ModP_possibility", 3, "Split-IP", 19, False, "Modalidade de Possibilidade (possivelmente)"),
    ProjecaoCartografica("ModP_volitional", 3, "Split-IP", 20, False, "Modalidade Volitiva (intencionalmente, de propósito)"),
    ProjecaoCartografica("ModP_obligation", 3, "Split-IP", 21, False, "Modalidade de Obrigação (obrigatoriamente)"),
    ProjecaoCartografica("ModP_ability_permission", 3, "Split-IP", 22, False, "Modalidade de Capacidade / Permissão"),
    ProjecaoCartografica("AspP_habitual", 3, "Split-IP", 23, False, "Aspecto Habitual (geralmente, habitualmente)"),
    ProjecaoCartografica("T_anterior", 3, "Split-IP", 24, False, "Tempo Relativo / Anterioridade (já, antes)"),
    ProjecaoCartografica("AspP_terminative", 3, "Split-IP", 25, False, "Aspecto Terminativo (não mais, cessar de)"),
    ProjecaoCartografica("AspP_continuative", 3, "Split-IP", 26, False, "Aspecto Continuativo (ainda, continuar a)"),
    ProjecaoCartografica("AspP_perfect", 3, "Split-IP", 27, False, "Aspecto Perfeito (ter + particípio / perfeição)"),
    ProjecaoCartografica("AspP_retrospective", 3, "Split-IP", 28, False, "Aspecto Retrospectivo (recém, há pouco)"),
    ProjecaoCartografica("AspP_proximative", 3, "Split-IP", 29, False, "Aspecto Proximativo (logo, quase, prestes a)"),
    ProjecaoCartografica("AspP_durative", 3, "Split-IP", 30, False, "Aspecto Durativo (brevemente, longamente)"),
    ProjecaoCartografica("AspP_progressive", 3, "Split-IP", 31, False, "Aspecto Progressivo (estar + gerúndio)"),
    ProjecaoCartografica("AspP_prospective", 3, "Split-IP", 32, False, "Aspecto Prospetivo (ir + infinitivo / a ponto de)"),
    ProjecaoCartografica("AspP_completive", 3, "Split-IP", 33, False, "Aspecto Completivo (completamente, de todo)"),
    ProjecaoCartografica("VoiceP_flex", 3, "Split-IP", 34, False, "Voz Gramatical Primária"),

    # ── 4. A BAIXA PERIFERIA ESQUERDA (Belletti 2004) ────────────────────────
    ProjecaoCartografica("TopP_low", 4, "Baixa Periferia", 35, True, "Tópico Baixo (Pós-auxiliar)"),
    ProjecaoCartografica("FocP_low", 4, "Baixa Periferia", 36, False, "Foco Baixo / Sujeito Pós-Verbal"),
    ProjecaoCartografica("TopP_low_clitic", 4, "Baixa Periferia", 37, True, "Tópico Baixo Clítico / Marginais"),

    # ── 5. O DOMÍNIO TEMÁTICO E ARGUMENTAL (Split-vP / First Phase) ──────────
    ProjecaoCartografica("VoiceP_agent", 5, "Split-vP", 38, False, "Voz / Agência (Introduz o Agente / Argumento Externo)"),
    ProjecaoCartografica("InitP", 5, "Split-vP", 39, False, "Iniciação (Subevento Causador)"),
    ProjecaoCartografica("ApplP_high", 5, "Split-vP", 40, False, "Aplicativo Alto (Beneficiário / Maleficiário Ético)"),
    ProjecaoCartografica("ProcP", 5, "Split-vP", 41, False, "Processo (Núcleo Dinâmico do Verbo)"),
    ProjecaoCartografica("ApplP_low", 5, "Split-vP", 42, False, "Aplicativo Baixo (Meta de Transferência / Objeto Indireto)"),
    ProjecaoCartografica("ResP", 5, "Split-vP", 43, False, "Resultado (Estado Final / Télico)"),
    ProjecaoCartografica("Root", 5, "Split-vP", 44, False, "√Root (Raiz Lexical Acategorial fundida ao Tema/Paciente)"),
]

PROJECOES_MAP: Dict[str, ProjecaoCartografica] = {p.nome: p for p in HIERARQUIA_CARTOGRAFICA_COMPLETA}
PROJECOES_RANKS: Dict[str, int] = {p.nome: p.rank_hierarquia for p in HIERARQUIA_CARTOGRAFICA_COMPLETA}

# Prefixos e labels canônicos
TODOS_PREFIXOS_CARTOGRAFICOS = tuple(p.nome for p in HIERARQUIA_CARTOGRAFICA_COMPLETA) + (
    "TopP", "MoodP", "ModP", "AspP", "VoiceP", "vP", "T_past", "T_future"
)
