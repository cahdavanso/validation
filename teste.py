import pandas as pd

import xlrd

arquivo_sigrh = r"P:\PESSOAL\VALIDAÇÃO DOS LANÇAMENTOS\2026\MAIO\GOV SC\RELATORIOS\AVERBADOS CAPITAL GOV SC 05.2026.xls"
# 1. Forçamos o separador (sep) e o encoding. 
# Se o seu CSV usa ponto e vírgula, troque para sep=';'
# O on_bad_lines='warn' ajuda a não travar se houver sujeira no arquivo
# Repare no [0] logo no final da chamada da função:
df = pd.read_html(arquivo_sigrh)[0]

# 2. Define a linha 0 como o nome das colunas
df.columns = df.iloc[0]

# 3. Remove a linha 0 do corpo dos dados e reseta o índice
df = df[1:].reset_index(drop=True)

# Agora sim!
print(f'Colunas corrigidas: {df.columns}')
print(f'Tipo do df: {type(df)}')
print(df.head(10))
