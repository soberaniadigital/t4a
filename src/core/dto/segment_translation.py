from dataclasses import dataclass


@dataclass( frozen = True )
class SegmentTranslation:
    """Triplet individual: original + tradução + referência."""
    original: str
    translated: str
    reference: str

    def __post_init__( self ):
        if not all( [ self.original, self.translated, self.reference ] ):
            raise ValueError( "Todos os campos devem ser não-vazios" )
