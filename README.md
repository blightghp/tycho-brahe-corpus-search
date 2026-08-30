# Tycho Brahe - Pesquisa Sintática Gerativa

Este repositório contém a infraestrutura e o aplicativo de pesquisa e análise sintática estrutural das árvores anotadas do projeto Tycho Brahe (http://www.tycho.iel.unicamp.br/). 

## Arquitetura do Repositório
Para facilitar o desenvolvimento descentralizado e a clareza do escopo de cada agente de software (React vs Rust vs Python), o projeto foi reestruturado nas seguintes áreas:

- `/python_backend`: Contém a inteligência de manipulação das árvores, o roteamento da lógica de tokenização com NLTK/spaCy, a conversão para SQLite e a orquestração da auditoria da cartografia. (Leia o `README.md` interno para passos de processamento).
- `/corpus_data`: Armazena os dados textuais puros (`*_psd.txt`) e os bancos de dados SQLite pré-computados (`.db`).
- `/tycho-desktop/src-tauri`: É o "Motor Rust" responsável por envelopar o backend em background, intermediar as permissões do SO e interagir com o front-end por via de IPC seguro. (Leia o `README.md` interno).
- `/tycho-desktop/src`: É o Frontend em React/TypeScript, contendo a Interface de Usuário estilizada, componentes gráficos em D3 e as telas de interação do pesquisador. (Leia o `README.md` interno).

---

## Plano Diretor de Manutenção e Implementação (Passo a Passo)

Abaixo está a orientação detalhada sobre como o fluxo deve ser operado e atualizado, dividindo o sistema do "Core" para a "Camada de Apresentação".

### 1. Camada de Dados e Tokenização Sintática (O mais demorado e procedural)
*Diretório: `/python_backend` e `/corpus_data`*
O que fazer/Implementar:
1. **Geração Inicial**: Se o banco de dados principal corromper ou for atualizado (com a Fase 3 e dados expandidos), você deve reconstruir o banco SQLite executando `python_backend/build_db_fase3.py`. Esse arquivo consumirá `corpus_data/*.txt`.
2. **Transformação Cartográfica (Oráculo)**: A árvore NLTK é importada, inspecionada nó a nó, e o `rewriter.py` insere as categorias expandidas (como TopP, MoodP). Se um nó anômalo for encontrado, ele será lançado na quarentena (`tb_quarentena` do SQLite `corpus_cartografia.db`).
3. **Compilação**: Para ligar o Python ao App, não rodamos servidores Flask (por segurança e estabilidade). Rodamos o script PowerShell `build_backend.ps1`, que empacota todo o NLP usando PyInstaller em um único `tycho_backend.exe`.

### 2. O Motor (Rust & Tauri Shell)
*Diretório: `/tycho-desktop/src-tauri`*
O que fazer/Implementar:
1. **Configuração de Recursos**: O arquivo `tauri.conf.json` governa como a aplicação mapeia os dados do usuário. Se adicionar novos arquivos ao `/corpus_data`, deve-se mapeá-los no array `bundle.resources` lá.
2. **Sidecar / Gates Seguros**: O Rust não roda código Python diretamente. Ele executa o `.exe` gerado pelo PyInstaller. Para isso, o `capabilities/default.json` bloqueia toda a execução local, exceto o binário assinado do backend. Qualquer nova ferramenta paralela deve ser mapeada na lista de capabilities do Tauri V2.
3. **Redução de Tamanho (LTO)**: O compilador Rust já foi ajustado com _Link-Time Optimization_. Apenas rode `npm run tauri build` se desejar um `.msi` novo; ele já sai ultra-comprimido.

### 3. A Interface e UX (Frontend React)
*Diretório: `/tycho-desktop/src`*
O que fazer/Implementar:
1. **Estilização & Créditos**: O frontend deve carregar os créditos formais ao projeto Tycho Brahe (IEL-Unicamp) explicitamente.
2. **Navegação Intuitiva**: A barra lateral altera o fluxo entre _Pesquisa em Árvores_ e a aba de _Human-in-the-Loop_ (Auditoria). Em caso de expansões, os componentes Tailwind devem enfatizar mensagens limpas e feedback responsivo.
3. **Comunicação Segura (IPC)**: A API do frontend (`services/api.ts`) é a única porta de entrada autorizada a despachar dados pela rede nativa usando `@tauri-apps/plugin-shell`. Se você criar um botão novo, conecte a lógica nessa ponte.

---
**Créditos e Metadados do Domínio**:
O processamento computacional foi gerado tendo como base arquitetural as árvores históricas geradas pelo *Tycho Brahe Parsed Corpus of Historical Portuguese*. Para referências teóricas, acesse o [site original do projeto](http://www.tycho.iel.unicamp.br/).
