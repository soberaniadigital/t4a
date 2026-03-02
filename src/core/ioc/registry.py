# Core
from src.core.domain.exceptions import ErroNomeProvedor
from src.core.interfaces.strategy_factory import StrategyFactory

"""
    O fluxo de uso será:
    
        - No início da execução, irá criar uma instância de cada implementação de 
        StrategyFactory e adicionar ao dicionário.
        - Quando o provedor for escolhido, utilizar método 'buscar_fabrica' passando
        o nome do provedor, para obter a instância dele.
"""


class StrategyRegistry:
    """
        Classe para registrar as fábricas de estratégias.
        Mapeia o nome do provedor (‘string’) para uma InterfaceFabricaEstrategia.
    """

    def __init__( self ):
        self.fabricas: dict[ str, StrategyFactory ] = { }

    def registrar( self, nome_fabrica: str, fabrica: StrategyFactory ):
        """
        Registrar no dicionário a implementação da fábrica de InterfaceFabricaEstrategia.

        :param nome_fabrica: Nome do provedor da fábrica.
        :param fabrica: Instância da fábrica.
        """

        self.fabricas[ nome_fabrica ] = fabrica

    def buscar_fabrica( self, nome_fabrica: str ) -> StrategyFactory:
        """
        Busca uma fábrica cadastrada no dicionário.
        """

        try:
            return self.fabricas.get( nome_fabrica )
        except KeyError:
            raise ErroNomeProvedor(
                mensagem = f'Erro ao buscar {nome_fabrica} no dicionário. Necessário registrar a fábrica.' )
