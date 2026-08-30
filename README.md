# Ferramenta de Pesquisa no Corpus Tycho Brahe

Ferramenta desenvolvida em Python para indexação, pesquisa rápida e transformação gerativa do **Corpus Tycho Brahe**, com base no guia prático *"Python para Linguística de Corpus"* e nos princípios da **Gramática Gerativa e Cartografia Sintática** (Planos Arquiteturais Fase 1, 2 e 3).

---

## 📐 Arquitetura em Fases

| Fase | Status | Descrição |
|------|:------:|-----------|
| **Fase 0** | ✅ Concluída | Pesquisa clássica por frequência, KWIC, colocados (MI) e n-gramas (SQLite + folhas) |
| **Fase 1** | ✅ Concluída | Pesquisa sintática gerativa: dominância direta/indireta, irmandade, lematização (SQLite + Nested Sets + spaCy) |
| **Fase 2 & 3** | ✅ Concluída | [Transdutor Cartográfico](docs/plano_projeto_implementacao.md) em Modelo Leque (Split-CP de Rizzi e Split-IP de Cinque) com Protocolo de 5 Motores e Auditoria Humana (*Human-in-the-Loop*) |

---

## 🚀 Funcionalidades

### Fase 0 – Pesquisa Básica (`pesquisa_corpus.py`)
1. **Frequência de Palavras e Etiquetas**
2. **Concordâncias (KWIC)** – Keyword In Context
3. **Colocados** com Informação Mútua (MI)
4. **N-gramas**
5. **Palavras-Chave (Keyness)** – Log-Likelihood vs corpus de referência
6. **Gráfico de Dispersão**
7. **Exportação para Excel**

### Fase 1 – Pesquisa Sintática Gerativa (`pesquisa_sintatica.py`)
1. **Frequência de Labels** – todos os rótulos sintáticos do corpus
2. **Busca por Atributo** – label, categoria base, função sintática, token ou lema
3. **Dominância Direta** (`A < B`) – pai imediato -> filho imediato
4. **Dominância Indireta** (`A << B`) – ancestral -> qualquer descendente, com Nested Sets em O(log n)
5. **Co-irmandade** (`A $ B`) – dois nós com o mesmo pai
6. **KWIC Sintático** – concordâncias centradas no sintagma alvo
7. **Exportação para Excel**

### Fases 2 e 3 – Transdutor Cartográfico & Auditoria (`processar_corpus.py`, `revisor_cli.py`)
1. **Modelo Leque (Fan Expansion)** – Preservação não-destrutiva das categorias originais (`CP-...`, `IP-...`) com abertura interna das projeções funcionais.
2. **Split-CP (Rizzi 1997, 2004)** – Identificação e projeção de `ForceP`, `TopP` (Tópico), `FocP` (Foco com Wh/traços `*T*`) e `FinP` (Finitude).
3. **Split-IP (Cinque 1999, 2002)** – Ancoragem adverbial de alta granularidade (25 projeções funcionais estritas, como `MoodP_evaluative`, `ModP_epistemic`, `AspP_celerative`, `T_anterior`, etc.).
4. **Validador de Hierarquia Restritiva** – Bloqueia mutações cegas em ordens anômalas/históricas, enviando para quarentena.
5. **Console Human-in-the-Loop (`revisor_cli.py`)** – Interface interativa para decisão de variantes históricas e correções pelo linguista.
6. **Exportador de Arquivos PSD (`exportar_corpus_expandido.py`)** – Geração de novos arquivos físicos `.psd` com parênteses balanceados.

---

## 🛠️ Instalação e Requisitos

### Pré-requisitos
* Python 3.9+

```bash
pip install -r requirements.txt
python -m spacy download pt_core_news_sm
```

---

## 📖 Como Usar

### 1. Fases 2 e 3 – Transdução Cartográfica do Corpus (Modelo Leque)

#### 🔹 Executar o Pipeline de Transdução em Lote
```bash
# Processar todos os arquivos do corpus e gerar banco de cartografia
python processar_corpus.py

# Ou testar em lote menor (ex: 2 arquivos)
python processar_corpus.py --limite 2
```

