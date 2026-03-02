import time
import random


def executar_tarefa():
    total_iters = 50  # Imagine que são 50 arquivos para baixar
    tamanho_barra = 30  # A barra terá 30 caracteres de largura visual

    print( "Iniciando Download..." )

    for i in range( total_iters + 1 ):
        time.sleep( 0.1 )  # Simula o tempo de processamento de cada item

        # 1. Calcula a porcentagem atual
        percentual = 100 * (i / total_iters)

        # 2. Calcula quantos blocos preencher baseados no tamanho da barra
        # (Regra de 3 simples: se 100% é 30 blocos, X% é Y blocos)
        preenchido = int( tamanho_barra * i // total_iters )

        # 3. Monta a string visual
        barra = '█' * preenchido + '-' * (tamanho_barra - preenchido)

        # 4. O PRINT MÁGICO
        # \r -> Volta o cursor para o início da linha
        # end='' -> Não pula para a próxima linha
        # flush=True -> Força a atualização visual imediata
        print( f'\rStatus: |{barra}| {percentual:.1f}%', end = '', flush = True )

    print( "\nConcluído!" )


def multiplas_barras():
    # Definindo o estado inicial dos 3 downloads
    progressos = [ 0, 0, 0 ]
    tamanho_barra = 20

    # Código ANSI para mover o cursor 1 linha para cima
    CURSOR_UP = '\033[F'

    print( "Iniciando downloads simultâneos...\n" )  # \n extra para dar espaço

    while any( p < 100 for p in progressos ):
        time.sleep( 0.1 )

        # Gera o desenho das 3 barras
        output_buffer = ""
        for i, p in enumerate( progressos ):
            # Incrementa aleatoriamente cada barra até 100
            if p < 100:
                progressos[ i ] = min( 100, p + random.randint( 1, 4 ) )

            # Monta o visual
            blocos = int( tamanho_barra * progressos[ i ] / 100 )
            barra = '█' * blocos + '-' * (tamanho_barra - blocos)
            output_buffer += f"Arquivo {i + 1}: |{barra}| {progressos[ i ]}%\n"

        # O TRUQUE:
        # 1. Printamos todo o bloco de texto (as 3 barras)
        print( output_buffer, end = '', flush = True )

        # 2. Se não acabou, movemos o cursor 3 linhas para CIMA para
        # que o próximo loop sobrescreva essas linhas
        if any( p < 100 for p in progressos ):
            print( CURSOR_UP * 3, end = '', flush = True )

    print( "Todos os downloads concluídos!" )


if __name__ == "__main__":
    # executar_tarefa()
    multiplas_barras()
