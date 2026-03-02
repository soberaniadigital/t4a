import asyncio
import sys
import os

sys.path.append( os.getcwd() )

from src.infrastructure.providers.deepl.factory import DeepLStrategyFactory


def main():
    print( "--- Teste Manual: DeepL ---" )

    fabrica = DeepLStrategyFactory()
    estrategia = fabrica.criar_estrategia()

    mensagem = "Software Architecture is cool"

    print( f"Traduzindo: '{mensagem}'..." )
    result = estrategia.traduzir( mensagem )

    print( f"Resultado: {result}" )


if __name__ == "__main__":
    main()
