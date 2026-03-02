from pathlib import Path


def construir_caminho_saida( arquivo_entrada: str, diretorio_base_saida: str, nome_estrategia: str ) -> str:
    """
    Gera o caminho completo de saída padronizado conforme regras de negócio.

    Regras:
    1. Pasta do Projeto: Extraída do nome do arquivo (ex: 'datamash' de 'datamash-1.4.12.1.de')
    2. Nome do Arquivo: Remove idioma original, adiciona pt_BR e a estratégia.

    Exemplo:
    Entrada: .../datamash-1.4.12.1.de.po
    Estratégia: LLAMA
    Saída: .../resultados/datamash/datamash-1.4.12.1.pt_BR-llama.po
    """
    path_entrada = Path( arquivo_entrada )
    # stem pega o nome sem a extensão .po (ex: datamash-1.4.12.1.de)
    nome_bruto = path_entrada.stem

    # --- 1. Definir Nome da Pasta (Projeto) ---
    # Pega tudo antes do primeiro hífen. Se não houver hífen, usa o nome todo.
    nome_projeto = nome_bruto.split( '-' )[ 0 ]

    # --- 2. Limpar código de idioma original ---
    # Se o nome termina com ponto e duas letras (ex: .de, .en, .fr), removemos.
    partes = nome_bruto.split( '.' )
    if len( partes ) > 1 and len( partes[ -1 ] ) == 2:
        # Reconstrói sem a última parte (remove o .de)
        nome_base = ".".join( partes[ :-1 ] )
    else:
        nome_base = nome_bruto

    # --- 3. Montar nome final ---
    # Ex: datamash-1.4.12.1 + .pt_BR-llama + .po
    nome_arquivo_final = f"{nome_base}.pt_BR-{nome_estrategia.lower()}{path_entrada.suffix}"

    # --- 4. Montar caminho completo ---
    # O PoFileAdapter já cuida de criar as pastas (makedirs),
    # então só precisamos retornar a string do caminho.
    caminho_completo = Path( diretorio_base_saida ) / nome_projeto / nome_arquivo_final

    return str( caminho_completo )
