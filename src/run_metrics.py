#!/usr/bin/env python3

import os

os.environ[ 'PYTORCH_MPS_HIGH_WATERMARK_RATIO' ] = '0.0'  # Desabilita MPS logs
os.environ[ 'MALLOC_STACK_LOGGING_NO_COMPACT' ] = '1'  # Fix macOS

import logging

logging.getLogger( "lightning" ).propagate = False
logging.getLogger( "lightning.pytorch" ).propagate = False
logging.getLogger( "pytorch_lightning" ).propagate = False
logging.getLogger( "lightning.pytorch" ).setLevel( logging.ERROR )
logging.getLogger( "lightning.pytorch.utilities.rank_zero" ).setLevel( logging.ERROR )
logging.getLogger( "lightning.pytorch.accelerators.mps" ).setLevel( logging.ERROR )
logging.getLogger( "pytorch_lightning" ).setLevel( logging.ERROR )
logging.getLogger( "Foundation" ).setLevel( logging.ERROR )

import argparse
import sys
from pathlib import Path
from tqdm import tqdm
from rich.console import Console
from rich.table import Table

# Setup de Path
ROOT_DIR = Path( __file__ ).resolve().parent.parent
sys.path.append( str( ROOT_DIR ) )

import warnings

warnings.filterwarnings( "ignore", message = "litmodels" )

from src.application.orchestrator.metrics_orchestrator import MetricsOrchestrator
from src.application.pipelines.comet_pipeline import CometPipeline
from src.application.pipelines.chrf_pipeline import ChrfPipeline
from src.application.pipelines.bleu_pipeline import BleuPipeline
from src.application.pipelines.ter_pipeline import TerPipeline
from src.application.pipelines.bertscore_pipeline import BertscorePipeline

logging.basicConfig( level = logging.INFO, format = '%(message)s' )
console = Console()


def main():
    parser = argparse.ArgumentParser( description = "Avaliação de traduções com COMET" )
    parser.add_argument( "input_dir", type = Path, help = "Pasta com arquivos .json" )
    parser.add_argument( "--output-dir", type = Path, default = Path( "metrics_csv" ),
                         help = "Pasta de saída dos CSVs" )
    args = parser.parse_args()

    # Configuração
    output_dir = args.output_dir
    output_dir.mkdir( exist_ok = True )

    # Inicializa orquestrador
    pipelines = [
        CometPipeline(),
        ChrfPipeline(),
        BleuPipeline(),
        TerPipeline(),
        BertscorePipeline()
    ]
    orchestrator = MetricsOrchestrator( pipelines )

    # Busca arquivos JSON
    json_files = list( args.input_dir.rglob( "*.json" ) )
    if not json_files:
        console.print( "[red]❌ Nenhum arquivo JSON encontrado[/red]" )
        sys.exit( 1 )

    console.print( f"📂 Encontrados {len( json_files )} arquivos JSON" )

    # Processa arquivos
    results = [ ]
    for json_file in tqdm( json_files, desc = "Avaliando arquivos" ):
        try:
            result = orchestrator.evaluate_file( json_file )
            csv_path = orchestrator.export_csv( result, output_dir, json_file )
            results.append( result )
        except Exception as e:
            console.print( f"[red]❌ Erro em {json_file.name}: {e}[/red]" )
            continue

    # Resumo final
    if results:
        show_summary( results )


def show_summary( results ):
    """Tabela resumo no terminal."""
    table = Table( title = "📊 RESUMO FINAL" )
    table.add_column( "Arquivo" )
    table.add_column( "Segmentos" )
    table.add_column( "Contexto" )
    table.add_column( "COMET", justify = "right" )
    table.add_column( "chrF++", justify = "right" )
    table.add_column( "BLEU", justify = "right" )
    table.add_column( "TER ↓", justify = "right" )
    table.add_column( "BERTScore", justify = "right" )

    for result in results:
        contexto = ",".join( result.input_data.context_languages )[ :20 ]
        comet_score = result.pipeline_results[ 0 ].corpus_score
        chrf_score = result.pipeline_results[ 1 ].corpus_score
        bleu_score = result.pipeline_results[ 2 ].corpus_score
        ter_score = result.pipeline_results[ 3 ].corpus_score
        bert_score = result.pipeline_results[ 4 ].corpus_score

        table.add_row(
            result.input_data.file_name[ :30 ],
            str( len( result.input_data.segments ) ),
            contexto,
            f"{comet_score:.2f}",
            f"{chrf_score:.2f}",
            f"{bleu_score:.2f}",
            f"{ter_score:.2f}",
            f"{bert_score:.2f}"
        )

    console.print( table )

    # Estatísticas agregadas
    comet_scores = [ r.pipeline_results[ 0 ].corpus_score for r in results ]
    chrf_scores = [ r.pipeline_results[ 1 ].corpus_score for r in results ]
    bleu_scores = [ r.pipeline_results[ 2 ].corpus_score for r in results ]
    ter_scores = [ r.pipeline_results[ 3 ].corpus_score for r in results ]
    bert_scores = [ r.pipeline_results[ 4 ].corpus_score for r in results ]

    console.print( f"\n📈 COMET médio: {sum( comet_scores ) / len( comet_scores ):.2f}" )
    console.print( f"📈 chrF++ médio: {sum( chrf_scores ) / len( chrf_scores ):.2f}" )
    console.print( f"📈 BLEU médio: {sum( bleu_scores ) / len( bleu_scores ):.2f}" )
    console.print( f"📈 TER médio: {sum( ter_scores ) / len( ter_scores ):.2f} (↓ menor = melhor)" )
    console.print( f"📈 BERTScore médio: {sum( bert_scores ) / len( bert_scores ):.2f}" )


def calculate_std( values ):
    """Desvio padrão simples."""
    from statistics import stdev
    return stdev( values ) if len( values ) > 1 else 0.0


if __name__ == "__main__":
    main()