#### 🔹 Painel de Auditoria e Revisão Humana (Human-in-the-Loop)
```bash
# Ver status e estatísticas das projeções funcionais injetadas
python revisor_cli.py --status

# Listar sentenças que violaram hierarquias e estão em quarentena
python revisor_cli.py --listar --limite 10

# Iniciar sessão interativa para aprovar variantes ou corrigir manualmente
python revisor_cli.py --revisar
```

#### 🔹 Exportar Árvores Expandidas para Arquivos PSD
```bash
python exportar_corpus_expandido.py --output-dir corpus_cartografico_psd
```

---

### 2. Fase 1 – Pesquisa Sintática Gerativa

```bash
# 1. Construir banco sintático da Fase 1 (se necessário refazer)
python build_db_fase1.py

# 2. Frequência de Labels Sintáticos
python pesquisa_sintatica.py --acao freq_labels --limite 30

# 3. Busca por Atributo (label, base, função, token ou lema)
python pesquisa_sintatica.py --acao busca --label NP-SBJ
python pesquisa_sintatica.py --acao busca --base NP
python pesquisa_sintatica.py --acao busca --lemma oferecer

# 4. Dominância Direta A < B
python pesquisa_sintatica.py --acao domina_direta --pai IP-MAT --filho NP-SBJ

# 5. Dominância Indireta A << B
python pesquisa_sintatica.py --acao domina_indireta --domina IP-MAT --contido N --lemma rei
python pesquisa_sintatica.py --acao domina_indireta --domina CP-REL --contido NP-SBJ --token "*pro*"

# 6. Co-irmandade A $ B
python pesquisa_sintatica.py --acao irmandade --irmao NP-SBJ --com VP

# 7. KWIC Sintático (centrado no sintagma)
python pesquisa_sintatica.py --acao kwic --label NP-SBJ --horizonte 4 --limite 15
```

---

### 3. Fase 0 – Buscas Clássicas

```bash
python build_db.py  # Se necessário construir o banco de unigramas
python pesquisa_corpus.py --acao freq_palavras --limite 20
python pesquisa_corpus.py --acao kwic --palavra rei --horizonte 5
python pesquisa_corpus.py --acao colocados --palavra rei --horizonte 3
python pesquisa_corpus.py --acao ngramas --n 3 --limite 10
python pesquisa_corpus.py --acao palavras_chave --limite 15
python pesquisa_corpus.py --acao dispersao --palavra Senhor
```

---

## 📂 Estrutura do Repositório

| Arquivo/Diretório | Descrição |
|-------------------|-----------|
| `docs/` | Documentação técnica e planos arquiteturais (Fases 2 e 3) |
| `tree_io.py` | Motores 1 e 5 – Leitura, deserialização e serialização de árvores PSD |
| `oracle.py` | Motor 2 – Classificador léxico e topológico de Rizzi e Cinque |
| `rewriter.py` | Motor 3 – Transdutor algorítmico em Modelo Leque e validador de ordem |
| `db_cartografia.py` | Camada de persistência para árvores expandidas e quarentena |
| `revisor_cli.py` | Motor 4 – Console interativo Human-in-the-Loop para auditoria |
| `processar_corpus.py` | Pipeline de execução em lote da transdução cartográfica |
| `exportar_corpus_expandido.py` | Exportador para arquivos físicos PSD expandidos |
| `test_tree_io.py` | Testes unitários de integridade de E/S de árvores |
| `test_cartografia.py` | Testes unitários do oráculo e transdutor cartográfico |
| `build_db_fase1.py` | Builder Fase 1 – Árvore completa + lemas (Nested Sets) |
| `pesquisa_sintatica.py` | CLI Fase 1 – Consultas sintáticas gerativas |
| `build_db.py` | Builder Fase 0 – Extração de unigramas |
| `pesquisa_corpus.py` | CLI Fase 0 – Buscas quantitativas clássicas |
| `requirements.txt` | Dependências Python do projeto |
| `*_psd.txt` | Arquivos de anotação sintática originais do Tycho Brahe |
