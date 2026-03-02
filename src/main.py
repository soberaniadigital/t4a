import sys
import logging
from pathlib import Path

# --- 1. SETUP DE AMBIENTE ---
# Garante que o Python encontre a pasta 'src' independente de onde o script seja chamado.
ROOT_DIR = Path( __file__ ).resolve().parent.parent
sys.path.append( str( ROOT_DIR ) )

# Configuração de Logs
logging.basicConfig(
    level = logging.INFO,
    format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename = 'execucao.log',  # <--- MUDANÇA AQUI
    filemode = 'w'
)
console_handler = logging.StreamHandler()
console_handler.setLevel( logging.ERROR )
logging.getLogger().addHandler( console_handler )
logger = logging.getLogger( __name__ )

# --- IMPORTS DA APLICAÇÃO ---
# DTOs
from src.application.dto.translation_job import TranslationJob
from src.application.dto.translation_context import ContextoTraducao

# Runners e Pipelines
from src.application.runners.parallel_runner import ParallelRunner
from src.application.pipelines.evaluation_pipeline import EvaluationPipeline

# Utils e Configs
from src.shared.utils.path_helper import construir_caminho_saida
from src.core.config.settings import LLAMA_NOME, GEMINI_NOME, MISTRAL_NOME, DEEPL_NOME

# --- 2. CONFIGURAÇÃO DE EXECUÇÃO (USER INPUT) ---

# Escolha o modo: "TRADUZIR" ou "AVALIAR"
MODO_OPERACAO = "TRADUZIR"

# Configurações de Arquivos
BASE_INPUT_DIR = ROOT_DIR / "data" / "extracted"
BASE_OUTPUT_DIR = ROOT_DIR / "resultados"

# Arquivo que será processado (deve estar na pasta data/input)
NOME_ARQUIVO_ALVO = "sed/sed-4.8.44.de.po"

# Lista de provedores que serão executados no modo TRADUZIR
# PROVEDORES_ATIVOS = [
#     LLAMA_NOME,
#     GEMINI_NOME,
#     MISTRAL_NOME,
#     DEEPL_NOME
# ]

PROVEDORES_ATIVOS = [
    LLAMA_NOME,
]

# Provedor específico que será analisado no modo AVALIAR
PROVEDOR_PARA_AVALIACAO = LLAMA_NOME


# --- 3. MÉTODOS AUXILIARES (FACTORIES & LOGIC) ---

def criar_jobs_traducao( arquivo_entrada: Path ) -> list[ TranslationJob ]:
    """
    Fábrica de Jobs: Prepara todas as configurações necessárias para
    que o Runner possa executar as threads.
    """
    jobs = [ ]

    # Prepara contextos (se existirem)
    contextos = [ ]
    path_ctx_de = BASE_INPUT_DIR / "file_en_de.po"
    path_ctx_fr = BASE_INPUT_DIR / "file_en_fr.po"

    if path_ctx_de.exists(): contextos.append( ContextoTraducao( str( path_ctx_de ), "DE" ) )
    if path_ctx_fr.exists(): contextos.append( ContextoTraducao( str( path_ctx_fr ), "FR" ) )

    # Cria um Job para cada estratégia configurada
    for estrategia in PROVEDORES_ATIVOS:
        # Gera o caminho de saída padronizado
        caminho_saida = construir_caminho_saida(
            arquivo_entrada = str( arquivo_entrada ),
            diretorio_base_saida = str( BASE_OUTPUT_DIR ),
            nome_estrategia = estrategia
        )

        job = TranslationJob(
            nome_estrategia = estrategia,
            arquivo_entrada = str( arquivo_entrada ),
            arquivo_saida = caminho_saida,
            contextos = contextos
        )
        jobs.append( job )

    return jobs


def executar_modo_traducao( arquivo_entrada: Path ):
    """Orquestra a execução paralela de traduções."""
    print( "=" * 60 )
    print( f"🚀 MODO TRADUÇÃO ATIVO" )
    print( f"📄 Arquivo Alvo: {arquivo_entrada.name}" )
    print( f"🧵 Estratégias: {', '.join( PROVEDORES_ATIVOS )}" )
    print( "=" * 60 )

    # 1. Preparar o Trabalho
    jobs = criar_jobs_traducao( arquivo_entrada )

    # 2. Executar em Paralelo (Gerenciamento de Threads oculto no Runner)
    runner = ParallelRunner( max_workers = 4 )
    resultados = runner.processar_batch( jobs )

    # 3. Relatório Simplificado
    print( "\n🏁 RESUMO DA OPERAÇÃO:" )
    for res in resultados:
        status = "✅ SUCESSO" if res.sucesso else "❌ FALHA"
        nome_arquivo = Path( res.caminho_saida_gerado ).name if res.caminho_saida_gerado else "N/A"
        print( f"   • {status} -> {nome_arquivo}" )
        if not res.sucesso:
            print( f"     Erro: {res.erro}" )


def executar_modo_avaliacao( arquivo_referencia: Path ):
    """Orquestra a avaliação de uma tradução específica."""
    print( "=" * 60 )
    print( f"⚖️  MODO AVALIAÇÃO ATIVO" )
    print( f"🔍 Analisando Estratégia: {PROVEDOR_PARA_AVALIACAO}" )
    print( "=" * 60 )

    # 1. Determinar onde está o arquivo traduzido (Hipótese)
    # Usamos o mesmo utilitário para garantir que vamos buscar no lugar certo
    caminho_hipotese = construir_caminho_saida(
        arquivo_entrada = str( arquivo_referencia ),
        diretorio_base_saida = str( BASE_OUTPUT_DIR ),
        nome_estrategia = PROVEDOR_PARA_AVALIACAO
    )

    if not Path( caminho_hipotese ).exists():
        print( f"❌ Erro: Arquivo traduzido não encontrado." )
        print( f"   Caminho esperado: {caminho_hipotese}" )
        print( "   Dica: Rode o modo TRADUZIR para esta estratégia antes." )
        return

    # 2. Executar Pipeline de Avaliação
    pipeline = EvaluationPipeline()
    metricas = pipeline.run(
        arquivo_referencia = str( arquivo_referencia ),
        arquivo_traduzido = caminho_hipotese
    )

    # 3. Exibir Resultados
    if metricas:
        print( "\n📊 RESULTADOS DAS MÉTRICAS:" )
        print( "-" * 30 )
        for m in metricas:
            print( f"   • {m.nome.ljust( 15 )}: {m.score:.4f}" )
            print( f"     Desc: {m.descricao}" )
            print( "-" * 30 )
    else:
        print( "\n⚠️ Nenhuma métrica gerada. Verifique os logs." )


# --- 4. BLOCO PRINCIPAL (ENTRY POINT) ---

def main():
    # Validação inicial do arquivo de entrada
    arquivo_entrada = BASE_INPUT_DIR / NOME_ARQUIVO_ALVO

    if not arquivo_entrada.exists():
        logger.error( f"Arquivo de entrada não encontrado: {arquivo_entrada}" )
        return

    # Seletor de Fluxo
    if MODO_OPERACAO == "TRADUZIR":
        executar_modo_traducao( arquivo_entrada )

    elif MODO_OPERACAO == "AVALIAR":
        executar_modo_avaliacao( arquivo_entrada )

    else:
        print( f"Modo '{MODO_OPERACAO}' inválido. Use 'TRADUZIR' ou 'AVALIAR'." )


if __name__ == "__main__":
    main()
