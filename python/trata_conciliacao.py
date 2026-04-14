import pandas as pd

class TRATA_CONCILIACAO:
    def __init__(self, conciliacao, kobraki):
        self.conciliacao = conciliacao
        self.kobraki = kobraki

    def trata_conciliacao(self):
            # Vamos verificar o tipo da coluna VALOR RECEBIDO de KOBRAKI para garantir que é numérica
            '''if 'VALOR RECEBIDO' in self.kobraki.columns:
                 print(f"Amostra de linhas da coluna VALOR RECEBIDO:\n{self.kobraki['VALOR RECEBIDO'].head()}")
                 print(f"Tipo da coluna VALOR RECEBIDO: {self.kobraki['VALOR RECEBIDO'].dtype}")
            else:
                try:
                     print(f"KOBRAKI:\n{self.kobraki.head()}")
                except Exception as e:
                     print(f"Erro ao exibir KOBRAKI:\n{e}")'''
            # Vamos verificar o tipo da coluna CONTRATO de KOBRAKI para garantir que é numérica
            '''if 'CONTRATO' in self.kobraki.columns:
                print(f"Amostra de linhas da coluna CONTRATO:\n{self.kobraki['CONTRATO'].head()}")
                print(f"Tipo da coluna CONTRATO: {self.kobraki['CONTRATO'].dtype}")

                print(f"Amostra de linhas da coluna CONTRATOS Conciliação:\n{self.conciliacao['CONTRATOS'].head()}")
                print(f"Tipo da coluna CONTRATOS: {self.conciliacao['CONTRATOS'].dtype}")'''

            
            kobraki_tratado = self.kobraki

            conciliacao_tratado = self.conciliacao
            # Converte para lista de colunas
            conciliacao_tratado.rename(columns={conciliacao_tratado.columns[0]: 'CONTRATOS'}, inplace=True)
            cols = list(conciliacao_tratado.columns)

            # Encontra o índice da primeira ocorrência de "CONTRATO" e altera
            '''for i, c in enumerate(cols):
                if c == "CONTRATO" and c != "CONTRATOS":
                    cols[i] = "CONTRATOS"  # só a primeira vez
                    break
                else:
                    break'''

            conciliacao_tratado.columns = cols
            conciliacao_tratado['CONTRATOS'] = conciliacao_tratado['CONTRATOS'].astype(str)
            conciliacao_tratado = conciliacao_tratado.drop_duplicates(subset='CONTRATOS')
            # Atualiza o DataFrame com novos nomes


            conciliacao_tratado = conciliacao_tratado

            # 1. Selecionar colunas com "d8" no nome e somar por linha (axis=1)
            # "D8 " precisa ficar com espaço para que a coluna "CONVENIO D8" não atrapalhe na hora da soma
            colunas_d8 = conciliacao_tratado.filter(regex=r'^(?!.*PRODUTO)D8').columns
            for col in colunas_d8:
                tipos = conciliacao_tratado[col].apply(type).value_counts()
                '''print(f"Coluna {col}:")
                print(tipos)
                print()'''
            conciliacao_tratado[colunas_d8] = conciliacao_tratado[colunas_d8].apply(pd.to_numeric, errors='coerce')

            soma_d8 = conciliacao_tratado.filter(regex=r'^(?!.*PRODUTO)D8').sum(axis=1)

            # Vamos criar uma coluna "KOBRAKI" na conciliação, e usar a coluna de "CONTRATOS" da conciliação 
            # para puxar os valores de "VALOR RECEBIDO" no kobraki puxando da coluna "CONTRATO"
            somase_kobraki = kobraki_tratado.groupby('CONTRATO')['VALOR RECEBIDO'].sum()
            conciliacao_tratado['KOBRAKI'] = conciliacao_tratado['CONTRATOS'].map(somase_kobraki)
            conciliacao_tratado['KOBRAKI'] = conciliacao_tratado['KOBRAKI'].fillna(0)

            # Somar as colunas de KOBRAKI e RECEBIDO GERAL para criar a coluna "TOTAL RECEBIDO"
            conciliacao_tratado['TOTAL RECEBIDO'] = conciliacao_tratado['KOBRAKI'] + conciliacao_tratado['RECEBIDO GERAL']

            # 2. Calcular prestação * prazo
            prestacao_vezes_prazo = conciliacao_tratado['PRESTAÇÃO'] * conciliacao_tratado['PRAZO']

            # 3. Calcular o resultado final
            conciliacao_tratado['Pago'] = soma_d8 - prestacao_vezes_prazo
            conciliacao_tratado['Saldo'] = conciliacao_tratado['Pago'] + conciliacao_tratado['TOTAL RECEBIDO']

            return conciliacao_tratado