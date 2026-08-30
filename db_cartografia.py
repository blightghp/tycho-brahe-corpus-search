"""
db_cartografia.py
=================
Camada de Persistência e Auditoria para a Cartografia Sintática (Fases 2 e 3).

Gerencia as tabelas:
  • tb_arvores_expandidas: árvores com expansão cartográfica validada (Modelo Leque).
  • tb_quarentena: sentenças com anomalias estruturais/ordem não-canônica para revisão humana.
  • tb_estatisticas_cartografia: métricas agregadas das projeções funcionais instanciadas.
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

DB_CARTOGRAFIA_PATH = "corpus_cartografia.db"


def get_db_connection(db_path: str = DB_CARTOGRAFIA_PATH) -> sqlite3.Connection:
    """Retorna uma conexão configurada com WAL para concorrência eficiente."""
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.execute("PRAGMA foreign_keys=ON")
    return con


def inicializar_banco_cartografia(db_path: str = DB_CARTOGRAFIA_PATH):
    """Cria o esquema de tabelas para expansão e quarentena humana."""
    con = get_db_connection(db_path)
    cur = con.cursor()
    
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS tb_arvores_expandidas (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            sentenca_id_fase1   INTEGER,
            arquivo             TEXT NOT NULL,
            sent_id_externo     TEXT,
            arvore_original     TEXT NOT NULL,
            arvore_expandida    TEXT NOT NULL,
            projecoes_injetadas TEXT NOT NULL, -- JSON array
            status              TEXT NOT NULL DEFAULT 'AUTOMATICO',
            data_processamento  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS tb_quarentena (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            arquivo             TEXT NOT NULL,
            sent_id_externo     TEXT,
            arvore_original     TEXT NOT NULL,
            motivo_anomalia     TEXT NOT NULL,
            tipo_anomalia       TEXT NOT NULL,
            arvore_sugerida     TEXT,
            arvore_corrigida    TEXT,
            status              TEXT NOT NULL DEFAULT 'PENDENTE', -- PENDENTE, CORRIGIDO, IGNORADO, APROVADO_VARIANTE
            observacoes_humanas TEXT,
            data_criacao        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_revisao        TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_exp_arq ON tb_arvores_expandidas(arquivo);
        CREATE INDEX IF NOT EXISTS idx_exp_status ON tb_arvores_expandidas(status);
        CREATE INDEX IF NOT EXISTS idx_quar_status ON tb_quarentena(status);
        CREATE INDEX IF NOT EXISTS idx_quar_tipo ON tb_quarentena(tipo_anomalia);
    """)
    con.commit()
    con.close()


def salvar_arvore_expandida(
    arquivo: str,
    arvore_original: str,
    arvore_expandida: str,
    projecoes: List[str],
    sent_id_externo: str = "",
    sentenca_id_fase1: Optional[int] = None,
    status: str = "AUTOMATICO",
    db_path: str = DB_CARTOGRAFIA_PATH
) -> int:
    """Insere ou atualiza uma árvore expandida com sucesso."""
    con = get_db_connection(db_path)
    try:
        cur = con.cursor()
        cur.execute(
            """INSERT INTO tb_arvores_expandidas 
               (sentenca_id_fase1, arquivo, sent_id_externo, arvore_original, arvore_expandida, projecoes_injetadas, status)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (sentenca_id_fase1, arquivo, sent_id_externo, arvore_original, arvore_expandida, json.dumps(projecoes), status)
        )
        row_id = cur.lastrowid
        con.commit()
        return row_id
    finally:
        con.close()


def registrar_quarentena(
    arquivo: str,
    arvore_original: str,
    motivo: str,
    tipo: str,
    sent_id_externo: str = "",
    arvore_sugerida: str = "",
    db_path: str = DB_CARTOGRAFIA_PATH
) -> int:
    """Insere uma sentença anômala na quarentena para auditoria humana."""
    con = get_db_connection(db_path)
    try:
        cur = con.cursor()
        cur.execute(
            """INSERT INTO tb_quarentena 
               (arquivo, sent_id_externo, arvore_original, motivo_anomalia, tipo_anomalia, arvore_sugerida, status)
               VALUES (?, ?, ?, ?, ?, ?, 'PENDENTE')""",
            (arquivo, sent_id_externo, arvore_original, motivo, tipo, arvore_sugerida)
        )
        row_id = cur.lastrowid
        con.commit()
        return row_id
    finally:
        con.close()


def obter_estatisticas(db_path: str = DB_CARTOGRAFIA_PATH) -> Dict[str, Any]:
    """Calcula estatísticas de transformação e quarentena."""
    con = get_db_connection(db_path)
    try:
        cur = con.cursor()
        total_expandidas = cur.execute("SELECT COUNT(*) FROM tb_arvores_expandidas").fetchone()[0]
        total_quarentena = cur.execute("SELECT COUNT(*) FROM tb_quarentena").fetchone()[0]
        quarentena_pendente = cur.execute("SELECT COUNT(*) FROM tb_quarentena WHERE status='PENDENTE'").fetchone()[0]
        quarentena_resolvida = cur.execute("SELECT COUNT(*) FROM tb_quarentena WHERE status!='PENDENTE'").fetchone()[0]
        
        # Projeções mais frequentes
        rows = cur.execute("SELECT projecoes_injetadas FROM tb_arvores_expandidas").fetchall()
        proj_counts: Dict[str, int] = {}
        for r in rows:
            try:
                for p in json.loads(r[0]):
                    proj_counts[p] = proj_counts.get(p, 0) + 1
            except Exception:
                pass
                
        return {
            "total_expandidas": total_expandidas,
            "total_quarentena": total_quarentena,
            "quarentena_pendente": quarentena_pendente,
            "quarentena_resolvida": quarentena_resolvida,
            "projecoes_frequencia": dict(sorted(proj_counts.items(), key=lambda x: x[1], reverse=True))
        }
    finally:
        con.close()


if __name__ == "__main__":
    inicializar_banco_cartografia()
    print("Banco de cartografia inicializado com sucesso.")
