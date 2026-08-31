# Plano Arquitetural (Fase 2): Implementação da Cartografia Sintática (Split-CP e Split-IP)

> [!NOTE]
> Documento histórico de planejamento. Não descreve o estado executável atual;
> para a sequência vigente e os artefatos permitidos, consulte
> [STATUS_DE_ARTEFATOS.md](STATUS_DE_ARTEFATOS.md).

Este documento detalha o segundo plano de sequência arquitetural. O foco desta fase é estender o motor de busca gerativo (detalhado na Fase 1) para suportar a **sequência estendida de núcleos funcionais** (A Abordagem Cartográfica), incorporando as projeções finas do sistema Complementizador (CP), conforme **Rizzi (1997; 2004)**, e do sistema Flexional (IP), conforme **Cinque (1999; 2002)**.

Como a anotação nativa do Corpus Tycho Brahe (`_psd`) utiliza um esquema mais "achatado" (flat) com base estrutural no *Penn Treebank* (ex: agrupa tudo em categorias amplas como `CP-ADV`, `IP-MAT`), este plano propõe uma arquitetura capaz de **mapear, projetar e consultar** a hierarquia cartográfica fina sobre a estrutura original.

---

## 1. O Desafio Cartográfico frente aos Dados do Corpus

### 1.1 O Sistema C (Rizzi 1997, 2004)
Rizzi propõe a explosão do nó `CP` na seguinte hierarquia básica:
`ForceP > (TopP*) > FocP > (TopP*) > FinP`
*O corpus original possui apenas nós como `CP`, acompanhados de funções como `CP-REL`, `CP-ADV` e complementizadores diretos (ex: `C que`).*

### 1.2 O Sistema I (Cinque 1999, 2002)
Cinque propõe uma hierarquia universal estrita para as projeções flexionais (Tempo, Modo, Aspecto e Voz) ancoradas por advérbios específicos:
`MoodP(speech_act) > MoodP(eval) > ModP(epistemic) > T(past) > T(future) > AspP(perfect) > ... > VP`
*O corpus original possui apenas nós macro como `IP-MAT` (Oração Matriz) e `IP-SUB` (Subordinada), com advérbios marcados genericamente como `ADVP` ou adjuntos.*

---

## 2. Arquitetura de Implementação (Expansão Cartográfica)

Para permitir buscas baseadas nessas hierarquias refinadas sem destruir a fidelidade aos dados originais do Tycho Brahe, a arquitetura introduzirá uma **Camada de Enriquecimento Heurístico e Virtualização de Grafos**.

### Camada 1: Motor de Reanotação Cartográfica (Heurísticas Baseadas em Regras)
Esta nova sub-camada ocorrerá no pipeline de ETL (após o parsing inicial da Fase 1). Ela criará nós virtuais baseando-se em pistas morfoléxicas e topológicas:

*   **Heurísticas para o Split-CP (Rizzi):**
    *   **ForceP:** Identificado pelo tipo de sentença (declarativa, interrogativa, matriz vs subordinada). O nó superior do `CP` projeta a força ilocucionária.
    *   **FocP (Foco):** Identificado quando um constituinte (NP, PP, ADVP) se move para a periferia esquerda, deixando um traço (`*T*`) ou através de elementos-Q (movimento-*wh*).
    *   **TopP (Tópico):** Identificado por constituintes deslocados à esquerda (geralmente isolados por vírgula) que não possuem quantificação ou traços de foco restritivo (frequentemente co-indexados com pronomes resumptivos).
    *   **FinP (Finitude):** Projetado adjacente ao IP, verificado pela flexão do verbo em I (finito vs não-finito).

