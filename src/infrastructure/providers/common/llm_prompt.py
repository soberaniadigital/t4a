# Interface
from src.core.interfaces.prompt_strategy import PromptStrategy

# Texto usado para construir o prompt
from src.core.config.settings import PROMPT_USER_TEMPLATE


class LlmPrompt( PromptStrategy ):

    def construir_prompt( self, texto_original: str, contexto: dict[ str, str ] = None ) -> str:
        secao_contexto: str = LlmPrompt._criar_secao_contexto( contexto )
        return self._substituir_conteudo( texto_original, secao_contexto )

    @staticmethod
    def _criar_secao_contexto( contexto: dict[ str, str ] ) -> str:
        """
        Método privado para criar o texto contendo as informações contextuais usadas na tradução.

        :param contexto: Dicionário onde chave é o idioma e o valor é o texto traduzido no idioma da chave.
        :return: Texto contendo todas as traduções para outros idiomas.
        """
        secao_contexto: str = ""
        if contexto:
            header = "## CONTEXT (Previous Translations for Consistency)\n"
            linhas = [ f'- English: "{en}"\n- Portuguese: "{pt}"' for en, pt in contexto.items() ]
            secao_contexto = header + "\n".join( linhas )
        return secao_contexto

    def _substituir_conteudo( self, texto_original: str, secao_contexto: str ) -> str:
        """
        Método privado para realizar a substituição do conteúdo dentro de PROMPT_USER_TEMPLATE.

        :param texto_original: Texto do arquivo que deseja traduzir.
        :param secao_contexto: Texto contendo todas as traduções para outros idiomas.
        :return: Texto contendo o prompt que será passado para a LLM.
        """
        prompt: str = self.template.safe_substitute(
            context_section = secao_contexto,
            original_text = texto_original
        )
        return prompt


if __name__ == "__main__":
    objeto = LlmPrompt( PROMPT_USER_TEMPLATE )
    texto: str = objeto.construir_prompt( 'I Love You' )
    print( texto )
