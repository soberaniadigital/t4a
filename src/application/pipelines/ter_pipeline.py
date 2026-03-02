import logging
from sacrebleu import TER
from src.core.interfaces.metrics_pipeline import MetricsPipeline
from src.core.dto.evaluation_input import EvaluationInput
from src.core.dto.pipeline_result import PipelineResult

logger = logging.getLogger( __name__ )


class TerPipeline( MetricsPipeline ):
    """Pipeline TER: Translation Edit Rate (esforço de pós-edição)."""

    def compute( self, input_data: EvaluationInput ) -> PipelineResult:
        """Calcula TER para todos os segmentos."""
        ter = TER()
        segment_scores = [ ]

        for seg in input_data.segments:
            try:
                raw = ter.sentence_score( seg.translated, [ seg.reference ] ).score
                # TER: quanto menor, melhor (0=perfeito, 100=máximo esforço)
                # Clip para 0-100 (edge cases podem ultrapassar)
                clipped = min( max( float( raw ), 0.0 ), 100.0 )
                segment_scores.append( clipped )
            except Exception as e:
                logger.warning( f"⚠️ TER falhou no segmento (usando 100.0): {e}" )
                segment_scores.append( 100.0 )  # Fallback: pior score

        return PipelineResult(
            metric_name = "ter",
            corpus_score = sum( segment_scores ) / len( segment_scores ),
            segment_scores = segment_scores,
            metadata = { "type": "TER (edit rate)", "note": "menor = melhor" }
        )

    def metric_name( self ) -> str:
        return "ter"
