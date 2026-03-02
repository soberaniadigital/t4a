# Interfaces
from src.core.interfaces.translation_strategy import TranslationStrategy

# Bibliotecas
from google import genai
from google.genai import types

# Core
from src.core.config.settings import GEMINI_MODEL_NAME, GEMINI_GENERATION_CONFIG, SYSTEM_INSTRUCTION

import importlib.metadata
from typing import Any


class GeminiStrategy( TranslationStrategy ):
    """
        Estratégia de tradução usando a API do Google Gemini.
        Este serviço consegue realizar tradução direta e usando contexto.
    """

    def __init__( self, cliente: genai.Client ):
        self.cliente = cliente

    def traduzir( self, mensagem: str ) -> str:
        try:
            response = self.cliente.models.generate_content(
                model = GEMINI_MODEL_NAME,
                contents = mensagem,
                config = types.GenerateContentConfig(
                    system_instruction = SYSTEM_INSTRUCTION,
                    response_mime_type = "application/json",
                    temperature = GEMINI_GENERATION_CONFIG.get( "temperature", 0.2 ),
                    top_p = GEMINI_GENERATION_CONFIG.get( "top_p", 1 ),
                    top_k = GEMINI_GENERATION_CONFIG.get( "top_k", 1 ),
                    max_output_tokens = GEMINI_GENERATION_CONFIG.get( "max_output_tokens", 2048 ),

                    safety_settings = GEMINI_GENERATION_CONFIG.get( "safety_settings" )
                )
            )
            return response.parts[ 0 ].text
        except Exception as error:
            print( f'Erro: {error}' )
            raise error

    def obter_configuracao( self ) -> dict[ str, Any ]:
        """
        Retorna metadados para reprodutibilidade científica.
        """
        try:
            # O nome do pacote no PIP é google-generativeai
            version = importlib.metadata.version( "google-generativeai" )
        except importlib.metadata.PackageNotFoundError:
            version = "unknown"

        return {
            "provider": "Google Gemini",
            "model_name": GEMINI_MODEL_NAME,
            "library_version": version,
            "generation_config": GEMINI_GENERATION_CONFIG,
            "api_endpoint": "google.genai.Client"
        }
