# Biblioteca
from google import genai

# Core
from src.core.interfaces.strategy_factory import StrategyFactory
from src.core.config.settings import GEMINI_NOME
from src.core.config.env import AppConfig
from src.core.domain.exceptions import ErroChaveProvedor, ErroCriarCliente

# Estratégia
from src.infrastructure.providers.gemini.strategy import GeminiStrategy


class GeminiStrategyFactory( StrategyFactory ):
    """
        Classe para criar uma estratégia para o Gemini.
        Lida com validação da chave usada, configuração e conexão.
    """

    @staticmethod
    def _validar_chave():
        """
            Método privado para verificar se localiza a chave da API.
        """
        if AppConfig.gemini_api_key is None:
            raise ErroChaveProvedor( detalhe = GEMINI_NOME )

    @staticmethod
    def _conectar_cliente():
        """
            Método privado para conectar o cliente.
        """
        try:
            cliente = genai.Client( api_key = AppConfig.gemini_api_key )
            return cliente

        except Exception as error:
            raise ErroCriarCliente( detalhe = GEMINI_NOME ) from error

    def criar_estrategia( self ) -> GeminiStrategy:
        """
            Método que retorna uma instância da estratégia do Gemini.
        """
        self._validar_chave()
        cliente: genai.Client = self._conectar_cliente()

        return GeminiStrategy(
            cliente = cliente,
        )


if __name__ == "__main__":
    fabrica = GeminiStrategyFactory()
    estrategia = fabrica.criar_estrategia()

    mensagem: str = "Traduza 'I love You!' para a Língua Português do Brasil."
    result = estrategia.traduzir( mensagem )
    print( result )
