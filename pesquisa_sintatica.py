"""
pesquisa_sintatica.py
=====================
Fase 1 – Camada 3 do Plano Arquitetural Gerativo.

Motor de consulta sintática baseado em SQL + Nested Sets.
Suporta:
  • Busca por label exato       : --label NP-SBJ
  • Busca por categoria base    : --base NP  (cobre NP-SBJ, NP-ACC ...)
  • Busca por função sintática  : --funcao SBJ
  • Busca por token             : --token rei
  • Busca por lema              : --lemma oferecer
  • Dominância direta  (A < B)  : --pai X --filho Y
  • Dominância indireta(A << B) : --domina X --contido Y
  • Co-irmandade       (A $ B)  : --irmao X --com Y
  • KWIC sintático              : --kwic-label X  (retorna contexto de folhas)
  • Frequência de labels        : --freq-labels
  • Exportação para Excel       : --exportar resultado.xlsx
"""

import sqlite3
import argparse
import sys
import os
import pandas as pd

DB_PATH = "corpus_fase1.db"


def get_con():
    if not os.path.exists(DB_PATH):
        print(f"Erro: '{DB_PATH}' não encontrado. Execute 'python build_db_fase1.py' primeiro.")
        sys.exit(1)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def escape_like(s: str) -> str:
    """Escapa caracteres curinga do SQL LIKE (% e _) para evitar wildcard injection."""
    if not s:
        return s
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


# ── Frequência de labels ──────────────────────────────────────────────────────
def freq_labels(limite: int = 30) -> pd.DataFrame:
    con = get_con()
    try:
        sql = """
            SELECT label, label_base, funcao,
                   COUNT(*) as frequencia
            FROM   tb_nos
            WHERE  eh_folha = 0
            GROUP  BY label
            ORDER  BY frequencia DESC
            LIMIT  ?
        """
        return pd.read_sql(sql, con, params=(limite,))
    finally:
        con.close()


# ── Busca básica por atributo ────────────────────────────────────────────────
def busca_por_atributo(
    label: str = None, base: str = None, funcao: str = None,
    token: str = None, lemma: str = None, limite: int = 20
) -> pd.DataFrame:
    con = get_con()
    try:
        condicoes = []
        params = []

        if label:
            condicoes.append("n.label = ?"); params.append(label)
        if base:
            condicoes.append("n.label_base = ?"); params.append(base)
        if funcao:
            condicoes.append("n.funcao = ?"); params.append(funcao)
        if token:
            condicoes.append("n.token = ?"); params.append(token)
        if lemma:
            condicoes.append("n.lemma = ?"); params.append(lemma)

        where = ("WHERE " + " AND ".join(condicoes)) if condicoes else ""
        sql = f"""
            SELECT n.id, n.label, n.label_base, n.funcao,
                   n.token, n.lemma, n.eh_folha,
                   n.lft, n.rgt, n.depth,
                   s.arquivo, s.id as sentenca_id
            FROM   tb_nos n
            JOIN   tb_sentencas s ON n.sentenca_id = s.id
            {where}
            LIMIT ?
        """
        params.append(limite)
        return pd.read_sql(sql, con, params=params)
    finally:
        con.close()


# ── Dominância direta A < B ──────────────────────────────────────────────────
def dominancia_direta(label_pai: str, label_filho: str, limite: int = 20) -> pd.DataFrame:
    """Retorna pares (pai, filho) onde pai domina diretamente filho.
    Equivalente à notação Tgrep: 'A < B'.
    """
    con = get_con()
    try:
        sql = """
            SELECT pai.id as id_pai, pai.label as label_pai,
                   filho.id as id_filho, filho.label as label_filho,
                   filho.token, filho.lemma,
                   s.arquivo, s.id as sentenca_id
            FROM   tb_nos pai
            JOIN   tb_relacoes r  ON r.pai_id   = pai.id
            JOIN   tb_nos filho   ON r.filho_id  = filho.id
            JOIN   tb_sentencas s ON pai.sentenca_id = s.id
            WHERE  pai.label   LIKE ? ESCAPE '\\'
              AND  filho.label LIKE ? ESCAPE '\\'
            LIMIT  ?
        """
        return pd.read_sql(
            sql, con,
            params=(f"{escape_like(label_pai)}%", f"{escape_like(label_filho)}%", limite)
        )
    finally:
        con.close()


