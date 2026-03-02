from src.application.dto.translation_job import TranslationJob
from src.application.dto.pipeline_result import PipelineResult
from src.core.ioc.bootstrap import build_translator_service
from src.application.pipelines.translation_pipeline import TranslationPipeline


class TranslationWorker:
    """
    Responsável por instanciar e executar o pipeline para um único Job.
    """

    @staticmethod
    def execute( job: TranslationJob ) -> tuple[ str, PipelineResult ]:
        pipeline = TranslationPipeline()
        resultado = pipeline.run( job )

        return job.nome_estrategia, resultado
