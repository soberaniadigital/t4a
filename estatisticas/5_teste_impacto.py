#!/usr/bin/env python3
"""
Analisa o impacto prático (Effect Size) e a taxa de Ganho/Perda (Win/Loss).
Focado em métricas de utilidade para o TCC.

Gera:
  - estatisticas/testes/resultados/analise_impacto_ganho.csv
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from scipy import stats

INPUT_DIR = Path( "metrics_csv" )
OUTPUT_DIR = Path( "estatisticas" ) / "impacto" / "analise"


def get_ctx_level( path ):
    try:
        df = pd.read_csv( path, nrows = 1 )
        cl = str( df[ "context_languages" ].iloc[ 0 ] ).strip() if "context_languages" in df.columns else ""
        if cl in ("", "nan"): return "ctx-0"
        return "ctx-1" if "," not in cl else "ctx-2"
    except:
        return None


def calculate_effect_size( base, exp ):
    """Calcula o coeficiente r de Rosenthal para o teste de Wilcoxon."""
    # Wilcoxon retorna a estatística W. Para r, precisamos do valor Z.
    # Usamos a aproximação normal para obter Z.
    res = stats.wilcoxon( base, exp, alternative = 'two-sided' )
    n = len( base )
    # Z aproximado (W - média) / desvio padrão
    # Para fins de TCC, r = Z / sqrt(N)
    # Uma forma comum de obter Z no scipy é via o atributo 'z' se disponível
    # ou calculando o ranksums (embora Wilcoxon seja pareado).
    # Vamos usar a lógica: r = Z / sqrt(N).
    # Como o scipy não dá o Z direto em versões antigas, calculamos manualmente:
    mu_w = n * (n + 1) / 4
    sigma_w = np.sqrt( n * (n + 1) * (2 * n + 1) / 24 )
    z_score = (res.statistic - mu_w) / sigma_w
    r = abs( z_score ) / np.sqrt( n )
    return round( r, 4 )


def main():
    if not INPUT_DIR.exists():
        print( f"[erro] Pasta {INPUT_DIR} não encontrada." )
        sys.exit( 1 )

    OUTPUT_DIR.mkdir( parents = True, exist_ok = True )
    projects = sorted( [ p for p in INPUT_DIR.iterdir() if p.is_dir() ] )

    impact_results = [ ]

    print( f"Iniciando Análise de Impacto e Ganho/Perda...\n" )

    for project_dir in projects:
        project_name = project_dir.name
        print( f"→ Projeto: {project_name}" )

        baseline_file = next( (p for p in project_dir.glob( "*.csv" ) if get_ctx_level( p ) == "ctx-0"), None )
        if not baseline_file: continue

        df_base = pd.read_csv( baseline_file )
        base_scores = df_base[ "bleu" ].values

        for exp_path in project_dir.glob( "*.csv" ):
            level = get_ctx_level( exp_path )
            if level == "ctx-0": continue

            df_exp = pd.read_csv( exp_path )
            exp_scores = df_exp[ "bleu" ].values

            if len( exp_scores ) != len( base_scores ): continue

            # 1. Ganho/Perda frase a frase
            diff = exp_scores - base_scores
            wins = np.sum( diff > 0.01 )  # Melhorou (margem de 0.01 para evitar ruído)
            losses = np.sum( diff < -0.01 )  # Piorou
            ties = np.sum( np.abs( diff ) <= 0.01 )  # Empatou

            win_rate = (wins / len( diff )) * 100

            # 2. Tamanho do Efeito (r)
            try:
                r_val = calculate_effect_size( base_scores, exp_scores )
                # Interpretação clássica de Cohen/Rosenthal
                if r_val < 0.1:
                    magnitude = "Insignificante"
                elif r_val < 0.3:
                    magnitude = "Pequeno"
                elif r_val < 0.5:
                    magnitude = "Médio"
                else:
                    magnitude = "Grande"
            except:
                r_val, magnitude = 0, "N/A"

            impact_results.append( {
                "projeto": project_name,
                "experimento": exp_path.stem,
                "nivel": level,
                "n_segmentos": len( diff ),
                "vitorias": wins,
                "empates": ties,
                "derrotas": losses,
                "taxa_vitoria_%": round( win_rate, 2 ),
                "tamanho_efeito_r": r_val,
                "impacto": magnitude
            } )

    if not impact_results:
        print( "[erro] Nenhum dado processado." )
        return

    df_final = pd.DataFrame( impact_results )

    # CSV GLOBAL (como já existia)
    csv_global = OUTPUT_DIR / "analise_impacto_ganho.csv"
    df_final.to_csv( csv_global, index = False )
    print( f"\n[ok] Análise global salva em: {csv_global}" )

    # UM CSV POR PROJETO: analise_impacto_ganho_<projeto>.csv
    for project_name, grp in df_final.groupby( "projeto" ):
        out_proj = OUTPUT_DIR / f"analise_impacto_ganho_{project_name}.csv"
        grp.to_csv( out_proj, index = False )
        print( f"  [ok] CSV do projeto {project_name} salvo em: {out_proj}" )


if __name__ == "__main__":
    main()
