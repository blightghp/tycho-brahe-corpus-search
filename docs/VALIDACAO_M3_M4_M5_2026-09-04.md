# Validação controlada M3, M4 e M5 — 4 de setembro de 2026

## Escopo e limite de publicação

Esta validação qualifica a prévia técnica `v0.2.0` do **cliente desktop**. Ela
não converte o Marco 3 em transdução cartográfica integral nem autoriza a
distribuição do Corpus Histórico do Português Tycho Brahe. O instalador não
contém PSD, M2, M3 ou credenciais; todo acesso a dados continua submetido aos
[termos oficiais do corpus](https://www.tycho.iel.unicamp.br/corpus/termos.html).

As fontes canônicas foram auditadas em clone limpo no commit `fc0d0ec`, com
resultado `integrity_status: PASS`, 57 arquivos verificados e nenhuma falha.
As alterações da prévia `v0.2.0` posteriores a esse ponto tratam apenas de
interface, versão, empacotamento, ícone, termos e documentação; não alteram
fontes PSD, regras M3 ou a ponte M4/M5.

## M3 — reconstrução e promoção controlada

| Verificação | Resultado |
|---|---|
| Documentos PSD | 30 |
| Blocos físicos | 63.784 |
| Candidatos históricos | 56.936 |
| Importados M2 | 56.926 |
| Rejeitados explicitamente | 10 |
| Nós de origem M2 | 2.385.719 |
| Entidades M3 | 2.246.518 |
| Decisões M3 | 3.048.189 |
| Evidências M3 | 3.849.860 |
| Evidências cartográficas | 4.656 |

A verificação integral do M3 reconstruído retornou `ok: true`, sem erros,
com 56.936 candidatos no escopo e 56.926 sentenças analisadas. A identidade da
fonte M2 foi `b4c867fc166d74e7cfe7eac26850353fc3ef9553327d952ba01f018ba35283b8`;
o M3 promovido retornou
`12163153dce9dfa98cfd8d56ab2b611ade44d326bc45e3cd3f79ecea8ab08b8a`.

O provisionador instalou o M3 no caminho controlado da aplicação sob
`%APPDATA%\br.unicamp.iel.tycho-brahe\artifacts\marco3`, usando hard link no
mesmo volume e registrando recibo com hashes e contagens. O banco não foi
incluído no repositório nem no bundle.

## M4 — busca evidencial e proveniência

Foi executada uma busca `NUCLEO_LEXICAL`, com limite 1, sobre o M3 promovido e
com `--verify-source` contra M2 e o manifesto canônico. O retorno foi:

| Campo | Resultado |
|---|---|
| Estado | `ok: true` |
| Modo de validação | `integral_m3_m2` |
| Validação completa da fonte | `true` |
| Ocorrências | 1 |
| Âncora demonstrativa | `NPR · Senhor` |
| Regra | `L_N` |

O sidecar M4 dedicado também foi executado diretamente contra o M3 promovido:
retornou código de saída 0, JSON válido, uma ocorrência e bytes UTF-8 válidos
para `evidência`. O resultado operou no modo leve esperado
`precondicao_m3_promovido`, pois a validação integral já havia sido realizada
na promoção controlada.

## M5 — ponte desktop e pacote release

O build release `v0.2.0` concluiu com o frontend React/Tailwind e a ponte
Tauri/Rust. Os sete testes da ponte M4 passaram, incluindo allowlist de
critérios, rejeição de campos de caminho, localização fixa do artefato, vetor
de argumentos posicional e validação do contrato JSON.

O sidecar que o Tauri coloca no pacote (`tycho_m4_search.exe`) foi executado
após o build contra o mesmo M3 controlado e retornou `ok: true`, uma ocorrência
e código de saída 0. O script NSIS gerado lista explicitamente o sidecar e não
lista M3 como recurso. O executável desktop release iniciou e apresentou uma
janela responsiva no ambiente de validação.

## Instalador e aceite

O build `npm run tauri -- build --bundles nsis` gerou:

```text
Tycho Brahe Search_0.2.0_x64-setup.exe
SHA-256: E4D8E58554B41E32F00A71861E2D82E2D2FEF6D34F53BD7148DCD96D344DA5F0
```

O script NSIS produzido contém `MUI_PAGE_LICENSE` e usa a cópia gerada de
`installer/TERMOS_DE_USO_E_DIREITOS.txt`. As 82 linhas do arquivo gerado foram
comparadas à fonte versionada sem diferenças; a página inclui o URL canônico
dos [termos oficiais do corpus](https://www.tycho.iel.unicamp.br/corpus/termos.html),
os créditos da Plataforma Tycho Brahe, de Luiz Henrique Lima Veronesi,
Charlotte Galves, IEL/UNICAMP e a delimitação da ferramenta complementar de
Gabriel Pinheiro.

O hash acima é do arquivo final validado que será enviado à release.

## Gates executados

```text
M3 integral M3↔M2: PASS
Consulta M4 integral: PASS
Sidecar M4 fonte: PASS
Sidecar M4 empacotado: PASS
npm run build: PASS
cargo fmt -- --check: PASS
cargo test --lib m4_bridge: 7 passed
python -m unittest discover: 59 passed, 1 skipped
npm audit --audit-level=moderate: 0 vulnerabilities
NSIS bundle: PASS
```

O artefato deve permanecer classificado como prévia técnica não assinada até
haver assinatura de código e a certificação científica independente prevista
na política de artefatos.
