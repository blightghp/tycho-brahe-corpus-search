# Plano Arquitetural - Fase 4: Interface de Usuário (UI/UX) e Distribuição Desktop

> [!NOTE]
> Documento histórico de planejamento. Não descreve o estado executável atual;
> para a sequência vigente e os artefatos permitidos, consulte
> [STATUS_DE_ARTEFATOS.md](STATUS_DE_ARTEFATOS.md).

## 1. Visão Geral
Este documento detalha o planejamento para a criação de uma interface gráfica (GUI) baseada em tecnologias web (TypeScript, React/Vue) empacotada como um aplicativo Desktop autônomo (via Tauri ou Electron). O objetivo é democratizar o acesso às ferramentas de pesquisa sintática gerativa e cartográfica do Corpus Tycho Brahe, eliminando a necessidade de os pesquisadores utilizarem linha de comando ou instalarem Python manualmente.

## 2. Objetivos Principais
- **Instalação Simplificada**: Um único executável (`.exe` ou instalador `.msi`) que configura o ambiente sem intervenção técnica.
- **Backend Embutido**: Empacotar o motor Python (`pesquisa_sintatica.py`, `oracle.py`, etc.) de forma transparente.
- **Gerenciamento de Dados Inteligente**: O aplicativo deve baixar o repositório/banco de dados inicial compactado e prepará-lo em diretórios de AppData.
- **UX Especializada**: Interfaces ricas para visualização de árvores sintáticas (em cascata), busca com preenchimento automático para categorias cartográficas, e uma tela para auditoria *Human-in-the-Loop*.

## 3. Stack Tecnológico Sugerido

### 3.1. Frontend (Interface)
- **Linguagem**: TypeScript (Fortemente tipado, robusto e escalável).
- **Framework de UI**: React.js ou Vue.js (a definir).
- **Estilização**: Tailwind CSS para design ágil e limpo.
- **Visualização de Árvores**: Bibliotecas como `react-d3-tree` ou criação de componentes SVG personalizados para renderizar as estruturas sintáticas de forma similar à sintaxe gerativa tradicional.

### 3.2. Core Desktop (Empacotador)
- **Framework**: **Tauri** (Recomendado).
  - *Motivo*: Usa Rust por baixo dos panos, o que resulta em binários pequenos (geralmente < 10MB para o core), menor consumo de RAM do que o Electron, e permite invocar processos externos (nosso Python) de forma segura.
- **Alternativa**: **Electron**.
  - *Motivo*: Padrão da indústria, porém gera arquivos muito grandes (100MB+ só para um app vazio).

### 3.3. Empacotamento do Python (Backend)
- **Ferramenta**: PyInstaller.
- O código Python da Fase 3 será compilado em um binário executável (`backend.exe` ou múltiplos executáveis utilitários) que receberá comandos via *Standard Input/Output* (JSON via stdout) ou servidor HTTP REST local embutido (ex: FastAPI ou Flask local).

## 4. Arquitetura do Sistema e Comunicação (IPC)

A comunicação entre a UI (TypeScript) e o Motor (Python) seguirá o seguinte fluxo:

1. O usuário digita uma busca, por exemplo: `[ForceP [TopP]]`.
2. A UI (TypeScript) envia um comando (via IPC do Tauri ou requisição HTTP local) para o executável Python empacotado.
3. O Python (usando `pesquisa_sintatica.py` modificado para output JSON) consulta o `corpus_fase3.db` e retorna as estruturas de árvore, contextos das frases, metadados, e links.
4. A UI recebe o JSON e renderiza os resultados dinamicamente, permitindo expandir/colapsar os nós da árvore na tela.

## 5. Módulos da Interface (UX)

### 5.1. Dashboard Principal (Busca)
- **Barra de Pesquisa Avançada**: Suporte a expressões regulares e atalhos para categorias como `TopP`, `FocP`, `FinP`, `IP`.
- **Filtros Laterais**: Filtros por autor, ano, texto, e se a frase sofreu "expansão cartográfica" ou é nativa da Fase 1.
- **Tabela de Resultados**: Lista paginada mostrando o trecho exato onde ocorreu o "hit", com destaques (highlights).

### 5.2. Visualizador de Árvore (Tree Viewer)
- Ao clicar em um resultado na tabela, abre-se um painel (modal ou divisão de tela) renderizando a árvore sintática completa ou simplificada.
- Ferramentas de zoom, pan (arrastar) e exportação em PNG/PDF da árvore.

### 5.3. Módulo de Revisão Manual (Human-in-the-Loop)
- Uma aba separada substituindo o `revisor_cli.py`.
- Mostra árvores em quarentena (do `tb_quarentena`).
- Interface gráfica com botões "Aprovar Expansão", "Rejeitar (Manter Original)", "Editar Estrutura", permitindo ao pesquisador salvar a alteração direto no SQLite.

### 5.4. Setup/Loading
- Tela que aparece apenas na primeira vez que o programa é aberto, ou ao pedir "Atualizar Corpus".
- Barra de progresso para: `Baixando corpus... -> Descompactando... -> Inicializando banco de dados`.

## 6. Plano de Implementação (Passo a Passo)

### Etapa 1: Prototipação e Setup do Repositório
- Criar a estrutura do projeto Tauri com React/TypeScript (`npm create tauri-app@latest`).
- Desenvolver wireframes (esboços visuais) básicos das telas principais.

### Etapa 2: Ponte de Comunicação (Bridge)
- Adaptar `pesquisa_sintatica.py` para receber argumentos CLI que retornem JSON estruturado ao invés de imprimir texto humano no console.
- Testar a chamada do Python a partir do Tauri e ler a resposta.

### Etapa 3: Desenvolvimento da UI
- Implementar as telas (Busca, Visualizador, Revisão).
- Integrar a comunicação com o backend em tempo real.

### Etapa 4: Gerenciamento do Download do Corpus
- Codificar a lógica (em Rust/Tauri) para baixar um arquivo ZIP (ex: `corpus_fase3.zip` de um GitHub Release ou servidor FTP do projeto) e extraí-lo para uma pasta local segura (`%AppData%\TychoBrahe_App`).

### Etapa 5: Empacotamento e Distribuição (Build)
- Configurar o script de build final.
- Usar PyInstaller para criar o binário do Python.
- Configurar o Tauri para incluir esse binário Python como um *sidecar*.
- Gerar o instalador final `.msi` e o `.exe` standalone.

## 7. Próximos Passos Imediatos
1. Obter aprovação deste plano.
2. Definir se o framework desktop será **Tauri** (recomendado) ou **Electron**.
3. Definir se a distribuição dos dados iniciais será um download na primeira execução ou empacotado no tamanho do instalador.
4. Inicializar a base de código do frontend (`src/`).
