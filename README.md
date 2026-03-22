# Como rodar

### Baixar arquivos

1. Rodar: `python3.11 web_scraper/run.py`
2. Irá criar uma pasta *downloads* dentro de *data*.
3. Rodar: `python3.11 web_scraper/align_data.py`

O primeiro comando irá baixar todos os arquivos necessários.
Já o segundo comando irá dividir os arquivos em:

- 30% deles na pasta *macbook*.
- 70% deles na pasta *aurora*.

Como tenho acesso a um computador (notebook) com uma RTX 5050, optei por usá-lo no processo de tradução.

### Instruções

1. Criar ambiente: `python3 -m venv .venv` ou `/opt/homebrew/bin/python3.11 -m venv .venv`
2. Ativar env: `source .venv/bin/activate`
3. Atualizar pip: `pip install --upgrade pip setuptools wheel`
4. Instalar dependências para traduzir: `pip install -e .`
5. Instalar dependências para avaliar: `pip install -e ".[eval]"`

### Rodar Projeto

1. Macbook:

```
python src/run_experiments.py --origem macbook
```

**Para MacBook**: Uso do `caffeinate -i` para impedir o bloqueio de tela.

```
caffeinate -i python src/run_experiments.py --origem macbook
```

2. Aurora:

```
python src/run_experiments.py --origem aurora
```

# Conectar no Aurora

- Ativar o Tailscale no Aurora.
- Rodar o comando `ssh -p 2222 vinicius@100.122.34.23` para conectar.
- Ativar env: `cd TCC/` ->  `source .venv/bin/activate`.

# Alternar computadores

- Para usar o Aurora: selecionar o servidor criado e usar o terminal apropriado.
- Para usar o MacBook: usar o terminal apropriado.

Ao rodar o projeto, precisa *puxar* os arquivos criados. Para isso, clica com o botão direito do mouse em resultados e
aperta em Deployment, por fim, clica em Download.

Não fechar WSL.

# Rodar tradução `run`

Constrói automaticamente todas as combinações de contexto a partir dos arquivos .po disponíveis em cada projeto, com
suporte a 7 idiomas de contexto e sistema de checkpoint.

## Idiomas Suportados

| Código | Idioma     | Família        |
|--------|------------|----------------|
| es     | Espanhol   | Românica       |
| fr     | Francês    | Românica       |
| de     | Alemão     | Germânica      |
| ru     | Russo      | Eslava         |
| zh_CN  | Chinês     | Sino-Tibetana  |
| vi     | Vietnamita | Austroasiática |
| id     | Indonésio  | Austronésia    |

O idioma alvo é sempre pt_BR.

- Rodar comando: `python src/run_context_levels_filtered.py --origem <fonte>`

## Níveis de Contexto Gerados

| Nível | Descrição      | Exemplo de arquivo gerado         |
|-------|----------------|-----------------------------------|
| ctx-0 | Sem contexto   | aspell.pt_BR.llama.ctx-0.po       |
| ctx-1 | 1 idioma       | aspell.pt_BR.llama.ctx-1.de.po    |
| ctx-2 | Par de idiomas | aspell.pt_BR.llama.ctx-2.de-es.po |

Para 7 idiomas disponíveis, o nível 2 gera 21 combinações por projeto (C(7,2) = 21).

# Avaliar `run_metrics`

Lê arquivos .json de tradução, calcula cinco métricas de qualidade (COMET, chrF++, BLEU, TER, BERTScore) para cada
segmento, salva um CSV por arquivo e exibe um resumo no terminal.

- Rodar comando: `python3 src/run_metrics.py resultados/context_levels_sample`

# Agregador `aggregate_metrics`

- Rodar o comando: `python3 src/aggregate_metrics.py --input metrics_csv --output metrics_aggregated`
- Vai produzir um arquivo para cada projeto contendo as métricas para cada experimento.

# Gerador `generate_analysis`

Lê um CSV agregado (gerado pelo aggregate_metrics.py) e produz um arquivo .md com tabelas de análise por métrica,
comparando os níveis de contexto (ctx-0, ctx-1, ctx-2, etc.).

