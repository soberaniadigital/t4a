# =============================================================================
# EXECUTOR DE NÍVEIS DE CONTEXTO - VERSÃO ADAPTADA PARA DADOS MULTILÍNGUES
# =============================================================================

import sys
import logging
import time
import argparse
import json
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
from datetime import datetime
from itertools import combinations

# Imports do Rich para UI
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich import box

# Setup de Path
ROOT_DIR = Path( __file__ ).resolve().parent.parent
sys.path.append( str( ROOT_DIR ) )

# Imports Aplicação
from src.application.runners.parallel_runner import ParallelRunner
from src.application.dto.translation_job import TranslationJob
from src.application.dto.translation_context import ContextoTraducao

# Log
logging.basicConfig(
    level = logging.INFO,
    format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename = 'context_levels_execution.log',
    filemode = 'w'
)

console = Console()

# --- CONFIGURAÇÃO ---
CONTEXT_LEVELS = [ 0, 1, 2 ]
PROVIDER = "LLAMA"

# Idiomas disponíveis (pt_BR é o alvo, os outros são contextos)
LANGUAGES = {
    'pt_BR': { 'name': 'Português (BR)', 'family': 'Românica' },
    'es': { 'name': 'Espanhol', 'family': 'Românica' },
    'fr': { 'name': 'Francês', 'family': 'Românica' },
    'de': { 'name': 'Alemão', 'family': 'Germânica' },
    'ru': { 'name': 'Russo', 'family': 'Eslava' },
    'zh_CN': { 'name': 'Chinês', 'family': 'Sino-Tibetana' },
    'vi': { 'name': 'Vietnamita', 'family': 'Austroasiática' },
    'id': { 'name': 'Indonésio', 'family': 'Austronésia' }
}

TARGET_LANGUAGE = 'pt_BR'
CONTEXT_LANGUAGES = [ lang for lang in LANGUAGES.keys() if lang != TARGET_LANGUAGE ]


class CheckpointManager:
    """Gerencia o registro de execuções já completadas"""

    def __init__( self, checkpoint_file: Path ):
        self.checkpoint_file = checkpoint_file
        self.completed_jobs: Set[ str ] = set()
        self.execution_times: Dict[ str, float ] = { }
        self._load_checkpoint()

    def _load_checkpoint( self ):
        """Carrega o checkpoint existente"""
        if self.checkpoint_file.exists():
            try:
                with open( self.checkpoint_file, 'r', encoding = 'utf-8' ) as f:
                    data = json.load( f )
                    self.completed_jobs = set( data.get( 'completed_jobs', [ ] ) )
                    self.execution_times = data.get( 'execution_times', { } )
                console.print( f"[cyan]✓ Checkpoint carregado: {len( self.completed_jobs )} execuções completadas[/]" )
            except Exception as e:
                console.print( f"[yellow]⚠ Erro ao carregar checkpoint: {e}[/]" )

    def _save_checkpoint( self ):
        """Salva o checkpoint atual"""
        try:
            self.checkpoint_file.parent.mkdir( parents = True, exist_ok = True )
            data = {
                'completed_jobs': list( self.completed_jobs ),
                'execution_times': self.execution_times,
                'last_update': datetime.now().isoformat()
            }
            with open( self.checkpoint_file, 'w', encoding = 'utf-8' ) as f:
                json.dump( data, f, indent = 2, ensure_ascii = False )
        except Exception as e:
            console.print( f"[red]✗ Erro ao salvar checkpoint: {e}[/]" )

    def is_completed( self, job: TranslationJob ) -> bool:
        """Verifica se um job já foi completado"""
        job_id = self._get_job_id( job )
        return job_id in self.completed_jobs

    def mark_completed( self, job: TranslationJob, execution_time: float ):
        """Marca um job como completado"""
        job_id = self._get_job_id( job )
        self.completed_jobs.add( job_id )
        self.execution_times[ job_id ] = execution_time
        self._save_checkpoint()

    def _get_job_id( self, job: TranslationJob ) -> str:
        """Gera um ID único para o job baseado em seus parâmetros"""
        return str( Path( job.arquivo_saida ).relative_to( ROOT_DIR ) )

    def get_statistics( self ) -> Dict:
        """Retorna estatísticas do checkpoint"""
        if not self.execution_times:
            return {
                'total_completed': len( self.completed_jobs ),
                'avg_time': 0,
                'total_time': 0,
                'min_time': 0,
                'max_time': 0
            }

        times = list( self.execution_times.values() )
        return {
            'total_completed': len( self.completed_jobs ),
            'avg_time': sum( times ) / len( times ),
            'total_time': sum( times ),
            'min_time': min( times ),
            'max_time': max( times )
        }


