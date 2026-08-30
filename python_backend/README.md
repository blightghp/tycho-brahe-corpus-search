# Motor Python, Banco de Dados e Tokenização

Este módulo centraliza todo o trabalho duro e procedural (lógico) de tokenização das sentenças, manipulação de árvores e modelagem de banco de dados do projeto.

## O Processo Demorado (Tokenização Sintática)

1. **Leitura**: O sistema consome os arquivos textuais anotados (`*_psd.txt`) localizados na pasta `../corpus_data`.
2. **Parsing**: Utilizando a estrutura `tree_io.py`, cada árvore de colchetes e parênteses lida é convertida para instâncias interpretáveis da classe `ParentedTree` da biblioteca NLP NLTK.
3. **Cartografia (Rizzi/Cinque)**: Passamos essas árvores pelo motor `rewriter.py` que, acompanhado das lógicas do `oracle.py`, faz inserção em "leque" (expansão) nas árvores. Em resumo, ele transforma CP e IP em uma estrutura complexa de ForceP, TopP, FocusP, etc.
4. **Persistência**: Essa árvore pesada convertida é persistida numa estrutura *Nested Set Model* do SQLite através do arquivo `build_db_fase3.py`.
5. **Auditoria**: Casos em que a árvore se desvia do padrão e onde a gramática estrita do *Tycho Brahe* falha na conversão, a sentença é redirecionada para a `tb_quarentena` (Módulo Human-in-the-Loop) para que o pesquisador julgue se deve aprovar uma expansão flexível ou descartar.

## Como Executar
Sempre que o código em Python for alterado (por exemplo, adicionar uma nova regra cartográfica), compile a ponte novamente para que a Interface saiba:
```bash
./build_backend.ps1
```
Isso usará o PyInstaller para condensar todas as bibliotecas de processamento no binário invisível consumido pelo frontend.
