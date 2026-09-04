# Motor Python, Banco de Dados e Tokenização

Este módulo centraliza todo o trabalho duro e procedural (lógico) de tokenização das sentenças, manipulação de árvores e modelagem de banco de dados do projeto Tycho Brahe.

> [!WARNING]
> Os bancos locais atuais são derivados legados, não entradas canônicas do
> pipeline e não formam uma base cartográfica validada. Antes de executar
> qualquer script que os modifique, consulte
> [`../docs/STATUS_DE_ARTEFATOS.md`](../docs/STATUS_DE_ARTEFATOS.md) e valide o
> manifesto de proveniência.

## Importação rastreável — Marco 2

`importador_rastreavel.py` é a entrada atual para criar uma base nova de fatos
de origem. Ele usa somente a biblioteca padrão, lê exclusivamente os PSD
canônicos, preserva cada grupo físico em BLOB e decide `IMPORTADO` ou
`REJEITADO` para todo candidato histórico físico. Não importa, não altera e não
usa os bancos legados como insumo.

O SQLite de saída contém as tabelas `recon_documentos`,
`recon_blocos_origem`, `recon_ledger_importacao`, `recon_sentencas`,
`recon_nos` e `recon_relacoes`. Ele é criado em staging e promovido apenas se
as identidades físicas, árvores, folhas, relações, nested set, FKs e o
manifesto externo coincidirem.

```powershell
$destino = 'C:\builds\tycho\corpus_marco2.sqlite'
python python_backend/importador_rastreavel.py build `
  --source-dir corpus_data `
  --manifest docs/manifests/marco2_importacao_rastreavel_2026-08-31.json `
  --output $destino

python python_backend/importador_rastreavel.py verify `
  --db $destino `
  --manifest docs/manifests/marco2_importacao_rastreavel_2026-08-31.json
```

O destino é recusado dentro de `corpus_data/`. No corpus atual há dez
rejeições explícitas; portanto `--fail-on-rejections` é esperado falhar até a
curadoria versionada desses casos. Consulte
[`../docs/IMPORTACAO_RASTREAVEL.md`](../docs/IMPORTACAO_RASTREAVEL.md) para o
esquema, as contagens e os limites do Marco 2.

## Análise gramatical evidencial — Marco 3

`analise_gramatical_recon.py` recebe um banco Marco 2 validado em modo somente
leitura e produz outro SQLite com o prefixo `m3_*`. Ele ancora o arquivo fonte
e seu manifesto por SHA-256, espelha cada nó de origem e registra decisões de
núcleo, projeção-fonte, relação local e evidência lexical cartográfica com
regra, confiança `HEURISTICA` e revisão `PENDENTE`.

Não importa NLTK ou spaCy, não modifica `recon_*` e não transforma árvores.
`CP`/`IP`/`NP`/`PP` são descritos como estrutura-fonte; o léxico congelado de
ADVP apenas registra evidência para uma projeção do catálogo, sem injetar o nó
teórico. O conjunto de regras é
`regras_gramatica_expandida_v1.json`.

```powershell
$m2 = 'C:\builds\tycho\corpus_marco2.sqlite'
$m3 = 'C:\builds\tycho\corpus_marco3_evidencial.sqlite'
python python_backend/analise_gramatical_recon.py build `
  --source-db $m2 `
  --source-manifest docs/manifests/marco2_importacao_rastreavel_2026-08-31.json `
  --output $m3
python python_backend/analise_gramatical_recon.py verify `
  --db $m3 --source-db $m2 `
  --source-manifest docs/manifests/marco2_importacao_rastreavel_2026-08-31.json
```

O esquema, os invariantes e as limitações científicas estão em
[`../docs/ANALISE_GRAMATICAL_EXPANDIDA.md`](../docs/ANALISE_GRAMATICAL_EXPANDIDA.md).

## Busca rastreável — Marco 4

`busca_rastreavel.py` consulta exclusivamente um SQLite Marco 3 promovido em
modo somente leitura. Os filtros são exatos e parametrizados; cada resultado
JSON traz a identidade M3, o bloco/sentença/nó de origem, a entidade, a
decisão, a regra e as evidências com hash. A consulta normal verifica a
pré-condição estrutural do M3; `--verify-source` pede a prova integral
M3--M2 antes da busca.

```powershell
$m3 = 'C:\builds\tycho\corpus_marco3_evidencial.sqlite'
python python_backend/busca_rastreavel.py search `
  --db $m3 `
  --entity-type EVIDENCIA_CARTOGRAFICA `
  --projection MoodP_evaluative `
  --rule E_ADV
```

O limite é 1--500 e não há interpolação de filtros em SQL. A busca desktop
Marco 5 usa este contrato por uma ponte Tauri/Rust dedicada, sem receber um
caminho de banco da interface. Para gerar o sidecar e provisionar um M3
validado antes de usar o painel, consulte
[`../docs/INTEGRACAO_DESKTOP_M4.md`](../docs/INTEGRACAO_DESKTOP_M4.md) e
[`../docs/BUSCA_RASTREAVEL.md`](../docs/BUSCA_RASTREAVEL.md). Execute:

```powershell
python python_backend/test_busca_rastreavel.py
```

## Auditoria de cobertura e pendências — Marco 6

`auditar_cobertura_m3.py` percorre um M3 promovido em modo somente leitura e
emite agregações por escopo, decisão, entidade, regra, projeção e evidência,
além de uma amostra determinística do backlog cartográfico `PENDENTE`. Não
edita a camada derivada nem registra revisão humana.

