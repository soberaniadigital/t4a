# Biblioteca
from deepl import Translator

# Core
from src.core.interfaces.strategy_factory import StrategyFactory
from src.core.config.settings import DEEPL_NOME
from src.core.config.env import AppConfig
from src.core.domain.exceptions import ErroChaveProvedor, ErroCriarCliente

# Estratégia
from src.infrastructure.providers.deepl.strategy import DeepLStrategy


class DeepLStrategyFactory( StrategyFactory ):
    """
        Classe para criar uma estratégia para o DeepL.
        Lida com validação da chave usada, configuração e conexão.
    """

    @staticmethod
    def _validar_chave():
        """
            Método privado para verificar se localiza a chave da API.
        """
        if AppConfig.deepl_api_key is None:
            raise ErroChaveProvedor( detalhe = DEEPL_NOME )

    @staticmethod
    def _conectar_cliente():
        """
            Método privado para conectar o cliente.
        """
        try:
            cliente = Translator( auth_key = AppConfig.deepl_api_key, )
            return cliente

        except Exception as error:
            raise ErroCriarCliente( detalhe = DEEPL_NOME ) from error

    def criar_estrategia( self ) -> DeepLStrategy:
        """
            Método que retorna uma instância da estratégia do DeepL.
        """
        self._validar_chave()
        cliente: Translator = self._conectar_cliente()

        return DeepLStrategy(
            cliente = cliente,
        )


if __name__ == "__main__":
    fabrica = DeepLStrategyFactory()
    estrategia = fabrica.criar_estrategia()

    mensagem: str = "I love You!"
    result = estrategia.traduzir( mensagem )
    print( result )
