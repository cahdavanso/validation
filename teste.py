import pandas as pd

arquivo_infoconsig = r"F:\Dados\NOVA ESTRUTURA\LANÇAMENTO CARTÕES\TRABALHANDO\2026\05 - Maio\PREF ÁGUAS LINDAS\RELATÓRIOS\CONTRATOS__AGUAS_LINDAS_GOIAS_RH_AGUAS_LINDAS_GOIAS_HOJE_PREVIDENCIA_CARTAO__20260507152212.csv"
# 1. Forçamos o separador (sep) e o encoding. 
# Se o seu CSV usa ponto e vírgula, troque para sep=';'
# O on_bad_lines='warn' ajuda a não travar se houver sujeira no arquivo
data = pd.read_csv(
    arquivo_infoconsig, 
    sep=';', 
    encoding='latin1', 
    header=None, # Lemos sem cabeçalho para ele não se confundir
    names=range(25), # Forçamos a leitura de várias colunas (ajuste o número se precisar)
    on_bad_lines='skip' 
)

# 2. Agora usamos aquela lógica de procurar a linha do CPF
for i in range(len(data)):
    linha_valores = data.iloc[i].astype(str).tolist()
    # Procuramos por uma palavra que você sabe que está no cabeçalho real
    if any('CPF' in str(s).upper() for s in linha_valores):
        data.columns = data.iloc[i] # Define a linha atual como cabeçalho
        data = data[i+1:].reset_index(drop=True) # Corta o que está acima
        break

# 3. Limpeza final: remove colunas totalmente vazias que o 'range(25)' pode ter criado
data = data.dropna(axis=1, how='all')

print(data.columns)