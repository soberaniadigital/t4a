from abc import ABC, abstractmethod
from typing import List
from src.core.dto.evaluation_input import EvaluationInput
from src.core.dto.pipeline_result import PipelineResult


class MetricsPipeline( ABC ):
    """Interface para pipelines de métricas."""

    @abstractmethod
    def compute( self, input_data: EvaluationInput ) -> PipelineResult:
        """Calcula a métrica para todos os segmentos."""
        pass

    @abstractmethod
    def metric_name( self ) -> str:
        """Nome da métrica (para CSV/colunas)."""
        pass
