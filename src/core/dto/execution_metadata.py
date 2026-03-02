from dataclasses import dataclass, field
from typing import Dict, Any, List


@dataclass
class ExecutionMetadata:
    """
    DTO que representa a 'Receita' utilizada para gerar a tradução.
    Garante rastreabilidade e reprodutibilidade científica.
    """
    # Identificação
    strategy_name: str
    model_name: str
    timestamp: str

    # Ambiente
    library_versions: Dict[ str, str ]  # Ex: {"google-generativeai": "0.3.0"}

    # Configuração da IA
    parameters: Dict[ str, Any ]  # temperature, top_p, seeds...
    prompt_template: str  # O texto exato do prompt (sem o conteúdo do arquivo)

    # Contexto de Entrada
    input_files_context: List[ str ]  # Quais idiomas foram usados de base

    # Métricas de Execução (Opcional)
    execution_time_seconds: float = 0.0
