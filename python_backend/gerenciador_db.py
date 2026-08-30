"""
gerenciador_db.py
=================
Utilitário de Gestão, Diagnóstico e Otimização do Banco de Dados Tycho Brahe.

Funcionalidades:
  • Verificação de integridade física e lógica (PRAGMA integrity_check, foreign_key_check).
  • Estatísticas estruturais e agrupamento filológico (por autor, século, período).
  • Otimização do SQLite (VACUUM, ANALYZE, reindexação).
  • Exportação de relatórios em JSON para consumo pelo motor Rust ou scripts CI/CD.
"""

import os
import sys
import sqlite3
import json
import argparse
from typing import Dict, Any, List

from db_cartografia import resolver_db_cartografia_path
from build_db_fase3 import resolver_db_fase3_path


def format_bytes(size: int) -> str:
    """Formata bytes para leitura humana (KB, MB, GB)."""
    s = float(size)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if s < 1024.0:
            return f"{s:.2f} {unit}"
        s /= 1024.0
    return f"{s:.2f} TB"



def obter_status_completo(db_fase3: str, db_carto: str) -> Dict[str, Any]:
    """Retorna um diagnóstico completo dos bancos SQLite."""
    res: Dict[str, Any] = {
        "fase3": {"existe": False},
        "cartografia": {"existe": False},
    }

    if os.path.exists(db_fase3):
        size = os.path.getsize(db_fase3)
        con = sqlite3.connect(db_fase3)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        try:
            total_sent = cur.execute("SELECT COUNT(*) FROM tb_sentencas").fetchone()[0]
            total_nos = cur.execute("SELECT COUNT(*) FROM tb_nos").fetchone()[0]
            total_carto = cur.execute("SELECT COUNT(*) FROM tb_nos WHERE eh_cartografico = 1").fetchone()[0]
            
            autores_rows = cur.execute(
                "SELECT autor, COUNT(*) as qtd FROM tb_sentencas GROUP BY autor ORDER BY qtd DESC"
            ).fetchall()
            autores = {r["autor"]: r["qtd"] for r in autores_rows if r["autor"]}

            seculos_rows = cur.execute(
                "SELECT seculo, COUNT(*) as qtd FROM tb_sentencas GROUP BY seculo ORDER BY seculo ASC"
            ).fetchall()
            seculos = {r["seculo"]: r["qtd"] for r in seculos_rows if r["seculo"]}

            res["fase3"] = {
                "existe": True,
                "caminho": os.path.abspath(db_fase3),
                "tamanho_bytes": size,
                "tamanho_formatado": format_bytes(size),
                "total_sentencas": total_sent,
                "total_nos": total_nos,
                "total_nos_cartograficos": total_carto,
                "taxa_cartografica_pct": round((total_carto / total_nos * 100), 2) if total_nos > 0 else 0,
                "autores": autores,
                "seculos": seculos,
            }
        except Exception as e:
            res["fase3"] = {"existe": True, "caminho": db_fase3, "erro": str(e)}
        finally:
            con.close()

    if os.path.exists(db_carto):
        size = os.path.getsize(db_carto)
        con = sqlite3.connect(db_carto)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        try:
            exp = cur.execute("SELECT COUNT(*) FROM tb_arvores_expandidas").fetchone()[0]
            quar_pend = cur.execute("SELECT COUNT(*) FROM tb_quarentena WHERE status = 'PENDENTE'").fetchone()[0]
            quar_resolv = cur.execute("SELECT COUNT(*) FROM tb_quarentena WHERE status != 'PENDENTE'").fetchone()[0]
            res["cartografia"] = {
                "existe": True,
                "caminho": os.path.abspath(db_carto),
                "tamanho_bytes": size,
                "tamanho_formatado": format_bytes(size),
                "total_expandidas": exp,
                "quarentena_pendente": quar_pend,
                "quarentena_resolvida": quar_resolv,
            }
        except Exception as e:
            res["cartografia"] = {"existe": True, "caminho": db_carto, "erro": str(e)}
        finally:
            con.close()

    return res


def verificar_integridade(db_path: str) -> Dict[str, Any]:
    """Executa verificações de integridade profunda no banco SQLite."""
    if not os.path.exists(db_path):
        return {"status": "ERRO", "motivo": f"Arquivo '{db_path}' inexistente"}

    con = sqlite3.connect(db_path)
    cur = con.cursor()
    try:
        integrity = cur.execute("PRAGMA integrity_check;").fetchall()
        fk_errors = cur.execute("PRAGMA foreign_key_check;").fetchall()
        return {
            "caminho": db_path,
            "integrity_check": [r[0] for r in integrity],
            "foreign_key_errors": len(fk_errors),
            "status": "OK" if len(integrity) == 1 and integrity[0][0] == "ok" and len(fk_errors) == 0 else "ALERTA"
        }
    finally:
        con.close()


