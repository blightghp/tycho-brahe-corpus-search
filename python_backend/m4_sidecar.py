"""Entrada minimalista para o sidecar dedicado da busca Marco 4.

O módulo preserva o contrato de ``busca_rastreavel.py`` sem importar o motor
legado de pesquisa, NLTK ou spaCy. O binário é produzido somente por um fluxo
explícito de build; este arquivo não cria artefatos nem escolhe bancos.
"""

from __future__ import annotations

import sys


def configure_utf8_streams() -> None:
    """Mantém o contrato JSON do sidecar em UTF-8 também no Windows."""

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")


configure_utf8_streams()

from busca_rastreavel import main


if __name__ == "__main__":
    raise SystemExit(main())
