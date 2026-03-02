# Biblioteca
from mistralai import Mistral

# Core
from src.core.interfaces.strategy_factory import StrategyFactory
from src.core.config.settings import MISTRAL_NOME
from src.core.config.env import AppConfig
from src.core.domain.exceptions import ErroChaveProvedor, ErroCriarCliente

# Estratégia
from src.infrastructure.providers.mistral.strategy import MistralStrategy


class MistralStrategyFactory( StrategyFactory ):
    """
        Classe para criar uma estratégia para o Mistral.
        Lida com validação da chave usada, configuração e conexão.
    """

    @staticmethod
    def _validar_chave():
        """
            Método privado para verificar se localiza a chave da API.
        """
        if AppConfig.mistral_api_key is None:
            raise ErroChaveProvedor( detalhe = MISTRAL_NOME )

    @staticmethod
    def _conectar_cliente():
        """
            Método privado para conectar o cliente.
        """
        # GeminiTexts.connecting_to_client()
        try:
            cliente = Mistral( api_key = AppConfig.mistral_api_key )
            # GeminiTexts.connected_to_client()
            return cliente

        except Exception as error:
            raise ErroCriarCliente( detalhe = MISTRAL_NOME ) from error

    def criar_estrategia( self ) -> MistralStrategy:
        """
            Método que retorna uma instância da estratégia do Mistral.
        """
        self._validar_chave()
        cliente: Mistral.Client = self._conectar_cliente()

        return MistralStrategy(
            cliente = cliente,
        )


if __name__ == '__main__':
    fabrica: MistralStrategyFactory = MistralStrategyFactory()
    estrategia: MistralStrategy = fabrica.criar_estrategia()

    mensagem: str = "Traduza 'I love You!' para a Língua Português do Brasil."
    result = estrategia.traduzir( mensagem )
    print( result )