# ── Dominância indireta A << B ───────────────────────────────────────────────
def dominancia_indireta(label_ancestral: str, label_descendente: str,
                         token_descendente: str = None,
                         lemma_descendente: str = None,
                         limite: int = 20) -> pd.DataFrame:
    """Retorna pares (ancestral, descendente) usando lft/rgt (Nested Sets).
    Equivalente à notação Tgrep: 'A << B'.
    A << B: anc.lft < desc.lft AND anc.rgt > desc.rgt
    """
    con = get_con()
    try:
        extra_cond = ""
        extra_params = []
        if token_descendente:
            extra_cond += " AND desc.token = ?"
            extra_params.append(token_descendente)
        if lemma_descendente:
            extra_cond += " AND desc.lemma = ?"
            extra_params.append(lemma_descendente)

        sql = f"""
            SELECT anc.id as id_ancestral, anc.label as label_ancestral,
                   desc.id as id_descendente, desc.label as label_descendente,
                   desc.token, desc.lemma, desc.depth - anc.depth as distancia,
                   s.arquivo, s.id as sentenca_id
            FROM   tb_nos anc
            JOIN   tb_nos desc ON desc.sentenca_id = anc.sentenca_id
                              AND desc.lft > anc.lft
                              AND desc.rgt < anc.rgt
            JOIN   tb_sentencas s ON anc.sentenca_id = s.id
            WHERE  anc.label LIKE ? ESCAPE '\\'
              AND  desc.label LIKE ? ESCAPE '\\'
              {extra_cond}
            LIMIT  ?
        """
        params = [f"{escape_like(label_ancestral)}%", f"{escape_like(label_descendente)}%"] + extra_params + [limite]
        return pd.read_sql(sql, con, params=params)
    finally:
        con.close()


# ── Co-irmandade A $ B ────────────────────────────────────────────────────────
def irmandade(label_a: str, label_b: str, limite: int = 20) -> pd.DataFrame:
    """Nós A e B que são irmãos (mesmo pai).
    Equivalente à notação Tgrep: 'A $ B'.
    """
    con = get_con()
    try:
        sql = """
            SELECT a.label as label_a, a.token as token_a, a.lemma as lemma_a,
                   b.label as label_b, b.token as token_b, b.lemma as lemma_b,
                   s.arquivo, s.id as sentenca_id
            FROM   tb_nos a
            JOIN   tb_relacoes ra ON ra.filho_id = a.id
            JOIN   tb_relacoes rb ON rb.filho_id = b.id
                                 AND rb.pai_id   = ra.pai_id
                                 AND b.id       != a.id
            JOIN   tb_nos b ON b.id = rb.filho_id
            JOIN   tb_sentencas s ON a.sentenca_id = s.id
            WHERE  a.label LIKE ? ESCAPE '\\'
              AND  b.label LIKE ? ESCAPE '\\'
            LIMIT  ?
        """
        return pd.read_sql(
            sql, con,
            params=(f"{escape_like(label_a)}%", f"{escape_like(label_b)}%", limite)
        )
    finally:
        con.close()


# ── KWIC Sintático ────────────────────────────────────────────────────────────
def kwic_sintatico(label: str, horizonte: int = 4, limite: int = 20) -> pd.DataFrame:
    """Para cada ocorrência do nó com o label dado, extrai as folhas
    lexicais adjacentes (KWIC centrado no sintagma alvo)."""
    con = get_con()
    try:
        # Acha os nós com o label pedido
        nos = pd.read_sql(
            "SELECT n.id, n.lft, n.rgt, n.sentenca_id, s.arquivo "
            "FROM tb_nos n JOIN tb_sentencas s ON n.sentenca_id = s.id "
            "WHERE n.label LIKE ? ESCAPE '\\' LIMIT ?",
            con, params=(f"{escape_like(label)}%", limite)
        )

        if nos.empty:
            return pd.DataFrame()

        rows = []
        for _, no in nos.iterrows():
            # Folhas da sentença inteira ordenadas por lft
            folhas = pd.read_sql(
                "SELECT token, lft FROM tb_nos "
                "WHERE sentenca_id=? AND eh_folha=1 ORDER BY lft",
                con, params=(int(no["sentenca_id"]),)
            )

            # Índices das folhas que pertencem ao sintagma alvo
            within = folhas[(folhas["lft"] >= no["lft"]) & (folhas["lft"] <= no["rgt"])]
            if within.empty:
                continue

            idx_start = folhas.index[folhas["lft"] == within["lft"].min()][0]
            idx_end = folhas.index[folhas["lft"] == within["lft"].max()][0]

            esq = " ".join(folhas.iloc[max(0, idx_start - horizonte): idx_start]["token"])
            alvo = " ".join(within["token"])
            dir_ = " ".join(folhas.iloc[idx_end + 1: idx_end + 1 + horizonte]["token"])

            rows.append({
                "Arquivo": no["arquivo"],
                "Esquerda": esq,
                f"[{label}]": alvo,
                "Direita": dir_,
            })

        return pd.DataFrame(rows)
    finally:
        con.close()


