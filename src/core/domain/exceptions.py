class ErroBase( Exception ):
    """
        Exceção base para todos os erros.
    """

    def __init__( self, mensagem: str = "Erro na aplicação.", detalhe: str = '' ):
        self.mensagem = mensagem

        # Garante que o Exception seja inicializada corretamente com a mensagem de erro
        super().__init__( mensagem )

    # Controla como a sua exceção é exibida como texto para o usuário final
    def __str__( self ):
        return self.mensagem


class ErroCriarCliente( ErroBase ):
    def __init__( self, mensagem: str = 'Erro ao criar o cliente.', detalhe: str = '' ):
        super().__init__( mensagem )
        self.detalhe = detalhe

    def __str__( self ):
        if self.detalhe:
            return f'[Provedor: {self.detalhe}] {self.mensagem}'
        return f'{self.mensagem}'


class ErroChaveProvedor( ErroBase ):
    def __init__( self, mensagem: str = 'Erro ao buscar chave da API.', detalhe: str = '' ):
        super().__init__( mensagem )
        self.detalhe = detalhe

    def __str__( self ):
        if self.detalhe:
            return f'[Provedor: {self.detalhe}] {self.mensagem}'
        return f'{self.mensagem}'


class ErroNomeProvedor( ErroBase ):
    def __init__( self, mensagem: str = 'Erro ao buscar provedor no dicionário.', detalhe: str = '' ):
        super().__init__( mensagem )
        self.detalhe = detalhe


class ErroCarregarArquivo( ErroBase ):
    def __init__( self, mensagem: str = 'Erro ao carregar arquivo.', detalhe: str = '' ):
        super().__init__( mensagem )
        self.detalhe = detalhe


class ErroSalvarArquivo( ErroBase ):
    def __init__( self, mensagem: str = 'Erro ao salvar arquivo.', detalhe: str = '' ):
        super().__init__( mensagem )
        self.detalhe = detalhe


class ErroFormatoResposta( ErroBase ):
    """
    Levantada quando a resposta (JSON) não segue o formato esperado estrito.
    """

    def __init__( self, mensagem: str = 'Formato de resposta inválido.', detalhe: str = '' ):
        super().__init__( mensagem, detalhe )
        self.detalhe = detalhe

    def __str__( self ):
        if self.detalhe:
            return f'[Validação] {self.mensagem} Detalhe: {self.detalhe}'
        return self.mensagem
