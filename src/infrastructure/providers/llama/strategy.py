# Interface
from src.core.interfaces.translation_strategy import TranslationStrategy

# Biblioteca
from ollama import Client

# Core
from src.core.config.settings import LLAMA_MODEL_NAME, LLAMA_GENERATION_CONFIG, SYSTEM_INSTRUCTION

# Para pegar versão da lib dinamicamente
import importlib.metadata


class LlamaStrategy( TranslationStrategy ):
    """
        Estratégia de tradução usando a API do Llama.
        Este serviço consegue realizar tradução direta e usando contexto.
    """

    def __init__( self, cliente: Client ):
        self.cliente = cliente
        self.opcoes: dict = { "temperature": LLAMA_GENERATION_CONFIG.get( "temperature", 0.2 ),
                              "top_p": LLAMA_GENERATION_CONFIG.get( "top_p", 1 ),
                              "top_k": LLAMA_GENERATION_CONFIG.get( "top_k", 40 ),
                              "num_predict": LLAMA_GENERATION_CONFIG.get( "max_output_tokens", 2048 ),
                              "seed": 42
                              }

    def traduzir( self, mensagem: str ) -> str:
        """
        Realizar a tradução de um texto num determinado idioma.

        Para o Ollama, é necessário que a mensagem esteja formatada usando "role: user".
        :param mensagem: Mensagem a ser enviado.
        :return: Texto traduzido para o idioma configurado.
        """
        try:
            response = self.cliente.chat(
                model = LLAMA_MODEL_NAME,
                messages = [
                    { "role": "system", "content": SYSTEM_INSTRUCTION },
                    { "role": "user", "content": mensagem }
                ],
                format = "json",
                options = self.opcoes
            )
            return response[ "message" ][ 'content' ]
        except Exception as error:
            raise error

    def obter_configuracao( self ) -> dict:
        """
        Retorna a configuração exata usada nesta instância.
        """
        try:
            version = importlib.metadata.version( "ollama" )
        except:
            version = "unknown"

        return {
            "provider": "Ollama (Local)",
            "model": LLAMA_MODEL_NAME,
            "library_version": version,
            "generation_config": self.opcoes,
            "system_instruction_hash": hash( SYSTEM_INSTRUCTION )
        }