class ExecutionTracker:
    """Rastreia o progresso da execução em tempo real"""

    def __init__( self, total_jobs: int ):
        self.total_jobs = total_jobs
        self.current_job = 0
        self.completed = 0
        self.failed = 0
        self.skipped = 0
        self.start_time = time.time()
        self.current_job_name = ""
        self.current_job_start = None

    def start_job( self, job_name: str ):
        """Marca o início de um novo job"""
        self.current_job += 1
        self.current_job_name = job_name
        self.current_job_start = time.time()

    def finish_job( self, success: bool ):
        """Marca o fim de um job"""
        if success:
            self.completed += 1
        else:
            self.failed += 1

    def skip_job( self ):
        """Marca um job como pulado"""
        self.skipped += 1
        self.current_job += 1

    def get_elapsed_time( self ) -> float:
        """Retorna tempo decorrido total"""
        return time.time() - self.start_time

    def get_current_job_time( self ) -> float:
        """Retorna tempo do job atual"""
        if self.current_job_start:
            return time.time() - self.current_job_start
        return 0

    def get_eta( self ) -> float:
        """Calcula tempo estimado restante"""
        if self.completed == 0:
            return 0
        avg_time = self.get_elapsed_time() / self.completed
        remaining = self.total_jobs - self.completed - self.skipped
        return avg_time * remaining

    def _format_time( self, seconds: float ) -> str:
        """Formata segundos em HH:MM:SS"""
        h, remainder = divmod( int( seconds ), 3600 )
        m, s = divmod( remainder, 60 )
        if h > 0:
            return f"{h}h {m}m {s}s"
        elif m > 0:
            return f"{m}m {s}s"
        else:
            return f"{s}s"


