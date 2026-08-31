import os
import shutil
import zipfile
import sys


# Os pacotes v1.0.0 foram congelados para auditoria no Marco 1. A publicação
# só pode ser retomada conscientemente após a reconstrução e a validação dos
# bancos; este opt-in evita sobrescrever a evidência legada por engano.
if os.environ.get("TYCHO_ALLOW_EXPERIMENTAL_RELEASE") != "1":
    sys.stderr.write(
        "Publicação bloqueada: os artefatos atuais são experimentais e estão "
        "congelados. Consulte docs/STATUS_DE_ARTEFATOS.md. Para uma auditoria "
        "controlada, defina TYCHO_ALLOW_EXPERIMENTAL_RELEASE=1 explicitamente.\n"
    )
    raise SystemExit(2)

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
release_dir = os.path.join(root, 'release')
portable_dir = os.path.join(release_dir, 'TychoBrahe_v1.0.0_Portable')
installers_dir = os.path.join(release_dir, 'installers')

print(f'==> Preparando diretorios de Release em: {release_dir}')
os.makedirs(portable_dir, exist_ok=True)
os.makedirs(installers_dir, exist_ok=True)
os.makedirs(os.path.join(portable_dir, 'bin'), exist_ok=True)
os.makedirs(os.path.join(portable_dir, 'corpus_data'), exist_ok=True)
os.makedirs(os.path.join(portable_dir, 'docs'), exist_ok=True)

print('==> Copiando executaveis...')
tauri_exe = os.path.join(root, 'tycho-desktop', 'src-tauri', 'target', 'release', 'tycho-desktop.exe')
sidecar_exe = os.path.join(root, 'tycho-desktop', 'src-tauri', 'bin', 'tycho_backend-x86_64-pc-windows-msvc.exe')

shutil.copy2(tauri_exe, os.path.join(portable_dir, 'Tycho Brahe Search.exe'))
shutil.copy2(sidecar_exe, os.path.join(portable_dir, 'bin', 'tycho_backend-x86_64-pc-windows-msvc.exe'))
shutil.copy2(sidecar_exe, os.path.join(portable_dir, 'bin', 'tycho_backend.exe'))

print('==> Copiando bancos de dados SQLite...')
db_fase3 = os.path.join(root, 'corpus_data', 'corpus_fase3.db')
db_carto = os.path.join(root, 'corpus_data', 'corpus_cartografia.db')
if os.path.exists(db_fase3):
    shutil.copy2(db_fase3, os.path.join(portable_dir, 'corpus_data', 'corpus_fase3.db'))
if os.path.exists(db_carto):
    shutil.copy2(db_carto, os.path.join(portable_dir, 'corpus_data', 'corpus_cartografia.db'))

print('==> Copiando instaladores oficiais...')
msi_src = os.path.join(root, 'tycho-desktop', 'src-tauri', 'target', 'release', 'bundle', 'msi', 'Tycho Brahe Search_0.1.0_x64_en-US.msi')
nsis_src = os.path.join(root, 'tycho-desktop', 'src-tauri', 'target', 'release', 'bundle', 'nsis', 'Tycho Brahe Search_0.1.0_x64-setup.exe')
if os.path.exists(msi_src):
    shutil.copy2(msi_src, os.path.join(installers_dir, 'Tycho_Brahe_Search_v1.0.0_x64.msi'))
if os.path.exists(nsis_src):
    shutil.copy2(nsis_src, os.path.join(installers_dir, 'Tycho_Brahe_Search_v1.0.0_Setup.exe'))

bat_content = """@echo off
title Tycho Brahe - Pesquisa Sintatica Gerativa v1.0.0
echo =========================================================================
echo   TYCHO BRAHE - MOTOR DE PESQUISA SINTATICA GERATIVA E CARTOGRAFICA
echo   Desenvolvido por: Gabriel Pinheiro (IEL / Unicamp)
echo   Corpus: Tycho Brahe Parsed Corpus of Historical Portuguese
echo =========================================================================
echo.
echo Inicializando o ambiente desktop...
start "" "%~dp0Tycho Brahe Search.exe"
exit
"""
with open(os.path.join(portable_dir, 'INICIAR_TYCHO_BRAHE.bat'), 'w', encoding='utf-8') as f:
    f.write(bat_content)

