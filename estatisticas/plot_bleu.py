#!/usr/bin/env python3
"""
Gera gráfico de barras de BLEU por configuração de contexto
para todos os projetos dentro de metrics_aggregated/, salvando
os resultados em estatisticas/resultados_bleu/.

Uso:
    python plot_bleu.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# ── Paleta ───────────────────────────────────────────────────────────────────
COLORS = { "ctx-0": "#6366f1", "ctx-1": "#22c55e", "ctx-2": "#f59e0b" }
BG = "#0f1117"
GRID = "#1e2130"
TEXT = "#e2e8f0"
SUBTEXT = "#94a3b8"
GAP = 0.4

INPUT_DIR = Path( "metrics_aggregated" )
OUTPUT_DIR = Path( "estatisticas" ) / "barras"


def find_aggregated_csv( project_dir: Path ) -> Path | None:
    candidates = list( project_dir.glob( "*.aggregated.csv" ) )
    if not candidates:
        print( f"  [aviso] Nenhum .aggregated.csv em: {project_dir}; pulando." )
        return None
    if len( candidates ) > 1:
        print( f"  [aviso] Múltiplos CSVs; usando: {candidates[ 0 ].name}" )
    return candidates[ 0 ]


def ctx_level( v: str ) -> str:
    cl = str( v ).strip()
    if cl in ("", "nan"):
        return "ctx-0"
    elif "," not in cl:
        return "ctx-1"
    else:
        return "ctx-2"


def ctx_label( v: str ) -> str:
    cl = str( v ).strip()
    return "none" if cl in ("", "nan") else cl


def build_xs( df: pd.DataFrame ) -> np.ndarray:
    xs = [ ]
    current_x = 0
    prev_order = None
    for _, row in df.iterrows():
        if prev_order is not None and row[ "_order" ] != prev_order:
            current_x += GAP
        xs.append( current_x )
        current_x += 1
        prev_order = row[ "_order" ]
    return np.array( xs )


def plot_project( project_name: str, df: pd.DataFrame, output_dir: Path ) -> None:
    df[ "ctx_level" ] = df[ "context_languages" ].apply( ctx_level )
    df[ "ctx_label" ] = df[ "context_languages" ].apply( ctx_label )
    df[ "_order" ] = df[ "ctx_level" ].map( { "ctx-0": 0, "ctx-1": 1, "ctx-2": 2 } )
    df = df.sort_values( [ "_order", "bleu" ], ascending = [ True, False ] ).reset_index( drop = True )

    xs = build_xs( df )

    # ── Figura ───────────────────────────────────────────────────────────────
    fig, ax = plt.subplots( figsize = (16, 6) )
    fig.patch.set_facecolor( BG )
    ax.set_facecolor( BG )

    # Linha baseline (ctx-0)
    baseline = df[ df[ "ctx_level" ] == "ctx-0" ][ "bleu" ].values[ 0 ]
    ax.axhline( baseline, color = COLORS[ "ctx-0" ], linewidth = 1.2,
                linestyle = "--", alpha = 0.7, zorder = 1 )
    ax.text(
        1.01, baseline,
        f"baseline  {baseline:.1f}",
        color = COLORS[ "ctx-0" ], fontsize = 8,
        ha = "left", va = "center", alpha = 0.9,
        transform = ax.get_yaxis_transform(),
        clip_on = False,
    )

    # Barras
    bar_colors = [ COLORS[ lvl ] for lvl in df[ "ctx_level" ] ]
    bars = ax.bar( xs, df[ "bleu" ], color = bar_colors,
                   width = 0.72, zorder = 2, linewidth = 0 )

    # Eixo X e xlim
    ax.set_xticks( xs )
    ax.set_xticklabels( df[ "ctx_label" ], rotation = 45,
                        ha = "right", fontsize = 8.5, color = TEXT )
    ax.set_xlim( -0.5, xs[ -1 ] + 0.5 )

    # Separadores entre grupos e coleta de group_xs
    group_xs = { }

    for order, grp in df.groupby( "_order", sort = True ):
        lvl = grp[ "ctx_level" ].iloc[ 0 ]
        idxs = grp.index.to_numpy()
        gxs = xs[ idxs ]
        group_xs[ lvl ] = gxs

        if idxs[ -1 ] < len( df ) - 1:
            sep = (xs[ idxs[ -1 ] ] + xs[ idxs[ -1 ] + 1 ]) / 2
            ax.axvline( sep, color = GRID, linewidth = 1.5, zorder = 3 )

    # Linha 1: labels de grupo coloridos
    xlim = ax.get_xlim()
    x_range = xlim[ 1 ] - xlim[ 0 ]
    group_label_names = { "ctx-0": "Sem contexto", "ctx-1": "1 idioma", "ctx-2": "2 idiomas" }

    for lvl, gxs in group_xs.items():
        ax_x = (gxs.mean() - xlim[ 0 ]) / x_range
        ax.text( ax_x, 1.01,
                 group_label_names[ lvl ],
                 ha = "center", va = "bottom", fontsize = 8,
                 color = COLORS[ lvl ], fontweight = "bold",
                 transform = ax.transAxes, clip_on = False )

    # Linha 2: subtítulo
    ax.text(
        0.0, 1.06,
        f"{len( df )} configurações · ordenado de forma decrescente por BLEU dentro de cada nível",
        ha = "left", va = "bottom",
        fontsize = 9, color = SUBTEXT,
        transform = ax.transAxes, clip_on = False,
    )

    # Valor no topo de cada barra
    for bar, val in zip( bars, df[ "bleu" ] ):
        ax.text( bar.get_x() + bar.get_width() / 2,
                 bar.get_height() + 0.2,
                 f"{val:.1f}",
                 ha = "center", va = "bottom",
                 fontsize = 7, color = TEXT, fontweight = "bold" )

    # Grid e estilo
    ax.yaxis.grid( True, color = GRID, linewidth = 0.8, zorder = 0 )
    ax.set_axisbelow( True )
    ax.spines[ : ].set_visible( False )
    ax.tick_params( colors = TEXT, length = 0 )
    ax.yaxis.set_tick_params( labelcolor = SUBTEXT, labelsize = 9 )
    ax.set_ylabel( "BLEU (0 - 100)", color = SUBTEXT, fontsize = 10, labelpad = 8 )

    # Legenda
    patches = [ mpatches.Patch( color = COLORS[ k ], label = k ) for k in COLORS ]
    ax.legend(
        handles = patches,
        loc = "lower right",
        bbox_to_anchor = (1.07, 0.0),
        frameon = True,
        framealpha = 0.15,
        edgecolor = GRID,
        facecolor = BG,
        labelcolor = TEXT,
        fontsize = 9,
    )

    # Título principal
    fig.suptitle(
        f"Gráfico de Barras — BLEU — {project_name}",
        x = 0.01, y = 1.0, ha = "left",
        fontsize = 14, fontweight = "bold", color = TEXT,
    )

    plt.tight_layout()

    output_path = output_dir / f"{project_name}.bleu.png"
    plt.savefig( str( output_path ), dpi = 150,
                 bbox_inches = "tight", facecolor = BG )
    plt.close()
    print( f"  [ok] {output_path}" )


def main():
    if not INPUT_DIR.exists():
        print( f"[erro] Pasta de entrada não encontrada: {INPUT_DIR}" )
        sys.exit( 1 )

    projects = sorted( p for p in INPUT_DIR.iterdir() if p.is_dir() )
    if not projects:
        print( f"[erro] Nenhum projeto encontrado em {INPUT_DIR}" )
        sys.exit( 1 )

    OUTPUT_DIR.mkdir( parents = True, exist_ok = True )

    print( f"Projetos encontrados: {len( projects )}" )
    print( f"Salvando em: {OUTPUT_DIR}\n" )

    for project_dir in projects:
        print( f"→ {project_dir.name}" )

        csv_path = find_aggregated_csv( project_dir )
        if csv_path is None:
            print()
            continue

        df = pd.read_csv( csv_path )

        if "bleu" not in df.columns:
            print( "  [aviso] Coluna 'bleu' não encontrada; pulando.\n" )
            continue

        plot_project( project_dir.name, df, OUTPUT_DIR )
        print()

    print( "Concluído." )


if __name__ == "__main__":
    main()
