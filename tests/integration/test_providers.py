import pytest
import logging
from src.core.domain.exceptions import ErroChaveProvedor, ErroCriarCliente

# Import Factories
from src.infrastructure.providers.gemini.factory import GeminiStrategyFactory
from src.infrastructure.providers.llama.factory import LlamaStrategyFactory
from src.infrastructure.providers.mistral.factory import MistralStrategyFactory
from src.infrastructure.providers.deepl.factory import DeepLStrategyFactory

# Configurar log para ver o que está acontecendo nos testes
logger = logging.getLogger( __name__ )


# --- TESTE GEMINI ---
@pytest.mark.asyncio
async def test_gemini_integration():
    """
    Testa se conseguimos conectar e traduzir com o Gemini.
    """
    print( "\n🔵 Testando Gemini..." )
    try:
        factory = GeminiStrategyFactory()
        strategy = factory.criar_estrategia()

        texto_original = "Hello World"
        resultado = await strategy.traduzir( texto_original )

        print( f"   Original: {texto_original}" )
        print( f"   Traduzido: {resultado}" )

        assert resultado is not None
        assert len( resultado ) > 0
        assert "Olá" in resultado or "mundo" in resultado.lower() or "{" in resultado  # Verifica JSON se for prompt

    except ErroChaveProvedor:
        pytest.skip( "Chave de API do Gemini não configurada." )
    except Exception as e:
        pytest.fail( f"Falha na integração com Gemini: {e}" )


# --- TESTE LLAMA (Local) ---
@pytest.mark.asyncio
async def test_llama_integration():
    """
    Testa se o Ollama local está respondendo.
    """
    print( "\n🦙 Testando Llama (Local)..." )
    try:
        factory = LlamaStrategyFactory()
        strategy = factory.criar_estrategia()

        texto_original = "Translate this: House"
        resultado = await strategy.traduzir( texto_original )

        print( f"   Resultado Llama: {resultado}" )

        assert resultado is not None
        assert len( resultado ) > 0

    except Exception as e:
        pytest.fail( f"Falha ao conectar com Ollama. Verifique se 'ollama serve' está rodando. Erro: {e}" )


# --- TESTE MISTRAL ---
@pytest.mark.asyncio
async def test_mistral_integration():
    """
    Testa a API do Mistral.
    """
    print( "\n🌪️ Testando Mistral..." )
    try:
        factory = MistralStrategyFactory()
        strategy = factory.criar_estrategia()

        texto_original = "Hello friend"
        resultado = await strategy.traduzir( texto_original )

        print( f"   Resultado Mistral: {resultado}" )
        assert resultado is not None

    except ErroChaveProvedor:
        pytest.skip( "Chave de API do Mistral não configurada." )
    except Exception as e:
        pytest.fail( f"Erro Mistral: {e}" )


# --- TESTE DEEPL ---
@pytest.mark.asyncio
async def test_deepl_integration():
    """
    Testa a API do DeepL (Lembrando que implementamos com Threads).
    """
    print( "\n🌊 Testando DeepL..." )
    try:
        factory = DeepLStrategyFactory()
        strategy = factory.criar_estrategia()

        texto_original = "Software Engineering"
        resultado = await strategy.traduzir( texto_original )

        print( f"   Resultado DeepL: {resultado}" )

        assert "Engenharia" in resultado

    except ErroChaveProvedor:
        pytest.skip( "Chave de API do DeepL não configurada." )
    except Exception as e:
        pytest.fail( f"Erro DeepL: {e}" )
