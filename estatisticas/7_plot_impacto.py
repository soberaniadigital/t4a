#!/usr/bin/env python3
"""
Gera gráficos de barras empilhadas (Wins/Ties/Losses) por projeto.
Baseia-se no arquivo analise_impacto_ganho.csv.

Gera:
  - estatisticas/testes/resultados/graficos_ganho_perda/projeto_nome.png
"""

import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

# ── Configurações Visuais ────────────────────────────────────────────────────
BG = "#0f1117"
TEXT = "#e2e8f0"
SUBTEXT = "#94a3b8"
# Cores semânticas: Vitória (Verde), Empate (Cinza), Derrota (Vermelho)
COLORS = [ "#22c55e", "#64748b", "#ef4444" ]

INPUT_CSV = Path( "estatisticas" ) / "impacto" / "analise_impacto_ganho.csv"
OUTPUT_DIR = Path( "estatisticas" ) / "impacto" / "graficos_ganho_perda"


def plot_project_win_rate( project_name, df_proj ):
    # Preparar dados
    plot_data = [ ]
    for _, row in df_proj.iterrows():
        total = row[ 'vitorias' ] + row[ 'empates' ] + row[ 'derrotas' ]
        if total == 0:
            continue
        plot_data.append( {
            'Experimento': row[ 'experimento' ],
            'Vitórias': (row[ 'vitorias' ] / total) * 100,
            'Empates': (row[ 'empates' ] / total) * 100,
            'Derrotas': (row[ 'derrotas' ] / total) * 100,
        } )

    df_plot = pd.DataFrame( plot_data )

    # Ordena:
    #  1) Vitórias desc (mais vitórias = melhor)
    #  2) Empates  desc (mais empates = melhor desempate)
    #  3) Derrotas asc  (menos derrotas = melhor)
    # Como o barh plota de baixo pra cima, ordenamos do pior pro melhor:
    df_plot = (
        df_plot.sort_values(
            [ 'Vitórias', 'Empates', 'Derrotas' ],
            ascending = [ True, True, False ]  # pior -> melhor (melhor fica em cima)
        )
        .reset_index( drop = True )
    )

    # Índice vira o nome do experimento (na ordem já ordenada)
    df_plot = df_plot.set_index( 'Experimento' )

    # Altura proporcional
    fig_h = max( 6, len( df_plot ) * 0.45 )
    fig, ax = plt.subplots( figsize = (14, fig_h) )

    df_plot.plot( kind = 'barh', stacked = True, color = COLORS, ax = ax, width = 0.8 )

    fig.patch.set_facecolor( BG )
    ax.set_facecolor( BG )

    ax.set_title(
        f"Taxa de Ganho/Perda por Experimento — {project_name}",
        color = TEXT, fontsize = 15, fontweight = 'bold', pad = 50, loc = 'left'
    )

    ax.set_xlabel( "Percentual (%) das Frases", color = SUBTEXT, fontsize = 10 )
    ax.set_ylabel( "" )

    ax.tick_params( colors = TEXT, labelsize = 9 )
    ax.set_xlim( 0, 100 )

    ax.legend(
        bbox_to_anchor = (0., 1.02, 1., .102), loc = 'lower left',
        ncol = 3, mode = "expand", borderaxespad = 0.5,
        frameon = False, labelcolor = TEXT
    )

    # Porcentagens dentro das barras
    for p in ax.patches:
        width = p.get_width()
        if width > 4:
            x = p.get_x() + width / 2
            y = p.get_y() + p.get_height() / 2
            ax.text(
                x, y, f'{width:.1f}%',
                ha = 'center', va = 'center',
                color = 'white', fontsize = 8, fontweight = 'bold'
            )

    plt.tight_layout( rect = [ 0, 0, 1, 0.90 ] )

    out_path = OUTPUT_DIR / f"{project_name}_ganho_perda.png"
    plt.savefig( out_path, dpi = 150, facecolor = BG, bbox_inches = 'tight' )
    plt.close()
    print( f"  [ok] Gráfico corrigido: {out_path}" )


def main():
    if not INPUT_CSV.exists():
        print( f"[erro] Arquivo {INPUT_CSV} não encontrado. Execute o script de análise primeiro." )
        sys.exit( 1 )

    OUTPUT_DIR.mkdir( parents = True, exist_ok = True )
    df = pd.read_csv( INPUT_CSV )

    print( f"Gerando gráficos de Ganho/Perda...\n" )

    for project_name, group in df.groupby( 'projeto' ):
        print( f"→ {project_name}" )
        plot_project_win_rate( project_name, group )

    print( "\nConcluído. Todos os gráficos estão em estatisticas/testes/resultados/graficos_ganho_perda/" )


if __name__ == "__main__":
    main()
