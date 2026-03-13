import pandas as pd

nome_teste = fr"P:\PESSOAL\VALIDAÇÃO DOS LANÇAMENTOS\2026\MARÇO\GOV MG - SEPLAG\RELATORIOS\TRABALHADO BENEFICIO GOV MG SEPLAG 02.2025.xlsx"
nome_teste_sem_aspas = nome_teste.replace('"', '')
df_teste = pd.read_excel(nome_teste_sem_aspas)


print(df_teste.head(15))