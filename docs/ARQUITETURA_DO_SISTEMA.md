# Arquitetura do Sistema - Tycho Brahe Search

O **Tycho Brahe Search** foi arquitetado como uma aplicação tripartida de alta performance e desacoplamento modular, combinando o ecossistema nativo do **Rust (Tauri v2)**, o poder analítico de **Python (NLP, spaCy, NLTK, SQLite)** e uma interface moderna em **React 19 + TypeScript + Tailwind CSS + D3.js**.

> [!WARNING]
> Este diagrama descreve a arquitetura pretendida e parte da implementação
> existente; não certifica que todos os fluxos estejam operacionais. No Marco
> 2, as fontes PSD são canônicas e a importação de origem é rastreável. No
> Marco 3, há uma camada derivada de evidências gramaticais versionadas; os
> bancos/pacotes legados continuam congelados como derivados experimentais.
> A transdução cartográfica completa, a busca desktop e a distribuição ainda
> dependem dos próximos marcos. Consulte
> [STATUS_DE_ARTEFATOS.md](STATUS_DE_ARTEFATOS.md) para o estado verificável.

---

## 1. Diagrama-alvo de camadas

```mermaid
graph TD
    subgraph DataFoundation [Camada 0: Fundamento de Proveniência Marco 2]
        PSD[PSD canônico: corpus_data/*_psd.txt]
        Manifest[Manifesto físico Marco 2]
        Importer[importador_rastreavel.py]
        Recon[(SQLite recon_* de fatos de origem)]
    end

    subgraph EvidenceLayer [Camada 0.5: Análise Evidencial Marco 3]
        Rules[regras_gramatica_expandida_v1.json]
        Analyzer[analise_gramatical_recon.py]
        M3[(SQLite m3_* versionado)]
    end

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
        DB[(Futuro índice analítico; bancos legados congelados)]
    end

    PSD --> Importer
    Manifest --> Importer
    Importer --> Recon
    Recon --> Analyzer
    Rules --> Analyzer
    Analyzer --> M3
    UI --> API
    HitL --> API
    API -- Invocação Tauri IPC --> Handler
    Handler -- Validação AppSec --> Sandbox
    Sandbox -- Execução Segura Sidecar --> Sidecar
    Sidecar --> Oracle
    Oracle --> Rewriter
    Rewriter --> Tokenizer
    Tokenizer --> DB
    M3 -. entrada auditada da busca futura .-> Sidecar
    Sidecar -- Resposta JSON UTF-8 --> Handler
    Handler -- Retorno Assíncrono --> API
    API --> UI
```

---

## 0. Fundamento de proveniência — Marco 2

Antes de qualquer expansão cartográfica, o importador isolado produz um banco
`recon_*` com todos os grupos físicos PSD, um ledger de decisão para cada
candidato histórico e a topologia fonte em adjacência/nested set. A ligação
com o manifesto externo impede que hashes internos do banco sejam tomados como
prova suficiente: documento, BLOB e fingerprint físico são reconferidos contra
o retrato Marco 2.

Essa camada não chama NLTK, spaCy, `rewriter.py` ou bancos legados. A futura
análise de núcleos lexicais e funcionais é construída no Marco 3 como uma
camada versionada ligada a `sentenca_id`/`no_id` de `recon_*`, sem reescrever
os fatos de origem. Ela materializa âncoras, decisões e evidências, mas não
injeta projeções invisíveis. Veja [IMPORTACAO_RASTREAVEL.md](IMPORTACAO_RASTREAVEL.md)
e [ANALISE_GRAMATICAL_EXPANDIDA.md](ANALISE_GRAMATICAL_EXPANDIDA.md).

---

## 0.5. Análise gramatical evidencial — Marco 3

`analise_gramatical_recon.py` abre o Marco 2 em modo somente leitura, valida
sua âncora externa e produz outro SQLite por staging atômico. O banco `m3_*`
espelha cada nó fonte e registra, para cada classificação, a regra, a evidência,
a confiança heurística e o estado de revisão. Ele mantém `CP`, `IP`, `NP`,
`PP` e demais sintagmas como estruturas que já existem na fonte; referências a
Cinque/Rizzi só aparecem como evidência lexical verificável, sem mutação de
árvore. O contrato completo está em
[ANALISE_GRAMATICAL_EXPANDIDA.md](ANALISE_GRAMATICAL_EXPANDIDA.md).

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
  - `analise_gramatical_recon.py`: Compilador Marco 3 de evidências e âncoras versionadas sobre `recon_*`, sem NLTK/spaCy e sem transformação do PSD.
  - `oracle.py`: Classificador de traços cartográficos e diagnósticos estruturais.
  - `rewriter.py`: Transdutor recursivo que expande nós sintéticos (CP, IP, VP) na hierarquia dos 5 domínios.
  - `tokenizador_cartografico.py`: Extração de lema, classe morfológica (POS) e mapeamento de papéis gerativos universais.
  - `pesquisa_sintatica.py`: Roteador CLI de alta velocidade que consulta as bases SQLite indexadas com o *Nested Set Model* (lft/rgt).
