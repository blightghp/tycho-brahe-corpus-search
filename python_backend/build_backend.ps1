<#
.SYNOPSIS
    Gera o sidecar histórico do motor Python para o bundle Tauri.

.DESCRIPTION
    Usa PyInstaller instalado no interpretador informado, sem depender de um
    caminho pessoal ou de uma versão específica do Python. Os bancos legados
    continuam externos ao executável e são resolvidos apenas em tempo de uso.
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
$buildDirectory = Join-Path $backendRoot 'build'
$distDirectory = Join-Path $backendRoot 'dist'
$entryPoint = Join-Path $backendRoot 'pesquisa_sintatica.py'
$targetName = 'tycho_backend'
$targetExecutable = Join-Path $outputDirectory "$targetName-x86_64-pc-windows-msvc.exe"
$hiddenImports = @(
    'cartografia_schema',
    'tokenizador_cartografico',
    'metadata_tycho',
    'oracle',
    'rewriter',
    'spacy'
)

if (-not (Test-Path -LiteralPath $entryPoint -PathType Leaf)) {
    throw "Entrada do backend não encontrada: $entryPoint"
}

& $PythonExecutable -m PyInstaller --version
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller não está disponível em '$PythonExecutable'. Instale python_backend/requirements-build.txt no ambiente de build."
}

$pyInstallerArgs = @(
    '-m', 'PyInstaller',
    '--noconfirm',
    '--clean',
    '--onefile',
    '--name', $targetName,
    '--distpath', $distDirectory,
    '--workpath', $buildDirectory,
    '--specpath', $buildDirectory,
    '--paths', $backendRoot
)
foreach ($module in $hiddenImports) {
    $pyInstallerArgs += "--hidden-import=$module"
}
$pyInstallerArgs += $entryPoint

Write-Host "Compilando $entryPoint com PyInstaller..."
& $PythonExecutable @pyInstallerArgs
if ($LASTEXITCODE -ne 0) {
    throw 'A geração do sidecar histórico falhou.'
}

$generatedExecutable = Join-Path $distDirectory "$targetName.exe"
if (-not (Test-Path -LiteralPath $generatedExecutable -PathType Leaf)) {
    throw "Executável histórico não encontrado após o build: $generatedExecutable"
}

if ($SkipTauriCopy) {
    Write-Host "Sidecar histórico gerado sem copiar para o bundle: $generatedExecutable"
    return
}

New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null
Copy-Item -LiteralPath $generatedExecutable -Destination $targetExecutable -Force
Write-Host "Sidecar histórico gerado: $targetExecutable"
