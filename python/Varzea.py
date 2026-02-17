import pandas as pd
import tkinter as tk
from tkinter import filedialog

# =========================
# Função para selecionar arquivo
# =========================
def escolher_arquivo(titulo="Escolha o arquivo"):
    root = tk.Tk()
    root.withdraw()  # Esconde a janela principal
    arquivo = filedialog.askopenfilename(
        title=titulo,
        filetypes=[("Arquivos Excel", "*.xlsx *.xls"), ("Arquivos CSV", "*.csv")]
    )
    return arquivo

# =========================
# Função para carregar arquivo
# =========================
def carregar_arquivo(caminho):
    ext = caminho.split(".")[-1].lower()
    if ext == "csv":
        try:
            return pd.read_csv(caminho, sep=";", encoding="utf-8")
        except:
            return pd.read_csv(caminho, sep=",", encoding="utf-8")
    elif ext in ["xls", "xlsx"]:
        return pd.read_excel(caminho, engine="openpyxl")
    else:
        raise ValueError(f"Extensão não suportada: {ext}")

# =========================
# Selecionar arquivos
# =========================
print("Selecione o relatório principal (CSV ou XLSX)")
arquivo_relatorio = escolher_arquivo()

print("Selecione a base Cred+função unificado (XLSX)")
arquivo_base = escolher_arquivo()

print("Selecione o arquivo Conciliação (CSV ou XLSX)")
arquivo_conciliacao = escolher_arquivo()

# =========================
# Carregar dados
# =========================
df_rel = carregar_arquivo(arquivo_relatorio)
df_base = carregar_arquivo(arquivo_base)
df_conc = carregar_arquivo(arquivo_conciliacao)

# ================================
# 2 - Extrair colunas necessárias
# ================================
colunas = ["Matricula", "CPF", "Nome", "ID Contrato Reserva", "Contrato Reserva", "Valor Parcela Descontar"]
df = df_rel[colunas].copy()

# ===================================================
# 3 e 4 - Criar colunas Contrato 1 / Contrato 2
# ===================================================
df["Contrato 1"] = df["Contrato Reserva"].astype(str).str.split("/").str[0].fillna("")
df["Contrato 2"] = df["Contrato Reserva"].astype(str).str.split("/").str[1].fillna(""   )

# ===================================================
# 5 - Abrir colunas auxiliares
# ===================================================
df["Esteira 1"] = ""
df["Esteira 2"] = ""
df["Pmt 1"] = 0
df["Pmt 2"] = 0
df["soma pmt"] = 0

# ==========================
# 6 e 7 - Preencher Esteiras
# ==========================
mapa_esteira = dict(zip(df_base["Codigo Credbase"].astype(str), df_base["Esteira"]))

def buscar_esteira(contrato):
    if pd.isna(contrato) or contrato == "":
        return ""
    return mapa_esteira.get(str(contrato), "Requer validação manual")

df["Esteira 1"] = df["Contrato 1"].apply(buscar_esteira)
df["Esteira 2"] = df["Contrato 2"].apply(buscar_esteira)

# ==========================
# 8 e 9 - Preencher PMTs
# ==========================
mapa_pmt = dict(zip(df_base["Codigo Credbase"].astype(str), df_base["Parcela"]))

def buscar_pmt(contrato):
    if pd.isna(contrato) or contrato == "":
        return 0
    return mapa_pmt.get(str(contrato), 0)

df["Pmt 1"] = df["Contrato 1"].apply(buscar_pmt)
df["Pmt 2"] = df["Contrato 2"].apply(buscar_pmt)

# ===============================
# 10 - Soma PMTs
# ===============================
df["soma pmt"] = df["Pmt 1"] + df["Pmt 2"]

# ===============================
# 11, 12, 13 - Dif e Vlr Lançar
# ===============================
df["Dif"] = df["Valor Parcela Descontar"] - df["soma pmt"]

def calcular_vlr_lancar(row):
    if row["soma pmt"] > row["Valor Parcela Descontar"]:
        return row["Valor Parcela Descontar"]
    else:
        return row["soma pmt"]

df["Vlr lançar"] = df.apply(calcular_vlr_lancar, axis=1)

# ===============================
# 14 - Colunas st1 e st2 do arquivo Conciliação
# ===============================
df["st1"] = df["Contrato 1"].map(dict(zip(df_conc["CONTRATO"].astype(str), df_conc["SITUAÇÃO DO CONTRATO"])))
df["st2"] = df["Contrato 2"].map(dict(zip(df_conc["CONTRATO"].astype(str), df_conc["SITUAÇÃO DO CONTRATO"])))

# ===============================
# 15 - Ajustar Vlr lançar para 0 se AÇÃO JUDICIAL
# ===============================
df.loc[df["st1"] == "AÇÃO JUDICIAL", "Vlr lançar"] = 0
df.loc[df["st2"] == "AÇÃO JUDICIAL", "Vlr lançar"] = 0

# ===============================
# Salvar resultado final
# ===============================
nome_arquivo_saida = "Lançamento Pref varzea grande.xlsx"
df.to_excel(nome_arquivo_saida, index=False)

print(f"✅ Automação concluída! Arquivo salvo como '{nome_arquivo_saida}'")