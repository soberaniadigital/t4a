#!/usr/bin/env python3
"""
Gera gráficos de barras empilhadas:
  - Top 15 global (todos os contextos)
  - Top 15 ctx-1 com ctx-0 como referência
  - Top 15 ctx-2 com ctx-0 como referência
"""
import re
import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# ── Visuais ──────────────────────────────────────────────────────────────────
BG = "#0f1117"
TEXT = "#e2e8f0"
SUBTEXT = "#94a3b8"
GRID = "#1e2130"
COLORS = [ "#22c55e", "#64748b", "#ef4444" ]  # Vitória / Empate / Derrota
COLORS_REF = [ "#818cf8", "#334155", "#f87171" ]  # mesmas semânticas, tom ctx-0

INPUT_CSV = Path( "estatisticas" ) / "impacto" / "media_global_contextos.csv"
OUTPUT_DIR = Path( "estatisticas" ) / "impacto"


# ── Helpers ───────────────────────────────────────────────────────────────────
def ctx_level( config: str ) -> str:
    """Extrai ctx-0 / ctx-1 / ctx-2 direto do nome do arquivo."""
    match = re.search( r'ctx-(\d+)', str( config ) )
    if match:
        return f"ctx-{match.group( 1 )}"
    # fallback caso a coluna não contenha o nome do arquivo
    c = str( config ).strip().lower()
    if c in ("", "nan", "none"):
        return "ctx-0"
    parts = [ p for p in c.replace( ",", " " ).replace( "-", " " ).split() if p ]
    return "ctx-1" if len( parts ) == 1 else "ctx-2"


def to_pct_row( row: pd.Series ) -> dict:
    total = row[ "vitorias" ] + row[ "empates" ] + row[ "derrotas" ]
    if total == 0:
        return None
    return {
        "config": row[ "configuracao" ],
        "Vitórias": (row[ "vitorias" ] / total) * 100,
        "Empates": (row[ "empates" ] / total) * 100,
        "Derrotas": (row[ "derrotas" ] / total) * 100,
        "n_projetos": int( row[ "total_projetos" ] ),
        "is_ref": False,
    }


# ── Renderização ──────────────────────────────────────────────────────────────
COLS = [ "Vitórias", "Empates", "Derrotas" ]


def render_chart( df_plot: pd.DataFrame, title: str, out_path: Path ):
    """Renderiza um gráfico de barras empilhadas horizontais."""
    n = len( df_plot )
    fig_h = max( 6, n * 0.65 )
    fig, ax = plt.subplots( figsize = (14, fig_h) )
    fig.patch.set_facecolor( BG )
    ax.set_facecolor( BG )

    # ── Barras (por linha para suportar cores individuais) ────────────────────
    bottoms = [ 0.0 ] * n
    for col_i, col in enumerate( COLS ):
        values = df_plot[ col ].values
        bar_colors = [
            COLORS_REF[ col_i ] if row[ "is_ref" ] else COLORS[ col_i ]
            for _, row in df_plot.iterrows()
        ]
        ax.barh( range( n ), values, left = bottoms, color = bar_colors, height = 0.75, zorder = 2 )
        # Percentual dentro da fatia
        for i, (val, left) in enumerate( zip( values, bottoms ) ):
            if val > 4:
                ax.text(
                    left + val / 2, i,
                    f"{val:.1f}%",
                    ha = "center", va = "center",
                    color = "white", fontsize = 9, fontweight = "bold", zorder = 3,
                )
        bottoms = [ bottoms[ i ] + values[ i ] for i in range( n ) ]

    # ── Separador visual antes da linha de referência ─────────────────────────
    for i, (_, row) in enumerate( df_plot.iterrows() ):
        if row[ "is_ref" ] and i > 0:
            ax.axhline( i - 0.5, color = SUBTEXT, linewidth = 0.8, linestyle = "--", alpha = 0.5, zorder = 1 )

    # ── Labels do eixo Y: SUPRIMIR os padrão e usar anotação manual ───────────
    ax.set_yticks( range( n ) )
    ax.set_yticklabels( [ ] )  # <── FIX: elimina o overlap

    for i, (_, row) in enumerate( df_plot.iterrows() ):
        suffix = "  ◀ ctx-0 (ref)" if row[ "is_ref" ] else ""
        label = f"(n={row[ 'n_projetos' ]})  {row[ 'config' ]}{suffix}"
        color = "#818cf8" if row[ "is_ref" ] else SUBTEXT
        ax.text(
            -1.5, i, label,
            ha = "right", va = "center",
            color = color, fontsize = 9,
        )

    # ── Estilo ────────────────────────────────────────────────────────────────
    ax.set_xlim( 0, 100 )
    ax.set_xlabel( "Percentual (%) Médio de Impacto nas Frases", color = SUBTEXT, fontsize = 11 )
    ax.set_ylabel( "" )
    ax.tick_params( colors = TEXT, labelsize = 10, length = 0 )
    ax.spines[ : ].set_visible( False )
    ax.xaxis.grid( True, color = GRID, linewidth = 0.8, zorder = 0 )
    ax.set_axisbelow( True )

    ax.set_title( title, color = TEXT, fontsize = 15, fontweight = "bold", pad = 42, loc = "left" )

    # ── Legenda ───────────────────────────────────────────────────────────────
    has_ref = df_plot[ "is_ref" ].any()
    handles = [ mpatches.Patch( color = c, label = l ) for c, l in zip( COLORS, COLS ) ]
    if has_ref:
        handles += [ mpatches.Patch( color = c, label = f"{l} (ctx-0)" )
                     for c, l in zip( COLORS_REF, COLS ) ]
    ax.legend(
        handles = handles,
        bbox_to_anchor = (0.0, 1.02, 1.0, 0.102), loc = "lower left",
        ncol = len( handles ), mode = "expand", borderaxespad = 0.5,
        frameon = False, labelcolor = TEXT, fontsize = 10,
    )

    plt.tight_layout( rect = [ 0.22, 0, 1, 0.95 ] )  # <── margem esquerda p/ anotações
    out_path.parent.mkdir( parents = True, exist_ok = True )
    plt.savefig( str( out_path ), dpi = 200, facecolor = BG, bbox_inches = "tight" )
    plt.close()
    print( f"  [ok] Salvo em: {out_path}" )


