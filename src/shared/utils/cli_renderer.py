# ARQUIVO: src/shared/utils/cli_renderer.py
import os
from src.application.dto.translation_job import TranslationJob

LARGURA_BARRA: int = 100


def exibir_resumo_requisicao( requisicao: TranslationJob ):
    """
    Renderiza um cartão visual no terminal com os detalhes da requisição.
    Não retorna nada, apenas imprime (Side Effect intencional de UI).
    """
    # Limpa um pouco a visualização pegando apenas o nome do arquivo, não o caminho todo
    nome_arquivo_entrada = os.path.basename( requisicao.arquivo_entrada )
    nome_arquivo_saida = os.path.basename( requisicao.arquivo_saida )

    print( "\n" + "=" * LARGURA_BARRA )
    print( f"📋 RESUMO DA OPERAÇÃO DE TRADUÇÃO" )
    print( "=" * LARGURA_BARRA )

    # Seção Principal
    print( f"🧠  Estratégia          : {requisicao.nome_estrategia.upper()}" )
    print( f"📄  Arquivo de Entrada  : {nome_arquivo_entrada}" )
    print( f"💾  Arquivo de Saída    : {nome_arquivo_saida}" )

    # Seção de Contexto (Condicional)
    print( "-" * LARGURA_BARRA )
    if requisicao.contextos:
        print( f"📚  Contexto Carregado ({len( requisicao.contextos )} arquivos):" )
        for ctx in requisicao.contextos:
            nome_ctx = os.path.basename( ctx.caminho )
            print( f"    • [{ctx.idioma}] {nome_ctx}" )
    else:
        print( "📚  Contexto            : Nenhum (Zero-shot)" )

    print( "=" * LARGURA_BARRA + "\n" )
