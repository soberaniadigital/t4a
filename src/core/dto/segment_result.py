from dataclasses import dataclass


@dataclass( frozen = True )
class SegmentResult:
    """Score de um segmento individual."""
    segment_index: int
    metric_name: str
    score: float
