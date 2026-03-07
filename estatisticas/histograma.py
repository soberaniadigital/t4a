#!/usr/bin/env python3
"""
Gera histograma de BLEU a partir do CSV agregado de um projeto.

Uso:
    python plot_bleu_histogram.py <caminho_do_projeto>

Exemplo:
    python plot_bleu_histogram.py metrics_aggregated/exif_v0.6.22
"""

import argparse
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description = "Histograma de BLEU por configuração de contexto"
    )
    parser.add_argument(
        "project_dir",
        type = Path,
        help = "Pasta do projeto dentro de metrics_aggregated/",
    )
    parser.add_argument(
        "--bins",
        type = int,
        default = 10,
        help = "Número de bins do histograma (padrão: 10)",
    )
    parser.add_argument(
        "--output",
        type = Path,
        default = None,
        help = "Caminho do PNG de saída (padrão: <project_dir>/<project>.bleu_hist.png)",
    )
    return parser.parse_args()


def find_aggregated_csv( project_dir: Path ) -> Path:
    candidates = list( project_dir.glob( "*.aggregated.csv" ) )
    if not candidates:
        print( f"[erro] Nenhum arquivo .aggregated.csv encontrado em: {project_dir}" )
        sys.exit( 1 )
    if len( candidates ) > 1:
        print( f"[aviso] Múltiplos CSVs encontrados, usando: {candidates[ 0 ].name}" )
    return candidates[ 0 ]


def ctx_level( context_languages: str ) -> str:
    cl = str( context_languages ).strip()
    if cl in ("", "nan"):
        return "ctx-0"
    elif "," not in cl:
        return "ctx-1"
    else:
        return "ctx-2"


def main():
    args = parse_args()

    if not args.project_dir.exists():
        print( f"[erro] Pasta não encontrada: {args.project_dir}" )
        sys.exit( 1 )

    csv_path = find_aggregated_csv( args.project_dir )
    df = pd.read_csv( csv_path )

    if "bleu" not in df.columns:
        print( "[erro] Coluna 'bleu' não encontrada no CSV." )
        sys.exit( 1 )

    project_name = args.project_dir.name
    df[ "ctx_level" ] = df[ "context_languages" ].apply( ctx_level )

    output_path = args.output or args.project_dir / f"{project_name}.bleu_hist.png"

    colors = pio.templates[ "plotly" ].layout.colorway  # fallback seguro
    try:
        colors = pio.templates[ "perplexity" ].layout.colorway
    except Exception:
        pass

    level_colors = {
        "ctx-0": colors[ 0 ],
        "ctx-1": colors[ 1 ],
        "ctx-2": colors[ 2 ],
    }

    fig = go.Figure()

    for level in [ "ctx-0", "ctx-1", "ctx-2" ]:
        subset = df[ df[ "ctx_level" ] == level ][ "bleu" ]
        if subset.empty:
            continue
        fig.add_trace(
            go.Histogram(
                x = subset,
                name = level,
                nbinsx = args.bins,
                marker_color = level_colors[ level ],
                opacity = 0.75,
            )
        )

    fig.update_layout(
        barmode = "overlay",
        title = {
            "text": (
                f"BLEU — {project_name}<br>"
                f"<span style='font-size:16px;font-weight:normal'>"
                f"{len( df )} configurações · distribuição por nível de contexto"
                f"</span>"
            ),
            "y": 0.95,  # empurra o título para baixo, abrindo espaço no topo
            "x": 0.0,
            "xanchor": "left",
            "yanchor": "top",
        },
        legend = dict(
            orientation = "h",
            yanchor = "top",
            y = 1.18,  # acima do título
            xanchor = "left",
            x = 0.0,
        ),
        margin = dict( t = 120 ),  # margem superior para acomodar legenda + título
    )
    fig.update_xaxes( title_text = "BLEU" )
    fig.update_yaxes( title_text = "Frequência" )

    fig.write_image( str( output_path ) )
    print( f"[ok] Histograma salvo em: {output_path}" )


if __name__ == "__main__":
    main()
