from dataclasses import dataclass
from typing import List
from src.core.dto.evaluation_input import EvaluationInput
from src.core.dto.pipeline_result import PipelineResult


@dataclass( frozen = True )
class EvaluationResult:
    """Resultado final de todas as métricas para um arquivo."""
    input_data: EvaluationInput
    pipeline_results: List[ PipelineResult ]
