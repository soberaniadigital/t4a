Primeiro são extraidas as strings do arquivos .po usando o script "extract_msgids.py" passando como argumentos o diretorio com os arquivos .po (./po_input) e um diretório em que os msgids serão salvos como .txt (./extracted_msgids).

Em seguida utilizando o script "translate_txt_nllb.py" passando como argumento a pasta com os arquivos .txt contendo as msgids extraidas (./extracted_msgids) e o diretorio com as traduções feitas pelo nllb (./translations). As traduções saem como um arquivo .tsv cada linha para cada tradução no formato texto_original<TAB>texto_traduzido>.

Por fim para relizar a avaliação BLEU, rode o script "bleu_eval.py" passando como argumento a pasta com os arquivos .po em PT-BR contendo o msgstr que será o target desejado da tradução (--po-dir .\pt_po_input) e a pasta com os arquivos .tsv traduzidos pelo nllb (--tsv-dir ./translations) e o diretório em que o csv será armazenado (--out-csv .\results\per_file_updated_bleu_scores.csv). 
