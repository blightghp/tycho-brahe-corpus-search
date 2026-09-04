# Integração desktop da busca evidencial — Marco 5

## O que está conectado

O desktop agora tem uma rota própria para a busca Marco 4, distinta do
sidecar e das telas legadas. A cadeia é:

```text
M4SearchPanel (React)
  → run_m4_search (Tauri/Rust tipado)
  → tycho_m4_search.exe (sidecar Python dedicado)
  → busca_rastreavel.py (SQLite M3 somente leitura)
```

O painel mostra entidade, origem, âncora, decisão e evidências; ele não tenta
converter uma evidência pendente em árvore cartográfica confirmada. A consulta
legada foi mantida como **Consulta Histórica** para auditoria e não é a rota
Marco 4.

## Fronteiras de segurança

- React envia somente `entityType`, `analyticalLabel`, `projection`, `token`,
  `ruleId` e `limit`; o tipo Rust rejeita campos extras como `db`, `args` e
  `command`.
- A ponte normaliza texto, exige ao menos um filtro, limita 1--500 e rejeita
  valores que possam ser lidos como opções pelo `argparse`.
- O caminho do banco nunca vem da interface. O Rust aceita somente:

  ```text
  %APPDATA%\br.unicamp.iel.tycho-brahe\artifacts\marco3\corpus_marco3_evidencial.sqlite
  ```

- O caminho é canonicalizado e deve permanecer dentro do diretório de dados do
  aplicativo. Não há fallback para CWD, `%TEMP%`, bancos legados ou variáveis
  de ambiente.
- Não há fallback do frontend para `Command.sidecar`; toda execução M4 passa
  pela ponte Rust. Saídas fora do contrato JSON, excessivas ou inconsistentes
  são rejeitadas.
- O sidecar emite JSON em UTF-8, inclusive quando o Windows usa uma página de
  código local diferente; a ponte decodifica os bytes diretamente como JSON.

## Preparar o sidecar e o artefato

O SQLite M3 não é empacotado: ele tem múltiplos gigabytes e só pode ser
instalado após validação. A partir da raiz do repositório:

```powershell
# Instala as dependências de build, incluindo PyInstaller.
python -m venv .venv
$python = Join-Path (Get-Location) '.venv\Scripts\python.exe'
& $python -m pip install -r python_backend/requirements-build.txt

# Gera um .exe ignorado pelo Git.
powershell -NoProfile -ExecutionPolicy Bypass -File python_backend/build_m4_sidecar.ps1 `
  -PythonExecutable $python

# Revalida M3↔M2 integralmente e instala o arquivo no local controlado.
# No mesmo volume, usa hard link; se isso não for possível, faz cópia em staging
# e confirma o SHA-256 antes da promoção.
python python_backend/provisionar_m4_artifact.py `
  --analysis-db C:\builds\tycho\corpus_marco3_evidencial.sqlite `
  --source-db C:\builds\tycho\corpus_marco2.sqlite `
  --source-manifest docs\manifests\marco2_importacao_rastreavel_2026-08-31.json
```

Uma instalação já existente é recusada por padrão. Somente após rever a origem
e o resultado da validação use `--replace`. O provisionador grava um recibo
JSON ao lado do SQLite com hashes e contagens; ele não altera PSD, M2 ou M3.

Depois de preparar ambos, inicie o aplicativo em desenvolvimento:

```powershell
cd tycho-desktop
npm run tauri dev
```

Para uma distribuição, gere primeiro o sidecar e só então execute o build
Tauri. O `tauri.conf.json` declara o binário M4, mas nunca lista o M3 como
`resource` do bundle. Os bancos legados `corpus_fase3.db` e
`corpus_cartografia.db` também não são recursos do bundle: são referências
opcionais de auditoria e não podem desbloquear ou substituir a rota M4.

## Estados esperados

| Código | Significado |
|---|---|
| `M4_ARTIFACT_UNAVAILABLE` | O M3 promovido ainda não foi provisionado no caminho controlado. |
| `M4_SIDECAR_UNAVAILABLE` | O executável dedicado não foi gerado ou não está presente no bundle. |
| `M4_INVALID_CRITERIA` | Não há filtro ou o payload não atende ao contrato restrito. |
| `M4_SIDECAR_PROTOCOL` | A resposta do processo não satisfaz o contrato JSON M4. |

Esses estados são intencionais: o aplicativo não substitui silenciosamente o
artefato requerido por uma base experimental ou por um caminho arbitrário.

## Verificação

```powershell
python python_backend/test_busca_rastreavel.py
python python_backend/test_provisionar_m4_artifact.py

cd tycho-desktop
npm run build

cd src-tauri
cargo check
cargo test --lib m4_bridge
cargo fmt -- --check
```

Em máquinas onde o `target/` local não seja gravável, defina um
`CARGO_TARGET_DIR` temporário antes do comando; isso não modifica os artefatos
versionados.
