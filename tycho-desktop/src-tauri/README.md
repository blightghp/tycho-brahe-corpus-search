# Motor Rust (Tauri / Core)

O `src-tauri` é o alicerce onde repousa o sistema de baixo nível da aplicação Desktop. Ele foi escrito usando a especificação do **Tauri V2**, cujo paradigma é maximizar segurança bloqueando IO desenfreado e manter o empacotamento pequeno, focado nas *WebView* nativas do Windows.

## Conexões e Gates (A Ponte IPC)
A parte crítica deste motor é habilitar que a requisição visual (feita no TS/React) acione um processo pesado e longo (Python/Banco) e retorne uma resposta confiável.

- **Gate de Execução**: Definido no `capabilities/default.json`. O Tauri não roda comandos aleatórios no terminal do usuário. Ele autoriza especificamente que um "sidecar" chamado `tycho_backend.exe` seja invocado.
- **Roteamento de Caminhos (Paths)**: O Tauri orquestra arquivos. Se quisermos que o Python acesse o `corpus_data/corpus_fase3.db`, registramos em `"resources"` do `tauri.conf.json`. No build/instalação, ele joga isso pro `%APPDATA%` e nosso Python engole esse dado local.
- **LTO**: A compilação `Cargo.toml` tem a *Link-Time Optimization* ativa (`lto = true`). Ele limpa binários lixo na geração de release.

## Como Gerar Release (Instaladores)
Na pasta mãe `tycho-desktop`, execute:
```bash
npm run tauri build
```
O output gerará executáveis nativos (ex: arquivos `.msi` para distribuição) em `target/release/bundle`.
