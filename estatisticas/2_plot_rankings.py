#!/usr/bin/env python3
"""
Análise de ranking de contextos por projeto.

Para cada projeto × estratégia:
  - Ranqueia os idiomas de ctx-1 e pares de ctx-2 pelo BLEU
  - Conta pódios (1º, 2º, 3º lugar) de cada idioma entre todos os projetos
  - Calcula delta de BLEU relativo ao baseline (ctx-0)
  - Gera heatmap projeto × idioma

Saída em: estatisticas/rankings/

Uso:
    python plot_rankings.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors

# ── Paleta ───────────────────────────────────────────────────────────────────
COLORS = { "ctx-0": "#6366f1", "ctx-1": "#22c55e", "ctx-2": "#f59e0b" }
PODIUM = { 1: "#f59e0b", 2: "#94a3b8", 3: "#b45309" }  # ouro, prata, bronze
BG = "#0f1117"
GRID = "#1e2130"
TEXT = "#e2e8f0"
SUBTEXT = "#94a3b8"

INPUT_DIR = Path( "metrics_aggregated" )
OUTPUT_DIR = Path( "estatisticas" ) / "rankings"


def ctx_level( v: str ) -> str:
    cl = str( v ).strip()
    if cl in ("", "nan"):
        return "ctx-0"
    elif "," not in cl:
        return "ctx-1"
    else:
        return "ctx-2"


def load_all() -> pd.DataFrame:
    frames = [ ]
    for csv_path in sorted( INPUT_DIR.rglob( "*.aggregated.csv" ) ):
        try:
            df = pd.read_csv( csv_path )
        except Exception as e:
            print( f"  [aviso] {csv_path.name}: {e}" )
            continue
        if "bleu" not in df.columns:
            continue
        if "context_languages" not in df.columns:
            df[ "context_languages" ] = ""
        if "strategy" not in df.columns:
            df[ "strategy" ] = "unknown"
        df[ "project" ] = csv_path.parent.name
        df[ "ctx_level" ] = df[ "context_languages" ].apply( ctx_level )
        df[ "ctx_lang" ] = df[ "context_languages" ].apply( normalize_ctx_lang )
        frames.append( df[ [ "project", "strategy", "ctx_level", "ctx_lang", "bleu" ] ] )

    if not frames:
        print( "[erro] Nenhum aggregated.csv encontrado." )
        sys.exit( 1 )

    return pd.concat( frames, ignore_index = True ).dropna( subset = [ "bleu" ] )


def build_rankings( data: pd.DataFrame, level: str ) -> pd.DataFrame:
    """
    Para cada projeto × estratégia, ranqueia os idiomas/pares de 'level'
    pelo BLEU. Retorna DataFrame com colunas:
        project, strategy, ctx_lang, bleu, baseline_bleu, delta, rank
    """
    subset = data[ data[ "ctx_level" ] == level ].copy()
    baseline = (
        data[ data[ "ctx_level" ] == "ctx-0" ]
        .groupby( [ "project", "strategy" ] )[ "bleu" ]
        .mean()
        .reset_index()
        .rename( columns = { "bleu": "baseline_bleu" } )
    )

    subset = subset.merge( baseline, on = [ "project", "strategy" ], how = "left" )
    subset[ "delta" ] = subset[ "bleu" ] - subset[ "baseline_bleu" ]

    # Rank dentro de cada projeto × estratégia (1 = melhor BLEU)
    subset[ "rank" ] = (
        subset.groupby( [ "project", "strategy" ] )[ "bleu" ]
        .rank( method = "min", ascending = False )
        .astype( int )
    )

    return subset.sort_values( [ "project", "strategy", "rank" ] ).reset_index( drop = True )


def podium_counts( rankings: pd.DataFrame, top_n: int = 3 ) -> pd.DataFrame:
    """Conta quantas vezes cada idioma ficou em cada posição (1..top_n)."""
    rows = [ ]
    for pos in range( 1, top_n + 1 ):
        counts = (
            rankings[ rankings[ "rank" ] == pos ]
            .groupby( "ctx_lang" )
            .size()
            .reset_index( name = f"pos_{pos}" )
        )
        rows.append( counts.set_index( "ctx_lang" ) )

    result = pd.concat( rows, axis = 1 ).fillna( 0 ).astype( int )

    # Garante que as colunas existam para podermos usá-las no desempate sem erros
    for pos in range( 1, top_n + 1 ):
        if f"pos_{pos}" not in result.columns:
            result[ f"pos_{pos}" ] = 0

    # Calcula os pontos totais
    result[ "total_pts" ] = (
            result[ "pos_1" ] * 3
            + result[ "pos_2" ] * 2
            + result[ "pos_3" ] * 1
    )

    # Ordena por: total de pontos -> vitórias em 1º -> vitórias em 2º -> vitórias em 3º
    return result.sort_values(
        by = [ "total_pts", "pos_1", "pos_2", "pos_3" ],
        ascending = [ False, False, False, False ]
    ).reset_index()


def plot_podium( counts: pd.DataFrame, level: str, output_dir: Path ) -> None:
    color_key = "ctx-1" if level == "ctx-1" else "ctx-2"
    top = counts.head( 20 )  # limita a 20 idiomas para legibilidade

    langs = top[ "ctx_lang" ].tolist()
    pos1 = top[ "pos_1" ].tolist() if "pos_1" in top.columns else [ 0 ] * len( langs )
    pos2 = top[ "pos_2" ].tolist() if "pos_2" in top.columns else [ 0 ] * len( langs )
    pos3 = top[ "pos_3" ].tolist() if "pos_3" in top.columns else [ 0 ] * len( langs )
    y = np.arange( len( langs ) )

    fig, ax = plt.subplots( figsize = (12, max( 5, len( langs ) * 0.45 )) )
    fig.patch.set_facecolor( BG )
    ax.set_facecolor( BG )

    b1 = ax.barh( y, pos1, color = PODIUM[ 1 ], label = "1º lugar", height = 0.6 )
    b2 = ax.barh( y, pos2, left = pos1, color = PODIUM[ 2 ], label = "2º lugar", height = 0.6 )
    b3 = ax.barh( y, pos3,
                  left = [ p1 + p2 for p1, p2 in zip( pos1, pos2 ) ],
                  color = PODIUM[ 3 ], label = "3º lugar", height = 0.6 )

    ax.set_yticks( y )
    ax.set_yticklabels( langs, fontsize = 9, color = TEXT )
    ax.invert_yaxis()
    ax.xaxis.grid( True, color = GRID, linewidth = 0.8 )
    ax.set_axisbelow( True )
    ax.spines[ : ].set_visible( False )
    ax.tick_params( colors = TEXT, length = 0 )
    ax.xaxis.set_tick_params( labelcolor = SUBTEXT, labelsize = 9 )
    ax.set_xlabel( "Nº de vezes no pódio", color = SUBTEXT, fontsize = 10, labelpad = 8 )

    # Pontuação total à direita de cada barra
    for i, (p1, p2, p3) in enumerate( zip( pos1, pos2, pos3 ) ):
        total = p1 * 3 + p2 * 2 + p3
        ax.text( p1 + p2 + p3 + 0.15, i, f"{total} pts",
                 va = "center", fontsize = 8, color = SUBTEXT )

    # Encontra a barra mais longa
    max_x = max( [ p1 + p2 + p3 for p1, p2, p3 in zip( pos1, pos2, pos3 ) ] ) if langs else 0

    # Aumenta o limite do eixo X (adicionando espaço extra, como 2.5 unidades)
    ax.set_xlim( 0, max_x + 2.5 )

    ax.legend(
        loc = "lower right", frameon = True, framealpha = 0.15,
        edgecolor = GRID, facecolor = BG, labelcolor = TEXT, fontsize = 9,
    )

    label = "1 idioma" if level == "ctx-1" else "2 idiomas"
    ax.text(
        0.0, 1.04,
        f"Pódio por idioma · {label} · pontuação: 1º=3pts, 2º=2pts, 3º=1pt",
        ha = "left", va = "bottom", fontsize = 9, color = SUBTEXT,
        transform = ax.transAxes, clip_on = False,
    )
    fig.suptitle(
        f"Ranking de Contextos — {label}",
        x = 0.01, y = 1.0, ha = "left",
        fontsize = 14, fontweight = "bold", color = TEXT,
    )

    plt.tight_layout()
    out = output_dir / f"podium_{level.replace( '-', '' )}.png"
    plt.savefig( str( out ), dpi = 150, bbox_inches = "tight", facecolor = BG )
    plt.close()
    print( f"  [ok] {out}" )


def plot_heatmap( rankings: pd.DataFrame, level: str, output_dir: Path ) -> None:
    # Média de BLEU por projeto × idioma (agrega estratégias)
    pivot = (
        rankings.groupby( [ "project", "ctx_lang" ] )[ "bleu" ]
        .mean()
        .unstack( fill_value = np.nan )
    )

    if pivot.empty:
        return

    projects = pivot.index.tolist()
    langs = pivot.columns.tolist()
    matrix = pivot.values

    fig_h = max( 4, len( projects ) * 0.4 )
    fig_w = max( 6, len( langs ) * 0.9 )
    fig, ax = plt.subplots( figsize = (fig_w, fig_h) )
    fig.patch.set_facecolor( BG )
    ax.set_facecolor( BG )

    cmap = plt.cm.YlOrRd
    im = ax.imshow( matrix, cmap = cmap, aspect = "auto" )

    ax.set_xticks( range( len( langs ) ) )
    ax.set_xticklabels( langs, rotation = 45, ha = "right", fontsize = 8, color = TEXT )
    ax.set_yticks( range( len( projects ) ) )
    ax.set_yticklabels( projects, fontsize = 8, color = TEXT )
    ax.tick_params( length = 0 )
    ax.spines[ : ].set_visible( False )

    # Valor em cada célula
    for i in range( len( projects ) ):
        for j in range( len( langs ) ):
            val = matrix[ i, j ]
            if not np.isnan( val ):
                ax.text( j, i, f"{val:.1f}",
                         ha = "center", va = "center",
                         fontsize = 7, color = "black" if val > 40 else TEXT )

    cbar = fig.colorbar( im, ax = ax, shrink = 0.6, pad = 0.02 )
    cbar.ax.tick_params( labelcolor = SUBTEXT, labelsize = 8 )
    cbar.set_label( "BLEU médio", color = SUBTEXT, fontsize = 9 )

    label = "1 idioma" if level == "ctx-1" else "2 idiomas"
    ax.text(
        0.0, 1.03,
        "BLEU médio por projeto e idioma de contexto (agrega estratégias)",
        ha = "left", va = "bottom", fontsize = 9, color = SUBTEXT,
        transform = ax.transAxes, clip_on = False,
    )
    fig.suptitle(
        f"Heatmap BLEU — {label}",
        x = 0.01, y = 1.0, ha = "left",
        fontsize = 14, fontweight = "bold", color = TEXT,
    )

    plt.tight_layout()
    out = output_dir / f"heatmap_{level.replace( '-', '' )}.png"
    plt.savefig( str( out ), dpi = 150, bbox_inches = "tight", facecolor = BG )
    plt.close()
    print( f"  [ok] {out}" )


def plot_delta( rankings: pd.DataFrame, level: str, output_dir: Path ) -> None:
    avg_delta = (
        rankings.groupby( "ctx_lang" )[ "delta" ]
        .mean()
        .sort_values( ascending = False )
        .reset_index()
    )

    fig, ax = plt.subplots( figsize = (12, 5) )
    fig.patch.set_facecolor( BG )
    ax.set_facecolor( BG )

    color_key = "ctx-1" if level == "ctx-1" else "ctx-2"
    bar_colors = [
        COLORS[ color_key ] if v >= 0 else "#ef4444"
        for v in avg_delta[ "delta" ]
    ]
    xs = np.arange( len( avg_delta ) )
    bars = ax.bar( xs, avg_delta[ "delta" ], color = bar_colors,
                   width = 0.65, zorder = 2, linewidth = 0 )

    ax.axhline( 0, color = SUBTEXT, linewidth = 0.8, linestyle = "--", alpha = 0.6 )

    ax.set_xticks( xs )
    ax.set_xticklabels( avg_delta[ "ctx_lang" ], rotation = 45,
                        ha = "right", fontsize = 8.5, color = TEXT )

    for bar, val in zip( bars, avg_delta[ "delta" ] ):
        ax.text( bar.get_x() + bar.get_width() / 2,
                 bar.get_height() + (0.15 if val >= 0 else -0.6),
                 f"{val:+.1f}",
                 ha = "center", va = "bottom",
                 fontsize = 7, color = TEXT, fontweight = "bold" )

    ax.yaxis.grid( True, color = GRID, linewidth = 0.8, zorder = 0 )
    ax.set_axisbelow( True )
    ax.spines[ : ].set_visible( False )
    ax.tick_params( colors = TEXT, length = 0 )
    ax.yaxis.set_tick_params( labelcolor = SUBTEXT, labelsize = 9 )
    ax.set_ylabel( "Δ BLEU vs baseline", color = SUBTEXT, fontsize = 10, labelpad = 8 )

    label = "1 idioma" if level == "ctx-1" else "2 idiomas"
    ax.text(
        0.0, 1.04,
        "Média do ganho de BLEU em relação ao ctx-0 (baseline) · por idioma de contexto",
        ha = "left", va = "bottom", fontsize = 9, color = SUBTEXT,
        transform = ax.transAxes, clip_on = False,
    )
    fig.suptitle(
        f"Ganho Médio vs Baseline — {label}",
        x = 0.01, y = 1.0, ha = "left",
        fontsize = 14, fontweight = "bold", color = TEXT,
    )

    plt.tight_layout()
    out = output_dir / f"delta_baseline_{level.replace( '-', '' )}.png"
    plt.savefig( str( out ), dpi = 150, bbox_inches = "tight", facecolor = BG )
    plt.close()
    print( f"  [ok] {out}" )


def normalize_ctx_lang( v ) -> str:
    cl = str( v ).strip()
    if cl in ("", "nan"):
        return ""
    parts = [ p.strip() for p in cl.split( "," ) ]
    return ", ".join( sorted( parts ) )


def main():
    if not INPUT_DIR.exists():
        print( f"[erro] Pasta não encontrada: {INPUT_DIR}" )
        sys.exit( 1 )

    OUTPUT_DIR.mkdir( parents = True, exist_ok = True )
    print( f"Salvando em: {OUTPUT_DIR}\n" )

    print( "Carregando dados..." )
    data = load_all()
    print( f"  {len( data )} linhas · {data[ 'project' ].nunique()} projetos\n" )

    for level in ("ctx-1", "ctx-2"):
        label = "1 idioma" if level == "ctx-1" else "2 idiomas"
        print( f"── {label} ──────────────────────────────" )

        rankings = build_rankings( data, level )
        if rankings.empty:
            print( "  [aviso] Sem dados; pulando.\n" )
            continue

        # CSVs
        csv_rank = OUTPUT_DIR / f"rankings_{level.replace( '-', '' )}.csv"
        rankings.to_csv( csv_rank, index = False )
        print( f"  [ok] {csv_rank}" )

        counts = podium_counts( rankings )
        csv_pod = OUTPUT_DIR / f"podium_{level.replace( '-', '' )}.csv"
        counts.to_csv( csv_pod, index = False )
        print( f"  [ok] {csv_pod}" )

        # Gráficos
        plot_podium( rankings if False else counts, level, OUTPUT_DIR )
        plot_heatmap( rankings, level, OUTPUT_DIR )
        plot_delta( rankings, level, OUTPUT_DIR )
        print()

    print( "Concluído." )


if __name__ == "__main__":
    main()
