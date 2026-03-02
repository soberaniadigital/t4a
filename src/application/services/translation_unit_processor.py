from src.core.interfaces.translation_strategy import TranslationStrategy
from src.infrastructure.providers.common.llm_prompt import LlmPrompt
from src.application.services.context_service import ContextService
from src.shared.utils.text_parser import extrair_traducao_estrita
from src.core.config.settings import DEEPL_NOME


class TranslationUnitProcessor:
    """
    Encapsula a complexidade de traduzir UM único item.
    Decide se usa Prompt (LLM) ou chamada direta (DeepL).
    """

    def __init__(
            self,
            strategy: TranslationStrategy,
            strategy_name: str,
            prompt_builder: LlmPrompt,
            context_service: ContextService = None
    ):
        self._strategy = strategy
        self._strategy_name = strategy_name
        self._prompt_builder = prompt_builder
        self.context_service = context_service

    def processar_item( self, chave: str, texto_original: str ) -> str:
        # Padrão Strategy aplicado corretamente: O processador decide o fluxo
        if self._strategy_name == DEEPL_NOME:
            return self._processar_direto( texto_original )
        else:
            return self._processar_llm( chave, texto_original )

    def _processar_direto( self, texto: str ) -> str:
        return self._strategy.traduzir( texto )

    def _processar_llm( self, chave: str, texto_original: str ) -> str:
        contexto_dados = { }
        if self.context_service:
            contexto_dados = self.context_service.obter_contexto( chave )

        prompt = self._prompt_builder.construir_prompt( texto_original, contexto_dados )
        resultado_bruto = self._strategy.traduzir( prompt )

        # A lógica de limpeza também pertence a este fluxo específico
        return extrair_traducao_estrita( resultado_bruto )

    def obter_estrategia( self ) -> TranslationStrategy:
        """
        Expõe a estratégia utilizada para que o serviço possa coletar metadados.
        """
        return self._strategy