def otimizar_banco(db_path: str) -> Dict[str, Any]:
    """Executa VACUUM e ANALYZE para desfragmentar páginas e recalcular estatísticas."""
    if not os.path.exists(db_path):
        return {"status": "ERRO", "motivo": f"Arquivo '{db_path}' inexistente"}

    tamanho_antes = os.path.getsize(db_path)
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    try:
        cur.execute("PRAGMA optimize;")
        cur.execute("ANALYZE;")
        con.commit()
        cur.execute("VACUUM;")
        con.commit()
    finally:
        con.close()

    tamanho_depois = os.path.getsize(db_path)
    return {
        "caminho": db_path,
        "tamanho_antes": format_bytes(tamanho_antes),
        "tamanho_depois": format_bytes(tamanho_depois),
        "economia_bytes": tamanho_antes - tamanho_depois,
        "status": "OTIMIZADO_COM_SUCESSO"
    }


def main():
    parser = argparse.ArgumentParser(description="Gerenciador do Banco de Dados Tycho Brahe")
    parser.add_argument("--status", action="store_true", help="Exibe relatório completo dos bancos")
    parser.add_argument("--check", action="store_true", help="Executa verificação de integridade física")
    parser.add_argument("--vacuum", action="store_true", help="Otimiza e desfragmenta os bancos SQLite")
    parser.add_argument("--json", action="store_true", help="Emite o resultado estritamente em formato JSON")
    parser.add_argument("--db", help="Caminho customizado do banco de dados")
    args = parser.parse_args()

    db_fase3 = args.db or resolver_db_fase3_path()
    db_carto = resolver_db_cartografia_path()

    if args.check:
        res = {
            "fase3": verificar_integridade(db_fase3),
            "cartografia": verificar_integridade(db_carto)
        }
        if args.json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            print("=" * 60)
            print("  VERIFICAÇÃO DE INTEGRIDADE SQLITE")
            print("=" * 60)
            for k, v in res.items():
                print(f"  • [{k.upper()}] Status: {v.get('status')} | FK Errors: {v.get('foreign_key_errors', 0)}")
            print("=" * 60)
        return

    if args.vacuum:
        res = {
            "fase3": otimizar_banco(db_fase3),
            "cartografia": otimizar_banco(db_carto)
        }
        if args.json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            print("=" * 60)
            print("  OTIMIZAÇÃO E VACUUM DO BANCO CONCLUÍDOS")
            print("=" * 60)
            for k, v in res.items():
                print(f"  • [{k.upper()}]: {v.get('tamanho_antes')} -> {v.get('tamanho_depois')}")
            print("=" * 60)
        return

    # Padrão: status
    status = obter_status_completo(db_fase3, db_carto)
    if args.json:
        print(json.dumps(status, indent=2, ensure_ascii=False))
    else:
        print("=" * 65)
        print("  PAINEL DE GESTÃO DO BANCO DE DADOS TYCHO BRAHE")
        print("=" * 65)
        f3 = status["fase3"]
        if f3.get("existe"):
            print(f"  • Banco Principal (Fase 3) : {f3.get('caminho')}")
            print(f"  • Tamanho em Disco         : {f3.get('tamanho_formatado')}")
            print(f"  • Total de Sentenças       : {f3.get('total_sentencas', 0):,}")
            print(f"  • Total de Nós (Nested Set): {f3.get('total_nos', 0):,}")
            print(f"  • Nós Cartográficos        : {f3.get('total_nos_cartograficos', 0):,} ({f3.get('taxa_cartografica_pct', 0)}%)")
            print("-" * 65)
            print("  Distribuição por Séculos:")
            for sec, qtd in f3.get("seculos", {}).items():
                print(f"    - Século {sec:<6}: {qtd:>6,} sentenças")
        else:
            print("  • Banco Principal (Fase 3) : NÃO ENCONTRADO")

        print("-" * 65)
        cart = status["cartografia"]
        if cart.get("existe"):
            print(f"  • Banco Cartografia (Auditoria): {cart.get('caminho')} ({cart.get('tamanho_formatado')})")
            print(f"  • Árvores Expandidas           : {cart.get('total_expandidas', 0):,}")
            print(f"  • Quarentenas Pendentes        : {cart.get('quarentena_pendente', 0):,}")
            print(f"  • Quarentenas Resolvidas       : {cart.get('quarentena_resolvida', 0):,}")
        else:
            print("  • Banco Cartografia : NÃO ENCONTRADO")
        print("=" * 65)


if __name__ == "__main__":
    main()
