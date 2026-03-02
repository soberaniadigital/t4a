import logging
import torch
from bert_score import score as bert_score_compute
from src.core.interfaces.metrics_pipeline import MetricsPipeline
from src.core.dto.evaluation_input import EvaluationInput
from src.core.dto.pipeline_result import PipelineResult

logger = logging.getLogger( __name__ )


class BertscorePipeline( MetricsPipeline ):
    """Pipeline BERTScore: embeddings contextuais (sinônimos, paráfrases)."""

    def __init__( self ):
        # MPS (Mac M1) ou CPU
        if torch.backends.mps.is_available():
            self.device = "mps"
        elif torch.cuda.is_available():
            self.device = "cuda"
        else:
            self.device = "cpu"

    def compute( self, input_data: EvaluationInput ) -> PipelineResult:
        """Calcula BERTScore para todos os segmentos."""
        hyps = [ seg.translated for seg in input_data.segments ]
        refs = [ seg.reference for seg in input_data.segments ]

        # Calcula BERTScore (F1 = balanço entre Precision e Recall)
        P, R, F1 = bert_score_compute(
            cands = hyps,
            refs = refs,
            model_type = "bert-base-multilingual-cased",  # ✅ Multilingual (PT-BR)
            device = self.device,
            verbose = False
        )

        # F1 retorna tensor 0-1, normaliza para 0-100
        segment_scores = [ float( f ) * 100 for f in F1.tolist() ]

        return PipelineResult(
            metric_name = "bertscore",
            corpus_score = sum( segment_scores ) / len( segment_scores ),
            segment_scores = segment_scores,
            metadata = {
                "type": "BERTScore F1 (multilingual)",
                "model": "neuralmind/bert-base-portuguese-cased",
                "device": self.device
            }
        )

    def metric_name( self ) -> str:
        return "bertscore"