class MultilingualExperimentBuilder:
    """Builder adaptado para trabalhar com arquivos .po multilíngues"""

    def __init__( self, base_input_dir: Path, base_output_dir: Path ):
        self.input_dir = base_input_dir
        self.output_dir = base_output_dir
        self.output_dir.mkdir( parents = True, exist_ok = True )

    def listar_projetos( self ) -> List[ Path ]:
        """Lista pastas de projetos no diretório de entrada"""
        if not self.input_dir.exists():
            return [ ]

        projetos = [
            p for p in self.input_dir.iterdir()
            if p.is_dir() and not p.name.startswith( '.' )
        ]

        return sorted( projetos )

    def _identificar_arquivos( self, projeto_dir: Path ) -> Tuple[ Optional[ Path ], Dict[ str, Path ] ]:
        """
        Identifica arquivos .po de cada idioma no projeto
        Retorna: (arquivo_alvo_pt_BR, mapa_contextos_outros_idiomas)
        """
        arquivos_po = { }

        for po_file in projeto_dir.glob( '*.po' ):
            filename = po_file.name

            # Identifica qual idioma é cada arquivo
            for lang_code in LANGUAGES.keys():
                if f'.{lang_code}.po' in filename:
                    arquivos_po[ lang_code ] = po_file
                    break

        if not arquivos_po:
            return None, { }

        # Arquivo alvo (pt_BR)
        arquivo_alvo = arquivos_po.get( TARGET_LANGUAGE )

        # Contextos são os outros idiomas
        mapa_contextos = {
            lang: path for lang, path in arquivos_po.items()
            if lang != TARGET_LANGUAGE
        }

        return arquivo_alvo, mapa_contextos

    def construir_jobs_para_nivel( self, projeto_dir: Path, nivel_contexto: int ) -> List[ TranslationJob ]:
        """
        Constrói jobs para um nível de contexto específico

        Nível 0: Sem contexto (tradução direta)
        Nível 1: Um idioma de contexto
        Nível 2: Dois idiomas de contexto
        """
        arquivo_alvo, mapa_contextos = self._identificar_arquivos( projeto_dir )

        if not arquivo_alvo or not arquivo_alvo.exists():
            console.print( f"[yellow]⚠ {projeto_dir.name}: Arquivo pt_BR não encontrado[/]" )
            return [ ]

        # Usa o arquivo em inglês como entrada (se existir, senão usa primeiro disponível)
        arquivo_entrada = self._encontrar_arquivo_origem( projeto_dir )
        if not arquivo_entrada:
            console.print( f"[yellow]⚠ {projeto_dir.name}: Nenhum arquivo de origem encontrado[/]" )
            return [ ]

        idiomas_disponiveis = list( mapa_contextos.keys() )
        jobs = [ ]

        if nivel_contexto == 0:
            # Nível 0: Sem contexto
            output_path = self._gerar_caminho_saida(
                projeto_dir.name,
                arquivo_entrada.name,
                PROVIDER,
                [ ]
            )
            output_path.parent.mkdir( parents = True, exist_ok = True )

            job = TranslationJob(
                nome_estrategia = PROVIDER,
                arquivo_entrada = str( arquivo_entrada ),
                arquivo_saida = str( output_path ),
                contextos = [ ]
            )
            jobs.append( job )

        elif nivel_contexto == 1:
            # Nível 1: Um idioma de contexto por vez
            for idioma_ctx in idiomas_disponiveis:
                ctx_path = mapa_contextos[ idioma_ctx ]
                output_path = self._gerar_caminho_saida(
                    projeto_dir.name,
                    arquivo_entrada.name,
                    PROVIDER,
                    [ idioma_ctx ]
                )
                output_path.parent.mkdir( parents = True, exist_ok = True )

                job = TranslationJob(
                    nome_estrategia = PROVIDER,
                    arquivo_entrada = str( arquivo_entrada ),
                    arquivo_saida = str( output_path ),
                    contextos = [ ContextoTraducao( str( ctx_path ), idioma_ctx.upper() ) ]
                )
                jobs.append( job )

        elif nivel_contexto == 2:
            # Nível 2: Pares de idiomas de contexto
            for combo in combinations( idiomas_disponiveis, 2 ):
                idioma1, idioma2 = combo
                output_path = self._gerar_caminho_saida(
                    projeto_dir.name,
                    arquivo_entrada.name,
                    PROVIDER,
                    list( combo )
                )
                output_path.parent.mkdir( parents = True, exist_ok = True )

                contextos = [
                    ContextoTraducao( str( mapa_contextos[ idioma1 ] ), idioma1.upper() ),
                    ContextoTraducao( str( mapa_contextos[ idioma2 ] ), idioma2.upper() )
                ]

                job = TranslationJob(
                    nome_estrategia = PROVIDER,
                    arquivo_entrada = str( arquivo_entrada ),
                    arquivo_saida = str( output_path ),
                    contextos = contextos
                )
                jobs.append( job )

        return jobs

    def _encontrar_arquivo_origem( self, projeto_dir: Path ) -> Optional[ Path ]:
        """
        Tenta encontrar o arquivo de origem (inglês preferencialmente)
        Fallback: usa primeiro arquivo .po disponível
        """
        # Tenta encontrar arquivo em inglês
        arquivos_en = list( projeto_dir.glob( '*.en.po' ) )
        if arquivos_en:
            return arquivos_en[ 0 ]

        # Fallback: qualquer .po que não seja pt_BR
        for po_file in projeto_dir.glob( '*.po' ):
            if '.pt_BR.po' not in po_file.name:
                return po_file

        return None

    def _gerar_caminho_saida(
            self,
            projeto_nome: str,
            arquivo_origem_nome: str,
            estrategia: str,
            idiomas_contexto: List[ str ]
    ) -> Path:
        """
        Gera caminho de saída padronizado
        Formato: projeto/arquivo.pt_BR.llama.ctx-N.langs.po
        """
        # Remove extensão e idioma original
        stem = arquivo_origem_nome.replace( '.po', '' ).replace( '.pot', '' )

        # Remove códigos de idioma conhecidos
        for lang in LANGUAGES.keys():
            stem = stem.replace( f'.{lang}', '' )

        # Monta sufixo de contexto
        n_ctx = len( idiomas_contexto )
        if n_ctx == 0:
            sufixo_ctx = "ctx-0"
        else:
            langs_str = "-".join( sorted( idiomas_contexto ) )
            sufixo_ctx = f"ctx-{n_ctx}.{langs_str}"

        # Nome final
        nome_final = f"{stem}.pt_BR.{estrategia.lower()}.{sufixo_ctx}.po"

        return self.output_dir / projeto_nome / nome_final


