# Motor Rust (Tauri / Core)

O `src-tauri` é o alicerce onde repousa o sistema de baixo nível da aplicação Desktop. Ele foi escrito usando a especificação do **Tauri V2**, cujo paradigma é maximizar segurança bloqueando IO desenfreado e manter o empacotamento pequeno, focado nas *WebView* nativas do Windows.

> [!WARNING]
> O roteamento atual dos recursos e bancos não foi validado para distribuição.
> Esta documentação descreve a intenção de arquitetura, não uma garantia de que
> os bancos sejam copiados ou resolvidos corretamente em `%APPDATA%`. Consulte
> [`../../docs/STATUS_DE_ARTEFATOS.md`](../../docs/STATUS_DE_ARTEFATOS.md).

## Conexões e Gates (A Ponte IPC)
A parte crítica deste motor é habilitar que a requisição visual (feita no TS/React) acione um processo pesado e longo (Python/Banco) e retorne uma resposta confiável.

- **Gate de Execução**: Definido no `capabilities/default.json`. O Tauri não roda comandos aleatórios no terminal do usuário. Ele autoriza especificamente que um "sidecar" chamado `tycho_backend.exe` seja invocado.
- **Roteamento de Caminhos (Paths)**: `resources` precisa ser resolvido de forma explícita por `resource_dir` e os dados editáveis devem ser copiados para uma área gravável. Essa correção faz parte da reconstrução; o mecanismo atual não deve ser usado como referência de distribuição.
- **LTO**: A compilação `Cargo.toml` tem a *Link-Time Optimization* ativa (`lto = true`). Ele limpa binários lixo na geração de release.

## Referência histórica: como gerar instaladores
Na pasta mãe `tycho-desktop`, execute:
```bash
npm run tauri build
```
O output gera executáveis nativos em `target/release/bundle`, mas eles não são
publicáveis enquanto o Marco 1 estiver vigente.