# ── Exportação ────────────────────────────────────────────────────────────────
def exportar(df: pd.DataFrame, path: str):
    if df.empty:
        print("Sem dados para exportar.")
        return
    try:
        df.to_excel(path, index=False)
        print(f"Exportado -> {path}")
    except Exception as e:
        print(f"Aviso: Não foi possível exportar para Excel ({e}). Tentando CSV...")
        csv = path.replace(".xlsx", ".csv")
        df.to_csv(csv, index=False)
        print(f"Exportado (CSV) -> {csv}")


# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser(
        description="Pesquisa Sintática Gerativa – Corpus Tycho Brahe (Fase 1)"
    )
    p.add_argument("--acao", required=True,
                   choices=["freq_labels", "busca", "domina_direta",
                            "domina_indireta", "irmandade", "kwic"],
                   help="Ação a executar")
    p.add_argument("--label",   help="Label completo   ex: NP-SBJ")
    p.add_argument("--base",    help="Categoria base   ex: NP  (cobre NP-SBJ, NP-ACC...)")
    p.add_argument("--funcao",  help="Função sintática ex: SBJ, ACC, VOC")
    p.add_argument("--token",   help="Forma ortográfica exata")
    p.add_argument("--lemma",   help="Lema da palavra")
    p.add_argument("--pai",     help="Label do nó pai  (dominância direta)")
    p.add_argument("--filho",   help="Label do nó filho(dominância direta)")
    p.add_argument("--domina",  help="Label do ancestral (dominância indireta)")
    p.add_argument("--contido", help="Label do descendente (dominância indireta)")
    p.add_argument("--irmao",   help="Label do nó A (irmandade)")
    p.add_argument("--com",     help="Label do nó B (irmandade)")
    p.add_argument("--horizonte", type=int, default=4,
                   help="Horizonte de palavras no KWIC (padrão: 4)")
    p.add_argument("--limite",  type=int, default=20,
                   help="Máximo de resultados (padrão: 20)")
    p.add_argument("--exportar", help="Salvar resultados em .xlsx")
    args = p.parse_args()

    if args.limite <= 0:
        p.error("--limite deve ser maior que 0")
    if args.horizonte <= 0:
        p.error("--horizonte deve ser maior que 0")

    df = pd.DataFrame()

    if args.acao == "freq_labels":
        df = freq_labels(args.limite)

    elif args.acao == "busca":
        df = busca_por_atributo(
            label=args.label, base=args.base, funcao=args.funcao,
            token=args.token, lemma=args.lemma, limite=args.limite
        )

    elif args.acao == "domina_direta":
        if not (args.pai and args.filho):
            p.error("--domina_direta requer --pai e --filho")
        df = dominancia_direta(args.pai, args.filho, args.limite)

    elif args.acao == "domina_indireta":
        if not (args.domina and args.contido):
            p.error("--domina_indireta requer --domina e --contido")
        df = dominancia_indireta(
            args.domina, args.contido,
            token_descendente=args.token,
            lemma_descendente=args.lemma,
            limite=args.limite
        )

    elif args.acao == "irmandade":
        if not (args.irmao and args.com):
            p.error("--irmandade requer --irmao e --com")
        df = irmandade(args.irmao, args.com, args.limite)

    elif args.acao == "kwic":
        if not args.label:
            p.error("--kwic requer --label")
        df = kwic_sintatico(args.label, args.horizonte, args.limite)

    if not df.empty:
        print(df.to_string(index=False))
        if args.exportar:
            exportar(df, args.exportar)
    else:
        print("Nenhum resultado encontrado.")


if __name__ == "__main__":
    main()
