import itertools
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from src.application.dto.translation_job import TranslationJob
from src.application.dto.translation_context import ContextoTraducao
from src.core.config.settings import LLAMA_NOME, GEMINI_NOME, MISTRAL_NOME, DEEPL_NOME

# Configuração das estratégias
# ESTRATEGIAS_ATIVAS = [ GEMINI_NOME, MISTRAL_NOME, LLAMA_NOME, DEEPL_NOME ]
ESTRATEGIAS_ATIVAS = [ LLAMA_NOME ]


class ExperimentBuilder:
    """
    Builder granular. Permite solicitar jobs por partes (por projeto/nível).
    """

    def __init__( self, base_input_dir: Path, base_output_dir: Path ):
        self.input_dir = base_input_dir
        self.output_dir = base_output_dir
        self.regex_filename = re.compile( r"^(.+)\.([a-z]{2,3}(?:_[A-Z]{2})?)\.po$" )

    def listar_projetos( self ) -> List[ Path ]:
        """Retorna a lista de pastas (projetos) disponíveis."""
        if not self.input_dir.exists():
            return [ ]
        # Retorna apenas diretórios, ordenados alfabeticamente para consistência
        return sorted( [ f for f in self.input_dir.iterdir() if f.is_dir() ] )

    def construir_jobs_para_nivel( self, projeto_path: Path, nivel_contexto: int ) -> List[ TranslationJob ]:
        """
        Gera os jobs APENAS para aquele projeto e aquele nível específico (0, 1, 2...).
        """
        # 1. Identificação dos Arquivos (Source vs Contextos)
        arquivo_source, arquivos_contexto_map = self._identificar_arquivos( projeto_path )

        if not arquivo_source:
            return [ ]

        jobs = [ ]
        idiomas_disponiveis = list( arquivos_contexto_map.keys() )

        # Filtra para garantir que o source não esteja na lista de contextos
        idiomas_disponiveis = [
            lang for lang in idiomas_disponiveis
            if arquivos_contexto_map[ lang ] != arquivo_source
        ]

        # Validação: Se pedimos 4 contextos e só existem 2, retornamos lista vazia
        if nivel_contexto > len( idiomas_disponiveis ):
            return [ ]

        # 2. Geração das Combinações para este Nível
        combinacoes = itertools.combinations( idiomas_disponiveis, nivel_contexto )

        for combo_idiomas in combinacoes:
            # Para cada combinação (ex: 'de' + 'fr'), geramos jobs para TODOS os provedores
            objs_contexto = [ ]
            for lang in combo_idiomas:
                path_ctx = arquivos_contexto_map[ lang ]
                objs_contexto.append( ContextoTraducao( str( path_ctx ), lang.upper() ) )

            for estrategia in ESTRATEGIAS_ATIVAS:
                path_saida = self._gerar_caminho_saida(
                    projeto_path.name,
                    arquivo_source.name,
                    estrategia,
                    combo_idiomas
                )

                job = TranslationJob(
                    nome_estrategia = estrategia,
                    arquivo_entrada = str( arquivo_source ),
                    arquivo_saida = str( path_saida ),
                    contextos = objs_contexto
                )
                jobs.append( job )

        return jobs

    def _identificar_arquivos( self, projeto_path: Path ) -> Tuple[ Optional[ Path ], Dict[ str, Path ] ]:
        """Lógica encapsulada para achar source e mapear contextos."""
        arquivo_source: Optional[ Path ] = None
        arquivos_contexto_map: Dict[ str, Path ] = { }
        todos_po = list( projeto_path.glob( "*.po" ) )

        for arquivo in todos_po:
            nome_base, idioma = self._analisar_arquivo( arquivo.name )
            if not idioma: continue

            if idioma == 'en':
                arquivo_source = arquivo
            elif idioma == 'pt_BR':
                continue
            else:
                arquivos_contexto_map[ idioma ] = arquivo

        # Fallback Logic (se não achar en.po)
        if not arquivo_source:
            pot_files = list( projeto_path.glob( "*.pot" ) )
            if pot_files:
                arquivo_source = pot_files[ 0 ]
            elif arquivos_contexto_map:
                primeiro_ctx = list( arquivos_contexto_map.values() )[ 0 ]
                arquivo_source = primeiro_ctx
                print( f"      ℹ️  [Fallback] Usando '{primeiro_ctx.name}' como source." )
            else:
                print( f"      ⚠️  [Erro] Pasta vazia ou inválida: {projeto_path.name}" )

        return arquivo_source, arquivos_contexto_map

    def _analisar_arquivo( self, nome_arquivo: str ) -> Tuple[ Optional[ str ], Optional[ str ] ]:
        match = self.regex_filename.match( nome_arquivo )
        if match:
            return match.group( 1 ), match.group( 2 )
        return None, None

    def _gerar_caminho_saida( self, projeto: str, nome_source: str, estrategia: str, combo_idiomas: tuple ) -> Path:
        stem = nome_source.replace( '.en.po', '' ).replace( '.pot', '' ).replace( '.po', '' )
        n = len( combo_idiomas )
        sulfixo_ctx = f"ctx-{n}"
        if n > 0:
            langs_str = "-".join( sorted( combo_idiomas ) )
            sulfixo_ctx += f".{langs_str}"
        nome_final = f"{stem}.pt_BR.{estrategia.lower()}.{sulfixo_ctx}.po"
        return self.output_dir / projeto / nome_final
