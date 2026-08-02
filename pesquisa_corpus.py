import sqlite3
import pandas as pd
import argparse
import urllib.request
import math
import sys
import os

DB_PATH = 'corpus.db'

def get_db_connection():
    if not os.path.exists(DB_PATH):
        print(f"Erro: Banco de dados '{DB_PATH}' não encontrado. Execute 'build_db.py' primeiro.")
        sys.exit(1)
    return sqlite3.connect(DB_PATH)

def freq_palavras(limite=50):
    con = get_db_connection()
    sql = """
    SELECT f.forma as Palavra, SUM(u.frequencia) as Frequência
    FROM tb_unigramas_freq u
    JOIN tb_formas f ON u.palavra = f.id
    GROUP BY u.palavra
    ORDER BY Frequência DESC
    LIMIT ?
    """
    df = pd.read_sql(sql, con, params=(limite,))
    con.close()
    return df

def freq_etiquetas(limite=50):
    con = get_db_connection()
    sql = """
    SELECT e.etiqueta as Etiqueta, SUM(u.frequencia) as Frequência
    FROM tb_unigramas_freq u
    JOIN tb_etiquetas e ON u.etiqueta = e.id
    GROUP BY u.etiqueta
    ORDER BY Frequência DESC
    LIMIT ?
    """
    df = pd.read_sql(sql, con, params=(limite,))
    con.close()
    return df

def kwic(palavra, horizonte=5, limite=20):
    con = get_db_connection()
    # Pega ID da palavra
    palavra_id_df = pd.read_sql("SELECT id FROM tb_formas WHERE forma = ?", con, params=(palavra,))
    if palavra_id_df.empty:
        print(f"Palavra '{palavra}' não encontrada no corpus.")
        return pd.DataFrame()
    palavra_id = int(palavra_id_df.iloc[0,0])

    sql = """
    SELECT u.id as occurrence_id, ctx.id as ctx_id, f.forma 
    FROM (SELECT id, texto FROM tb_unigramas WHERE palavra = ? LIMIT ?) u 
    JOIN tb_unigramas ctx ON ctx.id >= u.id - ? AND ctx.id <= u.id + ? AND ctx.texto = u.texto
    JOIN tb_formas f ON ctx.palavra = f.id
    ORDER BY occurrence_id, ctx_id
    """
    df = pd.read_sql(sql, con, params=(palavra_id, limite, horizonte, horizonte))
    con.close()

    if df.empty:
        return df

    # Agrupar por occurrence_id para recriar as linhas
    linhas = []
    for occ_id, group in df.groupby('occurrence_id'):
        contexto = ' '.join(group['forma'].tolist())
        linhas.append(contexto)
    
    return pd.DataFrame({'Concordância': linhas})

