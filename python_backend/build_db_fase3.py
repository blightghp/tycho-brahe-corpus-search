"""
build_db_fase3.py
=================
Fase 3 – Compilador do Banco Sintático-Cartográfico com Nested Sets (corpus_fase3.db).

Este script:
  1. Lê as árvores sintáticas expandidas do banco 'corpus_cartografia.db' (ou caminhos customizados).
  2. Enriquece cada sentença com metadados filológicos (autor, obra, século, período, texto limpo).
  3. Lematiza todas as folhas (tokens) em lote via spaCy com cache global.
  4. Mapeia e indexa a árvore cartográfica completa usando coordenadas Nested Sets (lft/rgt),
     marcando explicitamente os nós originais vs nós cartográficos injetados (eh_cartografico).
  5. Cria índices compostos de alto desempenho para consultas hierárquicas em O(log n).
"""

import os
import re
import sqlite3
import json
import argparse
from time import time
from typing import Set, Tuple, Optional, List
from nltk.tree import ParentedTree, Tree
import spacy

from tree_io import deserialize_tree, serialize_tree
from metadata_tycho import extrair_metadados_arquivo
from db_cartografia import resolver_db_cartografia_path

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


def pre_aquece_lemas_de_arvores(arvores_textos: List[str]):
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


def extrair_texto_plano(tree: Tree) -> str:
    """Reconstrói a frase legível a partir das folhas reais da árvore."""
    tokens = []
    for leaf in tree.leaves():
        if isinstance(leaf, str) and not LABEL_EMPTY.match(leaf):
            tokens.append(leaf)
    return " ".join(tokens)


def parse_label(label: str) -> Tuple[str, Optional[str], int]:
    """Divide 'NP-SBJ' em base='NP', funcao='SBJ' e indica se é cartográfico."""
    eh_cartografico = int(any(label == p or label.startswith(p + "_") or label.startswith(p + "-") for p in CARTOGRAPHIC_PREFIXES))
    partes = label.split("-", 1)
    base = partes[0]
    funcao = partes[1] if len(partes) > 1 else None
    return base, funcao, eh_cartografico


_counter = [0]


def inserir_arvore(cur, tree: Tree, sentenca_id: int, depth: int = 0, pai_id: Optional[int] = None) -> Tuple[int, int, int]:
    """
    Insere recursivamente nós em formato Nested Sets (lft/rgt).
    Retorna (node_id, rgt, qtd_cartograficos).
    """
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

    total_carto = eh_carto
    if not eh_folha:
        for subtree in tree:
            if isinstance(subtree, (Tree, ParentedTree)):
                _, _, c_sub = inserir_arvore(cur, subtree, sentenca_id, depth + 1, node_id)
                total_carto += c_sub

    _counter[0] += 1
    rgt = _counter[0]
    cur.execute("UPDATE tb_nos SET rgt=? WHERE id=?", (rgt, node_id))
    return node_id, rgt, total_carto


