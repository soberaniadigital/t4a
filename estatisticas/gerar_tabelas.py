#!/usr/bin/env python3
"""
Gera tabelas estilizadas em formato PNG para a apresentação.
Baseia-se nos arquivos CSV gerados pelas fases anteriores.

Gera:
  - estatisticas/testes/resultados/tabelas/tabela_global_kw.png
  - estatisticas/testes/resultados/tabelas/tabela_resumo_wilcoxon.png
"""

import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

# ── Configurações Visuais (Alinhadas com o gráfico de barras) ───────────────
BG = "#0f1117"
BG_ALT = "#151821"  # Cor alternativa para linhas pares (efeito zebrado)
GRID = "#1e2130"
TEXT = "#e2e8f0"
SUBTEXT = "#94a3b8"

# Cores semânticas
COLOR_YES = "#22c55e"  # Verde (Melhorou / Sim)
COLOR_NO = "#64748b"  # Cinza (Neutro / Sem diferença / Traço)
COLOR_BAD = "#ef4444"  # Vermelho (Piorou)

# Caminhos
INPUT_GLOBAL = Path( "estatisticas/nao_parametricos/comparativo_estatistico.csv" )
INPUT_WILCOXON = Path( "estatisticas/nao_parametricos/wilcoxon_pareado.csv" )
OUTPUT_DIR = Path( "estatisticas/testes/resultados/tabelas" )


def style_table( fig, ax, df, title, subtitle ):
    """Função auxiliar para desenhar e estilizar a tabela no matplotlib"""
    ax.axis( "off" )

    # 1. Definir larguras dinâmicas: a 1ª coluna fica mais larga
    n_cols = len( df.columns )
    first_col_w = 0.35
    other_col_w = (0.95 - first_col_w) / (n_cols - 1)
    col_widths = [ first_col_w ] + [ other_col_w ] * (n_cols - 1)

    # 2. Criar a tabela
    table = ax.table(
        cellText = df.values,
        colLabels = df.columns,
        cellLoc = "center",
        loc = "center",
        colWidths = col_widths,
    )

    # 3. Escalar a altura das células para o texto respirar
    table.scale( 1, 2.0 )
    table.auto_set_font_size( False )
    table.set_fontsize( 10 )

    for (row, col), cell in table.get_celld().items():
        # Bordas suaves com a cor GRID do tema
        cell.set_edgecolor( GRID )
        cell.set_linewidth( 1.2 )

        # Estilo do Cabeçalho
        if row == 0:
            cell.set_facecolor( BG )
            cell.set_text_props( weight = "bold", color = SUBTEXT, fontsize = 10 )
        # Estilo do Corpo
        else:
            # Efeito zebrado
            cell.set_facecolor( BG if row % 2 != 0 else BG_ALT )

            val = cell.get_text().get_text()
            col_name = df.columns[ col ]

            # Primeira coluna (Nomes dos projetos) alinhada à esquerda
            if col == 0:
                cell._loc = "left"  # Força alinhamento à esquerda
                cell.set_text_props( weight = "bold", color = TEXT )
                cell.get_text().set_text( f"   {val}" )  # Padding com espaços

            # Colorização Condicional
            elif val == "Sim":
                cell.set_text_props( color = COLOR_YES, weight = "bold" )
            elif val in ("-", "0", "ns"):
                cell.set_text_props( color = COLOR_NO )

            # Lógica para tabela Wilcoxon (Números)
            elif str( val ).isdigit() and int( val ) > 0:
                if col_name == "Melhorou":
                    cell.set_text_props( color = COLOR_YES, weight = "bold" )
                elif col_name == "Piorou":
                    cell.set_text_props( color = COLOR_BAD, weight = "bold" )
                else:
                    cell.set_text_props( color = TEXT )

            # Fallback
            else:
                cell.set_text_props( color = TEXT )

    # ── AJUSTES DE POSICIONAMENTO ──────────────────────────────────────────
    # Dá mais espaço para o título/subtítulo sem encostar na tabela
    fig.subplots_adjust( top = 0.80, bottom = 0.05 )

    # Título principal: mais alto
    fig.suptitle(
        title,
        x = 0.05,
        y = 0.97,
        ha = "left",
        fontsize = 14,
        fontweight = "bold",
        color = TEXT,
    )

    # Subtítulo: logo abaixo do título, com fonte menor
    fig.text(
        0.05,
        0.92,
        subtitle,
        ha = "left",
        va = "top",
        fontsize = 8.5,
        color = SUBTEXT,
    )

    return table


