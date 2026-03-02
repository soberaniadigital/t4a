import csv
import logging
from pathlib import Path
from typing import List, Dict, Any
from contextlib import contextmanager
import sys
from src.core.dto.evaluation_input import EvaluationInput
from src.core.dto.evaluation_result import EvaluationResult
from src.core.dto.pipeline_result import PipelineResult
from src.core.interfaces.metrics_pipeline import MetricsPipeline
from src.application.pipelines.comet_pipeline import CometPipeline
from src.application.pipelines.chrf_pipeline import ChrfPipeline

from src.application.parsers.json_parser import JsonEvaluationParser

logger = logging.getLogger( __name__ )


class MetricsOrchestrator:
    """Orquestra execução de pipelines e gera CSVs."""

    def __init__( self, pipelines: List[ MetricsPipeline ] ):
        self.pipelines = { p.metric_name(): p for p in pipelines }

    @contextmanager
    def _suppress_output( self ):
        """Suprime TODO output interno dos pipelines."""
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout = open( '/dev/null', 'w' )
        sys.stderr = open( '/dev/null', 'w' )
        try:
            yield
        finally:
            sys.stdout.close()
            sys.stderr.close()
            sys.stdout, sys.stderr = old_stdout, old_stderr

    def evaluate_file( self, json_file: Path ) -> EvaluationResult:
        """Avalia um arquivo JSON completo."""
        # Parse
        input_data = JsonEvaluationParser.parse( json_file )
        logger.info(
            f"📄 {json_file.name}: {len( input_data.segments )} segmentos, contexto: {input_data.context_languages}" )

        # Executa pipelines com output suprimido
        pipeline_results = [ ]
        with self._suppress_output():
            for pipeline in self.pipelines.values():
                logger.debug( f"🔢 {pipeline.metric_name().upper()}: {len( input_data.segments )} segmentos" )
                result = pipeline.compute( input_data )
                pipeline_results.append( result )
                logger.info( f"✅ {pipeline.metric_name().upper()}: {result.corpus_score:.2f}/100" )

        return EvaluationResult( input_data = input_data, pipeline_results = pipeline_results )

    def export_csv( self, result: EvaluationResult, output_dir: Path, source_file: Path ):
        """Gera CSV com pasta por projeto."""
        project_name = source_file.parent.name

        # Cria pasta específica do projeto
        project_dir = output_dir / project_name
        project_dir.mkdir( exist_ok = True )

        # CSV dentro da pasta do projeto
        csv_path = project_dir / f"{result.input_data.file_name}.csv"

        # Resto igual (headers, rows...)
        headers = [ "original", "translated", "reference", "context_languages", "strategy" ]
        for pipeline_result in result.pipeline_results:
            headers.append( pipeline_result.metric_name )

        rows = [ ]
        n_segments = len( result.input_data.segments )

        for i in range( n_segments ):
            row = {
                "original": result.input_data.segments[ i ].original,
                "translated": result.input_data.segments[ i ].translated,
                "reference": result.input_data.segments[ i ].reference,
                "context_languages": ",".join( result.input_data.context_languages ),
                "strategy": result.input_data.strategy_name
            }

            for pipeline_result in result.pipeline_results:
                row[ pipeline_result.metric_name ] = pipeline_result.segment_scores[ i ]

            rows.append( row )

        # Escreve CSV
        with open( csv_path, 'w', newline = '', encoding = 'utf-8' ) as f:
            writer = csv.DictWriter( f, fieldnames = headers )
            writer.writeheader()
            writer.writerows( rows )

        logger.info( f"📝 CSV gerado: {csv_path}" )
        return csv_path