def setup_arguments():
    parser = argparse.ArgumentParser( description = "Executor de Traduções com Níveis de Contexto (TCC)" )
    parser.add_argument(
        '--origem', type = str, required = True,
        choices = [ 'filtered', 'sample', 'download' ],
        help = "Fonte dos dados: filtered (interseção), sample (10%), ou download (completo)"
    )
    parser.add_argument(
        '--projeto', type = str, required = False,
        help = "Nome específico do projeto a processar (opcional)"
    )
    parser.add_argument(
        '--workers', type = int, default = 1,
        help = "Número de threads simultâneas"
    )
    parser.add_argument(
        '--reset-checkpoint', action = 'store_true',
        help = "Ignora checkpoint e executa tudo novamente"
    )
    parser.add_argument(
        '--max-projetos', type = int, default = None,
        help = "Limita o número de projetos a processar (útil para testes)"
    )
    return parser.parse_args()


def calcular_combinacoes( builder: MultilingualExperimentBuilder, projetos: List[ Path ] ) -> Dict:
    """Calcula todas as combinações possíveis"""
    console.print( "\n[bold yellow]🔄 Calculando combinações de contexto...[/]" )

    totais_por_nivel = { nivel: 0 for nivel in CONTEXT_LEVELS }
    detalhes_por_projeto = { }

    for projeto in projetos:
        _, mapa_ctx = builder._identificar_arquivos( projeto )
        qtd_ctx = len( mapa_ctx )

        if qtd_ctx == 0:
            console.print( f"[dim]  ⚠ {projeto.name}: Sem arquivos de contexto[/]" )
            continue

        combinacoes_projeto = { }
        for nivel in CONTEXT_LEVELS:
            jobs = builder.construir_jobs_para_nivel( projeto, nivel )
            qtd = len( jobs )
            combinacoes_projeto[ nivel ] = qtd
            totais_por_nivel[ nivel ] += qtd

        detalhes_por_projeto[ projeto.name ] = {
            'contextos_disponiveis': qtd_ctx,
            'combinacoes': combinacoes_projeto,
            'total': sum( combinacoes_projeto.values() )
        }

    return {
        'totais_por_nivel': totais_por_nivel,
        'total_geral': sum( totais_por_nivel.values() ),
        'detalhes': detalhes_por_projeto
    }