# ── Plot global ───────────────────────────────────────────────────────────────
def plot_top_global( df: pd.DataFrame ):
    rows = [ ]
    for _, row in df.iterrows():
        r = to_pct_row( row )
        if r:
            rows.append( r )

    df_plot = pd.DataFrame( rows )

    # Ordena: 1) Vitórias desc, 2) Empates desc, 3) Derrotas asc
    df_plot = (
        df_plot.sort_values(
            [ "Vitórias", "Empates", "Derrotas" ],
            ascending = [ True, True, False ],
        )
        .reset_index( drop = True )
    )

    render_chart(
        df_plot,
        "Melhores Contextos — Média Global (Todos os Projetos)",
        OUTPUT_DIR / "media_global_top_contextos.png",
    )


# ── Plot por nível (ctx-1 ou ctx-2) com ctx-0 como referência ────────────────
def plot_by_level( df: pd.DataFrame, level: str ):
    df[ "_ctx_level" ] = df[ "configuracao" ].apply( ctx_level )

    # referência ctx-0
    df_ref = df[ df[ "_ctx_level" ] == "ctx-0" ]
    ref_row = None
    if not df_ref.empty:
        ref_row = to_pct_row( df_ref.iloc[ 0 ] )
        if ref_row:
            ref_row[ "is_ref" ] = True

    # linhas do nível (ctx-1 ou ctx-2)
    rows = [ ]
    df_level = df[ df[ "_ctx_level" ] == level ]
    for _, row in df_level.iterrows():
        r = to_pct_row( row )
        if r:
            rows.append( r )

    if not rows:
        print( f"[aviso] Nenhuma linha para {level}." )
        return

    df_level_plot = pd.DataFrame( rows )

    # Ordena: 1) Vitórias desc, 2) Empates desc, 3) Derrotas asc
    df_level_plot = (
        df_level_plot.sort_values(
            [ "Vitórias", "Empates", "Derrotas" ],
            ascending = [ True, True, False ],
        )
        .reset_index( drop = True )
    )

    # Insere referência ctx-0 no topo da tabela (linha 0)
    if ref_row:
        df_plot = pd.concat(
            [ pd.DataFrame( [ ref_row ] ), df_level_plot ],
            ignore_index = True,
        )
    else:
        df_plot = df_level_plot

    label_map = { "ctx-1": "1 idioma", "ctx-2": "2 idiomas" }
    render_chart(
        df_plot,
        f"Contextos com {label_map.get( level, level )} — Média Global (com referência ctx-0)",
        OUTPUT_DIR / f"media_global_{level.replace( '-', '' )}.png",
    )


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    if not INPUT_CSV.exists():
        print( f"[erro] Arquivo {INPUT_CSV} não encontrado." )
        sys.exit( 1 )

    OUTPUT_DIR.mkdir( parents = True, exist_ok = True )
    df = pd.read_csv( INPUT_CSV )

    if df.empty:
        print( "[erro] O arquivo CSV está vazio." )
        sys.exit( 1 )

    print( "Gerando gráfico global..." )
    plot_top_global( df )

    print( "Gerando gráfico ctx-1..." )
    plot_by_level( df, "ctx-1" )

    print( "Gerando gráfico ctx-2..." )
    plot_by_level( df, "ctx-2" )

    print( "\nConcluído!" )


if __name__ == "__main__":
    main()
