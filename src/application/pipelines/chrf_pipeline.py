import logging
from typing import List
from sacrebleu import sentence_chrf, CHRF
from src.core.interfaces.metrics_pipeline import MetricsPipeline
from src.core.dto.evaluation_input import EvaluationInput
from src.core.dto.pipeline_result import PipelineResult

logger = logging.getLogger( __name__ )


class ChrfPipeline( MetricsPipeline ):
    """Pipeline chrF++: Character n-gram F-score (rápida, morfologia PT-BR)."""

    def compute( self, input_data: EvaluationInput ) -> PipelineResult:
        """Calcula chrF++ para todos os segmentos."""
        segment_scores = [ ]

        for seg in input_data.segments:
            chrf = CHRF( word_order = 2 )  # chrF++
            score = chrf.sentence_score( seg.translated, [ seg.reference ] )
            segment_scores.append( score.score )

        return PipelineResult(
            metric_name = "chrf",
            corpus_score = sum( segment_scores ) / len( segment_scores ),
            segment_scores = segment_scores,
            metadata = { "type": "chrF++ (char n-grams + word order)" }
        )

    def metric_name( self ) -> str:
        return "chrf"
