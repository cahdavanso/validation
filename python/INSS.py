import pandas as pd
import numpy as np
from datetime import datetime
import warnings
import os

# Ignora avisos de versões futuras do Pandas para manter o log limpo
warnings.filterwarnings("ignore", category=FutureWarning)

class INSS:
    def __init__(self, portal_file_list, front,conciliacao, caminho, casos_capital=None):
        
        # --- ADAPTAÇÃO: Recebendo DataFrames do server.py ---
        
        # Averbados (portal_file_list)
        self.averbados = portal_file_list if portal_file_list is not None else pd.DataFrame()

        # Front
        self.front = front if front is not None else None
        
        # Casos Capital
        self.casos_capital = casos_capital if casos_capital is not None else None
        
        # Conciliação
        self.conciliacao = conciliacao if conciliacao is not None else pd.DataFrame()
        
        self.caminho = caminho

        self.trata_front_final()

    def trata_conciliacao(self):
        conciliacao_tratado = self.conciliacao.copy()
        
        if conciliacao_tratado.empty:
            return pd.DataFrame()

        # Renomeia a primeira coluna para CONTRATOS
        conciliacao_tratado.rename(columns={conciliacao_tratado.columns[0]: 'CONTRATOS'}, inplace=True)
        
        # Padroniza colunas
        cols = list(conciliacao_tratado.columns)
        conciliacao_tratado.columns = cols
        
        conciliacao_tratado['CONTRATOS'] = conciliacao_tratado['CONTRATOS'].astype(str)
        conciliacao_tratado = conciliacao_tratado.drop_duplicates(subset='CONTRATOS')

        # Selecionar colunas com "d8" no nome (Regex)
        colunas_d8 = conciliacao_tratado.filter(regex=r'^(?!.*PRODUTO)D8').columns
        
        # Converte para numérico
        conciliacao_tratado[colunas_d8] = conciliacao_tratado[colunas_d8].apply(pd.to_numeric, errors='coerce')

        soma_d8 = conciliacao_tratado[colunas_d8].sum(axis=1)

        # Conversão segura para cálculos
        conciliacao_tratado['PMT'] = pd.to_numeric(conciliacao_tratado['PMT'], errors='coerce').fillna(0)
        conciliacao_tratado['PRAZO'] = pd.to_numeric(conciliacao_tratado['PRAZO'], errors='coerce').fillna(0)
        conciliacao_tratado['RECEBIDO GERAL'] = pd.to_numeric(conciliacao_tratado['RECEBIDO GERAL'], errors='coerce').fillna(0)

        # Cálculos
        prestacao_vezes_prazo = conciliacao_tratado['PMT'] * conciliacao_tratado['PRAZO']
        conciliacao_tratado['Pago'] = soma_d8 - prestacao_vezes_prazo
        conciliacao_tratado['Saldo'] = conciliacao_tratado['Pago'] + conciliacao_tratado['RECEBIDO GERAL']

        return conciliacao_tratado
    
    def tratamento_front_preliminar(self):
        front_consig = self.front.copy()

        # Trasnforma Prestacao em numérico
        # front_consig['Prestacao'] = front_consig['Prestacao'].astype(str).str.replace('.', '', regex=False)
        front_consig.rename(columns={'Prestracao': 'Prestacao'}, inplace=True)
        front_consig['Prestacao'] = front_consig['Prestacao'].astype(str).str.replace(',', '.', regex=False)
        front_consig['Prestacao'] = pd.to_numeric(front_consig['Prestacao'], errors='coerce').fillna(0)

        conciliacao = self.conciliacao.copy()

        # Colocar traços nos contratos xxxxxxxxx-x
        contratos_com_traço = front_consig['CCB'].astype(str).str.zfill(10).str.slice(0, 9) + '-' + front_consig['CCB'].astype(str).str.zfill(10).str.slice(9, 10)

        # Insere as colunas vazias necessárias
        front_consig.insert(0, 'NR_OPER', contratos_com_traço,True)
        front_consig.insert(21, 'Saldo', '', True)
        front_consig.insert(22, 'Valor a lançar', '', True)
        front_consig.insert(23, 'Análise', '', True)

        situacao_averbado_index = self.averbados.set_index('NR_OPER_EDITADO')['SITUAÇÃO'].copy()
        situacao_averbado_map = front_consig['Contrato'].map(situacao_averbado_index.to_dict())
        front_consig.insert(24, 'SITUAÇÃO', situacao_averbado_map, True)

        valor_reajustado_index = self.averbados.set_index('NR_OPER_EDITADO')['MARGEM REAJUSTADA'].copy()
        valor_reajustado = front_consig['Contrato'].map(valor_reajustado_index.to_dict())
        front_consig.insert(25, 'Valor Averbado Reajustado', valor_reajustado, True)

        print(f'Esteiras Únicas do front: {front_consig["Esteira"].unique()}')

        # Esteiras
        esteiras_permitidas = ['11 FORMALIZACAO', '09.0 PAGO', 'RISCO DA OPERACAO - OBITO', '14.0 RISCO DA OPERACAO - OBITO',
                               'RISCO DA OPERACAO-DEMAIS SITUACOES', '11.PROBLEMAS DE AVERBACAO', '10.7.0 INGRESSAR COM PROCESSO OU ACAO JURIDICO',
                               '07.1 \x96 QUITACAO \x96 PAGAMENTO AO CLIENTE', '10.7 CONTRATO NAO AVERBADO - AGUARDANDO RESOLUCAO', '11.2  DETERMINACAO JUDICIAL',
                               "15.0\tRISCO DA OPERACAO-DEMAIS SITUACOES", "11.1 CONTRATO FISICO ENVIADO AO BANCO", "07.0 QUITACAO \x96 ENVIO DE CESSAO",
                               "99 CARTAO UTILIZADO", "15.0 RISCO DA OPERACAO-DEMAIS SITUACOES"
                              ]
        
        # Vamos renomear a primeira coluna da conciliação
        conciliacao.rename(columns={conciliacao.columns[0]: 'CONTRATOS'}, inplace=True)
        # Converte para lista de colunas
        cols = list(conciliacao.columns)

        # Atualiza o DataFrame com novos nomes
        conciliacao.columns = cols
        conciliacao['CONTRATOS'] = conciliacao['CONTRATOS'].astype('Int64')

        # Adiciona a coluna de tipo da Conciliação
        print(f'colunas de front consig: {front_consig.columns}')
        tipo_conci = front_consig['Contrato'].map(conciliacao.set_index('CONTRATOS')['TIPO OP'].to_dict())
        front_consig.insert(19, 'Tipo Conciliação', tipo_conci, True)

        # Adiciona só as esteiras que podem ser lançadas
        # front_consig_esteiras = front_consig[front_consig['dsEsteira'].isin(esteiras_permitidas)].copy()


        # -------------------------------- MARCAR TUDO QUE NÃO LANÇA ---------------------------------- #
        # Tira tudo que é excluído do arquivo de Averbação
        def obs_situacao(row):
            # 1. Pega o valor bruto primeiro
            valor_bruto = row['SITUAÇÃO']
            
            # 2. Verifica se é nulo (NaN) ANTES de converter para string
            if pd.isna(valor_bruto) or valor_bruto == '':
                return ''

            # 3. Agora sim converte para string com segurança
            situacao = str(valor_bruto).strip()
            
            # 4. Verifica se a string virou 'nan' ou 'None' por acidente na conversão
            if situacao.lower() in ['nan', 'none', '']:
                return ''

            # 5. Lógica de Negócio
            if situacao in ['0 - Ativo', 'Ativo']:
                return 'LANÇAR'
            else:
                return f'NÃO - {situacao}'
            
        front_consig['Análise'] = front_consig.apply(obs_situacao, axis=1)

        # Marca saldo positivo
        conciliacao_tatado = self.trata_conciliacao()
        conciliacao_tatado['CONTRATOS'] = conciliacao_tatado['CONTRATOS'].astype('Int64')
        front_consig['Saldo'] = front_consig['Contrato'].map(conciliacao_tatado.set_index('CONTRATOS')['Saldo'].to_dict())
        front_consig_validado_termino = front_consig.copy()
        front_consig_validado_termino.loc[front_consig_validado_termino['Saldo'] > -0.01, 'Análise'] = 'NÃO LANÇAR - SALDO POSITIVO'
        # Valor que vai ser lançado
        # Substitui NaN em "Saldo" por um valor muito alto (para que "Parcela" seja escolhida)
        valor_a_lancar = np.minimum(np.abs(front_consig_validado_termino['Saldo']).fillna(float('inf')), front_consig_validado_termino['Prestacao'])

        front_consig_validado_termino['Valor a lançar'] = valor_a_lancar

        # Marca o que é Ação Judicial
        # No caso de Ação Judicial estiver estiver SIM e NÃO ao invés de 1 e 0
        front_consig_validado_termino['Acao Judicial'] = front_consig_validado_termino['Acao Judicial'].replace({'SIM': 1, 'NAO': 0})
        front_consig_validado_termino.loc[front_consig_validado_termino['Acao Judicial'] == 1, 'Análise'] = 'NÃO LANÇAR - AÇÃO JUDICIAL'

        # Marca o que é Obito
        # No caso de óbito estiver estiver SIM e NÃO ao invés de 1 e 0
        
        # front_consig_validado_termino['Obito'] = front_consig_validado_termino['Obito'].replace({'SIM': 1, 'NÃƒO': 0})
        # front_consig_validado_termino.loc[front_consig_validado_termino['Obito'] == 1, 'Análise'] = 'NÃO LANÇAR - ÓBITO'

        # Marca tudo que é orbital
        front_consig_validado_termino.loc[(front_consig_validado_termino['Orbital'].str.contains('SIM', na=False) & (front_consig_validado_termino['Análise'].isin(['', np.nan]))), 'Análise'] = 'NÃO LANÇAR - ORBITAL'
        
        # Marca Casos Patrick
        if not self.casos_capital is None:
            # print(f'casos capital:\n{self.casos_capital}')
            numero_operacao = self.casos_capital['NR. OPER.'].astype(str).str.slice(0, 9).tolist()
            self.casos_capital.insert(1, 'NR_OPER_EDITADO', numero_operacao, True)
            casos_capital_lista = self.casos_capital['NR_OPER_EDITADO'].astype(str).tolist()
            front_consig_validado_termino.loc[(front_consig_validado_termino['Contrato'].astype(str).str.slice(0, 9).isin(casos_capital_lista)), 'Análise'] = 'NÃO LANÇAR - CASOS PATRICK'

        # Marcar liquidados em StatusContrato
        front_consig_validado_termino.loc[(front_consig_validado_termino['Status'].str.contains('Liquidado|CANCELADO', na=False)), 'Análise'] = 'NÃO LANÇAR - LIQUIDADO'
        # Marca tudo que é Empréstimo
        # front_consig_validado_termino.loc[(front_consig_validado_termino['Tipo Operacao'].str.contains('EMPRÉSTIMO|EMPRESTIMO', na=False) & (front_consig_validado_termino['Análise'] == '')), 'Análise'] = 'NÃO LANÇAR - EMPRÉSTIMO'

        # Marca tudo que é Telesaque
        front_consig_validado_termino.loc[(front_consig_validado_termino['Tipo Conciliação'].str.contains('CARTÃO TS|CARTAO TS', na=False) & (front_consig_validado_termino['Análise'] == '')), 'Análise'] = 'NÃO LANÇAR - TELESAQUE'
    
        # Marca "NÃO LANÇAR - COMPLEMENTAR" nas células vazias da coluna Análise onde veio vazio na coluna de SITUAÇÃO
        front_consig_validado_termino.loc[(front_consig_validado_termino['Análise'] == '') & (front_consig_validado_termino['SITUAÇÃO'].isna()), 'Análise'] = 'NÃO LANÇAR - COMPLEMENTAR'

        front_consig_validado_termino.to_excel(
            fr'{self.caminho}\FRONT SEMI TRABALHADO INSS.xlsx',
            index=False, 
        )

        return front_consig_validado_termino

    def front_trabalhado(self):
        front_trabalhado = self.tratamento_front_preliminar()

        # Renomear colunas
        front_trabalhado.rename(columns={'Contrato': 'NR_OPER_EDITADO', 'CPF': 'CPF', 'Matricula': 'MATRICULA', 'Nome': 'CLIENTE', 
                                         'dtCessao': 'DT_BASE', 'Prestacao': 'VLR_PARC', 'Esteira': 'ESTEIRA','Tipo Operacao': 'PRODUTO', 'Convenio': 'ORIGEM_4'}, inplace=True)

        # Filtra só os que vão lançar
        front_trabalhado_lancar = front_trabalhado[front_trabalhado['Análise'] == 'LANÇAR'].copy()
        front_trabalhado_lancar.to_excel(
            fr'{self.caminho}\FRONT PARA LANÇAMENTO INSS.xlsx',
            index=False, 
        )

        # Cria arquivo de complementares + telesaque + orbital
        complementar_orbital_df = front_trabalhado[front_trabalhado['Análise'].str.contains('NÃO LANÇAR - COMPLEMENTAR|NÃO LANÇAR - TELESAQUE|NÃO LANÇAR - ORBITAL', na=False)].copy()
        complementar_orbital_df.to_excel(
            fr'{self.caminho}\FRONT COMPLEMENTARES TELESAQUE ORBITAL INSS.xlsx',
            index=False, 
        )

        return front_trabalhado_lancar, complementar_orbital_df

    def trata_front_final(self):
        front_trabalhado_lancar, complementar_orbital_df = self.front_trabalhado()

        # Separar as colunas necessárias
        front_trabalhado_lancar = front_trabalhado_lancar[['NR_OPER', 'NR_OPER_EDITADO', 'CPF', 'Análise', 'MATRICULA', 'CLIENTE', 'DT_BASE', 'VLR_PARC', 
                                                           'ESTEIRA', 'Saldo', 'SITUAÇÃO', 'Valor Averbado Reajustado', 'PRODUTO', 'ORIGEM_4']].copy()
        

        # Faz uma cópia do valor original, para controle
        front_trabalhado_lancar["VLR_PARC_ORIGINAL"] = front_trabalhado_lancar["VLR_PARC"]

        # Nova coluna para anotar quanto foi usado do "banco" de 30%
        front_trabalhado_lancar["VALOR_COMPLEMENTADO"] = 0.0
        front_trabalhado_lancar["STATUS_COMPLEMENTO"] = ""  # Total, Parcial, Nenhum
        front_trabalhado_lancar.insert(9, "VALOR A LANÇAR", '', True)

        # Soma dos valores de Complementar e Orbital
        soma_complementar = complementar_orbital_df.groupby('CPF')['VLR_PARC'].sum().reset_index(name="SOMA_COMPLEMENTAR_ORBITAL")

        # Junta os dados com a planilha principal
        front_final = front_trabalhado_lancar.merge(soma_complementar, on="CPF", how="left")

        # Preenche os NaN com zero (caso algum CPF não esteja em uma das duas planilhas)
        front_final["SOMA_COMPLEMENTAR_ORBITAL"] = front_final["SOMA_COMPLEMENTAR_ORBITAL"].fillna(0)

        # Calcula a soma total
        front_final["SOMA SOMASE"] = front_final["SOMA_COMPLEMENTAR_ORBITAL"]
        front_final["SOMA SOMASE"] = pd.to_numeric(front_final["SOMA SOMASE"], errors='coerce').fillna(0)

        # Remove colunas do Arquivo
        front_final = front_final.drop(columns=["SOMA_COMPLEMENTAR_ORBITAL"])

        front_trabalhado_lancar = front_final.copy()

        print(front_trabalhado_lancar[['Valor Averbado Reajustado', 'VLR_PARC']].dtypes)

        # 1. Converta as colunas para um formato numérico.
        #    Use os parâmetros 'decimal' e 'thousands' se seus dados usarem vírgula para decimal e ponto para milhar.
        #    'errors='coerce'' é muito útil: se ele não conseguir converter um valor, ele o transformará em NaN (nulo).

        colunas_para_converter = ['Valor Averbado Reajustado', 'VLR_PARC']
        for coluna in colunas_para_converter:
            # Ajuste os parâmetros decimal e milhar, conforme seus dados
            front_trabalhado_lancar[coluna] = pd.to_numeric(front_trabalhado_lancar[coluna], errors='coerce')

        # Preencha quaisquer valores que não puderam ser convertidos com 0 (ou outra estratégia que preferir)
        front_trabalhado_lancar[colunas_para_converter] = front_trabalhado_lancar[colunas_para_converter].fillna(0)

        # Calcula o "espaço" disponível em cada linha para receber um complemento.
        # .clip(0) garante que o resultado não seja negativo.
        front_trabalhado_lancar['ESPACO_PARA_COMPLEMENTO'] = (front_trabalhado_lancar['Valor Averbado Reajustado'] - front_trabalhado_lancar['VLR_PARC']).clip(0)
        print('Espaço Para Complemento, criado...\n\n')

        # a. Soma acumulada dos "pedidos" de complemento para cada CPF
        front_trabalhado_lancar['CUM_PEDIDO_COMPLEMENTO'] = front_trabalhado_lancar.groupby('CPF')['ESPACO_PARA_COMPLEMENTO'].cumsum()
        print('Espaço Para Complemento Acumulado, criado... \n\n')

        # b. Quanto já foi alocado para as linhas ANTERIORES do mesmo CPF
        alocado_anteriormente = front_trabalhado_lancar['CUM_PEDIDO_COMPLEMENTO'] - front_trabalhado_lancar['ESPACO_PARA_COMPLEMENTO']
        print('Acumulado Anteriormente, criado...\n\n')

        # c. Saldo restante do SOMA SOMASE disponível para a linha ATUAL
        saldo_restante_complemento = front_trabalhado_lancar['SOMA SOMASE'] - alocado_anteriormente
        print('Saldo Restante, calculado...\n\n')

        # d. O complemento REAL a ser adicionado é o MENOR entre o que a linha PODE RECEBER e o que nós TEMOS DE SALDO
        front_trabalhado_lancar['COMPLEMENTO_REAL'] = np.minimum(front_trabalhado_lancar['ESPACO_PARA_COMPLEMENTO'], saldo_restante_complemento.clip(0))
        print('Complemento Real, criado...\n\n')

        front_trabalhado_lancar['PARCELA COMPLEMENTO REAL'] = front_trabalhado_lancar['VLR_PARC'] + front_trabalhado_lancar['COMPLEMENTO_REAL']
        print('Parcela Complemento Real, calculado...\n\n')

        front_trabalhado_lancar['VALOR A LANÇAR'] = np.minimum(front_trabalhado_lancar['PARCELA COMPLEMENTO REAL'], front_trabalhado_lancar['Valor Averbado Reajustado'])
        print('Valor a Lançar, alocado...\n\n')

        print('Salvando Função tratado...')
        # Exporta os resultados
        front_trabalhado_lancar.to_excel(fr"{self.caminho}\LANÇAMENTO DE INSS TRATADO.xlsx", index=False)

        self.arquivo_lancamento(front_trabalhado_lancar)

    def arquivo_lancamento(self, funcao_tratado):
        print('Preparando arquivo de lançamento...')
        
        if self.averbados.empty:
            print("Aviso: Arquivo Averbados vazio. Pulando geração de lançamento final.")
            return

        funcao = funcao_tratado.copy()
        averbados = self.averbados.copy()

        # Prepara chaves
        if 'NR_OPER' in funcao.columns:
            funcao['NR_OPER_CURTO'] = funcao['NR_OPER'].astype(str).str.slice(0, 9)
        else:
            funcao['NR_OPER_CURTO'] = ''
            
        if 'NR_OPER_EDITADO' in averbados.columns:
            averbados['NR_OPER_EDITADO'] = averbados['NR_OPER_EDITADO'].astype(str)

        # Verifica colunas necessárias no averbados
        cols_averbados = ['NR_OPER_EDITADO']
        if 'EMPREGADOR' in averbados.columns: cols_averbados.append('EMPREGADOR')
        else: averbados['EMPREGADOR'] = ''
        
        if 'MATRÍCULA' in averbados.columns: cols_averbados.append('MATRÍCULA')
        else: averbados['MATRÍCULA'] = ''

        df_final = pd.merge(
            left=funcao,
            right=averbados[cols_averbados],
            left_on='NR_OPER_CURTO',
            right_on='NR_OPER_EDITADO',
            how='left'
        )

        inclusao_desconto = df_final.rename(columns={
            'NR_OPER': 'NR. OPER.',
            'CPF': 'CPF',
            'CLIENTE': 'CLIENTE',
            'VALOR A LANÇAR': 'VLR.PARC',
            'EMPREGADOR': 'EMPREGADOR',
            'NR_OPER_CURTO': 'PROPOSTA',
            'MATRÍCULA': 'MATRICULA/BENEFÍCIO'
        })

        # Garante colunas finais
        for col in ['NR. OPER.', 'CPF', 'CLIENTE', 'VLR.PARC', 'EMPREGADOR', 'PROPOSTA', 'MATRICULA/BENEFÍCIO']:
            if col not in inclusao_desconto.columns:
                inclusao_desconto[col] = ''

        inclusao_desconto['VLR.PARC'] = inclusao_desconto['VLR.PARC'].astype(str).str.replace(',', '.', regex=False)
        # Converte para float seguro
        inclusao_desconto['VLR.PARC'] = pd.to_numeric(inclusao_desconto['VLR.PARC'], errors='coerce')
        
        inclusao_desconto['PRAZO'] = ''

        colunas_finais = ['NR. OPER.', 'CPF', 'CLIENTE', 'VLR.PARC', 'EMPREGADOR', 'PROPOSTA',
                          'MATRICULA/BENEFÍCIO', 'PRAZO']
        inclusao_desconto = inclusao_desconto[colunas_finais]

        timestamp = datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
        caminho_arquivo = os.path.join(self.caminho, f'INSS_INCLUIR_DESCONTO_CARTÃO_{timestamp}.xlsx')

        inclusao_desconto.to_excel(caminho_arquivo, index=False)
        print(f'Arquivo de lançamento salvo em: {caminho_arquivo}')