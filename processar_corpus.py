"""
processar_corpus.py
===================
Pipeline de Processamento em Lote (Batch Transducer) do Corpus Tycho Brahe.

Aplica a transmutação cartográfica algorítmica (Modelo Leque) em todos os
arquivos *_psd.txt do corpus, integrando os Motores 1, 2, 3, 4 e 5.
"""

import os
import glob
import time
import argparse
from typing import List

from tree_io import (
    extract_blocks,
    extract_sent_id,
    deserialize_tree,
    serialize_tree,
    limpar_indices_coref
)
from oracle import extrair_evidencias_cinque, analisar_periferia_rizzi
from rewriter import transmutar_arvore_completa, CartographicAnomalyError
from db_cartografia import (
    inicializar_banco_cartografia,
    salvar_arvore_expandida,
    registrar_quarentena,
    obter_estatisticas,
    DB_CARTOGRAFIA_PATH
)


def processar_arquivo(
    filepath: str,
    strip_coref: bool = False
) -> dict:
    """Processa um arquivo individual do corpus e retorna contadores."""
    nome_arquivo = os.path.basename(filepath)
    blocos = extract_blocks(filepath)
    
    total_blocos = len(blocos)
    expandidas = 0
    quarentenas = 0
    erros = 0
    
    for bloco in blocos:
        sent_id = extract_sent_id(bloco)
        tree = deserialize_tree(bloco, strip_coref=strip_coref)
        
        if tree is None:
            erros += 1
            continue
            
        arvore_original_str = serialize_tree(tree)
        
        try:
            tree_expandida, projecoes = transmutar_arvore_completa(tree)
            arvore_expandida_str = serialize_tree(tree_expandida)
            
            salvar_arvore_expandida(
                arquivo=nome_arquivo,
                arvore_original=arvore_original_str,
                arvore_expandida=arvore_expandida_str,
                projecoes=projecoes,
                sent_id_externo=sent_id
            )
            expandidas += 1
            
        except CartographicAnomalyError as e:
            registrar_quarentena(
                arquivo=nome_arquivo,
                arvore_original=arvore_original_str,
                motivo=e.motivo,
                tipo=e.tipo_anomalia,
                sent_id_externo=sent_id
            )
            quarentenas += 1
            
        except Exception as e:
            registrar_quarentena(
                arquivo=nome_arquivo,
                arvore_original=arvore_original_str,
                motivo=f"Erro inesperado: {e}",
                tipo="ERRO_INESPERADO",
                sent_id_externo=sent_id
            )
            quarentenas += 1
            
    return {
        "total": total_blocos,
        "expandidas": expandidas,
        "quarentenas": quarentenas,
        "erros": erros
    }


def executar_pipeline(
    corpus_dir: str = ".",
    limite_arquivos: int = 0,
    reset_db: bool = False
):
    """Executa o processamento em lote para todos os arquivos do corpus."""
    if reset_db and os.path.exists(DB_CARTOGRAFIA_PATH):
        print(f"Resetando banco de cartografia '{DB_CARTOGRAFIA_PATH}'...")
        os.remove(DB_CARTOGRAFIA_PATH)
        
    inicializar_banco_cartografia()
    
    arquivos = sorted(glob.glob(os.path.join(corpus_dir, "*_psd.txt")))
    if limite_arquivos > 0:
        arquivos = arquivos[:limite_arquivos]
        
    print("=" * 65)
    print("  INICIANDO TRANSDUÇÃO CARTOGRÁFICA EM LOTE (FASES 2 E 3)")
    print(f"  Total de arquivos a processar: {len(arquivos)}")
    print("=" * 65)
    
    t0 = time.time()
    total_geral = 0
    total_expandidas = 0
    total_quarentenas = 0
    
    for idx, fpath in enumerate(arquivos, 1):
        nome = os.path.basename(fpath)
        print(f"  [{idx:02d}/{len(arquivos)}] Processando {nome:<18} ...", end=" ", flush=True)
        
        t_arq = time.time()
        res = processar_arquivo(fpath)
        dt_arq = time.time() - t_arq
        
        total_geral += res["total"]
        total_expandidas += res["expandidas"]
        total_quarentenas += res["quarentenas"]
        
        taxa_quarentena = (res["quarentenas"] / res["total"] * 100) if res["total"] > 0 else 0
        print(f"{res['expandidas']} ok | {res['quarentenas']} quarentena ({taxa_quarentena:.1f}%) [{dt_arq:.1f}s]")
        
    tempo_total = time.time() - t0
    stats = obter_estatisticas()
    
    print("\n" + "=" * 65)
    print("  CONCLUÍDO COM SUCESSO!")
    print("=" * 65)
    print(f"  • Tempo Total decorrido          : {tempo_total:.2f}s")
    print(f"  • Total de Sentenças analisadas : {total_geral:,}")
    print(f"  • Árvores Expandidas (Leque)    : {total_expandidas:,} ({(total_expandidas/total_geral*100):.1f}%)")
    print(f"  • Sentenças em Quarentena       : {total_quarentenas:,} ({(total_quarentenas/total_geral*100):.1f}%)")
    print("-" * 65)
    print("  Projeções Funcionais Injetadas:")
    for proj, count in list(stats['projecoes_frequencia'].items())[:15]:
        print(f"    - {proj:<24}: {count:>7,} vezes")
    print("=" * 65)
    print("Para auditar os casos em quarentena, execute: python revisor_cli.py --revisar")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline de Transdução Cartográfica do Corpus")
    parser.add_argument("--limite", type=int, default=0, help="Limitar quantidade de arquivos a processar (0 para todos)")
    parser.add_argument("--reset", action="store_true", help="Reiniciar o banco de cartografia do zero")
    args = parser.parse_args()
    
    executar_pipeline(limite_arquivos=args.limite, reset_db=args.reset)
