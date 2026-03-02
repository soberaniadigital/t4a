import os
import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from packaging import version as pkg_version
import concurrent.futures
from typing import List, Optional, Tuple, Dict, Any
from pathlib import Path
import time

# --- Rich Imports ---
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
    DownloadColumn,
    TransferSpeedColumn
)
from rich.panel import Panel
from rich.table import Table

# --- Configurações de Caminhos ---
SCRIPT_DIR = os.path.dirname( os.path.abspath( __file__ ) )
DATA_ROOT = os.path.abspath( os.path.join( SCRIPT_DIR, '..', 'data' ) )
DOWNLOAD_ROOT = os.path.join( DATA_ROOT, 'translations_download' )

# Configurações de Negócio
BASE_URL = "https://translationproject.org/domain/index.html"
DOMAIN_BASE_URL = "https://translationproject.org/domain/"

MAX_WORKERS = 5  # Menos workers para ser gentil com o servidor
THRESHOLD = 90.0

# Idiomas a serem baixados
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

console = Console()


class WebClient:
    @staticmethod
    def get_page( url: str ) -> Optional[ BeautifulSoup ]:
        try:
            response = requests.get( url, timeout = 20 )
            response.raise_for_status()
            return BeautifulSoup( response.text, 'html.parser' )
        except requests.RequestException:
            return None

    @staticmethod
    def download_file( url: str, destination: Path ) -> bool:
        """Baixa um arquivo e salva no destino especificado"""
        try:
            response = requests.get( url, timeout = 30, stream = True )
            response.raise_for_status()

            # Cria diretório se não existir
            destination.parent.mkdir( parents = True, exist_ok = True )

            # Salva o arquivo
            with open( destination, 'wb' ) as f:
                for chunk in response.iter_content( chunk_size = 8192 ):
                    f.write( chunk )

            return True
        except Exception as e:
            console.print( f"[red]Erro ao baixar {url}: {e}[/]" )
            return False


class ProjectAnalyzer:
    """Analisa um projeto e verifica traduções em múltiplos idiomas"""

    def __init__( self, project_url: str, project_name: str ):
        self.url = project_url
        self.name = project_name

    def _extract_language( self, filename: str ) -> str:
        """Extrai o código do idioma do nome do arquivo"""
        match = re.search( r'\.([a-zA-Z0-9_@]+)\.po$', filename )
        if match:
            return match.group( 1 )
        return "unknown"

    def _parse_stats( self, stats_text: str ) -> Tuple[ int, int ]:
        """Extrai números de tradução do formato 'X/Y'"""
        try:
            parts = stats_text.split( '/' )
            if len( parts ) != 2:
                return 0, 0
            current = int( parts[ 0 ].strip() )
            total = int( parts[ 1 ].strip() )
            return current, total
        except ValueError:
            return 0, 0

    def analyze( self ) -> Optional[ Dict[ str, Any ] ]:
        """Analisa o projeto e retorna informações de todos os idiomas"""
        soup = WebClient.get_page( self.url )
        if not soup:
            return None

        rows = soup.find_all( 'tr' )
        version_map: Dict[ str, List[ Dict[ str, Any ] ] ] = { }

        # Coleta todas as versões e seus arquivos
        for row in rows:
            cols = row.find_all( 'td' )
            version_text = None
            target_col_for_link = None
            stats_text = ""

            # Detecta formato da tabela
            if len( cols ) >= 5:
                version_text = cols[ 2 ].get_text( strip = True )
                target_col_for_link = cols[ 2 ]
                stats_text = cols[ 4 ].get_text( strip = True )
            elif len( cols ) == 3:
                version_text = cols[ 0 ].get_text( strip = True )
                target_col_for_link = cols[ 0 ]
                stats_text = cols[ 2 ].get_text( strip = True )
            else:
                continue

            if not version_text or not version_text[ 0 ].isdigit():
                continue

            link_tag = target_col_for_link.find( 'a', href = True )
            if link_tag:
                href = link_tag[ 'href' ]
                if href.endswith( '.po' ):
                    po_filename = os.path.basename( href )

                    if version_text not in version_map:
                        version_map[ version_text ] = [ ]

                    version_map[ version_text ].append( {
                        'filename': po_filename,
                        'url': urljoin( self.url, href ),
                        'stats': stats_text
                    } )

        if not version_map:
            return None

        # Identifica a versão mais recente
        try:
            latest_version = max( version_map.keys(), key = lambda v: pkg_version.parse( v ) )
        except (pkg_version.InvalidVersion, ValueError):
            latest_version = max( version_map.keys() )

        # Procura por todos os idiomas na versão mais recente
        candidates = version_map[ latest_version ]
        languages_data = { }

        for item in candidates:
            filename = item[ 'filename' ]
            lang = self._extract_language( filename )

            if lang in LANGUAGES:
                stats = item[ 'stats' ]
                translated, total = self._parse_stats( stats )

                if total > 0:
                    languages_data[ lang ] = {
                        'translated': translated,
                        'total': total,
                        'percentage': (translated / total * 100),
                        'url': item[ 'url' ],
                        'filename': filename
                    }

        if languages_data:
            return {
                'name': self.name,
                'latest_version': latest_version,
                'languages': languages_data,
                'url': self.url
            }

        return None