def colocados(palavra, horizonte=5, limite=20):
    con = get_db_connection()
    palavra_id_df = pd.read_sql("SELECT id FROM tb_formas WHERE forma = ?", con, params=(palavra,))
    if palavra_id_df.empty:
        print(f"Palavra '{palavra}' não encontrada no corpus.")
        return pd.DataFrame()
    palavra_id = int(palavra_id_df.iloc[0,0])

    # Frequencia total da palavra nódulo
    freq_n = pd.read_sql("SELECT sum(frequencia) FROM tb_unigramas_freq WHERE palavra = ?", con, params=(palavra_id,)).iloc[0,0]
    total_corpus = pd.read_sql("SELECT count(*) FROM tb_unigramas", con).iloc[0,0]

    # Busca colocados no horizonte
    sql = """
    SELECT ctx.palavra as col_id, COUNT(*) as freq_coocorrencia
    FROM (SELECT id, texto FROM tb_unigramas WHERE palavra = ?) u 
    JOIN tb_unigramas ctx ON ctx.id >= u.id - ? AND ctx.id <= u.id + ? AND ctx.texto = u.texto AND ctx.id != u.id
    GROUP BY ctx.palavra
    HAVING freq_coocorrencia > 1
    ORDER BY freq_coocorrencia DESC
    LIMIT ?
    """
    df_col = pd.read_sql(sql, con, params=(palavra_id, horizonte, horizonte, limite*2))
    
    if df_col.empty:
        con.close()
        return pd.DataFrame()

    col_ids = tuple(df_col['col_id'].tolist())
    placeholders = ','.join('?' * len(col_ids))
    
    sql_freq_col = f"""
    SELECT palavra, SUM(frequencia) as freq_total 
    FROM tb_unigramas_freq 
    WHERE palavra IN ({placeholders}) 
    GROUP BY palavra
    """
    df_freq = pd.read_sql(sql_freq_col, con, params=col_ids)
    
    sql_formas = f"SELECT id, forma FROM tb_formas WHERE id IN ({placeholders})"
    df_formas = pd.read_sql(sql_formas, con, params=col_ids)
    
    con.close()

    # Merge
    df_col = df_col.merge(df_freq, left_on='col_id', right_on='palavra')
    df_col = df_col.merge(df_formas, left_on='col_id', right_on='id')

    # Calcula Informação Mútua (MI)
    horizonte_total = horizonte * 2
    mi_list = []
    for _, row in df_col.iterrows():
        freq_cooc = row['freq_coocorrencia']
        freq_col = row['freq_total']
        expected = (freq_n * freq_col * horizonte_total) / total_corpus
        mi = math.log2(freq_cooc / expected) if expected > 0 else 0
        mi_list.append(round(mi, 2))
    
    df_col['MI'] = mi_list
    df_col = df_col.sort_values(by=['MI', 'freq_coocorrencia'], ascending=False).head(limite)
    
    return df_col[['forma', 'freq_coocorrencia', 'freq_total', 'MI']].rename(columns={'forma': 'Colocado', 'freq_coocorrencia': 'Co-ocorrências', 'freq_total': 'Frequência Total'})

def ngramas(n=2, limite=20):
    con = get_db_connection()
    print("Carregando sequências (pode levar alguns segundos)...")
    df = pd.read_sql("SELECT f.forma, u.texto FROM tb_unigramas u JOIN tb_formas f ON u.palavra = f.id ORDER BY u.id", con)
    con.close()
    
    print(f"Gerando {n}-gramas...")
    formas = df['forma']
    textos = df['texto']
    
    valid_mask = textos == textos.shift(-(n-1))
    
    ngram_series = formas
    for i in range(1, n):
        ngram_series = ngram_series.astype(str) + ' ' + formas.shift(-i).astype(str)
    
    ngram_series = ngram_series[valid_mask]
    
    counts = ngram_series.value_counts().head(limite).reset_index()
    counts.columns = ['N-grama', 'Frequência']
    return counts

def palavras_chave(limite=20):
    con = get_db_connection()
    print("Calculando frequências do corpus de estudo...")
    df_estudo = pd.read_sql("SELECT f.forma, SUM(u.frequencia) as freq FROM tb_unigramas_freq u JOIN tb_formas f ON u.palavra = f.id GROUP BY u.palavra", con)
    
    url = 'https://raw.githubusercontent.com/ilexistools/kitconc/master/kitconc/data/reflist_portuguese.tab'
    print(f"Baixando corpus de referência genérico ({url})...")
    try:
        df_ref = pd.read_table(url, header=None, names=['forma', 'freq'], dtype={'forma': str})
    except Exception as e:
        print(f"Erro ao baixar a lista de referência: {e}")
        return pd.DataFrame()

    total_estudo = df_estudo['freq'].sum()
    total_ref = df_ref['freq'].sum()
    
    df_estudo['forma'] = df_estudo['forma'].astype(str)
    
    df_merged = df_estudo.merge(df_ref[['forma', 'freq']], on='forma', how='left', suffixes=('_estudo', '_ref')).fillna(0)
    
    def log_likelihood(a, b, c, d):
        O1 = a + b
        E1 = c * O1 / (c + d)
        E2 = d * O1 / (c + d)
        v1 = a * math.log(a / E1) if a > 0 and E1 > 0 else 0
        v2 = b * math.log(b / E2) if b > 0 and E2 > 0 else 0
        return 2 * (v1 + v2)
    
    print("Calculando Log-Likelihood...")
    ll_scores = []
    for _, row in df_merged.iterrows():
        a = row['freq_estudo']
        b = row['freq_ref']
        if a > 5:
            ll = log_likelihood(a, b, total_estudo, total_ref)
        else:
            ll = 0
        ll_scores.append(round(ll, 2))
        
    df_merged['Keyness'] = ll_scores
    df_merged = df_merged[~df_merged['forma'].str.contains(r'^[^\w]+$')]
    
    df_merged = df_merged.sort_values(by='Keyness', ascending=False).head(limite)
    con.close()
    return df_merged[['forma', 'freq_estudo', 'freq_ref', 'Keyness']].rename(columns={'forma': 'Palavra-Chave', 'freq_estudo': 'Freq. Corpus', 'freq_ref': 'Freq. Referência'})

