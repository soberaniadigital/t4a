from abc import ABC, abstractmethod

from src.core.interfaces.translation_strategy import TranslationStrategy


class StrategyFactory( ABC ):
    """
        Classe que representa uma ‘interface’ para as fábricas de estratégias.
    """

    @abstractmethod
    def criar_estrategia( self ) -> TranslationStrategy:
        """
            Método que retorna uma instância da estratégia.
        """
        pass
