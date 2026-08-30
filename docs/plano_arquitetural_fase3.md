# Plano Arquitetural (Fase 3): Protocolo de Transformação e Expansão Algorítmica da Tokenização do Corpus

Este documento descreve o plano arquitetural para a **Fase 3**. O foco é definir um **Protocolo com Sistemas de Cálculo Algorítmico Avançado** para manipular as árvores sintáticas (AST) do corpus Tycho Brahe e realizar uma transformação estrutural. 

O objetivo é gerar uma nova versão do corpus, onde a tokenização original é expandida para englobar as categorias cartográficas de Rizzi e Cinque de forma permanente e pesquisável.

---

## 1. O Modelo "Leque" (Expansão Conservadora)

Seguindo diretrizes rigorosas, a mutação da árvore **não será destrutiva**. O protocolo adotará o modelo de **Expansão em Leque** (Fan Expansion). 
*   As categorias "enxutas" e clássicas originais do Tycho Brahe (ex: `CP-ADV`, `IP-MAT`) serão integralmente preservadas.
*   As categorias expandidas (ex: `ForceP`, `ModP_epi`) atuarão como nós filhos diretos que se "abrem" a partir das categorias originais. 
*   **Vantagem:** O corpus resultante manterá 100% de compatibilidade com pesquisadores que buscam a estrutura clássica, mas oferecerá uma subcamada imediata riquíssima para buscas cartográficas finas.
*   Exemplo de Representação em Leque: `(CP-ADV (ForceP (FinP (C que) (IP-SUB (ModP-epi ...)))))`

---

## 2. O Sistema de Cálculo Algorítmico (O Protocolo em 5 Motores)

A arquitetura do transformador atuará em uma cascata de submotores computacionais:

### Motor 1: Deserializador Estrutural e Topológico
O motor lerá a *string* do arquivo `_psd` e construirá uma Árvore N-ária Direcionada em memória. Cada nó terá ponteiros para o nó pai, nós irmãos, e índices que representam sua profundidade e limites léxicos.

### Motor 2: Classificador Léxico-Semântico (O Oráculo)
Rede de cálculo que classifica nós terminais (folhas).
*   Se lê `(ADVP (ADV infelizmente))`, o oráculo calcula o traço semântico e sinaliza topologicamente a necessidade estrutural de `ModP-EPISTEMIC`.
*   Se lê um nó de movimento `*T*` na periferia esquerda do `CP`, ele sinaliza a necessidade estrutural de `FocP`.

### Motor 3: Transdutor Algorítmico de Árvores (*Tree Rewriter*)
O núcleo do cálculo matemático de mutação de árvores.
*   **Cálculo Bottom-Up (Cinque):** Ao identificar advérbios/auxiliares sinalizados pelo Oráculo dentro de um `IP`, o motor corta a conexão imediata, injeta o nó expandido (ex: `ModP`) como filho do nó superior, e recoloca os elementos sob a nova projeção. A etiqueta `IP` "enxuta" permanece intacta no topo, cobrindo o leque flexional interno.
*   **Cálculo Top-Down (Rizzi):** A partir de um `CP`, o motor não o apaga, mas insere hierarquicamente `ForceP` como filho direto. Abaixo deste, se houver movimento-*wh*, insere `FocP`; se houver elementos separados por vírgula no limite esquerdo, insere `TopP`; finalizando com `FinP` cobrindo as bordas do `IP`.

### Motor 4: Módulo "Human-in-the-Loop" (Relatórios e Manutenção)
O algoritmo possui a estrita diretriz de **não forçar regras cegamente**. A ordem estrita de Cinque ou a posição de certos tópicos de Rizzi podem apresentar anomalias (uso poético, inversão histórica).
*   **Auditoria Restritiva:** Durante o Motor 3, se o cálculo estrutural detectar que a injeção de nós viola a hierarquia matemática esperada, a rotina de mutação para aquela sentença é suspensa.
*   **Log de Quarentena:** A árvore anômala é adicionada a um relatório detalhado de "Termos/Estruturas Não Identificadas".
*   **Manutenção Humana:** O software apresenta uma interface (Terminal ou GUI de revisão) listando as anomalias e permite que o especialista humano tome a decisão sintática (reescrevendo ou autorizando a quebra de regra) de forma pontual para a manutenção do corpus.

### Motor 5: Serializador Gerativo
Após a árvore transdutora estar validada matematicamente ou corrigida manualmente no Motor 4, o algoritmo converte a estrutura em memória de volta para uma *string* serializada (`_psd`) e a salva nos novos arquivos.

---

> [!TIP]
> **Status do Planejamento**
> As respostas às questões anteriores foram incorporadas na arquitetura. O plano descreve agora um sistema não-destrutivo ("leque") e dependente de supervisão humana para exceções (auditoria não-cega).

## 3. Próximo Passo
A engenharia da Fase 3 está completamente delineada. O que o sistema deve fazer agora?
*   Podemos desenhar a estrutura de tabelas que armazenará esse "Log de Manutenção Humana".
*   Podemos avançar para planejar a estratégia empírica de implementação de algum dos motores da Fase 1 ou 2.
*   Podemos aguardar até que você nos instrua a iniciar qualquer escrita de código.
