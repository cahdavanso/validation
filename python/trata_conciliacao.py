import pandas as pd
import numpy as np

class TRATA_CONCILIACAO:
    def __init__(self, conciliacao, kobraki=None, tacs=None):
        self.conciliacao = conciliacao
        self.kobraki = kobraki if kobraki is not None else None
        self.tacs = tacs if tacs is not None else None

        self.conciliacao.rename(columns={'RECEBIDO GERAL ': 'RECEBIDO GERAL'}, inplace=True)
        self.conciliacao.rename(columns={'TIPO OPERAÇÃO': 'PRODUTO', 'NOVO TIPO DE OPERAÇÃO': 'PRODUTO', 'PRODUTOS PELO D8': 'PRODUTO', 
                                         'PRODUTO D8': 'PRODUTO', 'PRODUTO PELO D8': 'PRODUTO', 'PRODUTO ATUALIZADO': 'PRODUTO',
                                         'TIPO DE OPERAÇÃO': 'PRODUTO'}, inplace=True)
        self.conciliacao.rename(columns={'PRESTAÇÃO ORIGINAL': 'PRESTAÇÃO', 'PMT': 'PRESTAÇÃO'}, inplace=True)

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
            tacs_tratado = self.tacs

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


            conciliacao_tratado = conciliacao_tratado.copy()

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
            inad_d8 = conciliacao_tratado.filter(like='INAD ').sum(axis=1)
            # O .filter() busca as colunas. Se não achar nada, o .sum(axis=1) garante que o retorno seja 0 por linha.
            redistribuicao_d8 = conciliacao_tratado.filter(like='REDISTRIBUIÇÃO').sum(axis=1)

            # Agora a soma do super_saldo nunca vai quebrar e nunca vai virar NaN por causa dessa variável
            super_saldo = soma_d8 + inad_d8 + redistribuicao_d8

            if conciliacao_tratado['CONTRATOS'].dtype != 'int64' and kobraki_tratado is not None and tacs_tratado is not None: # -> Onde vamos verificar se o contrato da conciliação está como string
                tacs_tratado['CONTRATO'] = tacs_tratado['CONTRATO'].astype(str)
                kobraki_tratado['CONTRATO'] = kobraki_tratado['CONTRATO'].astype(str)

            # Vamos criar uma coluna "KOBRAKI" na conciliação, e usar a coluna de "CONTRATOS" da conciliação 
            # para puxar os valores de "VALOR RECEBIDO" no kobraki puxando da coluna "CONTRATO"
            if kobraki_tratado is not None and tacs_tratado is not None:
                somase_kobraki = kobraki_tratado.groupby('CONTRATO')['VALOR RECEBIDO'].sum()
                conciliacao_tratado['KOBRAKI'] = conciliacao_tratado['CONTRATOS'].copy().map(somase_kobraki)
                conciliacao_tratado['KOBRAKI'] = conciliacao_tratado['KOBRAKI'].fillna(0)

                somase_tacs = tacs_tratado.groupby('CONTRATO')['ATRIBUIÇÃO'].sum()
                conciliacao_tratado['TACS'] = conciliacao_tratado['CONTRATOS'].copy().map(somase_tacs)
                conciliacao_tratado['TACS'] = conciliacao_tratado['TACS'].fillna(0)

                # Somar as colunas de KOBRAKI e RECEBIDO GERAL para criar a coluna "TOTAL RECEBIDO"
                conciliacao_tratado['TOTAL RECEBIDO'] = conciliacao_tratado['KOBRAKI'] + conciliacao_tratado['TACS'] + conciliacao_tratado['RECEBIDO GERAL']
            elif kobraki_tratado is not None and tacs_tratado is None:
                somase_kobraki = kobraki_tratado.groupby('CONTRATO')['VALOR RECEBIDO'].sum()
                conciliacao_tratado['KOBRAKI'] = conciliacao_tratado['CONTRATOS'].copy().map(somase_kobraki)
                conciliacao_tratado['KOBRAKI'] = conciliacao_tratado['KOBRAKI'].fillna(0)
                conciliacao_tratado['TOTAL RECEBIDO'] = conciliacao_tratado['KOBRAKI'] + conciliacao_tratado['RECEBIDO GERAL']
            elif kobraki_tratado is None and tacs_tratado is not None:
                
                somase_tacs = tacs_tratado.groupby('CONTRATO')['ATRIBUIÇÃO'].sum()                
                conciliacao_tratado['TACS'] = conciliacao_tratado['CONTRATOS'].copy().map(somase_tacs)
                conciliacao_tratado['TACS'] = conciliacao_tratado['TACS'].fillna(0)
                conciliacao_tratado['TOTAL RECEBIDO'] = conciliacao_tratado['TACS'] + conciliacao_tratado['RECEBIDO GERAL']
            else:
                 # Somar as colunas de KOBRAKI e RECEBIDO GERAL para criar a coluna "TOTAL RECEBIDO"
                conciliacao_tratado['TOTAL RECEBIDO'] = conciliacao_tratado['RECEBIDO GERAL']

            # 2. Calcular prestação * prazo
            # Garante que cada linha tenha um índice único de 0 até o final
            # Remove colunas com nomes duplicados, mantendo apenas a primeira vez que aparecem
            conciliacao_tratado = conciliacao_tratado.loc[:, ~conciliacao_tratado.columns.duplicated()]

            # Agora a conta vai funcionar porque só existe uma coluna 'PRESTAÇÃO' e uma 'PRAZO'
            print(f'PRESTAÇÃO TIPO {conciliacao_tratado['PRESTAÇÃO'].dtype}')
            print(f'PRAZO TIPO {conciliacao_tratado['PRAZO'].dtype}')
            print(f'AMOSTRA DE PRESTAÇÃO TIPO {conciliacao_tratado['PRESTAÇÃO'].head()}')
            print(f'AMOSTRA DE PRAZO TIPO {conciliacao_tratado['PRAZO'].head()}')

            if conciliacao_tratado['PRAZO'].dtype != 'int64':
                conciliacao_tratado.loc[(conciliacao_tratado['PRAZO'] == '') | (conciliacao_tratado['PRAZO'].isna()), 'PRAZO'] = 96
                conciliacao_tratado['PRAZO'] = pd.to_numeric(conciliacao_tratado['PRAZO'], errors='coerce').astype('int64')

            conciliacao_tratado['TOTAL'] = conciliacao_tratado['PRESTAÇÃO'] * conciliacao_tratado['PRAZO']
            prestacao_vezes_prazo = conciliacao_tratado['PRESTAÇÃO'] * conciliacao_tratado['PRAZO']

            # 3. Calcular o resultado final
            conciliacao_tratado['Pago'] = super_saldo - prestacao_vezes_prazo
            conciliacao_tratado['Saldo'] = conciliacao_tratado['Pago'] + conciliacao_tratado['TOTAL RECEBIDO']
            conciliacao_tratado['Saldo'] = conciliacao_tratado['Saldo'].fillna(-np.inf)

            return conciliacao_tratado