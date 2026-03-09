#!/usr/bin/env python3
"""
Testa a normalidade dos scores BLEU por segmento.

Para cada arquivo (experimento) dentro de cada projeto:
  - Shapiro-Wilk  (n ≤ 5 000)
  - Kolmogorov-Smirnov (todos os tamanhos)

Gera um CSV e um Heatmap por projeto na pasta:
  - estatisticas/testes/resultados/

Uso:
    python test_normalidade.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

# ── Paleta ───────────────────────────────────────────────────────────────────
BG = "#0f1117"
GRID = "#1e2130"
TEXT = "#e2e8f0"
SUBTEXT = "#94a3b8"
GREEN = "#22c55e"
RED = "#ef4444"

ALPHA = 0.05
INPUT_DIR = Path( "metrics_csv" )
OUTPUT_DIR = Path( "estatisticas" ) / "normalidade"


def ctx_level( v: str ) -> str:
    cl = str( v ).strip()
    if cl in ("", "nan"):
        return "ctx-0"
    elif "," not in cl:
        return "ctx-1"
    else:
        return "ctx-2"


def load_segments( project_dir: Path ) -> pd.DataFrame:
    frames = [ ]
    for path in sorted( project_dir.glob( "*.csv" ) ):
        try:
            df = pd.read_csv( path )
        except Exception as e:
            print( f"  [aviso] {path.name}: {e}" )
            continue
        if "bleu" not in df.columns:
            continue
        if "context_languages" not in df.columns:
            df[ "context_languages" ] = ""
        df[ "ctx_level" ] = df[ "context_languages" ].apply( ctx_level )
        df[ "arquivo" ] = path.stem
        frames.append( df[ [ "bleu", "ctx_level", "arquivo" ] ] )

    if not frames:
        return pd.DataFrame( columns = [ "bleu", "ctx_level", "arquivo" ] )
    return pd.concat( frames, ignore_index = True ).dropna( subset = [ "bleu" ] )


def test_normality( values: np.ndarray ) -> dict:
    n = len( values )
    result = { "n": n }

    # ── Shapiro-Wilk ─────────────────────────────────────────────────────────
    if n >= 3:
        sample = values if n <= 5000 else np.random.choice( values, 5000, replace = False )
        stat_sw, p_sw = stats.shapiro( sample )
        result[ "sw_stat" ] = round( float( stat_sw ), 6 )
        result[ "sw_p" ] = round( float( p_sw ), 6 )
        result[ "sw_normal" ] = p_sw >= ALPHA
    else:
        result[ "sw_stat" ] = None
        result[ "sw_p" ] = None
        result[ "sw_normal" ] = None

    # ── Kolmogorov-Smirnov ───────────────────────────────────────────────────
    mu, sigma = values.mean(), values.std()
    if sigma > 0:
        stat_ks, p_ks = stats.kstest( values, "norm", args = (mu, sigma) )
        result[ "ks_stat" ] = round( float( stat_ks ), 6 )
        result[ "ks_p" ] = round( float( p_ks ), 6 )
        result[ "ks_normal" ] = p_ks >= ALPHA
    else:
        result[ "ks_stat" ] = None
        result[ "ks_p" ] = None
        result[ "ks_normal" ] = None

    sw_ok = result[ "sw_normal" ]
    ks_ok = result[ "ks_normal" ]
    if sw_ok is None and ks_ok is None:
        result[ "normal" ] = None
    else:
        result[ "normal" ] = bool( sw_ok ) and bool( ks_ok )

    return result


def plot_heatmap( project_name: str, df: pd.DataFrame, output_dir: Path ) -> None:
    """Heatmap: linhas = arquivo, colunas = sw_p / ks_p."""
    arquivos = df[ "arquivo" ].tolist()
    sw_vals = df[ "sw_p" ].tolist()
    ks_vals = df[ "ks_p" ].tolist()
    normal = df[ "normal" ].tolist()

    matrix = np.array( [ sw_vals, ks_vals ], dtype = float ).T
    n_arqs = len( arquivos )

    fig_h = max( 6, n_arqs * 0.28 )
    fig, ax = plt.subplots( figsize = (10, fig_h) )
    fig.patch.set_facecolor( BG )
    ax.set_facecolor( BG )

    cmap = plt.cm.RdYlGn
    im = ax.imshow( matrix, cmap = cmap, aspect = "auto", vmin = 0, vmax = 0.2 )

    ax.set_xticks( [ 0, 1 ] )
    ax.set_xticklabels( [ "Shapiro-Wilk (p)", "K-S (p)" ], fontsize = 9, color = TEXT )
    ax.set_yticks( range( n_arqs ) )
    ax.set_yticklabels( arquivos, fontsize = 6.5, color = TEXT )
    ax.tick_params( length = 0 )
    ax.spines[ : ].set_visible( False )

    for i in range( n_arqs ):
        for j, vals in enumerate( [ sw_vals, ks_vals ] ):
            val = vals[ i ]
            if val is not None and not np.isnan( float( val ) ):
                cor = "black" if float( val ) > 0.08 else TEXT
                ax.text( j, i, f"{float( val ):.4f}",
                         ha = "center", va = "center", fontsize = 6, color = cor )

    for i, norm in enumerate( normal ):
        if norm is True:
            ax.text( 2.3, i, "✓", ha = "left", va = "center", fontsize = 7, color = GREEN )
        elif norm is False:
            ax.text( 2.3, i, "✗", ha = "left", va = "center", fontsize = 7, color = RED )

    cbar = fig.colorbar( im, ax = ax, shrink = 0.4, pad = 0.01 )
    cbar.ax.tick_params( labelcolor = SUBTEXT, labelsize = 7 )
    cbar.set_label( "valor-p  (verde ≥ 0.05)", color = SUBTEXT, fontsize = 8 )

    ax.text(
        0.0, 1.02,
        f"α = {ALPHA} · ✓ = não rejeita normalidade · ✗ = rejeita",
        ha = "left", va = "bottom", fontsize = 9, color = SUBTEXT,
        transform = ax.transAxes, clip_on = False,
    )
    # Título atualizado para mostrar o nome do projeto
    fig.suptitle(
        f"Teste de Normalidade — BLEU — {project_name}",
        x = 0.01, y = 1.0, ha = "left",
        fontsize = 14, fontweight = "bold", color = TEXT,
    )

    plt.tight_layout()
    # Salva com o nome do projeto para evitar sobrescrever
    out = output_dir / f"{project_name}_normalidade.png"
    plt.savefig( str( out ), dpi = 150, bbox_inches = "tight", facecolor = BG )
    plt.close()
    print( f"  [ok] Imagem salva em: {out}" )


def main():
    if not INPUT_DIR.exists():
        print( f"[erro] Pasta não encontrada: {INPUT_DIR}" )
        sys.exit( 1 )

    projects = sorted( p for p in INPUT_DIR.iterdir() if p.is_dir() )
    if not projects:
        print( f"[erro] Nenhum projeto encontrado em {INPUT_DIR}" )
        sys.exit( 1 )

    OUTPUT_DIR.mkdir( parents = True, exist_ok = True )
    print( f"Projetos encontrados: {len( projects )}" )
    print( f"Salvando resultados na pasta: {OUTPUT_DIR}\n" )

    for project_dir in projects:
        project_name = project_dir.name
        print( f"→ Analisando projeto: {project_name}" )
        df = load_segments( project_dir )

        if df.empty:
            print( "  [aviso] Sem dados; pulando.\n" )
            continue

        project_rows = [ ]
        for arquivo, grp in df.groupby( "arquivo", sort = True ):
            values = grp[ "bleu" ].values
            ctx_lvl = grp[ "ctx_level" ].iloc[ 0 ]
            result = test_normality( values )

            result[ "project" ] = project_name
            result[ "arquivo" ] = arquivo
            result[ "ctx_level" ] = ctx_lvl
            project_rows.append( result )

            veredicto = "normal" if result[ "normal" ] else "NÃO normal"
            sw_p = f"{result[ 'sw_p' ]:.4f}" if result[ "sw_p" ] is not None else "n/a"
            ks_p = f"{result[ 'ks_p' ]:.4f}" if result[ "ks_p" ] is not None else "n/a"
            print( f"  {arquivo}  n={result[ 'n' ]}  SW p={sw_p}  KS p={ks_p}  → {veredicto}" )

        if not project_rows:
            continue

        # Criação do DataFrame apenas para o projeto atual
        result_df = pd.DataFrame( project_rows )[
            [ "project", "arquivo", "ctx_level", "n",
              "sw_stat", "sw_p", "sw_normal",
              "ks_stat", "ks_p", "ks_normal",
              "normal" ]
        ]

        # Salva o CSV com o nome do projeto
        csv_path = OUTPUT_DIR / f"{project_name}_normalidade.csv"
        result_df.to_csv( csv_path, index = False )
        print( f"  [ok] CSV salvo em: {csv_path}" )

        # Gera o Heatmap para o projeto atual
        plot_heatmap( project_name, result_df, OUTPUT_DIR )
        print()

    print( "Concluído." )


if __name__ == "__main__":
    main()
