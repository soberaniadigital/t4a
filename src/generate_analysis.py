# src/generate_analysis.py (VERSÃO CORRIGIDA)

import argparse
import math
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
import numpy as np
from rich.console import Console

console = Console()


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser( description = "Gera análise Markdown de CSV agregado" )
    parser.add_argument( "input", type = Path, help = "CSV agregado" )
    parser.add_argument( "--output", "-o", type = Path, default = None, help = "Arquivo Markdown" )
    parser.add_argument( "--title", "-t", default = "Análise de Resultados", help = "Título" )
    return parser.parse_args()


def extract_project_name( csv_path: Path ) -> str:
    return csv_path.stem.replace( ".aggregated", "" )


def get_metric_columns( df: pd.DataFrame ) -> List[ str ]:
    """
    Detecta automaticamente colunas de métricas (numéricas, excluindo metadados)
    """
    exclude_cols = [ "file", "num_segments", "context_languages", "strategy", "num_segments" ]
    metric_cols = [
        c for c in df.columns
        if df[ c ].dtype in [ 'float64', 'float32', 'int64' ] and c not in exclude_cols
    ]
    return sorted( metric_cols )


def group_by_context_level( df: pd.DataFrame ) -> Dict[ str, List[ Dict ] ]:
    """
    Agrupa por nível de contexto (ctx-0, ctx-1, etc.)
    """
    groups = { }

    for _, row in df.iterrows():
        filename = row[ "file" ]
        if "ctx-" in str( filename ):
            # Extrai ctx-X do nome do arquivo
            ctx_match = re.search( r'ctx-(\d+)', str( filename ) )
            if ctx_match:
                ctx_level = ctx_match.group( 1 )
                key = f"ctx-{ctx_level}"

                if key not in groups:
                    groups[ key ] = [ ]

                # Adiciona linha para TODAS as métricas detectadas
                row_data = { "file": filename }
                for col in get_metric_columns( df ):
                    row_data[ col ] = row.get( col, np.nan )

                row_data[ "context_languages" ] = row[ "context_languages" ]
                row_data[ "num_segments" ] = row[ "num_segments" ]

                groups[ key ].append( row_data )

    return groups


def calculate_deltas( groups: Dict[ str, List[ Dict ] ], metric_name: str ) -> Dict[ str, Dict ]:
    """
    Calcula deltas para uma métrica específica
    """
    # Baseline ctx-0
    ctx_0_scores = [ g[ metric_name ] for g in groups.get( "ctx-0", [ ] ) if not pd.isna( g[ metric_name ] ) ]
    ctx_0_mean = np.mean( ctx_0_scores ) if ctx_0_scores else np.nan

    deltas = { }
    for level, experiments in groups.items():
        scores = [ e[ metric_name ] for e in experiments if not pd.isna( e[ metric_name ] ) ]
        if not scores:
            continue

        mean = np.mean( scores )

        delta_vs_0 = mean - ctx_0_mean if not pd.isna( ctx_0_mean ) else np.nan

        # Delta vs anterior
        prev_level = f"ctx-{int( level.split( '-' )[ 1 ] ) - 1}"
        prev_scores = [ e[ metric_name ] for e in groups.get( prev_level, [ ] ) if not pd.isna( e[ metric_name ] ) ]
        delta_vs_prev = mean - np.mean( prev_scores ) if prev_scores else np.nan

        # MELHOR = MENOR para TER, MAIOR para outras
        if metric_name.lower() == "ter":
            # TER: menor é melhor
            best_exp = min( experiments,
                            key = lambda x: x[ metric_name ] if not pd.isna( x[ metric_name ] ) else np.inf )
        else:
            # Outras: maior é melhor
            best_exp = max( experiments,
                            key = lambda x: x[ metric_name ] if not pd.isna( x[ metric_name ] ) else -np.inf )

        best_score = best_exp[ metric_name ]
        best_ctx = best_exp[ "context_languages" ]

        deltas[ level ] = {
            "mean": mean,
            "delta_vs_0": delta_vs_0,
            "delta_vs_prev": delta_vs_prev,
            "best_context": best_ctx,
            "best_score": best_score
        }

    return deltas


