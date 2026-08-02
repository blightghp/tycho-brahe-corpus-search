import sqlite3
import os
import glob
import re
import collections
from time import time

DB_PATH = 'corpus.db'

def build_database():
    if os.path.exists(DB_PATH):
        print(f"Limpando banco antigo {DB_PATH}...")
        os.remove(DB_PATH)

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    print("Criando tabelas...")
    cur.execute('CREATE TABLE tb_formas(id INTEGER NOT NULL PRIMARY KEY, forma VARCHAR(50))')
    cur.execute('CREATE TABLE tb_etiquetas(id INTEGER NOT NULL PRIMARY KEY, etiqueta VARCHAR(15))')
    cur.execute('CREATE TABLE tb_unigramas(id INTEGER NOT NULL PRIMARY KEY, palavra INTEGER, etiqueta INTEGER, sent INTEGER, texto INTEGER)')
    cur.execute('CREATE TABLE tb_unigramas_freq(id INTEGER NOT NULL PRIMARY KEY, palavra INTEGER, etiqueta INTEGER, frequencia INTEGER)')
    con.commit()

    formas = {}
    etiquetas = {}
    unigramas = []
    unigramas_freq = collections.Counter()

    def get_forma_id(f):
        if f not in formas:
            formas[f] = len(formas) + 1
        return formas[f]

    def get_etiqueta_id(e):
        if e not in etiquetas:
            etiquetas[e] = len(etiquetas) + 1
        return etiquetas[e]

    files = glob.glob('*_psd.txt')
    if not files:
        print("Erro: Nenhum arquivo '_psd.txt' encontrado no diretório atual.")
        return

    print(f'Encontrados {len(files)} arquivos. Iniciando extração e parsing...')

    start_time = time()
    sent_id = 0
    for text_id, fpath in enumerate(files, 1):
        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # O corpus parece separar as sentenças por linha em branco dupla
        blocks = content.split('\n\n')
        for block in blocks:
            # Expressão regular para pegar as folhas da árvore de anotação
            matches = re.findall(r'\(([^ (\n]+)\s+([^ ()\n]+)\)', block)
            if not matches:
                continue
            sent_id += 1
            for m in matches:
                tag, word = m
                w_id = get_forma_id(word)
                t_id = get_etiqueta_id(tag)
                
                unigramas.append((w_id, t_id, sent_id, text_id))
                unigramas_freq[(w_id, t_id)] += 1

    print(f'Extração concluída em {time() - start_time:.2f}s.')
    print(f'Total de palavras extraídas: {len(unigramas)}')
    print('Inserindo dados no banco SQLite...')

    cur.executemany('INSERT INTO tb_formas VALUES (?, ?)', [(v, k) for k, v in formas.items()])
    cur.executemany('INSERT INTO tb_etiquetas VALUES (?, ?)', [(v, k) for k, v in etiquetas.items()])

    # Batch insert unigramas para não consumir muita RAM
    chunk_size = 100000
    for i in range(0, len(unigramas), chunk_size):
        chunk = [(None,) + u for u in unigramas[i:i+chunk_size]]
        cur.executemany('INSERT INTO tb_unigramas VALUES (?, ?, ?, ?, ?)', chunk)

    cur.executemany('INSERT INTO tb_unigramas_freq VALUES (?, ?, ?, ?)', 
                    [(None, k[0], k[1], v) for k, v in unigramas_freq.items()])

    print('Criando índices (isso pode demorar um momento)...')
    cur.execute('CREATE UNIQUE INDEX idx_p ON tb_formas (forma)')
    cur.execute('CREATE UNIQUE INDEX idx_e ON tb_etiquetas (etiqueta)')
    cur.execute('CREATE INDEX idx_pe ON tb_unigramas (palavra, etiqueta)')
    cur.execute('CREATE INDEX idx_pef ON tb_unigramas_freq (palavra, etiqueta)')

    con.commit()
    con.close()
    print('Banco de dados construído com sucesso!')

if __name__ == "__main__":
    build_database()
