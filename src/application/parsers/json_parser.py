import json
from pathlib import Path
from src.core.dto.evaluation_input import EvaluationInput
from src.core.dto.segment_translation import SegmentTranslation


class JsonEvaluationParser:

    @staticmethod
    def _fix_encoding( text: str ) -> str:
        """Corrige texto corrompido Latin-1 lido como UTF-8."""
        if not text:
            return text
        try:
            # Encode como Latin-1 (volta ao bytes original) → decode como UTF-8
            return text.encode( 'latin-1' ).decode( 'utf-8' )
        except (UnicodeEncodeError, UnicodeDecodeError):
            # Texto já está correto, retorna sem alterar
            return text

    @staticmethod
    def parse( file_path: Path ) -> EvaluationInput:
        with open( file_path, 'r', encoding = 'utf-8' ) as f:
            data = json.load( f )

        job_info = data[ 'job_info' ]
        translations = data[ 'translations' ]
        prompt_info = data.get( 'prompt_info', { } )
        context_files = prompt_info.get( 'context_files', [ ] )

        segments = [ ]
        for trans in translations:
            segments.append( SegmentTranslation(
                original = trans[ 'original' ],
                translated = trans[ 'translated' ],
                reference = JsonEvaluationParser._fix_encoding( trans[ 'reference' ] )
            ) )

        return EvaluationInput(
            file_name = file_path.stem,
            segments = segments,
            context_languages = context_files,
            strategy_name = job_info[ 'strategy_name' ]
        )