```powershell
python python_backend/auditar_cobertura_m3.py report `
  --db $m3 `
  --sample-limit 20

python python_backend/test_auditar_cobertura_m3.py
```

Para validar M3↔M2 antes da agregação e entender os limites de curadoria, veja
[`../docs/AUDITORIA_COBERTURA_M3.md`](../docs/AUDITORIA_COBERTURA_M3.md).

## Estrutura histórica dos bancos SQLite

O diretório de trabalho pode conter os seguintes bancos derivados. Sua presença
não implica completude, validade científica ou aptidão para publicação:

1. **`corpus_cartografia.db`** (Banco de Transdução e Auditoria):
   - `tb_arvores_expandidas`: Registra as árvores geradas pelo motor cartográfico (Modelo Leque) com JSON de projeções injetadas.
   - `tb_quarentena`: Repositório de anomalias sintáticas para curadoria no módulo *Human-in-the-Loop*.
2. **`corpus_fase3.db`** (Banco Hierárquico Principal):
   - `tb_sentencas`: Metadados filológicos completos (`autor`, `titulo`, `seculo`, `ano_aproximado`, `periodo`, `genero`, `texto_plano`, contadores de nós e tokens).
   - `tb_nos`: Representação em grafo via **Nested Set Model** (`lft`, `rgt`, `depth`, `label`, `label_base`, `funcao`, `token`, `lemma`, `eh_cartografico`), permitindo consultas hierárquicas imediatas sem recursão SQL.
   - `tb_relacoes`: Mapeamento explícito de adjacência direta `(pai_id, filho_id)`.

3. **`corpus_fase1.db`** (referência legada): contém a importação original
   observada e serve apenas para comparação durante a reconstrução.

4. **`corpus.db`** (legado sem qualificação): não deve ser usado até receber
   inventário e validação explícitos.

As únicas entradas canônicas da próxima reconstrução são os arquivos
`corpus_data/*_psd.txt` versionados.

---

## Processo histórico de tokenização e expansão

> [!NOTE]
> O fluxo abaixo descreve scripts legados e a arquitetura pretendida. Ele não
> é a rota autorizada para reconstruir a base atual; a rota Marco 2 acima deve
> preceder qualquer transdutor cartográfico futuro.

1. **Leitura**: O sistema consome os arquivos textuais anotados (`*_psd.txt`) localizados na pasta `../corpus_data`.
2. **Parsing**: Utilizando a estrutura `tree_io.py`, cada árvore de colchetes e parênteses lida é convertida para instâncias interpretáveis da classe `ParentedTree` da biblioteca NLP NLTK.
3. **Cartografia (Rizzi/Cinque)**: Passamos essas árvores pelo motor `rewriter.py` que, acompanhado das lógicas do `oracle.py`, faz inserção em "leque" (expansão) nas árvores. Em resumo, ele transforma CP e IP em uma estrutura complexa de ForceP, TopP, FocusP, etc.
4. **Enriquecimento & Persistência**: A árvore é lematizada em lote via spaCy (`pt_core_news_sm`), recebe os metadados do catálogo histórico (`metadata_tycho.py`) e é persistida no SQLite via `build_db_fase3.py`.
5. **Auditoria**: Casos em que a árvore se desvia do padrão e onde a gramática estrita do *Tycho Brahe* falha na conversão, a sentença é redirecionada para a `tb_quarentena` (Módulo Human-in-the-Loop) para que o pesquisador julgue se deve aprovar uma expansão flexível ou descartar.

---

## Gestão e Diagnóstico do Banco (`gerenciador_db.py`)

Para inspecionar ou verificar fisicamente os bancos legados, use o utilitário
dedicado. Não execute `--vacuum` sobre os artefatos congelados nesta etapa.

```bash
# Verificar as fontes canônicas do Marco 2
python python_backend/controle_artefatos.py verify \
  --manifest docs/manifests/marco2_importacao_rastreavel_2026-08-31.json

# Relatório de status e distribuição por autores/séculos
python python_backend/gerenciador_db.py --status

# Verificação de integridade física e foreign keys
python python_backend/gerenciador_db.py --check

# Otimização e desfragmentação de páginas (VACUUM + ANALYZE)
python python_backend/gerenciador_db.py --vacuum
```

---

## Como Recompilar os Sidecars

Instale as dependências de build no mesmo interpretador que será passado aos
scripts. Isso evita depender de uma instalação pessoal ou de uma versão fixa
do Python:

```powershell
python -m venv .venv
$python = Join-Path (Get-Location) '.venv\Scripts\python.exe'
& $python -m pip install -r python_backend/requirements-build.txt
```

O sidecar histórico atende apenas à Consulta Histórica e continua esperando os
bancos legados externos durante a execução. Para instalá-lo no bundle Tauri:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File python_backend/build_backend.ps1 `
  -PythonExecutable $python
```

Em uma verificação de empacotamento, `-SkipTauriCopy` em qualquer um dos dois
scripts gera o executável em seu diretório `dist*` sem substituir o binário do
bundle.

Para a busca M4, use o fluxo dedicado abaixo; ele não empacota o banco M3:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File python_backend/build_m4_sidecar.ps1 `
  -PythonExecutable $python
```

Depois provisione um M3 validado conforme
[`../docs/INTEGRACAO_DESKTOP_M4.md`](../docs/INTEGRACAO_DESKTOP_M4.md). A
recompilação do sidecar não substitui bases, fontes PSD ou pacotes legados.
