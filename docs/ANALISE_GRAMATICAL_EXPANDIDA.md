# Análise gramatical expandida — Marco 3

## Estado verificável

O Marco 3 implementa uma camada derivada, versionada e auditável sobre um
banco `recon_*` validado do Marco 2. Ela não modifica o PSD, não atualiza
`recon_*` e não lê os bancos legados `corpus_fase1.db`,
`corpus_cartografia.db` ou `corpus_fase3.db`.

O artefato é um SQLite novo, produzido em *staging* no diretório do destino e
promovido apenas depois de validar a base Marco 2, o conjunto de regras, as
âncoras de origem, as folhas, o grafo de relações e as *foreign keys* internas.
Ele não declara que uma expansão cartográfica completa foi concluída: a
camada inicial registra evidências verificáveis, não injeta nós invisíveis nem
reescreve árvores do corpus.

## Princípio científico

Uma etiqueta no catálogo teórico não é, por si, uma observação no corpus.
Portanto, no conjunto `gramatica-expandida-evidencial@1`:

- `CP`, `IP`, `NP`, `PP`, `VP`, `ADJP`, `ADVP` e `CONJP` são preservados como
  **projeções-fonte** quando já ocorrem no PSD;
- `C`, `D` e `P` são registrados como núcleos/elementos-fonte apenas no
  contexto estrutural direto correspondente;
- `N`, `NPR`, `PRO`, `WPRO`, `ADJ`, `ADV` e `VB*` são reconhecidos como
  núcleos lexicais pela própria etiqueta PSD;
- `HV*`, `TR*`, `SR*` e `ET*` ficam como evidência de auxiliar/cópula, sem
  afirmar `T`, `AspP` ou `VoiceP`;
- categorias vazias (`*...*`) e o marcador `0`, bem como pontuação, são
  preservados nas folhas e explicitamente excluídos de candidaturas a núcleo;
- candidaturas de cabeça são ligadas somente por relações pai–filho imediatas
  já presentes em `recon_relacoes`; quando há mais de uma candidata, o estado
  é `AMBIGUO`, sem escolha silenciosa;
- um `ADVP` cujo rendimento completo coincide, após normalização NFC/casefold,
  com o léxico congelado pode registrar uma **evidência lexical cartográfica**
  (por exemplo, `felizmente` → `MoodP_evaluative`). Isso não cria `MoodP`,
  `ForceP`, `FinP`, `Root` ou qualquer outro nó novo.

As confianças armazenadas são marcadas como `HEURISTICA`; elas não representam
probabilidades calibradas ou julgamento humano. Todas começam com estado de
revisão `PENDENTE`.

## Entradas e contrato de saída

O executor [`../python_backend/analise_gramatical_recon.py`](../python_backend/analise_gramatical_recon.py)
usa apenas a biblioteca padrão do Python e importa o catálogo estático de
[`../python_backend/cartografia_schema.py`](../python_backend/cartografia_schema.py).
O bundle declarativo
[`../python_backend/regras_gramatica_expandida_v1.json`](../python_backend/regras_gramatica_expandida_v1.json)
é parte da identidade da execução.

Para cada banco Marco 3, ficam registrados:

1. SHA-256 do arquivo SQLite Marco 2, SHA-256/snapshot do manifesto externo,
   versão do schema e digest semântico das sentenças de origem;
2. SHA-256 do bundle de regras, do catálogo de projeções e do próprio executor;
3. uma linha de escopo para cada candidato histórico do ledger Marco 2 —
   `ANALISADA` para importados e `FORA_ESCOPO_REJEITADA` para as rejeições;
4. uma âncora materializada para cada `recon_no`, incluindo rótulo, função,
   coordenadas nested-set, pai, ordem entre irmãos e token;
5. decisões, entidades, relações e evidências com regra, confiança, método e
   estado de revisão;
6. uma prova por sentença de que a sequência, a contagem e o SHA-256 das
   folhas ancoradas são exatamente os do Marco 2.

As tabelas principais são:

| Tabela | Função |
|---|---|
| `m3_base_origem` | Âncora externa e semântica do banco Marco 2. |
| `m3_conjuntos_regras`, `m3_regras`, `m3_catalogo_projecoes` | Regras e vocabulário teórico congelados. |
| `m3_escopo_blocos`, `m3_sentencas_escopo`, `m3_nos_ancora` | Espelho auditável do escopo fonte. |
| `m3_decisoes`, `m3_entidades`, `m3_relacoes`, `m3_evidencias` | Análise rastreável por nó e relação. |
| `m3_revisoes` | Base append-only para revisão humana futura. |

SQLite não aplica chaves estrangeiras entre arquivos. Por isso, as chaves
internas Marco 3 são combinadas com a checagem externa do banco Marco 2 por
SHA-256 e pela revalidação das âncoras antes da promoção e na verificação.

## Construir e verificar

Primeiro construa e valide o Marco 2. Em seguida, escolha outro destino —
nunca dentro de `corpus_data/` e nunca no mesmo arquivo da fonte:

```powershell
$m2 = 'C:\builds\tycho\corpus_marco2.sqlite'
$m3 = 'C:\builds\tycho\corpus_marco3_evidencial.sqlite'

python python_backend/analise_gramatical_recon.py build `
  --source-db $m2 `
  --source-manifest docs/manifests/marco2_importacao_rastreavel_2026-08-31.json `
  --ruleset python_backend/regras_gramatica_expandida_v1.json `
  --output $m3

python python_backend/analise_gramatical_recon.py verify `
  --db $m3 `
  --source-db $m2 `
  --source-manifest docs/manifests/marco2_importacao_rastreavel_2026-08-31.json `
  --ruleset python_backend/regras_gramatica_expandida_v1.json
```

O parâmetro `--replace` só substitui um destino existente depois de toda a
validação do staging. Alterar o banco Marco 2, o manifesto, o arquivo de
regras, o catálogo ou o executor torna a verificação inválida até que uma nova
análise versionada seja construída.

## Construção integral observada

Em 1º de setembro de 2026, uma construção integral contra o banco Marco 2
validado produziu, fora do repositório:

| Medida | Resultado |
|---|---:|
| Candidatos do ledger Marco 2 no escopo | 56.936 |
| Sentenças importadas analisadas | 56.926 |
| Âncoras de nós fonte | 2.385.719 |
| Decisões auditáveis | 3.048.189 |
| Entidades de análise | 2.246.518 |
| Relações locais de candidatura a núcleo | 801.671 |
| Evidências registradas | 3.849.860 |
| Exclusões explícitas (vazios/pontuação) | 258.870 |
| Evidências lexicais cartográficas de ADVP | 4.656 |

Os dez candidatos rejeitados pelo Marco 2 permanecem visíveis em
`m3_escopo_blocos` como `FORA_ESCOPO_REJEITADA`; eles não são apagados nem
passam a integrar resultados analíticos.

## Limites e próximo marco

Este marco habilita uma busca que possa devolver, para cada correspondência, a
identidade fonte, a regra, a evidência, a confiança heurística e o estado de
revisão. Ele ainda não é a busca de usuário final nem uma transdução completa
dos cinco domínios. O próximo marco deve criar o índice/contrato de busca
somente sobre esta camada validada, com consultas parametrizadas e retorno de
proveniência obrigatório.
