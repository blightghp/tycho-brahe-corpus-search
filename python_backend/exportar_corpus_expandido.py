"""
exportar_corpus_expandido.py
============================
Motor 5 – Serializador Gerativo e Exportador do Corpus Cartográfico.

Exporta as árvores expandidas (Modelo Leque) armazenadas em 'corpus_cartografia.db'
de volta para arquivos de texto (.psd) e/ou compila um novo banco SQLite (corpus_fase3.db)
compatível com o motor de busca sintática (pesquisa_sintatica.py).
"""

import os
import sqlite3
import argparse
from typing import Dict, List

from db_cartografia import get_db_connection, DB_CARTOGRAFIA_PATH
from tree_io import format_psd_file_entry, deserialize_tree


def exportar_arquivos_psd(diretorio_saida: str = "corpus_cartografico_psd"):
    """Exporta as árvores expandidas agrupadas por arquivo de origem."""
    if not os.path.exists(DB_CARTOGRAFIA_PATH):
        print(f"Erro: Banco de cartografia '{DB_CARTOGRAFIA_PATH}' não encontrado. Execute 'processar_corpus.py' primeiro.")
        return
        
    os.makedirs(diretorio_saida, exist_ok=True)
    con = get_db_connection()
    try:
        cur = con.cursor()
        
        # Pega a lista de arquivos
        arquivos = [r[0] for r in cur.execute("SELECT DISTINCT arquivo FROM tb_arvores_expandidas ORDER BY arquivo").fetchall()]
        
        if not arquivos:
            print("Nenhuma árvore expandida encontrada no banco para exportação.")
            return
            
        print(f"Exportando {len(arquivos)} arquivos para o diretório '{diretorio_saida}/'...")
        
        total_exportadas = 0
        for arq in arquivos:
            out_path = os.path.join(diretorio_saida, arq)
            rows = cur.execute(
                """SELECT arvore_expandida, sent_id_externo 
                   FROM tb_arvores_expandidas 
                   WHERE arquivo = ? 
                   ORDER BY id ASC""",
                (arq,)
            ).fetchall()
            
            with open(out_path, "w", encoding="utf-8") as f:
                for r in rows:
                    tree = deserialize_tree(r["arvore_expandida"])
                    if tree:
                        entry = format_psd_file_entry(tree, sent_id=r["sent_id_externo"])
                        f.write(entry)
                        total_exportadas += 1
                        
            print(f"  -> {arq} ({len(rows)} sentenças)")
            
        print(f"\n[OK] Exportação concluída! Total de {total_exportadas:,} sentenças gravadas em '{diretorio_saida}/'.")
    finally:
        con.close()


def main():
    parser = argparse.ArgumentParser(description="Exportador do Corpus Cartográfico Expandido")
    parser.add_argument("--output-dir", default="corpus_cartografico_psd", help="Diretório de saída para arquivos .psd")
    args = parser.parse_args()
    
    exportar_arquivos_psd(args.output_dir)


if __name__ == "__main__":
    main()
