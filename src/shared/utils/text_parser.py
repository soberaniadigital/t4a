import json
import re
from typing import Dict, Any
import logging
from src.core.domain.exceptions import ErroFormatoResposta

logger = logging.getLogger( __name__ )


def extrair_traducao_estrita( json_str: str ) -> str:
    """
    Converte uma string JSON e retorna o valor da chave 'translation'.
    Tenta parse nativo primeiro. Se falhar, tenta recuperação via Regex.
    """

    # 1. Pré-processamento: Limpeza de Artefatos de LLM (Markdown)
    padrao_markdown = r"```(?:json)?\s*(.*?)\s*```"
    match = re.search( padrao_markdown, json_str, re.DOTALL )

    if match:
        conteudo_limpo = match.group( 1 ).strip()
    else:
        conteudo_limpo = json_str.strip()

    # 2. Tentativa 1: Parse JSON Padrão (Caminho Feliz)
    try:
        # strict=False ajuda com alguns caracteres de controle, mas não todos
        dados = json.loads( conteudo_limpo, strict = False )
        return _validar_e_extrair( dados )
    except json.JSONDecodeError:
        logger.warning(
            f"Falha no JSON parse nativo. Tentando recuperação via Regex. Conteúdo: {conteudo_limpo[ :50 ]}..." )

    # 3. Tentativa 2: Fallback via Regex (Caminho de Recuperação)
    # Isso resolve casos onde o LLM esqueceu de escapar uma aspa interna ou usou newlines reais.
    # Padrão busca: "translation" : "CONTEUDO" (ignorando espaços e quebras)
    # O [^"]* não funciona bem se tiver aspas escapadas dentro.
    # Usamos uma estratégia de capturar tudo entre a primeira aspa do valor e a última aspa antes do fecha chaves.

    try:
        # Regex explica: Procure "translation" seguido de :
        # Capture o grupo (.*?) que é o conteúdo, de forma 'não gulosa',
        # até encontrar o fechamento de aspas seguido de fecha chaves ou vírgula
        padrao_regex = r'"translation"\s*:\s*"(.*)"\s*}'
        match_fallback = re.search( padrao_regex, conteudo_limpo, re.DOTALL )

        if match_fallback:
            texto_extraido = match_fallback.group( 1 )
            # LLMs às vezes escapam duplamente no texto bruto (ex: \\n), precisamos desescapar
            # para ter o texto real, mas com cuidado para não quebrar C-strings.
            # Neste caso, retornamos o texto bruto recuperado.

            # Pequeno fix: Regex pode capturar escapes de JSON como literais (ex: \" vira \")
            # Vamos remover o escape da aspa gerado pelo JSON se existir
            texto_final = texto_extraido.replace( '\\"', '"' )
            return texto_final

    except Exception as e:
        logger.error( f"Falha também no Regex: {e}" )

    # Se tudo falhar, lançamos o erro original
    raise ErroFormatoResposta(
        mensagem = "Não foi possível extrair a tradução (JSON inválido e Regex falhou).",
        detalhe = f"Conteúdo recebido: {conteudo_limpo}"
    )


def _validar_e_extrair( dados: Any ) -> str:
    """Validações estruturais extraídas para função auxiliar."""
    if not isinstance( dados, dict ):
        raise ErroFormatoResposta( mensagem = "O JSON não é um objeto." )

    val = dados.get( "translation" )
    if val is None:  # Aceita string vazia, mas não None
        raise ErroFormatoResposta( mensagem = "Chave 'translation' ausente." )

    return str( val )
