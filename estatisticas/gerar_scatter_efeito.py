#!/usr/bin/env python3
"""
Gera um gráfico de dispersão relacionando a Taxa de Vitória (%)
com o Tamanho do Efeito (r de Rosenthal).
"""

import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

# ── Configurações Visuais ────────────────────────────────────────────────────
BG = "#0f1117"
TEXT = "#e2e8f0"
SUBTEXT = "#94a3b8"
GRID = "#1e2130"

COLOR_CTX1 = "#22c55e"  # Verde
COLOR_CTX2 = "#f59e0b"  # Laranja

INPUT_CSV = Path( "estatisticas/impacto/media_global_contextos.csv" )
OUTPUT_DIR = Path( "estatisticas/impacto" )


def main():
    if not INPUT_CSV.exists():
        print( f"[erro] Arquivo {INPUT_CSV} não encontrado." )
        sys.exit( 1 )

    OUTPUT_DIR.mkdir( parents = True, exist_ok = True )
    df = pd.read_csv( INPUT_CSV )

    # Filtrar dados inválidos
    df = df.dropna( subset = [ 'taxa_vitoria_%', 'tamanho_efeito_r' ] )

    # Criar a figura
    fig, ax = plt.subplots( figsize = (12, 7) )
    fig.patch.set_facecolor( BG )
    ax.set_facecolor( BG )

    # Plotar os pontos
    for _, row in df.iterrows():
        config = str( row[ 'configuracao' ] )
        x = row[ 'taxa_vitoria_%' ]
        y = row[ 'tamanho_efeito_r' ]

        # Cor baseada no tipo de contexto
        is_ctx1 = "ctx-1" in config
        color = COLOR_CTX1 if is_ctx1 else COLOR_CTX2

        # Desenhar o ponto
        ax.scatter( x, y, color = color, s = 120, alpha = 0.8, edgecolors = BG, linewidth = 1.5, zorder = 3 )

        # Adicionar o rótulo aos top 15 (para não poluir)
        if y > 0.58 or x > 42:
            ax.text( x + 0.3, y, config, color = TEXT, fontsize = 9, va = 'center', ha = 'left', zorder = 4 )

    # ── Desenhar as faixas de Magnitude (Efeito) ─────────────────────────────
    # Efeito Grande (>= 0.5)
    ax.axhspan( 0.5, 0.8, color = "#22c55e", alpha = 0.05, zorder = 1 )
    ax.text( df[ 'taxa_vitoria_%' ].min(), 0.78, " EFEITO GRANDE (r ≥ 0.5)", color = COLOR_CTX1, fontsize = 10,
             fontweight = 'bold', alpha = 0.7 )

    # Efeito Médio (0.3 a 0.5)
    ax.axhspan( 0.3, 0.5, color = "#f59e0b", alpha = 0.05, zorder = 1 )
    ax.text( df[ 'taxa_vitoria_%' ].min(), 0.48, " EFEITO MÉDIO (r ≥ 0.3)", color = COLOR_CTX2, fontsize = 10,
             fontweight = 'bold', alpha = 0.7 )

    # ── Estilização do Gráfico ───────────────────────────────────────────────
    ax.set_title(
        "Relação entre Taxa de Vitória e Tamanho do Efeito (r)",
        color = TEXT, fontsize = 16, fontweight = 'bold', pad = 20, loc = 'left'
    )

    ax.set_xlabel( "Taxa de Vitória Média (%)", color = SUBTEXT, fontsize = 11, labelpad = 10 )
    ax.set_ylabel( "Tamanho do Efeito Médio (r de Rosenthal)", color = SUBTEXT, fontsize = 11, labelpad = 10 )

    ax.tick_params( colors = TEXT, labelsize = 10 )
    ax.grid( True, color = GRID, linestyle = '--', linewidth = 0.8, zorder = 0 )
    ax.spines[ 'top' ].set_visible( False )
    ax.spines[ 'right' ].set_visible( False )
    ax.spines[ 'bottom' ].set_color( GRID )
    ax.spines[ 'left' ].set_color( GRID )

    # Legenda customizada
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D( [ 0 ], [ 0 ], marker = 'o', color = 'w', label = 'Contexto: 1 Idioma', markerfacecolor = COLOR_CTX1,
                markersize = 10 ),
        Line2D( [ 0 ], [ 0 ], marker = 'o', color = 'w', label = 'Contexto: 2 Idiomas', markerfacecolor = COLOR_CTX2,
                markersize = 10 )
    ]
    ax.legend( handles = legend_elements, loc = 'lower right', frameon = True, facecolor = BG, edgecolor = GRID,
               labelcolor = TEXT )

    # Salvar
    plt.tight_layout()
    out_path = OUTPUT_DIR / "scatter_efeito_magnitude.png"
    plt.savefig( out_path, dpi = 200, facecolor = BG, bbox_inches = 'tight' )
    plt.close()
    print( f"[ok] Gráfico de Dispersão salvo em: {out_path}" )


if __name__ == "__main__":
    main()