readme_portable = """================================================================================
  TYCHO BRAHE - PESQUISA SINTATICA GERATIVA E CARTOGRAFICA (v1.0.0 PORTABLE)
  Desenvolvedor: Gabriel Pinheiro (Pesquisador em Linguistica - IEL / Unicamp)
================================================================================

Este pacote contem a versao portatil e autocontida do sistema Tycho Brahe Search.
NAO E NECESSARIO INSTALAR PYTHON, NODE.JS OU RUST PARA EXECUTAR ESTE PROGRAMA.

COMO EXECUTAR:
1. De um duplo clique no arquivo 'INICIAR_TYCHO_BRAHE.bat' ou em 'Tycho Brahe Search.exe'.
2. A interface grafica abrira automaticamente conectada aos bancos de dados.

ESTRUTURA DO PACOTE:
- Tycho Brahe Search.exe      -> Executavel principal da interface grafica nativa.
- INICIAR_TYCHO_BRAHE.bat     -> Atalho de inicializacao rapida com 1 clique.
- bin/                        -> Motor de processamento analitico e oraculo cartografico (Sidecar).
- corpus_data/                -> Bancos de dados SQLite indexados com a sintaxe expandida nos 5 dominios.
- docs/                       -> Documentacao teorica e manual do usuario.

CREDITOS E ATRIBUICAO:
- Corpus Tycho Brahe: Tycho Brahe Parsed Corpus of Historical Portuguese
  Universidade Estadual de Campinas (UNICAMP) / IEL / FAPESP
  Website: http://www.tycho.iel.unicamp.br/
================================================================================
"""
with open(os.path.join(portable_dir, 'LEIA-ME.txt'), 'w', encoding='utf-8') as f:
    f.write(readme_portable)

# Gerar Documentos Oficiais em docs/
docs_root = os.path.join(root, 'docs')
os.makedirs(docs_root, exist_ok=True)

# 1. MANUAL_DO_USUARIO.md
manual_content = """# Manual do Usuário - Tycho Brahe Search v1.0.0

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
"""
with open(os.path.join(docs_root, 'MANUAL_DO_USUARIO.md'), 'w', encoding='utf-8') as f:
    f.write(manual_content)
with open(os.path.join(portable_dir, 'docs', 'MANUAL_DO_USUARIO.md'), 'w', encoding='utf-8') as f:
    f.write(manual_content)