class TranslationDownloader:
    """Baixa arquivos de tradução dos projetos excelentes"""

    def __init__( self ):
        self.excellent_projects = [ ]
        self.download_stats = {
            'total_files': 0,
            'downloaded': 0,
            'failed': 0,
            'skipped': 0
        }

    def fetch_all_projects( self ) -> List[ Tuple[ str, str ] ]:
        """Obtém lista de todos os projetos disponíveis"""
        console.print( "[cyan]Obtendo lista de projetos...[/]" )

        soup = WebClient.get_page( BASE_URL )
        if not soup:
            console.print( "[red]Erro ao acessar página principal[/]" )
            return [ ]

        table = soup.find( 'table' )
        if not table:
            console.print( "[red]Tabela de projetos não encontrada[/]" )
            return [ ]

        rows = table.find_all( 'tr' )
        projects = [ ]

        for row in rows:
            if row.find( 'th' ):
                continue

            cols = row.find_all( 'td' )
            if not cols:
                continue

            link = cols[ 0 ].find( 'a', href = True )
            if link:
                name = link.get_text( strip = True )
                url = urljoin( DOMAIN_BASE_URL, link[ 'href' ] )
                projects.append( (name, url) )

        console.print( f"[green]✓ Encontrados {len( projects )} projetos[/]" )
        return projects

    def _has_all_languages_above_threshold( self, project: Dict[ str, Any ] ) -> bool:
        """Verifica se o projeto tem TODOS os 8 idiomas com pelo menos 90%"""
        languages = project[ 'languages' ]

        if len( languages ) < len( LANGUAGES ):
            return False

        for lang_code in LANGUAGES.keys():
            if lang_code not in languages:
                return False
            if languages[ lang_code ][ 'percentage' ] < THRESHOLD:
                return False

        return True

    def find_excellent_projects( self, projects: List[ Tuple[ str, str ] ] ):
        """Encontra projetos com todos os 8 idiomas ≥90%"""

        progress = Progress(
            SpinnerColumn(),
            TextColumn( "[bold blue]{task.description}" ),
            BarColumn( bar_width = None ),
            TextColumn( "[progress.percentage]{task.percentage:>3.0f}%" ),
            TextColumn( "•" ),
            TextColumn( "[green]Excelentes: {task.fields[excellent_count]}" ),
            TimeElapsedColumn(),
            console = console
        )

        with progress:
            task_id = progress.add_task(
                f"[cyan]Buscando projetos excelentes...",
                total = len( projects ),
                excellent_count = 0
            )

            with concurrent.futures.ThreadPoolExecutor( max_workers = MAX_WORKERS ) as executor:
                analyzers = [ ProjectAnalyzer( url, name ) for name, url in projects ]

                future_to_analyzer = {
                    executor.submit( analyzer.analyze ): analyzer
                    for analyzer in analyzers
                }

                for future in concurrent.futures.as_completed( future_to_analyzer ):
                    try:
                        result = future.result()
                        if result and self._has_all_languages_above_threshold( result ):
                            self.excellent_projects.append( result )
                            progress.update(
                                task_id,
                                advance = 1,
                                excellent_count = len( self.excellent_projects )
                            )
                        else:
                            progress.advance( task_id )
                    except Exception:
                        progress.advance( task_id )

    def download_translations( self ):
        """Baixa os arquivos .po dos projetos excelentes"""

        if not self.excellent_projects:
            console.print( "[yellow]Nenhum projeto excelente encontrado para download[/]" )
            return

        # Calcula total de arquivos a baixar
        total_files = len( self.excellent_projects ) * len( LANGUAGES )
        self.download_stats[ 'total_files' ] = total_files

        console.print( f"\n[bold cyan]Iniciando download de {total_files} arquivos "
                       f"de {len( self.excellent_projects )} projetos...[/]\n" )

        # Cria diretório raiz de downloads
        Path( DOWNLOAD_ROOT ).mkdir( parents = True, exist_ok = True )

        # Log de downloads
        log_file = Path( DOWNLOAD_ROOT ) / 'download_log.txt'

        progress = Progress(
            SpinnerColumn(),
            TextColumn( "[bold blue]{task.description}" ),
            BarColumn( bar_width = None ),
            TextColumn( "[progress.percentage]{task.percentage:>3.0f}%" ),
            TextColumn( "•" ),
            TextColumn( "[green]{task.completed}/{task.total} arquivos" ),
            TimeElapsedColumn(),
            console = console
        )

        with open( log_file, 'w', encoding = 'utf-8' ) as log:
            log.write( "LOG DE DOWNLOAD DE TRADUÇÕES\n" )
            log.write( "=" * 100 + "\n\n" )

            with progress:
                task_id = progress.add_task(
                    "[cyan]Baixando arquivos de tradução...",
                    total = total_files
                )

                for project in self.excellent_projects:
                    project_name = project[ 'name' ]
                    project_version = project[ 'latest_version' ]

                    # Cria pasta do projeto (sanitiza o nome)
                    safe_name = re.sub( r'[^\w\s-]', '', project_name ).strip().replace( ' ', '_' )
                    project_dir = Path( DOWNLOAD_ROOT ) / f"{safe_name}_v{project_version}"
                    project_dir.mkdir( parents = True, exist_ok = True )

                    log.write( f"\nProjeto: {project_name} (v{project_version})\n" )
                    log.write( "-" * 100 + "\n" )

                    # Baixa cada idioma
                    for lang_code in LANGUAGES.keys():
                        if lang_code in project[ 'languages' ]:
                            lang_data = project[ 'languages' ][ lang_code ]
                            url = lang_data[ 'url' ]
                            filename = lang_data[ 'filename' ]

                            destination = project_dir / filename

                            # Verifica se já existe
                            if destination.exists():
                                log.write( f"  [SKIP] {filename} - Já existe\n" )
                                self.download_stats[ 'skipped' ] += 1
                                progress.advance( task_id )
                                continue

                            # Faz o download
                            success = WebClient.download_file( url, destination )

                            if success:
                                log.write( f"  [OK] {filename} - {lang_data[ 'percentage' ]:.1f}% "
                                           f"({lang_data[ 'translated' ]}/{lang_data[ 'total' ]})\n" )
                                self.download_stats[ 'downloaded' ] += 1
                            else:
                                log.write( f"  [ERRO] {filename}\n" )
                                self.download_stats[ 'failed' ] += 1

                            progress.advance( task_id )

                            # Pequeno delay para não sobrecarregar o servidor
                            time.sleep( 0.1 )

            log.write( "\n" + "=" * 100 + "\n" )
            log.write( "RESUMO DO DOWNLOAD\n" )
            log.write( "=" * 100 + "\n" )
            log.write( f"Total de arquivos: {self.download_stats[ 'total_files' ]}\n" )
            log.write( f"Baixados com sucesso: {self.download_stats[ 'downloaded' ]}\n" )
            log.write( f"Já existiam (pulados): {self.download_stats[ 'skipped' ]}\n" )
            log.write( f"Falhas: {self.download_stats[ 'failed' ]}\n" )

        console.print( f"\n[green]✓ Log salvo em: {log_file}[/]" )

    def display_summary( self ):
        """Exibe resumo dos downloads"""

        table = Table(
            title = "Resumo de Downloads",
            show_header = True,
            header_style = "bold magenta"
        )
        table.add_column( "Métrica", style = "cyan" )
        table.add_column( "Quantidade", justify = "right", style = "white" )

        table.add_row( "Projetos Excelentes", str( len( self.excellent_projects ) ) )
        table.add_row( "Total de Arquivos", str( self.download_stats[ 'total_files' ] ) )
        table.add_row( "✓ Baixados", f"[green]{self.download_stats[ 'downloaded' ]}[/]" )
        table.add_row( "⊘ Já Existiam", f"[yellow]{self.download_stats[ 'skipped' ]}[/]" )
        table.add_row( "✗ Falhas", f"[red]{self.download_stats[ 'failed' ]}[/]" )

        console.print( "\n" )
        console.print( table )

        # Lista dos projetos baixados
        if self.excellent_projects:
            projects_table = Table(
                title = f"Projetos Baixados ({len( self.excellent_projects )})",
                show_header = True,
                header_style = "bold green"
            )
            projects_table.add_column( "Projeto", style = "cyan" )
            projects_table.add_column( "Versão", style = "dim" )
            projects_table.add_column( "Pasta", style = "yellow" )

            for project in sorted( self.excellent_projects, key = lambda x: x[ 'name' ] )[ :20 ]:
                safe_name = re.sub( r'[^\w\s-]', '', project[ 'name' ] ).strip().replace( ' ', '_' )
                folder_name = f"{safe_name}_v{project[ 'latest_version' ]}"

                projects_table.add_row(
                    project[ 'name' ],
                    project[ 'latest_version' ],
                    folder_name
                )

            console.print( "\n" )
            console.print( projects_table )

            if len( self.excellent_projects ) > 20:
                console.print( f"\n[dim]... e mais {len( self.excellent_projects ) - 20} projetos[/]" )

        console.print( f"\n[bold green]📁 Arquivos salvos em: {DOWNLOAD_ROOT}[/]" )


