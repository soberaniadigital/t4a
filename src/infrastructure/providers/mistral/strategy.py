# Interface
from src.core.interfaces.translation_strategy import TranslationStrategy

# Biblioteca
from mistralai import Mistral
from mistralai.models import ResponseFormat, UserMessage, SystemMessage

# Core
from src.core.config.settings import MISTRAL_MODEL_NAME, MISTRAL_GENERATION_CONFIG, SYSTEM_INSTRUCTION

import importlib.metadata
from typing import Any


class MistralStrategy( TranslationStrategy ):
    """
        Estratégia de tradução usando a API do Mistral.
        Este serviço consegue realizar tradução direta e usando contexto.
    """

    def __init__( self, cliente: Mistral ):
        self.cliente = cliente

    def traduzir( self, mensagem: str ) -> str:
        """
        Realizar a tradução de um texto num determinado idioma.

        Para o Mistral, é necessário que a mensagem esteja formatada usando "role: user".
        :param mensagem: Mensagem a ser enviado.
        :return: Texto traduzido para o idioma configurado.
        """
        try:
            response = self.cliente.chat.complete(
                model = MISTRAL_MODEL_NAME,
                messages = [
                    SystemMessage( content = SYSTEM_INSTRUCTION ),
                    UserMessage( content = mensagem )
                ],
                response_format = ResponseFormat( type = "json_object" ),
                temperature = MISTRAL_GENERATION_CONFIG.get( "temperature", 0.2 ),
                top_p = MISTRAL_GENERATION_CONFIG.get( "top_p", 1 ),
                max_tokens = MISTRAL_GENERATION_CONFIG.get( "max_tokens", 2048 ),
                safe_prompt = MISTRAL_GENERATION_CONFIG.get( "safe_prompt", False ),
                random_seed = MISTRAL_GENERATION_CONFIG.get( "random_seed", None )
            )
            return response.choices[ 0 ].message.content
        except Exception as error:
            raise error

    def obter_configuracao( self ) -> dict[ str, Any ]:
        try:
            version = importlib.metadata.version( "mistralai" )
        except importlib.metadata.PackageNotFoundError:
            version = "unknown"

        return {
            "provider": "Mistral AI",
            "model_name": MISTRAL_MODEL_NAME,
            "library_version": version,
            "generation_config": MISTRAL_GENERATION_CONFIG
        }
