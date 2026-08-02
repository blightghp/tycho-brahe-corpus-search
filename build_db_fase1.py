"""
build_db_fase1.py
=================
Fase 1 – Camada 1 e 2 do Plano Arquitetural Gerativo.

Este script:
  1. Lê os arquivos *_psd.txt com NLTK ParentedTree (estrutura completa de árvore).
  2. Lematiza cada folha (nó terminal) com spaCy (pt_core_news_sm).
  3. Armazena a árvore completa em SQLite usando o modelo Nested Sets (lft/rgt),
     permitindo consultas de dominância hierárquica em O(lTabelas geradas:
  tb_sentencas   – metadados de cada sentença (arquivo, id_sentenca, texto_id)
  tb_nos         – cada nó da árvore (label, token, lemma, lft, rgt, depth)
  tb_relacoes    – pares explícitos pai->filho (para c-comando e irmandade)
"""

import os
import re
import sqlite3
import glob
from time import time

from nltk.tree import ParentedTree
import spacy

# ── Constantes ──────────────────────────────────────────────────────────────
DB_PATH = "corpus_fase1.db"
CORPUS_DIR = "."
LABEL_EMPTY = re.compile(r"^\*.*\*[\d-]*$|^0$|^\*\w+\*-?\d*$")

# ── Pré-carrega o modelo spaCy ───────────────────────────────────────────────
print("Carregando modelo spaCy (pt_core_news_sm)...")
nlp = spacy.load("pt_core_news_sm", disable=["parser", "ner"])


# Cache global de lemas: evita chamar spaCy repetidamente para a mesma forma
_lemma_cache = {}


def lemmatize_token(token_str):
    """Retorna o lema de um token via spaCy (com cache). Para categorias
    vazias retorna o próprio token sem lematização."""
    if LABEL_EMPTY.match(token_str):
        return token_str
    if token_str in _lemma_cache:
        return _lemma_cache[token_str]
    doc = nlp(token_str)
    lemma = doc[0].lemma_ if doc else token_str
    _lemma_cache[token_str] = lemma
    return lemma


def pre_aquece_lemas(arquivos):
    """Extrai TODOS os tokens únicos do corpus e lematiza em batch via
    nlp.pipe(), preenchendo _lemma_cache antes da inserção no banco."""
    print("Pré-computando lemas em batch (spaCy pipe)...")
    tokens_unicos = set()
    for fpath in arquivos:
        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        for tag, word in re.findall(r'\(([^ (\n]+)\s+([^ ()\n]+)\)', content):
            if not LABEL_EMPTY.match(word):
                tokens_unicos.add(word)
    tokens_list = list(tokens_unicos)
    # Processa em lotes de 512 (muito mais rápido que um por um)
    docs = list(nlp.pipe(tokens_list, batch_size=512))
    for tok_str, doc in zip(tokens_list, docs):
        _lemma_cache[tok_str] = doc[0].lemma_ if doc else tok_str
    print(f"  {len(tokens_list):,} formas únicas lematizadas.")


def extrair_blocos(filepath: str) -> list[str]:
    """Divide o arquivo em blocos de sentença separados por linha em branco."""
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    # Remove o bloco de ID final e separa em sentenças
    blocos = [b.strip() for b in content.split("\n\n") if b.strip()]
    # Filtra blocos CODE (sem estrutura de árvore sintática)
    return [b for b in blocos if b.startswith("(") and ("(IP-" in b or "(CP-" in b)]


def limpar_indices_coref(block: str) -> str:
    """Remove índices de co-referência do tipo -1, -2 etc. dos rótulos não-terminais
    para facilitar a busca (mantém no token se for categoria vazia)."""
    # Substitui padrões como NP-SBJ-6 → NP-SBJ, mas mantém *pro* inalterado
    return re.sub(r"(\b[A-Z][A-Z0-9$@\-]+)-\d+\b(?!\*)", r"\1", block)


def parsear_bloco(block: str) -> ParentedTree | None:
    """Converte um bloco de texto psd em ParentedTree do NLTK.
    Remove o nó (ID ...) externo antes do parse."""
    # Remove linha ID ao final  ex: (ID A_001_PSD,03.1)
    block = re.sub(r"\(ID [^\)]+\)", "", block)
    # Retira duplo parêntese externo que o Tycho Brahe usa: ( (IP-MAT ...))
    block = block.strip()
    if block.startswith("( ("):
        block = block[2:-1].strip()
    try:
        return ParentedTree.fromstring(block)
    except Exception:
        return None


# ── Construção do banco ──────────────────────────────────────────────────────

