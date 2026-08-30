# Motor Python, Banco de Dados e Tokenização

Este módulo centraliza todo o trabalho duro e procedural (lógico) de tokenização das sentenças, manipulação de árvores e modelagem de banco de dados do projeto Tycho Brahe.

## Estrutura dos Bancos de Dados (SQLite)

O projeto opera com dois bancos SQLite complementares com suporte a WAL (Write-Ahead Logging):

1. **`corpus_cartografia.db`** (Banco de Transdução e Auditoria):
   - `tb_arvores_expandidas`: Registra as árvores geradas pelo motor cartográfico (Modelo Leque) com JSON de projeções injetadas.
   - `tb_quarentena`: Repositório de anomalias sintáticas para curadoria no módulo *Human-in-the-Loop*.
2. **`corpus_fase3.db`** (Banco Hierárquico Principal):
   - `tb_sentencas`: Metadados filológicos completos (`autor`, `titulo`, `seculo`, `ano_aproximado`, `periodo`, `genero`, `texto_plano`, contadores de nós e tokens).
   - `tb_nos`: Representação em grafo via **Nested Set Model** (`lft`, `rgt`, `depth`, `label`, `label_base`, `funcao`, `token`, `lemma`, `eh_cartografico`), permitindo consultas hierárquicas imediatas sem recursão SQL.
   - `tb_relacoes`: Mapeamento explícito de adjacência direta `(pai_id, filho_id)`.

---

## O Processo Demorado (Tokenização Sintática)

1. **Leitura**: O sistema consome os arquivos textuais anotados (`*_psd.txt`) localizados na pasta `../corpus_data`.
2. **Parsing**: Utilizando a estrutura `tree_io.py`, cada árvore de colchetes e parênteses lida é convertida para instâncias interpretáveis da classe `ParentedTree` da biblioteca NLP NLTK.
3. **Cartografia (Rizzi/Cinque)**: Passamos essas árvores pelo motor `rewriter.py` que, acompanhado das lógicas do `oracle.py`, faz inserção em "leque" (expansão) nas árvores. Em resumo, ele transforma CP e IP em uma estrutura complexa de ForceP, TopP, FocusP, etc.
4. **Enriquecimento & Persistência**: A árvore é lematizada em lote via spaCy (`pt_core_news_sm`), recebe os metadados do catálogo histórico (`metadata_tycho.py`) e é persistida no SQLite via `build_db_fase3.py`.
5. **Auditoria**: Casos em que a árvore se desvia do padrão e onde a gramática estrita do *Tycho Brahe* falha na conversão, a sentença é redirecionada para a `tb_quarentena` (Módulo Human-in-the-Loop) para que o pesquisador julgue se deve aprovar uma expansão flexível ou descartar.

---

## Gestão e Diagnóstico do Banco (`gerenciador_db.py`)

Para inspecionar, verificar integridade física ou otimizar os bancos de dados, use o utilitário dedicado:

```bash
# Relatório de status e distribuição por autores/séculos
python python_backend/gerenciador_db.py --status

# Verificação de integridade física e foreign keys
python python_backend/gerenciador_db.py --check

# Otimização e desfragmentação de páginas (VACUUM + ANALYZE)
python python_backend/gerenciador_db.py --vacuum
```

---

## Como Recompilar o Sidecar
Sempre que o código em Python for alterado (por exemplo, adicionar uma nova regra cartográfica), compile a ponte novamente para que a Interface saiba:
```bash
./build_backend.ps1
```
Isso usará o PyInstaller para condensar todas as bibliotecas de processamento no binário invisível consumido pelo frontend.
