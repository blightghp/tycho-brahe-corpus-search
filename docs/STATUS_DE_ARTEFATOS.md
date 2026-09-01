# Estado dos artefatos e política de publicação

## Estado verificável — Marco 2 concluído

O projeto permanece em **reconstrução controlada**. O Marco 2 concluiu a
importação PSD rastreável: há um parser isolado, um banco reconstruível e um
ledger explícito para cada candidato histórico físico. Isso ainda **não**
certifica a cartografia expandida, a busca desktop ou uma distribuição
científica/publicável.

Os bancos cartográficos e os pacotes `v1.0.0` continuam congelados para
auditoria. Há dois retratos de proveniência:

- [`manifests/estado_experimental_2026-08-31.json`](manifests/estado_experimental_2026-08-31.json)
  preserva o congelamento histórico inicial;
- [`manifests/marco2_importacao_rastreavel_2026-08-31.json`](manifests/marco2_importacao_rastreavel_2026-08-31.json)
  é o contrato atual de fonte física e pipeline.

O banco Marco 2 é produzido em um destino externo explícito e não é instalado
em `corpus_data/`. Consulte [IMPORTACAO_RASTREAVEL.md](IMPORTACAO_RASTREAVEL.md)
para reconstruí-lo e verificá-lo.

## Classificação

| Classe | Caminhos | Regra de uso |
|---|---|---|
| Fonte canônica protegida | `corpus_data/*_psd.txt` | Única entrada autorizada para a reconstrução. Não alterar; validar o parser por bloco antes de promover resultados. |
| Referência derivada legada | `corpus_data/corpus_fase1.db` | Preservar em leitura; usar apenas para comparação e diagnóstico. |
| Derivado experimental | `corpus_data/corpus_cartografia.db`, `corpus_data/corpus_fase3.db` | Não publicar, não tratar como corpus completo e não reutilizar como entrada de build. |
| Legado sem qualificação | `corpus_data/corpus.db` | Não consumir até que receba inventário e validação explícitos. |
| Banco Marco 2 | Destino externo de `importador_rastreavel.py` | Reconstruível e validável; não substituir nem alimentar os bancos congelados. |
| Distribuição retirada | `release/` e pacotes `v1.0.0` | Guardados para auditoria; não suportados e não publicáveis. |
| Snapshot de runtime | sidecars Python atuais | Registrados apenas para comparação; não certificam o funcionamento do pacote. |

Os bancos e `release/` são ignorados pelo Git. Por isso, o manifesto registra
seus hashes como artefatos opcionais: a ausência deles em um clone não altera
o estado das fontes PSD, mas uma cópia presente e divergente é reportada.

## Identidade da fonte

`sent_id_externo` não é uma chave confiável: há blocos sem ID e há IDs
reutilizados. A identidade canônica do importador Marco 2 é:

```text
arquivo_relativo + ordinal_bloco_fisico + ordinal_candidato + SHA-256_do_BLOB_bruto
```

O caminho é portátil, por exemplo `corpus_data/a_001_psd.txt`; o ordinal de
candidato é nulo em blocos físicos fora do subconjunto IP/CP. O ID externo é
somente metadado.

O Marco 2 registra dois fingerprints por documento: o histórico de
S-expressões, para compatibilidade com o congelamento, e o físico de blocos,
ordinais e hashes brutos, para provar o conteúdo do ledger. Eles não são
intercambiáveis em fontes malformadas ou grupos mistos.

## Como verificar o congelamento

Execute a partir da raiz do repositório:

```powershell
python python_backend/controle_artefatos.py verify `
  --manifest docs/manifests/marco2_importacao_rastreavel_2026-08-31.json `
  --require-experimental
```

`"ok": true` nesse comando atesta a integridade das fontes, do pipeline Marco
2 e dos artefatos observados. O resultado ainda declara
`publication_approved: false`: integridade não torna os derivados uma
distribuição aprovada nem declara a busca funcional.

O manifesto histórico permanece como evidência do Marco 1, mas seu snapshot de
pipeline não é o contrato de builds novos. Para reconstruir e conferir o banco
Marco 2, use [IMPORTACAO_RASTREAVEL.md](IMPORTACAO_RASTREAVEL.md).

Para produzir um novo retrato observacional, sem modificar o corpus ou bancos:

```powershell
python python_backend/controle_artefatos.py snapshot `
  --output docs/manifests/novo_snapshot.json `
  --include-release
```

O teste isolado deste controle não depende de NLTK ou spaCy:

```powershell
python python_backend/test_controle_artefatos.py
```

## Evidências registradas neste marco

- Há 30 arquivos PSD versionados, 63.784 blocos físicos preservados e 56.936
  candidatos históricos físicos com decisão no ledger.
- A reconstrução validada registra 56.926 `IMPORTADO`, 10 `REJEITADO` e
  2.385.719 nós de origem, sem depender dos bancos legados.
- `corpus_data/va_013_psd.txt` conserva o trailer DOS `0x1A`; os blocos
  defeituosos são rejeitados explicitamente sem impedir os registros seguintes.
- As dez rejeições, seus ordinais e motivos são listados em
  [IMPORTACAO_RASTREAVEL.md](IMPORTACAO_RASTREAVEL.md); elas não são perdas
  silenciosas nem licença para editar a fonte canônica.
- O banco Fase 1 observado contém 56.796 sentenças, e os bancos cartográfico e
  Fase 3 continuam referências incompletas/experimentais, não saídas do Marco
  2 nem bases cartográficas integrais.

## Regras operacionais até o próximo marco

1. Não executar `processar_corpus.py --reset` contra os bancos congelados.
2. Não executar `package_release.py` sem a autorização explícita exigida pelo
   próprio script; ela existe apenas para auditoria controlada.
3. Não sobrescrever nem editar os PSD de `corpus_data/`.
4. Toda reconstrução deve escrever primeiro em caminhos temporários, validar
   cobertura, folhas e integridade, e só então promover o resultado.
5. Não ocultar as dez rejeições: qualquer recuperação deve ser versionada,
   revisável e produzir novo manifesto.
6. Não apresentar o banco Marco 2 como cartografia expandida integral antes da
   camada de análise gramatical e da busca verificável.

## Próximos marcos da reconstrução

1. **Gramática expandida:** transdutor versionado ligado aos nós `recon_*` que
   separe núcleo lexical, projeções funcionais, evidência e confiança,
   preservando as folhas.
2. **Busca verificável:** índice e contrato único de resultados por sentença,
   análise e evidência, exercitados pela API Python, comando Tauri e React.
3. **Curadoria de rejeições:** resolução explícita dos dez casos, sem alterar
   a fonte canônica fora de processo autorizado.
4. **Publicação:** migração limpa, testes ponta a ponta, pacote novo e
   manifesto produzido no próprio build.

## Critérios para uma futura publicação estável

1. Cobertura integral dos arquivos e dos blocos do manifesto, sem duplicatas.
2. Preservação comprovada da sequência superficial das folhas.
3. Regras cartográficas versionadas, com evidência, confiança e revisão humana.
4. Busca, interface e auditoria validadas ponta a ponta em pacote limpo.
5. Manifesto de corpus, ferramentas, esquema e distribuição gerado no build.
