# ARQUIVO: src/shared/utils/console_progress.py
import sys
import time


class ConsoleProgressBar:
    """
    Gerencia a exibição visual de progresso no terminal.
    Agora com contador (x/y) e estimativa de tempo (ETA).
    """

    def __init__( self, total: int, prefixo: str = 'Progresso', tamanho_barra: int = 30 ):
        self.total = total
        self.prefixo = prefixo
        self.tamanho_barra = tamanho_barra
        self.atual = 0
        self.inicio = time.time()  # Marca o timestamp inicial

    def incrementar( self ):
        """Avança uma unidade e atualiza a tela."""
        self.atual += 1
        self._atualizar_tela()

    def _formatar_tempo( self, segundos: float ) -> str:
        """Converte segundos em formato MM:SS."""
        if segundos < 0:
            return "00:00"
        m, s = divmod( int( segundos ), 60 )
        return f"{m:02d}:{s:02d}"

    def _atualizar_tela( self ):
        if self.total == 0:
            return

        # 1. Cálculos Básicos
        percentual = 100 * (self.atual / self.total)
        preenchido = int( self.tamanho_barra * self.atual // self.total )

        # 2. Construção da Barra
        barra = '\033[32m█\033[0m' * preenchido + '-' * (self.tamanho_barra - preenchido)

        # 3. Cálculo do ETA (Tempo Estimado)
        agora = time.time()
        decorrido = agora - self.inicio

        # Evita divisão por zero no primeiro milissegundo
        if self.atual > 0 and decorrido > 0:
            velocidade_media = self.atual / decorrido  # itens por segundo
            itens_restantes = self.total - self.atual
            eta_segundos = itens_restantes / velocidade_media
            eta_str = self._formatar_tempo( eta_segundos )
        else:
            eta_str = "--:--"

        # 4. Formatação Final
        # Layout: Progresso: |████------| 40.0% [20/50] ETA: 00:15
        contador_str = f"[{self.atual}/{self.total}]"

        msg = (
            f"\r{self.prefixo}: |{barra}| "
            f"{percentual:.1f}% {contador_str} "
            f"ETA: {eta_str}"
        )

        sys.stdout.write( msg )
        sys.stdout.flush()

    def finalizar( self ):
        """Pula para a próxima linha e exibe tempo total."""
        tempo_total = time.time() - self.inicio
        sys.stdout.write( f" - Concluído em {self._formatar_tempo( tempo_total )}\n" )
