# Biblioteca
from ollama import Client

# Core
from src.core.interfaces.strategy_factory import StrategyFactory
from src.core.config.settings import LLAMA_NOME
from src.core.config.env import AppConfig
from src.core.domain.exceptions import ErroChaveProvedor, ErroCriarCliente

# Estratégia
from src.infrastructure.providers.llama.strategy import LlamaStrategy


class LlamaStrategyFactory( StrategyFactory ):
    """
        Classe para criar uma estratégia para o Llama.
        Lida com validação da chave usada, configuração e conexão.
    """

    @staticmethod
    def _validar_host():
        """
            Método privado para verificar se localiza a URL do Llama.
        """
        if AppConfig.llama_url is None:
            raise ErroChaveProvedor( mensagem = "Erro ao localizar URL.", detalhe = LLAMA_NOME )

    @staticmethod
    def _conectar_cliente():
        """
            Método privado para conectar o cliente.
        """
        try:
            cliente = Client( host = AppConfig.llama_url )
            return cliente
        except Exception as error:
            raise ErroCriarCliente( detalhe = LLAMA_NOME ) from error

    def criar_estrategia( self ) -> LlamaStrategy:
        """
            Método que retorna uma instância da estratégia do Llama.
        """
        self._validar_host()
        cliente: Client = self._conectar_cliente()

        return LlamaStrategy(
            cliente = cliente,
        )


if __name__ == "__main__":
    fabrica = LlamaStrategyFactory()
    estrategia = fabrica.criar_estrategia()

    mensagem: str = "Traduza 'I love You!' para a Língua Português do Brasil."
    result = estrategia.traduzir( mensagem )
    print( result )
