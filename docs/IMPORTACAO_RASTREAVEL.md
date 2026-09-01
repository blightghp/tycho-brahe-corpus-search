# Marco 2 — importação PSD rastreável

Este documento descreve a base de dados reconstruída pelo Marco 2. Ela é uma
base de **fatos de origem**: preserva o PSD físico, o resultado do parser e a
topologia original. Ela ainda não é a base cartográfica expandida nem a base de
busca distribuída pela aplicação desktop.

## Contrato de entrada e identidade

O único insumo aceito é `corpus_data/*_psd.txt`, conferido contra
[`manifests/marco2_importacao_rastreavel_2026-08-31.json`](manifests/marco2_importacao_rastreavel_2026-08-31.json).
O importador nunca lê `corpus_fase1.db`, `corpus_cartografia.db`,
`corpus_fase3.db` ou `corpus.db` como entrada.

Cada grupo físico é separado por uma linha literalmente vazia em bytes
(`\r?\n\r?\n`). Uma linha contendo apenas espaços continua pertencendo à
árvore. O marcador DOS terminal `0x1A`, presente em `va_013_psd.txt`, permanece
no hash do documento e é guardado em `recon_documentos.trailer_dos`; ele não é
entregue ao parser como parte da última árvore.

A identidade imutável de uma unidade importável é:

```text
caminho_relativo + ordinal_bloco_fisico + ordinal_candidato + SHA-256_do_BLOB_bruto
```

`id_externo` é apenas metadado: pode faltar ou repetir. O caminho é sempre
portátil, por exemplo `corpus_data/a_001_psd.txt`, e não somente o nome do
arquivo.

Há dois fingerprints, propositalmente diferentes:

| Fingerprint | Domínio | Uso |
|---|---|---|
| Histórico de S-expressões | S-expressões recuperadas pelo scanner de compatibilidade | Confirma que a fonte congelada ainda corresponde ao retrato do Marco 1. |
| Físico Marco 2 | Blocos delimitados por linha vazia, seus ordinais e hashes brutos | Confirma que o ledger e os BLOBs no SQLite correspondem exatamente ao recorte que o importador usa. |

Eles não devem ser fundidos. Há grupos físicos mistos e arquivos malformados
nos quais a fronteira de S-expressão não é a fronteira física; `va_009` é um
caso observado. O manifesto Marco 2 registra ambos por documento e no resumo
global.

## Banco reconstruído

`python_backend/importador_rastreavel.py` cria um SQLite novo em staging no
mesmo volume do destino e só o promove com `os.replace` após todas as
validações. O destino é recusado se estiver dentro de `corpus_data/`; um banco
existente só pode ser substituído com `--replace`.

| Tabela | Conteúdo |
|---|---|
| `recon_documentos` | Hash e tamanho do arquivo, metadados, trailer DOS e fingerprints físicos por documento. |
| `recon_blocos_origem` | Todos os grupos físicos, com offsets, BLOB bruto, hash, ordinal físico e ordinal de candidato quando aplicável. |
| `recon_ledger_importacao` | Uma decisão obrigatória (`IMPORTADO` ou `REJEITADO`) para cada candidato histórico físico, versão do parser e hashes derivados. |
| `recon_sentencas` | Árvore normalizada derivada, texto superficial e ligação de proveniência apenas para itens `IMPORTADO`. |
| `recon_nos` e `recon_relacoes` | Topologia original em adjacência e nested set, com ordem de irmãos e de folhas. |
| `recon_meta` | Versões, caminho/hash do manifesto e contagens agregadas. |

Registros `CODE`, fragmentos e demais grupos fora do subconjunto histórico
IP/CP são preservados em `recon_blocos_origem`; eles não são descartados nem
recebem falsamente uma sentença. A ampliação de escopo para esses registros é
uma decisão explícita do próximo marco.

## Invariantes para promoção

Antes de publicar o SQLite, o importador exige:

1. hashes/tamanhos das 30 fontes, fingerprint histórico e fingerprint físico
   iguais aos do manifesto Marco 2;