# 2. GUIA_CARTOGRAFIA_SINTATICA.md
guia_content = """# Guia Teórico da Cartografia Sintática e os 5 Grandes Domínios

Este documento descreve o modelo teórico de Gramática Gerativa formal implementado no **Tycho Brahe Search**, fundamentado no Programa Cartográfico (*Cartographic Approach*) iniciado por Luigi Rizzi (1997, 2004), Guglielmo Cinque (1999), Adriana Belletti (2004), Gillian Ramchand (2008) e pesquisadores associados.

---

## 1. Fundamentos Teóricos

A abordagem tradicional de sintaxe gerativa representava a estrutura sentencial por meio de nós oracionais genéricos:
$$\\text{CP} \\longrightarrow \\text{IP} \\longrightarrow \\text{VP}$$

No Programa Cartográfico, esses nós sintéticos foram decompostos em uma **hierarquia estrita e universal de dezenas de projeções funcionais**, permitindo o mapeamento fino de traços ilocucionários, informacionais, modais, temporais, aspectuais e argumentais.

```mermaid
graph TD
    D1["DOMÍNIO 1: ATO DE FALA (Extrema Periferia Esquerda) - SAP, VocP, EvalP"]
    D2["DOMÍNIO 2: COMPLEMENTIZADOR (Split-CP) - ForceP, TopP, IntP, FocP, ModP, FinP"]
    D3["DOMÍNIO 3: FLEXIONAL (Split-IP / TP) - MoodP, ModP, TP, AspP, VoiceP"]
    D4["DOMÍNIO 4: BAIXA PERIFERIA ESQUERDA (Acima de vP) - TopP_low, FocP_low"]
    D5["DOMÍNIO 5: TEMÁTICO E ARGUMENTAL (Split-vP / First Phase) - VoiceP, InitP, ProcP, ResP, Root"]

    D1 --> D2
    D2 --> D3
    D3 --> D4
    D4 --> D5
```

---

## 2. A Hierarquia Universal dos 5 Grandes Domínios

### Domínio 1: O Domínio do Ato de Fala (Extrema Periferia Esquerda)
*Fundamentação: Speas & Tenny (2003), Hill (2007).*
Codifica a ancoragem pragmática e a relação de interlocução direta entre Falante (*Speaker*) e Ouvinte (*Hearer*):
1. **`SAP` (Speech Act Phrase)**: Codifica a força pragmática e a interação de fala.
2. **`VocP` (Vocative Phrase)**: Posição estrutural de ancoragem de vocativos e chamamentos (*Senhor*, *Ó Deus*).
3. **`EvalP / AttP` (Evaluative / Attitude Phrase)**: Ponto de ancoragem para atitudes expressivas do enunciador (*Francamente*, *Honestamente*).

---

### Domínio 2: O Domínio Complementizador (Split-CP)
*Fundamentação: Rizzi (1997, 2001, 2004).*
Interface entre a proposição e o contexto discursivo/oracional externo:
1. **`ForceP`**: Tipo ilocucionário da oração (declarativa, interrogativa, imperativa, exclamativa) e complementizadores matrizes (*que*).
2. **`TopP (Shift)*`**: Tópico discursivo de mudança ou contraste (*Aboutness-Shift Topic*).
3. **`IntP`**: Operador interrogativo de orações sim/não (*se*, *porventura*).
4. **`TopP (Familiar)*`**: Tópico familiar/dado no contexto compartilhado.
5. **`FocP`**: Foco contrastivo, clivadas e operadores *Wh-* interrogativos (*quem*, *o que*, *quando*).
6. **`ModP`**: Posição modificadora para advérbios da periferia esquerda (*rapidamente* pré-verbal focalizado).
7. **`QembP`**: Perguntas embutidas e subordinadas interrogativas indiretas.
8. **`FinP`**: Especificação de finitude (tempo finito vs infinitivo/gerúndio) e fronteira com o domínio flexional.

---

### Domínio 3: O Domínio Flexional (Split-IP / TP)
*Fundamentação: Cinque (1999).*
Hierarquia universal e estrita de projeções modais, temporais, aspectuais e de voz. O sistema impõe a seguinte ordenação invariante:
1. **`MoodP_speech-act`**: *francamente*, *honestamente*.
2. **`MoodP_evaluative`**: *felizmente*, *lamentavelmente*.
3. **`MoodP_evidential`**: *evidentemente*, *alegadamente*.
4. **`ModP_epistemic`**: *provavelmente*, *possivelmente*.
5. **`T_Past / T_Future`**: *então*, *amanhã*, *antigamente*.
6. **`MoodP_irrealis`**: *talvez*.
7. **`ModP_necessity`**: *necessariamente*, *obrigatoriamente*.
8. **`ModP_possibility`**: *possivelmente*.
9. **`ModP_volitional`**: *voluntariamente*, *de bom grado*.
10. **`ModP_obligation`**: *obrigatoriamente*.
11. **`ModP_ability/permission`**: *facilmente*, *livremente*.
12. **`AspP_habitual`**: *habitualmente*, *costumeiramente*.
13. **`T_Anterior`**: *já*, *outrora*.
14. **`AspP_terminative`**: *não mais*, *cessantemente*.
15. **`AspP_continuative`**: *ainda*, *continuamente*.
16. **`AspP_perfect`**: *sempre*, *nunca*.
17. **`AspP_retrospective`**: *recentemente*, *logo*.
18. **`AspP_proximative`**: *prestes a*, *quase*.
19. **`AspP_durative`**: *brevemente*, *longamente*.
20. **`AspP_progressive`**: *progressivamente*, *a passo e passo*.
21. **`AspP_prospective`**: *futuramente*, *em breve*.
22. **`AspP_completive`**: *completamente*, *de todo*.
23. **`VoiceP`**: *bem*, *mal* (Voz ativa, passiva, média).

---

### Domínio 4: A Baixa Periferia Esquerda
*Fundamentação: Belletti (2004).*
Zona informacional situada na borda superior do vP para ativação de constituintes no domínio pós-verbal:
1. **`TopP_low`**: Tópico baixo de ligação anafórica.
2. **`FocP_low`**: Foco informacional baixo / Sujeitos pós-verbais in situ (*Chegou [o rei]*).
3. **`TopP_low`**: Posição baixa de clíticos e elementos topicalizados internamente.

---

### Domínio 5: O Domínio Temático e Argumental (Split-vP / First Phase)
*Fundamentação: Ramchand (2008), Pylkkänen (2008), Harley (2013).*
Decomposição da micro-estrutura do evento verbal e atribuição de papéis temáticos:
1. **`VoiceP`**: Introdução do argumento externo / Iniciador / Agente.
2. **`InitP` (Initiation Phrase)**: Sub-evento que desencadeia a causalidade do evento.
3. **`ApplP_high` (High Applicative Phrase)**: Introdução de beneficiários / malfeitores externos.
4. **`ProcP` (Process Phrase)**: Núcleo dinâmico verbal / Processo em desenvolvimento.
5. **`ApplP_low` (Low Applicative Phrase)**: Introdução de recipient / posse / alvo interno.
6. **`ResP` (Result Phrase)**: Sub-evento de estado resultante ou telicidade.
7. **`Root / Path / Ground / Meas`**: Raiz lexical pura, trajetória e Tema/Paciente afetado.
"""
with open(os.path.join(docs_root, 'GUIA_CARTOGRAFIA_SINTATICA.md'), 'w', encoding='utf-8') as f:
    f.write(guia_content)
