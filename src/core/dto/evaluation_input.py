from dataclasses import dataclass
from typing import List
from src.core.dto.segment_translation import SegmentTranslation


@dataclass( frozen = True )
class EvaluationInput:
    """Dados completos parseados de um arquivo JSON."""
    file_name: str
    segments: List[ SegmentTranslation ]
    context_languages: List[ str ]  # ex: ["DE"]
    strategy_name: str

    def __post_init__( self ):
        if len( self.segments ) == 0:
            raise ValueError( "Deve ter pelo menos um segmento" )
