from src.infrastructure.io.po_file_adapter import PoFileAdapter


class ContextService:
    """
    Classe responsável por manipular as informações dos arquivos de contexto.
    """

    def __init__( self, caminhos_arquivos: list[ list[ str ] ], po_handler: PoFileAdapter ):
        """
        Necessário passar caminhos_arquivos e po_handler.

        :param caminhos_arquivos: Lista contendo uma lista com as informações: caminho do arquivo de
            contexto e o seu idioma.
        :param po_handler: Instância do PoHandler.
        """
        self.contexto = None
        self.dicionario: dict[ str, dict ] = { }
        self.caminhos_arquivos: list[ list[ str ] ] = caminhos_arquivos
        self.po_handler: PoFileAdapter = po_handler
        self._preparar_dicionario()

    def _preparar_dicionario( self ):
        """
        Método privado para criar um dicionário onde as chaves são os idiomas e os valores as informações
        dos arquivos de contexto em lista.
        """
        for item in self.caminhos_arquivos:
            caminho: str = item[ 0 ]
            idioma: str = item[ 1 ]
            self.dicionario[ idioma ] = self.po_handler.carregar_arquivo( caminho )

    def obter_contexto( self, chave: str ) -> dict[ str, str ]:
        """
        Método para obter as traduções do conteúdo de chave nos demais idiomas.
        :param chave: Qual a chave para buscar nos itens do dicionário.
        :return: Dicionário contendo idioma na chave e conteúdo no valor.
        """
        self.contexto: dict[ str, str ] = { }
        for idioma, conteudo in self.dicionario.items():
            self.contexto[ idioma ] = conteudo[ chave ]
        return self.contexto