*   **Heurísticas para o Split-IP (Cinque):**
    *   **Ancoragem Adverbial:** Utilizaremos o lema dos advérbios (obtidos na lematização da Fase 1) como "âncoras" para projetar os núcleos funcionais invisíveis. Ex: Se o advérbio `provavelmente` for detectado no `IP`, a arquitetura projeta um nó `ModP_epistemic` dominando aquela zona da árvore.
    *   **Marcadores Morfológicos e Auxiliares:** O tempo e aspecto morfológico dos verbos e a presença de verbos auxiliares (ex: `ter` + particípio) irão disparar a criação (instanciação) de nós como `T_past` ou `AspP_perfect`.

### Camada 2: Armazenamento em Grafos (Múltiplas Visões - *Multi-View Graphs*)
A abordagem ideal para essa expansão baseia-se puramente em um Banco de Dados de Grafos (Neo4j):

1.  A árvore original do Tycho Brahe é mantida intacta com a aresta `DOMINATES_ORIGINAL`.
2.  O Motor de Reanotação cria novos *Nodes* para `ForceP`, `TopP`, `FocP`, `FinP`, `MoodP`, etc.
3.  Esses novos nós se conectam à árvore usando uma aresta diferente, ex: `DOMINATES_CARTOGRAPHIC`.
4.  **Vantagem:** O linguista pode alternar entre a "Visão Clássica/Penn" e a "Visão Cartográfica" com um simples parâmetro de busca, evitando corrupção dos dados originais.

### Camada 3: Motor de Consulta Estendida (Carto-Tgrep)
A linguagem de busca precisará incorporar o vocabulário das hierarquias estendidas, permitindo consultas mistas (léxico, anotação original e nós cartográficos injetados).

*Exemplos de Queries no Sistema Proposto:*
1.  **Explorando a Periferia Esquerda (Rizzi):**
    `FocP < (*T* $) (TopP < NP)`
    *(Encontrar orações onde o Foco contém um traço e é vizinho inferior de um Tópico projetando um Sintagma Nominal).*
2.  **Explorando a Hierarquia Adverbial (Cinque):**
    `ModP_epistemic << (ADVP [lemma="talvez"])`
    *(Encontrar projeções modais epistêmicas instanciadas/lexicalizadas pelo advérbio "talvez").*

## 3. Fluxo de Processamento (Pipeline Atualizado)

1.  **Leitura e Parsing (Original):** O arquivo `.psd` é lido.
2.  **Lematização (Fase 1):** Nós terminais recebem os atributos de lema.
3.  **Reanotação Cartográfica (Novo):**
    *   As regras identificam advérbios de Cinque e projetam nós IP estendidos.
    *   A posição estrutural e os traços de movimento (*T*) expandem o CP em Force, Top, Foc, Fin.
4.  **Armazenamento em Grafo Duplo:** As estruturas (original e estendida) são gravadas no Neo4j com diferentes tipos de arestas (`edges`).
5.  **Consulta:** O pesquisador realiza a consulta via interface, extraindo as sentenças no Excel ou visualizando os grafos cartográficos detalhados da estrutura interna.

> [!WARNING]
> **Aviso Importante: Limitações dos Dados vs Teoria**
> Uma vez que a Cartografia de Cinque é extremamente detalhada (dezenas de projeções), nós "vazios" (onde não há advérbio ou auxiliar foneticamente realizado para dispará-los) não poderão ser instanciados de maneira universal para todas as sentenças sem gerar sobrecarga especulativa no banco de dados. O projeto irá instanciar essas projeções finas **apenas** quando houver material morfossintático (evidência no corpus) que justifique sua projeção ativa (ex: presença de *T*, advérbios cinquenianos, ou conectivos).

> [!IMPORTANT]
> **Aguardando Feedback**
> Como da última vez, não foi implementada nenhuma linha de código. O plano foca unicamente no desenho arquitetural desta expansão lógica.
> Você concorda com a abordagem heurística baseada em "Grafos de Múltiplas Visões" e "Ancoragem Adverbial/Morfológica" para mapear os nós invisíveis de Rizzi e Cinque sobre os dados originais do Tycho Brahe?
