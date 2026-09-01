# Busca rastreável — Marco 4

## Estado e escopo

O Marco 4 introduz uma busca de linha de comando sobre o SQLite `m3_*`
promovido pelo Marco 3. A consulta é estritamente somente leitura: não usa os
bancos legados, não altera `recon_*`, não reescreve o PSD e não cria projeções
cartográficas.

Nesta etapa, a busca está disponível pela API Python e pela CLI
[`../python_backend/busca_rastreavel.py`](../python_backend/busca_rastreavel.py).
A ponte Tauri/React agora possui um sidecar dedicado e exige um artefato Marco
3 provisionado em local controlado. A distribuição ainda não é certificada e
o M3 não é embutido no instalador; veja
[INTEGRACAO_DESKTOP_M4.md](INTEGRACAO_DESKTOP_M4.md) antes de usar a tela.

## Contrato científico e de segurança

O arquivo de análise é aberto por URI SQLite com `mode=ro` e `query_only=ON`.
Os filtros são valores vinculados por parâmetros; nenhum valor fornecido pelo
usuário é interpolado como identificador ou fragmento de SQL. Ao menos um
filtro é obrigatório. Eles são exatos, conjuntivos e limitados a 1--500
ocorrências. A ordenação é estável:

```text
caminho relativo → ordinal do bloco → sentença Marco 2 → preordem → entidade
```

Antes de buscar, o módulo exige uma pré-condição leve de artefato promovido:
schema Marco 3, uma execução `PROMOVIDA`, um conjunto de regras, uma âncora
Marco 2 e metadados internos coerentes. Para uma prova completa M3--M2, use
`--verify-source`; essa operação revalida hashes, folhas, âncoras, evidências e
fonte, por isso é deliberadamente mais custosa que uma consulta interativa.

## Filtros disponíveis

| Opção | Significado |
|---|---|
| `--entity-type` | Um tipo Marco 3, como `NUCLEO_LEXICAL`, `NUCLEO_FUNCIONAL`, `PROJECAO_FONTE` ou `EVIDENCIA_CARTOGRAFICA`. |
| `--label` | Rótulo analítico exato, por exemplo `NUCLEO_LEXICAL_NOMINAL`. |
| `--projection` | Projeção-fonte ou projeção apenas evidenciada, por exemplo `CP` ou `MoodP_evaluative`. |
| `--token` | Token de origem exato. |
| `--rule` | Identificador da regra Marco 3, por exemplo `L_N` ou `E_ADV`. |
| `--limit` | Máximo determinístico de resultados, entre 1 e 500 (padrão: 50). |

Uma evidência `MoodP_evaluative`, por exemplo, continua sendo uma evidência
lexical de um `ADVP`; ela não é uma afirmação de que o corpus contém um nó
`MoodP` injetado.

## Exemplos

```powershell
$m2 = 'C:\builds\tycho\corpus_marco2.sqlite'
$m3 = 'C:\builds\tycho\corpus_marco3_evidencial.sqlite'

# Núcleos nominais observados pelo rótulo PSD e pela regra L_N.
python python_backend/busca_rastreavel.py search `
  --db $m3 `
  --entity-type NUCLEO_LEXICAL `
  --label NUCLEO_LEXICAL_NOMINAL `
  --rule L_N `
  --limit 25

# Evidência cartográfica lexical; não cria uma projeção no corpus.
python python_backend/busca_rastreavel.py search `
  --db $m3 `
  --entity-type EVIDENCIA_CARTOGRAFICA `
  --projection MoodP_evaluative `
  --rule E_ADV `
  --limit 25

# Revalidação integral da derivação antes da consulta.
python python_backend/busca_rastreavel.py search `
  --db $m3 `
  --token felizmente `
  --entity-type NUCLEO_LEXICAL `
  --verify-source `
  --source-db $m2 `
  --source-manifest docs/manifests/marco2_importacao_rastreavel_2026-08-31.json
```

## Resultado obrigatório por ocorrência

A saída é JSON e contém sempre:

- `analysis`: versão e hashes do executor, das regras e da fonte Marco 2;
- `origin`: caminho relativo, documento, bloco, ordinais, hashes, sentença e
  classe estrutural de origem;
- `anchor`: nó Marco 2, rótulo, função, preordem, posição de folha e token;
- `entity`: classificação Marco 3 e, quando cabível, projeção-fonte ou apenas
  evidenciada;
- `decision`: regra, confiança heurística, status da evidência, revisão e
  justificativa;
- `evidence`: valores versionados com SHA-256 e descrição.

Assim, uma ocorrência nunca é retornada como um rótulo solto: ela conserva a
cadeia necessária para auditoria linguística e reprodução.

## Uso pelo desktop

O painel **Busca Evidencial (M4)** usa o mesmo contrato, mas não recebe um
caminho de banco da interface. Antes de iniciá-lo, gere o sidecar e provisione
um M3 validado, como descrito em
[INTEGRACAO_DESKTOP_M4.md](INTEGRACAO_DESKTOP_M4.md). Quando o artefato estiver
ausente, a UI deve informar `M4_ARTIFACT_UNAVAILABLE`, e não recorrer a bancos
Fase 3/cartografia.

## Testes

```powershell
python python_backend/test_busca_rastreavel.py
```

A suíte constrói um M2/M3 mínimo pelas APIs públicas e verifica importação sem
NLTK/spaCy, proveniência, evidência, filtros conjuntivos, ordenação,
parametrização contra texto de injeção SQL, limites, pré-condição Marco 3,
validação integral opcional e saída JSON da CLI.
