# Ferramenta de Pesquisa no Corpus Tycho Brahe

Ferramenta desenvolvida em Python para indexação e pesquisa rápida no **Corpus Tycho Brahe**, com base no guia prático *"Python para Linguística de Corpus"*.

O software converte os arquivos de anotação sintática (`*_psd.txt`) para um banco de dados relacional **SQLite** otimizado, permitindo executar pesquisas estatísticas e computacionais em fração de segundo.

## 🚀 Funcionalidades

A ferramenta permite realizar buscas por diversos parâmetros da Linguística de Corpus:

1. **Frequência de Palavras e Etiquetas**: Listagem das formas e etiquetas morfossintáticas mais frequentes.
2. **Concordâncias (KWIC - Keyword In Context)**: Exibição da palavra-chave centralizada em seu contexto com horizonte configurável.
3. **Colocados (Coocorrência)**: Busca de colocados no horizonte da palavra-chave com cálculo de **Informação Mútua (MI)**.
4. **N-gramas**: Geração e contagem de n-gramas (bigramas, trigramas, etc.).
5. **Palavras-Chave (Keyness)**: Cálculo de chavicidade usando **Log-Likelihood** em comparação a um corpus de referência em português.
6. **Gráficos de Dispersão**: Visualização gráfica do posicionamento da palavra ao longo dos textos do corpus.
7. **Exportação de Resultados**: Suporte a exportação direta das buscas para planilhas Excel (`.xlsx`).

---

## 🛠️ Instalação e Requisitos

### Pré-requisitos
* Python 3.8+
* Módulos adicionais: `pandas`, `openpyxl`, `matplotlib` (opcional para gráficos)

Instale os requisitos rodando:
```bash
pip install pandas openpyxl matplotlib
```

---

## 📖 Como Usar

### 1. Construir o Banco de Dados
Para extrair os dados dos arquivos `*_psd.txt` e popular o banco indexado `corpus.db`:

```bash
python build_db.py
```

### 2. Executar Buscas

O script `pesquisa_corpus.py` fornece uma interface de linha de comando (CLI) intuitiva.

#### 🔹 Frequência de Palavras
```bash
python pesquisa_corpus.py --acao freq_palavras --limite 20
```

#### 🔹 Frequência de Etiquetas Morfossintáticas
```bash
python pesquisa_corpus.py --acao freq_etiquetas --limite 20
```

#### 🔹 Concordância (KWIC)
```bash
python pesquisa_corpus.py --acao kwic --palavra Senhor --horizonte 5 --limite 10
```

#### 🔹 Colocados
```bash
python pesquisa_corpus.py --acao colocados --palavra rei --horizonte 3 --limite 10
```

#### 🔹 N-gramas
```bash
python pesquisa_corpus.py --acao ngramas --n 3 --limite 10
```

#### 🔹 Palavras-Chave (Log-Likelihood)
```bash
python pesquisa_corpus.py --acao palavras_chave --limite 15
```

#### 🔹 Gráfico de Dispersão
```bash
python pesquisa_corpus.py --acao dispersao --palavra Senhor
```

#### 🔹 Exportar Resultados para Excel
Adicione o argumento `--exportar` a qualquer comando:
```bash
python pesquisa_corpus.py --acao kwic --palavra rei --exportar resultado_kwic.xlsx
```

---

## 📂 Estrutura do Repositório

* `build_db.py` - Script de parsing dos arquivos `.txt` do Tycho Brahe e criação do BD SQLite.
* `pesquisa_corpus.py` - CLI principal de consultas e geração de relatórios/gráficos.
* `*_psd.txt` - Arquivos de texto anotados do Corpus Tycho Brahe.
* `README.md` - Documentação do projeto.
