# Motor Rust (Tauri / Core)

O `src-tauri` é o alicerce onde repousa o sistema de baixo nível da aplicação Desktop. Ele foi escrito usando a especificação do **Tauri V2**, cujo paradigma é maximizar segurança bloqueando IO desenfreado e manter o empacotamento pequeno, focado nas *WebView* nativas do Windows.

> [!WARNING]
> A distribuição não está validada. A rota Marco 5 resolve exclusivamente um
> M3 previamente provisionado em `%APPDATA%`; os recursos e bancos legados
> continuam fora dessa garantia. Consulte
> [`../../docs/STATUS_DE_ARTEFATOS.md`](../../docs/STATUS_DE_ARTEFATOS.md).

## Conexões e Gates (A Ponte IPC)
A parte crítica deste motor é habilitar que a requisição visual (feita no TS/React) acione um processo pesado e longo (Python/Banco) e retorne uma resposta confiável.

- **Gate de Execução**: Definido no `capabilities/default.json`. O Tauri não roda comandos aleatórios no terminal do usuário. Ele autoriza especificamente os sidecars legados `tycho_backend.exe` e o dedicado `tycho_m4_search.exe`.
- **Rota M4 controlada**: `run_m4_search` aceita somente critérios tipados, sem caminho de banco ou argumentos livres. `m4_bridge.rs` canonicaliza exclusivamente `%APPDATA%\br.unicamp.iel.tycho-brahe\artifacts\marco3\corpus_marco3_evidencial.sqlite` e o sidecar recebe um vetor fixo de argumentos, sem shell.
- **Provisionamento**: o SQLite M3 não é um `resource` do bundle. `provisionar_m4_artifact.py` o valida contra o M2 antes de instalá-lo no caminho controlado. Se ele não existir, a busca falha explicitamente, sem fallback para bases legadas.
- **LTO**: A compilação `Cargo.toml` tem a *Link-Time Optimization* ativa (`lto = true`). Ele limpa binários lixo na geração de release.

## Referência histórica: como gerar instaladores
Na pasta mãe `tycho-desktop`, execute:
```bash
npm run tauri build
```
O output gera executáveis nativos em `target/release/bundle`, mas eles não são
publicáveis nesta etapa. Antes do build, gere o sidecar M4 e siga
[`../../docs/INTEGRACAO_DESKTOP_M4.md`](../../docs/INTEGRACAO_DESKTOP_M4.md).
