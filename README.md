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

## Avaliar

- Rodar comando: `python3 src/run_metrics.py resultados/context_levels_sample`