"""
tokenizador_cartografico.py
===========================
Motor de Tokenização e Etiquetação Termo a Termo com Anotação Cartográfica Gerativa.

Classifica cada constituinte e token da sentença na sequência universal estrita
de 5 Grandes Domínios da Gramática Gerativa (Rizzi, Cinque, Belletti, Ramchand):
  1. Domínio do Ato de Fala (SAP, VocP, EvalP/AttP)
  2. Domínio Complementizador (ForceP, TopP, IntP, FocP, ModP, QembP, FinP)
  3. Domínio Flexional (Split-IP de Cinque)
  4. Baixa Periferia Esquerda (Belletti - TopP_low, FocP_low)
  5. Domínio Temático e Argumental (Split-vP - VoiceP_agent, InitP, ApplP_high, ProcP, ApplP_low, ResP, √Root)
"""

import os
import sys
import re
import json
import argparse
from typing import Dict, Any, List, Optional, Tuple
from nltk.tree import ParentedTree, Tree
import spacy

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from cartografia_schema import (
    HIERARQUIA_CARTOGRAFICA_COMPLETA,
    PROJECOES_MAP,
    PROJECOES_RANKS
)
from oracle import (
    classificar_adverbio_cinque,
    diagnosticar_periferia_completa,
    diagnosticar_baixa_periferia_e_vP,
    ADVERB_CINQUE_LEXICON
)
from rewriter import transmutar_arvore_completa
from tree_io import deserialize_tree, serialize_tree

# Carrega spaCy para POS e Lematização
_nlp = None

def get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("pt_core_news_sm")
    return _nlp


class TokenCartografico(dict):
    """Representa um token com sua respectiva etiquetação cartográfica e funcional."""
    def __init__(
        self,
        indice: int,
        termo: str,
        lema: str,
        pos: str,
        dominio_id: int,
        dominio_nome: str,
        projecao: str,
        papel_gerativo: str,
        eh_cartografico: bool,
        trilha_arvore: Optional[str] = None
    ):
        super().__init__(
            indice=indice,
            termo=termo,
            lema=lema,
            pos=pos,
            dominio_id=dominio_id,
            dominio_nome=dominio_nome,
            projecao=projecao,
            papel_gerativo=papel_gerativo,
            eh_cartografico=eh_cartografico,
            trilha_arvore=trilha_arvore or ""
        )


