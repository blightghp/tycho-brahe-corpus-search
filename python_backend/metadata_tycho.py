"""
metadata_tycho.py
=================
Catálogo de Metadados e Atribuição Histórica do Corpus Tycho Brahe.

Mapeia as siglas dos arquivos anotados (formato Penn Treebank PSD) para os respectivos
autores, títulos de obras, séculos, anos aproximados e períodos do Português Histórico:
  - Português Médio (sécs. XV-XVI)
  - Português Clássico (sécs. XVII-XVIII)
  - Português Moderno (séc. XIX)

Referência: Tycho Brahe Parsed Corpus of Historical Portuguese (IEL-Unicamp)
http://www.tycho.iel.unicamp.br/
"""

import os
from typing import Dict, Any, Optional

TYCHO_CATALOG: Dict[str, Dict[str, Any]] = {
    "a_001": {
        "autor": "Pe. Antônio Vieira",
        "titulo": "Cartas",
        "seculo": "XVII",
        "ano_aproximado": 1670,
        "periodo": "Português Clássico",
        "genero": "Epistolar"
    },
    "a_003": {
        "autor": "Pe. Antônio Vieira",
        "titulo": "Sermões",
        "seculo": "XVII",
        "ano_aproximado": 1680,
        "periodo": "Português Clássico",
        "genero": "Religioso / Oratória"
    },
    "a_004_part": {
        "autor": "Afonso de Albuquerque",
        "titulo": "Cartas de Afonso de Albuquerque",
        "seculo": "XVI",
        "ano_aproximado": 1515,
        "periodo": "Português Médio",
        "genero": "Historiográfico / Epistolar"
    },
    "b_001": {
        "autor": "Bernardim Ribeiro",
        "titulo": "História de Menina e Moça",
        "seculo": "XVI",
        "ano_aproximado": 1554,
        "periodo": "Português Médio",
        "genero": "Novela Pastoril"
    },
    "b_003": {
        "autor": "D. Francisco Manuel de Melo",
        "titulo": "Carta de Guia de Casados",
        "seculo": "XVII",
        "ano_aproximado": 1651,
        "periodo": "Português Clássico",
        "genero": "Tratado Moral / Epistolar"
    },
    "b_005": {
        "autor": "Manuel Maria Barbosa du Bocage",
        "titulo": "Cartas e Correspondência",
        "seculo": "XVIII",
        "ano_aproximado": 1795,
        "periodo": "Português Clássico / Ilustrado",
        "genero": "Epistolar"
    },
    "b_008": {
        "autor": "Brás Ferreira",
        "titulo": "Correspondência Oficial",
        "seculo": "XVIII",
        "ano_aproximado": 1740,
        "periodo": "Português Clássico",
        "genero": "Documental"
    },
    "c_001": {
        "autor": "Luís de Camões",
        "titulo": "Cartas de Luís de Camões",
        "seculo": "XVI",
        "ano_aproximado": 1570,
        "periodo": "Português Médio / Renascentista",
        "genero": "Epistolar"
    },
    "c_002": {
        "autor": "Matias Aires",
        "titulo": "Reflexões sobre a Vaidade dos Homens",
        "seculo": "XVIII",
        "ano_aproximado": 1752,
        "periodo": "Português Clássico / Ilustrado",
        "genero": "Filosófico / Moral"
    },
    "c_003": {
        "autor": "D. Francisco de Portugal",
        "titulo": "Arte de Galantaria",
        "seculo": "XVII",
        "ano_aproximado": 1670,
        "periodo": "Português Clássico",
        "genero": "Tratado Cortesão"
    },
    "c_005": {
        "autor": "Marquês de Castelo Melhor",
        "titulo": "Correspondência Política",
        "seculo": "XVII",
        "ano_aproximado": 1665,
        "periodo": "Português Clássico",
        "genero": "Político / Epistolar"
    },
    "c_007_part": {
        "autor": "D. Luís de Meneses (Conde da Ericeira)",
        "titulo": "História de Portugal Restaurado",
        "seculo": "XVII",
        "ano_aproximado": 1679,
        "periodo": "Português Clássico",
        "genero": "Historiografia"
    },
    "g_001": {
        "autor": "Gil Vicente",
        "titulo": "Farsas e Autos",
        "seculo": "XVI",
        "ano_aproximado": 1530,
        "periodo": "Português Médio",
        "genero": "Teatro"
    },
    "g_004": {
        "autor": "Gaspar Correia",
        "titulo": "Lendas da Índia",
        "seculo": "XVI",
        "ano_aproximado": 1560,
        "periodo": "Português Médio",
        "genero": "Crónica / Historiografia"
    },
    "g_008": {
        "autor": "Garcia de Resende",
        "titulo": "Crónica de D. João II",
        "seculo": "XVI",
        "ano_aproximado": 1545,
        "periodo": "Português Médio",
        "genero": "Crónica Histórica"
    },
    "l_001": {
        "autor": "Fernão Lopes",
        "titulo": "Crónica de D. João I",
        "seculo": "XV",
        "ano_aproximado": 1443,
        "periodo": "Português Médio",
        "genero": "Crónica Régia"
    },
    "m_003": {
        "autor": "D. Francisco Manuel de Melo",
        "titulo": "Apólogos Dialogais",
        "seculo": "XVII",
        "ano_aproximado": 1655,
        "periodo": "Português Clássico",
        "genero": "Diálogo Satírico"
    },
    "m_008": {
        "autor": "D. Francisco Manuel de Melo",
        "titulo": "Feira dos Anexins",
        "seculo": "XVII",
        "ano_aproximado": 1670,
        "periodo": "Português Clássico",
        "genero": "Prosa Satírica"
    },
    "o_001": {
        "autor": "Fernão Álvares do Oriente",
        "titulo": "Lusitânia Transformada",
        "seculo": "XVI",
        "ano_aproximado": 1590,
        "periodo": "Português Médio / Renascentista",
        "genero": "Novela Pastoril"
    },
    "p_001": {
        "autor": "Fernão Mendes Pinto",
        "titulo": "Peregrinação",
        "seculo": "XVII",
        "ano_aproximado": 1614,
        "periodo": "Português Clássico",
        "genero": "Relato de Viagens"
    },
    "s_001": {
        "autor": "Francisco Rodrigues Lobo",
        "titulo": "Corte na Aldeia",
        "seculo": "XVII",
        "ano_aproximado": 1619,
        "periodo": "Português Clássico",
        "genero": "Diálogo Cortesão"
    },
    "s_004": {
        "autor": "Frei Luís de Sousa",
        "titulo": "Vida de D. Frei Bartolomeu dos Mártires",
        "seculo": "XVII",
        "ano_aproximado": 1619,
        "periodo": "Português Clássico",
        "genero": "Hagiografia / Biografia"
    },
    "v_001": {
        "autor": "Gil Vicente",
        "titulo": "Autos e Comédias",
        "seculo": "XVI",
        "ano_aproximado": 1520,
        "periodo": "Português Médio",
        "genero": "Teatro"
    },
    "v_002": {
        "autor": "Frei Heitor Pinto",
        "titulo": "Imagem da Vida Cristã",
        "seculo": "XVI",
        "ano_aproximado": 1563,
        "periodo": "Português Médio",
        "genero": "Tratado Religioso"
    },
    "v_004_part": {
        "autor": "João de Barros",
        "titulo": "Décadas da Ásia",
        "seculo": "XVI",
        "ano_aproximado": 1552,
        "periodo": "Português Médio",
        "genero": "Historiografia das Descobertas"
    }
}


