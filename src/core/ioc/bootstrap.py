# Dependências usadas
from src.core.ioc.registry import StrategyRegistry
from src.infrastructure.io.po_file_adapter import PoFileAdapter
from src.infrastructure.providers.common.llm_prompt import LlmPrompt

from src.application.services.translator_service import TranslatorService

# Importamos as fábricas concretas AQUI, e não no serviço
from src.infrastructure.providers.deepl.factory import DeepLStrategyFactory
from src.infrastructure.providers.gemini.factory import GeminiStrategyFactory
from src.infrastructure.providers.mistral.factory import MistralStrategyFactory
from src.infrastructure.providers.llama.factory import LlamaStrategyFactory
from src.core.config.settings import DEEPL_NOME, GEMINI_NOME, MISTRAL_NOME, LLAMA_NOME, PROMPT_USER_TEMPLATE


def build_translator_service() -> TranslatorService:
    """
    Factory Method do Sistema: Constrói o TranslatorService com todas
    as suas dependências configuradas.
    """

    # 1. Cria as dependências
    registry = StrategyRegistry()
    po_file_adapter = PoFileAdapter()
    prompt_build = LlmPrompt( PROMPT_USER_TEMPLATE )

    # 2. Registra as estratégias (A "configuração" acontece aqui)
    # Se amanhã você criar 'ClaudeStrategy', só mexe neste arquivo.
    registry.registrar( DEEPL_NOME, DeepLStrategyFactory() )
    registry.registrar( GEMINI_NOME, GeminiStrategyFactory() )
    registry.registrar( MISTRAL_NOME, MistralStrategyFactory() )
    registry.registrar( LLAMA_NOME, LlamaStrategyFactory() )

    # 3. Injeta o registry no serviço
    service = TranslatorService(
        registry = registry,
        po_adapter = po_file_adapter,
        prompt_builder = prompt_build
    )

    return service
