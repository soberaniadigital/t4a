#!/usr/bin/env python3
"""
Agrega os resultados de Ganho/Perda por tipo de contexto através de todos os projetos.
Responde: "Qual configuração de contexto é a melhor no geral?"

Gera:
  - estatisticas/testes/resultados/media_global_contextos.csv
"""

import sys
from pathlib import Path
import pandas as pd
import re

INPUT_CSV = Path( "estatisticas" ) / "impacto" / "analise_impacto_ganho.csv"
OUTPUT_CSV = Path( "estatisticas" ) / "impacto" / "media_global_contextos.csv"


def extrair_config( nome_arquivo ):
    # Tenta extrair a parte central: ex "ctx-2.es-fr"
    match = re.search( r'(ctx-\d+\.[a-z\-_]+)', nome_arquivo )
    return match.group( 1 ) if match else nome_arquivo


def main():
    if not INPUT_CSV.exists():
        print( f"[erro] O arquivo {INPUT_CSV} não existe." )
        return

    df = pd.read_csv( INPUT_CSV )

    # 1. Normalizar o nome do experimento para agrupar entre projetos
    # Ex: "aspell...ctx-2.es-fr..." vira "ctx-2.es-fr"
    df[ 'configuracao' ] = df[ 'experimento' ].apply( extrair_config )

    # 2. Agrupar e calcular as médias
    df_global = df.groupby( 'configuracao' ).agg( {
        'taxa_vitoria_%': 'mean',
        'tamanho_efeito_r': 'mean',
        'vitorias': 'sum',
        'derrotas': 'sum',
        'empates': 'sum',
        'projeto': 'count'  # Conta em quantos projetos esse contexto apareceu
    } ).rename( columns = { 'projeto': 'total_projetos' } )

    # 3. Ordenar pelos melhores resultados (maior taxa de vitória)
    df_global = df_global.sort_values( by = 'taxa_vitoria_%', ascending = False )

    # Salvar
    df_global.to_csv( OUTPUT_CSV )
    print( f"[ok] Relatório global salvo em: {OUTPUT_CSV}" )
    print( "\nTop 5 Configurações de Contexto (Média Global):" )
    print( df_global[ [ 'taxa_vitoria_%', 'tamanho_efeito_r', 'total_projetos' ] ].head() )


if __name__ == "__main__":
    main()
