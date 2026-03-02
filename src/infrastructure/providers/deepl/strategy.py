# Interface
from src.core.interfaces.translation_strategy import TranslationStrategy

# Biblioteca
from deepl import Translator

# Core
from src.core.config.settings import DEEP_L_LANGUAGE

import importlib.metadata
from typing import Dict, Any


class DeepLStrategy( TranslationStrategy ):
    """
        Estratégia de tradução usando a API do DeepL.
        Este serviço consegue realizar tradução direta e usando contexto.
    """

    def __init__( self, cliente: Translator ):
        self.cliente = cliente
        self.idioma_alvo: str = DEEP_L_LANGUAGE

    def traduzir( self, mensagem: str ) -> str:
        """
        Realizar a tradução de um texto num determinado idioma.

        :param mensagem: Mensagem a ser enviado.
        :return: Texto traduzido para o idioma configurado.
        """
        try:
            response = self.cliente.translate_text(
                text = mensagem,
                target_lang = self.idioma_alvo
            )
            return response.text
        except Exception as error:
            raise error

    def obter_configuracao( self ) -> Dict[ str, Any ]:
        try:
            version = importlib.metadata.version( "deepl" )
        except importlib.metadata.PackageNotFoundError:
            version = "unknown"

        return {
            "provider": "DeepL",
            "model_name": "DeepL Standard (API)",
            "library_version": version,
            "target_language": self.idioma_alvo,
            "generation_config": {
                "type": "NMT (Neural Machine Translation)",
                "context_aware": True
            }
        }
