import sys
import os
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.append( os.getcwd() )

from src.application.dto.translation_job import TranslationJob
from src.shared.utils.path_helper import construir_caminho_saida

from src.application.services.translator_service import TranslatorService
from src.core.config.settings import LLAMA_NOME, GEMINI_NOME, MISTRAL_NOME, DEEPL_NOME

from src.core.ioc.bootstrap import build_translator_service


def main():
    # 1. Configurações
    # Você pode trocar por GEMINI_NOME ou MISTRAL_NOME para testar outros
    ESTRATEGIA_ESCOLHIDA = LLAMA_NOME

    BASE_DIR = os.getcwd()
    ARQUIVO_ENTRADA = os.path.join( BASE_DIR, "resultados/teste_service_output.po" )
    ARQUIVO_SAIDA = construir_caminho_saida(
        arquivo_entrada = ARQUIVO_ENTRADA,
        diretorio_base_saida = f"{BASE_DIR}/resultados",
        nome_estrategia = ESTRATEGIA_ESCOLHIDA
    )
    # Verificação básica de segurança
    if not os.path.exists( ARQUIVO_ENTRADA ):
        print( f"❌ Erro: Arquivo de entrada não encontrado em: {ARQUIVO_ENTRADA}" )
        return

    try:
        # 2. Instanciação do Serviço
        service: TranslatorService = build_translator_service()
        requisicao: TranslationJob = TranslationJob(
            nome_estrategia = ESTRATEGIA_ESCOLHIDA,
            arquivo_entrada = ARQUIVO_ENTRADA,
            arquivo_saida = ARQUIVO_SAIDA,
        )

        service.executar_traducao( requisicao )

    except Exception as e:
        print( f"\n☠️ Falha no teste do serviço: {e}" )
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