def exibir_planejamento( estatisticas: Dict, checkpoint_stats: Dict ):
    """Exibe planejamento detalhado da execução"""

    table = Table(
        title = "📊 Planejamento de Execução - Níveis de Contexto",
        box = box.ROUNDED,
        show_lines = True
    )
    table.add_column( "Projeto", style = "cyan", max_width = 40 )
    table.add_column( "Ctx", justify = "center", style = "magenta" )

    for nivel in CONTEXT_LEVELS:
        table.add_column( f"Nv {nivel}", justify = "right", style = "yellow" )

    table.add_column( "Total", justify = "right", style = "green bold" )

    # Linhas de projetos
    for projeto, dados in sorted( estatisticas[ 'detalhes' ].items() ):
        row = [
            projeto[ :37 ] + "..." if len( projeto ) > 40 else projeto,
            str( dados[ 'contextos_disponiveis' ] )
        ]
        for nivel in CONTEXT_LEVELS:
            row.append( str( dados[ 'combinacoes' ][ nivel ] ) )
        row.append( str( dados[ 'total' ] ) )
        table.add_row( *row )

    # Linha de totais
    totais_row = [ "TOTAL", "-" ]
    for nivel in CONTEXT_LEVELS:
        totais_row.append( str( estatisticas[ 'totais_por_nivel' ][ nivel ] ) )
    totais_row.append( str( estatisticas[ 'total_geral' ] ) )
    table.add_row( *totais_row, style = "bold white on blue" )

    console.print( table )

    # Resumo
    console.print( "\n[bold cyan]📈 Resumo por Nível:[/]" )
    descricoes = {
        0: "Tradução Direta (sem contexto)",
        1: "Contexto de 1 idioma",
        2: "Contexto de 2 idiomas"
    }
    for nivel in CONTEXT_LEVELS:
        qtd = estatisticas[ 'totais_por_nivel' ][ nivel ]
        console.print( f"  • Nível {nivel} ({descricoes[ nivel ]}): [green]{qtd}[/] execuções" )

    console.print( f"\n[bold white on blue] 🚀 TOTAL: {estatisticas[ 'total_geral' ]} execuções [/]" )

    # Estatísticas de checkpoint
    if checkpoint_stats[ 'total_completed' ] > 0:
        console.print( f"\n[bold yellow]📋 Checkpoint Existente:[/]" )
        console.print( f"  • Execuções completadas: [green]{checkpoint_stats[ 'total_completed' ]}[/]" )
        console.print( f"  • Tempo médio: [cyan]{checkpoint_stats[ 'avg_time' ]:.1f}s[/]" )
        console.print( f"  • Tempo total acumulado: [cyan]{checkpoint_stats[ 'total_time' ] / 60:.1f} minutos[/]" )

        restantes = estatisticas[ 'total_geral' ] - checkpoint_stats[ 'total_completed' ]
        if restantes > 0:
            console.print( f"  • [yellow]Restam {restantes} execuções[/]" )
        else:
            console.print( f"  • [green]✓ Todas as execuções já foram completadas![/]" )


def executar_jobs_com_checkpoint(
        jobs: List[ TranslationJob ],
        runner: ParallelRunner,
        checkpoint: CheckpointManager,
        tracker: ExecutionTracker
):
    """Executa jobs com checkpoint e visualização melhorada"""

    for job in jobs:
        # Verifica checkpoint
        if checkpoint.is_completed( job ):
            tracker.skip_job()
            continue

        # Nome amigável do job
        job_name = Path( job.arquivo_saida ).name
        tracker.start_job( job_name )

        # Atualiza display
        console.print( f"\n[bold cyan]▶ [{tracker.current_job}/{tracker.total_jobs}][/] {job_name}" )

        # Executa job
        start_time = time.time()
        try:
            resultado = runner.processar_batch( [ job ] )
            execution_time = time.time() - start_time

            if resultado and resultado[ 0 ].sucesso:
                checkpoint.mark_completed( job, execution_time )
                tracker.finish_job( True )
                console.print( f"  [green]✓ Concluído em {execution_time:.1f}s[/]" )
            else:
                tracker.finish_job( False )
                erro = resultado[ 0 ].erro if resultado else "Erro desconhecido"
                console.print( f"  [red]✗ Falhou: {erro}[/]" )

        except Exception as e:
            execution_time = time.time() - start_time
            tracker.finish_job( False )
            console.print( f"  [red]✗ Exceção: {e}[/]" )