def etiquetar_token_individual(
    termo: str,
    lema: str,
    pos: str,
    parent_labels: List[str]
) -> Tuple[int, str, str, str, bool]:
    """
    Classifica um constituinte/folha de forma precisa, sem contaminação por nós ancestrais distantes.
    Prioridade:
      1. Função local do constituinte imediato (NP-VOC, NP-SBJ, PP-DAT, V, ADV funcional).
      2. Nó funcional direto pai (FocP, TopP, ForceP, T_anterior, etc.).
      3. Classificação lexical via léxico estendido de Cinque.
      4. Papéis temáticos da Primeira Fase (Split-vP).
    """
    t_lower = termo.lower().strip()
    l_lower = lema.lower().strip()

    # ── 1. DOMÍNIO 1: ATO DE FALA ────────────────────────────────────────────
    if any("VOC" in pl for pl in parent_labels) or t_lower in ("ó", "senhor", "ó senhor"):
        return (1, "Ato de Fala", "VocP", "Vocativo / Chamamento Direto", True)

    proj_adv = classificar_adverbio_cinque(t_lower, l_lower)
    if proj_adv in ("MoodP_speech_act", "MoodP_evaluative"):
        desc = PROJECOES_MAP.get(proj_adv, (None, 1, "", 0, False, "Modo de Avaliação do Falante"))[5]
        return (1, "Ato de Fala", proj_adv, desc, True)

    # ── 2. DOMÍNIO 2: SPLIT-CP (Periferia Esquerda) ───────────────────────────
    if any("WNP" in pl or "WPP" in pl or "WADVP" in pl for pl in parent_labels):
        return (2, "Split-CP", "FocP", "Operador Wh / Foco Contrastivo", True)

    if t_lower in ("se", "si") and any("C" == pl or pl.startswith("C-") for pl in parent_labels):
        return (2, "Split-CP", "IntP", "Elemento Interrogativo Estrutural", True)

    if any(pl.startswith("TopP") for pl in parent_labels[:3]):
        return (2, "Split-CP", "TopP", "Tópico Deslocado à Esquerda", True)

    if any(pl == "C" or pl.startswith("C-") for pl in parent_labels):
        return (2, "Split-CP", "FinP", "Complementizador de Finitude", True)

    # ── 3. DOMÍNIO 3: SPLIT-IP (Hierarquia de Cinque) ─────────────────────────
    if (pos.startswith("ADV") or any("ADV" in pl for pl in parent_labels[:2])) and proj_adv:
        p_info = PROJECOES_MAP.get(proj_adv)
        if p_info:
            return (3, "Split-IP", p_info.nome, p_info.descricao, True)

    # ── 4. DOMÍNIO 4: BAIXA PERIFERIA ESQUERDA (Belletti) ────────────────────
    if any("FocP_low" in pl for pl in parent_labels[:3]):
        return (4, "Baixa Periferia", "FocP_low", "Foco Baixo / Sujeito Pós-Verbal", True)

    # ── 5. DOMÍNIO 5: SPLIT-vP (First Phase Syntax - Ramchand/Harley) ─────────
    # Sujeito Agente (Argumento Externo)
    if any("NP-SBJ" in pl for pl in parent_labels):
        return (5, "Split-vP", "VoiceP_agent", "Argumento Externo (Agente / Sujeito)", True)

    # Objeto Indireto / Meta / Aplicativo
    if any("PP-DAT" in pl or "NP-DAT" in pl or "ApplP_low" in pl for pl in parent_labels):
        return (5, "Split-vP", "ApplP_low", "Aplicativo Baixo (Meta / Objeto Indireto)", True)

    # Objeto Direto / Tema / Raiz Lexical
    if any("NP-ACC" in pl or "Root" in pl for pl in parent_labels):
        return (5, "Split-vP", "Root", "Raiz Lexical Root (Tema / Argumento Interno)", True)

    # Processo Dinâmico (Verbo)
    if pos.startswith("V") or any(pl.startswith("V") or pl.startswith("HV") or pl.startswith("ET") or pl.startswith("TR") for pl in parent_labels[:2]):
        return (5, "Split-vP", "ProcP", "Processo Dinâmico / Núcleo Verbal", True)

    # Preposições e determinantes funcionais
    if pos in ("ADP", "DET", "PRON"):
        return (5, "Split-vP", "Func_Lexical", f"Elemento Funcional ({pos})", False)

    # Padrão
    return (5, "Split-vP", "Constituinte_Base", "Constituinte Temático Geral", False)


def tokenizar_e_etiquetar_arvore(tree: Tree) -> List[TokenCartografico]:
    """
    Varre termo a termo as folhas da árvore e gera o mapeamento cartográfico detalhado.
    """
    nlp = get_nlp()
    tokens_cartograficos: List[TokenCartografico] = []
    
    parented = ParentedTree.convert(tree) if not isinstance(tree, ParentedTree) else tree

    folhas_com_pos = []
    for leaf_pos in parented.treepositions("leaves"):
        leaf = parented[leaf_pos]
        if not isinstance(leaf, str):
            continue

        # Coleta rótulos da linhagem de pais (do mais próximo para o mais distante)
        parents = []
        curr = parented[leaf_pos[:-1]]
        while curr is not None:
            if hasattr(curr, "label"):
                parents.append(curr.label())
            curr = curr.parent()

        folhas_com_pos.append((leaf, parents, "/".join(parents)))

    if not folhas_com_pos:
        return []

    palavras = [f[0] for f in folhas_com_pos]
    doc = nlp(" ".join(palavras))

    for i, (termo, parents, trilha) in enumerate(folhas_com_pos):
        spacy_tok = doc[i] if i < len(doc) else None
        lema = spacy_tok.lemma_ if spacy_tok else termo
        pos = spacy_tok.pos_ if spacy_tok else "NOUN"

        dom_id, dom_nome, proj, papel, eh_carto = etiquetar_token_individual(
            termo=termo,
            lema=lema,
            pos=pos,
            parent_labels=parents
        )

        tokens_cartograficos.append(TokenCartografico(
            indice=i + 1,
            termo=termo,
            lema=lema,
            pos=pos,
            dominio_id=dom_id,
            dominio_nome=dom_nome,
            projecao=proj,
            papel_gerativo=papel,
            eh_cartografico=eh_carto,
            trilha_arvore=trilha
        ))

    return tokens_cartograficos


