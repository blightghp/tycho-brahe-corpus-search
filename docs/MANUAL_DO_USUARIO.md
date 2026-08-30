# Manual do Usuário - Tycho Brahe Search v1.0.0

**Tycho Brahe Search** é uma plataforma desktop de alto desempenho para pesquisa sintática, visualização cartográfica e análise estrutural baseada no *Tycho Brahe Parsed Corpus of Historical Portuguese*.

Desenvolvido por **Gabriel Pinheiro** (Pesquisador em Linguística no IEL / Unicamp).

---

## 1. Instalação e Execução

### Opção A: Versão Portátil (Recomendada - Sem Instalação)
1. Baixe o arquivo `TychoBrahe_v1.0.0_Windows_x64_Portable.zip` na pasta `release/` ou na aba de Releases do GitHub.
2. Descompacte o arquivo `.zip` em qualquer pasta de sua preferência.
3. Dê um duplo clique no arquivo `INICIAR_TYCHO_BRAHE.bat` ou diretamente em `Tycho Brahe Search.exe`.
4. O programa inicializará instantaneamente com todos os bancos de dados pré-carregados.

### Opção B: Instalador Automático Windows (Setup / MSI)
1. Execute `Tycho_Brahe_Search_v1.0.0_Setup.exe` ou `Tycho_Brahe_Search_v1.0.0_x64.msi`.
2. Siga as instruções do assistente de instalação.
3. Abra o programa pelo menu Iniciar ou pelo atalho na Área de Trabalho.

---

## 2. Visão Geral da Interface

A aplicação é dividida em quatro áreas principais:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  [Logo] TYCHO BRAHE - Pesquisa Sintática Gerativa        [Créditos] [⚙] │
├─────────────────────────────────────────────────────────────────────────┤
│  [ 🔍 Pesquisa de Corpus ]   [ 🛡️ Revisão Quarentena ]   [ ⚙️ Diagnóstico ] │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  [ Barra de Busca: Digite o label (ex: ForceP, NP-SBJ, MoodP_eval)   ]  │
│  Filtros Rápidos: [D1: SAP] [D2: ForceP] [D2: FocP] [D3: ModP] ...     │
│                                                                         │
├────────────────────────────────────┬────────────────────────────────────┤
│  RESULTADOS (Tabela / Lista)       │  DETALHES DA SENTENÇA SELECIONADA │
│  - ID Sentença & Arquivo Histórico │  - Visualizador D3 da Árvore       │
│  - Texto da Sentença               │  - Anotação por Cores (5 Domínios) │
│  - Projeções Cartográficas         │  - Grade Termo a Termo com Traços  │
│                                    │  - Árvore PSD Raw vs Cartográfica │
└────────────────────────────────────┴────────────────────────────────────┘
```

---

## 3. Funcionalidades de Pesquisa Sintática

### 3.1. Tipos de Consultas Suportadas
- **Projeções Cartográficas Universais**: Busque por `SAP`, `VocP`, `ForceP`, `TopP`, `FocP`, `FinP`, `MoodP_evaluative`, `T_future`, `AspP_durative`, `VoiceP`, `ProcP`, `Root`, etc.
- **Constituintes Tradicionais do Corpus Tycho Brahe**: Busque por `NP-SBJ` (Sujeito), `NP-ACC` (Objeto Direto), `PP` (Sintagma Preposicional), `ADVP` (Sintagma Adverbial), `IP-MAT` (Oração Matriz), `CP-REL` (Oração Relativa).
- **Busca Lexical e Lemática**: Filtre por palavras específicas (ex: *rei*, *senhor*, *deu*) ou seus lemas subjacentes.

### 3.2. Chips de Filtro Rápido
Clique nos chips coloridos abaixo da barra de pesquisa para aplicar filtros imediatos dos 5 Grandes Domínios Cartográficos:
- 🟣 **D1: SAP** — Speech Act Phrase
- 🟣 **D1: VocP** — Posição de Vocativo
- 🔵 **D2: ForceP** — Tipo Ilocucionário e Força da Cláusula
- 🔵 **D2: FocP** — Foco Contrastivo e Operadores Wh-
- 🔵 **D2: FinP** — Finitude e Interface com a Flexão
- 🟢 **D3: MoodP_eval** — Modo Avaliativo
- 🟢 **D3: ModP_epist** — Modalidade Epistêmica
- 🟢 **D3: T_past / future** — Tempo Gramatical
- 🟡 **D4: Low Periphery** — Foco Baixo e Sujeitos Pós-Verbais
- 🔴 **D5: VoiceP / ProcP** — Estrutura Argumental e Eventiva

---

## 4. Visualização Interativa de Árvores Sintáticas (D3.js)

Ao selecionar uma sentença nos resultados de busca:
1. **Esquema Cromático por Domínio**:
   - 🟣 **Violeta**: Domínio 1 — Ato de Fala (SAP, VocP, EvalP).
   - 🔵 **Índigo**: Domínio 2 — Complementizador Split-CP (ForceP, TopP, IntP, FocP, FinP).
   - 🟢 **Esmeralda**: Domínio 3 — Flexional Split-IP (MoodP, ModP, TP, AspP, VoiceP).
   - 🟡 **Âmbar**: Domínio 4 — Baixa Periferia Esquerda (TopP_low, FocP_low).
   - 🔴 **Rosa/Vermelho**: Domínio 5 — Temático First Phase (VoiceP_agent, ProcP, ResP, Root).
   - ⚪ **Cinza**: Nós Estruturais Básicos e Folhas Lexicais.
2. **Controles de Navegação**:
   - **Zoom / Pan**: Use a roda do mouse ou arraste com o botão esquerdo para navegar em árvores profundas.
   - **Centralizar / Reset**: Clique nos botões de controle de visualização para reajustar o enquadramento.

---

## 5. Tabela Termo a Termo e Extração de Traços

Abaixo da árvore sintática, a aplicação exibe a **Decomposição Morfossintática Termo a Termo**:
- **Termo**: O token exato em português arcaico/clássico extraído do texto.
- **Projeção Funcional**: A projeção sintática cartográfica exata onde o constituinte se ancora.
- **Domínio**: O estrato hierárquico correspondente (D1 a D5).
- **Lema**: O lema canônico normalizado.
- **POS Tag**: A classe gramatical formal.
- **Papel Gerativo**: Função teórica formal (ex: *Operador Ilocucionário*, *Tópico Familiar*, *Tempo Anterior*, *Iniciador/Agente*, *Processo/Verbo*, *Raiz Temática/Paciente*).

---

## 6. Módulo Human-in-the-Loop (Auditoria de Quarentena)

Sentenças históricas com anomalias estruturais ou ordens não-canônicas que violam a hierarquia universal de Cinque (1999) são automaticamente isoladas para auditoria humana:
1. Acesse a aba **🛡️ Revisão Quarentena**.
2. Visualize a lista de sentenças em quarentena com o diagnóstico da anomalia (ex: `HIERARQUIA_CINQUE_VIOLADA`, `CP_DESCONHECIDO`).
3. Compare a árvore original com a derivação cartográfica proposta.
4. Clique em **Aprovar**, **Rejeitar** ou **Editar Manualmente** para atualizar o status no banco de dados.

---

## 7. Diagnóstico e Status do Sistema

Acesse a aba **⚙️ Diagnóstico** para verificar:
- Status de conexão com o motor Rust e o Sidecar Python.
- Caminhos absolutos e integridade dos bancos de dados SQLite ativos.
- Estatísticas em tempo real: número total de sentenças indexadas, nós cartográficos gerados e itens em quarentena.