with open(os.path.join(portable_dir, 'docs', 'GUIA_CARTOGRAFIA_SINTATICA.md'), 'w', encoding='utf-8') as f:
    f.write(guia_content)

# 3. ARQUITETURA_DO_SISTEMA.md
arq_content = """# Arquitetura do Sistema - Tycho Brahe Search

O **Tycho Brahe Search** foi arquitetado como uma aplicação tripartida de alta performance e desacoplamento modular, combinando o ecossistema nativo do **Rust (Tauri v2)**, o poder analítico de **Python (NLP, spaCy, NLTK, SQLite)** e uma interface moderna em **React 19 + TypeScript + Tailwind CSS + D3.js**.

---

## 1. Diagrama Geral de Camadas

```mermaid
graph TD
    subgraph Frontend [Camada 1: Frontend Desktop React 19 + TypeScript]
        UI[Interface de Pesquisa & Visualizador D3]
        HitL[Painel Human-in-the-Loop]
        API[Cliente IPC: services/api.ts]
    end

    subgraph RustCore [Camada 2: Motor Nativo Rust / Tauri v2 Core]
        Handler[IPC Commands: run_backend_query]
        Health[Verificador de Saúde do Sistema]
        Sandbox[Sandboxing & Capabilities: default.json]
    end

    subgraph PythonBackend [Camada 3: Motor Analítico & Banco de Dados Python]
        Sidecar[Executável PyInstaller: tycho_backend.exe]
        Oracle[Oráculo Cartográfico: oracle.py]
        Rewriter[Transdutor de Árvores: rewriter.py]
        Tokenizer[Tokenizador Termo a Termo: tokenizador_cartografico.py]
        DB[(Bancos de Dados SQLite: corpus_fase3.db & corpus_cartografia.db)]
    end

    UI --> API
    HitL --> API
    API -- Invocação Tauri IPC --> Handler
    Handler -- Validação AppSec --> Sandbox
    Sandbox -- Execução Segura Sidecar --> Sidecar
    Sidecar --> Oracle
    Oracle --> Rewriter
    Rewriter --> Tokenizer
    Tokenizer --> DB
    Sidecar -- Resposta JSON UTF-8 --> Handler
    Handler -- Retorno Assíncrono --> API
    API --> UI
```

---

## 2. Descrição das Camadas

### Camada 1: Frontend (React / TypeScript / Tailwind / D3)
- **Localização**: `tycho-desktop/src/`
- **Responsabilidade**: Renderização gráfica, visualizador interativo em árvore SVG com pan/zoom via D3, tabela termo a termo com badges cromáticas por domínio, e sistema de auditoria *Human-in-the-Loop*.
- **Comunicação**: Invoca os comandos do Tauri nativo de forma assíncrona com tipagem estrita TypeScript.

### Camada 2: Motor Rust (Tauri v2 Shell)
- **Localização**: `tycho-desktop/src-tauri/`
- **Responsabilidade**: Camada de orquestração do sistema operacional. Gerencia o ciclo de vida do processo Python Sidecar, aplica validações de segurança (AppSec) contra Self-DoS, controla a política estrita de *Content Security Policy* (CSP) e compila executáveis nativos com otimizações LTO (*Link-Time Optimization*).

### Camada 3: Motor Analítico Python (PyInstaller Sidecar)
- **Localização**: `python_backend/`
- **Responsabilidade**:
  - `oracle.py`: Classificador de traços cartográficos e diagnósticos estruturais.
  - `rewriter.py`: Transdutor recursivo que expande nós sintéticos (CP, IP, VP) na hierarquia dos 5 domínios.
  - `tokenizador_cartografico.py`: Extração de lema, classe morfológica (POS) e mapeamento de papéis gerativos universais.
  - `pesquisa_sintatica.py`: Roteador CLI de alta velocidade que consulta as bases SQLite indexadas com o *Nested Set Model* (lft/rgt).
"""
with open(os.path.join(docs_root, 'ARQUITETURA_DO_SISTEMA.md'), 'w', encoding='utf-8') as f:
    f.write(arq_content)
