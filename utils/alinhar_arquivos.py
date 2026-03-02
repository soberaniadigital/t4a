import os
from pathlib import Path
from typing import Dict, Set, List, Tuple
import polib
from collections import defaultdict

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
DOWNLOAD_ROOT = os.path.join( DATA_ROOT, 'translations_download' )
FILTERED_ROOT = os.path.join( DATA_ROOT, 'translations_filtered' )

# Idiomas monitorados
LANGUAGES = [ 'pt_BR', 'es', 'fr', 'de', 'ru', 'zh_CN', 'vi', 'id' ]

console = Console()


class TranslationIntersector:
    """Encontra strings traduzidas em comum entre todos os idiomas"""

    def __init__( self ):
        self.projects_stats = [ ]

    def find_project_folders( self ) -> List[ Path ]:
        """Encontra todas as pastas de projetos baixados"""
        download_path = Path( DOWNLOAD_ROOT )

        if not download_path.exists():
            console.print( f"[red]Pasta de downloads não encontrada: {DOWNLOAD_ROOT}[/]" )
            return [ ]

        # Lista todas as pastas (ignora arquivos como download_log.txt)
        project_folders = [
            folder for folder in download_path.iterdir()
            if folder.is_dir()
        ]

        return sorted( project_folders )

    def find_po_files( self, project_folder: Path ) -> Dict[ str, Path ]:
        """
        Encontra arquivos .po para cada idioma em uma pasta de projeto
        Retorna: dict com {lang_code: Path}
        """
        po_files = { }

        for po_file in project_folder.glob( '*.po' ):
            filename = po_file.name

            # Tenta identificar o idioma no nome do arquivo
            for lang_code in LANGUAGES:
                if f'.{lang_code}.po' in filename:
                    po_files[ lang_code ] = po_file
                    break

        return po_files

    def get_translated_msgids( self, po_file_path: Path ) -> Set[ str ]:
        """
        Extrai msgids que estão traduzidos (msgstr não vazio) de um arquivo .po
        """
        try:
            po = polib.pofile( str( po_file_path ) )
            translated = set()

            for entry in po:
                # Ignora entradas obsoletas e não traduzidas
                if not entry.obsolete and entry.msgstr and entry.msgstr.strip():
                    # Usa msgid como identificador único
                    translated.add( entry.msgid )

            return translated
        except Exception as e:
            console.print( f"[red]Erro ao ler {po_file_path.name}: {e}[/]" )
            return set()

    def find_common_translations( self, project_folder: Path ) -> Dict:
        """
        Encontra strings traduzidas em comum entre todos os 8 idiomas
        """
        project_name = project_folder.name

        # Encontra arquivos .po para cada idioma
        po_files = self.find_po_files( project_folder )

        # Verifica se tem todos os 8 idiomas
        if len( po_files ) != len( LANGUAGES ):
            missing = set( LANGUAGES ) - set( po_files.keys() )
            console.print( f"[yellow]⚠ {project_name}: Faltando idiomas {missing}[/]" )
            return None

        # Carrega strings traduzidas de cada idioma
        translated_by_lang = { }

        for lang_code, po_path in po_files.items():
            translated_by_lang[ lang_code ] = self.get_translated_msgids( po_path )

        # Calcula interseção (strings traduzidas em TODOS os idiomas)
        common_msgids = set.intersection( *translated_by_lang.values() )

        # Estatísticas
        total_per_lang = { lang: len( msgids ) for lang, msgids in translated_by_lang.items() }

        return {
            'project_name': project_name,
            'project_folder': project_folder,
            'po_files': po_files,
            'common_msgids': common_msgids,
            'common_count': len( common_msgids ),
            'total_per_lang': total_per_lang,
            'translated_by_lang': translated_by_lang
        }

    def create_filtered_po_files( self, project_data: Dict ):
        """
        Cria novos arquivos .po contendo apenas as strings comuns
        """
        project_name = project_data[ 'project_name' ]
        common_msgids = project_data[ 'common_msgids' ]
        po_files = project_data[ 'po_files' ]

        if len( common_msgids ) == 0:
            console.print( f"[yellow]⚠ {project_name}: Nenhuma string comum, pulando...[/]" )
            return False

        # Cria pasta de destino
        output_folder = Path( FILTERED_ROOT ) / project_name
        output_folder.mkdir( parents = True, exist_ok = True )

        # Processa cada idioma
        for lang_code, original_po_path in po_files.items():
            try:
                # Carrega arquivo original
                po = polib.pofile( str( original_po_path ) )

                # Cria novo arquivo PO apenas com strings comuns
                filtered_po = polib.POFile()

                # Copia metadados
                filtered_po.metadata = po.metadata.copy()

                # Adiciona comentário indicando o filtro
                filtered_po.metadata[ 'X-Filtered-By' ] = 'Translation Intersector'
                filtered_po.metadata[ 'X-Original-Entries' ] = str( len( po ) )
                filtered_po.metadata[ 'X-Filtered-Entries' ] = str( len( common_msgids ) )

                # Adiciona apenas entradas comuns
                for entry in po:
                    if entry.msgid in common_msgids:
                        # Cria nova entrada (cópia)
                        new_entry = polib.POEntry(
                            msgid = entry.msgid,
                            msgstr = entry.msgstr,
                            msgid_plural = entry.msgid_plural,
                            msgstr_plural = entry.msgstr_plural,
                            occurrences = entry.occurrences,
                            comment = entry.comment,
                            tcomment = entry.tcomment,
                            flags = entry.flags
                        )
                        filtered_po.append( new_entry )

                # Salva arquivo filtrado
                output_path = output_folder / original_po_path.name
                filtered_po.save( str( output_path ) )

            except Exception as e:
                console.print( f"[red]Erro ao criar arquivo filtrado para {lang_code}: {e}[/]" )
                return False

        return True

    def process_all_projects( self ):
        """Processa todos os projetos baixados"""

        project_folders = self.find_project_folders()

        if not project_folders:
            console.print( "[yellow]Nenhuma pasta de projeto encontrada[/]" )
            return

        console.print( f"\n[cyan]Encontradas {len( project_folders )} pastas de projetos[/]\n" )

        progress = Progress(
            SpinnerColumn(),
            TextColumn( "[bold blue]{task.description}" ),
            BarColumn( bar_width = None ),
            TextColumn( "[progress.percentage]{task.percentage:>3.0f}%" ),
            TextColumn( "•" ),
            TextColumn( "[green]{task.completed}/{task.total}" ),
            TimeElapsedColumn(),
            console = console
        )

        with progress:
            task_id = progress.add_task(
                "[cyan]Processando projetos...",
                total = len( project_folders )
            )

            for project_folder in project_folders:
                # Encontra strings comuns
                project_data = self.find_common_translations( project_folder )

                if project_data:
                    # Cria arquivos filtrados
                    success = self.create_filtered_po_files( project_data )

                    if success:
                        self.projects_stats.append( project_data )

                progress.advance( task_id )

    def generate_report( self ):
        """Gera relatório com estatísticas"""

        if not self.projects_stats:
            console.print( "[yellow]Nenhum projeto processado com sucesso[/]" )
            return

        report_path = Path( FILTERED_ROOT ) / 'intersection_report.txt'

        # Ordena por quantidade de strings comuns (decrescente)
        self.projects_stats.sort( key = lambda x: x[ 'common_count' ], reverse = True )

        with open( report_path, 'w', encoding = 'utf-8' ) as f:
            f.write( "=" * 120 + "\n" )
            f.write( "RELATÓRIO DE INTERSEÇÃO DE TRADUÇÕES\n" )
            f.write( "Strings traduzidas simultaneamente em todos os 8 idiomas\n" )
            f.write( "=" * 120 + "\n\n" )

            # Resumo geral
            total_projects = len( self.projects_stats )
            total_common = sum( p[ 'common_count' ] for p in self.projects_stats )
            avg_common = total_common / total_projects if total_projects > 0 else 0

            f.write( "RESUMO GERAL\n" )
            f.write( "-" * 120 + "\n" )
            f.write( f"Total de Projetos Processados: {total_projects}\n" )
            f.write( f"Total de Strings Comuns (soma): {total_common}\n" )
            f.write( f"Média de Strings Comuns por Projeto: {avg_common:.1f}\n\n" )

            # Top projetos com mais strings comuns
            f.write( "=" * 120 + "\n" )
            f.write( "TOP PROJETOS POR STRINGS COMUNS\n" )
            f.write( "=" * 120 + "\n\n" )

            for i, project in enumerate( self.projects_stats[ :20 ], 1 ):
                f.write( f"\n{i}. {project[ 'project_name' ]}\n" )
                f.write( "-" * 120 + "\n" )
                f.write( f"   Strings Comuns (todos os idiomas): {project[ 'common_count' ]}\n\n" )

                f.write( "   Strings traduzidas por idioma:\n" )
                for lang in LANGUAGES:
                    count = project[ 'total_per_lang' ].get( lang, 0 )
                    percentage = (project[ 'common_count' ] / count * 100) if count > 0 else 0
                    f.write( f"     • {lang}: {count} strings ({percentage:.1f}% são comuns)\n" )

                # Calcula taxa de aproveitamento
                max_strings = max( project[ 'total_per_lang' ].values() )
                efficiency = (project[ 'common_count' ] / max_strings * 100) if max_strings > 0 else 0
                f.write( f"\n   Taxa de Aproveitamento: {efficiency:.1f}% "
                         f"({project[ 'common_count' ]}/{max_strings} do maior idioma)\n" )

            # Detalhamento completo
            f.write( "\n\n" + "=" * 120 + "\n" )
            f.write( "DETALHAMENTO COMPLETO\n" )
            f.write( "=" * 120 + "\n\n" )

            for project in self.projects_stats:
                f.write( f"\n{'─' * 120}\n" )
                f.write( f"Projeto: {project[ 'project_name' ]}\n" )
                f.write( f"{'─' * 120}\n" )
                f.write( f"Strings comuns: {project[ 'common_count' ]}\n\n" )

                f.write( "Distribuição por idioma:\n" )
                for lang in LANGUAGES:
                    count = project[ 'total_per_lang' ].get( lang, 0 )
                    f.write( f"  {lang}: {count} strings\n" )

        console.print( f"\n[green]✓ Relatório salvo em: {report_path}[/]" )

    def generate_csv_report( self ):
        """Gera relatório CSV com estatísticas"""

        if not self.projects_stats:
            return

        csv_path = Path( FILTERED_ROOT ) / 'intersection_stats.csv'

        with open( csv_path, 'w', encoding = 'utf-8' ) as f:
            # Cabeçalho
            header = [ 'Projeto', 'Strings_Comuns' ]
            for lang in LANGUAGES:
                header.append( f'{lang}_Total' )
            header.append( 'Taxa_Aproveitamento_%' )
            f.write( ','.join( header ) + '\n' )

            # Dados
            for project in self.projects_stats:
                row = [
                    project[ 'project_name' ],
                    str( project[ 'common_count' ] )
                ]

                max_strings = max( project[ 'total_per_lang' ].values() )

                for lang in LANGUAGES:
                    row.append( str( project[ 'total_per_lang' ].get( lang, 0 ) ) )

                efficiency = (project[ 'common_count' ] / max_strings * 100) if max_strings > 0 else 0
                row.append( f"{efficiency:.2f}" )

                f.write( ','.join( row ) + '\n' )

        console.print( f"[green]✓ CSV salvo em: {csv_path}[/]" )

    def display_summary( self ):
        """Exibe resumo visual no console"""

        if not self.projects_stats:
            return

        # Top 15 projetos
        table = Table(
            title = "Top 15 Projetos - Maior Interseção de Traduções",
            show_header = True,
            header_style = "bold magenta"
        )
        table.add_column( "Projeto", style = "cyan" )
        table.add_column( "Strings Comuns", justify = "right", style = "green bold" )
        table.add_column( "Maior Idioma", justify = "right" )
        table.add_column( "Taxa Aproveit.", justify = "right", style = "yellow" )

        for project in self.projects_stats[ :15 ]:
            max_strings = max( project[ 'total_per_lang' ].values() )
            efficiency = (project[ 'common_count' ] / max_strings * 100) if max_strings > 0 else 0

            table.add_row(
                project[ 'project_name' ],
                str( project[ 'common_count' ] ),
                str( max_strings ),
                f"{efficiency:.1f}%"
            )

        console.print( "\n" )
        console.print( table )

        # Estatísticas gerais
        stats_table = Table( show_header = False, box = None, title = "\nEstatísticas Gerais" )
        stats_table.add_column( "Métrica", style = "bold" )
        stats_table.add_column( "Valor", justify = "right" )

        total_projects = len( self.projects_stats )
        total_common = sum( p[ 'common_count' ] for p in self.projects_stats )
        avg_common = total_common / total_projects if total_projects > 0 else 0

        # Projeto com mais strings comuns
        best_project = self.projects_stats[ 0 ]

        stats_table.add_row( "Total de Projetos", f"[cyan]{total_projects}[/]" )
        stats_table.add_row( "Total de Strings Comuns (soma)", f"[green]{total_common:,}[/]" )
        stats_table.add_row( "Média por Projeto", f"[yellow]{avg_common:.1f}[/]" )
        stats_table.add_row( "Projeto com Mais Strings",
                             f"[magenta]{best_project[ 'project_name' ]}[/] ({best_project[ 'common_count' ]})" )

        console.print( "\n" )
        console.print( stats_table )

        console.print( f"\n[bold green]📁 Arquivos filtrados salvos em: {FILTERED_ROOT}[/]" )


def main():
    console.print( Panel.fit(
        "[bold magenta]Intersector de Traduções[/]\n"
        "[italic]Encontra strings traduzidas simultaneamente em todos os 8 idiomas[/]\n\n"
        "Para cada projeto, identifica o maior subconjunto comum e cria arquivos .po filtrados",
        border_style = "magenta"
    ) )

    # Verifica se polib está instalado
    try:
        import polib
    except ImportError:
        console.print( "[red]Erro: Biblioteca 'polib' não encontrada[/]" )
        console.print( "[yellow]Instale com: pip install polib[/]" )
        return

    intersector = TranslationIntersector()

    # Processa todos os projetos
    intersector.process_all_projects()

    if not intersector.projects_stats:
        console.print( "\n[yellow]Nenhum projeto processado com sucesso[/]" )
        return

    # Gera relatórios
    intersector.generate_report()
    intersector.generate_csv_report()

    # Exibe resumo
    intersector.display_summary()

    console.print( "\n[bold green]✓ Processamento concluído![/]" )


if __name__ == "__main__":
    main()
