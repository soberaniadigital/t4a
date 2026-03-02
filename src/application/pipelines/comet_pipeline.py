import logging
import torch
from typing import List, Dict, Any
from comet import download_model, load_from_checkpoint
from src.core.interfaces.metrics_pipeline import MetricsPipeline
from src.core.dto.evaluation_input import EvaluationInput
from src.core.dto.pipeline_result import PipelineResult
from src.core.dto.segment_translation import SegmentTranslation

logger = logging.getLogger( __name__ )


class CometPipeline( MetricsPipeline ):
    """Pipeline COMET-22 com suporte MPS (Mac M1)."""

    def __init__( self ):
        # Detecta MPS (Mac) ou CPU
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        self.model = None
        self._load_model()

    def _load_model( self ):
        """Lazy load do modelo COMET."""
        model_name = "Unbabel/wmt22-comet-da"
        try:
            self.model = load_from_checkpoint( download_model( model_name ) )
            self.model.to( self.device )
            self.model.eval()
            logger.info( f"COMET carregado em {self.device}" )
        except Exception as e:
            logger.error( f"Erro carregando COMET: {e}" )
            raise

    def compute( self, input_data: EvaluationInput ) -> PipelineResult:
        """Calcula COMET com API correta."""
        # COMET espera lista de dicts: [{"src": "...", "mt": "...", "ref": "..."}]
        data = [ ]
        for seg in input_data.segments:
            data.append( {
                "src": seg.original,  # ✅ source
                "mt": seg.translated,  # ✅ hypothesis (machine translation)
                "ref": seg.reference  # ✅ reference
            } )

        # Chama predict com dados no formato correto
        with torch.no_grad():
            model_output = self.model.predict(
                samples = data,
                gpus = 1 if self.device != "cpu" else 0,
                accelerator = "mps" if self.device == "mps" else None
            )

        # Normaliza 0-1 -> 0-100
        segment_scores_raw = model_output.scores  # Lista: [0.45, 0.72, ...]
        segment_scores = [ float( s ) * 100 for s in segment_scores_raw ]  # 0-100

        return PipelineResult(
            metric_name = "comet",
            corpus_score = sum( segment_scores ) / len( segment_scores ),
            segment_scores = segment_scores,
            metadata = { "device": self.device, "n_segments": len( segment_scores ) }
        )

    def metric_name( self ) -> str:
        return "comet"
