# Estado dos artefatos e política de publicação

## Marco 1 — contenção e proveniência

O projeto está em **reconstrução controlada**. Os bancos cartográficos e os
pacotes identificados como `v1.0.0` foram congelados para auditoria: não são
uma versão estável, não devem ser redistribuídos como produto validado e não
devem sustentar resultados científicos corpus-integrais.

O retrato verificável deste congelamento está em
[`manifests/estado_experimental_2026-08-31.json`](manifests/estado_experimental_2026-08-31.json).
Ele registra SHA-256, tamanho e sinais estruturais dos dados disponíveis no
momento da auditoria, sem versionar os bancos ou binários grandes.

## Classificação

| Classe | Caminhos | Regra de uso |
|---|---|---|
| Fonte canônica protegida | `corpus_data/*_psd.txt` | Única entrada autorizada para a reconstrução. Não alterar; validar o parser por bloco antes de promover resultados. |
| Referência derivada legada | `corpus_data/corpus_fase1.db` | Preservar em leitura; usar apenas para comparação e diagnóstico. |
| Derivado experimental | `corpus_data/corpus_cartografia.db`, `corpus_data/corpus_fase3.db` | Não publicar, não tratar como corpus completo e não reutilizar como entrada de build. |
| Legado sem qualificação | `corpus_data/corpus.db` | Não consumir até que receba inventário e validação explícitos. |
| Distribuição retirada | `release/` e pacotes `v1.0.0` | Guardados para auditoria; não suportados e não publicáveis. |
| Snapshot de runtime | sidecars Python atuais | Registrados apenas para comparação; não certificam o funcionamento do pacote. |

Os bancos e `release/` são ignorados pelo Git. Por isso, o manifesto registra
seus hashes como artefatos opcionais: a ausência deles em um clone não altera
o estado das fontes PSD, mas uma cópia presente e divergente é reportada.

## Identidade da fonte

`sent_id_externo` não é uma chave confiável: há blocos sem ID e há IDs
reutilizados. A identidade canônica a ser usada pelo novo importador será:

```text
arquivo_relativo + ordinal_do_bloco + SHA-256_do_bloco
```

O ID externo será preservado como metadado. O manifesto já guarda, por arquivo,
o digest agregado dessas identidades candidatas, para impedir perdas silenciosas
no próximo parser.

## Como verificar o congelamento

Execute a partir da raiz do repositório:

```powershell
python python_backend/controle_artefatos.py verify `
  --manifest docs/manifests/estado_experimental_2026-08-31.json
```

Isso exige todas as fontes PSD e o snapshot de código; bancos, binários e
pacotes legados ausentes geram aviso. Para exigir também os artefatos legados
que existem nesta cópia de trabalho:

```powershell
python python_backend/controle_artefatos.py verify `
  --manifest docs/manifests/estado_experimental_2026-08-31.json `
  --require-experimental
```

`"ok": true` nesse comando atesta somente a integridade dos arquivos
observados. O resultado também declara `publication_approved: false`: nenhum
artefato deste manifesto é uma distribuição aprovada.

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

- Há 30 arquivos PSD versionados.
- O corpus bruto possui 60.376 ocorrências de registros `ID` e 56.936 blocos
  candidatos segundo o filtro histórico `(IP-|CP-)`.
- `corpus_data/va_013_psd.txt` tem saldo bruto de parênteses igual a `-2`. É
  um sinal de integridade a investigar pelo novo parser, não uma licença para
  editar a fonte canônica.
- O banco Fase 1 observado contém 56.796 sentenças. A diferença deve ser
  explicada por resultados explícitos de importação ou rejeição na próxima
  reconstrução; falhas silenciosas não serão aceitas.
- O banco cartográfico observado cobre apenas três arquivos, contém duplicatas
  e apresenta árvores cuja sequência superficial diverge da origem.
- O Fase 3 observado cobre apenas dois arquivos. Logo, nenhum dos dois pode
  ser apresentado como corpus cartográfico integral.

## Regras operacionais até o próximo marco

1. Não executar `processar_corpus.py --reset` contra os bancos congelados.
2. Não executar `package_release.py` sem a autorização explícita exigida pelo
   próprio script; ela existe apenas para auditoria controlada.
3. Não sobrescrever nem editar os PSD de `corpus_data/`.
4. Toda reconstrução deve escrever primeiro em caminhos temporários, validar
   cobertura, folhas e integridade, e só então promover o resultado.
5. A próxima base deverá registrar, para cada bloco candidato, `IMPORTADO` ou
   `REJEITADO` com motivo, além do hash da fonte e da versão das regras.

## Próximos marcos da reconstrução

1. **Importação rastreável:** parser isolado, tabela de proveniência por bloco
   e ledger explícito de importação/rejeição, inclusive para `va_013`.
2. **Gramática expandida:** transdutor versionado que separa núcleo lexical,
   projeções funcionais, evidência e nível de confiança, preservando as folhas.
3. **Busca verificável:** índice e contrato único de resultados por sentença,
   exercitados pela API Python, comando Tauri e interface React.
4. **Publicação:** migração limpa, testes ponta a ponta, pacote novo e
   manifesto produzido no próprio build.

## Critérios para uma futura publicação estável

1. Cobertura integral dos arquivos e dos blocos do manifesto, sem duplicatas.
2. Preservação comprovada da sequência superficial das folhas.
3. Regras cartográficas versionadas, com evidência, confiança e revisão humana.
4. Busca, interface e auditoria validadas ponta a ponta em pacote limpo.
5. Manifesto de corpus, ferramentas, esquema e distribuição gerado no build.
