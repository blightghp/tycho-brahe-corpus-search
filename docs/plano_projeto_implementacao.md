# Plano de Projeto e Implementação (Fases 2 e 3)

> [!NOTE]
> Documento histórico de planejamento. Não descreve o estado executável atual;
> para a sequência vigente e os artefatos permitidos, consulte
> [STATUS_DE_ARTEFATOS.md](STATUS_DE_ARTEFATOS.md).

Este documento detalha o passo a passo para a construção do **Transdutor Algorítmico Cartográfico**, materializando as Fases 2 (Mapeamento Cartográfico) e 3 (Mutação em Leque) sobre o Corpus Tycho Brahe.

## Visão Geral
A implementação será guiada pelo **Protocolo de 5 Motores**, garantindo que as expansões cartográficas (Split-CP e Split-IP) não quebrem as categorias originais do corpus, utilizando a inserção de nós "filhos" (Modelo Leque) e incluindo auditoria humana para estruturas sintáticas ambíguas.

---

## 🛠️ Passo a Passo da Implementação

### Etapa 1: Estruturação do Banco de Dados de Auditoria (Human-in-the-Loop)
**Objetivo:** Preparar a persistência para sentenças que o algoritmo não conseguir resolver com 100% de confiança matemática.
*   **Ações:**
    1. Criar um script `build_db_auditoria.py`.
    2. Criar tabela `tb_quarentena` com as colunas: `id_sentenca`, `arquivo_origem`, `arvore_original`, `motivo_anomalia`, `status_revisao` (Pendente/Resolvido), e `arvore_corrigida`.
    3. Criar tabela `tb_arvores_expandidas` para armazenar as árvores que passarem direto (transformadas com sucesso sem anomalias).

### Etapa 2: Motores 1 e 5 - I/O de Árvores (Deserialização e Serialização)
**Objetivo:** Transitar bidirecionalmente entre o texto em formato S-expression (`_psd`) e instâncias manipuláveis de árvore na memória do Python.
*   **Ações:**
    1. Criar módulo `tree_io.py`.
    2. Desenvolver a função `deserialize_tree(string_psd)`: Converte a string bruta do banco para o objeto lógico `nltk.ParentedTree`.
    3. Desenvolver a função `serialize_tree(tree)`: Converte a `ParentedTree` mutada de volta para string em formato S-expression (`_psd`), garantindo o alinhamento de parênteses necessário.
    4. Criar rotina de testes unitários para provar que a ação de ida e volta (`serialize(deserialize(A)) == A`) não perde informações topológicas e textuais.

### Etapa 3: Motor 2 - Classificador Léxico-Semântico (O Oráculo)
**Objetivo:** Identificar gatilhos morfoléxicos e topológicos que disparam as projeções cartográficas invisíveis de Rizzi e Cinque.
*   **Ações:**
    1. Criar módulo `oracle.py`.
    2. **Mapear léxico de Cinque:** Criar dicionário associando classes de advérbios aos seus núcleos gerativos correspondentes (ex: o lema advérbio `provavelmente` aciona o núcleo `ModP_epistemic`).
    3. **Mapear topologia de Rizzi:** Implementar funções para detectar traços de movimento-*wh* (`*T*`) no interior de projeções `CP` ou detectar elementos sem traços quantificados na periferia esquerda (para `TopP`).
    4. Implementar rotina que varre a `ParentedTree` original e insere tags ou anotações temporárias indicando a **intenção de mutação**.

### Etapa 4: Motor 3 - Transdutor Algorítmico (Tree Rewriter)
**Objetivo:** É o núcleo matemático do projeto. Realiza as "cirurgias" na árvore sintática aplicando rigorosamente o "Modelo Leque".
*   **Ações:**
    1. Criar módulo central `rewriter.py`.
    2. **Expansão Flexional (Split-IP, Bottom-Up):** Função que, orientada pelo Oráculo, afasta o nó `IP` do VP e injeta os nós ordenados da hierarquia de Cinque no meio, realocando os filhos adequadamente.
    3. **Expansão do Complementizador (Split-CP, Top-Down):** Função que reestrutura o interior do `CP`, ramificando-o em `ForceP`, `TopP`, `FocP` e `FinP`, mantendo a etiqueta original do corpus (ex: `CP-ADV`) intocada como a "casca externa".
    4. **Validador de Hierarquia Estrita:** Função fiscalizadora que detecta violações após as reescritas (ex: se gerar um `FinP` acima de `ForceP`), acionando assim a `AnomalyError`.

### Etapa 5: Motor 4 - Módulo "Human-in-the-Loop" (Revisão)
**Objetivo:** Interface interativa para que o linguista decida casos problemáticos.
*   **Ações:**
    1. Criar script de CLI `revisor_cli.py`.
    2. O sistema buscará as próximas sentenças listadas na `tb_quarentena`.
    3. Apresentará no console a sentença, a árvore anômala original, e o erro gerativo levantado pelo Motor 3.
    4. Fornecerá ações ao especialista: **[1]** Autorizar a mutação anômala (uso literário/exceção); **[2]** Reescrever a árvore manualmente; **[3]** Pular para depois.

### Etapa 6: Integração e Pipeline de Processamento em Lote (Batch Processor)
**Objetivo:** Juntar os módulos, rodar o corpus massivamente na "linha de montagem" e gerar a versão final turbinada.
*   **Ações:**
    1. Criar script `processar_corpus.py`.
    2. Estabelecer loop principal carregando sentenças de `corpus_fase1.db`.
    3. Aplicar sequencialmente os Motores 1, 2 e 3 em cada árvore.
    4. Persistir as processadas com sucesso na `tb_arvores_expandidas` ou registrar falhas na `tb_quarentena`.
    5. Script gerador final `exportar_corpus_expandido.py` que coleta todas as árvores (aprovadas de forma automatizada e corrigidas via revisão humana), exportando-as de volta em arquivos físicos `_psd` dentro de um diretório `corpus_fase3/`. Estas poderão ser consumidas diretamente pelo script clássico `pesquisa_sintatica.py` (Fase 1).

---

## 📅 Marcos de Entrega (Milestones)

1. **Milestone 1:** Motores de I/O (`tree_io.py`) e Banco de Auditoria em SQLite construídos e testados (Etapas 1 e 2).
2. **Milestone 2:** Oráculo classificador (`oracle.py`) programado com as listas fechadas do português baseadas em Rizzi e Cinque (Etapa 3).
3. **Milestone 3:** Algoritmo transdutor principal operando cirurgias em Árvores (`rewriter.py`) lidando com instâncias isoladas (Etapa 4).
4. **Milestone 4:** Linha de montagem automatizada em ação, interface CLI funcional para revisão da quarentena, e output massivo do corpus novo (Etapas 5 e 6).
