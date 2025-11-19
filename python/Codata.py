import pandas as pd
import xlrd
import openpyxl
from datetime import datetime
import numpy as np
import tabula

rejeitados = ['/']

class CODATA:
# Dentro de python/Codata.py

    def __init__(self, portal_file_list, convenio, credbase, funcao, consignataria, conciliacao, liquidados, andamento_list, caminho, tutela=None, orbital=None):

        # A API FastAPI já leu, unificou e tratou a codificação. 
        # Aqui, apenas atribuímos o DataFrame ou inicializamos como vazio se for None.
        
        # Averbados (portal_file_list)
        self.averbados = portal_file_list if portal_file_list is not None else pd.DataFrame()

        # Credbase
        self.creds_unficados = credbase if credbase is not None else pd.DataFrame()

        # Andamento
        self.andamento = andamento_list if andamento_list is not None else pd.DataFrame()

        self.convenio = convenio
        self.consignataria = consignataria

        # Função (funcao_bruto) - CORREÇÃO: Trata None para evitar pd.read_csv(None, ...)
        self.funcao_bruto = funcao if funcao is not None else pd.DataFrame()

        # Conciliação - CORREÇÃO: Trata None para evitar pd.read_excel(None, ...)
        self.conciliacao = conciliacao if conciliacao is not None else pd.DataFrame()

        # Liquidados - CORREÇÃO: Trata None para evitar pd.read_excel(None, ...)
        self.liquidados_file = liquidados if liquidados is not None else pd.DataFrame()

        # Lógica de validação do arquivo liquidados
        if not self.liquidados_file.empty:
            # Certificando que o tipo dos contratos do Operações Liquidadas
            if 'Nº OPERAÇÃO' in self.liquidados_file.columns:
                self.liquidados_file['Nº OPERAÇÃO'] = self.liquidados_file['Nº OPERAÇÃO'].astype(str)
        
        # Tutela (Liminar) - CORREÇÃO: Trata None para evitar pd.read_excel(None, ...)
        self.tutela = tutela if tutela is not None else pd.DataFrame()
        self.caminho = caminho

        # Orbitall - CORREÇÃO: Trata None para evitar pd.read_excel(None, ...)
        self.orbital = orbital if orbital is not None else pd.DataFrame()
        
        # Chama a primeira função da cadeia de processamento
        self.tratamento_funcao()

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
        funcao.insert(5, 'CONTSE SEMI TRABALHADO', '', True)
        if 'CONTSE LOCAL' not in funcao.columns:
            funcao.insert(6, 'CONTSE LOCAL', '', True)
        if 'CONTSE SEQ' not in funcao.columns:
            funcao.insert(7, 'CONTSE SEQ', '', True)
        funcao.insert(8, 'Diff', '', True)
        funcao.insert(9, 'OP_LIQ', '', True)
        funcao.insert(10, 'CONTRATO CONCILIACAO', '', True)
        funcao.insert(11, 'STATUS CONCILIACAO', '', True)
        funcao.insert(12, 'Saldo', '', True)
        if 'OBS' not in funcao.columns:
            funcao.insert(13, 'OBS', '', True)

        # Concat de CPF + PARCELA
        funcao['VLR_PARC'] = funcao['VLR_PARC'].str.replace('.', '', regex=False)
        funcao['VLR_PARC'] = funcao['VLR_PARC'].str.replace(',', '.', regex=False)
        funcao['VLR_PARC'] = pd.to_numeric(funcao['VLR_PARC'], errors='coerce').fillna(0)

        # Esta linha agora é a ÚNICA que cria a coluna 'CONCAT', o que é o correto.
        funcao['CONCAT'] = funcao['CPF'].astype(str) + funcao['VLR_PARC'].astype(str)

        # Criação do Credbase Semi Trabalhado
        condicoes_1 = ['11 FORMALIZAÇÃO ', '07.0 QUITAÇÃO - LIBERAÇÃO TROCO', '07.4 ENVIA CESSÃO FUNDO',
                       '11.2  DETERMINAÇÃO JUDICIAL', '10.7.0 INGRESSAR COM PROCESSO OU AÇÃO JURIDICO',
                       '10.7.1 ACORDO EM ANDAMENTO', '02.03 AGUARDANDO PROCESSAMENTO CARTÃO',
                       '02.3 AGUARDANDO PROCESSAMENTO DE CARTÃO',
                       '07.0 QUITACAO – ENVIO DE CESSAO', '07.1 – QUITACAO – PAGAMENTO AO CLIENTE',
                       '07.1.1 QUITACAO - CORRECAO DE CCB', '07.2 TED DEVOLVIDA – PAGAMENTO AO CLIENTE',
                       '10.3.1 CONTRATO AVERBADO AGUARDANDO LIQUIDAÇÃO REFIN',
                       '08.0 LIBERAÇÃO TROCO', '09.0 PAGO', '09.1 - APOSENTADORIA IGEPREV - AVERB. TOTAL',
                       '09.2 - APOSENTADORIA IGEPREV - AVERB. PARCIAL', '07.1 \x96 QUITACAO \x96 PAGAMENTO AO CLIENTE',
                       '10.3.1 CONTRATO AVERBADO AGUARDANDO LIQUIDAÇÃO REFIN',
                       '07.2 TED DEVOLVIDA \x96 PAGAMENTO AO CLIENTE',
                       '10.5 AGUARDANDO AVERBACAO COMPRA OUTROS CONVENIOS', '07.0 QUITACAO \x96 ENVIO DE CESSAO',
                       '10.6 CONTRATO AVERBADO - AGUARDANDO COMPROVANTE DE RESERVA',
                       '02.03 AGUARDANDO PROCESSAMENTO CARTÃO', 'INTEGRADO', 'RISCO DA OPERAÇÃO - ÓBITO',
                       'RISCO DA OPERAÇÂO-DEMAIS SITUAÇÕES',
                       '10.7 CONTRATO NÃO AVERBADO - AGUARDANDO RESOLUÇÃO', '11.1 CONTRATO FÍSICO ENVIADO AO BANCO ',
                       '11.PROBLEMAS DE AVERBAÇÃO', '15.0\tRISCO DA OPERAÇÂO-DEMAIS SITUAÇÕES',
                       '15.0	RISCO DA OPERAÇÂO-DEMAIS SITUAÇÕES', '14.0 RISCO DA OPERAÇÃO - ÓBITO',
                       '07.4 ENVIA CESSAO FUNDO', '08.0 LIBERACAO TROCO', '07.1 AGUARDANDO AVERBACAO',
                       '11.PROBLEMAS DE AVERBACAO', '07.2 AGUARDANDO DESAVERBACAO IF',
                       '07.5 AGUARDANDO DESAVERBACAO BENEFICIO', '10.7.0 INGRESSAR COM PROCESSO OU AÇÃO JURIDICO',
                       '10.3 AGUARDANDO AVERBACAO COMPRA EMPRESTIMO SIAPE', 'FISICOS PARAIBA', 'OPERAÇÃO TEMPORARIAMENTE SUSPENSA']

        if self.consignataria == 'CAPITAL':
            consig_list = ['BANCO CAPITAL', 'BANCO CAPITAL S.A.', 'BANCO CAPITAL S.A. ', 'CB/CAPITAL', 'CB/CAPITAL	',
                           'CC BANCO CAPITAL S.A. ', 'Banco CB DIGITAL', 'CB/CAPITAL	', 'CAPITAL', 'CAPITAL*']
        else:
            consig_list = ['INSPFEM - CARD', 'INSPFEM']

        # Garante que a coluna 'Esteira' exista antes de filtrar
        cred_unificado = self.unificacao_creds()
        if 'Esteira' in cred_unificado.columns:
            cred_semi = cred_unificado[cred_unificado['Esteira'].isin(condicoes_1)].copy()

            cred_semi = cred_semi[cred_semi['Banco'].isin(consig_list)]

            # Cria a coluna CONCAT CPF PARC apenas se cred_semi não for vazio
            if not cred_semi.empty:
                concat_cpf_parc = cred_semi['CPF'].astype(str) + cred_semi['Parcela'].astype(str)
                cred_semi.insert(13, 'CONCAT CPF PARC', concat_cpf_parc, True)

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

        except Exception as e:
            op_liq = pd.DataFrame(columns=['Nº OPERAÇÃO'])
            print(f"Planilha de Operações Liquidadas está vazia {e}")

        funcao['OP_LIQ'] = funcao['OP_LIQ'].fillna('')

        for idx, row in funcao.iterrows():
            if funcao.loc[idx, 'CONTSE LOCAL'] > funcao.loc[idx, 'CONTSE SEMI TRABALHADO']:
                funcao.loc[idx, 'Diff'] = 'VERDADEIRO'
            else:
                funcao.loc[idx, 'Diff'] = 'FALSO'

        # Condição 1: Coluna 'Diff' contém 'FALSO'
        mask_diff = funcao['Diff'].str.contains('FALSO', na=False)

        # Condição 2: Coluna 'PRODUTO' contém 'EMPRESTIMO' ou 'BENS DURAVEIS'
        if self.consignataria == "CAPITAL":
            # segue sua lógica original para CAPITAL
            mask_produto = (
                    funcao['PRODUTO'].str.contains('EMPRESTIMO', na=False)
                    | funcao['PRODUTO'].str.contains('BENS DURAVEIS', na=False)
                    | funcao['PRODUTO'].str.contains('EMPR COMPRA DIVIDA', na=False)
                    | funcao['PRODUTO'].str.contains('CARTÃO PLÁSTICO', na=False)
                    | funcao['PRODUTO'].str.contains('CARTAO BENEFICIO', na=False)
            )
            mask_origem_4 = (funcao['ORIGEM_4'].str.contains('INSPFEM', na=False))

            # Máscara final
            mask_final = mask_diff | mask_produto | mask_origem_4

        else:
            # NÃO é CAPITAL
            # Sempre "NÃO" se for CARTÃO PLÁSTICO
            print(funcao['PRODUTO'].unique())

            mask_cartao_plastico = funcao['PRODUTO'].str.contains('CARTÃ\x83O PLÃ\x81STICO', na=False)

            # "NÃO" se não for CARTÃO BENEFÍCIO nem ADIANTAMENTO SALARIAL,
            # mas somente quando também não for GOV PB INSPFEM
            mask_produto = (
                    ~funcao['PRODUTO'].str.contains('CARTAO BENEFICIO', na=False)
                    & ~funcao['PRODUTO'].str.contains('ADIANTAMENTO SALARIAL', na=False)
                    & ~funcao['ORIGEM_4'].str.contains('GOV PB INSPFEM', na=False, case=False)
            )

            # Máscara final = casos que devem receber "NÃO"
            mask_final = mask_diff | mask_cartao_plastico | mask_produto

        # print(funcao['OBS'][funcao['OBS'] == "NÃO"])

        # CONCILIAÇÃO
        conciliacao_tratado = self.trata_conciliacao()

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

        condicao_saldo = funcao['Saldo'].fillna(float(-1.0)) >= 0.01

        # Aplica a condição: se qualquer uma for verdadeira, OBS = 'NÃO'; caso contrário, OBS = ''
        funcao['OBS'] = np.where(condicao_saldo, 'NÃO', '')

        funcao.loc[(funcao['OBS'] == '') & (funcao['OP_LIQ'] != ''), 'OBS'] = 'NÃO'

        # SALDO POSITIVO
        mask_positivo = funcao['Saldo'] >= 0
        funcao.loc[mask_positivo, 'OBS'] = "NÃO"
        # Agora, aplique o 'NÃO' nos locais corretos usando a máscara
        funcao.loc[mask_final, 'OBS'] = 'NÃO'

        # Verifica se CONTSE LOCAL é igual á CONTSE SEMI CRED e se existe na concilicação
        for idx, row in funcao.iterrows():
            if (
                    row['CONTSE LOCAL'] == row['CONTSE SEMI TRABALHADO']
                    and row['CONTRATO CONCILIACAO'] != ''
                    and "EMPRESTIMO" not in str(row['PRODUTO']) and "BENS DURAVEIS" not in str(row['PRODUTO'])
                    and "EMPR COMPRA DIVIDA" not in str(row['PRODUTO']) and "CARTÃ\x83O PLÃ\x81STICO" not in str(
                row['PRODUTO'])
            ):
                funcao.loc[idx, 'OBS'] = ''

        # FUNÇÃO INTERMEDIARIO
        funcao.to_excel(fr'{self.caminho}\FUNÇÃO INTERMEDIÁRIO.xlsx', index=False)

        # FUNÇÃO SEM O QUE É NÃO
        funcao_tratado = funcao[funcao['OBS'] == ''].copy()

        funcao_tratado['CONTSE SEQ'] = funcao_tratado.groupby('CONCAT').cumcount() + 1

        # Decidir se é espelho se o contse for menor oul igual ao contse local menos o contse semi
        # exemplo com seu dataframe (supondo que já está carregado como df)
        def classificar_obs(row):
            if row['CONTSE SEMI TRABALHADO'] == 0:
                return "SIM"
            elif row['CONTSE SEMI TRABALHADO'] > row['CONTSE LOCAL']:
                return "NÃO - ESPELHO"
            elif row['CONTSE SEQ'] <= (row['CONTSE LOCAL'] - row['CONTSE SEMI TRABALHADO']):
                return "SIM"
            elif row['CONTRATO CONCILIACAO'] != "":
                return "SIM"
            else:
                return "NÃO - ESPELHO"

        funcao_tratado['OBS'] = funcao_tratado.apply(classificar_obs, axis=1)

        funcao_tratado.to_excel(fr'{self.caminho}\FUNCAO COM NÃO.xlsx', index=False)

        self.unificacao_cred_funcao(cred_semi, funcao_tratado)

    def unificacao_creds(self):

        # RENOMEIA A COLUNA CODIGO_CREDBASE
        if 'Codigo Credbase' in self.creds_unficados.columns:
            cred = self.creds_unficados.rename(columns={'Codigo Credbase': 'Codigo_Credbase'})
            self.creds_unficados = cred

        credbase_reduzido = self.creds_unficados[['Codigo_Credbase', 'Banco(s) quitado(s)', 'Filial', 'Esteira',
                                                 'Esteira(dias)', 'Tipo', 'Operacao', 'Situacao', 'Inicio', 'Cliente',
                                                 'Data Averbacao', 'CPF', 'Convenio', 'Banco', 'Parcela', 'Prazo',
                                                 'Tabela', 'Matricula']]

        # Vamos alterar o tipo do Codigo_Credbase já que agora a coluna está com o nome certo
        credbase_reduzido['Codigo_Credbase'] = credbase_reduzido['Codigo_Credbase'].astype(str)

        credbase_reduzido['Parcela'] = credbase_reduzido['Parcela'].str.replace('.', '')
        credbase_reduzido['Parcela'] = credbase_reduzido['Parcela'].str.replace(',', '.')
        credbase_reduzido['Parcela'] = pd.to_numeric(credbase_reduzido['Parcela'], errors='coerce')

        credbase_reduzido.to_excel(fr'{self.caminho}\CREDBASE UNIFICADO.xlsx', index=False)

        # print(self.creds_unficados)

        return credbase_reduzido



    def unificacao_cred_funcao(self, cred, func):
        funcao = func[func['OBS'] == 'SIM'].copy()

        # Cria a coluna NR_OPER_EDITADO
        # Remove tudo que não for número
        funcao['VLR_PARC'] = pd.to_numeric(funcao['VLR_PARC'], errors='coerce')


        # Transforma a coluna de NR_OPER_EDITADO EM NúMERO
        # funcao['NR_OPER_EDITADO'] = funcao['NR_OPER_EDITADO'].astype(int)


        # Cria a coluna Esteira no Função
        funcao.insert(4, 'Esteira', '', True)
        funcao['Esteira'] = 'INTEGRADO'

        funcao.to_excel(fr'{self.caminho}\Funcao tratado.xlsx', index=False)

        # Certificar-se de que as colunas 'Código' e 'NR_OPER' estão presentes
        if 'Codigo_Credbase' in cred.columns and 'NR_OPER_EDITADO' in funcao.columns:
            # Empilhar os valores da coluna 'NR_OPER' abaixo dos valores da coluna 'Código'
            nova_coluna_codigo = cred['Codigo_Credbase'].tolist() + funcao['NR_OPER_EDITADO'].tolist()
            nova_coluna_matricula = cred['Matricula'].tolist() + funcao['MATRICULA'].tolist()
            nova_coluna_esteira = cred['Esteira'].tolist() + funcao['Esteira'].tolist()
            nova_coluna_inicio = cred['Inicio'].tolist() + funcao['DT_BASE'].tolist()
            nova_coluna_cliente = cred['Cliente'].tolist() + funcao['CLIENTE'].tolist()
            nova_coluna_cpf = cred['CPF'].tolist() + funcao['CPF'].tolist()
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

            # Junta a coluna de VLR_PARC do função junto à coluna Parcela do Credbase
            cred['Parcela'] = nova_coluna_parcela

            # Junta a coluna de PRODUTO do função junto à coluna Tipo do Credbase
            cred['Tipo'] = nova_coluna_produto

            # Preenche o restante dos bancos com a consignataria selecionada
            cred['Banco'] = cred['Banco'].fillna(self.consignataria)

            # Junta a coluna DataBase do função junto à coluna Inicio do Credbase
            cred['Inicio'] = nova_coluna_inicio

            # Junta a coluna PARC do função junto à coluna Prazo do Credbase
            cred['Prazo'] = nova_coluna_prazo

        cred['Tabela'] = cred['Tabela'].fillna('CARTÃO')

        credbase_reduzido = cred[['Codigo_Credbase', 'Banco(s) quitado(s)', 'Filial', 'Esteira', 'Esteira(dias)', 'Tipo',
                                 'Operacao', 'Situacao', 'Inicio', 'Cliente', 'Data Averbacao', 'CPF', 'Convenio', 'Banco',
                                 'Parcela', 'Prazo', 'Tabela', 'Matricula']]

        credbase_reduzido.to_excel(rf'{self.caminho}\Teste Credbase Reduzido.xlsx', index=False)

        self.validacao_termino(credbase_reduzido, funcao)

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


        if self.consignataria != 'CAPITAL':
            self.credbase_trabalhado_func(cred_copy)
        else:
            self.andamento_func(cred_copy, funcao)

    def andamento_func(self, cred, func):
        # Andamento
        funcao = func.copy()
        # Primeiro, criamos um dicionário de correspondência
        # modalidade_dict = andam_file.set_index('Código na instituição')['Modalidade'].to_dict()
        # prazo_dict = andam_file.set_index('Código na instituição')['Prazo Total'].to_dict()

        andam_file = self.trata_cod_and(self.andamento)
        andam_file.to_excel(rf'{self.caminho}\ANDAMENTO_TESTE.xlsx', index=False)

        # Função para decidir o valor da nova modalidade
        def substituir_modalidade():
            # 1. Identifica todas as colunas com 'Contrato' no nome
            colunas_contratos = [col for col in andam_file.columns if 'Contrato' in col]

            # 2. Cria uma coluna 'Prazo' vazia no Credbase
            cred['PRAZO'] = None

            # 3. Cria um dicionário auxiliar: contrato → prazo
            contrato_para_prazo = {}

            '''andam_file['Valor da Parcela'] = andam_file['Valor da Parcela'].str.replace(".", '')
            andam_file['Valor da Parcela'] = andam_file['Valor da Parcela'].str.replace(",", '.')'''
            andam_file['Valor da Parcela'] = pd.to_numeric(andam_file['Valor da Parcela'], errors='coerce')
            # print(f'Modalidade e Parcela do Código 407337: {andam_file.loc[andam_file['Código'] == 407337, ['Modalidade', 'Valor da Parcela']]}')

            # Para cada linha no arquivo de andamentos, verifica todas as colunas de contrato
            for _, row in andam_file.iterrows():
                prazo = row.get('Prazo')  # Pode ser 'Prazo Total' dependendo do nome
                for col in colunas_contratos:
                    contrato = row.get(col)
                    if pd.notna(contrato):
                        contrato_para_prazo[str(contrato).strip()] = prazo

            # 4. Aplica a busca no Credbase
            return cred['Codigo_Credbase'].astype(str).str.strip().map(contrato_para_prazo)

        # Aplica a função ao DataFrame cred
        cred['PRAZO'] = substituir_modalidade()

        # preenche espaços vazios na coluna Andamento
        status_andamento = cred['PRAZO'].fillna('')

        # Tipo Amortização
        amort = cred['Banco(s) quitado(s)'].fillna('')

        '''print(f'Bancos quitados: {cred['Banco(s) quitado(s)'][cred['Codigo_Credbase'] == '480596']}')
        print(f'Prazo: {cred['PRAZO'][cred['Codigo_Credbase'] == '480596']}')'''

        # Verifica se contém prazo
        cond_prazo = (
                (status_andamento != '')
                & (status_andamento != '1')
                & (status_andamento != '0')
                & (status_andamento != 1)
                & (status_andamento != 0)
                & (~amort.str.contains('AMORT', na=False))
        )

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

        self.credbase_trabalhado_func(cred)

    def trata_cod_and(self, andamentos):
        # PUXA OS ARQUIVOS À SEREM TRATADOS
        data_averbados = andamentos

        # SUBSTITUIMOS CARACTER POR NADA
        contrato_editado = data_averbados['Contrato'].astype(str).apply(
            lambda x: ''.join(char for char in x if char.isdigit() or char in rejeitados))

        contrato_editado = contrato_editado.replace('//', '/', regex=True)

        # INSERE A COLUNA CONTRATO EDITADO COM OS NÚMEROS JÁ TRATADOS
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
                    'Int64')'''  # Int64 permite nulos

            # Descobre a posição da coluna 'Contrato'
            col_index = data_averbados.columns.get_loc('Contrato Editado')

            # Divide o DataFrame original em duas partes
            antes = data_averbados.iloc[:, :col_index + 1]  # Inclui 'Contrato'
            depois = data_averbados.iloc[:, col_index + 1:]

            # Concatena com os novos dados no meio
            data_averbados = pd.concat([antes, df_contratos_separados, depois], axis=1)

        return data_averbados

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

    def trata_conciliacao(self):
        conciliacao_tratado = self.conciliacao
        # Converte para lista de colunas
        cols = list(conciliacao_tratado.columns)

        # Encontra o índice da primeira ocorrência de "CONTRATO" e altera
        for i, c in enumerate(cols):
            if c == "CONTRATO" and c != "CONTRATOS":
                cols[i] = "CONTRATOS"  # só a primeira vez
                break
            else:
                break

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

    # FUNÇÃO QUE SUBSTITUI CARACTER
    def replace_characters(self, file, coluna, localizar, substituir):
        column = file[coluna].replace(localizar, substituir, regex=True)
        return column

    def substituir_virgula_por_ponto(self, valor):
        return valor.replace('.', ',')

    def credbase_trabalhado_func(self, cred):
        # Trata o credbase
        conciliacao_tratado = self.trata_conciliacao()

        creds_unificados = cred.copy()

        condicoes_1 = ['11 FORMALIZAÇÃO ', '07.0 QUITAÇÃO - LIBERAÇÃO TROCO', '07.4 ENVIA CESSÃO FUNDO',
                       '11.2  DETERMINAÇÃO JUDICIAL', '10.7.0 INGRESSAR COM PROCESSO OU AÇÃO JURIDICO',
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
                       '10.3 AGUARDANDO AVERBACAO COMPRA EMPRESTIMO SIAPE', 'FISICOS PARAIBA', 'OPERAÇÃO TEMPORARIAMENTE SUSPENSA']

        cred_esteira = cred[cred['Esteira'].isin(condicoes_1)]
        semi_cred = creds_unificados[creds_unificados['Esteira'].isin(condicoes_1)].copy()

        if self.consignataria == 'CAPITAL':
            consig_list = ['BANCO CAPITAL', 'BANCO CAPITAL S.A.', 'BANCO CAPITAL S.A. ', 'CB/CAPITAL', 'CB/CAPITAL	',
                           'CC BANCO CAPITAL S.A. ', 'Banco CB DIGITAL', 'CB/CAPITAL	', 'CAPITAL', 'CAPITAL*']
        else:
            consig_list = ['INSPFEM - CARD', 'INSPFEM']

        semi_cred = semi_cred[semi_cred['Banco'].isin(consig_list)]

        if self.consignataria != 'INSPFEM':
            # Separa as tabelas de lançamento
            condicoes_2 = cred_esteira['Tabela'].str.contains('CART')
            cred_tab_cart = cred_esteira[condicoes_2]

            # Condições especiais
            cart = 'CART'
            ben = 'BEN'

            # Seleciona Tipo Cartão
            condicoes_3 = ['Cartão de crédito']
            cred_tipo = cred_esteira[cred_esteira['Tipo'].isin(condicoes_3)]
            # Tira tabela Cartão
            condicoes_4 = ~cred_tipo['Tabela'].str.contains(f'{cart}|{ben}')
            cred_tipo = cred_tipo[condicoes_4]

            # Tira tipo Cartão
            cred_amor = cred_esteira[~cred_esteira['Tipo'].isin(condicoes_3)]
            # Tira tabela Cartão
            condicoes_5 = ~cred_amor['Tabela'].str.contains(f'{cart}|{ben}')
            cred_amor = cred_amor[condicoes_5]
            # Verifica Amortização em Bancos quitados depois de tirar tipo e tabela cartão
            condicoes_6 = cred_amor['Banco(s) quitado(s)'].str.contains('AMOR', na=False)
            cred_amor['Banco(s) quitado(s)'] = cred_amor['Banco(s) quitado(s)']
            cred_amor = cred_amor[condicoes_6]
            credbase_trabalhado = pd.concat([cred_tab_cart, cred_tipo, cred_amor], ignore_index=True)

            # Seleciona a consignatária correta
            if self.consignataria == 'CIASPREV':
                consig_list = ['BANCO ACC', 'CIASPREV']
            elif self.consignataria == 'CAPITAL':
                consig_list = ['BANCO CAPITAL', 'BANCO CAPITAL S.A.', 'BANCO CAPITAL S.A. ', 'CB/CAPITAL', 'CB/CAPITAL	',
                               'CC BANCO CAPITAL S.A. ', 'Banco CB DIGITAL', 'CB/CAPITAL	', 'CAPITAL', 'CAPITAL*']
            elif self.consignataria == 'CLICKBANK':
                consig_list = ['CB/CLICK BANK', 'CB/CLICK BANK	', 'Banco CB DIGITAL']
            elif self.consignataria == 'HOJE':
                consig_list = ['BANCO HP']
            credbase_trabalhado = credbase_trabalhado[credbase_trabalhado['Banco'].isin(consig_list)]
        else:
            consig_list = ['INSPFEM - CARD', 'INSPFEM']
            credbase_trabalhado = cred_esteira[cred_esteira['Banco'].isin(consig_list)]

        # Tira ponto e traço do CPF
        cpf = self.replace_characters(credbase_trabalhado, 'CPF', '\D', '')
        credbase_trabalhado.insert(17, 'cpf', cpf, True)
        # Tira o zero à esquerda
        credbase_trabalhado['cpf'] = credbase_trabalhado['cpf'].astype(float)

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



        # Tipo Amortização
        amort = credbase_trabalhado['Banco(s) quitado(s)'].fillna('')

        # preenche espaços vazios na coluna Andamento
        if self.consignataria == "CAPITAL":
            status_prazo = credbase_trabalhado['PRAZO'].fillna('')
            # Verifica se contém prazo
            cond_prazo = (
                    (status_prazo != '')
                    & (status_prazo != 1)
                    & (status_prazo != 0)
                    & (status_prazo != '1')
                    & (status_prazo != '0')
                    & (~amort.str.contains('AMORT', na=False))
            )

            # Aplica a condição: se qualquer uma for verdadeira, OBS = 'NÃO'; caso contrário, OBS = ''
            credbase_trabalhado['OBS'] = np.where(cond_prazo, 'NÃO', '')

        # ====================================== TUTELA LIMINAR ==================================================

        # Agora tem essa droga de tutela também
        # Dicionário de mapeamento: cada banco "oficial" -> lista de possíveis nomes no credbase
        if self.tutela is not None:
            liminares = self.tutela

            mapa_bancos = {
                "CIASPREV": ['BANCO ACC', 'CIASPREV'],
                "CAPITAL": ['BANCO CAPITAL', 'BANCO CAPITAL S.A.', 'CB/CAPITAL', 'CB/CAPITAL\t',
                            'CC BANCO CAPITAL S.A. ', 'CAPITAL', 'Banco CB DIGITAL', 'QUERO MAIS CRÉDITO',
                            'AKI CAPITAL', 'J.A BANK ', 'J.A BANK', 'CAPITAL*'],
                "CLICKBANK": ['CB/CLICK BANK', 'CB/CLICK BANK\t', 'Banco CB DIGITAL',
                              'QUERO MAIS CRÉDITO', 'CLICK'],
                "HP": ['BANCO HP'],
                "ABCCARD": ['ABCCARD'],
                "BEMCARTOES": ['CB/BEM CARTÕES'],
                "INSPFEM": ['INSPFEM - CARD', 'INSPFEM']
            }

            # Também criaremos um mapeamento para os nomes do arquivo de liminares
            mapa_liminares = {
                "CIASPREV": "CIASPREV - CENTRO DE INTEGRACAO E ASSISTENCIA AOS SERVIDORES PUBLICOS PREVIDENCIA PRIVADA",
                "CAPITAL": "CAPITAL CONSIG SOCIEDADE DE CREDITO DIRETO S.A",
                "CLICKBANK": "CLICKBANK INSTITUICAO DE PAGAMENTOS LTDA",
                "HP": "HOJE PREVIDÊNCIA PRIVADA",
                "BEMCARTOES": "BEMCARTOES BENEFICIOS S.A",
                "INSPFEM": "INSPEFEM"
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

            credbase_trabalhado.drop('BANCO_PAD', axis=1)

            liminares.drop('BANCO_PAD', axis=1)

            # Verifica se a chave está em liminares
            mask_liminar = credbase_trabalhado['CHAVE'].isin(liminares['CHAVE'])

            # Marca OBS = NÃO onde a chave bateu
            credbase_trabalhado.loc[mask_liminar, 'OBS'] = 'NÃO'

        # ==================================== FIM TUTELA LIMINAR ====================================================

        # (f"OBS 16481: {credbase_trabalhado['OBS'][credbase_trabalhado['Codigo_Credbase'] == 16481]}")

        # SALDO POSITIVO
        mask_positivo = credbase_trabalhado['Saldo'] >= 0
        credbase_trabalhado.loc[mask_positivo, 'OBS'] = "NÃO"

        # print(f"OBS 475458: {credbase_trabalhado['Saldo'][credbase_trabalhado['Codigo_Credbase'] == '475458']}")

        credbase_trabalhado.to_excel(fr'{self.caminho}\TESTE CREDBASE TRABALHADO.xlsx', index=False)

        '''print(f'Bancos quitados: {credbase_trabalhado['Banco(s) quitado(s)'][credbase_trabalhado['Codigo_Credbase'] == '480596']}')
        print(f'Prazo: {credbase_trabalhado['PRAZO'][credbase_trabalhado['Codigo_Credbase'] == '480596']}')
        print(f'OBS: {credbase_trabalhado['OBS'][credbase_trabalhado['Codigo_Credbase'] == '480596']}')'''

        # Tira os NÃO do credbase trabalhado
        credbase_trabalhado = credbase_trabalhado[credbase_trabalhado['OBS'] != "NÃO"]

        # Aqui o contrato não aparece

        # =========================================================================================== #
        #                                   REFIN QUE LANÇAREMOS                                      #
        # =========================================================================================== #
        def refin():
            averbados = self.averbados

            '''soma_valores_dict = averbados.groupby('CPF')['Valor da Reserva'].sum().to_dict()
            averbados['SOMASE'] = averbados['CPF'].map(soma_valores_dict)'''
            averbados['CONCAT'] = averbados['CPF'].astype(str) + averbados['Valor da Reserva'].astype(str)

            # averbados = averbados[averbados['Modalidade'] == 'Cartão de Crédito']

            averbados.to_excel(fr'{self.caminho}/averbados_unif.xlsx', index=False)


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

        credbase_trabalhado = credbase_trabalhado.drop_duplicates(subset=['Codigo_Credbase'], keep='first')
        # print(df_refin)

        # Transforma em xlsx
        credbase_trabalhado.to_excel(fr'{self.caminho}\Credbase Trabalhado.xlsx', index=False)
        # print(len(credbase_trabalhado))

        # print(df_refin)

        # refin()
        self.averbados_func(credbase_trabalhado)

    def averbados_func(self, cred):
        # RELATORIO
        credbase = cred.copy()
        averbados = self.averbados
        # Remove a última linha que contém o valor total das parcelas
        averbados = averbados.drop(averbados.index[-1])

        # Insere a coluna Codigo Entidade para o layout ser feito corretamente
        averbados.insert(6, 'Codigo Entidade', '', allow_duplicates=True)
        averbados.loc[averbados['Entidade'] == 'SEAD 1', 'Codigo Entidade'] = '1'
        averbados.loc[averbados['Entidade'] == 'SEAD 2', 'Codigo Entidade'] = '2'
        averbados.loc[averbados['Entidade'] == 'CODATA PB', 'Codigo Entidade'] = '3'
        averbados.loc[averbados['Entidade'] == 'UEPB', 'Codigo Entidade'] = '6'
        averbados.loc[averbados['Entidade'] == 'PBPREV INATIVOS - UEPB', 'Codigo Entidade'] = '11'
        averbados.loc[averbados['Entidade'] == 'PBPREV', 'Codigo Entidade'] = '13'
        averbados.loc[averbados['Entidade'] == 'PBPREV INATIVOS - PBPREV', 'Codigo Entidade'] = '20'
        averbados.loc[averbados['Entidade'] == 'PBPREV INATIVOS - IASS', 'Codigo Entidade'] = '17'
        averbados.loc[averbados['Entidade'] == 'PBPREV INATIVOS - DETRAN', 'Codigo Entidade'] = '18'
        averbados.loc[averbados['Entidade'] == 'PBPREV INATIVOS - DER', 'Codigo Entidade'] = '19'

        # Orbitall
        orbitall = self.orbital

        # Transforma a coluna em averbados mesmo
        # averbados['Data do Cadastro'] = pd.to_datetime(averbados['Data do Cadastro'], dayfirst=True)

        # Deixa apenas os dias sem as horas
        # averbados['Data do Cadastro'] = averbados['Data do Cadastro'].dt.date

        # Deixa a ordem do maior para o menor
        # averbados = averbados.sort_values(by='Valor da Reserva', ascending=False)

        # Tira as duplicatas de CPF e Matrícula deixando apenas as incidências de maior valor
        averbados = averbados.drop_duplicates(subset=['Matrícula', 'Entidade'], keep='first')

        # Adicionar outras colunas em Averbados
        # averbados.insert(5, 'CONCAT', '', True)
        averbados['VALOR A LANÇAR'] = ''
        averbados['CONTSE'] = ''
        averbados['CONTSE SEQ'] = ''
        averbados['SOMASE'] = ''
        # averbados['VALOR ATRIBUIDO'] = ''
        # averbados['FALTA ATRIBUIR'] = ''
        # averbados['DIFF'] = ''
        averbados['OBS'] = ''

        # Tira valor vazio do Valor da Reserva
        mask_nao = (averbados['Valor da Reserva'] == 0) | (averbados['Valor da Reserva'].isna())
        averbados.loc[mask_nao, 'OBS'] = 'NÃO'

        # Separa o que não é NÃO em outra planilha
        # averbado_novo = averbados[averbados['OBS'] != 'NÃO'].copy()
        averbado_novo = averbados.copy()

        # CONTSE
        averbado_novo['CONTSE'] = averbado_novo.groupby('CPF')['CPF'].transform('count')

        # CONTSE SEQ
        averbado_novo['CONTSE SEQ'] = averbado_novo.groupby('CPF').cumcount() + 1

        if self.consignataria == 'CAPITAL':
            soma_condicional_dict_averb = credbase.groupby('CPF')['Valor a lançar'].sum().to_dict()
            averbado_novo['SOMASE'] = averbado_novo['CPF'].map(soma_condicional_dict_averb)
            averbado_novo['SOMASE'] = averbado_novo['SOMASE'].fillna(0)
        else:
            # 1. Soma por CPF no credbase
            somase_credbase = credbase.groupby('CPF')['Valor a lançar'].sum()

            # 2. Contagem de contratos no credbase (para somar 25 por contrato)
            qtd_contratos = credbase.groupby('CPF').size() * 25

            # 3. Soma por CPF no orbital
            somase_orbital = orbitall.groupby('CPF/CNPJ')['Valor da Parcela'].sum()

            # 4. Combina tudo em um único dataframe
            soma_total = (
                somase_credbase.add(qtd_contratos, fill_value=0)
                .add(somase_orbital, fill_value=0)
            )

            # 5. Mapeia no dataframe final
            averbado_novo['SOMASE'] = averbado_novo['CPF'].map(soma_total).fillna(0)

        # =============================================================================
        #        INÍCIO DA NOVA LÓGICA VETORIZADA (SUBSTITUI O SEU LOOP 'FOR')
        # =============================================================================

        # IMPORTANTE: Garanta que as colunas de valores são numéricas, não texto.
        # O .to_numeric(errors='coerce') converte o que for possível para número e põe NaN no que não for.
        averbado_novo['Valor da Reserva'] = pd.to_numeric(averbado_novo['Valor da Reserva'], errors='coerce').fillna(0)
        averbado_novo['SOMASE'] = pd.to_numeric(averbado_novo['SOMASE'], errors='coerce').fillna(0)

        # NOTA: Como não há coluna de prioridade, a ordem de distribuição dependerá
        # da ordem atual do DataFrame. Se precisar de uma ordem específica,
        # um .sort_values() viria aqui.

        # 1. Calcula a soma ACUMULADA da reserva dentro de cada grupo de CPF.
        # Esta é a "mágica" que substitui a necessidade de um loop.
        averbado_novo['SOMA ACUMULADA DA RESERVA'] = averbado_novo.groupby('CPF')['Valor da Reserva'].cumsum()

        # 2. Calcula o valor que JÁ FOI ALOCADO para as linhas ANTERIORES.
        # É a soma acumulada até a linha atual, menos o valor da própria linha.
        alocado_anteriormente = averbado_novo['SOMA ACUMULADA DA RESERVA'] - averbado_novo['Valor da Reserva']

        # 3. Calcula o saldo restante do SOMASE ANTES de processar a linha atual.
        saldo_restante = averbado_novo['SOMASE'] - alocado_anteriormente

        # 4. O valor a lançar é o MÍNIMO entre o que a reserva da linha pede e o saldo que ainda temos.
        # Usamos .clip(0) para garantir que o saldo não seja negativo (se já estourou, é 0).
        valor_a_lancar = np.minimum(averbado_novo['Valor da Reserva'], saldo_restante.clip(0))

        # 5. Atribui o resultado final arredondado às colunas.
        averbado_novo['VALOR A LANÇAR'] = valor_a_lancar.round(2)
        # averbado_novo['VALOR ATRIBUIDO'] = valor_a_lancar.round(2)

        # 6. Preenche a coluna OBS para linhas que não receberam nada.
        averbado_novo.loc[averbado_novo['VALOR A LANÇAR'] == 0, 'OBS'] = 'NÃO'

        # 7. (Opcional) Remove a coluna auxiliar que criamos.
        # averbado_novo = averbado_novo.drop(columns=['SOMA ACUMULADA DA RESERVA'])

        averbado_novo.to_excel(fr'{self.caminho}\TRABALHADO AVERBADO.xlsx', index=False)
        averbado_novo['VALOR A LANÇAR'] = pd.to_numeric(averbado_novo['VALOR A LANÇAR'], errors='coerce')
        averbado_novo['VALOR A LANÇAR'] = averbado_novo['VALOR A LANÇAR'].map('{:.2f}'.format)
        averbado_novo['VALOR A LANÇAR'] = averbado_novo['VALOR A LANÇAR'].astype(str)
        averbado_novo['CPF'] = (averbado_novo['CPF'].astype(str).str.replace(r'\D', '', regex=True))  # remove tudo que não for dígito
        averbado_novo['Matrícula'] = averbado_novo['Matrícula'].astype(str).str.replace(r'\.0$', '', regex=True)
        averbado_novo['Rubrica'] = averbado_novo['Rubrica'].astype(str).str.replace(r'\.0$', '', regex=True)
        averbado_novo['Entidade'] = averbado_novo['Entidade'].astype(str).str.replace(r'\.0$', '', regex=True)

        self.process_entities(averbado_novo, self.caminho)

    def format_column(self, series, length):
        """Formata uma coluna para ter um comprimento fixo, adicionando zeros à esquerda quando necessário."""
        return series.astype(str).apply(lambda x: x.zfill(length) if len(x) < length else x)

    def create_layout(self, df, banco):
        """Cria o layout formatado para o DataFrame fornecido."""
        matricula_formatted = self.format_column(df['Matrícula'], 20)
        cpf_formatted = self.format_column(df['CPF'], 11)
        entidade_formatted = self.format_column(df['Codigo Entidade'], 0)
        rubrica_formatted = self.format_column(df['Rubrica'], 4)
        parcela_formatted = self.format_column(df['VALOR A LANÇAR'], 23)
        prazo_formatted = '1'
        competencia_formatted = f'{str(datetime.now().month).zfill(2)}{datetime.now().year}'

        layout = (matricula_formatted + cpf_formatted + entidade_formatted + rubrica_formatted +
                  parcela_formatted + prazo_formatted + competencia_formatted)


        return layout.str.replace('.', '')

    def save_layout(self, layout, entity_name, output_dir):
        """Salva o layout formatado em um arquivo .txt."""
        file_name = f'LANCAMENTO CARTAO GOV PB {self.consignataria} {entity_name} {str(datetime.now().month).zfill(2)}-{datetime.now().year}.txt'
        file_path = f'{output_dir}/{file_name}'
        layout.to_csv(file_path, index=False, header=False)

    def process_entities(self, arquivo, output_dir):
        """Processa cada entidade no DataFrame, gerando e salvando o layout apropriado."""
        entidades = arquivo['Entidade'].unique().astype(str)
        print(f'Entidades\n{entidades}')

        averbados = arquivo

        for entidade in entidades:
            df_entidade = averbados[averbados['Entidade'].astype(str) == entidade]
            df_entidade = df_entidade[df_entidade['VALOR A LANÇAR'] != '0.00']
            layout = self.create_layout(df_entidade, self.consignataria)

            if len(df_entidade['Entidade'].unique()) > 0:
                entity_name = df_entidade['Entidade'].unique()[0]
                self.save_layout(layout, entity_name, output_dir)
            else:
                # Se estiver vazia, defina um valor padrão ou mostre um erro
                entity_name = None  # ou "Padrão", ou "Não Encontrado"
                print("Aviso: Não foi possível encontrar a 'Entidade' pois o DataFrame está vazio.")

    # print(len(credbase_trabalhado))

