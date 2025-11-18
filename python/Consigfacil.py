import pandas as pd
import xlrd
import openpyxl
from datetime import datetime
import re
import numpy as np
import chardet

rejeitados = ['/']


class CONSIGFACIL:
    # O construtor agora recebe DataFrames (ou None), não caminhos/listas de caminhos
    def __init__(self, portal_file_list, convenio, credbase, funcao, conciliacao, andamento_list, caminho, liquidados=None, historico_refin=None, tutela=None):

        # A API FastAPI já leu, unificou e tratou a codificação. 
        # Aqui, apenas atribuímos o DataFrame ou None.

        # Averbados (portal_file_list)
        self.averbados = portal_file_list
        if self.averbados is None:
            self.averbados = pd.DataFrame()
            
        if 'Valor da reserva' not in self.averbados.columns:
            self.averbados['Valor da reserva'] = 0.0

        # Credbase
        self.creds_unificados = credbase
        if self.creds_unificados is None:
            self.creds_unificados = pd.DataFrame()

        # Andamento
        self.andamento = andamento_list
        if self.andamento is None:
            self.andamento = pd.DataFrame()


        self.convenio = convenio

        # Função
        self.funcao_bruto = funcao
        if self.funcao_bruto is None:
            self.funcao_bruto = pd.DataFrame()


        # Conciliação
        # Mantive a criação do conciliacao_falso para garantir que o código não quebre se for None
        conciliacao_falso = pd.DataFrame(columns=['CONTRATOS', 'CPF', 'PRESTAÇÃO', 'PRAZO', 'D8 JUN 25', 'ST JUL 25','RECEBIDO GERAL'])
        conciliacao_falso['CONTRATOS'] = 123
        conciliacao_falso['CPF'] = '123.456'
        conciliacao_falso['PRESTAÇÃO'] = 10
        conciliacao_falso['PRAZO'] = 96
        conciliacao_falso['D8 JUN 25'] = 10
        conciliacao_falso['ST JUL 25'] = 'DESCONTO TOTAL'
        conciliacao_falso['RECEBIDO GERAL'] = 0

        self.conciliacao = conciliacao if conciliacao is not None else conciliacao_falso

        # Liquidados
        self.liquidados_file = liquidados if liquidados is not None else None

        if self.liquidados_file is not None:
            # Certificando que o tipo dos contratos do Operações Liquidadas
            self.liquidados_file['Nº OPERAÇÃO'] = self.liquidados_file['Nº OPERAÇÃO'].astype(str)

        # Tutela (Liminar)
        self.tutela = tutela if tutela is not None else None
        self.caminho = caminho # Caminho de saída

        # Histórico de Refins
        self.historico = historico_refin if historico_refin is not None else None

        self.tratamento_funcao()
