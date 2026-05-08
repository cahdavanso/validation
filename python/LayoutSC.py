import pandas as pd
import tkinter as tk
from tkinter import filedialog
import os
import re

def selecionar_arquivo():
    root = tk.Tk()
    root.withdraw() # Esconde a janelinha branca pequena
    
    # Garante que a janela de seleção de arquivo fique por cima de tudo
    root.attributes('-topmost', True) 
    
    caminho_arquivo = filedialog.askopenfilename(
        title="Selecione o arquivo Excel",
        filetypes=[("Arquivos Excel", "*.xlsx")]
    )
    
    root.destroy() # Fecha o processo do tkinter para não travar o terminal
    return caminho_arquivo

def processar_arquivo():
    # 1. Pedir competência
    competencia = input("Digite a competência - formato mmAAAA: ").strip()
    if len(competencia) != 6 or not competencia.isdigit():
        print("Erro: Formato de competência inválido. Use mmAAAA (ex: 042026).")
        return

    mes = competencia[:2]
    ano = competencia[2:]



    # 2. Selecionar o arquivo
    caminho_excel = selecionar_arquivo()
    if not caminho_excel:
        print("Nenhum arquivo selecionado.")
        return

    try:
        # 3. Ler o Excel
        # Definimos MATRICULA como string para não perder zeros à esquerda no início
        df = pd.read_excel(caminho_excel, dtype={'MATRICULA': str, 'CPF': str})
        
        linhas_formatadas = []

        for _, row in df.iterrows():
            # CPF: Remove pontos/traços e preenche com zeros à esquerda (11 dígitos)
            cpf_limpo = re.sub(r'\D', '', str(row['CPF']))
            cpf = cpf_limpo.zfill(11)

            # MATRICULA: Já lida como string, preenche com zeros à esquerda (15 dígitos)
            matricula = str(row['MATRICULA']).zfill(15)

            # PRAZO (Nº Parcelas): Preenche com zeros à esquerda (3 dígitos)
            # Caso realmente não queira usar o prazo da planilha, troque por "000"
            prazo = str(row['PRAZO']).zfill(3)

            # VALOR: Remove vírgula/ponto e preenche com zeros à esquerda (16 dígitos)
            # Multiplicamos por 100 para remover a vírgula mantendo os centavos
            valor_num = float(row['VALOR'])
            valor_formatado = str(int(round(valor_num * 100))).zfill(16)

            # CONTRATO: Preenche com zeros à esquerda (20 dígitos) conforme exemplo
            contrato = "0".zfill(20)

            # Montagem da linha seguindo as posições da imagem
            # Pos: 1(MM), 3(AAAA), 7(CPF), 18(Esp), 22(Matr), 37(Esp), 41(Parc), 44(Val), 60(Op), 61(Tipo), 63(Cont), 83(Esp), 133(ZZZ)
            linha = (
                f"{mes}"                # 1-2   (2)
                f"{ano}"                # 3-6   (4)
                f"{cpf}"                # 7-17  (11)
                f"{' ' * 4}"            # 18-21 (4)
                f"{matricula}"          # 22-36 (15)
                f"{' ' * 4}"            # 37-40 (4)
                f"{prazo}"              # 41-43 (3)
                f"{valor_formatado}"    # 44-59 (16)
                f"I"                    # 60    (1) - Operação: Inclusão
                f"VL"                   # 61-62 (2) - Tipo: Valor Fixo
                f"{contrato}"           # 63-82 (20)
                f"{' ' * 50}"           # 83-132(50)
                f"ZZZ"                  # 133-135(3)
            )
            linhas_formatadas.append(linha)

        # 4. Salvar arquivo TXT
        nome_txt = os.path.splitext(caminho_excel)[0] + ".txt"
        with open(nome_txt, 'w', encoding='utf-8') as f:
            f.write('\n'.join(linhas_formatadas))

        print(f"\nSucesso! Arquivo gerado: {os.path.basename(nome_txt)}")

    except Exception as e:
        print(f"Ocorreu um erro ao processar: {e}")

if __name__ == "__main__":
    processar_arquivo()