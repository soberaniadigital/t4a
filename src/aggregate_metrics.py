# src/aggregate_metrics.py
"""
Agrega métricas por arquivo/projeto a partir dos CSVs gerados pelo run_metrics.

Uso:
    python -m src.aggregate_metrics \
        --input-dir metrics_csv \
        --output-dir metrics_aggregated
"""

import argparse
from pathlib import Path
from typing import List

import pandas as pd
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description = "Agrega métricas por arquivo dentro de cada projeto",
    )

    parser.add_argument(
        "--input-dir",
        "-i",
        type = str,
        default = "metrics_csv",
        help = "Pasta raiz com os CSVs de métricas (padrão: metrics_csv)",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type = str,
        default = "metrics_aggregated",
        help = "Pasta onde serão salvos os CSVs agregados (padrão: metrics_aggregated)",
    )

    return parser.parse_args()


def find_project_dirs( root: Path ) -> List[ Path ]:
    """
    Encontra subpastas de projeto dentro de root.

    Exemplo:
        metrics_csv/aspell_v0.60.8.1
        metrics_csv/bison_v3.5.90
    """
    if not root.exists():
        raise FileNotFoundError( f"Pasta de entrada não encontrada: {root}" )

    # Considera qualquer subdiretório como projeto
    project_dirs = [ p for p in root.iterdir() if p.is_dir() ]
    return sorted( project_dirs )


def aggregate_project( project_dir: Path, output_dir: Path ) -> Path:
    """
    Lê todos os CSVs de um projeto e gera um CSV agregado com médias por arquivo.

    Columns esperadas:
        original, translated, reference, context_languages, strategy, <metricas...>
    """
    console.print( f"\n[bold cyan]📁 Projeto:[/] {project_dir.name}" )

    csv_files = sorted( project_dir.glob( "*.csv" ) )
    if not csv_files:
        console.print( "[yellow]  ⚠️ Nenhum CSV encontrado, pulando[/]" )
        return None

    rows = [ ]

    for csv_path in csv_files:
        df = pd.read_csv( csv_path )

        # Identidade do arquivo
        filename = csv_path.name
        context = str( df[ "context_languages" ].iloc[ 0 ] ) if "context_languages" in df.columns else ""
        strategy = str( df[ "strategy" ].iloc[ 0 ] ) if "strategy" in df.columns else ""

        # Seleciona colunas numéricas (métricas)
        metric_cols = [
            c
            for c in df.columns
            if c not in [ "original", "translated", "reference", "context_languages", "strategy" ]
        ]

        numeric_cols = df[ metric_cols ].select_dtypes( include = [ "number" ] )
        means = numeric_cols.mean( skipna = True )

        row = {
            "file": filename,
            "num_segments": len( df ),
            "context_languages": context,
            "strategy": strategy,
        }
        # Adiciona médias das métricas
        for col, val in means.items():
            row[ col ] = val

        rows.append( row )

    agg_df = pd.DataFrame( rows )

    # Ordena por nome de arquivo
    agg_df = agg_df.sort_values( "file" )

    # Garante pasta de saída do projeto
    project_output_dir = output_dir / project_dir.name
    project_output_dir.mkdir( parents = True, exist_ok = True )

    output_path = project_output_dir / f"{project_dir.name}.aggregated.csv"
    agg_df.to_csv( output_path, index = False )

    # Tabela resumo bonitinha no terminal
    table = Table(
        title = f"Resumo - {project_dir.name}",
        box = box.SIMPLE_HEAVY,
        show_lines = False,
    )
    table.add_column( "Arquivo", style = "cyan", no_wrap = True )
    table.add_column( "Segs", justify = "right" )
    table.add_column( "Ctx", style = "yellow", no_wrap = True )
    table.add_column( "Strategy", style = "magenta", no_wrap = True )
    for col in agg_df.columns:
        if col not in [ "file", "num_segments", "context_languages", "strategy" ]:
            table.add_column( col, justify = "right" )

    for _, r in agg_df.iterrows():
        row = [
            str( r[ "file" ] ),
            str( r[ "num_segments" ] ),
            str( r[ "context_languages" ] ),
            str( r[ "strategy" ] ),
        ]
        for col in agg_df.columns:
            if col not in [ "file", "num_segments", "context_languages", "strategy" ]:
                val = r[ col ]
                row.append( f"{val:.2f}" if pd.notna( val ) else "-" )
        table.add_row( *row )

    console.print( table )
    console.print( f"[green]  ✓ CSV agregado salvo em:[/] {output_path}" )

    return output_path


def main():
    args = parse_arguments()

    input_root = Path( args.input_dir )
    output_root = Path( args.output_dir )
    output_root.mkdir( parents = True, exist_ok = True )

    console.print( "\n" + "=" * 80 )
    console.print( "[bold cyan]📊 AGREGADOR DE MÉTRICAS POR PROJETO[/]" )
    console.print( "=" * 80 + "\n" )

    project_dirs = find_project_dirs( input_root )

    if not project_dirs:
        console.print( f"[red]❌ Nenhum projeto encontrado em {input_root}[/]" )
        raise SystemExit( 1 )

    console.print( f"[cyan]Encontrados {len( project_dirs )} projetos em {input_root}[/]" )

    generated = [ ]
    for project_dir in project_dirs:
        out = aggregate_project( project_dir, output_root )
        if out:
            generated.append( out )

    console.print( "\n" + "=" * 80 )
    console.print( f"[bold green]✅ Agregação concluída![/]" )
    console.print( f"[green]📁 Projetos agregados:[/] {len( generated )}" )
    console.print( f"[green]📂 Pasta de saída:[/] {output_root}\n" )


if __name__ == "__main__":
    main()
