"""
pesquisa_sintatica.py
=====================
Motor de Consulta Sintática e Cartográfica (Fases 1, 2 e 3).

Suporta:
  • Busca por label exato       : --label NP-SBJ / --label ForceP / --label MoodP_evaluative
  • Busca por categoria base    : --base NP / --base ModP
  • Busca por função sintática  : --funcao SBJ / --funcao ACC
  • Busca por token             : --token rei
  • Busca por lema              : --lemma oferecer
  • Dominância direta  (A < B)  : --pai IP-MAT --filho ForceP
  • Dominância indireta(A << B) : --domina ForceP --contido NP-SBJ
  • Co-irmandade       (A $ B)  : --irmao FocP --com FinP
  • KWIC sintático              : --kwic --label ForceP
  • Frequência de labels        : --acao freq_labels
  • Frequência cartográfica     : --acao freq_cartografia
  • Visualização de Árvore      : --acao ver_arvore --sentenca-id 1
  • Comparação de Árvores       : --acao comparar --sentenca-id 1
  • Exportação para Excel/CSV   : --exportar resultado.xlsx
"""

import sqlite3
import argparse
import sys
import os
from typing import Optional
import pandas as pd
from nltk.tree import Tree

from tree_io import deserialize_tree, serialize_tree

DEFAULT_DB_FASE3 = "corpus_fase3.db"
DEFAULT_DB_FASE1 = "corpus_fase1.db"


def resolver_db_path(custom_path: Optional[str] = None) -> str:
    """Resolve o banco de dados ativo."""
    if custom_path:
        if not os.path.exists(custom_path):
            sys.stderr.write(f"Erro: Banco '{custom_path}' não encontrado.\n")
            sys.exit(1)
        return custom_path
        
    appdata = os.getenv("APPDATA")
    app_dir = os.path.join(appdata, "tycho-desktop") if appdata else "."
    
    db_fase3 = os.path.join(app_dir, DEFAULT_DB_FASE3)
    db_fase1 = os.path.join(app_dir, DEFAULT_DB_FASE1)
    
    # Fallbacks locais (útil para dev)
    if os.path.exists(DEFAULT_DB_FASE3):
        return DEFAULT_DB_FASE3
    if os.path.exists(db_fase3):
        return db_fase3
    if os.path.exists(DEFAULT_DB_FASE1):
        return DEFAULT_DB_FASE1
    if os.path.exists(db_fase1):
        return db_fase1
        
    sys.stderr.write(f"Erro: Banco de dados não encontrado.\nColoque {DEFAULT_DB_FASE3} em {app_dir}\n")
    sys.exit(1)


