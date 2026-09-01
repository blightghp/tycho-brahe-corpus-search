# Auditoria de cobertura e pendências — Marco 6

## Objetivo

O Marco 6 transforma o conteúdo integral de um SQLite Marco 3 promovido em um
relatório JSON de cobertura e de pendências para curadoria. Ele conta o escopo
importado/rejeitado, sentenças, âncoras, decisões, núcleos lexicais e
funcionais, relações, regras, projeções-fonte, projeções apenas evidenciadas e
tipos de evidência.

O relatório é deliberadamente **somente leitura**. Ele não altera arquivos
PSD, Marco 2, Marco 3 ou a tabela `m3_revisoes`; tampouco converte uma decisão
heurística `PENDENTE` em aprovação linguística.

## Pré-condição e execução

Por padrão, a ferramenta exige o contrato leve de um M3 promovido: schema,
execução, regras e âncora Marco 2 coerentes. Para um retrato de liberação, a
opção `--verify-source` revalida integralmente M3↔M2 antes das agregações. Por
percorrer milhões de registros, trate a auditoria integral como operação em
lote, não como consulta interativa da tela desktop.

```powershell
$m2 = 'C:\builds\tycho\corpus_marco2.sqlite'
$m3 = 'C:\builds\tycho\corpus_marco3_evidencial.sqlite'

# Retrato somente leitura com até 20 amostras determinísticas de evidência
# cartográfica pendente.
python python_backend/auditar_cobertura_m3.py report `
  --db $m3 `
  --sample-limit 20

# Prova integral da derivação antes da auditoria.
python python_backend/auditar_cobertura_m3.py report `
  --db $m3 `
  --sample-limit 50 `
  --verify-source `
  --source-db $m2 `
  --source-manifest docs/manifests/marco2_importacao_rastreavel_2026-08-31.json
```

`--sample-limit` aceita de 0 a 200. As amostras não são uma lista de
prioridade científica: são um recorte estável, ordenado por origem, de
evidências cartográficas que continuam pendentes.

## Contrato do relatório

A saída possui quatro blocos:

- `analysis`: identidade do M3, do executor, das regras e da fonte Marco 2;
- `validation`: informa se foi usada a pré-condição leve ou a validação
  integral M3↔M2;
- `coverage`: agregações auditáveis por estado de escopo, tipo de decisão,
  status de evidência, entidade, regra, relação, tipo de evidência e projeção;
- `curation`: tamanho do backlog `PENDENTE`, eventos de revisão já registrados
  e amostras com arquivo/bloco/sentença/âncora/regra/projeção/hash de origem.

Cada amostra é uma referência ao dado de origem, não uma árvore cartográfica
nova. `MoodP_evaluative`, por exemplo, continua uma evidência lexical ligada a
um `ADVP` observado até que a revisão humana documentada sustente outra
conclusão.

## Execução integral observada

Em 1º de setembro de 2026, o relatório foi executado sobre o M3 integral já
validado no provisionamento Marco 5. A própria auditoria usou a pré-condição
de M3 promovido e não alterou o arquivo. O recorte verificável foi:

| Medida | Resultado |
|---|---:|
| Blocos `IMPORTADO` / `ANALISADA` | 56.926 |
| Blocos `REJEITADO` / `FORA_ESCOPO_REJEITADA` | 10 |
| Sentenças | 56.926 |
| Âncoras | 2.385.719 |
| Decisões pendentes | 3.048.189 |
| Entidades pendentes | 2.246.518 |
| Relações pendentes | 801.671 |
| Evidências cartográficas pendentes | 4.656 |
| Eventos humanos de revisão registrados | 0 |

As entidades foram decompostas assim:

| Tipo | Ocorrências |
|---|---:|
| `PROJECAO_FONTE` | 905.125 |
| `NUCLEO_LEXICAL` | 562.262 |
| `NUCLEO_FUNCIONAL` | 299.312 |
| `EXCLUSAO` | 258.870 |
| `NUCLEO_FRONTEIRA` | 172.210 |
| `EVIDENCIA_AUXILIAR` | 44.083 |
| `EVIDENCIA_CARTOGRAFICA` | 4.656 |

As 4.656 evidências cartográficas distribuíram-se por dez projeções apenas
evidenciadas: `AspP_completive` (16), `AspP_continuative` (2.063),
`AspP_habitual` (32), `AspP_proximative` (46), `ModP_epistemic` (106),
`MoodP_evaluative` (41), `MoodP_evidential` (6), `MoodP_speech_act` (6),
`T_anterior` (2.105) e `T_past_future` (235). São gatilhos lexicais
auditáveis da regra `E_ADV`, não inserções de nós na fonte.

## Uso para curadoria

O fluxo correto é:

1. Reconstruir e validar M2 e M3; não usar os bancos legados.
2. Gerar a auditoria Marco 6 e escolher um recorte documentável.
3. Examinar a cadeia de proveniência pela Busca Marco 4/5: fonte, bloco,
   âncora, regra, evidência e justificativa.
4. Registrar uma decisão humana apenas em um processo de curadoria autorizado
   e versionado. O Marco 6 não escreve essa decisão por conta própria.
5. Reconstruir/validar a camada derivada quando uma mudança de regras for
   aprovada; nunca editar silenciosamente o PSD ou promover a heurística.

## Testes

```powershell
python python_backend/test_auditar_cobertura_m3.py
```

A suíte constrói M2/M3 mínimos pelas APIs públicas, verifica o contrato JSON,
a validação integral opcional, os limites de amostra, a rejeição de artefatos
inválidos e a imutabilidade do SQLite auditado.
