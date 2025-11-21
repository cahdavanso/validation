from symtable import Class

import pandas as pd
import numpy as np
import xlrd
import openpyxl
from datetime import datetime
import tabula
from pandas.io.formats.style import Styler
import jinja2

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)


class INSS:
    def __init__ (self, orbital_file, funcao_file, arq_averbados, casos_capital,op_liquidados, conciliacao, tutela, caminho):
        self.orbital = pd.read_excel(orbital_file)
        self.funcao_bruto = pd.read_csv(funcao_file, encoding="ISO-8859-1", sep=";", on_bad_lines="skip")
        self.averbados = pd.read_excel(arq_averbados)
        self.casos_capital = pd.read_excel(casos_capital)
        self.op_liq = pd.read_excel(op_liquidados)
        self.conciliacao = pd.read_excel(conciliacao)
        self.tutela = pd.read_excel(tutela)
        self.caminho = caminho

        self.tratamento_funcao()

    def trata_conciliacao(self):
        conciliacao_tratado = self.conciliacao

        # Encontra o índice da primeira ocorrência de "CONTRATO" e altera
        '''for i, c in enumerate(cols):
            if c == "CONTRATO" and c != "CONTRATOS":
                cols[i] = "CONTRATOS"  # só a primeira vez
                break
            else:
                break'''
        conciliacao_tratado.rename(columns={conciliacao_tratado.columns[0]: 'CONTRATOS'}, inplace=True)
        print(f'primeira coluna de conciliação {conciliacao_tratado.columns[0]}')
        # Converte para lista de colunas
        cols = list(conciliacao_tratado.columns)
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

        # 2. Calcular prestação * prazo
        prestacao_vezes_prazo = conciliacao_tratado['PRESTAÇÃO'] * conciliacao_tratado['PRAZO']

        # 3. Calcular o resultado final
        conciliacao_tratado['Pago'] = soma_d8 - prestacao_vezes_prazo
        conciliacao_tratado['Saldo'] = conciliacao_tratado['Pago'] + conciliacao_tratado['RECEBIDO GERAL']

        return conciliacao_tratado

    def tratamento_funcao(self):
        funcao = self.funcao_bruto

        # print(cred_unificado['Esteira'].unique())

        # Por algum motivo a coluna de NR_OPER vem com esse bug no nome
        if 'ï»¿NR_OPER' in funcao.columns:
            funcao = funcao.rename(columns={'ï»¿NR_OPER': 'NR_OPER'})

        # Alterar o tipo do número de contrato do Função para String e da parcela para float
        funcao['NR_OPER'] = funcao['NR_OPER'].astype(str)
        # funcao['VLR_PARC'] = pd.to_numeric(funcao['VLR_PARC'], errors="coerce")

        codigo_editado = funcao['NR_OPER'].replace(r"\D", "", regex=True)
        funcao.insert(1, 'NR_OPER_EDITADO', codigo_editado, True)
        funcao['NR_OPER_EDITADO'] = funcao['NR_OPER_EDITADO'].str.slice(0, 9)

        funcao['NR_OPER_EDITADO'] = funcao['NR_OPER_EDITADO'].astype(str)

        # <-- CORREÇÃO: A linha "funcao.insert(3, 'CONCAT', '', True)" foi REMOVIDA daqui.

        # Insere as outras colunas vazias
        funcao.insert(8, 'CASOS CAPITAL', '', True)
        funcao.insert(9, 'OP_LIQ', '', True)
        funcao.insert(10, 'CONTRATO CONCILIACAO', '', True)
        funcao.insert(11, 'STATUS CONCILIACAO', '', True)
        funcao.insert(12, 'LIMINAR', '', True)
        funcao.insert(13, 'Saldo', '', True)
        funcao.insert(14, 'SITUAÇÃO', '', True)
        funcao.insert(15, 'Valor Averbado Reajustado', True)
        if 'Análise' not in funcao.columns:
            funcao.insert(2, 'Análise', '', True)

        funcao['Análise'] = funcao['Análise'].fillna('')
        funcao['SITUAÇÃO'] = funcao['SITUAÇÃO'].fillna('')

        # Concat de CPF + PARCELA
        funcao['VLR_PARC'] = funcao['VLR_PARC'].str.replace('.', '', regex=False)
        funcao['VLR_PARC'] = funcao['VLR_PARC'].str.replace(',', '.', regex=False)
        funcao['VLR_PARC'] = pd.to_numeric(funcao['VLR_PARC'], errors='coerce').fillna(0)

        # OP LIQUIDADO
        try:
            op_liq = self.op_liq
            n_operacao_liq = op_liq
            n_operacao_liq['Número Operação'] = op_liq['Nº OPERAÇÃO']
            funcao['OP_LIQ'] = funcao['NR_OPER'].map(
                n_operacao_liq.set_index('Nº OPERAÇÃO')['Número Operação'].to_dict())

        except Exception as e:
            op_liq = pd.DataFrame(columns=['Nº OPERAÇÃO'])
            print(f"Planilha de Operações Liquidadas está vazia {e}")


        funcao['OP_LIQ'] = funcao['OP_LIQ'].fillna('')

        # Condição 2: Coluna 'PRODUTO' contém 'EMPRESTIMO' ou 'BENS DURAVEIS'
        # segue sua lógica original para CAPITAL

        # print(f'Produtos de INSS: {funcao['PRODUTO'].unique()}')

        mask_produto_orbital = (
                funcao['PRODUTO'].str.contains('000061 - CARTÃO PLÁSTICO', na=False)
                | funcao['PRODUTO'].str.contains('000094 - CARTÃO PLÁSTICO - RE', na=False)
                | funcao['PRODUTO'].str.contains('CARTÃ\x83O PLÃ\x81STICO - RE', na=False)
                | funcao['PRODUTO'].str.contains('000061 - CARTÃ\x83O PLÃ\x81STICO')
        )
        mask_produto_complementar = (funcao['PRODUTO'].str.contains('000012 - DIG INSS REP LEGAL', na=False)
                                     | funcao['PRODUTO'].str.contains('000015 - DIG INSS', na=False)
                                     | funcao['PRODUTO'].str.contains('000106 - CARTÃO TS', na=False)
                                     | funcao['PRODUTO'].str.contains('CARTÃ\x83O TS', na=False)
                                     | funcao['PRODUTO'].str.contains('000098 - DIG INSS 30%', na=False)
                                     | funcao['PRODUTO'].str.contains('000104 - CARTAO SEGURO - A VISTA', na=False)
                                     | funcao['PRODUTO'].str.contains('000105 - CARTAO - SEG PARC', na=False))


        #

        # Máscara final
        # mask_final = mask_produto_orbital | mask_produto_complementar

        # print(funcao['Análise'][funcao['Análise'] == "NÃO"])

        # CASOS CAPITAL
        casos_patrick = self.casos_capital
        casos_capital = casos_patrick
        casos_capital['Numero Operacao'] = casos_patrick['NR. OPER.']
        funcao['CASOS CAPITAL'] = funcao['NR_OPER'].map(casos_capital.set_index('NR. OPER.')['Numero Operacao'].to_dict())

        funcao['CASOS CAPITAL'] = funcao['CASOS CAPITAL'].fillna('')

        capital_mask = funcao['CASOS CAPITAL'] != ''


        # CONCILIAÇÃO
        conciliacao_tratado = self.trata_conciliacao()

        print('Arquivo de Conciliação, analisado\n\n')

        # Converte para lista de colunas
        cols = list(conciliacao_tratado.columns)

        # Encontra o índice da primeira ocorrência de "CONTRATO" e altera
        for i, c in enumerate(cols):
            if c == "CONTRATO" and c != "CONTRATOS":
                cols[i] = "CONTRATOS"  # só a primeira vez
                break
            else:
                break

        # Atualiza o DataFrame com novos nomes
        conciliacao_tratado.columns = cols
        conciliacao_tratado['CONTRATOS'] = conciliacao_tratado['CONTRATOS'].astype('Int64').astype(str)

        contratos_conciliacao = pd.DataFrame()

        '''Precisei fazer um Dataframe separado porque por algum motivo ele não conseguia usar os contratos como índice,
           e puxar os mesmos contratos... Eu poderia criar uma coluna de contratos dentro da propria conciliacao mas resolvi
           criar um DataFrame novo só com essas colunas já que é tudo que vamos precisar delas'''

        contratos_conciliacao['CONTRATO'] = conciliacao_tratado['CONTRATOS']
        contratos_conciliacao['CONTRATO PUXAR'] = conciliacao_tratado['CONTRATOS']
        funcao['CONTRATO CONCILIACAO'] = funcao['NR_OPER_EDITADO'].map(
            contratos_conciliacao.set_index('CONTRATO')['CONTRATO PUXAR'].to_dict())
        # Precisei transformar os códigos da coluna "CONTRATO CONCILIACAO" em número, mas para isso precisei transformar os vazios em 0
        # funcao['CONTRATO CONCILIACAO'] = pd.to_numeric(funcao['CONTRATO CONCILIACAO'], errors='coerce').fillna(0).astype(int)

        # Agora preciso transformar os zeros em NaN
        funcao.loc[funcao['CONTRATO CONCILIACAO'] == 0, 'CONTRATO CONCILIACAO'] = np.nan

        # E de NaN para vazio mesmo... Quem sabe assim ele reconhece o número de contrato. PS: Não era esse o problema
        funcao['CONTRATO CONCILIACAO'] = funcao['CONTRATO CONCILIACAO'].fillna('')

        # Criar coluna auxiliar (1 = preenchido, 0 = vazio)
        funcao['has_conciliacao'] = funcao['CONTRATO CONCILIACAO'].notna() & (funcao['CONTRATO CONCILIACAO'] != '')

        # Ordenar colocando os contratos da conciliação preenchidos primeiro
        funcao = funcao.sort_values(by="has_conciliacao", ascending=False).drop(columns="has_conciliacao")

        # Puxar o último status para o credbase
        status = conciliacao_tratado.filter(like='ST ')
        status_name = status.columns[-1]

        funcao.loc[:, 'STATUS CONCILIACAO'] = funcao['NR_OPER_EDITADO'].map(
            conciliacao_tratado.set_index('CONTRATOS')[status_name]).to_dict()

        print('Status da Conciliação, analisado\n\n')

        # print(f'status \n{cred_copy[cred_copy['Codigo_Credbase'] == 300846910]}')

        # Puxar o saldo para o credbase
        funcao.loc[:, 'Saldo'] = funcao['NR_OPER_EDITADO'].map(
            conciliacao_tratado.set_index('CONTRATOS')['Saldo']).to_dict()

        # Garante que a coluna de status seja tratada como texto, e em minúsculas para facilitar comparações
        status_cred = funcao['STATUS CONCILIACAO'].fillna('')


        # Cria uma condição booleana para os casos onde a observação deve ser "NÃO"
        condicao_status = (
            # status_cred.str.contains('SUSPENSO') |
                status_cred.str.contains('QUITADO') |
                status_cred.str.contains('TERMINO DE CONTRATO') |
                status_cred.str.contains('LIQUIDADO') |
                status_cred.str.contains('CANCELADO') |
                status_cred.str.contains('FUTURO')
            # status_cred.str.contains('JUDICIAL')
        )

        '''condicao_saldo = funcao['Saldo'].fillna(float(-1.0)) >= 0.01

        # Aplica a condição: se qualquer uma for verdadeira, OBS = 'NÃO'; caso contrário, OBS = ''
        funcao['Análise'] = np.where(condicao_saldo, 'NÃO', '')'''

        def obs_situacao(row):
            '''Função que junta "NÃO" com o motivo (versão corrigida)'''

            # Garante que situacao seja uma string e remove espaços extras
            situacao = str(row['SITUAÇÃO']).strip()

            if situacao not in ['0 - Ativo', 'Ativo', '']:
                return f'NÃO - {situacao}'
            elif situacao in ['0 - Ativo', 'Ativo']:
                return 'LANÇAR'
            else:  # Este else agora só será acionado por um texto realmente vazio ('')
                return row['Análise']

        averbados = self.averbados
        averbados['NR_OPER_EDITADO'] = averbados['NR_OPER_EDITADO'].astype(str)

        # Adiciona o que é Situação Ativo e o Valor Averbado Reajustado
        funcao['SITUAÇÃO'] = funcao['NR_OPER_EDITADO'].map(averbados.set_index("NR_OPER_EDITADO")['SITUAÇÃO'].to_dict())
        print('SITUAÇÃO do Arquivo de Averbados, analisado\n\n')

        funcao['Valor Averbado Reajustado'] = funcao['NR_OPER_EDITADO'].map(
            averbados.set_index("NR_OPER_EDITADO")['MARGEM REAJUSTADA'].to_dict())
        print('Valor Averbado Reajustado, analisado\n\n')

        funcao['Análise'] = funcao.apply(obs_situacao, axis=1)
        funcao['Análise'] = funcao['Análise'].replace('NÃO - nan', '')

        # ====================================== TUTELA LIMINAR ==================================================

        # Agora tem essa droga de tutela também
        # Dicionário de mapeamento: cada banco "oficial" -> lista de possíveis nomes no credbase
        liminares = self.tutela
        if liminares is not None:
            mask_liminar = funcao['CPF'].isin(liminares['CPF'])
            funcao['LIMINAR'] = funcao['CPF'].map(liminares.set_index("CPF")["CONTRATO"].to_dict())
            funcao.loc[mask_liminar, 'Análise'] = 'NÃO - LIMINAR'

        # ==================================== FIM TUTELA LIMINAR ====================================================

        print('LIMINAR, analisado\n\n')

        # Procura os Liquidados
        # Condição 1: A coluna 'LIMINAR' está vazia (ou era nula)
        condicao_liminar = (funcao['LIMINAR'].fillna('') == '')

        # Condição 2: A coluna 'OP_LIQ' TEM um valor (não está vazia e não era nula)
        condicao_op_liq = (funcao['OP_LIQ'].fillna('') != '')

        # Aplicando a lógica combinada
        funcao.loc[condicao_liminar & condicao_op_liq, 'Análise'] = 'NÃO - LIQUIDADO'

        print('Operações Liquidadas, analisado\n\n')

        # MASK CASOS CAPITAL
        funcao.loc[
            (funcao['Análise'] == '') & (funcao['CASOS CAPITAL'] != ''), 'Análise'] = 'NÃO LANÇAR - ENVIADO CAPITAL'

        # SALDO POSITIVO
        mask_positivo = (funcao['Saldo'] >= 0) & (funcao['NR_OPER'].str.startswith('600'))
        funcao.loc[((funcao['LIMINAR'] == '') | (funcao['OP_LIQ'] == '')) & mask_positivo, 'Análise'] = "NÃO - SALDO"
        print('Saldo da Conciliação, analisado\n\n')
        # Agora, aplique o 'NÃO' nos locais corretos usando a máscara
        funcao.loc[((funcao['LIMINAR'] == '') | (funcao['OP_LIQ'] == '')) & mask_produto_orbital, 'Análise'] = 'NÃO LANÇAR - ORBITAL'
        print('ORBITAL, analisado\n\n')

        funcao.loc[((funcao['LIMINAR'] == '') | (funcao['OP_LIQ'] == '')) & (funcao['Análise'] == '') & mask_produto_complementar, 'Análise'] = 'NÃO LANÇAR - COMPLEMENTAR'
        print('COMPLEMENTAR, analisado\n\n')

        # Preenche vazio em Análise
        funcao.loc[funcao['Análise'] == '', 'Análise'] = 'NÃO LANÇAR - COMPLEMENTAR EXTRA'

        # FUNÇÃO INTERMEDIARIO
        funcao.to_excel(fr'{self.caminho}\FUNÇÃO INTERMEDIÁRIO.xlsx', index=False)

        # FUNÇÃO SÓ O QUE É LANÇAR
        funcao_tratado = funcao[funcao['Análise'] == 'LANÇAR'].copy()
        print('Separando apenas os casos a serem lançados...\n\n')

        # print(funcao_tratado.columns)

        # COMPLEMENTARES
        valores_desejados = ['NÃO LANÇAR - COMPLEMENTAR', 'NÃO LANÇAR - COMPLEMENTAR EXTRA']
        funcao_complementos = funcao[funcao['Análise'].isin(valores_desejados)]

        funcao_tratado.to_excel(fr'{self.caminho}\FUNCAO COM NÃO.xlsx', index=False)

        self.trata_funcao_final(funcao_tratado, funcao_complementos)


    def trata_funcao_final(self, funcao, funcao_complementos):

        # Complementares
        complementares = funcao_complementos.copy()

        # Separar só as colunas corretas
        funcao = funcao[['NR_OPER', 'NR_OPER_EDITADO', 'Análise', 'CPF', 'MATRICULA','CLIENTE', 'DT_BASE',
                         'VLR_PARC', 'Saldo', 'SITUAÇÃO', 'Valor Averbado Reajustado', 'PRODUTO','ORIGEM_4']].copy()
        '''funcao = funcao[['NR.PROP.', 'NR. OPER.', 'NR. OP. ', 'MOVIMENTAÇÃO', 'OBSERVAÇÃO', 'CPF', 'Matricula', 'CLIENTE',
                         'VLR_PARC', 'SITUAÇÃO INSS', 'VL RESERVADO AJUSTADO INSS']]'''


        # Faz uma cópia do valor original, para controle
        funcao["VLR_PARC_ORIGINAL"] = funcao["VLR_PARC"]

        # Nova coluna para anotar quanto foi usado do "banco" de 30%
        funcao["VALOR_COMPLEMENTADO"] = 0.0
        funcao["STATUS_COMPLEMENTO"] = ""  # Total, Parcial, Nenhum
        funcao.insert(9, "VALOR A LANÇAR", '', True)

        # Soma dos valores de Complementar e Orbital
        soma_complementar = complementares.groupby('CPF')['VLR_PARC'].sum().reset_index(name="SOMA_COMPLEMENTAR")
        soma_orbital = self.orbital.groupby('CPF/CNPJ')['VALOR DESCONTO'].sum().reset_index(name="SOMA_ORBITAL")

        # Renomeia a coluna para que o merge funcione
        soma_orbital = soma_orbital.rename(columns={"CPF/CNPJ": "CPF"})

        # Junta os dados com a planilha principal
        funcao_final = funcao.merge(soma_complementar, on="CPF", how="left")
        funcao_final = funcao_final.merge(soma_orbital, on="CPF", how="left")

        # Preenche os NaN com zero (caso algum CPF não esteja em uma das duas planilhas)
        funcao_final["SOMA_COMPLEMENTAR"] = funcao_final["SOMA_COMPLEMENTAR"].fillna(0)
        funcao_final["SOMA_ORBITAL"] = funcao_final["SOMA_ORBITAL"].fillna(0)

        # Calcula a soma total
        funcao_final["SOMA SOMASE"] = funcao_final["SOMA_COMPLEMENTAR"] + funcao_final["SOMA_ORBITAL"]

        # Remove colunas do Arquivo
        funcao_final = funcao_final.drop(columns=["SOMA_COMPLEMENTAR", "SOMA_ORBITAL"])

        funcao = funcao_final

        print(funcao[['Valor Averbado Reajustado', 'VLR_PARC']].dtypes)

        # 1. Converta as colunas para um formato numérico.
        #    Use os parâmetros 'decimal' e 'thousands' se seus dados usarem vírgula para decimal e ponto para milhar.
        #    'errors='coerce'' é muito útil: se ele não conseguir converter um valor, ele o transformará em NaN (nulo).

        colunas_para_converter = ['Valor Averbado Reajustado', 'VLR_PARC']
        for coluna in colunas_para_converter:
            # Ajuste os parâmetros decimal e milhar, conforme seus dados
            funcao[coluna] = pd.to_numeric(funcao[coluna], errors='coerce')

        # Preencha quaisquer valores que não puderam ser convertidos com 0 (ou outra estratégia que preferir)
        funcao[colunas_para_converter] = funcao[colunas_para_converter].fillna(0)

        # Calcula o "espaço" disponível em cada linha para receber um complemento.
        # .clip(0) garante que o resultado não seja negativo.
        funcao['ESPACO_PARA_COMPLEMENTO'] = (funcao['Valor Averbado Reajustado'] - funcao['VLR_PARC']).clip(0)
        print('Espaço Para Complemento, criado...\n\n')

        # a. Soma acumulada dos "pedidos" de complemento para cada CPF
        funcao['CUM_PEDIDO_COMPLEMENTO'] = funcao.groupby('CPF')['ESPACO_PARA_COMPLEMENTO'].cumsum()
        print('Espaço Para Complemento Acumulado, criado... \n\n')

        # b. Quanto já foi alocado para as linhas ANTERIORES do mesmo CPF
        alocado_anteriormente = funcao['CUM_PEDIDO_COMPLEMENTO'] - funcao['ESPACO_PARA_COMPLEMENTO']
        print('Acumulado Anteriormente, criado...\n\n')

        # c. Saldo restante do SOMA SOMASE disponível para a linha ATUAL
        saldo_restante_complemento = funcao['SOMA SOMASE'] - alocado_anteriormente
        print('Saldo Restante, calculado...')

        # d. O complemento REAL a ser adicionado é o MENOR entre o que a linha PODE RECEBER e o que nós TEMOS DE SALDO
        funcao['COMPLEMENTO_REAL'] = np.minimum(funcao['ESPACO_PARA_COMPLEMENTO'], saldo_restante_complemento.clip(0))
        print('Complemento Real, criado...\n\n')

        funcao['PARCELA COMPLEMENTO REAL'] = funcao['VLR_PARC'] + funcao['COMPLEMENTO_REAL']
        print('Parcela Complemento Real, calculado...\n\n')

        funcao['VALOR A LANÇAR'] = np.minimum(funcao['PARCELA COMPLEMENTO REAL'], funcao['Valor Averbado Reajustado'])
        print('Valor a Lançar, alocado...\n\n')

        print('Salvando Função tratado...')
        # Exporta os resultados
        funcao.to_excel(fr"{self.caminho}\LANÇAMENTO DE INSS TRATADO.xlsx", index=False)

        self.arquivo_lancamento(funcao)


    def arquivo_lancamento(self, funcao_tratado):
        """
            Versão refatorada da função, utilizando pd.merge para mais eficiência e legibilidade.
            """
        print('Preparando arquivo de lançamento...')

        # 1. Prepara os DataFrames para a junção (merge)
        funcao = funcao_tratado.copy()
        averbados = self.averbados.copy()

        # Garante que as chaves de junção sejam do mesmo tipo (string)
        funcao['NR_OPER_CURTO'] = funcao['NR_OPER'].astype(str).str.slice(0, 9)
        averbados['NR_OPER_EDITADO'] = averbados['NR_OPER_EDITADO'].astype(str)

        # 2. Usa pd.merge para buscar 'EMPREGADOR' e 'MATRÍCULA' de uma só vez
        # Isso substitui todo o processo de .map()
        df_final = pd.merge(
            left=funcao,
            right=averbados[['NR_OPER_EDITADO', 'EMPREGADOR', 'MATRÍCULA']],
            left_on='NR_OPER_CURTO',
            right_on='NR_OPER_EDITADO',
            how='left'  # 'left' garante que nenhuma linha de 'funcao' seja perdida
        )

        # 3. Cria o DataFrame de lançamento com os nomes de coluna corretos
        # Selecionando e renomeando as colunas necessárias em um único passo
        inclusao_desconto = df_final.rename(columns={
            'NR_OPER': 'NR. OPER.',
            'CPF': 'CPF',
            'CLIENTE': 'CLIENTE',
            'VALOR A LANÇAR': 'VLR.PARC',
            'EMPREGADOR': 'EMPREGADOR',
            'NR_OPER_CURTO': 'PROPOSTA',
            'MATRÍCULA': 'MATRICULA/BENEFÍCIO'
        })

        # 4. Ajusta os tipos de dados e valores finais
        inclusao_desconto['VLR.PARC'] = inclusao_desconto['VLR.PARC'].astype(str).str.replace(',', '.').astype(float)
        inclusao_desconto['PRAZO'] = ''

        # 5. Seleciona apenas as colunas na ordem desejada
        colunas_finais = ['NR. OPER.', 'CPF', 'CLIENTE', 'VLR.PARC', 'EMPREGADOR', 'PROPOSTA',
                          'MATRICULA/BENEFÍCIO', 'PRAZO']
        inclusao_desconto = inclusao_desconto[colunas_finais]

        # 6. Gera o nome do arquivo com data e hora para evitar sobreposição
        timestamp = datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
        caminho_arquivo = fr'{self.caminho}\INSS_INCLUIR_DESCONTO_CARTÃO_{timestamp}.xlsx'

        inclusao_desconto.to_excel(caminho_arquivo, index=False)
        print(f'Arquivo de lançamento salvo em: {caminho_arquivo}')