with open(os.path.join(portable_dir, 'docs', 'ARQUITETURA_DO_SISTEMA.md'), 'w', encoding='utf-8') as f:
    f.write(arq_content)

# 4. REFERENCIAS_E_CREDITOS.md
ref_content = """# Referências Bibliográficas e Créditos Institucionais

## Autoria e Desenvolvimento do Software
- **Autor**: Gabriel Pinheiro
- **Filiação Institucional**: Pesquisador em Linguística no Instituto de Estudos da Linguagem (IEL) / Universidade Estadual de Campinas (UNICAMP).
- **Repositório do Projeto**: [https://github.com/blightghp/tycho-brahe-corpus-search](https://github.com/blightghp/tycho-brahe-corpus-search)

---

## Atribuição Institucional do Corpus
Este software utiliza como base analítica as árvores sintáticas anotadas do **Tycho Brahe Parsed Corpus of Historical Portuguese**:
- **Instituição**: Universidade Estadual de Campinas (UNICAMP) / Instituto de Estudos da Linguagem (IEL) / FAPESP.
- **Coordenação Histórica**: Charlotte Galves, Helena Britto, et al.
- **Portal Oficial do Projeto**: [http://www.tycho.iel.unicamp.br/](http://www.tycho.iel.unicamp.br/)
- **Documentação de Anotação**: [Guia de Anotação Sintática do Corpus Tycho Brahe](http://www.tycho.iel.unicamp.br/~corpus/manual/annotation.html)

---

## Referências Teóricas em Gramática Gerativa e Cartografia Sintática

1. **Belletti, Adriana (2004)**. *Aspects of the Low IP Area*. In: The Structure of CP and IP (The Cartography of Syntactic Structures, Vol. 2), ed. Luigi Rizzi, Oxford University Press, pp. 16-51.
2. **Cinque, Guglielmo (1999)**. *Adverbs and Functional Heads: A Cross-Linguistic Perspective*. Oxford University Press.
3. **Galves, Charlotte; Faria, Pablo (2010)**. *O Corpus Anotado Tycho Brahe: Métodos e Ferramentas para a Sintaxe Histórica do Português*. Revista de Estudos Linguísticos.
4. **Harley, Heidi (2013)**. *External Arguments and the VoiceP*. In: Generative Syntax in the Twenty-First Century.
5. **Hill, Virginia (2007)**. *Vocatives and the left periphery*. Lingua, 117(12), 2077-2105.
6. **Pylkkänen, Liina (2008)**. *Introducing Arguments*. MIT Press.
7. **Ramchand, Gillian (2008)**. *Verb Meaning and the Lexicon: A First Phase Syntax*. Cambridge University Press.
8. **Rizzi, Luigi (1997)**. *The Fine Structure of the Left Periphery*. In: Elements of Grammar, ed. Liliane Haegeman, Kluwer, pp. 281-337.
9. **Rizzi, Luigi (2004)**. *Locality and Left Periphery*. In: Structures and Beyond (The Cartography of Syntactic Structures, Vol. 3), ed. Adriana Belletti, Oxford University Press, pp. 223-251.
10. **Speas, Peggy; Tenny, Carol (2003)**. *Configurational properties of point of view roles*. In: Asymmetry in Grammar, John Benjamins, pp. 315-344.

---

## Como Citar Este Projeto

```bibtex
@software{pinheiro2026tychobrahe,
  author = {Gabriel Pinheiro},
  title = {Tycho Brahe Search: Motor Desktop de Pesquisa Sintática Gerativa e Cartográfica},
  year = {2026},
  publisher = {GitHub},
  journal = {GitHub repository},
  howpublished = {\\url{https://github.com/blightghp/tycho-brahe-corpus-search}},
  institution = {Instituto de Estudos da Linguagem, Universidade Estadual de Campinas (UNICAMP)}
}
```
"""
with open(os.path.join(docs_root, 'REFERENCIAS_E_CREDITOS.md'), 'w', encoding='utf-8') as f:
    f.write(ref_content)
