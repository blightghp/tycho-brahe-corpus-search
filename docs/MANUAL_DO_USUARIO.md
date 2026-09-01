# Manual de Interface Histórico — Tycho Brahe Search

> [!WARNING]
> Este documento descreve a experiência-alvo e a interface histórica. Os
> pacotes `v1.0.0` e os bancos cartográficos legados estão em reconstrução
> controlada; não constituem produto estável nem corpus validado. A rota
> **Busca Evidencial (M4)** está integrada ao desktop, mas exige um M3
> validado e provisionado e não confirma hipóteses sem revisão humana.
> Consulte [STATUS_DE_ARTEFATOS.md](STATUS_DE_ARTEFATOS.md) antes de executar
> ou citar resultados.

**Tycho Brahe Search** é uma plataforma desktop em reconstrução para pesquisa
sintática, visualização cartográfica e análise estrutural baseada no *Tycho
Brahe Parsed Corpus of Historical Portuguese*.

Todos os direitos reservados à Plataforma Tycho Brahe © 2026 — Criada e desenvolvida principalmente por **Luiz Henrique Lima Veronesi** como fruto de sua tese de doutorado em Linguística no IEL/UNICAMP, sob orientação da **Profª Drª Charlotte Galves**, professora do IEL/UNICAMP. O motor de busca complementar **Tycho Brahe Search** foi elaborado por Gabriel Pinheiro como extensão complementar, a partir de sua proposta de arquitetura para a implementação de núcleos cartográficos.

A referência completa da tese, os créditos do DACILAT — projeto associado cujos corpora ajudam a alimentar a Plataforma — e a lista de participantes estão em [REFERENCIAS_E_CREDITOS.md](REFERENCIAS_E_CREDITOS.md).

---

## 1. Estado de instalação e execução

Não há distribuição estável suportada nesta revisão. Os arquivos em `release/`
foram congelados para auditoria e não devem ser apresentados como uma versão
funcional, redistribuídos ou utilizados para resultados de pesquisa.

### Referência histórica: versão portátil
1. Baixe o arquivo `TychoBrahe_v1.0.0_Windows_x64_Portable.zip` na pasta `release/` ou na aba de Releases do GitHub.
2. Descompacte o arquivo `.zip` em qualquer pasta de sua preferência.
3. Dê um duplo clique no arquivo `INICIAR_TYCHO_BRAHE.bat` ou diretamente em `Tycho Brahe Search.exe`.
4. Esta sequência é histórica e **não é um procedimento de instalação validado**.

### Referência histórica: instalador Windows
1. Execute `Tycho_Brahe_Search_v1.0.0_Setup.exe` ou `Tycho_Brahe_Search_v1.0.0_x64.msi`.
2. Siga as instruções do assistente de instalação.
3. Não use esses instaladores como distribuição aprovada nesta etapa.

### Desenvolvimento: busca evidencial Marco 4

Para usar a rota atual de busca, gere o sidecar dedicado, provisione o M3
validado e inicie o desktop em desenvolvimento. O procedimento completo,
incluindo os limites de segurança e os estados de falha explícitos, está em
[INTEGRACAO_DESKTOP_M4.md](INTEGRACAO_DESKTOP_M4.md). O banco Marco 3 não é
incluído nos instaladores históricos.

---

## 2. Visão Geral da Interface

A entrada atual é a aba **Busca Evidencial (M4)**. Ela aceita ao menos um
filtro de entidade, rótulo, projeção, token ou regra e mostra a cadeia de
proveniência de cada ocorrência: arquivo e bloco PSD, âncora de nó, decisão e
evidências. Uma decisão `PENDENTE` deve ser lida como classificação heurística
revisável, nunca como uma árvore cartográfica automaticamente confirmada.

O esquema abaixo preserva as áreas históricas para auditoria; a consulta
histórica não é a rota M4:

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

## 3. Funcionalidades previstas de pesquisa sintática

### 3.1. Tipos de consultas em validação
- **Projeções Cartográficas Universais**: Busque por `SAP`, `VocP`, `ForceP`, `TopP`, `FocP`, `FinP`, `MoodP_evaluative`, `T_future`, `AspP_durative`, `VoiceP`, `ProcP`, `Root`, etc.
- **Constituintes Tradicionais do Corpus Tycho Brahe**: Busque por `NP-SBJ` (Sujeito), `NP-ACC` (Objeto Direto), `PP` (Sintagma Preposicional), `ADVP` (Sintagma Adverbial), `IP-MAT` (Oração Matriz), `CP-REL` (Oração Relativa).
- **Busca Lexical e Lemática**: prevista para filtrar por palavras específicas (ex: *rei*, *senhor*, *deu*) ou seus lemas subjacentes; ainda não deve ser considerada validada na interface atual.

### 3.2. Busca evidencial rastreável (Marco 4)

Use a aba **Busca Evidencial (M4)** para a rota implementada nesta revisão.
Os filtros são exatos, conjuntivos e limitados a 1--500 resultados. O painel
não aceita caminhos de banco, comandos livres ou a validação integral custosa:
o M3 só chega ao local da aplicação após o provisionamento verificado. Consulte
[BUSCA_RASTREAVEL.md](BUSCA_RASTREAVEL.md) para os campos e
[INTEGRACAO_DESKTOP_M4.md](INTEGRACAO_DESKTOP_M4.md) para a preparação.

### 3.3. Chips de Filtro Rápido
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

## 6. Módulo Human-in-the-Loop (fluxo em validação)

Sentenças históricas com anomalias estruturais ou ordens não-canônicas que violam a hierarquia universal de Cinque (1999) são automaticamente isoladas para auditoria humana:
1. Acesse a aba **🛡️ Revisão Quarentena**.
2. Visualize a lista de sentenças em quarentena com o diagnóstico da anomalia (ex: `HIERARQUIA_CINQUE_VIOLADA`, `CP_DESCONHECIDO`).
3. Compare a árvore original com a derivação cartográfica proposta.
4. A persistência das decisões está em correção; não use a interface atual para
   produzir decisões de curadoria definitivas.

---

## 7. Diagnóstico e Status do Sistema

Acesse a aba **⚙️ Diagnóstico** para verificar:
- Status de conexão com o motor Rust e o Sidecar Python.
- Caminhos absolutos e integridade dos bancos de dados SQLite ativos.
- Estatísticas em tempo real: número total de sentenças indexadas, nós cartográficos gerados e itens em quarentena.
