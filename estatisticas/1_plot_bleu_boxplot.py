#!/usr/bin/env python3
"""
Gera boxplot de BLEU por nível de contexto para todos os projetos
dentro de metrics_csv/, salvando os resultados em
estatisticas/boxplot/.

Também salva um CSV com a estatística descritiva de cada arquivo
(experimento) em estatisticas/boxplot/bleu_descritiva.csv.

Uso:
    python plot_bleu_boxplot.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# ── Paleta ───────────────────────────────────────────────────────────────────
COLORS  = { "ctx-0": "#6366f1", "ctx-1": "#22c55e", "ctx-2": "#f59e0b" }
BG      = "#0f1117"
GRID    = "#1e2130"
TEXT    = "#e2e8f0"
SUBTEXT = "#94a3b8"

CTX_ORDER       = [ "ctx-0", "ctx-1", "ctx-2" ]
CTX_LABEL_NAMES = { "ctx-0": "Sem contexto", "ctx-1": "1 idioma", "ctx-2": "2 idiomas" }

INPUT_DIR  = Path( "metrics_csv" )
OUTPUT_DIR = Path( "estatisticas" ) / "boxplot"


def ctx_level( v: str ) -> str:
    cl = str( v ).strip()
    if cl in ("", "nan"):
        return "ctx-0"
    elif "," not in cl:
        return "ctx-1"
    else:
        return "ctx-2"


def load_segments( project_dir: Path ) -> pd.DataFrame:
    frames = []
    for path in sorted( project_dir.glob( "*.csv" ) ):
        try:
            df = pd.read_csv( path )
        except Exception as e:
            print( f"  [aviso] Ignorando {path.name}: {e}" )
            continue

        if "bleu" not in df.columns:
            continue

        if "context_languages" not in df.columns:
            df[ "context_languages" ] = ""

        df[ "ctx_level" ] = df[ "context_languages" ].apply( ctx_level )
        df[ "arquivo" ]   = path.stem
        frames.append( df[ [ "bleu", "ctx_level", "context_languages", "arquivo" ] ] )

    if not frames:
        return pd.DataFrame( columns = [ "bleu", "ctx_level", "context_languages", "arquivo" ] )

    return pd.concat( frames, ignore_index = True ).dropna( subset = [ "bleu" ] )


def compute_stats( df: pd.DataFrame ) -> list[ dict ]:
    rows = []
    for arquivo, grp in df.groupby( "arquivo", sort = True ):
        values   = grp[ "bleu" ]
        ctx_lvl  = grp[ "ctx_level" ].iloc[ 0 ]
        ctx_lang = str( grp[ "context_languages" ].iloc[ 0 ] ).strip()
        q1       = float( values.quantile( 0.25 ) )
        q3       = float( values.quantile( 0.75 ) )
        rows.append( {
            "arquivo":          arquivo,
            "ctx_level":        ctx_lvl,
            "ctx_label":        CTX_LABEL_NAMES.get( ctx_lvl, ctx_lvl ),
            "idioma_contexto":  "" if ctx_lang in ("", "nan") else ctx_lang,
            "n":                len( values ),
            "media":            round( values.mean(),   4 ),
            "mediana":          round( values.median(), 4 ),
            "desvio_padrao":    round( values.std(),    4 ),
            "variancia":        round( values.var(),    4 ),
            "minimo":           round( values.min(),    4 ),
            "q1":               round( q1,              4 ),
            "q3":               round( q3,              4 ),
            "maximo":           round( values.max(),    4 ),
            "iqr":              round( q3 - q1,         4 ),
            "zeros":            int( ( values == 0 ).sum() ),
            "pct_zeros":        round( ( values == 0 ).mean() * 100, 2 ),
        } )
    return rows


def style_boxplot( bp: dict, colors: list ) -> None:
    for patch, color in zip( bp[ "boxes" ], colors ):
        patch.set_facecolor( color )
        patch.set_alpha( 0.80 )
        patch.set_linewidth( 0 )

    for element in bp[ "medians" ]:
        element.set( color = TEXT, linewidth = 1.8 )

    for element in bp[ "whiskers" ] + bp[ "caps" ]:
        element.set( color = SUBTEXT, linewidth = 1.0, linestyle = "-" )

    for flier in bp[ "fliers" ]:
        flier.set(
            marker = "o", markerfacecolor = SUBTEXT,
            markeredgecolor = "none", markersize = 3, alpha = 0.5,
        )


def plot_project( project_name: str, df: pd.DataFrame, output_dir: Path ) -> None:
    present = [ lvl for lvl in CTX_ORDER if lvl in df[ "ctx_level" ].values ]
    if not present:
        print( f"  [aviso] Nenhum ctx_level reconhecido; pulando." )
        return

    groups   = [ df[ df[ "ctx_level" ] == lvl ][ "bleu" ].values for lvl in present ]
    colors   = [ COLORS[ lvl ] for lvl in present ]
    x_pos    = list( range( 1, len( present ) + 1 ) )
    baseline = float( np.median( groups[ 0 ] ) )

    fig, ax = plt.subplots( figsize = (10, 6) )
    fig.patch.set_facecolor( BG )
    ax.set_facecolor( BG )

    ax.axhline(
        baseline, color = COLORS[ "ctx-0" ],
        linewidth = 1.2, linestyle = "--", alpha = 0.7, zorder = 1,
    )
    ax.text(
        1.01, baseline,
        f"baseline  {baseline:.1f}",
        color = COLORS[ "ctx-0" ], fontsize = 8,
        ha = "left", va = "center", alpha = 0.9,
        transform = ax.get_yaxis_transform(),
        clip_on = False,
    )

    bp = ax.boxplot(
        groups,
        positions    = x_pos,
        patch_artist = True,
        showfliers   = True,
        widths       = 0.55,
        zorder       = 2,
    )
    style_boxplot( bp, colors )

    ax.set_xticks( x_pos )
    ax.set_xticklabels(
        [ CTX_LABEL_NAMES[ lvl ] for lvl in present ],
        fontsize = 9, color = TEXT,
    )
    ax.set_xlim( 0.3, len( present ) + 0.7 )

    xlim    = ax.get_xlim()
    x_range = xlim[ 1 ] - xlim[ 0 ]
    for pos, lvl in zip( x_pos, present ):
        ax_x = ( pos - xlim[ 0 ] ) / x_range
        ax.text(
            ax_x, 1.01,
            CTX_LABEL_NAMES[ lvl ],
            ha = "center", va = "bottom",
            fontsize = 8, color = COLORS[ lvl ], fontweight = "bold",
            transform = ax.transAxes, clip_on = False,
        )

    counts_str = " · ".join(
        f"{CTX_LABEL_NAMES[ lvl ]}: n={len( g )}"
        for lvl, g in zip( present, groups )
    )
    ax.text(
        0.0, 1.06,
        counts_str,
        ha = "left", va = "bottom",
        fontsize = 9, color = SUBTEXT,
        transform = ax.transAxes, clip_on = False,
    )

    ax.yaxis.grid( True, color = GRID, linewidth = 0.8, zorder = 0 )
    ax.set_axisbelow( True )
    ax.spines[ : ].set_visible( False )
    ax.tick_params( colors = TEXT, length = 0 )
    ax.yaxis.set_tick_params( labelcolor = SUBTEXT, labelsize = 9 )
    ax.set_ylabel( "BLEU (0 - 100)", color = SUBTEXT, fontsize = 10, labelpad = 8 )

    patches = [ mpatches.Patch( color = COLORS[ k ], label = k ) for k in CTX_ORDER ]
    ax.legend(
        handles        = patches,
        loc            = "lower right",
        bbox_to_anchor = ( 1.07, 0.0 ),
        frameon        = True,
        framealpha     = 0.15,
        edgecolor      = GRID,
        facecolor      = BG,
        labelcolor     = TEXT,
        fontsize       = 9,
    )

    fig.suptitle(
        f"Boxplot — BLEU — {project_name}",
        x = 0.01, y = 1.0, ha = "left",
        fontsize = 14, fontweight = "bold", color = TEXT,
    )

    plt.tight_layout()

    output_path = output_dir / f"{project_name}.bleu.boxplot.png"
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

    all_stats = []

    for project_dir in projects:
        print( f"→ {project_dir.name}" )

        df = load_segments( project_dir )
        if df.empty:
            print( "  [aviso] Sem dados válidos; pulando.\n" )
            continue

        all_stats.extend( compute_stats( df ) )
        plot_project( project_dir.name, df, OUTPUT_DIR )
        print()

    if all_stats:
        csv_path = OUTPUT_DIR / "bleu_descritiva.csv"
        pd.DataFrame( all_stats ).to_csv( csv_path, index = False )
        print( f"[ok] CSV salvo em: {csv_path}" )

    print( "Concluído." )


if __name__ == "__main__":
    main()