def criar_esquema(cur):
    """Cria tabelas com suporte a metadados filológicos e Nested Sets."""
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS tb_sentencas (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            arquivo          TEXT NOT NULL,
            sent_id_externo  TEXT,
            autor            TEXT,
            titulo           TEXT,
            seculo           TEXT,
            ano_aproximado   INTEGER,
            periodo          TEXT,
            genero           TEXT,
            texto_plano      TEXT,
            qtd_tokens       INTEGER DEFAULT 0,
            qtd_cartograficos INTEGER DEFAULT 0,
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
    """Cria índices compostos para otimização extrema de consultas hierárquicas."""
    print("  Criando índices compostos de alta performance...")
    cur.executescript("""
        CREATE INDEX IF NOT EXISTS idx_nos_sent_lft_rgt ON tb_nos(sentenca_id, lft, rgt);
        CREATE INDEX IF NOT EXISTS idx_nos_carto_base   ON tb_nos(eh_cartografico, label_base);
        CREATE INDEX IF NOT EXISTS idx_nos_label        ON tb_nos(label);
        CREATE INDEX IF NOT EXISTS idx_nos_base         ON tb_nos(label_base);
        CREATE INDEX IF NOT EXISTS idx_nos_funcao       ON tb_nos(funcao);
        CREATE INDEX IF NOT EXISTS idx_nos_token        ON tb_nos(token);
        CREATE INDEX IF NOT EXISTS idx_nos_lemma        ON tb_nos(lemma);
        CREATE INDEX IF NOT EXISTS idx_nos_folha        ON tb_nos(eh_folha);
        CREATE INDEX IF NOT EXISTS idx_nos_lft          ON tb_nos(lft);
        CREATE INDEX IF NOT EXISTS idx_nos_rgt          ON tb_nos(rgt);
        CREATE INDEX IF NOT EXISTS idx_rel_pai          ON tb_relacoes(pai_id);
        CREATE INDEX IF NOT EXISTS idx_rel_filho        ON tb_relacoes(filho_id);

        CREATE INDEX IF NOT EXISTS idx_sent_autor_ano   ON tb_sentencas(autor, ano_aproximado);
        CREATE INDEX IF NOT EXISTS idx_sent_seculo      ON tb_sentencas(seculo);
        CREATE INDEX IF NOT EXISTS idx_sent_arq         ON tb_sentencas(arquivo);
    """)


def resolver_db_fase3_path(custom_path: Optional[str] = None) -> str:
    """Resolve o caminho de saída do banco corpus_fase3.db."""
    if custom_path:
        return custom_path
    if os.path.exists("corpus_fase3.db"):
        return "corpus_fase3.db"
    corpus_data = os.path.join(os.path.dirname(__file__), "..", "corpus_data", "corpus_fase3.db")
    if os.path.exists(corpus_data):
        return os.path.abspath(corpus_data)
    return "corpus_fase3.db"


def build_database_fase3(carto_db_path: Optional[str] = None, output_db_path: Optional[str] = None):
    db_carto = carto_db_path or resolver_db_cartografia_path()
    db_out = output_db_path or resolver_db_fase3_path()

    if not os.path.exists(db_carto):
        print(f"Erro: Banco de cartografia '{db_carto}' não encontrado.")
        print("Execute 'python processar_corpus.py' primeiro.")
        return

    if os.path.exists(db_out):
        print(f"Substituindo banco existente '{db_out}'...")
        try:
            os.remove(db_out)
        except Exception:
            pass

    con_carto = sqlite3.connect(db_carto)
    con_carto.row_factory = sqlite3.Row
    cur_carto = con_carto.cursor()

    con_f3 = sqlite3.connect(db_out)
    cur_f3 = con_f3.cursor()
    cur_f3.execute("PRAGMA journal_mode=WAL")
    cur_f3.execute("PRAGMA synchronous=NORMAL")
    cur_f3.execute("PRAGMA cache_size=-64000")
    cur_f3.execute("PRAGMA temp_store=MEMORY")

    criar_esquema(cur_f3)
    con_f3.commit()

    print(f"Lendo árvores expandidas de '{db_carto}'...")
    rows_expandidas = cur_carto.execute(
        "SELECT arquivo, sent_id_externo, arvore_original, arvore_expandida, status FROM tb_arvores_expandidas ORDER BY id ASC"
    ).fetchall()

    textos_arvores = [r["arvore_expandida"] for r in rows_expandidas]
    pre_aquece_lemas_de_arvores(textos_arvores)

    print(f"Indexando {len(rows_expandidas):,} árvores cartográficas em '{db_out}'...")
    t0 = time()

    for idx, r in enumerate(rows_expandidas, 1):
        tree = deserialize_tree(r["arvore_expandida"])
        if tree is None:
            continue

        meta = extrair_metadados_arquivo(r["arquivo"])
        texto_plano = extrair_texto_plano(tree)
        qtd_tokens = len(texto_plano.split())

        cur_f3.execute(
            """INSERT INTO tb_sentencas 
               (arquivo, sent_id_externo, autor, titulo, seculo, ano_aproximado, periodo, genero,
                texto_plano, qtd_tokens, sent_original, sent_expandida, status_origem)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (r["arquivo"], r["sent_id_externo"], meta["autor"], meta["titulo"], meta["seculo"],
             meta["ano_aproximado"], meta["periodo"], meta["genero"], texto_plano, qtd_tokens,
             r["arvore_original"], r["arvore_expandida"], r["status"])
        )
        sentenca_id = cur_f3.lastrowid
        _counter[0] = 0

        _, _, total_carto = inserir_arvore(cur_f3, tree, sentenca_id)
        cur_f3.execute("UPDATE tb_sentencas SET qtd_cartograficos=? WHERE id=?", (total_carto, sentenca_id))
        
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
    print(f"  BANCO CARTOGRÁFICO '{db_out}' CRIADO COM SUCESSO!")
    print("=" * 65)
    print(f"  • Sentenças Indexadas    : {len(rows_expandidas):,}")
    print(f"  • Total de Nós (Grafo)  : {total_nos:,}")
    print(f"  • Nós Cartográficos (Leque): {total_carto:,} ({(total_carto/total_nos*100):.1f}%)")
    print(f"  • Tempo decorrido        : {elapsed:.2f}s")
    print("=" * 65)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compilador do Banco Sintático Fase 3")
    parser.add_argument("--carto-db", help="Caminho do banco de cartografia fonte (corpus_cartografia.db)")
    parser.add_argument("--output-db", help="Caminho de saída para o banco SQLite (corpus_fase3.db)")
    args = parser.parse_args()

    build_database_fase3(carto_db_path=args.carto_db, output_db_path=args.output_db)
