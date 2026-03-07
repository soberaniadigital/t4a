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
