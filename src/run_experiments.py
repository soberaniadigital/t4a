import sys
import logging
import time
import argparse
from pathlib import Path

# Imports do Rich para UI
from rich.console import Console
from rich.table import Table
from rich import box

# Setup de Path
ROOT_DIR = Path( __file__ ).resolve().parent.parent
sys.path.append( str( ROOT_DIR ) )

# Imports Aplicação
from src.application.builders.experiment_builder import ExperimentBuilder
from src.application.runners.parallel_runner import ParallelRunner

# Log
logging.basicConfig(
    level = logging.INFO,
    format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename = 'experimento_sequencial.log',
    filemode = 'w'
)

console = Console()

# --- CONSTANTE DE CONFIGURAÇÃO ---
MAX_CONTEXT_LEVEL = 4  # Isso irá gerar os níveis: 0, 1, 2 e 3 (range é exclusivo no final)


def setup_arguments():
    parser = argparse.ArgumentParser( description = "Executor de Experimentos de Tradução (TCC)" )
    parser.add_argument(
        '--origem', type = str, required = True, choices = [ 'aurora', 'macbook', 'extracted' ],
        help = "Nome da pasta de origem dentro de data/ (ex: aurora, macbook)"
    )
    parser.add_argument(
        '--workers', type = int, default = 1,
        help = "Número de threads simultâneas (Padrão: 1 para execução sequencial)"
    )
    return parser.parse_args()


def exibir_estimativa_execucao( builder: ExperimentBuilder, projetos: list ) -> int:
    """
    Calcula e exibe uma tabela com o total de jobs que serão criados.
    Retorna o total geral de jobs.
    """
    total_geral = 0

    table = Table( title = f"📊 Planejamento de Execução (Até Nível {MAX_CONTEXT_LEVEL - 1})", box = box.ROUNDED )
    table.add_column( "Projeto", style = "cyan", no_wrap = True )
    table.add_column( "Ctx Disp.", justify = "center", style = "magenta" )

    # Cria colunas dinamicamente baseado no MAX_CONTEXT_LEVEL
    for i in range( MAX_CONTEXT_LEVEL ):
        table.add_column( f"Lvl {i}", justify = "right" )

    table.add_column( "Total", justify = "right", style = "green bold" )

    console.print( "\n[bold yellow]🔄 Calculando combinações possíveis... Aguarde...[/]" )

    for projeto in projetos:
        # Pega info básica
        _, mapa_ctx = builder._identificar_arquivos( projeto )
        qtd_ctx = len( mapa_ctx )

        row_counts = [ ]
        total_projeto = 0

        # Calcula jobs apenas até o nível definido (0, 1, 2, 3)
        for nivel in range( MAX_CONTEXT_LEVEL ):
            jobs = builder.construir_jobs_para_nivel( projeto, nivel )
            qtd = len( jobs )
            row_counts.append( str( qtd ) if qtd > 0 else "-" )
            total_projeto += qtd

        total_geral += total_projeto

        # Monta a linha da tabela
        row_data = [ projeto.name, str( qtd_ctx ) ] + row_counts + [ str( total_projeto ) ]
        table.add_row( *row_data )

    console.print( table )
    console.print( f"\n[bold white on blue] 🚀 TOTAL GERAL DE EXECUÇÕES: {total_geral} [/]\n" )

    return total_geral


def main():
    args = setup_arguments()

    input_dir = ROOT_DIR / "data" / args.origem
    output_dir = ROOT_DIR / "resultados" / f"experimentos_{args.origem}"

    if not input_dir.exists():
        console.print( f"[bold red]❌ Erro: Diretório não encontrado: {input_dir}[/]" )
        return

    # Instancia Builder e Runner
    builder = ExperimentBuilder( input_dir, output_dir )
    runner = ParallelRunner( max_workers = args.workers )
    projetos = builder.listar_projetos()

    if not projetos:
        console.print( "[yellow]⚠️ Nenhum projeto encontrado.[/]" )
        return

    # --- EXIBIR ESTIMATIVA ---
    total_jobs = exibir_estimativa_execucao( builder, projetos )

    if total_jobs == 0:
        console.print( "[red]Nenhum job gerado. Verifique os arquivos de entrada.[/]" )
        return

    console.print( "Iniciando processamento em 3 segundos... (Ctrl+C para cancelar)" )
    time.sleep( 3 )

    # --- LOOP DE EXECUÇÃO ---
    print( "=" * 60 )
    print( "▶️  INICIANDO EXECUÇÃO" )
    print( "=" * 60 )

    for i, projeto in enumerate( projetos, 1 ):
        console.print( f"\n[bold cyan]🔷 PROJETO [{i}/{len( projetos )}]: {projeto.name.upper()}[/]" )
        print( "-" * 60 )

        # Loop controlado pela constante (0, 1, 2, 3)
        for nivel in range( MAX_CONTEXT_LEVEL ):
            jobs_batch = builder.construir_jobs_para_nivel( projeto, nivel )

            if not jobs_batch:
                continue

            print( f"\n   📍 Nível {nivel}: Processando {len( jobs_batch )} jobs..." )

            runner.processar_batch( jobs_batch )

            time.sleep( 0.5 )

    console.print( "\n[bold green]🏁 TODOS OS EXPERIMENTOS CONCLUÍDOS.[/]" )


if __name__ == "__main__":
    main()