with open(os.path.join(portable_dir, 'docs', 'REFERENCIAS_E_CREDITOS.md'), 'w', encoding='utf-8') as f:
    f.write(ref_content)

# 5. REESCREVER README.md PRINCIPAL
main_readme = """# Tycho Brahe Search: Plataforma de Pesquisa Sintática Gerativa e Cartográfica

[![Release v1.0.0](https://img.shields.io/badge/release-v1.0.0-emerald.svg)](https://github.com/blightghp/tycho-brahe-corpus-search/releases)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20x64-indigo.svg)](https://github.com/blightghp/tycho-brahe-corpus-search/releases)
[![Rust](https://img.shields.io/badge/core-Rust%20%2F%20Tauri%20v2-orange.svg)](https://tauri.app/)
[![Python NLP](https://img.shields.io/badge/nlp-Python%20%2F%20spaCy%20%2F%20NLTK-yellow.svg)](https://spacy.io/)
[![Frontend](https://img.shields.io/badge/ui-React%2019%20%2F%20Tailwind%20%2F%20D3-cyan.svg)](https://react.dev/)

> **Desenvolvido por Gabriel Pinheiro**  
> *Pesquisador em Linguística no Instituto de Estudos da Linguagem (IEL) / Universidade Estadual de Campinas (UNICAMP)*  
> Projeto associado ao [Tycho Brahe Parsed Corpus of Historical Portuguese](http://www.tycho.iel.unicamp.br/)

---

## 📖 Apresentação do Projeto

O **Tycho Brahe Search** é um ambiente computacional integrado para investigação morfossintática, análise diacrônica e visualização cartográfica de árvores sintáticas históricas em língua portuguesa. 

O software realiza a transdução algorítmica das anotações sintáticas clássicas do *Corpus Tycho Brahe* em **árvores cartográficas universais de 5 domínios**, permitindo o mapeamento fino de traços de ato de fala, complementizadores (Split-CP), hierarquia adverbial e flexional de Cinque (Split-IP), baixa periferia informacional e estrutura temática de primeira fase (Split-vP).

```
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                      OS 5 GRANDES DOMÍNIOS CARTOGRÁFICOS                    │
 ├─────────────────────────────────────────────────────────────────────────────┤
 │  🟣 Domínio 1 (Ato de Fala)         : SAP → VocP → EvalP / AttP             │
 │  🔵 Domínio 2 (Split-CP)            : ForceP → TopP* → IntP → FocP → FinP   │
 │  🟢 Domínio 3 (Split-IP / Cinque)   : MoodP → ModP → TP → AspP → VoiceP     │
 │  🟡 Domínio 4 (Baixa Periferia)     : TopP_low → FocP_low (Sujeito Pós-V)   │
 │  🔴 Domínio 5 (First Phase Syntax)  : VoiceP → InitP → ProcP → ResP → Root  │
 └─────────────────────────────────────────────────────────────────────────────┘
```

---

## ✨ Principais Funcionalidades

- 🌳 **Visualizador Interativo de Árvores D3.js**: Renderização gráfica dinâmica em SVG com zoom contínuo, pan, centralização e codificação cromática por domínio teórico.
- 🔬 **Decomposição Morfossintática Termo a Termo**: Grade estrutural com extração automática de tokens arcaicos, lemas normatizados, POS tags spaCy e papéis gerativos formais.
- ⚡ **Motor de Busca Hierárquica de Alta Performance**: Consultas instantâneas por labels exatos, categorias base, funções sintáticas, dominância direta ($A < B$), dominância indireta ($A \\ll B$) e co-irmandade ($A \\$ B$) indexadas em SQLite (*Nested Set Model*).
- 🛡️ **Módulo Human-in-the-Loop (Auditoria de Quarentena)**: Isolamento automático e interface de revisão comparativa de sentenças com inversões ou anomalias da hierarquia universal de Cinque.
- 🚀 **Arquitetura Tripartida Segura**: Core nativo em Rust (Tauri v2) com sandboxing estrito e Content Security Policy (CSP), sidecar analítico Python (PyInstaller) e frontend reativo em React 19 + TypeScript.
- 📦 **Distribuição 100% Portátil**: Executável único pronto para uso, sem necessidade de instalar Node.js, Python ou compiladores.

---

## 📥 Download e Execução Imediata

Você pode baixar a versão pronta para uso diretamente da pasta [`release/`](./release) deste repositório ou na aba [Releases](https://github.com/blightghp/tycho-brahe-corpus-search/releases):

| Pacote | Tamanho | Descrição | Link de Download |
| :--- | :---: | :--- | :--- |
| 📦 **Versão Portátil (.ZIP)** | ~243 MB | **Recomendado**. Descompacte e execute com 1 clique (sem instalação). | [`TychoBrahe_v1.0.0_Windows_x64_Portable.zip`](./release/TychoBrahe_v1.0.0_Windows_x64_Portable.zip) |
| ⚙️ **Instalador Setup (.EXE)** | ~115 MB | Instalador guiado padrão do Windows com atalho no menu iniciar. | [`Tycho_Brahe_Search_v1.0.0_Setup.exe`](./release/installers/Tycho_Brahe_Search_v1.0.0_Setup.exe) |
| 🛡️ **Pacote MSI (.MSI)** | ~143 MB | Instalador corporativo/acadêmico Windows Installer WiX. | [`Tycho_Brahe_Search_v1.0.0_x64.msi`](./release/installers/Tycho_Brahe_Search_v1.0.0_x64.msi) |

### Como Executar a Versão Portátil (1 Clique):
1. Baixe o [`TychoBrahe_v1.0.0_Windows_x64_Portable.zip`](./release/TychoBrahe_v1.0.0_Windows_x64_Portable.zip).
2. Extraia o arquivo ZIP em qualquer diretório.
3. Dê um duplo clique em **`INICIAR_TYCHO_BRAHE.bat`** (ou `Tycho Brahe Search.exe`).

---

## 📚 Documentação do Projeto

Para consultar os manuais e diretrizes aprofundadas, acesse os guias na pasta [`docs/`](./docs):

- 📘 [**Manual do Usuário**](./docs/MANUAL_DO_USUARIO.md): Guia completo de navegação, consultas, atalhos e auditoria.
- 🔬 [**Guia de Cartografia Sintática**](./docs/GUIA_CARTOGRAFIA_SINTATICA.md): Fundamentação teórica dos 5 grandes domínios e 44 projeções funcionais universais.
- 🏛️ [**Arquitetura do Sistema**](./docs/ARQUITETURA_DO_SISTEMA.md): Diagrama detalhado do pipeline Rust + Python + TypeScript/D3.
- 🛡️ [**Relatório de Auditoria AppSec**](./docs/revisao_appsec.md): Medidas defensivas, mitigação de SQLi, prevenção de Self-DoS e sandboxing CSP.
- 🎓 [**Referências Bibliográficas e Créditos**](./docs/REFERENCIAS_E_CREDITOS.md): Atribuições acadêmicas, histórico do Corpus Tycho Brahe e citação em BibTeX.

---

## 🏛️ Estrutura do Repositório

```
tycho-brahe-corpus-search/
├── README.md                     <- Apresentação principal do projeto
├── release/                      <- Binários executáveis, instaladores e ZIP portátil
│   ├── TychoBrahe_v1.0.0_Windows_x64_Portable.zip
│   ├── installers/               <- Instaladores MSI e Setup.exe
│   └── TychoBrahe_v1.0.0_Portable/ <- Diretório descompactado pronto para execução
├── docs/                         <- Manuais e documentações teóricas e arquiteturais
│   ├── MANUAL_DO_USUARIO.md
│   ├── GUIA_CARTOGRAFIA_SINTATICA.md
│   ├── ARQUITETURA_DO_SISTEMA.md
│   ├── REFERENCIAS_E_CREDITOS.md
│   └── revisao_appsec.md
├── corpus_data/                  <- Textos históricos (.txt) e bancos SQLite (.db)
├── python_backend/               <- Oráculo cartográfico, rewriter, tokenizador e CLI
│   ├── cartografia_schema.py
│   ├── oracle.py
│   ├── rewriter.py
│   ├── tokenizador_cartografico.py
│   ├── pesquisa_sintatica.py
│   └── test_e2e_pipeline.py
└── tycho-desktop/                <- Aplicação Desktop Tauri v2 + React 19 + TypeScript
    ├── src/                      <- Componentes React, D3 TreeView, TermBreakdown
    └── src-tauri/                <- Motor Rust, sidecars e configuração de segurança
```

---

## 🔬 Como Citar

Se você utilizar este software em suas pesquisas e publicações acadêmicas, por favor cite:

```bibtex
@software{pinheiro2026tychobrahe,
  author = {Gabriel Pinheiro},
  title = {Tycho Brahe Search: Motor Desktop de Pesquisa Sintática Gerativa e Cartográfica},
  year = {2026},
  publisher = {GitHub},
  howpublished = {\\url{https://github.com/blightghp/tycho-brahe-corpus-search}},
  institution = {Instituto de Estudos da Linguagem, Universidade Estadual de Campinas (UNICAMP)}
}
```

---

## 🎓 Agradecimentos e Créditos Institucionais

- **Corpus Tycho Brahe**: *Tycho Brahe Parsed Corpus of Historical Portuguese*  
  Universidade Estadual de Campinas (UNICAMP) / Instituto de Estudos da Linguagem (IEL) / FAPESP  
  Portal Oficial: [http://www.tycho.iel.unicamp.br/](http://www.tycho.iel.unicamp.br/)
"""
with open(os.path.join(root, 'README.md'), 'w', encoding='utf-8') as f:
    f.write(main_readme)

print('==> Recompactando arquivo ZIP portátil atualizado...')
zip_path = os.path.join(release_dir, 'TychoBrahe_v1.0.0_Windows_x64_Portable.zip')
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    for foldername, subfolders, filenames in os.walk(portable_dir):
        for filename in filenames:
            file_path = os.path.join(foldername, filename)
            arcname = os.path.relpath(file_path, portable_dir)
            zf.write(file_path, arcname)

print('==> Processo de Release e Documentação Concluído com Sucesso!')
for item in os.listdir(release_dir):
    p = os.path.join(release_dir, item)
    sz = os.path.getsize(p) if os.path.isfile(p) else 'DIR'
    print(f'  {item}: {sz}')
