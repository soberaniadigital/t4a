"""
Uso do Design Pattern 'Strategy'.

Todos os serviços de prompt serão implementados seguindo a 'interface' PromptStrategy.
"""

from abc import ABC, abstractmethod
from string import Template


class PromptStrategy( ABC ):
    """
    'Interface' para prompt direto ou com contexto.
    """

    def __init__( self, template: Template ):
        self.template: Template = template

    @abstractmethod
    def construir_prompt( self, texto_original: str, contexto: dict[ str, str ] = None ) -> str:
        """
        Realizar a criação do prompt utilizando o texto que deseja traduzir e o contexto
        (se disponível).
        :param texto_original: Texto do arquivo que deseja traduzir.
        :param contexto: Traduções em outros idiomas do arquivo que deseja traduzir.
        :return: Prompt criado.
        """
        pass