def main():
    args = setup_arguments()

    # Mapeia origem para pasta correta
    origem_map = {
        'filtered': 'translations_filtered',
        'sample': 'translations_sample',
        'download': 'translations_download'
    }

    input_dir = ROOT_DIR / "data" / origem_map[ args.origem ]
    output_dir = ROOT_DIR / "resultados" / f"context_levels_{args.origem}"
    checkpoint_file = output_dir / ".checkpoint.json"

    if not input_dir.exists():
        console.print( f"[bold red]❌ Erro: Diretório não encontrado: {input_dir}[/]" )
        console.print( f"[yellow]Execute primeiro os scripts de download/filtragem/amostragem![/]" )
        return

    # Banner inicial
    console.print( Panel.fit(
        f"[bold magenta]🎯 Executor de Níveis de Contexto[/]\n"
        f"[cyan]Origem:[/] {args.origem} ({origem_map[ args.origem ]})\n"
        f"[cyan]Provedor:[/] {PROVIDER}\n"
        f"[cyan]Níveis:[/] {CONTEXT_LEVELS}\n"
        f"[cyan]Idioma Alvo:[/] {TARGET_LANGUAGE}\n"
        f"[cyan]Idiomas Contexto:[/] {len( CONTEXT_LANGUAGES )}\n"
        f"[dim]Workers: {args.workers}[/]",
        border_style = "magenta"
    ) )

    # Setup
    builder = MultilingualExperimentBuilder( input_dir, output_dir )
    runner = ParallelRunner( max_workers = args.workers )

    # Lista projetos
    projetos = builder.listar_projetos()

    if args.projeto:
        projetos = [ p for p in projetos if p.name == args.projeto ]
        if not projetos:
            console.print( f"[bold red]❌ Projeto '{args.projeto}' não encontrado![/]" )
            return

    if args.max_projetos:
        projetos = projetos[ :args.max_projetos ]
        console.print( f"[yellow]⚠ Limitado a {args.max_projetos} projeto(s)[/]" )

    if not projetos:
        console.print( "[yellow]⚠️ Nenhum projeto encontrado.[/]" )
        return

    console.print( f"\n[cyan]📁 Encontrados {len( projetos )} projeto(s)[/]" )

    # Calcula combinações
    estatisticas = calcular_combinacoes( builder, projetos )

    if estatisticas[ 'total_geral' ] == 0:
        console.print( "[red]Nenhum job gerado. Verifique os arquivos de entrada.[/]" )
        return

    # Checkpoint
    if args.reset_checkpoint and checkpoint_file.exists():
        checkpoint_file.unlink()
        console.print( "[yellow]✓ Checkpoint resetado[/]" )

    checkpoint = CheckpointManager( checkpoint_file )
    checkpoint_stats = checkpoint.get_statistics()

    # Exibe planejamento
    exibir_planejamento( estatisticas, checkpoint_stats )

    # Verifica se há trabalho a fazer
    restantes = estatisticas[ 'total_geral' ] - checkpoint_stats[ 'total_completed' ]
    if restantes == 0:
        console.print( "\n[bold green]✓ Todas as execuções já foram completadas![/]" )
        console.print( "[dim]Use --reset-checkpoint para executar novamente[/]" )
        return

    console.print( f"\n[bold green]Iniciando {restantes} execução(ões) em 3 segundos...[/]" )
    console.print( "[dim](Ctrl+C para pausar - o checkpoint será salvo)[/]" )
    time.sleep( 3 )

    # Execução
    print( "\n" + "=" * 60 )
    print( "▶️  INICIANDO EXECUÇÃO" )
    print( "=" * 60 )

    tracker = ExecutionTracker( estatisticas[ 'total_geral' ] )

    try:
        for i, projeto in enumerate( projetos, 1 ):
            console.print( f"\n[bold magenta]📦 PROJETO [{i}/{len( projetos )}]: {projeto.name.upper()}[/]" )
            print( "-" * 60 )

            for nivel in CONTEXT_LEVELS:
                jobs_batch = builder.construir_jobs_para_nivel( projeto, nivel )

                if not jobs_batch:
                    continue

                console.print( f"\n[bold yellow]  📍 Nível {nivel}:[/] {len( jobs_batch )} job(s)" )

                executar_jobs_com_checkpoint( jobs_batch, runner, checkpoint, tracker )

        # Relatório final
        console.print( "\n" + "=" * 60 )
        console.print( "[bold green]🏁 EXECUÇÃO CONCLUÍDA![/]" )
        console.print( "=" * 60 )

        final_stats = checkpoint.get_statistics()
        console.print( f"✓ Total executado: {final_stats[ 'total_completed' ]}" )
        console.print( f"✓ Tempo total: {final_stats[ 'total_time' ] / 60:.1f} minutos" )
        console.print( f"✓ Tempo médio por execução: {final_stats[ 'avg_time' ]:.1f}s" )
        console.print( f"📁 Resultados em: [cyan]{output_dir}[/]" )

    except KeyboardInterrupt:
        console.print( "\n\n[yellow]⏸️  Execução pausada pelo usuário[/]" )
        current_stats = checkpoint.get_statistics()
        console.print( f"✓ Checkpoint salvo: {current_stats[ 'total_completed' ]} execuções completadas" )
        console.print( "[dim]Execute novamente para continuar de onde parou[/]" )


if __name__ == "__main__":
    main()
