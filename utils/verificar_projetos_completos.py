import os
import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from packaging import version as pkg_version
import concurrent.futures
from typing import List, Optional, Tuple, Dict, Any

# --- Rich Imports ---
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeElapsedColumn
)
from rich.panel import Panel
from rich.table import Table

# --- Configurações de Caminhos ---
SCRIPT_DIR = os.path.dirname( os.path.abspath( __file__ ) )
DATA_ROOT = os.path.abspath( os.path.join( SCRIPT_DIR, '..', 'data' ) )

# Configurações de Negócio
BASE_URL = "https://translationproject.org/domain/index.html"
DOMAIN_BASE_URL = "https://translationproject.org/domain/"

# Arquivos de saída
REPORT_FILE = os.path.join( DATA_ROOT, "relatorio_multilingue.txt" )
REPORT_CSV = os.path.join( DATA_ROOT, "relatorio_multilingue.csv" )
REPORT_SUMMARY_CSV = os.path.join( DATA_ROOT, "resumo_por_idioma.csv" )
REPORT_EXCELLENT_CSV = os.path.join( DATA_ROOT, "projetos_90_todos_idiomas.csv" )

MAX_WORKERS = 10
THRESHOLD = 90.0  # Percentual mínimo para considerar "bem traduzido"

# Idiomas a serem analisados por família linguística
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
        """
        Extrai números de tradução do formato 'X/Y'
        Retorna: (traduzidas, total)
        """
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
        """
        Analisa o projeto e retorna informações de todos os idiomas
        Retorna None se não tiver nenhum dos idiomas monitorados
        """
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

            # Valida se é uma versão numérica
            if not version_text or not version_text[ 0 ].isdigit():
                continue

            # Procura link para arquivo .po
            link_tag = target_col_for_link.find( 'a', href = True )
            if link_tag:
                href = link_tag[ 'href' ]
                if href.endswith( '.po' ):
                    po_filename = os.path.basename( href )

                    if version_text not in version_map:
                        version_map[ version_text ] = [ ]

                    version_map[ version_text ].append( {
                        'filename': po_filename,
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

            # Verifica se é um dos idiomas que estamos monitorando
            if lang in LANGUAGES:
                stats = item[ 'stats' ]
                translated, total = self._parse_stats( stats )

                if total > 0:
                    languages_data[ lang ] = {
                        'translated': translated,
                        'total': total,
                        'percentage': (translated / total * 100)
                    }

        # Só retorna se encontrou pelo menos um idioma
        if languages_data:
            return {
                'name': self.name,
                'latest_version': latest_version,
                'languages': languages_data
            }

        return None


class ReportGenerator:
    """Gera relatório de projetos com traduções multilíngues"""

    def __init__( self ):
        self.projects_data = [ ]
        self.excellent_projects = [ ]  # Projetos com todos os 8 idiomas ≥90%

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
            if row.find( 'th' ):  # Ignora cabeçalho
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
        """
        Verifica se o projeto tem TODOS os 8 idiomas com pelo menos 90% de tradução
        """
        languages = project[ 'languages' ]

        # Verifica se tem os 8 idiomas
        if len( languages ) < len( LANGUAGES ):
            return False

        # Verifica se todos os idiomas obrigatórios estão presentes
        for lang_code in LANGUAGES.keys():
            if lang_code not in languages:
                return False

        # Verifica se todos têm pelo menos 90%
        for lang_code in LANGUAGES.keys():
            if languages[ lang_code ][ 'percentage' ] < THRESHOLD:
                return False

        return True

    def analyze_projects( self, projects: List[ Tuple[ str, str ] ] ):
        """Analisa projetos e identifica os que têm todos os idiomas bem traduzidos"""

        progress = Progress(
            SpinnerColumn(),
            TextColumn( "[bold blue]{task.description}" ),
            BarColumn( bar_width = None ),
            TextColumn( "[progress.percentage]{task.percentage:>3.0f}%" ),
            TextColumn( "•" ),
            TextColumn( "[green]Total: {task.fields[found_count]}" ),
            TextColumn( "[yellow]| Excelentes: {task.fields[excellent_count]}" ),
            TimeElapsedColumn(),
            console = console
        )

        with progress:
            task_id = progress.add_task(
                f"[cyan]Analisando traduções multilíngues...",
                total = len( projects ),
                found_count = 0,
                excellent_count = 0
            )

            with concurrent.futures.ThreadPoolExecutor( max_workers = MAX_WORKERS ) as executor:
                # Cria analyzers
                analyzers = [ ProjectAnalyzer( url, name ) for name, url in projects ]

                # Submete tarefas
                future_to_analyzer = {
                    executor.submit( analyzer.analyze ): analyzer
                    for analyzer in analyzers
                }

                # Processa resultados conforme completam
                for future in concurrent.futures.as_completed( future_to_analyzer ):
                    analyzer = future_to_analyzer[ future ]
                    try:
                        result = future.result()
                        if result:
                            self.projects_data.append( result )

                            # Verifica se é um projeto "excelente"
                            if self._has_all_languages_above_threshold( result ):
                                self.excellent_projects.append( result )

                            progress.update(
                                task_id,
                                advance = 1,
                                found_count = len( self.projects_data ),
                                excellent_count = len( self.excellent_projects )
                            )
                        else:
                            progress.advance( task_id )
                    except Exception as exc:
                        console.print( f"[red]Erro ao analisar {analyzer.name}: {exc}[/]" )
                        progress.advance( task_id )

    def generate_report( self ):
        """Gera relatório em formato texto"""

        os.makedirs( os.path.dirname( REPORT_FILE ), exist_ok = True )

        if not self.projects_data:
            console.print( "[yellow]Nenhum projeto encontrado[/]" )
            return

        # Ordena projetos por nome
        self.projects_data.sort( key = lambda x: x[ 'name' ] )

        with open( REPORT_FILE, 'w', encoding = 'utf-8' ) as f:
            # Cabeçalho
            f.write( "=" * 120 + "\n" )
            f.write( "RELATÓRIO DE TRADUÇÕES MULTILÍNGUES\n" )
            f.write( "Translation Project (translationproject.org)\n" )
            f.write( "=" * 120 + "\n\n" )

            # DESTAQUE: Projetos com todos os idiomas ≥90%
            if self.excellent_projects:
                f.write( "🌟 " * 40 + "\n" )
                f.write( f"PROJETOS EXCELENTES: TODOS OS 8 IDIOMAS COM ≥{THRESHOLD}% DE TRADUÇÃO\n" )
                f.write( f"Total: {len( self.excellent_projects )} projetos\n" )
                f.write( "🌟 " * 40 + "\n\n" )

                for project in sorted( self.excellent_projects, key = lambda x: x[ 'name' ] ):
                    f.write( f"\n{'─' * 120}\n" )
                    f.write( f"✓ {project[ 'name' ]} (v{project[ 'latest_version' ]})\n" )
                    f.write( f"{'─' * 120}\n" )

                    # Mostra todos os idiomas com suas estatísticas
                    families = { }
                    for lang_code in LANGUAGES.keys():
                        family = LANGUAGES[ lang_code ][ 'family' ]
                        if family not in families:
                            families[ family ] = [ ]
                        families[ family ].append( lang_code )

                    for family, lang_codes in sorted( families.items() ):
                        f.write( f"\n  {family}:\n" )
                        for lang_code in lang_codes:
                            data = project[ 'languages' ][ lang_code ]
                            lang_name = LANGUAGES[ lang_code ][ 'name' ]
                            status = "✓ COMPLETO" if data[ 'percentage' ] >= 100 else f"• {data[ 'percentage' ]:.1f}%"
                            f.write( f"    {status} {lang_name}: {data[ 'translated' ]}/{data[ 'total' ]} mensagens\n" )

                f.write( "\n" + "=" * 120 + "\n\n" )

            # Estatísticas gerais por idioma
            f.write( "ESTATÍSTICAS POR IDIOMA\n" )
            f.write( "-" * 120 + "\n\n" )

            # Agrupa por família linguística
            families = { }
            for lang_code, lang_info in LANGUAGES.items():
                family = lang_info[ 'family' ]
                if family not in families:
                    families[ family ] = [ ]
                families[ family ].append( lang_code )

            for family, lang_codes in sorted( families.items() ):
                f.write( f"\n{family}:\n" )
                for lang_code in lang_codes:
                    lang_name = LANGUAGES[ lang_code ][ 'name' ]

                    # Conta projetos com este idioma
                    projects_with_lang = [ p for p in self.projects_data if lang_code in p[ 'languages' ] ]
                    count = len( projects_with_lang )

                    if count > 0:
                        # Calcula estatísticas
                        complete = sum(
                            1 for p in projects_with_lang if p[ 'languages' ][ lang_code ][ 'percentage' ] >= 100 )
                        above_90 = sum(
                            1 for p in projects_with_lang if p[ 'languages' ][ lang_code ][ 'percentage' ] >= 90 )
                        total_msgs = sum( p[ 'languages' ][ lang_code ][ 'total' ] for p in projects_with_lang )
                        translated_msgs = sum(
                            p[ 'languages' ][ lang_code ][ 'translated' ] for p in projects_with_lang )
                        avg_completion = (translated_msgs / total_msgs * 100) if total_msgs > 0 else 0

                        f.write( f"  • {lang_name} ({lang_code}): {count} projetos | "
                                 f"{complete} completos | {above_90} com ≥90% | {avg_completion:.1f}% média\n" )
                    else:
                        f.write( f"  • {lang_name} ({lang_code}): 0 projetos\n" )

            # Detalhamento por projeto
            f.write( "\n" + "=" * 120 + "\n" )
            f.write( "DETALHAMENTO COMPLETO POR PROJETO\n" )
            f.write( "=" * 120 + "\n\n" )

            for project in self.projects_data:
                # Marca projetos excelentes
                is_excellent = self._has_all_languages_above_threshold( project )
                marker = "🌟 " if is_excellent else ""

                f.write( f"\n{'─' * 120}\n" )
                f.write( f"{marker}Projeto: {project[ 'name' ]} (v{project[ 'latest_version' ]})\n" )
                if is_excellent:
                    f.write( f"Status: ⭐ EXCELENTE - Todos os 8 idiomas com ≥{THRESHOLD}%\n" )
                f.write( f"{'─' * 120}\n" )

                # Agrupa idiomas por família
                for family, lang_codes in sorted( families.items() ):
                    langs_in_project = [ lc for lc in lang_codes if lc in project[ 'languages' ] ]
                    if langs_in_project:
                        f.write( f"\n  {family}:\n" )
                        for lang_code in langs_in_project:
                            data = project[ 'languages' ][ lang_code ]
                            lang_name = LANGUAGES[ lang_code ][ 'name' ]
                            status = "✓ COMPLETO" if data[ 'percentage' ] >= 100 else "• EM PROGRESSO"
                            f.write( f"    {status} {lang_name}: {data[ 'percentage' ]:.1f}% "
                                     f"({data[ 'translated' ]}/{data[ 'total' ]})\n" )

        console.print( f"\n[green]✓ Relatório TXT salvo em: {REPORT_FILE}[/]" )

    def generate_csv( self ):
        """Gera relatório detalhado em formato CSV"""

        if not self.projects_data:
            return

        with open( REPORT_CSV, 'w', encoding = 'utf-8' ) as f:
            # Cabeçalho
            header = "Projeto,Versão,Idioma,Família Linguística,Traduzidas,Total,Percentual,Status,Projeto Excelente\n"
            f.write( header )

            for project in self.projects_data:
                name = project[ 'name' ]
                version = project[ 'latest_version' ]
                is_excellent = "SIM" if self._has_all_languages_above_threshold( project ) else "NÃO"

                for lang_code, data in project[ 'languages' ].items():
                    lang_name = LANGUAGES[ lang_code ][ 'name' ]
                    family = LANGUAGES[ lang_code ][ 'family' ]

                    # Define status
                    if data[ 'percentage' ] >= 100:
                        status = "Completo"
                    elif data[ 'percentage' ] >= 90:
                        status = "Quase Completo"
                    else:
                        status = "Em Progresso"

                    f.write( f"{name},{version},{lang_name} ({lang_code}),{family},"
                             f"{data[ 'translated' ]},{data[ 'total' ]},{data[ 'percentage' ]:.2f},{status},{is_excellent}\n" )

        console.print( f"[green]✓ Relatório CSV detalhado salvo em: {REPORT_CSV}[/]" )

    def generate_excellent_projects_csv( self ):
        """Gera CSV exclusivo com projetos que têm todos os 8 idiomas ≥90%"""

        if not self.excellent_projects:
            console.print( f"[yellow]⚠ Nenhum projeto com todos os 8 idiomas ≥{THRESHOLD}%[/]" )
            return

        with open( REPORT_EXCELLENT_CSV, 'w', encoding = 'utf-8' ) as f:
            # Cabeçalho
            f.write( "Projeto,Versão,pt_BR_%,es_%,fr_%,de_%,ru_%,zh_CN_%,vi_%,id_%,Média_%\n" )

            for project in sorted( self.excellent_projects, key = lambda x: x[ 'name' ] ):
                name = project[ 'name' ]
                version = project[ 'latest_version' ]
                langs = project[ 'languages' ]

                # Coleta percentuais de cada idioma
                percentages = [ ]
                row_data = [ name, version ]

                for lang_code in [ 'pt_BR', 'es', 'fr', 'de', 'ru', 'zh_CN', 'vi', 'id' ]:
                    pct = langs[ lang_code ][ 'percentage' ]
                    percentages.append( pct )
                    row_data.append( f"{pct:.2f}" )

                # Calcula média
                avg = sum( percentages ) / len( percentages )
                row_data.append( f"{avg:.2f}" )

                f.write( ",".join( row_data ) + "\n" )

        console.print( f"[green]✓ CSV de projetos excelentes salvo em: {REPORT_EXCELLENT_CSV}[/]" )

    def generate_summary_csv( self ):
        """Gera CSV com resumo por idioma"""

        if not self.projects_data:
            return

        with open( REPORT_SUMMARY_CSV, 'w', encoding = 'utf-8' ) as f:
            f.write( "Idioma,Código,Família,Total Projetos,Completos (100%),Quase Completos (≥90%),"
                     "Em Progresso (<90%),Total Mensagens,Mensagens Traduzidas,% Média Conclusão\n" )

            for lang_code, lang_info in sorted( LANGUAGES.items(), key = lambda x: x[ 1 ][ 'family' ] ):
                lang_name = lang_info[ 'name' ]
                family = lang_info[ 'family' ]

                # Filtra projetos com este idioma
                projects_with_lang = [ p for p in self.projects_data if lang_code in p[ 'languages' ] ]

                if projects_with_lang:
                    total_projects = len( projects_with_lang )
                    complete = sum(
                        1 for p in projects_with_lang if p[ 'languages' ][ lang_code ][ 'percentage' ] >= 100 )
                    almost_complete = sum( 1 for p in projects_with_lang
                                           if 90 <= p[ 'languages' ][ lang_code ][ 'percentage' ] < 100 )
                    in_progress = sum(
                        1 for p in projects_with_lang if p[ 'languages' ][ lang_code ][ 'percentage' ] < 90 )

                    total_msgs = sum( p[ 'languages' ][ lang_code ][ 'total' ] for p in projects_with_lang )
                    translated_msgs = sum( p[ 'languages' ][ lang_code ][ 'translated' ] for p in projects_with_lang )
                    avg_completion = (translated_msgs / total_msgs * 100) if total_msgs > 0 else 0

                    f.write( f"{lang_name},{lang_code},{family},{total_projects},{complete},"
                             f"{almost_complete},{in_progress},{total_msgs},{translated_msgs},{avg_completion:.2f}\n" )

        console.print( f"[green]✓ Resumo por idioma salvo em: {REPORT_SUMMARY_CSV}[/]" )

    def display_summary( self ):
        """Exibe resumo visual no console"""

        if not self.projects_data:
            return

        # DESTAQUE: Projetos Excelentes
        if self.excellent_projects:
            excellent_table = Table(
                title = f"🌟 Projetos com TODOS os 8 Idiomas ≥{THRESHOLD}% 🌟",
                show_header = True,
                header_style = "bold green",
                border_style = "green"
            )
            excellent_table.add_column( "Projeto", style = "cyan bold" )
            excellent_table.add_column( "Versão", style = "dim" )
            excellent_table.add_column( "Média %", justify = "right", style = "green" )

            for project in sorted( self.excellent_projects, key = lambda x: x[ 'name' ] )[ :15 ]:
                langs = project[ 'languages' ]
                avg = sum( langs[ lc ][ 'percentage' ] for lc in LANGUAGES.keys() ) / len( LANGUAGES )

                excellent_table.add_row(
                    project[ 'name' ],
                    project[ 'latest_version' ],
                    f"{avg:.1f}%"
                )

            console.print( "\n" )
            console.print( excellent_table )

        # Tabela de resumo por idioma
        table = Table(
            title = "Resumo por Idioma e Família Linguística",
            show_header = True,
            header_style = "bold magenta"
        )
        table.add_column( "Família", style = "cyan" )
        table.add_column( "Idioma", style = "white" )
        table.add_column( "Projetos", justify = "right" )
        table.add_column( "≥90%", justify = "right", style = "yellow" )
        table.add_column( "100%", justify = "right", style = "green" )

        # Agrupa por família
        families = { }
        for lang_code, lang_info in LANGUAGES.items():
            family = lang_info[ 'family' ]
            if family not in families:
                families[ family ] = [ ]
            families[ family ].append( lang_code )

        for family, lang_codes in sorted( families.items() ):
            for i, lang_code in enumerate( lang_codes ):
                lang_name = LANGUAGES[ lang_code ][ 'name' ]
                projects_with_lang = [ p for p in self.projects_data if lang_code in p[ 'languages' ] ]

                if projects_with_lang:
                    total = len( projects_with_lang )
                    above_90 = sum( 1 for p in projects_with_lang
                                    if p[ 'languages' ][ lang_code ][ 'percentage' ] >= 90 )
                    complete = sum( 1 for p in projects_with_lang
                                    if p[ 'languages' ][ lang_code ][ 'percentage' ] >= 100 )

                    family_display = family if i == 0 else ""
                    table.add_row(
                        family_display,
                        f"{lang_name} ({lang_code})",
                        str( total ),
                        str( above_90 ),
                        str( complete )
                    )

        console.print( "\n" )
        console.print( table )

        # Estatísticas gerais
        stats_table = Table( show_header = False, box = None, title = "\nEstatísticas Gerais" )
        stats_table.add_column( "Métrica", style = "bold" )
        stats_table.add_column( "Valor", justify = "right" )

        total_projects = len( self.projects_data )
        excellent_count = len( self.excellent_projects )
        excellent_pct = (excellent_count / total_projects * 100) if total_projects > 0 else 0

        stats_table.add_row( "Total de Projetos Analisados", f"[cyan]{total_projects}[/]" )
        stats_table.add_row( f"Projetos com Todos os 8 Idiomas ≥{THRESHOLD}%",
                             f"[green bold]{excellent_count}[/] [dim]({excellent_pct:.1f}%)[/]" )

        if excellent_count > 0:
            avg_strings = sum(
                sum( p[ 'languages' ][ lc ][ 'total' ] for lc in LANGUAGES.keys() ) / len( LANGUAGES )
                for p in self.excellent_projects
            ) / len( self.excellent_projects )
            stats_table.add_row( "Média de Strings (Projetos Excelentes)", f"[yellow]{avg_strings:.0f}[/]" )

        console.print( "\n" )
        console.print( stats_table )


def main():
    console.print( Panel.fit(
        "[bold magenta]Relatório Multilíngue - Translation Project[/]\n"
        "[italic]Identifica projetos com excelente suporte multilíngue[/]\n\n"
        f"[bold green]Busca projetos com TODOS os 8 idiomas ≥{THRESHOLD}%[/]\n"
        "Idiomas: pt_BR, es, fr, de, ru, zh_CN, vi, id",
        border_style = "magenta"
    ) )

    generator = ReportGenerator()

    # Busca lista de projetos
    projects = generator.fetch_all_projects()
    if not projects:
        console.print( "[red]Nenhum projeto encontrado. Encerrando.[/]" )
        return

    # Analisa projetos
    generator.analyze_projects( projects )

    if not generator.projects_data:
        console.print( "[yellow]Nenhum projeto com os idiomas monitorados foi encontrado.[/]" )
        return

    # Gera relatórios
    generator.generate_report()
    generator.generate_csv()
    generator.generate_excellent_projects_csv()
    generator.generate_summary_csv()

    # Exibe resumo
    generator.display_summary()

    console.print( "\n[bold green]✓ Análise concluída![/]" )


if __name__ == "__main__":
    main()