2. cada candidato físico com exatamente uma decisão no ledger;
3. `IMPORTADO + REJEITADO = candidatos físicos`, sem decisão para bloco fora
   do escopo histórico;
4. cada sentença ligada a um ledger `IMPORTADO`, ao bloco e ao documento
   corretos;
5. SHA-256 do BLOB, da árvore normalizada e das folhas recompostos e conferidos;
6. texto superficial, folhas da árvore serializada e nós terminais idênticos em
   ordem e repetição;
7. uma raiz por sentença, `nós = relações + 1`, relações pai-filho válidas e
   coordenadas nested-set contínuas;
8. `integrity_check`, `foreign_key_check` e ausência de arquivos `-wal`/`-shm`.

## Resultado da reconstrução validada

| Medida | Resultado |
|---|---:|
| Arquivos PSD | 30 |
| Blocos físicos preservados | 63.784 |
| Candidatos históricos físicos com decisão | 56.936 |
| Importados | 56.926 |
| Rejeitados explicitamente | 10 |
| Nós de origem persistidos | 2.385.719 |

As dez rejeições não são perdas silenciosas. Elas permanecem consultáveis pelo
ledger e devem ser resolvidas por curadoria, correção da fonte autorizada ou
uma política de recuperação versionada; nenhum desses caminhos é executado por
este marco.

| Arquivo | Bloco físico / candidato | Motivo |
|---|---:|---|
| `a_003_psd.txt` | 913 / 848 | `MULTIPLAS_RAIZES` |
| `p_001_psd.txt` | 526 / 470 | `MULTIPLAS_RAIZES` |
| `v_004_part_psd.txt` | 301 / 241 | `MULTIPLAS_RAIZES` |
| `va_009_psd.txt` | 902 / 845 | `TOKENS_APOS_EXPRESSAO` |
| `va_013_psd.txt` | 3 / 2 | `TOKENS_APOS_EXPRESSAO` |
| `va_013_psd.txt` | 109 / 92 | `TOKENS_APOS_EXPRESSAO` |
| `va_013_psd.txt` | 416 / 367 | `TOKENS_APOS_EXPRESSAO` |
| `va_013_psd.txt` | 533 / 473 | `TOKENS_APOS_EXPRESSAO` |
| `va_013_psd.txt` | 556 / 494 | `TOKENS_APOS_EXPRESSAO` |
| `va_013_psd.txt` | 678 / 602 | `TOKENS_APOS_EXPRESSAO` |

## Execução reproduzível

Na raiz do repositório, primeiro valide o retrato atual:

```powershell
python python_backend/controle_artefatos.py verify `
  --manifest docs/manifests/marco2_importacao_rastreavel_2026-08-31.json `
  --require-experimental
```

Depois escolha um destino novo, fora de `corpus_data/`:

```powershell
$destino = 'C:\builds\tycho\corpus_marco2.sqlite'
python python_backend/importador_rastreavel.py build `
  --source-dir corpus_data `
  --manifest docs/manifests/marco2_importacao_rastreavel_2026-08-31.json `
  --output $destino

python python_backend/importador_rastreavel.py verify --db $destino
```

Para o corpus atual, `--fail-on-rejections` é um teste de política e deve
impedir a promoção, pois há dez decisões `REJEITADO` deliberadamente expostas.
Ele será apropriado após a resolução versionada de todas elas.

## Próximo marco: análise gramatical expandida

O transdutor não deve sobrescrever `recon_*`. A próxima camada deve criar uma
versão de análise separada, ligada por `sentenca_id` e `no_id` de origem, com:

1. versão e hash do conjunto de regras;
2. classificação de cada núcleo lexical e projeção funcional;
3. relações de cabeça, complemento, especificador e projeção, preservando a
   árvore fonte como evidência;
4. regra aplicada, evidência, confiança e estado de revisão humana por decisão;
5. prova automática de que as folhas originais e expandidas são idênticas;
6. contrato de busca que devolva identidade de origem, análise, evidência e
   versão das regras por resultado.

Somente depois dessa camada, do índice de busca e da integração Tauri/React
testada ponta a ponta será possível declarar a busca funcional ou publicar uma
distribuição estável.