def dispersao(palavra):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("Erro: matplotlib não instalado. Execute 'pip install matplotlib'.")
        return

    con = get_db_connection()
    sql = """
    SELECT u.texto, u.id 
    FROM tb_unigramas u 
    JOIN tb_formas f ON u.palavra = f.id 
    WHERE f.forma = ?
    ORDER BY u.texto, u.id
    """
    df = pd.read_sql(sql, con, params=(palavra,))
    con.close()

    if df.empty:
        print(f"Palavra '{palavra}' não encontrada para dispersão.")
        return

    fig, ax = plt.subplots(figsize=(10, 6))
    for texto_id, group in df.groupby('texto'):
        x_vals = group['id'].tolist()
        y_vals = [texto_id] * len(x_vals)
        ax.plot(x_vals, y_vals, '|', color='blue', markersize=10)
    
    ax.set_yticks(df['texto'].unique())
    ax.set_ylabel('ID do Texto')
    ax.set_xlabel('Posição da Ocorrência no Corpus')
    ax.set_title(f'Dispersão da palavra: "{palavra}"')
    
    output_path = f'dispersao_{palavra}.png'
    plt.savefig(output_path)
    print(f"Gráfico de dispersão salvo em: {output_path}")

def export_df(df, filename):
    if df.empty:
        print("Não há dados para exportar.")
        return
    try:
        df.to_excel(filename, index=False)
        print(f"Resultados exportados para {filename}")
    except Exception as e:
        print(f"Erro ao exportar (verifique se openpyxl está instalado): {e}")
        csv_file = filename.replace('.xlsx', '.csv')
        df.to_csv(csv_file, index=False)
        print(f"Resultados exportados para {csv_file}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Ferramenta de Pesquisa no Corpus Tycho Brahe")
    parser.add_argument('--acao', choices=['freq_palavras', 'freq_etiquetas', 'kwic', 'colocados', 'ngramas', 'palavras_chave', 'dispersao'], required=True)
    parser.add_argument('--palavra', type=str, help="Palavra alvo para KWIC, Colocados ou Dispersão")
    parser.add_argument('--n', type=int, default=2, help="Tamanho do N-grama")
    parser.add_argument('--horizonte', type=int, default=5, help="Tamanho do horizonte para contexto (KWIC/Colocados)")
    parser.add_argument('--limite', type=int, default=20, help="Quantidade máxima de resultados a retornar")
    parser.add_argument('--exportar', type=str, help="Caminho do arquivo .xlsx para salvar os resultados (opcional)")

    args = parser.parse_args()

    df = None
    if args.acao == 'freq_palavras':
        df = freq_palavras(args.limite)
    elif args.acao == 'freq_etiquetas':
        df = freq_etiquetas(args.limite)
    elif args.acao == 'kwic':
        if not args.palavra:
            print("Erro: --palavra é obrigatório para KWIC.")
        else:
            df = kwic(args.palavra, args.horizonte, args.limite)
    elif args.acao == 'colocados':
        if not args.palavra:
            print("Erro: --palavra é obrigatório para Colocados.")
        else:
            df = colocados(args.palavra, args.horizonte, args.limite)
    elif args.acao == 'ngramas':
        df = ngramas(args.n, args.limite)
    elif args.acao == 'palavras_chave':
        df = palavras_chave(args.limite)
    elif args.acao == 'dispersao':
        if not args.palavra:
            print("Erro: --palavra é obrigatório para Dispersão.")
        else:
            dispersao(args.palavra)

    if df is not None:
        print(df.to_string(index=False))
        if args.exportar:
            export_df(df, args.exportar)