# (O restante da classe CONSIGFACIL permanece INALTERADO)

    def unificacao_creds(self):

        # RENOMEIA A COLUNA CODIGO_CREDBASE
        if 'Codigo Credbase' in self.creds_unificados.columns or 'ï»¿Codigo_Credbase' in self.creds_unificados.columns:
            cred = self.creds_unificados.rename(columns={'Codigo Credbase': 'Codigo_Credbase', 'ï»¿Codigo_Credbase': 'Codigo_Credbase'})
            self.creds_unificados = cred

        crebase_reduzido = self.creds_unificados[['Codigo_Credbase', 'Banco(s) quitado(s)', 'Filial', 'Esteira',
                                                 'Esteira(dias)', 'Tipo', 'Operacao', 'Situacao', 'Inicio', 'Cliente',
                                                 'Data Averbacao', 'CPF', 'Convenio', 'Banco', 'Parcela', 'Prazo',
                                                 'Tabela', 'Matricula']]

        # Vamos alterar o tipo do Codigo_Credbase já que agora a coluna está com o nome certo
        crebase_reduzido['Codigo_Credbase'] = crebase_reduzido['Codigo_Credbase'].astype(str)


        crebase_reduzido['Parcela'] = crebase_reduzido['Parcela'].str.replace('.', '')
        crebase_reduzido['Parcela'] = crebase_reduzido['Parcela'].str.replace(',', '.')
        crebase_reduzido['Parcela'] = pd.to_numeric(crebase_reduzido['Parcela'], errors='coerce')

        crebase_reduzido.to_excel(fr'{self.caminho}\CREDBASE UNIFICADO.xlsx', index=False)

        # print(self.creds_unificados)

        return crebase_reduzido


    def tratamento_funcao(self):
        funcao = self.funcao_bruto

        # print(cred_unificado['Esteira'].unique())

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
        funcao.insert(4, 'CONTSE SEMI TRABALHADO', '', True)
        if 'CONTSE LOCAL' not in funcao.columns:
            funcao.insert(5, 'CONTSE LOCAL', '', True)
        funcao.insert(6, 'Diff', '', True)
        funcao.insert(7, 'OP_LIQ', '', True)
        funcao.insert(8, 'CONTRATO CONCILIACAO', '', True)
        if 'OBS' not in funcao.columns:
            funcao.insert(10, 'OBS', '', True)

        # Concat de CPF + PARCELA
        funcao['VLR_PARC'] = funcao['VLR_PARC'].str.replace('.', '', regex=False)
        funcao['VLR_PARC'] = funcao['VLR_PARC'].str.replace(',', '.', regex=False)
        funcao['VLR_PARC'] = pd.to_numeric(funcao['VLR_PARC'], errors='coerce').fillna(0)

        # Esta linha agora é a ÚNICA que cria a coluna 'CONCAT', o que é o correto.
        funcao['CONCAT'] = funcao['CPF'].astype(str) + funcao['VLR_PARC'].astype(str)

        # Criação do Credbase Semi Trabalhado
        condicoes_1 = ['11 FORMALIZAÇÃO ', '07.0 QUITAÇÃO - LIBERAÇÃO TROCO', '07.4 ENVIA CESSÃO FUNDO',
                       '11.2  DETERMINAÇÃO JUDICIAL', '11.2 ACORDO CLIENTE', '10.7.0 INGRESSAR COM PROCESSO OU AÇÃO JURIDICO',
                       '10.7.1 ACORDO EM ANDAMENTO', '02.03 AGUARDANDO PROCESSAMENTO CARTÃO', '02.3 AGUARDANDO PROCESSAMENTO DE CARTÃO',
                       '07.0 QUITACAO – ENVIO DE CESSAO', '07.1 – QUITACAO – PAGAMENTO AO CLIENTE',
                       '07.1.1 QUITACAO - CORRECAO DE CCB', '07.2 TED DEVOLVIDA – PAGAMENTO AO CLIENTE',
                       '10.3.1 CONTRATO AVERBADO AGUARDANDO LIQUIDAÇÃO REFIN',
                       '08.0 LIBERAÇÃO TROCO', '09.0 PAGO', '09.1 - APOSENTADORIA IGEPREV - AVERB. TOTAL',
                       '09.2 - APOSENTADORIA IGEPREV - AVERB. PARCIAL', '07.1 \x96 QUITACAO \x96 PAGAMENTO AO CLIENTE',
                       '10.3.1 CONTRATO AVERBADO AGUARDANDO LIQUIDAÇÃO REFIN',
                       '07.2 TED DEVOLVIDA \x96 PAGAMENTO AO CLIENTE',
                       '10.5 AGUARDANDO AVERBACAO COMPRA OUTROS CONVENIOS', '07.0 QUITACAO \x96 ENVIO DE CESSAO',
                       '10.6 CONTRATO AVERBADO - AGUARDANDO COMPROVANTE DE RESERVA',
                       '02.03 AGUARDANDO PROCESSAMENTO CARTÃO', 'INTEGRADO', 'RISCO DA OPERAÇÃO - ÓBITO', 'RISCO DA OPERAÇÂO-DEMAIS SITUAÇÕES',
                       '10.7 CONTRATO NÃO AVERBADO - AGUARDANDO RESOLUÇÃO', '11.1 CONTRATO FÍSICO ENVIADO AO BANCO ',
                       '11.PROBLEMAS DE AVERBAÇÃO', '15.0\tRISCO DA OPERAÇÂO-DEMAIS SITUAÇÕES',
                       '15.0	RISCO DA OPERAÇÂO-DEMAIS SITUAÇÕES', '14.0 RISCO DA OPERAÇÃO - ÓBITO',
                       '07.4 ENVIA CESSAO FUNDO', '08.0 LIBERACAO TROCO', '07.1 AGUARDANDO AVERBACAO',
                       '11.PROBLEMAS DE AVERBACAO', '07.2 AGUARDANDO DESAVERBACAO IF',
                       '07.5 AGUARDANDO DESAVERBACAO BENEFICIO', '10.7.0 INGRESSAR COM PROCESSO OU AÇÃO JURIDICO',
                       '10.3 AGUARDANDO AVERBACAO COMPRA EMPRESTIMO SIAPE', 'OPERAÇÃO TEMPORARIAMENTE SUSPENSA', 'FISICOS PARAIBA']

        cred_unificado = self.unificacao_creds()

        # Garante que a coluna 'Esteira' exista antes de filtrar
        if 'Esteira' in cred_unificado.columns:
            cred_semi = cred_unificado[cred_unificado['Esteira'].isin(condicoes_1)].copy()

            # Cria a coluna CONCAT CPF PARC apenas se cred_semi não for vazio
            if not cred_semi.empty:
                concat_cpf_parc = cred_semi['CPF'].astype(str) + cred_semi['Parcela'].astype(str)
                cred_semi.insert(12, 'CONCAT CPF PARC', concat_cpf_parc, True)

                # Contse Semi Trabalhado
                contse_concat_semi_cred = cred_semi.groupby('CONCAT CPF PARC')['CONCAT CPF PARC'].count().to_dict()

                # <-- CORREÇÃO 2: Garantido que o .map é chamado na coluna ['CONCAT'] e não no DataFrame 'funcao'
                funcao['CONTSE SEMI TRABALHADO'] = funcao['CONCAT'].map(contse_concat_semi_cred)
                funcao['CONTSE SEMI TRABALHADO'] = funcao['CONTSE SEMI TRABALHADO'].fillna(0)
        # print(funcao['CONTSE SEMI TRABALHADO'])

        # Contse Local
        funcao['CONTSE LOCAL'] = funcao.groupby('CONCAT')['CONCAT'].transform('count')

        # OP LIQUIDADO
        try:
            op_liq = self.liquidados_file
            n_operacao_liq = op_liq
            n_operacao_liq['Número Operação'] = op_liq['Nº OPERAÇÃO']
            funcao['OP_LIQ'] = funcao['NR_OPER'].map(n_operacao_liq.set_index('Nº OPERAÇÃO')['Número Operação'].to_dict())

        except Exception as e :
            op_liq = pd.DataFrame(columns=['Nº OPERAÇÃO'])
            print(f"Planilha de Operações Liquidadas está vazia {e}")


        funcao['OP_LIQ'] = funcao['OP_LIQ'].fillna('')

        funcao.loc[(funcao['OBS'] == '') & (funcao['OP_LIQ'] != ''), 'OBS'] = 'NÃO'

        for idx, row in funcao.iterrows():
            if funcao.loc[idx, 'CONTSE LOCAL'] > funcao.loc[idx, 'CONTSE SEMI TRABALHADO']:
                funcao.loc[idx, 'Diff'] = 'VERDADEIRO'
            else:
                funcao.loc[idx, 'Diff'] = 'FALSO'

        # Condição 1: Coluna 'Diff' contém 'FALSO'
        mask_diff = funcao['Diff'].str.contains('FALSO', na=False)

        # Condição 2: Coluna 'PRODUTO' contém 'EMPRESTIMO'
        mask_produto = funcao['PRODUTO'].str.contains('EMPRESTIMO', na=False)

        # A máscara final é Verdadeira se QUALQUER uma das condições for Verdadeira
        mask_final = mask_diff | mask_produto

        # Agora, aplique o 'NÃO' nos locais corretos usando a máscara
        funcao.loc[mask_final, 'OBS'] = 'NÃO'

        # print(funcao['OBS'][funcao['OBS'] == "NÃO"])

        # CONCILIAÇÃO
        conciliacao_tratado = self.conciliacao

        conciliacao_tratado.rename(columns={conciliacao_tratado.columns[0]: 'CONTRATOS'}, inplace=True)

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
        funcao['CONTRATO CONCILIACAO'] = funcao['NR_OPER_EDITADO'].map(contratos_conciliacao.set_index('CONTRATO')['CONTRATO PUXAR'].to_dict())
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
        funcao = funcao.sort_values(by='CPF', ascending=True)

        # Verifica se CONTSE LOCAL é igual á CONTSE SEMI CRED e se existe na concilicação
        for idx, row in funcao.iterrows():
            if (
                    row['CONTSE LOCAL'] == row['CONTSE SEMI TRABALHADO']
                    and row['CONTRATO CONCILIACAO'] != ''
                    and "EMPRESTIMO" not in str(row['PRODUTO'])
            ):
                funcao.loc[idx, 'OBS'] = ''

        # FUNÇÃO INTERMEDIARIO
        funcao.to_excel(fr'{self.caminho}\FUNÇÃO INTERMEDIÁRIO.xlsx', index=False)

        funcao_tratado = funcao[funcao['OBS'] == '']
        self.unificacao_cred_funcao(cred_semi, funcao_tratado)

    def unificacao_cred_funcao(self, cred, func):
        funcao = func.copy()

        # Cria a coluna NR_OPER_EDITADO
        # Remove tudo que não for número
        funcao['VLR_PARC'] = pd.to_numeric(funcao['VLR_PARC'], errors='coerce')


        # Transforma a coluna de NR_OPER_EDITADO EM NúMERO
        # funcao['NR_OPER_EDITADO'] = funcao['NR_OPER_EDITADO'].astype(int)


        # Cria a coluna Esteira no Função
        funcao.insert(5, 'Esteira', '', True)
        funcao['Esteira'] = 'INTEGRADO'

        funcao.to_excel(fr'{self.caminho}\FUNCAO TRATADO {self.convenio} AUTOMATIZADO {str(datetime.now().month).zfill(2)}{datetime.now().year}.xlsx', index=False)

        # Certificar-se de que as colunas 'Código' e 'NR_OPER' estão presentes
        if 'Codigo_Credbase' in cred.columns and 'NR_OPER_EDITADO' in funcao.columns:
            # Empilhar os valores da coluna 'NR_OPER' abaixo dos valores da coluna 'Código'
            nova_coluna_codigo = cred['Codigo_Credbase'].tolist() + funcao['NR_OPER_EDITADO'].tolist()
            nova_coluna_matricula = cred['Matricula'].tolist() + funcao['MATRICULA'].tolist()
            nova_coluna_esteira = cred['Esteira'].tolist() + funcao['Esteira'].tolist()
            nova_coluna_inicio = cred['Inicio'].tolist() + funcao['DT_BASE'].tolist()
            nova_coluna_cliente = cred['Cliente'].tolist() + funcao['CLIENTE'].tolist()
            nova_coluna_cpf = cred['CPF'].tolist() + funcao['CPF'].tolist()
            nova_coluna_banco = cred['Banco'].tolist() + funcao['ORIGEM_2'].tolist()
            nova_coluna_produto = cred['Tipo'].tolist() + funcao['PRODUTO'].tolist()
            nova_coluna_prazo = cred['Prazo'].tolist() + funcao['PARC'].tolist()
            nova_coluna_convenio = cred['Convenio'].tolist() + funcao['ORIGEM_4'].tolist()
            nova_coluna_parcela = cred['Parcela'].tolist() + funcao['VLR_PARC'].tolist()

            # Criar um novo DataFrame para armazenar o resultado
            nova_planilha_codigo = pd.DataFrame(nova_coluna_codigo, columns=['Codigo_Credbase'])

            # Manter as outras colunas da planilha A
            outras_colunas_codigo = cred.drop(columns=['Codigo_Credbase'])

            # Resetar os índices de ambos antes do concat
            nova_planilha_codigo.reset_index(drop=True, inplace=True)
            outras_colunas_codigo.reset_index(drop=True, inplace=True)

            # cred = cred.drop('Esteira', axis=1)
            cred = pd.concat([nova_planilha_codigo, outras_colunas_codigo.reindex(nova_planilha_codigo.index)], axis=1)

            # Adiciona Integrado e Não Integrado na coluna esteira do Credbase
            cred['Esteira'] = nova_coluna_esteira

            # Adiciona as matriculas na coluna de matricula
            cred['Matricula'] = nova_coluna_matricula

            # Junta os clientes do Função junto a coluna de clientes do Credbase
            cred['Cliente'] = nova_coluna_cliente

            # Junta os CPFs do Função junto a coluna de CPFs do Credbase
            cred['CPF'] = nova_coluna_cpf

            # Adiciona o convenio devido na coluna Convenio
            cred['Convenio'] = nova_coluna_convenio

            # Adiciona os bancos junto do cred
            cred['Banco'] = nova_coluna_banco

            # Junta a coluna de VLR_PARC do função junto à coluna Parcela do Credbase
            cred['Parcela'] = nova_coluna_parcela

            # Junta a coluna de PRODUTO do função junto à coluna Tipo do Credbase
            cred['Tipo'] = nova_coluna_produto

            # Junta a coluna DataBase do função junto à coluna Inicio do Credbase
            cred['Inicio'] = nova_coluna_inicio

            # Junta a coluna PARC do função junto à coluna Prazo do Credbase
            cred['Prazo'] = nova_coluna_prazo

        cred['Tabela'] = cred['Tabela'].fillna('CARTÃO')

        crebase_reduzido = cred[['Codigo_Credbase', 'Banco(s) quitado(s)', 'Filial', 'Esteira', 'Esteira(dias)', 'Tipo',
                                 'Operacao', 'Situacao', 'Inicio', 'Cliente', 'Data Averbacao', 'CPF', 'Convenio', 'Banco',
                                 'Parcela', 'Prazo', 'Tabela', 'Matricula']]

        crebase_reduzido.to_excel(rf'{self.caminho}\Teste Credbase Reduzido.xlsx', index=False)

        self.validacao_termino(crebase_reduzido, funcao)

    def trata_conciliacao(self):
        conciliacao_tratado = self.conciliacao
        # Converte para lista de colunas


        # Encontra o índice da primeira ocorrência de "CONTRATO" e altera
        # print(f'primeira coluna de conciliação {conciliacao_tratado.columns[0]}')
        conciliacao_tratado.rename(columns={conciliacao_tratado.columns[0]: 'CONTRATOS'}, inplace=True)

        cols = list(conciliacao_tratado.columns)
        conciliacao_tratado.columns = cols
        conciliacao_tratado['CONTRATOS'] = conciliacao_tratado['CONTRATOS'].astype(str)
        conciliacao_tratado = conciliacao_tratado.drop_duplicates(subset='CONTRATOS')
        # Atualiza o DataFrame com novos nomes


        conciliacao_tratado = conciliacao_tratado

        # 1. Selecionar colunas com "d8" no nome e somar por linha (axis=1)
        # "D8 " precisa ficar com espaço para que a coluna "CONVENIO D8" não atrapalhe na hora da soma
        colunas_d8 = conciliacao_tratado.filter(like='D8 ').columns
        for col in colunas_d8:
            tipos = conciliacao_tratado[col].apply(type).value_counts()
            '''print(f"Coluna {col}:")
            print(tipos)
            print()'''
        conciliacao_tratado[colunas_d8] = conciliacao_tratado[colunas_d8].apply(pd.to_numeric, errors='coerce')

        soma_d8 = conciliacao_tratado.filter(like='D8 ').sum(axis=1)

        # 2. Calcular prestação * prazo
        prestacao_vezes_prazo = conciliacao_tratado['PRESTAÇÃO'] * conciliacao_tratado['PRAZO']

        # 3. Calcular o resultado final
        conciliacao_tratado['Pago'] = soma_d8 - prestacao_vezes_prazo
        conciliacao_tratado['Saldo'] = conciliacao_tratado['Pago'] + conciliacao_tratado['RECEBIDO GERAL']

        return conciliacao_tratado


    def validacao_termino(self, cred, func):
        funcao = func.copy()
        cred_copy = cred.copy()
        conciliacao_tratado = self.trata_conciliacao()

        # Puxar o último status para o credbase
        status = conciliacao_tratado.filter(like='ST ')
        status_name = status.columns[-1]
        '''print(f'Tipo do contrato no cred: {type(cred_copy.loc[1, 'Codigo_Credbase'])}')
        print(f'Tipo do contrato da conciliação: {type(conciliacao_tratado.loc[1, 'CONTRATOS'])}')'''

        # Certifica que todos os contratos no Credbase trabalhado são do mesmo tipo
        # cred['Codigo_Credbase'] = cred['Codigo_Credbase'].astype(str)

        cred_copy.loc[:, 'Status'] = cred_copy['Codigo_Credbase'].map(conciliacao_tratado.set_index('CONTRATOS')[status_name]).to_dict()
        conciliacao_tratado.to_excel(fr'{self.caminho}\Conciliacao_TESTE.xlsx', index=False)


        # print(f'status \n{cred_copy[cred_copy['Codigo_Credbase'] == 300846910]}')

        # Puxar o saldo para o credbase
        cred_copy.loc[:, 'Saldo'] = cred_copy['Codigo_Credbase'].map(conciliacao_tratado.set_index('CONTRATOS')['Saldo']).to_dict()

        # Valor que vai ser lançado
        # Substitui NaN em "Saldo" por um valor muito alto (para que "Parcela" seja escolhida)
        valor_a_lancar = np.minimum(np.abs(cred_copy['Saldo']).fillna(float('inf')), cred_copy['Parcela'])

        cred_copy['Valor a lançar'] = valor_a_lancar

        self.andamento_func(cred_copy, funcao)

    def andamento_func(self, cred, func):
        # Andamento
        funcao = func.copy()
        # Primeiro, criamos um dicionário de correspondência
        # modalidade_dict = andam_file.set_index('Código na instituição')['Modalidade'].to_dict()
        # prazo_dict = andam_file.set_index('Código na instituição')['Prazo Total'].to_dict()

        andam_file = self.trata_cod_and(self.andamento)


        # Aplica a função ao DataFrame cred
        cred['PRAZO'] = self.substituir_modalidade(andam_file, cred)

        # preenche espaços vazios na coluna Andamento
        status_andamento = cred['PRAZO'].fillna('')


        # Verifica se contém prazo
        cond_prazo = (status_andamento != '') & (status_andamento != 1) & (status_andamento != 0)

        # Verifica se contém 'Empréstimo'
        '''cond_empr = status_andamento.str.contains('Empréstimo', na=False)
    
        # Tenta converter para número e verifica se > 2 (vai colocar NaN onde não for número)
        status_numerico = pd.to_numeric(status_andamento, errors='coerce')
        cond_numerico = status_numerico > 2
    
        # Combina as duas condições
        condicao_andamento = cond_empr | cond_numerico'''

        # Coloca em obs o que não vamos usar
        # Garante que a coluna de status seja tratada como texto, e em minúsculas para facilitar comparações
        status_cred = cred['Status'].fillna('')

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

        condicao_saldo = cred['Saldo'].fillna(float(-1.0)) >= 0.01

        # Aplica a condição: se qualquer uma for verdadeira, OBS = 'NÃO'; caso contrário, OBS = ''
        cred['OBS'] = np.where(condicao_saldo | cond_prazo, 'NÃO', '')

        '''cred.to_excel(
            r"C:\\Users\Guilherme\Documents\CONSIGFACIL\PREF PORTO VELHO IPAM\RELATORIOS\Teste Credbase Unificado.xlsx",
            index=False)'''

        self.averbados_func(cred)

    # Função para decidir o valor da nova modalidade
    def substituir_modalidade(self, andam_file, cred):
        # 1. Identifica todas as colunas com 'Contrato' no nome
        colunas_contratos = [col for col in andam_file.columns if 'Contrato' in col]

        # 2. Cria uma coluna 'Prazo' vazia no Credbase
        if 'PRAZO' not in cred.columns:
            cred['PRAZO'] = None

        # 3. Cria um dicionário auxiliar: contrato → prazo
        contrato_para_prazo = {}

        if andam_file['Valor da Parcela'].dtype == 'object':
            andam_file['Valor da Parcela'] = andam_file['Valor da Parcela'].str.replace(".", '')
            andam_file['Valor da Parcela'] = andam_file['Valor da Parcela'].str.replace(",", '.')
            andam_file['Valor da Parcela'] = pd.to_numeric(andam_file['Valor da Parcela'], errors='coerce')
            # print(f'Modalidade e Parcela do Código 407337: {andam_file.loc[andam_file['Código'] == 407337, ['Modalidade', 'Valor da Parcela']]}')

        # 4. Tira casos que são previdencia e igual a 20, 40, 60
        andam_file_sem_prev_seguro = andam_file[~(((andam_file['Modalidade'] == 'Previdência') | (
                andam_file['Modalidade'] == 'Seguros') | (andam_file['Modalidade'] == 'Mensalidade'))
                                                  & ((andam_file['Valor da Parcela'] == 20) | (
                        andam_file['Valor da Parcela'] == 40)
                                                     | (andam_file['Valor da Parcela'] == 60)))]

        # print(andam_file_sem_prev_seguro['Serviço'].unique())

        '''print(f'Andamento completo: {len(andam_file)}')
        print(f'Andamento sem previdência: {len(andam_file_sem_prev_seguro)}')'''

        # Para cada linha no arquivo de andamentos, verifica todas as colunas de contrato
        for _, row in andam_file_sem_prev_seguro.iterrows():
            prazo = row.get('Prazo Total')  # Pode ser 'Prazo Total' dependendo do nome
            for col in colunas_contratos:
                contrato = row.get(col)
                if pd.notna(contrato):
                    contrato_para_prazo[str(contrato).strip()] = prazo

        andam_file_sem_prev_seguro.to_excel(rf'{self.caminho}\ANDAMENTO GERAL {self.convenio}.xlsx', index=False)

        # 4. Aplica a busca no Credbase
        return cred['Codigo_Credbase'].astype(str).str.strip().map(contrato_para_prazo)


    def separar_contratos(self, contrato):
        # Inicializa uma lista para armazenar os contratos separados
        contratos_separados = []
        posicao = 0

        while posicao < len(contrato):
            # Verifica se o contrato começa com "200" ou "300" e tem 9 ou 10 dígitos
            if (contrato[posicao:posicao + 3] in ["200", "300", "201","301", "302"]) and (len(contrato) - posicao >= 9):
                if len(contrato) - posicao >= 10 and contrato[posicao + 9].isdigit():
                    # Corrige contratos de 10 dígitos para 9 dígitos removendo o último dígito
                    contratos_separados.append(contrato[posicao:posicao + 9])
                    posicao += 10
                else:
                    contratos_separados.append(contrato[posicao:posicao + 9])
                    posicao += 9
            # Verifica se o contrato tem 6 dígitos
            elif len(contrato) - posicao >= 6 and contrato[posicao:posicao + 6].isdigit():
                contratos_separados.append(contrato[posicao:posicao + 6])
                posicao += 6
            elif len(contrato) - posicao >= 5 and contrato[posicao:posicao + 5].isdigit():
                contratos_separados.append(contrato[posicao:posicao + 5])
                posicao += 5
            elif len(contrato) - posicao >= 4 and contrato[posicao:posicao + 4].isdigit():
                contratos_separados.append(contrato[posicao:posicao + 4])
                posicao += 4
            else:
                posicao += 1

        # Retorna os contratos separados por barras
        return '/'.join(contratos_separados)

    def trata_cod_and(self, andamentos):
        # PUXA OS ARQUIVOS À SEREM TRATADOS
        data_averbados = andamentos
        # print(data_averbados.columns)

        # SUBSTITUIMOS CARACTER POR NADA
        contrato_editado = data_averbados['Código na instituição'].astype(str).apply(
            lambda x: ''.join(char for char in x if char.isdigit() or char in rejeitados))

        contrato_editado = contrato_editado.replace('//', '/', regex=True)

        # INSERE A COLUNA CONTRATO EDITADO COM OS NÚMEROS JÁ TRATADOS
        if "Contrato Editado" not in data_averbados.columns:
            data_averbados.insert(2, "Contrato Editado", contrato_editado, True)

        data_averbados['Contrato Editado'] = data_averbados['Contrato Editado'].apply(self.separar_contratos)

        # Verifica se há contratos separados para dividir em novas colunas
        if data_averbados['Contrato Editado'].str.contains('/').any():
            # Separa os contratos em novas colunas
            df_contratos_separados = data_averbados['Contrato Editado'].str.split('/', expand=True)

            # Cria listas de nomes de colunas para contratos
            contrato_cols = [f'Contrato_{i + 1}' for i in range(df_contratos_separados.shape[1])]
            df_contratos_separados.columns = contrato_cols

            # Converte para int (cuidado com valores nulos ou não numéricos)
            '''for col in contrato_cols:
                df_contratos_separados[col] = pd.to_numeric(df_contratos_separados[col], errors='coerce').astype(
                    'Int64')  # Int64 permite nulos'''

            # Descobre a posição da coluna 'Contrato Editado'
            col_index = data_averbados.columns.get_loc('Contrato Editado')

            # Divide o DataFrame original em duas partes
            antes = data_averbados.iloc[:, :col_index + 1]  # Inclui 'Contrato Editado'
            depois = data_averbados.iloc[:, col_index + 1:]

            # Concatena com os novos dados no meio
            data_averbados = pd.concat([antes, df_contratos_separados, depois], axis=1)

        return data_averbados


    def credbase_trabalhado_func(self, cred):
        # CREDBASE TRABALHADO
        # cred['Esteira'] = cred['Esteira'].str.replace('\x96', '-', regex=False)

        conciliacao_tratado = self.trata_conciliacao()

        creds_unificados = self.unificacao_creds()

        condicoes_1 = ['11 FORMALIZAÇÃO ', '07.0 QUITAÇÃO - LIBERAÇÃO TROCO', '07.4 ENVIA CESSÃO FUNDO',
                       '11.2  DETERMINAÇÃO JUDICIAL', '11.2 ACORDO CLIENTE', '10.7.0 INGRESSAR COM PROCESSO OU AÇÃO JURIDICO',
                       '10.7.1 ACORDO EM ANDAMENTO', '02.03 AGUARDANDO PROCESSAMENTO CARTÃO', '02.3 AGUARDANDO PROCESSAMENTO DE CARTÃO',
                       '07.0 QUITACAO – ENVIO DE CESSAO', '07.1 – QUITACAO – PAGAMENTO AO CLIENTE',
                       '07.1.1 QUITACAO - CORRECAO DE CCB', '07.2 TED DEVOLVIDA – PAGAMENTO AO CLIENTE',
                       '10.3.1 CONTRATO AVERBADO AGUARDANDO LIQUIDAÇÃO REFIN',
                       '08.0 LIBERAÇÃO TROCO', '09.0 PAGO', '09.1 - APOSENTADORIA IGEPREV - AVERB. TOTAL',
                       '09.2 - APOSENTADORIA IGEPREV - AVERB. PARCIAL', '07.1 \x96 QUITACAO \x96 PAGAMENTO AO CLIENTE',
                       '10.3.1 CONTRATO AVERBADO AGUARDANDO LIQUIDAÇÃO REFIN',
                       '07.2 TED DEVOLVIDA \x96 PAGAMENTO AO CLIENTE',
                       '10.5 AGUARDANDO AVERBACAO COMPRA OUTROS CONVENIOS', '07.0 QUITACAO \x96 ENVIO DE CESSAO',
                       '10.6 CONTRATO AVERBADO - AGUARDANDO COMPROVANTE DE RESERVA',
                       '02.03 AGUARDANDO PROCESSAMENTO CARTÃO', 'INTEGRADO', 'RISCO DA OPERAÇÃO - ÓBITO', 'RISCO DA OPERAÇÂO-DEMAIS SITUAÇÕES',
                       '10.7 CONTRATO NÃO AVERBADO - AGUARDANDO RESOLUÇÃO', '11.1 CONTRATO FÍSICO ENVIADO AO BANCO ',
                       '11.PROBLEMAS DE AVERBAÇÃO', '15.0\tRISCO DA OPERAÇÂO-DEMAIS SITUAÇÕES',
                       '15.0	RISCO DA OPERAÇÂO-DEMAIS SITUAÇÕES', '14.0 RISCO DA OPERAÇÃO - ÓBITO',
                       '07.4 ENVIA CESSAO FUNDO', '08.0 LIBERACAO TROCO', '07.1 AGUARDANDO AVERBACAO',
                       '11.PROBLEMAS DE AVERBACAO', '07.2 AGUARDANDO DESAVERBACAO IF',
                       '07.5 AGUARDANDO DESAVERBACAO BENEFICIO', '10.7.0 INGRESSAR COM PROCESSO OU AÇÃO JURIDICO',
                       '10.3 AGUARDANDO AVERBACAO COMPRA EMPRESTIMO SIAPE', 'OPERAÇÃO TEMPORARIAMENTE SUSPENSA', 'FISICOS PARAIBA']

        cred_esteira = cred[cred['Esteira'].isin(condicoes_1)]
        semi_cred = creds_unificados[creds_unificados['Esteira'].isin(condicoes_1)].copy()


        if self.convenio not in ['PREF. RECIFE', 'PREF. CAMPINA GRANDE']:
            # Separa as tabelas de lançamento
            condicoes_2 = cred_esteira['Tabela'].str.contains('CART') & ~cred_esteira['Tabela'].str.contains('BEN')
            # Seleciona Tipo Cartão
            condicoes_3 = cred_esteira['Tipo'].str.contains('Cartão de crédito') & ~cred_esteira['Tabela'].str.contains(
                'CART')
            condicoes_3_5 = cred_esteira['Tipo'].str.contains('Cartão de crédito') & cred_esteira['Tabela'].str.contains(
                'BEN')
            cred_tipo_ben = cred_esteira[condicoes_3_5]
        else:
            # Separa as tabelas de lançamento
            condicoes_2 = cred_esteira['Tabela'].str.contains('CART')
            # Seleciona Tipo Cartão
            condicoes_3 = cred_esteira['Tipo'].str.contains('Cartão') & ~cred_esteira['Tabela'].str.contains('CART')
            # Seleciona tipo Cartão de crédito na tabela BEN
            cred_tipo_ben = pd.DataFrame()

        cred_tab_cart = cred_esteira[condicoes_2]

        cred_tipo = cred_esteira[condicoes_3]

        # Tira tabela Cartão
        condicoes_4 = cred_esteira['Tipo'].str.contains('Cartão')
        cred_tipo = cred_tipo[condicoes_4]

        # Tira tipo Cartão
        cred_amor = cred_esteira[~cred_esteira['Tipo'].isin(condicoes_4)]
        # Tira tabela Cartão
        '''condicoes_5 = ~cred_amor['Tabela'].str.contains('CART')
        cred_amor = cred_amor[condicoes_5]'''
        # Verifica Amortização em Bancos quitados depois de tirar tipo e tabela cartão
        condicoes_6 = cred_amor['Banco(s) quitado(s)'].str.contains('AMOR', na=False)
        cred_amor['Banco(s) quitado(s)'] = cred_amor['Banco(s) quitado(s)']
        cred_amor = cred_amor[condicoes_6]
        credbase_trabalhado = pd.concat([cred_tipo, cred_amor, cred_tipo_ben, cred_tab_cart], ignore_index=True)


        # Seleciona a consignatária correta
        '''if consignataria == 'CIASPREV':
            consig_list = ['BANCO ACC', 'CIASPREV', 'QUERO MAIS CRÉDITO']
        elif consignataria == 'CAPITAL':
            consig_list = ['BANCO CAPITAL', 'BANCO CAPITAL S.A.', 'CB/CAPITAL', 'CB/CAPITAL	', 'CC BANCO CAPITAL S.A. ',
                           'CAPITAL', 'Banco CB DIGITAL', 'QUERO MAIS CRÉDITO', 'AKI CAPITAL', 'J.A BANK ', 'J.A BANK',
                           'CAPITAL*']
        elif consignataria == 'CLICKBANK':
            consig_list = ['CB/CLICK BANK', 'CB/CLICK BANK	', 'Banco CB DIGITAL', 'QUERO MAIS CRÉDITO', 'CLICK']
        elif consignataria == 'HOJE':
            consig_list = ['BANCO HP', 'QUERO MAIS CRÉDITO', 'AKI CAPITAL']
        elif consignataria == 'ABCCARD':
            consig_list = ['ABCCARD', 'QUERO MAIS CRÉDITO', 'AKI CAPITAL']
        elif consignataria == 'CB/BEM CARTÕES':
            consig_list = ['CB/BEM CARTÕES', 'QUERO MAIS CRÉDITO', 'BEM CARTÕES', 'AKI CAPITAL']
        credbase_trabalhado = credbase_trabalhado[credbase_trabalhado['Banco'].isin(consig_list)]'''

        credbase_trabalhado = credbase_trabalhado[~credbase_trabalhado['Banco'].isin(['BANCO FUTURO '])]

        # Tira ponto e traço do CPF
        cpf = credbase_trabalhado['CPF'].replace("\D", "", regex=True)
        credbase_trabalhado.insert(17, 'cpf', cpf, True)
        # Tira o zero à esquerda
        credbase_trabalhado['cpf'] = credbase_trabalhado['cpf'].astype(float)

        # Certifica que todos os contratos no Credbase trabalhado são do mesmo tipo
        # credbase_trabalhado['Codigo_Credbase'] = credbase_trabalhado['Codigo_Credbase'].astype(str)

        # Puxar o último status para o credbase
        status = conciliacao_tratado.filter(like='ST ')
        status_name = status.columns[-1]
        # Puxar o saldo para o credbase
        credbase_trabalhado.loc[:, 'Saldo'] = credbase_trabalhado['Codigo_Credbase'].map(
            conciliacao_tratado.set_index('CONTRATOS')['Saldo']).to_dict()
        credbase_trabalhado.loc[:, 'Status'] = credbase_trabalhado['Codigo_Credbase'].map(
            conciliacao_tratado.set_index('CONTRATOS')[status_name]).to_dict()

        # Coloca em obs o que não vamos usar
        # Garante que a coluna de status seja tratada como texto, e em minúsculas para facilitar comparações
        status_cred = credbase_trabalhado['Status'].fillna('')

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


        # preenche espaços vazios na coluna Andamento
        status_prazo= credbase_trabalhado['PRAZO'].fillna('')

        # Verifica se contém prazo
        cond_prazo = (status_prazo != '') & (status_prazo != 1) & (status_prazo != 0)


        # Aplica a condição: se qualquer uma for verdadeira, OBS = 'NÃO'; caso contrário, OBS = ''
        credbase_trabalhado['OBS'] = np.where(cond_prazo, 'NÃO', '')


        # ======================================  LIMINAR ==================================================

        # Agora tem essa droga de tutela também
        # Dicionário de mapeamento: cada banco "oficial" -> lista de possíveis nomes no credbase
        if self.tutela is not None:
            liminares = self.tutela

            mapa_bancos = {
                "CIASPREV": ['BANCO ACC', 'CIASPREV'],
                "CAPITAL": ['BANCO CAPITAL', 'BANCO CAPITAL S.A.', 'CB/CAPITAL', 'CB/CAPITAL\t',
                            'CC BANCO CAPITAL S.A. ', 'CAPITAL', 'Banco CB DIGITAL', 'QUERO MAIS CRÉDITO', 'AKRK',
                            'AKI CAPITAL', 'J.A BANK ', 'J.A BANK', 'CAPITAL*'],
                "CLICKBANK": ['CB/CLICK BANK', 'CB/CLICK BANK\t', 'Banco CB DIGITAL','AKRK',
                              'QTUTELAUERO MAIS CRÉDITO', 'CLICK'],
                "HP": ['BANCO HP'],
                "ABCCARD": ['ABCCARD'],
                "BEMCARTOES": ['CB/BEM CARTÕES', 'BEM CARTÕES']
            }

            # Também criaremos um mapeamento para os nomes do arquivo de liminares
            mapa_liminares = {
                "CIASPREV": "CIASPREV - CENTRO DE INTEGRACAO E ASSISTENCIA AOS SERVIDORES PUBLICOS PREVIDENCIA PRIVADA",
                "CAPITAL": "CAPITAL CONSIG SOCIEDADE DE CREDITO DIRETO S.A",
                "CLICKBANK": "CLICKBANK INSTITUICAO DE PAGAMENTOS LTDA",
                "HP": "HOJE PREVIDÊNCIA PRIVADA",
                "BEMCARTOES": "BEMCARTOES BENEFICIOS S.A"
            }

            # Função para padronizar os nomes de bancos do credbase
            def normalizar_banco_credbase(nome):
                if pd.isna(nome):
                    return None
                nome = nome.strip().upper()
                for banco, aliases in mapa_bancos.items():
                    if any(alias.strip().upper() in nome for alias in aliases):
                        return banco
                return None  # se não bater com nada

            # Função para padronizar os nomes do arquivo liminares
            def normalizar_banco_liminar(nome):
                if pd.isna(nome):
                    return None
                nome = nome.strip().upper()
                for banco, nome_oficial in mapa_liminares.items():
                    if nome_oficial.strip().upper() == nome:
                        return banco
                return None

            # --- Aplicação no DataFrame ---
            # Padroniza banco no credbase
            credbase_trabalhado['BANCO_PAD'] = credbase_trabalhado['Banco'].apply(normalizar_banco_credbase)

            # Padroniza banco no liminares
            liminares['BANCO_PAD'] = liminares['CONSIGNATARIA'].apply(normalizar_banco_liminar)

            # Agora cria chaves combinando CPF e banco padronizado
            credbase_trabalhado['CHAVE'] = credbase_trabalhado['CPF'].astype(str) + "_" + credbase_trabalhado[
                'BANCO_PAD'].astype(str)
            liminares['CHAVE'] = liminares['CPF'].astype(str) + "_" + liminares['BANCO_PAD'].astype(str)

            # credbase_trabalhado.drop('BANCO_PAD', axis=1)

            # liminares.drop('BANCO_PAD', axis=1)

            # Mask contratos
            mask_contratos_liminar = credbase_trabalhado['Codigo_Credbase'].astype(str).isin(liminares['CONTRATO'].astype(str))
            # print(mask_contratos_liminar.value_counts())

            # Verifica se a chave está em liminares
            mask_liminar = credbase_trabalhado['CHAVE'].isin(liminares['CHAVE'])

            # Marca OBS = NÃO onde a chave bateu
            credbase_trabalhado.loc[mask_liminar | mask_contratos_liminar, 'OBS'] = 'NÃO - LIMINAR'

        # ==================================== FIM TUTELA LIMINAR ====================================================


        # SALDO POSITIVO
        mask_positivo = credbase_trabalhado['Saldo'] >= 0
        credbase_trabalhado.loc[mask_positivo, 'OBS'] = "NÃO"

        credbase_trabalhado.to_excel(fr'{self.caminho}\TESTE CREDBASE TRABALHADO.xlsx', index=False)

        # Tira os NÃO do credbase trabalhado
        mask_nao = credbase_trabalhado['OBS'].fillna('').str.strip().isin(["NÃO", "NÃO - LIMINAR"])
        credbase_trabalhado = credbase_trabalhado.loc[~mask_nao].copy()

        # Aqui o contrato não aparece

        # =========================================================================================== #
        #                                   REFIN QUE LANÇAREMOS                                      #
        # =========================================================================================== #

        historico_refin = self.historico
        andam_file = self.trata_cod_and(self.andamento)

        def refin():
            averbados = self.averbados

            '''soma_valores_dict = averbados.groupby('CPF')['Valor da Reserva'].sum().to_dict()
            averbados['SOMASE'] = averbados['CPF'].map(soma_valores_dict)'''
            averbados['CONCAT'] = averbados['CPF'].astype(str) + averbados['Valor da reserva'].astype(str)

            if self.convenio not in ['PREF. CAMPINA GRANDE']:
                averbados = averbados[averbados['Modalidade'] == 'Cartão de Crédito']
            else:
                averbados = averbados[averbados['Modalidade'].isin(['Cartão de Crédito', 'Cartão Benefício (Compras)'])]

            averbados.to_excel(fr'{self.caminho}/averbados_unif.xlsx', index=False)

            if self.convenio in ['GOV. MA', 'PREF. PAÇO DO LUMIAR', 'PREF. BAYEUX']:
                # Criar uma cópia só para o caso de +20 reais no BANCO HP
                semi_cred_hp20 = semi_cred.copy()
                semi_cred_hp20.loc[semi_cred_hp20['Banco'] == 'BANCO HP', 'Parcela'] += 20

                # Criar CONCAT com +20
                semi_cred_hp20['CONCAT'] = semi_cred_hp20['CPF'].astype(str) + semi_cred_hp20['Parcela'].astype(str)

                # CONCAT original (sem ajuste)
                semi_cred['CONCAT'] = semi_cred['CPF'].astype(str) + semi_cred['Parcela'].astype(str)

                # CONCAT no credbase_trabalhado
                cred_trabalhado_concat = credbase_trabalhado['CPF'].astype(str) + credbase_trabalhado['Parcela'].astype(str)
                if "CONCAT" not in credbase_trabalhado.columns:
                    credbase_trabalhado.insert(22, 'CONCAT', cred_trabalhado_concat, True)

                # Dicionário SOMASE
                soma_condicional_dict_averb = credbase_trabalhado.groupby('CONCAT')['Parcela'].sum().to_dict()
                averbados['SOMASE'] = averbados['CONCAT'].map(soma_condicional_dict_averb).fillna(0)



                # Casos que não bateram de primeira
                somase_zero = averbados[averbados['SOMASE'] == 0]

                somase_zero.to_excel(fr'{self.caminho}\SOMASE ZERO TESTE.xlsx', index=False)
                semi_cred.to_excel(fr'{self.caminho}\NOVO SEMI CRED.xlsx', index=False)

                # 1ª tentativa: verificar se algum desses casos bate com +20
                casos_batidos_20 = semi_cred_hp20[semi_cred_hp20['CONCAT'].isin(somase_zero['CONCAT'])]

                # Para os que ainda não bateram, tentar com o valor original
                restantes = somase_zero[~somase_zero['CONCAT'].isin(casos_batidos_20['CONCAT'])]
                casos_batidos_normal = semi_cred[semi_cred['CONCAT'].isin(restantes['CONCAT'])]

                # Juntar os dois resultados
                casos_batidos = pd.concat([casos_batidos_20, casos_batidos_normal], ignore_index=True)

                casos_batidos['Valor a lançar'] = casos_batidos['Parcela']

                # Se quiser manter só os de Refin
                # df_refin = casos_batidos[casos_batidos['Tipo'] == 'Refin'] & (casos_batidos['OBS'] != 'NÃO')]
                df_refin = casos_batidos
            else:
                # CONCAT original (sem ajuste)
                semi_cred['CONCAT'] = semi_cred['CPF'].astype(str) + semi_cred['Parcela'].astype(str)

                # CONCAT no credbase_trabalhado
                cred_trabalhado_concat = credbase_trabalhado['CPF'].astype(str) + credbase_trabalhado['Parcela'].astype(
                    str)
                credbase_trabalhado.insert(22, 'CONCAT', cred_trabalhado_concat, True)

                # Dicionário SOMASE
                soma_condicional_dict_averb = credbase_trabalhado.groupby('CONCAT')['Parcela'].sum().to_dict()
                averbados['SOMASE'] = averbados['CONCAT'].map(soma_condicional_dict_averb).fillna(0)

                # Casos que não bateram de primeira
                somase_zero = averbados[averbados['SOMASE'] == 0]

                somase_zero.to_excel(fr'{self.caminho}\SOMASE ZERO TESTE.xlsx', index=False)
                semi_cred.to_excel(fr'{self.caminho}\NOVO SEMI CRED.xlsx', index=False)

                casos_batidos_normal = semi_cred[semi_cred['CONCAT'].isin(somase_zero['CONCAT'])]

                # Juntar os dois resultados
                casos_batidos = casos_batidos_normal

                # Se quiser manter só os de Refin
                df_refin = casos_batidos[casos_batidos['Tipo'] == 'Refin']


            return df_refin

        df_refin = refin()

        df_refin.to_excel(fr'{self.caminho}\REFIN.xlsx', index=False)
        credbase_trabalhado = pd.concat([credbase_trabalhado, df_refin])

        # ==================================== HISTÓRICO DE REFIN ======================================================

        if historico_refin is not None:
            historico_refin = historico_refin.rename(
                columns={'Codigo Credbase': 'Codigo_Credbase', 'ï»¿Codigo_Credbase': 'Codigo_Credbase'})
            # lista das colunas do primeiro DataFrame
            nova_coluna_codigo = credbase_trabalhado['Codigo_Credbase'].tolist() + historico_refin['Codigo_Credbase'].tolist()
            nova_coluna_matricula = credbase_trabalhado['Matricula'].tolist() + historico_refin['Matricula'].tolist()
            nova_coluna_esteira = credbase_trabalhado['Esteira'].tolist() + historico_refin['Esteira'].tolist()
            nova_coluna_inicio = credbase_trabalhado['Inicio'].tolist() + historico_refin['Inicio'].tolist()
            nova_coluna_cliente = credbase_trabalhado['Cliente'].tolist() + historico_refin['Cliente'].tolist()
            nova_coluna_cpf = credbase_trabalhado['CPF'].tolist() + historico_refin['CPF'].tolist()
            nova_coluna_banco = credbase_trabalhado['Banco'].tolist() + historico_refin['Banco'].tolist()
            nova_coluna_produto = credbase_trabalhado['Tipo'].tolist() + historico_refin['Tipo'].tolist()
            nova_coluna_prazo = credbase_trabalhado['Prazo'].tolist() + historico_refin['Prazo'].tolist()
            nova_coluna_convenio = credbase_trabalhado['Convenio'].tolist() + historico_refin['Convenio'].tolist()
            nova_coluna_parcela = credbase_trabalhado['Parcela'].tolist() + historico_refin['Parcela'].tolist()
            nova_coluna_tabela = credbase_trabalhado['Tabela'].tolist() + historico_refin['Tabela'].tolist()
            nova_coluna_valor_lancar = credbase_trabalhado['Valor a lançar'].tolist() + historico_refin['Valor a lançar'].tolist()

            # Criar um novo DataFrame para armazenar o resultado
            nova_planilha_codigo = pd.DataFrame(nova_coluna_codigo, columns=['Codigo_Credbase'])

            # Manter as outras colunas da planilha A
            outras_colunas_codigo = credbase_trabalhado.drop(columns=['Codigo_Credbase'])

            # Resetar os índices de ambos antes do concat
            nova_planilha_codigo.reset_index(drop=True, inplace=True)
            outras_colunas_codigo.reset_index(drop=True, inplace=True)

            # cred = cred.drop('Esteira', axis=1)
            credbase_trabalhado = pd.concat([nova_planilha_codigo, outras_colunas_codigo.reindex(nova_planilha_codigo.index)], axis=1)

            # Adiciona Integrado e Não Integrado na coluna esteira do Credbase
            credbase_trabalhado['Esteira'] = nova_coluna_esteira

            # Adiciona as matriculas na coluna de matricula
            credbase_trabalhado['Matricula'] = nova_coluna_matricula

            # Junta os clientes do Função junto a coluna de clientes do Credbase
            credbase_trabalhado['Cliente'] = nova_coluna_cliente

            # Junta os CPFs do Função junto a coluna de CPFs do Credbase
            credbase_trabalhado['CPF'] = nova_coluna_cpf

            # Adiciona o convenio devido na coluna Convenio
            credbase_trabalhado['Convenio'] = nova_coluna_convenio

            # Adiciona os bancos junto do cred
            credbase_trabalhado['Banco'] = nova_coluna_banco

            # Junta a coluna de VLR_PARC do função junto à coluna Parcela do Credbase
            credbase_trabalhado['Parcela'] = nova_coluna_parcela

            credbase_trabalhado['Tabela'] = nova_coluna_tabela

            credbase_trabalhado['Valor a lançar'] = nova_coluna_valor_lancar
            # print(credbase_trabalhado['Valor a lançar'].dtype)

            # Junta a coluna de PRODUTO do função junto à coluna Tipo do Credbase
            credbase_trabalhado['Tipo'] = nova_coluna_produto

            # Junta a coluna DataBase do função junto à coluna Inicio do Credbase
            credbase_trabalhado['Inicio'] = nova_coluna_inicio

            # Junta a coluna PARC do função junto à coluna Prazo do Credbase
            credbase_trabalhado['Prazo'] = nova_coluna_prazo

        # ==============================================================================================================

        credbase_trabalhado['Codigo_Credbase'] = credbase_trabalhado['Codigo_Credbase'].astype(str)
        credbase_trabalhado = credbase_trabalhado.drop_duplicates(subset=['Codigo_Credbase'], keep='first')
        # tirar novamente os contratos com prazo
        credbase_trabalhado['PRAZO'] = self.substituir_modalidade(andam_file, credbase_trabalhado)

        # Verifica se contém prazo
        # preenche espaços vazios na coluna Andamento
        status_andamento = credbase_trabalhado['PRAZO'].fillna('')
        cond_prazo = (status_andamento != '') & (status_andamento != 1) & (status_andamento != 0)

        # Pega de novo a maldita conciliação

        conciliacao_tratado = self.trata_conciliacao()
        conciliacao_tratado['CONTRATOS'] = conciliacao_tratado['CONTRATOS'].astype(str)

        # Puxar o saldo para o credbase
        credbase_trabalhado.loc[:, 'Saldo'] = credbase_trabalhado['Codigo_Credbase'].map(
            conciliacao_tratado.set_index('CONTRATOS')['Saldo']).to_dict()

        condicao_saldo = credbase_trabalhado['Saldo'].fillna(-1.0).round(2) >= 0

        # Aplica a condição: se qualquer uma for verdadeira, OBS = 'NÃO'; caso contrário, OBS = ''
        credbase_trabalhado.loc[(credbase_trabalhado['OBS'].fillna('') == '') & (condicao_saldo | cond_prazo), 'OBS'] = 'NÃO'

        # Pega de novo a maldita liminar
        if self.tutela is not None:

            # Padroniza banco no credbase
            credbase_trabalhado['BANCO_PAD'] = credbase_trabalhado['Banco'].apply(normalizar_banco_credbase)
            credbase_trabalhado['CHAVE'] = credbase_trabalhado['CPF'].astype(str) + "_" + credbase_trabalhado[
                'BANCO_PAD'].astype(str)

            # Verifica se a chave está em liminares

            mask_liminar = credbase_trabalhado['CHAVE'].isin(liminares['CHAVE'])

            # Marca OBS = NÃO onde a chave bateu
            credbase_trabalhado.loc[mask_liminar, 'OBS'] = 'NÃO'

        # print(df_refin)

        # Tira os NÃO do credbase trabalhado DE NOVO... PRAGA
        credbase_trabalhado = credbase_trabalhado[credbase_trabalhado['OBS'] != "NÃO"]


        # ==================================== ADICIONA PECULIOS NO FUNÇÃO =============================================
        df_hp = self.averbados[self.averbados['Login'].isin(['HOJE', 'HOJEPREV'])]
        df_averb = self.averbados

        contse_geral = df_averb.groupby("CPF")["CPF"].count().to_dict()
        contse_hp = df_hp.groupby("CPF")["CPF"].count().to_dict()
        credbase_trabalhado['Contse Averb Geral'] = credbase_trabalhado['CPF'].map(contse_geral)
        credbase_trabalhado['Contse Averb HP'] = credbase_trabalhado['CPF'].map(contse_hp)

        credbase_trabalhado.loc[
            (credbase_trabalhado['Codigo_Credbase'].str.len() > 6) &
            (credbase_trabalhado['Contse Averb Geral'] == credbase_trabalhado['Contse Averb HP']),
            'Valor a lançar'
        ] += 20


        # ==============================================================================================================

        # ================================= ADICIONA PECULIOS NOS CONTRATOS CREDBASE ===================================
        mask = (credbase_trabalhado['Codigo_Credbase'].str.len() <= 6) & \
               (credbase_trabalhado['Banco'] == 'BANCO HP')

        credbase_trabalhado.loc[mask, 'Valor a lançar'] += 20
        # ==============================================================================================================

        # Transforma em xlsx
        credbase_trabalhado.to_excel(fr'{self.caminho}\CREDBASE TRABALHADO {self.convenio} AUTOMATIZADO {str(datetime.now().month).zfill(2)}{datetime.now().year}.xlsx', index=False)
        # print(len(credbase_trabalhado))

            # print(df_refin)


        # refin()
        # self.averbados_func(credbase_trabalhado)

        return credbase_trabalhado


    def averbados_func(self, cred):
        # Contse do Credbase no relatório de averbados
        credbase = self.credbase_trabalhado_func(cred)
        averbados = self.averbados

        if self.convenio in ['PREF. CAMPINA GRANDE', 'PREF. RECIFE']:
            averbados = averbados[averbados['Modalidade'].isin(['Cartão de Crédito', 'Cartão Benefício (Compras)', 'Cartão Benefício'])]
        else:
            averbados = averbados[averbados['Modalidade'] == 'Cartão de Crédito']

        # Realoca a coluna "Login" para o início da planilha
        if averbados.columns[0] != 'Login':
            # 1. Cria a nova ordem: a coluna 'Login' + todas as outras colunas que não são 'Login'
            nova_ordem = ['Login'] + [col for col in averbados.columns if col != 'Login']

            # 2. Reorganiza o DataFrame com a nova lista
            averbados = averbados[nova_ordem]

        # Remover de Averbados algumas colunas
        colunas_para_remover = ['Validade', 'Saldo de reserva', 'Data', 'IP', 'Código', '%']

        averbados = averbados.drop(columns=colunas_para_remover, errors='ignore')

        # Adicionar outras colunas em Averbados
        # averbados.insert(5, 'CONCAT', '', True)
        averbados['VALOR A LANÇAR'] = ''
        averbados['CONTSE'] = ''
        averbados['CONTSE SEQ'] = ''
        averbados['SOMASE CRED'] = ''
        # averbados['VALOR ATRIBUIDO'] = ''
        # averbados['FALTA ATRIBUIR'] = ''
        # averbados['DIFF'] = ''
        averbados['OBS'] = ''

        # Tira valor vazio do Valor da Reserva
        mask_nao = (averbados['Valor da reserva'] == 0) | (averbados['Valor da reserva'].isna())
        averbados.loc[mask_nao, 'OBS'] = 'NÃO'

        # Separa o que não é NÃO em outra planilha
        # averbado_novo = averbados[averbados['OBS'] != 'NÃO'].copy()
        averbado_novo = averbados.copy()

        # CONTSE
        averbado_novo['CONTSE'] = averbado_novo.groupby('CPF')['CPF'].transform('count')

        # CONTSE SEQ
        averbado_novo['CONTSE SEQ'] = averbado_novo.groupby('CPF').cumcount() + 1

        # Se for PREF. BAYEUX adiciona mais 20 reais para cada contrato
        '''if self.convenio in ['PREF. BAYEUX', 'PREF. PAÇO DO LUMIAR']:
            for idx, row in credbase.iterrows():
                credbase.loc[idx, 'Valor a lançar'] = credbase.loc[idx, 'Valor a lançar'] + 20
        elif self.convenio == 'GOV. MA':
            credbase.loc[credbase['Banco'] == 'BANCO HP', 'Valor a lançar'] += 20'''

        # SOMASE
        soma_condicional_dict_averb = credbase.groupby('CPF')['Valor a lançar'].sum().to_dict()
        averbado_novo['SOMASE CRED'] = averbado_novo['CPF'].map(soma_condicional_dict_averb)
        # print(type(averbado_novo.loc[0, 'SOMASE']))
        averbado_novo['SOMASE CRED'] = averbado_novo['SOMASE CRED'].fillna(0)


        # =============================================================================
        #        INÍCIO DA NOVA LÓGICA VETORIZADA (SUBSTITUI O SEU LOOP 'FOR')
        # =============================================================================

        # IMPORTANTE: Garanta que as colunas de valores são numéricas, não texto.
        # O .to_numeric(errors='coerce') converte o que for possível para número e põe NaN no que não for.
        averbado_novo['Valor da reserva'] = pd.to_numeric(averbado_novo['Valor da reserva'], errors='coerce').fillna(0)
        averbado_novo['SOMASE CRED'] = pd.to_numeric(averbado_novo['SOMASE CRED'], errors='coerce').fillna(0)

        # NOTA: Como não há coluna de prioridade, a ordem de distribuição dependerá
        # da ordem atual do DataFrame. Se precisar de uma ordem específica,
        # um .sort_values() viria aqui.

        # 1. Calcula a soma ACUMULADA da reserva dentro de cada grupo de CPF.
        # Esta é a "mágica" que substitui a necessidade de um loop.
        averbado_novo['SOMA ACUMULADA DA RESERVA'] = averbado_novo.groupby('CPF')['Valor da reserva'].cumsum()

        # 2. Calcula o valor que JÁ FOI ALOCADO para as linhas ANTERIORES.
        # É a soma acumulada até a linha atual, menos o valor da própria linha.
        alocado_anteriormente = averbado_novo['SOMA ACUMULADA DA RESERVA'] - averbado_novo['Valor da reserva']

        # 3. Calcula o saldo restante do SOMASE ANTES de processar a linha atual.
        saldo_restante = averbado_novo['SOMASE CRED'] - alocado_anteriormente

        # 4. O valor a lançar é o MÍNIMO entre o que a reserva da linha pede e o saldo que ainda temos.
        # Usamos .clip(0) para garantir que o saldo não seja negativo (se já estourou, é 0).
        valor_a_lancar = np.minimum(averbado_novo['Valor da reserva'], saldo_restante.clip(0))

        # 5. Atribui o resultado final arredondado às colunas.
        averbado_novo['VALOR A LANÇAR'] = valor_a_lancar.round(2)
        # averbado_novo['VALOR ATRIBUIDO'] = valor_a_lancar.round(2)

        # 6. Preenche a coluna OBS para linhas que não receberam nada.
        averbado_novo.loc[averbado_novo['VALOR A LANÇAR'] == 0, 'OBS'] = 'NÃO'

        # 7. (Opcional) Remove a coluna auxiliar que criamos.
        # averbado_novo = averbado_novo.drop(columns=['SOMA ACUMULADA DA RESERVA'])

        averbado_novo.to_excel(fr'{self.caminho}\TRABALHADO AVERBADO {self.convenio} AUTOMATIZADO {str(datetime.now().month).zfill(2)}{datetime.now().year}.xlsx', index=False)