- Rodar o comando `python3 src/generate_analysis.py caminho/para/csv` para cada projeto.
- O arquivo .md será salvo na pasta atual com o nome do projeto automaticamente.

## O que é gerado no .md

Para cada métrica detectada no CSV, uma tabela no formato:

### COMET (maior = melhor) - aspell_v0.60.8.1

| Nível | Média | Δ vs ctx-0 | Δ vs ctx-1 | Melhor contexto |
|-------|-------|------------|------------|-----------------|
| ctx-0 | 75.93 | 0.00       | nan        | ...             |
| ctx-1 | 78.19 | +2.26      | +2.26      | ES (80.00)      |
| ctx-2 | 79.03 | +3.10      | +0.84      | ES,RU (80.56)   |

# Análise estatística (modelo misto linear)

Análise usando modelo de efeitos mistos lineares (lmer) com design nested within-subjects e blocking.
Responde três perguntas:

- **Q1**: Os tipos de tratamento diferem (direto vs single-pivot vs dual-pivot)?
- **Q2**: Os idiomas pivot diferem dentro do tratamento single-pivot?
- **Q3**: Os pares de idiomas diferem dentro do tratamento dual-pivot?

## Instalar R (Debian)

```bash
sudo apt update
sudo apt install -y r-base r-base-dev
```

## Setup (Python + R)

```bash
make setup
```

Isso cria o venv Python (`.venv/`) e instala os pacotes R via renv (`renv/library/`).

## Gerar dados e rodar análise

```bash
# Gerar experiment_data.csv a partir dos CSVs em metrics_csv/
make experiment-data

# Rodar análise completa (gera experiment_data.csv + roda o script R)
make analysis
```

Ou rodar manualmente:

```bash
python3 estatisticas/generate_experiment_csv.py
Rscript estatisticas/analysis.R
```

## Arquivos gerados em `estatisticas/`

### Dados

| Arquivo | Descrição |
|---------|-----------|
| `experiment_data.csv` | Dados transformados para o R (112K linhas) |

### Estatísticas descritivas

| Arquivo | Descrição |
|---------|-----------|
| `desc_by_treatment_type.csv` | Média, SD, mediana por tipo de tratamento |
| `desc_by_single_context.csv` | Média, SD, mediana por idioma de contexto (single) |
| `desc_by_dual_context.csv` | Média, SD, mediana por par de idiomas (dual) |
| `desc_by_source_project.csv` | Média, SD, mediana por projeto |

### Diagnósticos do modelo

| Arquivo | Descrição |
|---------|-----------|
| `diagnostics_qqplot.png` | QQ plot dos resíduos |
| `diagnostics_residuals_vs_fitted.png` | Resíduos vs valores ajustados |
| `diagnostics_residual_hist.png` | Histograma dos resíduos |
| `diagnostics_ranef_source.png` | QQ plot dos efeitos aleatórios (source project) |

### Gráficos

| Arquivo | Descrição |
|---------|-----------|
| `plot_q1_treatment_types.png` | Comparação dos tipos de tratamento (EMMs + CIs) |
| `plot_q2_single_context.png` | Ranking dos idiomas de contexto (single) |
| `plot_q3_dual_context_top10.png` | Top 10 pares de idiomas (dual) |
| `plot_dist_treatment_type.png` | Boxplot por tipo de tratamento |
| `plot_dist_single_context.png` | Boxplot por idioma de contexto (single) |
| `plot_dist_source_project.png` | Boxplot por projeto |
| `plot_hist_treatment_type.png` | Histograma facetado por tipo de tratamento |

### Resultados para o paper

| Arquivo | Descrição |
|---------|-----------|
| `results_q1_treatment_means.csv` | EMMs por tipo de tratamento |
| `results_q1_pairwise.csv` | Comparações pareadas entre tipos de tratamento |
| `results_q2_single_context_cld.csv` | Ranking single-context (compact letter display) |
| `results_q3_dual_context_cld.csv` | Ranking dual-context (compact letter display) |
| `results_q3_dunnett_vs_best.csv` | Comparações Dunnett contra o melhor par |
