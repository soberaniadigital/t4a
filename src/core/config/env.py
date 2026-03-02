"""
    Definição da classe que contém as variáveis de ambiente.
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv, find_dotenv

# Procurando e carregando o .env
load_dotenv( find_dotenv() )


@dataclass
class AppConfig:
    # Chaves
    deepl_api_key: str = os.getenv( "DEEPL_API_KEY" )
    gemini_api_key: str = os.getenv( "GEMINI_API_KEY" )
    mistral_api_key: str = os.getenv( "MISTRAL_API_KEY" )
    llama_url: str = os.getenv( "LLAMA_URL" )
