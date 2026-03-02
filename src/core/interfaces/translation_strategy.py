"""
Uso do Design Pattern Strategy.

Todos os serviços de tradução serão implementados seguindo a 'interface' TranslationStrategy.
"""

from abc import ABC, abstractmethod
from typing import Any


class TranslationStrategy( ABC ):
    """
    ‘Interface’ para as estratégias de tradução:
        - Gemini
        - Mistral
        - DeepL
        - Llama
        - ...
    """

    @abstractmethod
    def traduzir( self, mensagem: str ) -> str:
        """
        Realizar a tradução de um texto num determinado idioma.
        :param mensagem: Mensagem a ser enviado.
        :return: Texto traduzido para o idioma configurado.
        """
        pass

    @abstractmethod
    def obter_configuracao( self ) -> dict[ str, Any ]:
        """
        Retorna os metadados técnicos da estratégia.
        Ex: Nome do modelo, temperatura, top_p, versão da lib.
        """
        pass
