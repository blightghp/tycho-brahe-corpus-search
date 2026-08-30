# Tycho Brahe Search: Plataforma de Pesquisa Sintática Gerativa e Cartográfica

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
- ⚡ **Motor de Busca Hierárquica de Alta Performance**: Consultas instantâneas por labels exatos, categorias base, funções sintáticas, dominância direta ($A < B$), dominância indireta ($A \ll B$) e co-irmandade ($A \$ B$) indexadas em SQLite (*Nested Set Model*).
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
  howpublished = {\url{https://github.com/blightghp/tycho-brahe-corpus-search}},
  institution = {Instituto de Estudos da Linguagem, Universidade Estadual de Campinas (UNICAMP)}
}
```

---

## 🎓 Agradecimentos e Créditos Institucionais

- **Corpus Tycho Brahe**: *Tycho Brahe Parsed Corpus of Historical Portuguese*  
  Universidade Estadual de Campinas (UNICAMP) / Instituto de Estudos da Linguagem (IEL) / FAPESP  
  Portal Oficial: [http://www.tycho.iel.unicamp.br/](http://www.tycho.iel.unicamp.br/)
