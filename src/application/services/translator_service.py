from pathlib import Path
from typing import Optional

from src.core.ioc.registry import StrategyRegistry
from src.infrastructure.providers.common.llm_prompt import LlmPrompt
from src.infrastructure.io.po_file_adapter import PoFileAdapter
from src.application.services.context_service import ContextService
from src.shared.utils.sync_batch_executor import BatchExecutor
from src.application.services.translation_unit_processor import TranslationUnitProcessor
from src.application.dto.translation_job import TranslationJob

import json
import time
from datetime import datetime
import importlib.metadata

from rich.console import Console

console = Console()


class TranslatorService:
    def __init__( self,
                  registry: StrategyRegistry,
                  po_adapter: PoFileAdapter,
                  prompt_builder: LlmPrompt
                  ):
        self._registry = registry
        self._po_adapter = po_adapter
        self._prompt_builder = prompt_builder

    def executar_traducao( self, job: TranslationJob ):
        """
        Método Orquestrador: Agora ele lê como uma história linear.
        """
        start_time = time.time()

        # 1. Preparação (Setup)
        # Ocultamos a complexidade de criar os objetos
        processador = self._construir_processador( job )
        executor = BatchExecutor( job.nome_estrategia )
        dados_entrada = self._po_adapter.carregar_arquivo( job.arquivo_entrada )

        # 2. Execução (Action)
        resultados_tuplas = executor.execute(
            items = dados_entrada,
            processor_func = processador.processar_item,
            on_progress = job.progress_callback
        )

        # 3. Finalização e Metadados
        tempo_total = time.time() - start_time

        # Salva o PO
        dict_resultados = dict( resultados_tuplas )
        self._salvar_resultados( dict_resultados, job.arquivo_saida )

        self.gerar_arquivo_metadados( job, processador, tempo_total, dict_resultados )

    def _construir_processador( self, job: TranslationJob ) -> TranslationUnitProcessor:
        """
        Encapsula a lógica de 'montagem' das dependências de tradução.
        """
        # 1. Cria a Estratégia
        fabrica = self._registry.buscar_fabrica( job.nome_estrategia )
        estrategia = fabrica.criar_estrategia()

        # 2. Cria o Contexto (se necessário)
        servico_contexto = self._criar_servico_contexto( job.contextos )

        # 3. Monta o Processador
        return TranslationUnitProcessor(
            strategy = estrategia,
            strategy_name = job.nome_estrategia,
            prompt_builder = self._prompt_builder,
            context_service = servico_contexto
        )

    def _criar_servico_contexto( self, arquivos_contexto: list ) -> Optional[ ContextService ]:
        """
        Trata a conversão de DTO para o formato esperado pelo ContextService.
        """
        if not arquivos_contexto:
            return None

        # Adapter: Converte lista de objetos para lista de listas (compatibilidade legado)
        lista_formatada = [ [ ctx.caminho, ctx.idioma ] for ctx in arquivos_contexto ]
        return ContextService( lista_formatada, self._po_adapter )

    def _salvar_resultados( self, dados: dict, caminho: str ):
        """
        Abstrai o salvamento.
        """
        self._po_adapter.salvar_arquivo( dados, caminho )
        print( f"💾 Arquivo salvo com sucesso em: {caminho}" )

    def gerar_arquivo_metadados( self, job: TranslationJob, processador: TranslationUnitProcessor,
                                 duration: float, dados_traduzidos: dict ):
        """
        Compila e salva o JSON de metadados.
        NOVO: Inclui tradução de referência (pt_BR) nas amostras.
        """
        estrategia = processador.obter_estrategia()
        config_estrategia = estrategia.obter_configuracao()

        reference_translations = { }

        # Tenta localizar o arquivo pt_BR de referência
        arquivo_entrada_path = Path( job.arquivo_entrada )
        projeto_dir = arquivo_entrada_path.parent

        # Procura por arquivo .pt_BR.po na mesma pasta
        arquivos_ptbr = list( projeto_dir.glob( "*.pt_BR.po" ) )

        if arquivos_ptbr:
            try:
                # Carrega o primeiro arquivo pt_BR encontrado
                reference_translations = self._po_adapter.carregar_arquivo( str( arquivos_ptbr[ 0 ] ) )
                console.print( f"[dim]  ✓ Referência pt_BR carregada: {arquivos_ptbr[ 0 ].name}[/]" )
            except Exception as e:
                console.print( f"[yellow]  ⚠ Erro ao carregar referência pt_BR: {e}[/]" )

        context_sentences = { }
        if processador.context_service:
            sample_keys = list( dados_traduzidos.keys() )[ :5 ]

            for key in sample_keys:
                contexto = processador.context_service.obter_contexto( key )
                if contexto:
                    context_sentences[ key ] = contexto

        from src.core.config.settings import SYSTEM_INSTRUCTION, PROMPT_USER_TEMPLATE

        prompt_templates = {
            "system_instruction": SYSTEM_INSTRUCTION,
            "user_template": PROMPT_USER_TEMPLATE.template,
            "explanation": "O prompt final é formado por: SYSTEM_INSTRUCTION + USER_TEMPLATE preenchido com original_text e context_section"
        }

        all_translations = [ ]

        # Itera sobre TODAS as traduções
        for key, translated_value in dados_traduzidos.items():
            translation_entry = {
                "original": key,
                "translated": translated_value
            }

            # Adiciona referência se existir
            if key in reference_translations:
                translation_entry[ "reference" ] = reference_translations[ key ]

            all_translations.append( translation_entry )

        metadados = {
            "job_info": {
                "input_file": job.arquivo_entrada,
                "output_file": job.arquivo_saida,
                "strategy_name": job.nome_estrategia,
                "execution_date": datetime.now().isoformat(),
                "duration_seconds": round( duration, 2 ),
                "reference_file": str( arquivos_ptbr[ 0 ] ) if arquivos_ptbr else None
            },
            "model_config": config_estrategia,
            "prompt_info": {
                "templates": prompt_templates,
                "context_files": [ ctx.idioma for ctx in job.contextos ],
                "context_sentences_sample": context_sentences
            },
            "translation_stats": {
                "total_entries": len( dados_traduzidos ),
                "reference_available": bool( arquivos_ptbr )
            },
            "environment": {
                "python_version": importlib.metadata.sys.version
            },
            "translations": all_translations
        }

        # Salva arquivo .meta.json
        caminho_meta = job.arquivo_saida + ".meta.json"
        try:
            with open( caminho_meta, 'w', encoding = 'utf-8' ) as f:
                json.dump( metadados, f, indent = 4, ensure_ascii = False )
            print( f"✓ Metadados salvos em: {caminho_meta}" )
        except Exception as e:
            print( f"✗ Erro ao salvar metadados: {e}" )
