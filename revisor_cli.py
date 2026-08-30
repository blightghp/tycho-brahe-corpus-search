"""
revisor_cli.py
==============
Motor 4 – Módulo "Human-in-the-Loop" (Auditoria e Manutenção Cartográfica).

Interface CLI para os pesquisadores e linguistas revisarem, corrigirem
e aprovarem sentenças com anomalias estruturais ou ordens não-canônicas
registradas na quarentena.
"""

import sys
import argparse
import json
import sqlite3
from datetime import datetime
from typing import Optional

from db_cartografia import (
    get_db_connection,
    obter_estatisticas,
    DB_CARTOGRAFIA_PATH
)
from tree_io import deserialize_tree, serialize_tree


def formatar_estatisticas():
    """Imprime um sumário das estatísticas do banco cartográfico."""
    stats = obter_estatisticas()
    print("=" * 60)
    print("  PAINEL DE AUDITORIA CARTOGRÁFICA (HUMAN-IN-THE-LOOP)")
    print("=" * 60)
    print(f"  • Árvores expandidas com sucesso : {stats['total_expandidas']:,}")
    print(f"  • Total de sentenças em quarentena : {stats['total_quarentena']:,}")
    print(f"    - Pendentes de revisão          : {stats['quarentena_pendente']:,}")
    print(f"    - Já revisadas / resolvidas     : {stats['quarentena_resolvida']:,}")
    print("-" * 60)
    print("  Projeções Funcionais mais instanciadas:")
    for proj, count in list(stats['projecoes_frequencia'].items())[:12]:
        print(f"    - {proj:<22}: {count:>6,} ocorrências")
    print("=" * 60)


def listar_quarentena(limite: int = 20, status: str = "PENDENTE"):
    """Lista as sentenças em quarentena filtradas por status."""
    con = get_db_connection()
    try:
        cur = con.cursor()
        rows = cur.execute(
            """SELECT id, arquivo, sent_id_externo, tipo_anomalia, motivo_anomalia, data_criacao
               FROM tb_quarentena 
               WHERE status = ? 
               ORDER BY id ASC 
               LIMIT ?""",
            (status, limite)
        ).fetchall()
        
        if not rows:
            print(f"Nenhuma sentença em quarentena com status '{status}'.")
            return
            
        print(f"\n--- Sentenças em Quarentena ({status}) [Limite: {limite}] ---")
        for r in rows:
            print(f"ID #{r['id']} | {r['arquivo']} ({r['sent_id_externo'] or 'S/ID'})")
            print(f"  Tipo   : {r['tipo_anomalia']}")
            print(f"  Motivo : {r['motivo_anomalia']}")
            print("-" * 50)
    finally:
        con.close()


def modo_interativo_revisao():
    """Inicia a sessão interativa de revisão humana sentença por sentença."""
    con = get_db_connection()
    try:
        cur = con.cursor()
        
        while True:
            row = cur.execute(
                """SELECT id, arquivo, sent_id_externo, arvore_original, motivo_anomalia, tipo_anomalia
                   FROM tb_quarentena 
                   WHERE status = 'PENDENTE' 
                   ORDER BY id ASC 
                   LIMIT 1"""
            ).fetchone()
            
            if not row:
                print("\n[OK] Parabéns! Não há mais sentenças pendentes na quarentena.")
                break
                
            q_id = row['id']
            arquivo = row['arquivo']
            sent_id = row['sent_id_externo']
            arvore_orig = row['arvore_original']
            motivo = row['motivo_anomalia']
            tipo = row['tipo_anomalia']
            
            print("\n" + "=" * 65)
            print(f"  REVISÃO DE QUARENTENA #{q_id} | {arquivo} ({sent_id})")
            print("=" * 65)
            print(f"  Tipo de Anomalia : {tipo}")
            print(f"  Diagnóstico      : {motivo}")
            print("-" * 65)
            print("  ÁRVORE ORIGINAL:")
            tree_obj = deserialize_tree(arvore_orig)
            if tree_obj:
                print("  " + serialize_tree(tree_obj, indent=2).replace("\n", "\n  "))
            else:
                print(f"  {arvore_orig}")
            print("-" * 65)
            print("  Opções de Decisão Humana:")
            print("    [1] Aprovar como variante histórica / estilística legítima")
            print("    [2] Inserir correção manual (S-expression)")
            print("    [3] Descartar / Ignorar (manter anotação original)")
            print("    [p] Próxima (pular sem decidir)")
            print("    [q] Sair da revisão")
            
            escolha = input("\nEscolha uma opção: ").strip().lower()
            
            if escolha == '1':
                obs = input("Observação justificativa (opcional): ").strip()
                cur.execute(
                    """UPDATE tb_quarentena 
                       SET status='APROVADO_VARIANTE', observacoes_humanas=?, data_revisao=CURRENT_TIMESTAMP 
                       WHERE id=?""",
                    (obs or "Aprovado pelo linguista como variante histórica", q_id)
                )
                con.commit()
                print(f"[OK] Sentença #{q_id} aprovada como variante histórica.")
                
            elif escolha == '2':
                print("Cole a S-expression corrigida (finalize com linha vazia):")
                linhas = []
                while True:
                    l = input()
                    if not l.strip():
                        break
                    linhas.append(l)
                arvore_corrigida = "\n".join(linhas)
                if arvore_corrigida:
                    parsed = deserialize_tree(arvore_corrigida)
                    if parsed is not None:
                        cur.execute(
                            """UPDATE tb_quarentena 
                               SET status='CORRIGIDO', arvore_corrigida=?, data_revisao=CURRENT_TIMESTAMP 
                               WHERE id=?""",
                            (arvore_corrigida, q_id)
                        )
                        con.commit()
                        print(f"[OK] Sentença #{q_id} corrigida com sucesso.")
                    else:
                        print("[ERRO] A string fornecida não é uma S-expression válida. Operação cancelada.")
                else:
                    print("Operação cancelada.")
                    
            elif escolha == '3':
                cur.execute(
                    """UPDATE tb_quarentena 
                       SET status='IGNORADO', data_revisao=CURRENT_TIMESTAMP 
                       WHERE id=?""",
                    (q_id,)
                )
                con.commit()
                print(f"[OK] Sentença #{q_id} marcada como ignorada.")
                
            elif escolha == 'p':
                print("Pulando para o próximo caso...")
                continue
                
            elif escolha == 'q':
                print("Saindo do modo interativo.")
                break
            else:
                print("Opção inválida.")
    finally:
        con.close()


def main():
    parser = argparse.ArgumentParser(
        description="Motor 4 – Módulo Human-in-the-Loop para Auditoria Cartográfica"
    )
    parser.add_argument("--status", action="store_true", help="Exibe o painel de estatísticas da cartografia")
    parser.add_argument("--listar", action="store_true", help="Lista as sentenças pendentes de quarentena")
    parser.add_argument("--revisar", action="store_true", help="Inicia o console interativo de revisão humana")
    parser.add_argument("--limite", type=int, default=20, help="Quantidade de itens a listar (padrão: 20)")
    parser.add_argument("--filtro-status", default="PENDENTE", help="Filtro de status para listagem (padrão: PENDENTE)")
    
    args = parser.parse_args()
    
    if args.status:
        formatar_estatisticas()
    elif args.listar:
        listar_quarentena(args.limite, args.filtro_status)
    elif args.revisar:
        modo_interativo_revisao()
    else:
        # Se nenhum argumento for passado, exibe o painel de status
        formatar_estatisticas()
        print("\nDica: use 'python revisor_cli.py --revisar' para iniciar a auditoria humana interativa.")


if __name__ == "__main__":
    main()
