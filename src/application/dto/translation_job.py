from dataclasses import dataclass, field
from typing import Optional, Callable

from src.application.dto.translation_context import ContextoTraducao


@dataclass
class TranslationJob:
    """
    Representa uma 'Ordem de Serviço' unitária.
    Contém tudo que o Pipeline precisa para rodar UMA vez.
    """
    nome_estrategia: str  # Qual IA usar (Llama, Gemini...)
    arquivo_entrada: str  # Onde ler
    arquivo_saida: str  # Onde salvar
    contextos: list[ ContextoTraducao ] = field( default_factory = list )

    # Campo transiente (não persistido) para auxiliar na UI
    # Armazena a função que deve ser chamada a cada tradução concluída
    progress_callback: Optional[ Callable[ [ ], None ] ] = None