def plot_global_table():
    if not INPUT_GLOBAL.exists():
        print( f"[aviso] {INPUT_GLOBAL} não encontrado." )
        return

    df = pd.read_csv( INPUT_GLOBAL )

    plot_df = pd.DataFrame()
    plot_df[ "Projeto" ] = df[ "projeto" ]
    plot_df[ "Global (KW)?" ] = df[ "kruskal_significativo" ]

    def format_sig( val ):
        return "Sim" if val == "*" else "-"

    plot_df[ "ctx-0 vs ctx-1" ] = df[ "m_whitney_ctx-0_vs_ctx-1_p_sig" ].apply( format_sig )
    plot_df[ "ctx-0 vs ctx-2" ] = df[ "m_whitney_ctx-0_vs_ctx-2_p_sig" ].apply( format_sig )
    plot_df[ "ctx-1 vs ctx-2" ] = df[ "m_whitney_ctx-1_vs_ctx-2_p_sig" ].apply( format_sig )

    fig, ax = plt.subplots( figsize = (10, 7) )
    fig.patch.set_facecolor( BG )
    ax.set_facecolor( BG )

    style_table(
        fig,
        ax,
        plot_df,
        title = "Tabela de Significação — Kruskal-Wallis & Mann-Whitney",
        subtitle = f"{len( plot_df )} projetos analisados • '-' indica sem diferença significativa (ns)",
    )

    out_path = OUTPUT_DIR / "tabela_global_kw.png"
    plt.savefig( out_path, dpi = 150, facecolor = BG )
    plt.close()
    print( f"  [ok] Tabela Global salva: {out_path}" )


def plot_wilcoxon_table():
    if not INPUT_WILCOXON.exists():
        print( f"[aviso] {INPUT_WILCOXON} não encontrado." )
        return

    df = pd.read_csv( INPUT_WILCOXON )

    agg_df = df.groupby( [ "projeto", "resultado" ] ).size().unstack( fill_value = 0 )

    for col in [ "Melhorou", "Sem diferença", "Piorou" ]:
        if col not in agg_df.columns:
            agg_df[ col ] = 0

    agg_df = agg_df.sort_values( "Melhorou", ascending = False ).reset_index()
    agg_df.columns = [ "Projeto", "Melhorou", "Sem Diferença", "Piorou" ]

    fig, ax = plt.subplots( figsize = (9, 7) )
    fig.patch.set_facecolor( BG )
    ax.set_facecolor( BG )

    style_table(
        fig,
        ax,
        agg_df,
        title = "Impacto Direto nas Frases — Wilcoxon Pareado",
        subtitle = f"{len( agg_df )} projetos • Ordenado pelo volume de melhorias",
    )

    out_path = OUTPUT_DIR / "tabela_resumo_wilcoxon.png"
    plt.savefig( out_path, dpi = 150, facecolor = BG )
    plt.close()
    print( f"  [ok] Tabela Wilcoxon salva: {out_path}" )


def main():
    OUTPUT_DIR.mkdir( parents = True, exist_ok = True )
    print( "Iniciando geração das tabelas em PNG...\n" )

    plot_global_table()
    plot_wilcoxon_table()

    print( "\nConcluído!" )


if __name__ == "__main__":
    main()
