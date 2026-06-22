import pandas as pd

import xlrd

arquivo_neoconsig = r"P:\PESSOAL\VALIDAÇÃO DOS LANÇAMENTOS\2026\JUNHO\PREF SOROCABA\RELATORIOS\operacaoEmprestimo_20260619131857.xls"

df_neo = pd.read_html(arquivo_neoconsig, thousands='.', decimal=',')[0]

print(df_neo)
