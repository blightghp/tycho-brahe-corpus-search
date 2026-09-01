"""Empacota uma release experimental sem reescrever a documentação canônica.

Os pacotes v1.0.0 permanecem congelados enquanto a reconstrução de dados e a
busca auditável não forem concluídas. Por isso este script exige um opt-in
explícito. Mesmo com o opt-in, ele só copia documentos versionados para a
release portátil: nunca reescreve ``README.md`` ou ``docs/`` da raiz.
"""

from __future__ import annotations

import os
import shutil
import sys
import zipfile
from pathlib import Path


if os.environ.get("TYCHO_ALLOW_EXPERIMENTAL_RELEASE") != "1":
    sys.stderr.write(
        "Publicação bloqueada: os artefatos atuais são experimentais e estão "
        "congelados. Consulte docs/STATUS_DE_ARTEFATOS.md. Para uma auditoria "
        "controlada, defina TYCHO_ALLOW_EXPERIMENTAL_RELEASE=1 explicitamente.\n"
    )
    raise SystemExit(2)


ROOT = Path(__file__).resolve().parents[1]
RELEASE_DIR = ROOT / "release"
PORTABLE_DIR = RELEASE_DIR / "TychoBrahe_v1.0.0_Portable"
INSTALLERS_DIR = RELEASE_DIR / "installers"
PORTABLE_DOCS_DIR = PORTABLE_DIR / "docs"

PORTABLE_DOCUMENTS = (
    "MANUAL_DO_USUARIO.md",
    "GUIA_CARTOGRAFIA_SINTATICA.md",
    "ARQUITETURA_DO_SISTEMA.md",
    "REFERENCIAS_E_CREDITOS.md",
    "IMPORTACAO_RASTREAVEL.md",
    "ANALISE_GRAMATICAL_EXPANDIDA.md",
    "STATUS_DE_ARTEFATOS.md",
)


def require_file(path: Path, label: str) -> Path:
    if not path.is_file():
        raise FileNotFoundError(f"{label} não encontrado: {path}")
    return path


def copy_if_present(source: Path, destination: Path) -> bool:
    if not source.is_file():
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return True


def write_portable_readme(destination: Path) -> None:
    destination.write_text(
        """================================================================================
  TYCHO BRAHE SEARCH — FERRAMENTA COMPLEMENTAR (PACOTE EXPERIMENTAL)
  Todos os direitos reservados à Plataforma Tycho Brahe © 2026
================================================================================

PLATAFORMA TYCHO BRAHE
- Criada e desenvolvida principalmente por Luiz Henrique Lima Veronesi como
  fruto de sua tese de doutorado em Linguística no IEL/UNICAMP.
- Professora e orientadora: Profª Drª Charlotte Galves (IEL / UNICAMP).
- Referência: VERONESI, Luiz Henrique Lima. A Plataforma Tycho Brahe: um
  sistema para corpora sintaticamente anotados. 2026. 211 f. Tese (Doutorado
  em Linguística) — Instituto de Estudos da Linguagem, Universidade Estadual
  de Campinas, Campinas, 2026.
- Tese: https://www.tycho.iel.unicamp.br/upload/Luiz_Veronesi_A_Plataforma_Tycho_Brahe_Tese_2026.pdf
- Portal: https://www.tycho.iel.unicamp.br/

DACILAT
Corpora Anotados Digitais de Línguas Indígenas Brasileiras com Traduções
Automáticas é um projeto científico de documentação digital para a preservação
e análise de línguas nativas do Brasil. É associado à Plataforma Tycho Brahe,
e seus corpora contribuem para alimentá-la.
Portal: https://www.tycho.iel.unicamp.br/dacilat
Participantes: Maria Filomena Sandalo (Coordenadora); Charlotte Galves
(Pesquisadora Principal); Pablo Feliciano de Faria; Luiz Henrique Lima Veronesi;
Leonel de Alencar Araripe; Michael Becker; Vanda Pires; André Luiz Rosa Teixeira;
Juliana Lopes Gurgel; Ticiana Andrade de Sena; Osmar Francisco; Hilário Silva;
Sandra Silva (colaboradores).

FERRAMENTA COMPLEMENTAR
Tycho Brahe Search foi elaborado por Gabriel Pinheiro como ferramenta
complementar, a partir de sua proposta de arquitetura para a implementação de
núcleos cartográficos. Essa menção não transfere autoria ou direitos da
Plataforma Tycho Brahe.

ESTADO DO PACOTE
Este pacote é experimental e não certifica a busca, a transdução cartográfica
integral ou uma distribuição estável. Consulte docs/STATUS_DE_ARTEFATOS.md e a
documentação Marco 2/Marco 3 antes de qualquer uso científico ou publicação.

COMO EXECUTAR
1. Dê duplo clique em INICIAR_TYCHO_BRAHE.bat ou Tycho Brahe Search.exe.
2. Não é necessário instalar Python, Node.js ou Rust para abrir o pacote.
================================================================================
""",
        encoding="utf-8",
    )


