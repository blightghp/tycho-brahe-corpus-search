# Revisão AppSec (Application Security) - Tycho Brahe

Este documento consolida os resultados da auditoria de segurança de software ponta a ponta realizada sobre o projeto. Foram validadas as camadas do Frontend, Backend em Rust e Motor em Python.

> [!IMPORTANT]
> Esta revisão cobre controles de segurança no escopo de código analisado. Ela
> não certifica disponibilidade funcional, integridade do corpus, validade
> linguística, completude dos bancos ou aprovação de uma distribuição. Para o
> estado de publicação, consulte [STATUS_DE_ARTEFATOS.md](STATUS_DE_ARTEFATOS.md).

## 1. Prevenção contra SQL Injection (Python Backend)
Todos os scripts Python responsáveis por interagir com os bancos SQLite (`build_db.py`, `build_db_fase3.py`, `pesquisa_sintatica.py`, etc.) foram auditados.
- **Constatação**: Não há concatenações inseguras (`f"..."` ou `%s`) de strings geradas pelo usuário diretamente em *statements* SQL.
- **Validação**: Todas as queries utilizam *parameterized queries* com tuplas `(arg,)`.
- **Refinamento Aplicado**: Implementada a função segura `escape_like()` em `pesquisa_sintatica.py` para escapar internamente wildcards do SQL (`%`, `_`), mitigando *Wildcard Injection DoS*.

## 2. Prevenção de RCE e Command Injection (Tauri / Rust)

A orquestração dos executáveis Python a partir da interface React usa o sistema
Tauri Sidecar.

- **Constatação**: Os argumentos são formatados localmente (`Vec<String>`) e atrelados ao método `.args()`, que não invoca chamadas em _shell_ (desviando de ataques envolvendo `&&` ou `|`).
- **Rota Marco 4**: `run_m4_search` recebe um tipo Rust com `deny_unknown_fields`, aceita apenas os filtros documentados, exige ao menos um deles, limita texto/resultado e rejeita valores que começariam uma nova opção do `argparse`. A UI não pode enviar `db`, `args`, `command` ou `--verify-source`.
- **Refinamento Aplicado**: A ponte `m4_bridge.rs` canonicaliza somente o M3 já provisionado sob o diretório de dados do aplicativo, verifica sua contenção e monta um vetor de argumentos fixo. A resposta do sidecar é limitada e validada contra o contrato JSON antes de retornar ao frontend.
- **Legado**: `run_backend_query` conserva os limites de tamanho de `acao` e `args` e o máximo de argumentos por requisição. Isso reduz tentativas locais de sobrecarga de memória, mas a rota legada não é a busca Marco 4.

## 3. Sandboxing de Escopo e Allowed Binaries (Tauri `default.json`)

- **Constatação**: O arquivo de configuração principal em `capabilities/default.json` bloqueia execução arbitrária e permite `shell:allow-execute` apenas para `bin/tycho_backend` e `bin/tycho_m4_search`, ambos como `sidecar: true`.
- **Status**: Escopo explícito para dois binários conhecidos; não há permissão de terminal genérica.

## 4. Política de Segurança de Conteúdo Frontend (CSP)
Para mitigar a vulnerabilidade a ataques *Cross-Site Scripting* (XSS) locais pelo navegador/WebView interno do aplicativo.
- **Constatação Anterior**: A configuração de CSP estava configurada incorretamente no `tauri.conf.json` como `"csp": null`.
- **Correção Aplicada**: Refatorado para restrição ativa:
  ```json
  "csp": "default-src 'self'; connect-src 'self' ipc: http://ipc.localhost; img-src 'self' asset: data:; style-src 'self' 'unsafe-inline';"
  ```
- **React Frontend**: Ausência confirmada de chamadas à API desprotegida `dangerouslySetInnerHTML` e injeções JavaScript `eval()` em toda a árvore DOM no TypeScript.

## 5. Resiliência de Manipulação de Path e Encoding
Ataques baseados em Directory Traversal (`../..`) ou Unicode.
- **Python**: A reconfiguração da entrada/saída `sys.stdout.reconfigure(encoding="utf-8")` na cabeça do `pesquisa_sintatica.py` estabiliza e higieniza sub-processos do sidecar em máquinas Windows com locale desconfigurado (`cp1252`).
- A rota M4 não recebe arquivos ou identificadores de banco pelo IPC. O caminho fixo é canonicalizado e precisa permanecer abaixo do diretório de dados do aplicativo; não há fallback para CWD, `%TEMP%`, variáveis de ambiente ou bancos legados.

## Conclusão

Os controles descritos devem ser reavaliados após a reconstrução da busca,
persistência e empacotamento. Nenhuma credencial `hardcoded` ou chave
criptográfica ativa foi identificada no escopo analisado. Esta constatação não
constitui certificação de *Release Candidate*.
