import logging
from src.core.ioc.bootstrap import build_translator_service
from src.application.dto.pipeline_result import PipelineResult
from src.application.dto.translation_job import TranslationJob
from src.application.services.translator_service import TranslatorService

logger = logging.getLogger( __name__ )


class TranslationPipeline:
    """
    Responsabilidade: Executar a lógica de tradução de ponta a ponta para UM job.
    Não sabe nada sobre threads.
    """

    def run( self, job: TranslationJob ) -> PipelineResult:
        logger.info( f"▶️  [Pipeline] Iniciando: {job.nome_estrategia}" )

        try:
            service: TranslatorService = build_translator_service()
            service.executar_traducao( job )

            return PipelineResult(
                sucesso = True,
                caminho_saida_gerado = job.arquivo_saida,
                erro = None
            )

        except Exception as e:
            logger.error( f"❌ [Pipeline] Falha em {job.nome_estrategia}: {e}" )
            return PipelineResult(
                sucesso = False,
                caminho_saida_gerado = "",
                erro = str( e )
            )