def write_launcher(destination: Path) -> None:
    destination.write_text(
        """@echo off
title Tycho Brahe Search - Ferramenta Complementar Experimental
echo =========================================================================
echo   TYCHO BRAHE SEARCH - FERRAMENTA COMPLEMENTAR EXPERIMENTAL
echo   Todos os direitos reservados à Plataforma Tycho Brahe © 2026
echo   Criada e desenvolvida principalmente por Luiz Henrique Lima Veronesi
echo   Orientadora: Profa. Dra. Charlotte Galves (IEL / UNICAMP)
echo   Search complementar elaborado por Gabriel Pinheiro
echo =========================================================================
echo.
start "" "%~dp0Tycho Brahe Search.exe"
exit
""",
        encoding="utf-8",
    )


def copy_documentation() -> None:
    PORTABLE_DOCS_DIR.mkdir(parents=True, exist_ok=True)
    for name in PORTABLE_DOCUMENTS:
        source = ROOT / "docs" / name
        if source.is_file():
            shutil.copy2(source, PORTABLE_DOCS_DIR / name)
        else:
            print(f"==> Documento não encontrado; não copiado: {source}")
    shutil.copy2(require_file(ROOT / "README.md", "README canônico"), PORTABLE_DIR / "README.md")


def main() -> int:
    print(f"==> Preparando release experimental em: {RELEASE_DIR}")
    for directory in (PORTABLE_DIR, INSTALLERS_DIR, PORTABLE_DIR / "bin", PORTABLE_DIR / "corpus_data"):
        directory.mkdir(parents=True, exist_ok=True)

    tauri_exe = require_file(
        ROOT / "tycho-desktop" / "src-tauri" / "target" / "release" / "tycho-desktop.exe",
        "executável Tauri",
    )
    sidecar_exe = require_file(
        ROOT / "tycho-desktop" / "src-tauri" / "bin" / "tycho_backend-x86_64-pc-windows-msvc.exe",
        "executável sidecar",
    )
    shutil.copy2(tauri_exe, PORTABLE_DIR / "Tycho Brahe Search.exe")
    shutil.copy2(sidecar_exe, PORTABLE_DIR / "bin" / "tycho_backend-x86_64-pc-windows-msvc.exe")
    shutil.copy2(sidecar_exe, PORTABLE_DIR / "bin" / "tycho_backend.exe")

    for database_name in ("corpus_fase3.db", "corpus_cartografia.db"):
        if copy_if_present(ROOT / "corpus_data" / database_name, PORTABLE_DIR / "corpus_data" / database_name):
            print(f"==> Banco experimental copiado: {database_name}")

    msi_source = ROOT / "tycho-desktop" / "src-tauri" / "target" / "release" / "bundle" / "msi" / "Tycho Brahe Search_0.1.0_x64_en-US.msi"
    nsis_source = ROOT / "tycho-desktop" / "src-tauri" / "target" / "release" / "bundle" / "nsis" / "Tycho Brahe Search_0.1.0_x64-setup.exe"
    copy_if_present(msi_source, INSTALLERS_DIR / "Tycho_Brahe_Search_v1.0.0_x64.msi")
    copy_if_present(nsis_source, INSTALLERS_DIR / "Tycho_Brahe_Search_v1.0.0_Setup.exe")

    write_launcher(PORTABLE_DIR / "INICIAR_TYCHO_BRAHE.bat")
    write_portable_readme(PORTABLE_DIR / "LEIA-ME.txt")
    copy_documentation()

    zip_path = RELEASE_DIR / "TychoBrahe_v1.0.0_Windows_x64_Portable.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for file_path in PORTABLE_DIR.rglob("*"):
            if file_path.is_file():
                archive.write(file_path, file_path.relative_to(PORTABLE_DIR))
    print(f"==> Release experimental compactada: {zip_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
