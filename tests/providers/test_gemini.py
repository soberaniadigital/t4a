import asyncio
import sys
import os

sys.path.append( os.getcwd() )

from src.infrastructure.providers.gemini.factory import GeminiStrategyFactory


async def main():
    print( "--- Teste Manual: Gemini ---" )

    try:
        fabrica = GeminiStrategyFactory()
        estrategia = fabrica.criar_estrategia()

        mensagem = "Translate the phrase 'Software Architecture is cool' into Brazilian Portuguese. Do not add any other content."

        print( f"Traduzindo: '{mensagem}'..." )
        result = await estrategia.traduzir( mensagem )

        print( f"Resultado: {result}" )
    except Exception as e:
        print( f"Erro: {e}" )


if __name__ == "__main__":
    asyncio.run( main() )
