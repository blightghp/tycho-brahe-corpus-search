"""
build_db_fase3.py
=================
Fase 3 – Compilador do Banco Sintático-Cartográfico com Nested Sets (corpus_fase3.db).

Este script:
  1. Lê as árvores sintáticas expandidas do banco 'corpus_cartografia.db' (ou arquivos físicos).
  2. Lematiza todas as folhas (tokens) em lote via spaCy com cache global.
  3. Mapeia e indexa a árvore cartográfica completa usando coordenadas Nested Sets (lft/rgt),
     marcando explicitamente os nós originais vs nós cartográficos injetados (eh_cartografico).
  4. Cria índices otimizados para consultas hierárquicas em O(log n).
"""

import os
import re
import sqlite3
import json
import glob
from time import time
from typing import Set, Tuple, Optional
from nltk.tree import ParentedTree, Tree
import spacy

from tree_io import deserialize_tree, serialize_tree

DB_CARTOGRAFIA_PATH = "corpus_cartografia.db"
DB_FASE3_PATH = "corpus_fase3.db"
LABEL_EMPTY = re.compile(r"^\*.*\*[\d-]*$|^0$|^\*\w+\*-?\d*$")

CARTOGRAPHIC_PREFIXES = (
    "ForceP", "TopP", "FocP", "FinP", "CoreIP",
    "MoodP", "ModP", "AspP", "VoiceP", "T_past", "T_future", "T_anterior"
)

# ── Carrega spaCy para Lematização em Lote ────────────────────────────────────
print("Carregando modelo spaCy (pt_core_news_sm)...")
nlp = spacy.load("pt_core_news_sm", disable=["parser", "ner"])
_lemma_cache = {}


def lemmatize_token(token_str: str) -> str:
    """Retorna o lema de um token via spaCy (com cache)."""
    if LABEL_EMPTY.match(token_str):
        return token_str
    if token_str in _lemma_cache:
        return _lemma_cache[token_str]
    doc = nlp(token_str)
    lemma = doc[0].lemma_ if doc else token_str
    _lemma_cache[token_str] = lemma
    return lemma


def pre_aquece_lemas_de_arvores(arvores_textos):
    """Extrai todos os tokens únicos e lematiza em batch com nlp.pipe()."""
    print("Pré-computando lemas em batch (spaCy pipe)...")
    tokens_unicos = set()
    for txt in arvores_textos:
        for m in re.findall(r'\(([^ (\n]+)\s+([^ ()\n]+)\)', txt):
            word = m[1]
            if not LABEL_EMPTY.match(word):
                tokens_unicos.add(word)
                
    tokens_list = list(tokens_unicos)
    docs = list(nlp.pipe(tokens_list, batch_size=512))
    for tok_str, doc in zip(tokens_list, docs):
        _lemma_cache[tok_str] = doc[0].lemma_ if doc else tok_str
    print(f"  {len(tokens_list):,} formas únicas lematizadas.")


def parse_label(label: str) -> Tuple[str, Optional[str], int]:
    """
    Divide 'NP-SBJ' em base='NP', funcao='SBJ' e indica se é cartográfico.
    """
    eh_cartografico = int(any(label == p or label.startswith(p + "_") or label.startswith(p + "-") for p in CARTOGRAPHIC_PREFIXES))
    partes = label.split("-", 1)
    base = partes[0]
    funcao = partes[1] if len(partes) > 1 else None
    return base, funcao, eh_cartografico


_counter = [0]


def inserir_arvore(cur, tree: Tree, sentenca_id: int, depth: int = 0, pai_id: Optional[int] = None) -> Tuple[int, int]:
    """Insere recursivamente nós em formato Nested Sets (lft/rgt)."""
    _counter[0] += 1
    lft = _counter[0]

    label = tree.label() if hasattr(tree, "label") else str(tree)
    base, funcao, eh_carto = parse_label(label)

    eh_folha = int(len(tree) == 1 and isinstance(tree[0], str))
    token = tree[0] if eh_folha else None
    lemma = lemmatize_token(token) if token else None

    cur.execute(
        """INSERT INTO tb_nos
           (sentenca_id, label, label_base, funcao, token, lemma,
            eh_folha, eh_cartografico, lft, rgt, depth)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (sentenca_id, label, base, funcao, token, lemma,
         eh_folha, eh_carto, lft, 0, depth)
    )
    node_id = cur.lastrowid

    if pai_id is not None:
        cur.execute("INSERT INTO tb_relacoes VALUES (?,?)", (pai_id, node_id))

    if not eh_folha:
        for subtree in tree:
            if isinstance(subtree, (Tree, ParentedTree)):
                inserir_arvore(cur, subtree, sentenca_id, depth + 1, node_id)

    _counter[0] += 1
    rgt = _counter[0]
    cur.execute("UPDATE tb_nos SET rgt=? WHERE id=?", (rgt, node_id))
    return node_id, rgt


def criar_esquema(cur):
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS tb_sentencas (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            arquivo          TEXT NOT NULL,
            sent_id_externo  TEXT,
            sent_original    TEXT,
            sent_expandida   TEXT,
            status_origem    TEXT NOT NULL DEFAULT 'EXPANDIDA'
        );

        CREATE TABLE IF NOT EXISTS tb_nos (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            sentenca_id      INTEGER NOT NULL,
            label            TEXT NOT NULL,
            label_base       TEXT NOT NULL,
            funcao           TEXT,
            token            TEXT,
            lemma            TEXT,
            eh_folha         INTEGER NOT NULL DEFAULT 0,
            eh_cartografico  INTEGER NOT NULL DEFAULT 0,
            lft              INTEGER NOT NULL,
            rgt              INTEGER NOT NULL,
            depth            INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (sentenca_id) REFERENCES tb_sentencas(id)
        );

        CREATE TABLE IF NOT EXISTS tb_relacoes (
            pai_id           INTEGER NOT NULL,
            filho_id         INTEGER NOT NULL,
            PRIMARY KEY (pai_id, filho_id),
            FOREIGN KEY (pai_id)   REFERENCES tb_nos(id),
            FOREIGN KEY (filho_id) REFERENCES tb_nos(id)
        );
    """)