def generate_markdown_table( deltas: Dict[ str, Dict ], project_name: str, metric_name: str,
                             is_lower_better: bool = False ) -> str:
    """Gera tabela Markdown"""
    direction = "(menor = melhor)" if is_lower_better else "(maior = melhor)"

    md = f"\n\n## **{metric_name}** {direction} - {project_name}\n\n"

    md += "| Nível | Média | Δ vs ctx-0 | Δ vs ctx-1 | Melhor contexto |\n"
    md += "|-------|-------|------------|------------|-----------------|\n"

    for level in sorted( deltas.keys() ):
        d = deltas[ level ]

        # Formatação com destaque
        mean_fmt = f"**{d[ 'mean' ]:.2f}**"
        delta_0_fmt = f"**{d[ 'delta_vs_0' ]:.2f}**" if abs( d[ 'delta_vs_0' ] ) > 0.1 else f"{d[ 'delta_vs_0' ]:.2f}"
        delta_prev_fmt = f"**{d[ 'delta_vs_prev' ]:.2f}**" if abs(
            d[ 'delta_vs_prev' ] ) > 0.1 else f"{d[ 'delta_vs_prev' ]:.2f}"
        best_fmt = f"**{d[ 'best_score' ]:.2f}**"

        md += f"| {level} | {mean_fmt} | {delta_0_fmt} | {delta_prev_fmt} | {d[ 'best_context' ]} ({best_fmt}) |\n"

    # Observação automática
    if deltas:
        overall_gain = deltas[ list( deltas.keys() )[ -1 ] ][ 'delta_vs_0' ]
        if not pd.isna( overall_gain ):
            if is_lower_better:
                if overall_gain < 0:
                    gain_desc = f"**redução de {abs( overall_gain ):.2f}** pontos"
                else:
                    gain_desc = f"**aumento de {overall_gain:.2f}** pontos"
            else:
                if overall_gain > 0:
                    gain_desc = f"**ganho de {overall_gain:.2f}** pontos"
                else:
                    gain_desc = f"**variação de {overall_gain:.2f}** pontos"

            md += f"\n*Observação*: Contexto proporciona {gain_desc} sobre baseline.\n"

    return md


def generate_full_analysis( df: pd.DataFrame, project_name: str ) -> str:
    """Gera análise completa"""
    md = f"# {project_name.upper()}\n\n"

    # Detecta métricas automaticamente
    metric_cols = get_metric_columns( df )

    # Mapeamento direção (menor=melhor)
    lower_better = { "ter": True }

    for metric in metric_cols:
        try:
            groups = group_by_context_level( df )
            if not groups:
                continue

            deltas = calculate_deltas( groups, metric )
            if deltas:
                md += generate_markdown_table( deltas, project_name, metric, lower_better.get( metric, False ) )
        except Exception as e:
            console.print( f"[yellow]⚠️ Erro na métrica {metric}: {e}[/]" )
            continue

    return md


def main():
    args = parse_arguments()

    csv_path = args.input
    if not csv_path.exists():
        console.print( f"[red]❌ Arquivo não encontrado: {csv_path}[/]" )
        raise SystemExit( 1 )

    project_name = extract_project_name( csv_path )
    output_path = args.output or Path( f"{project_name}_analysis.md" )

    console.print( f"[bold cyan]📊 Gerando análise para:[/] {project_name}" )
    console.print( f"[cyan]Métricas detectadas:[/] {get_metric_columns( pd.read_csv( csv_path ) )}" )

    df = pd.read_csv( csv_path )

    analysis_md = generate_full_analysis( df, project_name )

    output_path.write_text( analysis_md, encoding = "utf-8" )

    console.print( f"[green]✅ Análise salva em:[/] {output_path}" )

    console.print( "\n" + "=" * 80 )
    console.print( "[bold cyan]PREVIEW:[/]" )
    console.print( analysis_md[ :1500 ] + "..." )


if __name__ == "__main__":
    import re  # Necessário para regex

    main()
