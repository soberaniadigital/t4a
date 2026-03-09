#!/usr/bin/env python3
"""
Realiza o Teste de Wilcoxon Pareado.
Ideal para comparar o desempenho na MESMA frase em condições diferentes (contextos).

Gera:
  - estatisticas/testes/resultados/wilcoxon_pareado.csv
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from scipy import stats

INPUT_DIR = Path( "metrics_csv" )
OUTPUT_DIR = Path( "estatisticas" ) / "nao_parametricos"
ALPHA = 0.05


def get_ctx_level( path ):
    # Lógica simples para identificar o nível no carregamento
    try:
        df = pd.read_csv( path, nrows = 1 )
        cl = str( df[ "context_languages" ].iloc[ 0 ] ).strip() if "context_languages" in df.columns else ""
        if cl in ("", "nan"): return "ctx-0"
        return "ctx-1" if "," not in cl else "ctx-2"
    except:
        return None


def main():
    if not INPUT_DIR.exists():
        print( f"[erro] Pasta {INPUT_DIR} não encontrada." )
        sys.exit( 1 )

    OUTPUT_DIR.mkdir( parents = True, exist_ok = True )
    projects = sorted( [ p for p in INPUT_DIR.iterdir() if p.is_dir() ] )

    all_comparisons = [ ]

    print( f"Iniciando Testes de Wilcoxon Pareado...\n" )

    for project_dir in projects:
        project_name = project_dir.name
        print( f"→ Projeto: {project_name}" )

        # 1. Separar Baseline (ctx-0) dos Experimentos (ctx-1/2)
        baseline_file = None
        experiments = [ ]

        for path in project_dir.glob( "*.csv" ):
            level = get_ctx_level( path )
            if level == "ctx-0":
                baseline_file = path
            elif level in [ "ctx-1", "ctx-2" ]:
                experiments.append( (path, level) )

        if not baseline_file:
            print( f"  [aviso] Baseline (ctx-0) não encontrado. Pulando projeto." )
            continue

        # Carregar notas do baseline
        df_base = pd.read_csv( baseline_file )
        base_scores = df_base[ "bleu" ].values
        n_base = len( base_scores )

        # 2. Comparar cada experimento contra o baseline
        for exp_path, level in experiments:
            df_exp = pd.read_csv( exp_path )
            exp_scores = df_exp[ "bleu" ].values

            if len( exp_scores ) != n_base:
                print( f"  [erro] Tamanho diferente em {exp_path.name} (n={len( exp_scores )} vs base={n_base})" )
                continue

            # Teste de Wilcoxon (Pareado)
            # 'two-sided' testa se há diferença (melhor ou pior)
            # 'greater' testaria apenas se o experimento é MELHOR que o base
            try:
                stat, p_val = stats.wilcoxon( base_scores, exp_scores, alternative = 'two-sided' )

                all_comparisons.append( {
                    "projeto": project_name,
                    "arquivo_experimento": exp_path.stem,
                    "nivel": level,
                    "n_frases": n_base,
                    "mediana_base": round( np.median( base_scores ), 4 ),
                    "mediana_exp": round( np.median( exp_scores ), 4 ),
                    "p_value": round( p_val, 6 ),
                    "significativo": "Sim" if p_val < ALPHA else "Não",
                    "resultado": "Melhorou" if (
                            p_val < ALPHA and np.median( exp_scores ) > np.median( base_scores )) else (
                        "Piorou" if (p_val < ALPHA and np.median( exp_scores ) < np.median(
                            base_scores )) else "Sem diferença")
                } )
            except ValueError:
                # Ocorre se todas as diferenças forem zero (arquivos idênticos)
                all_comparisons.append( {
                    "projeto": project_name, "arquivo_experimento": exp_path.stem, "nivel": level,
                    "n_frases": n_base, "p_value": 1.0, "significativo": "Não", "resultado": "Idênticos"
                } )

    if all_comparisons:
        final_df = pd.DataFrame( all_comparisons )
        csv_path = OUTPUT_DIR / "wilcoxon_pareado.csv"
        final_df.to_csv( csv_path, index = False )
        print( f"\n[ok] Teste de Wilcoxon concluído! Salvo em: {csv_path}" )
    else:
        print( "[erro] Nenhuma comparação foi realizada." )


if __name__ == "__main__":
    main()