def criar_banco(cur):
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS tb_sentencas (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            arquivo     TEXT NOT NULL,
            texto_id    INTEGER NOT NULL,
            sent_orig   TEXT
        );

        CREATE TABLE IF NOT EXISTS tb_nos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            sentenca_id INTEGER NOT NULL,
            label       TEXT NOT NULL,
            label_base  TEXT NOT NULL,   -- label sem função sintática ex: NP-SBJ → NP
            funcao      TEXT,            -- função sintática  ex: SBJ, ACC, VOC
            token       TEXT,            -- NULL para nós não-terminais
            lemma       TEXT,            -- NULL para nós não-terminais
            eh_folha    INTEGER NOT NULL DEFAULT 0,
            lft         INTEGER NOT NULL,
            rgt         INTEGER NOT NULL,
            depth       INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (sentenca_id) REFERENCES tb_sentencas(id)
        );

        CREATE TABLE IF NOT EXISTS tb_relacoes (
            pai_id      INTEGER NOT NULL,
            filho_id    INTEGER NOT NULL,
            PRIMARY KEY (pai_id, filho_id),
            FOREIGN KEY (pai_id)   REFERENCES tb_nos(id),
            FOREIGN KEY (filho_id) REFERENCES tb_nos(id)
        );
    """)


def parse_label(label: str):
    """Divide 'NP-SBJ' em base='NP' e funcao='SBJ'.
    Trata casos compostos como 'IP-MAT' (base='IP', funcao='MAT'),
    'NP-SBJ-ACC' → base='NP', funcao='SBJ-ACC'."""
    partes = label.split("-", 1)
    base = partes[0]
    funcao = partes[1] if len(partes) > 1 else None
    return base, funcao


# Contador global para Nested Sets
_counter = [0]


def inserir_arvore(cur, tree, sentenca_id,
                   depth=0, pai_id=None):
    """Recursão DFS que insere cada nó com coordenadas lft/rgt (Nested Sets).
    Retorna (node_id, rgt_final)."""
    _counter[0] += 1
    lft = _counter[0]

    label = tree.label() if hasattr(tree, "label") else str(tree)
    label_base, funcao = parse_label(label)

    # É folha?
    eh_folha = int(isinstance(tree[0], str)) if len(tree) > 0 else 0
    token = tree[0] if eh_folha else None
    lemma = lemmatize_token(token) if token else None

    # Insere o nó (rgt ainda não sabemos)
    cur.execute(
        """INSERT INTO tb_nos
           (sentenca_id, label, label_base, funcao, token, lemma,
            eh_folha, lft, rgt, depth)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (sentenca_id, label, label_base, funcao, token, lemma,
         eh_folha, lft, 0, depth)
    )
    node_id = cur.lastrowid

    if pai_id is not None:
        cur.execute("INSERT INTO tb_relacoes VALUES (?,?)", (pai_id, node_id))

    if not eh_folha:
        for subtree in tree:
            if isinstance(subtree, ParentedTree):
                inserir_arvore(cur, subtree, sentenca_id, depth + 1, node_id)
            elif isinstance(subtree, str):
                # token solto (não deveria ocorrer com árvore bem formada, mas por segurança)
                pass

    _counter[0] += 1
    rgt = _counter[0]
    cur.execute("UPDATE tb_nos SET rgt=? WHERE id=?", (rgt, node_id))
    return node_id, rgt


def criar_indices(cur):
    print("  Criando índices SQL...")
    cur.executescript("""
        CREATE INDEX IF NOT EXISTS idx_nos_sent   ON tb_nos(sentenca_id);
        CREATE INDEX IF NOT EXISTS idx_nos_label  ON tb_nos(label);
        CREATE INDEX IF NOT EXISTS idx_nos_base   ON tb_nos(label_base);
        CREATE INDEX IF NOT EXISTS idx_nos_funcao ON tb_nos(funcao);
        CREATE INDEX IF NOT EXISTS idx_nos_token  ON tb_nos(token);
        CREATE INDEX IF NOT EXISTS idx_nos_lemma  ON tb_nos(lemma);
        CREATE INDEX IF NOT EXISTS idx_nos_folha  ON tb_nos(eh_folha);
        CREATE INDEX IF NOT EXISTS idx_nos_lft    ON tb_nos(lft);
        CREATE INDEX IF NOT EXISTS idx_nos_rgt    ON tb_nos(rgt);
        CREATE INDEX IF NOT EXISTS idx_rel_pai    ON tb_relacoes(pai_id);
        CREATE INDEX IF NOT EXISTS idx_rel_filho  ON tb_relacoes(filho_id);
    """)


def build_database():
    if os.path.exists(DB_PATH):
        print(f"Removendo banco existente '{DB_PATH}'...")
        os.remove(DB_PATH)

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA synchronous=NORMAL")

    criar_banco(cur)
    con.commit()

    arquivos = sorted(glob.glob(os.path.join(CORPUS_DIR, "*_psd.txt")))
    print(f"Encontrados {len(arquivos)} arquivos.")

    # ── Lematização em batch antes de começar o parsing ──────────────────
    pre_aquece_lemas(arquivos)

    total_sentencas = 0
    total_nos = 0
    t0 = time()

    for texto_id, fpath in enumerate(arquivos, 1):
        nome = os.path.basename(fpath)
        print(f"  [{texto_id:02d}/{len(arquivos)}] {nome} ...", end=" ", flush=True)
        blocos = extrair_blocos(fpath)
        cont = 0
        for bloco in blocos:
            bloco_limpo = limpar_indices_coref(bloco)
            tree = parsear_bloco(bloco_limpo)
            if tree is None:
                continue

            cur.execute(
                "INSERT INTO tb_sentencas (arquivo, texto_id, sent_orig) VALUES (?,?,?)",
                (nome, texto_id, bloco[:200])
            )
            sentenca_id = cur.lastrowid
            _counter[0] = 0  # reinicia contadores Nested Sets por sentença

            inserir_arvore(cur, tree, sentenca_id)
            cont += 1

            if cont % 200 == 0:
                con.commit()

        con.commit()
        total_sentencas += cont
        total_nos_arquivo = cur.execute(
            "SELECT count(*) FROM tb_nos WHERE sentenca_id IN "
            "(SELECT id FROM tb_sentencas WHERE arquivo=?)", (nome,)
        ).fetchone()[0]
        total_nos += total_nos_arquivo
        print(f"{cont} sentenças / {total_nos_arquivo} nós")

    criar_indices(cur)
    con.commit()
    con.close()

    elapsed = time() - t0
    print(f"\nOK! Banco '{DB_PATH}' construido com sucesso.")
    print(f"  Sentenças : {total_sentencas:,}")
    print(f"  Nós totais: {total_nos:,}")
    print(f"  Tempo     : {elapsed:.1f}s")


if __name__ == "__main__":
    build_database()
