<#
.SYNOPSIS
    Gera o sidecar dedicado da busca Marco 4 para o bundle Tauri.

.DESCRIPTION
    Requer PyInstaller instalado no Python selecionado. Não baixa dependências,
    não constrói um banco M3 e não altera corpus, release ou documentação. O
    artefato M3 permanece externo ao bundle por ter múltiplos gigabytes e por
    exigir provisionamento/verificação próprios.
#>

[CmdletBinding()]
param(
    [ValidateNotNullOrEmpty()]
    [string]$PythonExecutable = 'python',

    [switch]$SkipTauriCopy
)

$ErrorActionPreference = 'Stop'

$backendRoot = Split-Path -Parent $PSCommandPath
$projectRoot = Split-Path -Parent $backendRoot
$outputDirectory = Join-Path $projectRoot 'tycho-desktop\src-tauri\bin'
$buildDirectory = Join-Path $backendRoot 'build_m4_sidecar'
$distDirectory = Join-Path $backendRoot 'dist_m4_sidecar'
$entryPoint = Join-Path $backendRoot 'm4_sidecar.py'
$targetName = 'tycho_m4_search'
$targetExecutable = Join-Path $outputDirectory "$targetName-x86_64-pc-windows-msvc.exe"

if (-not (Test-Path -LiteralPath $entryPoint -PathType Leaf)) {
    throw "Entrada M4 não encontrada: $entryPoint"
}

& $PythonExecutable -m PyInstaller --version
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller não está disponível em '$PythonExecutable'. Instale python_backend/requirements-build.txt no ambiente de build antes de gerar o sidecar M4."
}

New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null

& $PythonExecutable -m PyInstaller --noconfirm --clean --onefile `
    --name $targetName `
    --distpath $distDirectory `
    --workpath $buildDirectory `
    --specpath $buildDirectory `
    --paths $backendRoot `
    $entryPoint
if ($LASTEXITCODE -ne 0) {
    throw 'A geração do sidecar Marco 4 falhou.'
}

$generatedExecutable = Join-Path $distDirectory "$targetName.exe"
if (-not (Test-Path -LiteralPath $generatedExecutable -PathType Leaf)) {
    throw "Executável M4 não encontrado após o build: $generatedExecutable"
}

if ($SkipTauriCopy) {
    Write-Host "Sidecar Marco 4 gerado sem copiar para o bundle: $generatedExecutable"
    return
}

Copy-Item -LiteralPath $generatedExecutable -Destination $targetExecutable -Force
Write-Host "Sidecar Marco 4 gerado: $targetExecutable"
