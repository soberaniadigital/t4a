import logging
from typing import List
from sacrebleu import sentence_bleu
from src.core.interfaces.metrics_pipeline import MetricsPipeline
from src.core.dto.evaluation_input import EvaluationInput
from src.core.dto.pipeline_result import PipelineResult

logger = logging.getLogger( __name__ )


class BleuPipeline( MetricsPipeline ):
    """Pipeline BLEU: Baseline universal de MT."""

    def compute( self, input_data: EvaluationInput ) -> PipelineResult:
        """Calcula BLEU para todos os segmentos."""
        segment_scores = [ ]

        for seg in input_data.segments:
            # BLEU: hypothesis vs reference (n-gram precision)
            score = sentence_bleu( seg.translated, [ seg.reference ] ).score
            segment_scores.append( score )

        return PipelineResult(
            metric_name = "bleu",
            corpus_score = sum( segment_scores ) / len( segment_scores ),
            segment_scores = segment_scores,
            metadata = { "type": "BLEU (n-gram precision, 1-4 grams)" }
        )

    def metric_name( self ) -> str:
        return "bleu"
