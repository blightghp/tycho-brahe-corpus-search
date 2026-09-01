"""Entrada minimalista para o sidecar dedicado da busca Marco 4.

O módulo preserva o contrato de ``busca_rastreavel.py`` sem importar o motor
legado de pesquisa, NLTK ou spaCy. O binário é produzido somente por um fluxo
explícito de build; este arquivo não cria artefatos nem escolhe bancos.
"""

from __future__ import annotations

from busca_rastreavel import main


if __name__ == "__main__":
    raise SystemExit(main())
