from typing import Callable, Any, List, Tuple, Optional

from src.application.dto.translation_job import TranslationJob


class BatchExecutor:
    """
    Executor síncrono. Processa itens sequencialmente.
    """

    def __init__( self, nome_estrategia: str ) -> None:
        self.nome_estrategia: str = nome_estrategia

    def execute(
            self,
            items: dict,
            processor_func: Callable[ [ str, Any ], Any ],
            on_progress: Optional[ Callable[ [ ], None ] ] = None
    ) -> List[ Tuple[ str, Any ] ]:

        resultados = [ ]

        for key, value in items.items():
            try:
                result = processor_func( key, value )
                resultados.append( (key, result) )
            except Exception as e:
                print( f"[{self.nome_estrategia}] \nErro ao processar [{key}]: {e}" )
                resultados.append( (key, value) )
            finally:
                # O Padrão Observer: Notifica quem estiver ouvindo que um item terminou
                if on_progress:
                    on_progress()

        return resultados