def processar_sentenca_texto(texto_ou_arvore: str) -> Dict[str, Any]:
    """
    Processa uma string de árvore bracketed ou sentença pura e retorna o relatório termo a termo.
    """
    if texto_ou_arvore.strip().startswith("(") and texto_ou_arvore.strip().endswith(")"):
        tree = deserialize_tree(texto_ou_arvore)
    else:
        nlp = get_nlp()
        doc = nlp(texto_ou_arvore)
        tree = Tree("IP", [Tree(tok.pos_, [tok.text]) for tok in doc])

    tree_expandida, projecoes = transmutar_arvore_completa(tree)
    tokens_etiquetados = tokenizar_e_etiquetar_arvore(tree_expandida)

    return {
        "arvore_original": serialize_tree(tree),
        "arvore_cartografica": serialize_tree(tree_expandida),
        "projecoes_injetadas": projecoes,
        "total_tokens": len(tokens_etiquetados),
        "tokens": [dict(t) for t in tokens_etiquetados]
    }


def formatar_tabela_tokens(tokens: List[Dict[str, Any]]) -> str:
    """Formata a saída de tokens em tabela ASCII alinhada."""
    linhas = []
    cabecalho = f"{'#':<3} | {'Termo':<15} | {'Lema':<15} | {'POS':<6} | {'Dom':<3} | {'Projeção':<18} | {'Papel Gerativo':<40}"
    linhas.append("=" * len(cabecalho))
    linhas.append(cabecalho)
    linhas.append("-" * len(cabecalho))

    for t in tokens:
        linha = (
            f"{t['indice']:<3} | "
            f"{t['termo'][:15]:<15} | "
            f"{t['lema'][:15]:<15} | "
            f"{t['pos'][:6]:<6} | "
            f"D{t['dominio_id']} | "
            f"{t['projecao'][:18]:<18} | "
            f"{t['papel_gerativo'][:40]:<40}"
        )
        linhas.append(linha)

    linhas.append("=" * len(cabecalho))
    return "\n".join(linhas)


def main():
    parser = argparse.ArgumentParser(description="Tokenizador e Etiquetador Cartográfico Universal")
    parser.add_argument("--frase", help="Sentença ou árvore bracketed entre aspas para analisar")
    parser.add_argument("--json", action="store_true", help="Emite o resultado estritamente em JSON")
    args = parser.parse_args()

    frase_exemplo = args.frase or "(CP (ForceP (IP (ADVP (ADV felizmente)) (NP-SBJ (N rei)) (ADVP (ADV já)) (VP (V deu) (NP-ACC (N livro)) (PP-DAT (P a) (NP (N rainha)))))))"

    res = processar_sentenca_texto(frase_exemplo)

    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        print("\n" + "=" * 75)
        print("  TOKENIZAÇÃO E ETIQUETAÇÃO CARTOGRÁFICA GERATIVA (5 DOMÍNIOS)")
        print("=" * 75)
        print("Árvore Cartográfica Gerada:")
        print(res["arvore_cartografica"])
        print("\nProjeções Injetadas:", ", ".join(res["projecoes_injetadas"]) if res["projecoes_injetadas"] else "Nenhuma")
        print("\nGrade Termo a Termo:")
        print(formatar_tabela_tokens(res["tokens"]))


if __name__ == "__main__":
    main()