def main():
    console.print( Panel.fit(
        "[bold magenta]Download de Traduções - Translation Project[/]\n"
        "[italic]Baixa arquivos .po dos projetos com todos os 8 idiomas ≥90%[/]\n\n"
        "Idiomas: pt_BR, es, fr, de, ru, zh_CN, vi, id",
        border_style = "magenta"
    ) )

    downloader = TranslationDownloader()

    # Busca lista de projetos
    projects = downloader.fetch_all_projects()
    if not projects:
        console.print( "[red]Nenhum projeto encontrado. Encerrando.[/]" )
        return

    # Encontra projetos excelentes
    downloader.find_excellent_projects( projects )

    if not downloader.excellent_projects:
        console.print( f"[yellow]Nenhum projeto com todos os 8 idiomas ≥{THRESHOLD}% encontrado.[/]" )
        return

    console.print( f"\n[bold green]✓ Encontrados {len( downloader.excellent_projects )} projetos excelentes[/]" )

    # Confirma download
    console.print( f"\n[yellow]Isso irá baixar {len( downloader.excellent_projects ) * 8} arquivos .po[/]" )
    response = input( "\nDeseja continuar? (s/N): " )

    if response.lower() not in [ 's', 'sim', 'y', 'yes' ]:
        console.print( "[yellow]Download cancelado pelo usuário[/]" )
        return

    # Faz o download
    downloader.download_translations()

    # Exibe resumo
    downloader.display_summary()

    console.print( "\n[bold green]✓ Processo concluído![/]" )


if __name__ == "__main__":
    main()