def extrair_metadados_arquivo(nome_arquivo: str) -> Dict[str, Any]:
    """
    Retorna o dicionário de metadados histórico-filológicos a partir do nome do arquivo PSD.
    
    Exemplo:
      extrair_metadados_arquivo("a_001_psd.txt") ->
      {
        "autor": "Pe. Antônio Vieira",
        "titulo": "Cartas",
        "seculo": "XVII",
        "ano_aproximado": 1670,
        "periodo": "Português Clássico",
        "genero": "Epistolar",
        "sigla": "a_001"
      }
    """
    base = os.path.basename(nome_arquivo).replace("_psd.txt", "").replace(".txt", "")
    
    if base in TYCHO_CATALOG:
        info = dict(TYCHO_CATALOG[base])
        info["sigla"] = base
        return info
        
    # Tratamento para siglas 'va_002', 'va_009', etc.
    if base.startswith("va_"):
        return {
            "autor": "Vários Autores (Documentos Históricos)",
            "titulo": f"Documento Histórico {base.upper()}",
            "seculo": "XVI-XVIII",
            "ano_aproximado": 1650,
            "periodo": "Português Histórico",
            "genero": "Documental",
            "sigla": base
        }
        
    return {
        "autor": "Desconhecido / Anônimo",
        "titulo": base,
        "seculo": "Desconhecido",
        "ano_aproximado": 1600,
        "periodo": "Português Histórico",
        "genero": "Geral",
        "sigla": base
    }
