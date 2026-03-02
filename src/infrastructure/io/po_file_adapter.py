# Biblioteca
import os

from polib import pofile, POFile, POEntry

from src.core.domain.exceptions import ErroCarregarArquivo, ErroSalvarArquivo


def _garantir_diretorio( caminho_arquivo: str ):
    """
    Função auxiliar para garantir que a pasta de destino exista.
    Isso evita o erro comum 'FileNotFoundError' ao tentar salvar em uma pasta nova.
    """
    diretorio = os.path.dirname( caminho_arquivo )
    if diretorio and not os.path.exists( diretorio ):
        os.makedirs( diretorio, exist_ok = True )


def _carregar_arquivo_bruto( caminho_arquivo: str ):
    """
    Carregar arquivo .po
    :param caminho_arquivo: Caminho do arquivo po.
    :return: Instância de um POFile.
    """

    try:
        return pofile( caminho_arquivo )
    except Exception:
        raise ErroCarregarArquivo( mensagem = f'Erro ao carregar arquivo: {caminho_arquivo}.' )


class PoFileAdapter:
    """
        Classe responsável por manipular arquivos .po.
    """

    def carregar_arquivo( self, caminho_arquivo: str ) -> dict:
        """
        Carrega o arquivo .po e retorna um dicionário.
        :param caminho_arquivo: Caminho do arquivo po.
        :return: Dicionário onde a chave é o termo original e o valor é a tradução.
        """
        arquivo = _carregar_arquivo_bruto( caminho_arquivo )

        dicionario: dict = {
            entrada.msgid: entrada.msgstr
            for entrada in arquivo
            if entrada.msgid
        }

        return dicionario

    def salvar_arquivo( self, dados: dict, caminho_saida: str, metadados: dict = None ) -> None:
        """
        Criar um arquivo contendo a tradução feita.
        :param dados: Dicionário contendo o valor traduzido para cada chave.
        :param caminho_saida: Caminho que irá salvar o arquivo.
        :param metadados: Metadados do arquivo .po.
        :return: Sem retorno.
        """

        try:
            po = POFile()
            po.metadata = {
                'Project-Id-Version': '1.0',
                'Report-Msgid-Bugs-To': 'suporte@exemplo.com',
                'POT-Creation-Date': '2023-10-27 12:00+0000',
                'PO-Revision-Date': '2023-10-27 12:00+0000',
                'MIME-Version': '1.0',
                'Content-Type': 'text/plain; charset=utf-8',
                'Content-Transfer-Encoding': '8bit'
            }

            if metadados:
                po.metadata.update( metadados )

            for original, traduzido in dados.items():
                entry = POEntry(
                    msgid = original,
                    msgstr = traduzido
                )
                po.append( entry )

                # 4. Garante que o diretório existe antes de salvar
            _garantir_diretorio( caminho_saida )

            # 5. Salva o arquivo
            po.save( caminho_saida )

        except Exception:
            raise ErroSalvarArquivo( mensagem = f"Erro ao salvar arquivo .po em {caminho_saida}." )


if __name__ == "__main__":
    objeto = PoFileAdapter()

    caminho: str = '/Users/viniciuscandeia/development/TCC/data/input/datamash/datamash-1.4.12.1.de.po'
    dicionario = objeto.carregar_arquivo( caminho )

    print( dicionario )