def get_con(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = resolver_db_path(db_path)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    return con


def escape_like(s: str) -> str:
    """Escapa caracteres curinga do SQL LIKE (% e _) para evitar wildcard injection."""
    if not s:
        return s
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


# ── Frequência de Labels ──────────────────────────────────────────────────────
def freq_labels(limite: int = 30, db_path: Optional[str] = None) -> pd.DataFrame:
    con = get_con(db_path)
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


def freq_cartografia(limite: int = 30, db_path: Optional[str] = None) -> pd.DataFrame:
    """Retorna a frequência apenas dos nós gerados pela expansão cartográfica (Fases 2 e 3)."""
    con = get_con(db_path)
    try:
        # Verifica se a coluna eh_cartografico existe na tabela
        cur = con.cursor()
        colunas = [r[1] for r in cur.execute("PRAGMA table_info(tb_nos)").fetchall()]
        if "eh_cartografico" not in colunas:
            print("Aviso: O banco atual não possui anotação cartográfica (Fase 3). Executando frequência geral.")
            return freq_labels(limite, db_path)

        sql = """
            SELECT label, COUNT(*) as frequencia
            FROM   tb_nos
            WHERE  eh_cartografico = 1
            GROUP  BY label
            ORDER  BY frequencia DESC
            LIMIT  ?
        """
        return pd.read_sql(sql, con, params=(limite,))
    finally:
        con.close()


def get_cartografia_db_path() -> str:
    appdata = os.getenv("APPDATA")
    app_dir = os.path.join(appdata, "tycho-desktop") if appdata else "."
    db_path = os.path.join(app_dir, "corpus_cartografia.db")
    if os.path.exists("corpus_cartografia.db"):
        return "corpus_cartografia.db"
    return db_path

def quarentena_listar(limite: int = 50) -> pd.DataFrame:
    """Retorna itens pendentes na quarentena cartográfica."""
    try:
        con = sqlite3.connect(get_cartografia_db_path())
        sql = """
            SELECT id, arquivo, sent_id_externo, arvore_original, arvore_sugerida, motivo_anomalia, tipo_anomalia, status 
            FROM tb_quarentena 
            WHERE status = 'PENDENTE'
            ORDER BY id ASC
            LIMIT ?
        """
        df = pd.read_sql(sql, con, params=(limite,))
        con.close()
        return df
    except sqlite3.OperationalError:
        # Banco pode não existir
        return pd.DataFrame()

def quarentena_resolver(id_item: int, acao: str, arvore_corrigida: str = "") -> pd.DataFrame:
    """Resolve um item da quarentena (aprovar_sugerida, manter_original, corrigir)."""
    try:
        con = sqlite3.connect(get_cartografia_db_path())
        cur = con.cursor()
        
        status = 'PENDENTE'
        if acao == 'aprovar_sugerida':
            status = 'CORRIGIDO'
        elif acao == 'manter_original':
            status = 'IGNORADO'
        elif acao == 'corrigir':
            status = 'CORRIGIDO'
            
        cur.execute(
            "UPDATE tb_quarentena SET status = ?, arvore_corrigida = ?, data_revisao = CURRENT_TIMESTAMP WHERE id = ?",
            (status, arvore_corrigida, id_item)
        )
        con.commit()
        con.close()
        return pd.DataFrame([{"success": True, "id": id_item, "acao": acao}])
    except Exception as e:
        return pd.DataFrame([{"error": str(e)}])


# ── Busca básica por atributo ────────────────────────────────────────────────
def busca_por_atributo(
    label: str = None, base: str = None, funcao: str = None,
    token: str = None, lemma: str = None, apenas_carto: bool = False,
    limite: int = 20, db_path: Optional[str] = None
) -> pd.DataFrame:
    con = get_con(db_path)
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
            
        cur = con.cursor()
        colunas = [r[1] for r in cur.execute("PRAGMA table_info(tb_nos)").fetchall()]
        if apenas_carto and "eh_cartografico" in colunas:
            condicoes.append("n.eh_cartografico = 1")

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
def dominancia_direta(label_pai: str, label_filho: str, limite: int = 20, db_path: Optional[str] = None) -> pd.DataFrame:
    """Retorna pares (pai, filho) onde pai domina diretamente filho (A < B)."""
    con = get_con(db_path)
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
def dominancia_indireta(
    label_ancestral: str, label_descendente: str,
    token_descendente: str = None, lemma_descendente: str = None,
    limite: int = 20, db_path: Optional[str] = None
) -> pd.DataFrame:
    """Retorna pares (ancestral, descendente) usando coordenadas lft/rgt (A << B)."""
    con = get_con(db_path)
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
def irmandade(label_a: str, label_b: str, limite: int = 20, db_path: Optional[str] = None) -> pd.DataFrame:
    """Nós A e B que são irmãos sob o mesmo pai imediato (A $ B)."""
    con = get_con(db_path)
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
def kwic_sintatico(label: str, horizonte: int = 4, limite: int = 20, db_path: Optional[str] = None) -> pd.DataFrame:
    """Gera concordâncias KWIC centradas no constituinte sintático alvo."""
    con = get_con(db_path)
    try:
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
            folhas = pd.read_sql(
                "SELECT token, lft FROM tb_nos "
                "WHERE sentenca_id=? AND eh_folha=1 ORDER BY lft",
                con, params=(int(no["sentenca_id"]),)
            )

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


# ── Visualizador de Árvores Sintáticas ─────────────────────────────────────────
def ver_arvore(sentenca_id: int, formato: str = "diagrama", db_path: Optional[str] = None):
    """Exibe o diagrama visual em árvore sintática para uma sentença."""
    con = get_con(db_path)
    try:
        cur = con.cursor()
        colunas = [r[1] for r in cur.execute("PRAGMA table_info(tb_sentencas)").fetchall()]
        
        campo_arvore = "sent_expandida" if "sent_expandida" in colunas else "sent_orig"
        row = cur.execute(
            f"SELECT arquivo, id, {campo_arvore} FROM tb_sentencas WHERE id = ?",
            (sentenca_id,)
        ).fetchone()
        
        if not row:
            print(f"Sentença #{sentenca_id} não encontrada no banco.")
            return

        print("=" * 65)
        print(f"  ÁRVORE SINTÁTICA DA SENTENÇA #{row['id']} ({row['arquivo']})")
        print("=" * 65)
        
        raw_tree = row[2]
        tree = deserialize_tree(raw_tree)
        
        if tree is None:
            print("String da árvore:")
            print(raw_tree)
            return

        if formato == "diagrama":
            # Imprime visualmente em formato de árvore vertical / ASCII
            try:
                tree.pretty_print()
            except Exception:
                print(serialize_tree(tree, indent=2))
        else:
            print(serialize_tree(tree, indent=2))
        print("=" * 65)
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


# ── CLI Principal ─────────────────────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser(
        description="Motor de Busca Sintática Gerativa e Cartográfica – Corpus Tycho Brahe"
    )
    p.add_argument("--db", help="Caminho do banco SQLite (padrão: corpus_fase3.db ou corpus_fase1.db)")
    p.add_argument("--acao", required=True,
                   choices=["freq_labels", "freq_cartografia", "busca", "domina_direta",
                            "domina_indireta", "irmandade", "kwic", "ver_arvore", 
                            "quarentena_listar", "quarentena_resolver", "tokenizar"],
                   help="Ação a executar")
    p.add_argument("--label",        help="Label completo ex: ForceP, MoodP_evaluative, NP-SBJ")
    p.add_argument("--base",         help="Categoria base ex: NP, MoodP, CP")
    p.add_argument("--funcao",       help="Função sintática ex: SBJ, ACC, VOC")
    p.add_argument("--token",        help="Forma ortográfica exata")
    p.add_argument("--lemma",        help="Lema da palavra")
    p.add_argument("--pai",          help="Label do nó pai (dominância direta)")
    p.add_argument("--filho",        help="Label do nó filho (dominância direta)")
    p.add_argument("--domina",       help="Label do ancestral (dominância indireta)")
    p.add_argument("--contido",      help="Label do descendente (dominância indireta)")
    p.add_argument("--irmao",        help="Label do nó A (irmandade)")
    p.add_argument("--com",          help="Label do nó B (irmandade)")
    p.add_argument("--sentenca-id",  type=int, help="ID da sentença para visualização")
    p.add_argument("--formato-arvore", default="diagrama", choices=["diagrama", "sexp"], help="Formato de exibição da árvore")
    p.add_argument("--formato", default="texto", choices=["texto", "json"], help="Formato de saída dos resultados (texto ou json)")
    p.add_argument("--apenas-carto", action="store_true", help="Filtrar apenas nós cartográficos injetados")
    p.add_argument("--horizonte",    type=int, default=4, help="Horizonte de palavras no KWIC (padrão: 4)")
    p.add_argument("--limite",       type=int, default=20, help="Máximo de resultados (padrão: 20)")
    p.add_argument("--exportar",     help="Salvar resultados em .xlsx")
    args = p.parse_args()

    if args.limite <= 0:
        p.error("--limite deve ser maior que 0")
    if args.horizonte <= 0:
        p.error("--horizonte deve ser maior que 0")

    df = pd.DataFrame()

    if args.acao == "freq_labels":
        df = freq_labels(args.limite, db_path=args.db)

    elif args.acao == "freq_cartografia":
        df = freq_cartografia(args.limite, db_path=args.db)

    elif args.acao == "busca":
        df = busca_por_atributo(
            label=args.label, base=args.base, funcao=args.funcao,
            token=args.token, lemma=args.lemma, apenas_carto=args.apenas_carto,
            limite=args.limite, db_path=args.db
        )

    elif args.acao == "domina_direta":
        if not (args.pai and args.filho):
            p.error("--domina_direta requer --pai e --filho")
        df = dominancia_direta(args.pai, args.filho, args.limite, db_path=args.db)

    elif args.acao == "domina_indireta":
        if not (args.domina and args.contido):
            p.error("--domina_indireta requer --domina e --contido")
        df = dominancia_indireta(
            args.domina, args.contido,
            token_descendente=args.token,
            lemma_descendente=args.lemma,
            limite=args.limite, db_path=args.db
        )

    elif args.acao == "irmandade":
        if not (args.irmao and args.com):
            p.error("--irmandade requer --irmao e --com")
        df = irmandade(args.irmao, args.com, args.limite, db_path=args.db)

    elif args.acao == "kwic":
        if not args.label:
            p.error("--kwic requer --label")
        df = kwic_sintatico(args.label, args.horizonte, args.limite, db_path=args.db)

    elif args.acao == "quarentena_listar":
        df = quarentena_listar(args.limite)
        
    elif args.acao == "quarentena_resolver":
        # Assumindo que token é o ID e lemma é a ação
        if not (args.token and args.lemma):
            p.error("--quarentena_resolver requer --token (id) e --lemma (acao)")
        df = quarentena_resolver(int(args.token), args.lemma)

    elif args.acao == "tokenizar":
        texto = args.token or args.label or ""
        if not texto:
            p.error("--tokenizar requer --token ou --label com a sentença/árvore")
        from tokenizador_cartografico import processar_sentenca_texto
        res_tok = processar_sentenca_texto(texto)
        df = pd.DataFrame(res_tok["tokens"])

    elif args.acao == "ver_arvore":
        if not args.sentenca_id:
            p.error("--ver_arvore requer --sentenca-id")
        ver_arvore(args.sentenca_id, formato=args.formato_arvore, db_path=args.db)
        return

    if not df.empty:
        if getattr(args, 'formato', 'texto') == 'json':
            print(df.to_json(orient="records", force_ascii=False))
        else:
            print(df.to_string(index=False))
        if args.exportar:
            exportar(df, args.exportar)
    else:
        if getattr(args, 'formato', 'texto') == 'json':
            print("[]")
        else:
            print("Nenhum resultado encontrado.")


if __name__ == "__main__":
    main()
