# Ferramenta de Pesquisa no Corpus Tycho Brahe

Ferramenta desenvolvida em Python para indexação e pesquisa rápida no **Corpus Tycho Brahe**, com base no guia prático *"Python para Linguística de Corpus"* e nos princípios da **Gramática Gerativa** (Planos Arquiteturais Fase 1, 2 e 3).

---

## 📐 Arquitetura em Fases

| Fase | Descrição |
|------|-----------|
| **Fase 0** | Pesquisa básica por frequência, KWIC e n-gramas (SQLite + folhas) |
| **Fase 1** | Pesquisa por estrutura sintática gerativa: dominância, irmandade, lematização (SQLite + Nested Sets + spaCy) |
| **Fase 2** | *(Planejada)* Cartografia sintática – Split-CP (Rizzi 1997; 2004) e Split-IP (Cinque 1999; 2002) como nós virtuais |
| **Fase 3** | *(Planejada)* Transdutor algorítmico de árvores – transformação física do corpus para incorporar as categorias cartográficas expandidas em modelo "leque" |

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
3. **Dominância Direta** (`A < B`) – pai imediato → filho imediato
4. **Dominância Indireta** (`A << B`) – ancestral → qualquer descendente, com Nested Sets O(log n)
5. **Co-irmandade** (`A $ B`) – dois nós com o mesmo pai
6. **KWIC Sintático** – concordâncias centradas no sintagma (não na palavra)
7. **Exportação para Excel**

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

### Fase 0 – Build do Banco Básico (se necessário refazer)
```bash
python build_db.py
```

### Fase 1 – Build do Banco Sintático Gerativo
```bash
python build_db_fase1.py
```
> Isso vai lematizar todos os tokens únicos em batch e armazenar a estrutura completa das árvores sintáticas com coordenadas Nested Sets.

---

### Fase 0 – Buscas Básicas

```bash
python pesquisa_corpus.py --acao freq_palavras --limite 20
python pesquisa_corpus.py --acao kwic --palavra rei --horizonte 5
python pesquisa_corpus.py --acao colocados --palavra rei --horizonte 3
python pesquisa_corpus.py --acao ngramas --n 3 --limite 10
python pesquisa_corpus.py --acao palavras_chave --limite 15
python pesquisa_corpus.py --acao dispersao --palavra Senhor  # requer matplotlib
```

---

### Fase 1 – Buscas Sintáticas Gerativas

#### 🔹 Frequência de Labels Sintáticos
```bash
python pesquisa_sintatica.py --acao freq_labels --limite 30
```

#### 🔹 Busca por Atributo (label, base, função, token ou lema)
```bash
# Todos os NP-SBJ do corpus
python pesquisa_sintatica.py --acao busca --label NP-SBJ

# Todos os sintagmas da categoria base NP (NP-SBJ, NP-ACC, NP-VOC...)
python pesquisa_sintatica.py --acao busca --base NP

# Todos os nós com função sintática ACC (objeto direto)
python pesquisa_sintatica.py --acao busca --funcao ACC

# Busca por lema
python pesquisa_sintatica.py --acao busca --lemma oferecer
```

#### 🔹 Dominância Direta `A < B`
```bash
# IP-MAT que domina diretamente NP-SBJ
python pesquisa_sintatica.py --acao domina_direta --pai IP-MAT --filho NP-SBJ
```

#### 🔹 Dominância Indireta `A << B`
```bash
# IP-MAT que contém em qualquer profundidade um N com lema "rei"
python pesquisa_sintatica.py --acao domina_indireta --domina IP-MAT --contido N --lemma rei

# CP-REL que domina algum sujeito nulo
python pesquisa_sintatica.py --acao domina_indireta --domina CP-REL --contido NP-SBJ --token "*pro*"
```

#### 🔹 Co-irmandade `A $ B`
```bash
# NP-SBJ e VP que são irmãos na mesma sentença
python pesquisa_sintatica.py --acao irmandade --irmao NP-SBJ --com VP
```

#### 🔹 KWIC Sintático (centrado no sintagma)
```bash
# Concordâncias de NP-SBJ centradas no sintagma
python pesquisa_sintatica.py --acao kwic --label NP-SBJ --horizonte 4 --limite 15
```

#### 🔹 Exportar qualquer resultado para Excel
```bash
python pesquisa_sintatica.py --acao domina_indireta --domina IP-MAT --contido N --lemma rei --exportar resultado.xlsx
```

---

## 📂 Estrutura do Repositório

| Arquivo | Descrição |
|---------|-----------|
| `build_db.py` | Builder Fase 0 – extrai folhas, cria `corpus.db` |
| `pesquisa_corpus.py` | CLI Fase 0 – KWIC, frequência, colocados, n-gramas, keyness |
| `build_db_fase1.py` | Builder Fase 1 – árvore completa + lemas, cria `corpus_fase1.db` |
| `pesquisa_sintatica.py` | CLI Fase 1 – dominância, irmandade, KWIC sintático |
| `requirements.txt` | Dependências Python |
| `*_psd.txt` | Arquivos de texto anotados do Corpus Tycho Brahe |
