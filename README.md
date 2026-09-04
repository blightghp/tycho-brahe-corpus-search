# Tycho Brahe Search: Plataforma de Pesquisa Sintática Gerativa e Cartográfica

[![Estado](https://img.shields.io/badge/estado-reconstru%C3%A7%C3%A3o%20controlada-amber.svg)](docs/STATUS_DE_ARTEFATOS.md)
[![Direitos reservados](https://img.shields.io/badge/direitos-reservados-4f46e5.svg)](NOTICE.md)
[![Platform](https://img.shields.io/badge/platform-Windows%20x64-indigo.svg)](docs/STATUS_DE_ARTEFATOS.md)
[![Rust](https://img.shields.io/badge/core-Rust%20%2F%20Tauri%20v2-orange.svg)](https://tauri.app/)
[![Python NLP](https://img.shields.io/badge/nlp-Python%20%2F%20spaCy%20%2F%20NLTK-yellow.svg)](https://spacy.io/)
[![Frontend](https://img.shields.io/badge/ui-React%2019%20%2F%20Tailwind%20%2F%20D3-cyan.svg)](https://react.dev/)

> **Plataforma Tycho Brahe** — Todos os direitos reservados à Plataforma Tycho Brahe © 2026
>
> Criada e desenvolvida principalmente por **Luiz Henrique Lima Veronesi** como fruto de sua tese de doutorado em Linguística no IEL/UNICAMP.
>
> Professora e orientadora: **Profª Drª Charlotte Galves** — Instituto de Estudos da Linguagem (IEL) / Universidade Estadual de Campinas (UNICAMP).
>
> Projeto associado ao [DACILAT](https://www.tycho.iel.unicamp.br/dacilat), cujos corpora e colaboradores ajudam a alimentar a Plataforma Tycho Brahe.
>
> O **Tycho Brahe Search** (este motor de busca complementar) foi elaborado por **Gabriel Pinheiro**,
> a partir de sua proposta de implementação dos núcleos cartográficos com uma arquitetura projetada como ferramenta complementar à plataforma.
>
> **Referência principal:**
> VERONESI, Luiz Henrique Lima. *A Plataforma Tycho Brahe: um sistema para corpora sintaticamente anotados*. 2026. 211 f. Tese (Doutorado em Linguística) — Instituto de Estudos da Linguagem, Universidade Estadual de Campinas, Campinas, 2026. Disponível em: [https://www.tycho.iel.unicamp.br/upload/Luiz_Veronesi_A_Plataforma_Tycho_Brahe_Tese_2026.pdf](https://www.tycho.iel.unicamp.br/upload/Luiz_Veronesi_A_Plataforma_Tycho_Brahe_Tese_2026.pdf)
>
> **Termos do corpus:** [termos oficiais do Corpus Histórico do Português Tycho Brahe](https://www.tycho.iel.unicamp.br/corpus/termos.html). Eles são a fonte vinculante para qualquer uso de dados; o cliente desktop não inclui nem licencia o corpus, M2, M3 ou credenciais.

> [!WARNING]
> **Estado do projeto: reconstrução controlada — Marcos 2 e 3 concluídos; busca
> Marco 4 e ponte desktop Marco 5 implementadas.** A importação PSD é
> rastreável e reproduzível, a camada Marco 3 registra âncoras e evidências
> gramaticais sem reescrever o corpus, e a busca devolve proveniência
> obrigatória. A tela desktop requer um M3 validado e provisionado; os bancos
> `corpus_cartografia.db`, `corpus_fase3.db` e os pacotes `v1.0.0` continuam
> artefatos experimentais arquivados. A transdução cartográfica integral, a
> distribuição estável ainda não estão certificadas. Consulte o
> [estado dos artefatos](docs/STATUS_DE_ARTEFATOS.md) e a
> [busca rastreável](docs/BUSCA_RASTREAVEL.md).

---

## 📖 Apresentação do Projeto

O **Tycho Brahe Search** é um ambiente computacional em reconstrução para
investigação morfossintática, análise diacrônica e visualização cartográfica de
árvores sintáticas históricas em língua portuguesa.

Os cinco domínios abaixo formam a ontologia e a meta de implementação. A sua
instanciação integral e a distribuição pesquisável estão em validação; a
situação verificável está documentada em
[STATUS_DE_ARTEFATOS.md](docs/STATUS_DE_ARTEFATOS.md).

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

## ✨ Arquitetura-alvo em reconstrução

- 🌳 **Visualizador Interativo de Árvores D3.js**: Renderização gráfica dinâmica em SVG com zoom contínuo, pan, centralização e codificação cromática por domínio teórico.
- 🔬 **Decomposição Morfossintática Termo a Termo**: Grade estrutural com extração automática de tokens arcaicos, lemas normatizados, POS tags spaCy e papéis gerativos formais.
- ⚡ **Motor de Busca Hierárquica**: consultas por labels, categorias, funções e relações estruturais, em reconstrução com contrato de resultados por sentença.
- 🛡️ **Módulo Human-in-the-Loop (Auditoria de Quarentena)**: Isolamento automático e interface de revisão comparativa de sentenças com inversões ou anomalias da hierarquia universal de Cinque.
- 🚀 **Arquitetura Tripartida Segura**: Core nativo em Rust (Tauri v2) com sandboxing estrito e Content Security Policy (CSP), sidecar analítico Python (PyInstaller) e frontend reativo em React 19 + TypeScript.
- 📦 **Prévia técnica verificável**: o cliente `v0.2.0` é distribuído sem corpus, M2 ou M3, com aceite dos termos e evidência de validação M3/M4/M5; não constitui distribuição científica estável.

---

## 📥 Estado de distribuição

Há uma [prévia técnica Windows `v0.2.0`](https://github.com/blightghp/tycho-brahe-corpus-search/releases/tag/v0.2.0) do cliente desktop. Ela substitui os instaladores antigos apenas como canal técnico do aplicativo: o pacote NSIS exige aceite dos termos, não contém PSD, M2, M3, credenciais ou qualquer cópia do corpus, e não concede acesso aos dados.

O uso de dados do Corpus Histórico do Português Tycho Brahe continua sujeito aos [termos oficiais do portal](https://www.tycho.iel.unicamp.br/corpus/termos.html), inclusive restrições de finalidade acadêmica/pedagógica, uso comercial, redistribuição, senhas e citação. A prévia não certifica uma transdução cartográfica integral nem uma distribuição científica estável. Os pacotes `v1.0.0`, ZIP e diretório `release/` permanecem arquivados somente para auditoria e não devem ser utilizados.

---

## 📚 Documentação do Projeto

Para consultar os manuais e diretrizes aprofundadas, acesse os guias na pasta [`docs/`](./docs):

- 📘 [**Manual do Usuário**](./docs/MANUAL_DO_USUARIO.md): Guia completo de navegação, consultas, atalhos e auditoria.
- 🧭 [**Estado dos Artefatos**](./docs/STATUS_DE_ARTEFATOS.md): Fonte de verdade sobre dados, bancos, pacotes e política de publicação.
- 🧱 [**Importação Rastreável**](./docs/IMPORTACAO_RASTREAVEL.md): Contrato do banco Marco 2, evidências, rejeições e reprodução segura.
- 🔎 [**Busca Rastreável**](./docs/BUSCA_RASTREAVEL.md): Consultas Marco 4 por entidade, rótulo, projeção, token e regra, com proveniência obrigatória.
- 🖥️ [**Integração Desktop M4**](./docs/INTEGRACAO_DESKTOP_M4.md): Sidecar dedicado, provisionamento verificado do M3 e contrato Tauri/React restrito.
- ✅ [**Validação M3/M4/M5 — 2026-09-04**](./docs/VALIDACAO_M3_M4_M5_2026-09-04.md): Evidências de reconstrução, busca, ponte desktop, instalador e gates da prévia técnica.
- 📊 [**Auditoria de Cobertura M3**](./docs/AUDITORIA_COBERTURA_M3.md): Relatório Marco 6 somente leitura de cobertura, regras, evidências e backlog de curadoria.
- 🔬 [**Guia de Cartografia Sintática**](./docs/GUIA_CARTOGRAFIA_SINTATICA.md): Fundamentação teórica dos 5 grandes domínios e 44 projeções funcionais universais.
- 🏛️ [**Arquitetura do Sistema**](./docs/ARQUITETURA_DO_SISTEMA.md): Diagrama detalhado do pipeline Rust + Python + TypeScript/D3.
- 🛡️ [**Relatório de Auditoria AppSec**](./docs/revisao_appsec.md): Medidas defensivas, mitigação de SQLi, prevenção de Self-DoS e sandboxing CSP.
- 🎓 [**Referências Bibliográficas e Créditos**](./docs/REFERENCIAS_E_CREDITOS.md): Atribuições acadêmicas, histórico do Corpus Tycho Brahe e citação em BibTeX.

---

## 🏛️ Estrutura do Repositório

```
tycho-brahe-corpus-search/
├── README.md                     <- Apresentação principal do projeto
├── release/                      <- Artefatos legados congelados; não são uma distribuição suportada
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

Se você utilizar a **Plataforma Tycho Brahe** em suas pesquisas e publicações acadêmicas, por favor cite a referência principal:

```bibtex
@phdthesis{veronesi2026tychobrahe,
  author = {Luiz Henrique Lima Veronesi},
  title = {A Plataforma Tycho Brahe: um sistema para corpora sintaticamente anotados},
  year = {2026},
  school = {Universidade Estadual de Campinas},
  type = {Tese (Doutorado em Linguística)},
  address = {Campinas},
  pages = {211},
  url = {https://www.tycho.iel.unicamp.br/upload/Luiz_Veronesi_A_Plataforma_Tycho_Brahe_Tese_2026.pdf}
}
```

Para citar especificamente o **motor de busca cartográfico** (esta ferramenta complementar):

```bibtex
@software{tychobrahesearch2026,
  title = {Tycho Brahe Search: Motor Desktop de Pesquisa Sintática Gerativa e Cartográfica},
  year = {2026},
  publisher = {GitHub},
  howpublished = {\url{https://github.com/blightghp/tycho-brahe-corpus-search}},
  note = {Ferramenta complementar à Plataforma Tycho Brahe (VERONESI, 2026). Arquitetura de núcleos cartográficos elaborada por Gabriel Pinheiro.}
}
```

---

## 🎓 Agradecimentos e Créditos Institucionais

**Todos os direitos reservados à Plataforma Tycho Brahe © 2026**

- **Plataforma Tycho Brahe**: Criada e desenvolvida principalmente por **Luiz Henrique Lima Veronesi** como fruto de sua pesquisa de doutorado em Linguística na UNICAMP, sob orientação da **Profª Drª Charlotte Galves**, professora do IEL/UNICAMP.
  Portal Oficial: [https://www.tycho.iel.unicamp.br/](https://www.tycho.iel.unicamp.br/)

- **DACILAT** — Corpora Anotados Digitais de Línguas Indígenas Brasileiras com Traduções Automáticas:
  Projeto científico de documentação digital para a preservação e análise de línguas nativas do Brasil, associado à Plataforma Tycho Brahe; os corpora construídos pelo grupo ajudam a alimentar a Plataforma.
  Portal: [https://www.tycho.iel.unicamp.br/dacilat](https://www.tycho.iel.unicamp.br/dacilat)

- **Corpus Tycho Brahe**: *Tycho Brahe Parsed Corpus of Historical Portuguese*  
  Universidade Estadual de Campinas (UNICAMP) / Instituto de Estudos da Linguagem (IEL) / FAPESP

### Participantes do DACILAT

| Nome | Papel |
|---|---|
| Maria Filomena Sandalo | Coordenadora |
| Charlotte Galves | Pesquisadora Principal |
| Pablo Feliciano de Faria | Colaborador |
| Luiz Henrique Lima Veronesi | Criador e Desenvolvedor Principal da Plataforma; Colaborador DACILAT |
| Leonel de Alencar Araripe | Colaborador |
| Michael Becker | Colaborador |
| Vanda Pires | Colaborador |
| André Luiz Rosa Teixeira | Colaborador |
| Juliana Lopes Gurgel | Colaborador |
| Ticiana Andrade de Sena | Colaborador |
| Osmar Francisco | Colaborador |
| Hilário Silva | Colaborador |
| Sandra Silva | Colaborador |

### Ferramenta complementar de busca

O **Tycho Brahe Search** (este motor de busca desktop) foi elaborado por **Gabriel Pinheiro** como ferramenta complementar à Plataforma Tycho Brahe, a partir de sua proposta de implementação dos núcleos cartográficos com uma arquitetura própria.