def criar_indices(cur):
    print("  Criando índices de alta performance...")
    cur.executescript("""
        CREATE INDEX IF NOT EXISTS idx_nos_sent   ON tb_nos(sentenca_id);
        CREATE INDEX IF NOT EXISTS idx_nos_label  ON tb_nos(label);
        CREATE INDEX IF NOT EXISTS idx_nos_base   ON tb_nos(label_base);
        CREATE INDEX IF NOT EXISTS idx_nos_funcao ON tb_nos(funcao);
        CREATE INDEX IF NOT EXISTS idx_nos_carto  ON tb_nos(eh_cartografico);
        CREATE INDEX IF NOT EXISTS idx_nos_token  ON tb_nos(token);
        CREATE INDEX IF NOT EXISTS idx_nos_lemma  ON tb_nos(lemma);
        CREATE INDEX IF NOT EXISTS idx_nos_folha  ON tb_nos(eh_folha);
        CREATE INDEX IF NOT EXISTS idx_nos_lft    ON tb_nos(lft);
        CREATE INDEX IF NOT EXISTS idx_nos_rgt    ON tb_nos(rgt);
        CREATE INDEX IF NOT EXISTS idx_rel_pai    ON tb_relacoes(pai_id);
        CREATE INDEX IF NOT EXISTS idx_rel_filho  ON tb_relacoes(filho_id);
    """)


def build_database_fase3():
    if not os.path.exists(DB_CARTOGRAFIA_PATH):
        print(f"Erro: '{DB_CARTOGRAFIA_PATH}' não encontrado. Execute 'python processar_corpus.py' primeiro.")
        return

    if os.path.exists(DB_FASE3_PATH):
        print(f"Removendo banco existente '{DB_FASE3_PATH}'...")
        os.remove(DB_FASE3_PATH)

    con_carto = sqlite3.connect(DB_CARTOGRAFIA_PATH)
    con_carto.row_factory = sqlite3.Row
    cur_carto = con_carto.cursor()

    con_f3 = sqlite3.connect(DB_FASE3_PATH)
    cur_f3 = con_f3.cursor()
    cur_f3.execute("PRAGMA journal_mode=WAL")
    cur_f3.execute("PRAGMA synchronous=NORMAL")

    criar_esquema(cur_f3)
    con_f3.commit()

    # Carrega todas as árvores expandidas
    print("Carregando árvores do banco de cartografia...")
    rows_expandidas = cur_carto.execute(
        "SELECT arquivo, sent_id_externo, arvore_original, arvore_expandida, status FROM tb_arvores_expandidas ORDER BY id ASC"
    ).fetchall()

    # Carrega também os textos das árvores para pré-aquecer o lematizador
    textos_arvores = [r["arvore_expandida"] for r in rows_expandidas]
    pre_aquece_lemas_de_arvores(textos_arvores)

    print(f"Indexando {len(rows_expandidas):,} árvores cartográficas em '{DB_FASE3_PATH}'...")
    t0 = time()
    total_nos = 0

    for idx, r in enumerate(rows_expandidas, 1):
        tree = deserialize_tree(r["arvore_expandida"])
        if tree is None:
            continue

        cur_f3.execute(
            """INSERT INTO tb_sentencas (arquivo, sent_id_externo, sent_original, sent_expandida, status_origem)
               VALUES (?, ?, ?, ?, ?)""",
            (r["arquivo"], r["sent_id_externo"], r["arvore_original"], r["arvore_expandida"], r["status"])
        )
        sentenca_id = cur_f3.lastrowid
        _counter[0] = 0

        inserir_arvore(cur_f3, tree, sentenca_id)
        
        if idx % 1000 == 0:
            con_f3.commit()
            print(f"  [{idx:05d}/{len(rows_expandidas):,}] sentenças indexadas...")

    con_f3.commit()
    criar_indices(cur_f3)
    con_f3.commit()

    total_nos = cur_f3.execute("SELECT count(*) FROM tb_nos").fetchone()[0]
    total_carto = cur_f3.execute("SELECT count(*) FROM tb_nos WHERE eh_cartografico=1").fetchone()[0]

    con_f3.close()
    con_carto.close()

    elapsed = time() - t0
    print("\n" + "=" * 65)
    print(f"  BANCO CARTOGRÁFICO '{DB_FASE3_PATH}' CRIADO COM SUCESSO!")
    print("=" * 65)
    print(f"  • Sentenças Indexadas    : {len(rows_expandidas):,}")
    print(f"  • Total de Nós (Grafo)  : {total_nos:,}")
    print(f"  • Nós Cartográficos (Leque): {total_carto:,} ({(total_carto/total_nos*100):.1f}%)")
    print(f"  • Tempo decorrido        : {elapsed:.2f}s")
    print("=" * 65)


if __name__ == "__main__":
    build_database_fase3()
