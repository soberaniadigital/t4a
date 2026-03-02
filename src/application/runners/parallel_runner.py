from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

# IMPORTS DO RICH
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeRemainingColumn,
    MofNCompleteColumn
)
from rich.console import Console

from src.application.dto.translation_job import TranslationJob
from src.application.pipelines.translation_pipeline import TranslationPipeline
from src.application.dto.pipeline_result import PipelineResult

from src.infrastructure.io.po_file_adapter import PoFileAdapter


class ParallelRunner:
    def __init__( self, max_workers: int = 4 ):
        self.max_workers = max_workers
        self._po_reader = PoFileAdapter()

    def processar_batch( self, jobs: List[ TranslationJob ] ) -> List[ PipelineResult ]:
        console = Console()
        console.print( f"\n[bold green]🚀  Iniciando Batch Paralelo com {len( jobs )} estratégias...[/]\n" )

        resultados = [ ]

        # Configuração das Colunas da Barra
        progress_columns = [
            SpinnerColumn(),
            TextColumn( "[bold blue]{task.description}" ),
            BarColumn( bar_width = None ),  # Ocupa o espaço disponível
            TextColumn( "[progress.percentage]{task.percentage:>3.0f}%" ),
            MofNCompleteColumn(),  # Mostra (15/150)
            TimeRemainingColumn(),  # ETA
        ]

        # O Context Manager do Rich gerencia a tela
        with Progress( *progress_columns, console = console ) as progress:

            futures_map = { }
            with ThreadPoolExecutor( max_workers = self.max_workers ) as executor:

                # 1. Configurar as Barras ANTES de rodar
                for job in jobs:
                    # Lemos o arquivo rapidinho só pra saber o tamanho total da barra
                    try:
                        dados = self._po_reader.carregar_arquivo( job.arquivo_entrada )
                        total_items = len( dados )
                    except:
                        total_items = 100

                    # Adiciona a tarefa visual
                    task_id = progress.add_task(
                        description = f"{job.nome_estrategia.ljust( 10 )}",
                        total = total_items
                    )

                    # Cria a função que será chamada lá no fundo do BatchExecutor
                    # O 'advance=1' move a barra um passo
                    def update_ui( tid = task_id ):
                        progress.update( tid, advance = 1 )

                    # Injeta no Job
                    job.progress_callback = update_ui

                    # Inicia a Thread
                    future = executor.submit( self._worker_wrapper, job )
                    futures_map[ future ] = job

                # 2. Monitorar Finalização
                for future in as_completed( futures_map ):
                    job = futures_map[ future ]
                    try:
                        res = future.result()
                        resultados.append( res )
                    except Exception as exc:
                        console.print( f"[red]❌ Erro crítico em {job.nome_estrategia}: {exc}[/]" )

        return resultados

    @staticmethod
    def _worker_wrapper( job: TranslationJob ) -> PipelineResult:
        pipeline = TranslationPipeline()
        return pipeline.run( job )
