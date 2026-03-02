from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass( frozen = True )
class PipelineResult:
    """Resultado de uma métrica para todo o arquivo."""
    metric_name: str
    corpus_score: float  # score agregado
    segment_scores: List[ float ]  # um por segmento
    metadata: Dict[ str, Any ] = None  # stats extras

    def __post_init__( self ):
        if len( self.segment_scores ) == 0:
            raise ValueError( "Deve ter segment_scores" )
        if self.corpus_score < 0 or self.corpus_score > 100:
            raise ValueError( "corpus_score deve estar entre 0-100" )
