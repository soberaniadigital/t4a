import sys
from pathlib import Path


def criar_separador( caminho_arquivo: Path ) -> str:
    """
    Cria uma divisão visual clara contendo o caminho completo do arquivo.
    """
    linha = "=" * 80
    return f"\n{linha}\nARQUIVO: {caminho_arquivo.absolute()}\n{linha}\n"


def consolidar_arquivos( diretorio_origem: str, arquivo_saida: str ):
    """
    Lê todos os arquivos de um diretório (e subdiretórios) e os consolida em um único arquivo de texto.
    Ignora arquivos que não podem ser lidos como texto (ex: binários).
    """
    path_origem = Path( diretorio_origem )

    # Validação básica (Fail Fast)
    if not path_origem.exists() or not path_origem.is_dir():
        print( f"Erro: O diretório '{diretorio_origem}' não existe ou não é uma pasta." )
        return

    print( f"Iniciando a leitura em: {path_origem.absolute()}..." )

    with open( arquivo_saida, 'w', encoding = 'utf-8' ) as outfile:
        # rglob('*') percorre todos os arquivos recursivamente
        for arquivo in path_origem.rglob( '*' ):
            if arquivo.is_file() and arquivo.name != arquivo_saida:
                try:
                    # Tenta ler o arquivo como texto UTF-8
                    conteudo = arquivo.read_text( encoding = 'utf-8', errors = 'strict' )

                    # Escreve o separador e o conteúdo
                    outfile.write( criar_separador( arquivo ) )
                    outfile.write( conteudo + "\n" )

                    print( f"[OK] Processado: {arquivo.name}" )

                except (UnicodeDecodeError, PermissionError):
                    # Se falhar (arquivo binário ou sem permissão), apenas avisa e pula (Resiliência)
                    print( f"[PULADO] Não foi possível ler (provavelmente binário): {arquivo.name}" )
                except Exception as e:
                    print( f"[ERRO] Falha ao ler {arquivo.name}: {e}" )

    print( f"\nConcluído! Todo o conteúdo foi salvo em '{arquivo_saida}'." )


# --- Execução Principal ---
if __name__ == "__main__":
    # Configuração
    pasta_alvo: str = "/Users/viniciuscandeia/development/TCC/src"
    # pasta_alvo: str = "/Users/viniciuscandeia/development/TCC/web_scraper"
    nome_saida = "arquivos_consolidados.txt"

    # Chamada da função
    consolidar_arquivos( pasta_alvo, nome_saida )
