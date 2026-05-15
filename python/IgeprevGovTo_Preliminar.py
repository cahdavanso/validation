import pandas as pd
import zipfile
import io
from io import StringIO
from python.trata_conciliacao import TRATA_CONCILIACAO
from python.ESTEIRAS import load_esteiras
import openpyxl
import numpy as np
from datetime import datetime
import os

'''def abas(excel_file):
    # 2. Pegamos a lista de todas as abas disponíveis
    todas_as_abas = excel_file.sheet_names

    # print(f'todas as abas: {todas_as_abas}')

    # 3. Identificamos as abas dinamicamente
    # Buscamos por 'Linhas' mas garantimos que não seja a que você quer descartar (se houver uma regra)
    # E buscamos por 'desc. Parciais'
    aba_linhas = None
    aba_parciais = None

    for nome in todas_as_abas:
        # Lógica para a aba de Linhas
        # Aqui verificamos se tem 'Linhas' no nome e se NÃO tem outros termos indesejados
        if "Linhas" in nome and "Suspensas" not in nome:
            aba_linhas = nome
        
        # Lógica para a aba de Descontos Parciais
        if "Desc. Parciais" in nome:
            aba_parciais = nome

        if  aba_linhas is not None and aba_parciais is not None:
            return aba_linhas, aba_parciais
        else:
            continue

d8_gov_to_amostra = pd.ExcelFile(r"P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\RETORNO-GOV_TOCANTINS-CAPITAL-032026.xlsx")
planilha_linhas, planilha_parciais = abas(d8_gov_to_amostra)'''

# print(f'planilhas linhas: {planilha_linhas}\nplanilhas parciais: {planilha_parciais}')


'''front = pd.read_csv(r"P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\FRONT GOV TO - IGEPREV 04-2026.csv", encoding="utf-8-sig", sep=";", on_bad_lines="skip", low_memory=False)
funcao = pd.read_csv(r"P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\FUNCAO GOV TO - IGEPREV 04-2026.csv", encoding="utf-8-sig", sep=";", on_bad_lines="skip", low_memory=False)
averbado_gov_to_capital = pd.read_excel(r"P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\AVERBADOSGOVTOCAPITAL942026_13_10.xlsx", header=17)
averbado_gov_to_ciasprev = pd.read_excel(r"P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\AVERBADOSGOVTOCIASPREV942026_13_11.xlsx", header=17)
averbado_gov_to_hp = pd.read_excel(r"P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\AVERBADOSGOVTOHOJE942026_13_9.xlsx", header=17)
averbado_igeprev_capital = pd.read_excel(r"P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\provisionamento_margem_CAPITAL.xlsx", header=4)
averbado_igeprev_ciasprev = pd.read_excel(r"P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\provisionamento_margem_CIASPREV.xlsx", header=4)
d8_gov_to_capital = pd.read_excel(r"P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\RETORNO-GOV_TOCANTINS-CAPITAL-032026.xlsx", header=7,sheet_name=planilha_linhas)
d8_gov_to_ciasprev = pd.read_excel(r"P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\RETORNO-GOV_TOCANTINS-CIASPREV-032026.xlsx", header=7,sheet_name=planilha_linhas)
d8_gov_to_hp = pd.read_excel(r"P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\RETORNO-GOV_TOCANTINS-CLICKBANK-032026.xlsx", header=7,sheet_name=planilha_linhas)
d8_gov_to_click = pd.read_excel(r"P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\RETORNO-GOV_TOCANTINS-HOJE-032026.xlsx", header=7,sheet_name=planilha_linhas)
d8_gov_to_capital_parciais = pd.read_excel(r"P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\RETORNO-GOV_TOCANTINS-CAPITAL-032026.xlsx", header=7, sheet_name=planilha_parciais)
d8_gov_to_ciasprev_parciais = pd.read_excel(r"P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\RETORNO-GOV_TOCANTINS-CIASPREV-032026.xlsx", header=7, sheet_name=planilha_parciais)
d8_gov_to_hp_parciais = pd.read_excel(r"P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\RETORNO-GOV_TOCANTINS-CLICKBANK-032026.xlsx", header=7, sheet_name=planilha_parciais)
d8_gov_to_click_parciais = pd.read_excel(r"P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\RETORNO-GOV_TOCANTINS-HOJE-032026.xlsx", header=7, sheet_name=planilha_parciais)
d8_igeprev_capital = pd.read_csv(r"P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\Movimento_Financeiro-IGEPREV-CAPITAL-032026.csv", encoding="latin1", sep=";", on_bad_lines="skip", low_memory=False)
d8_igeprev_ciasprev = pd.read_csv(r"P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\Movimento_Financeiro-IGEPREV-CIASPREV-032026.csv", encoding="latin1", sep=";", on_bad_lines="skip", low_memory=False)
conciliacao_df = pd.read_excel(r"P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\Conciliação-Governo do Tocantins + IGEPREV - 032026.xlsx")
kobraki_df = pd.read_excel(r"P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\RECEBIVEIS KOBRAKI - ABRIL 2026.xlsx", sheet_name="CONSOLIDADO")

caminho = r"P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\teste_programa"
'''
# , portal_file_list, d8_to, d8_igeprev, conciliacao=None,  kobraki=None
# averbado_unif = pd.concat()

class IGEPREV_GOVTO:
    def __init__(self, front, funcao, portal_file_path_to, portal_file_path_igeprev, d8_file_path_to, d8_file_path_igeprev, caminho, conciliacao=None, kobraki=None):
        self.caminho = caminho
        self.front = front
        self.averbados_to = portal_file_path_to
        self.averbados_igeprev = portal_file_path_igeprev
        self.d8_to = d8_file_path_to
        self.d8_igeprev = d8_file_path_igeprev
        self.funcao = funcao
        self.kobraki = kobraki if kobraki is not None else None
        self.caminho = caminho
        
        conciliacao_falso = pd.DataFrame(
            columns=['CONTRATOS', 'CPF', 'PRESTAÇÃO', 'PRAZO', 'D8 JUN 25', 'ST JUL 25', 'RECEBIDO GERAL'])
        conciliacao_falso['CONTRATOS'] = 123
        conciliacao_falso['CPF'] = '123.456'
        conciliacao_falso['PRESTAÇÃO'] = 10
        conciliacao_falso['PRODUTO'] = 'Cartão de Crédito'
        conciliacao_falso['PRAZO'] = 96
        conciliacao_falso['D8 JUN 25'] = 10
        conciliacao_falso['ST JUL 25'] = 'DESCONTO TOTAL'
        conciliacao_falso['RECEBIDO GERAL'] = 0


        self.conciliacao = conciliacao if conciliacao is not None else conciliacao_falso
        self.conciliacao.rename(columns={'PRESTAÇÃO ORIGINAL': 'PRESTAÇÃO', 'PMT': 'PRESTAÇÃO'}, inplace=True)
        self.conciliacao.rename(columns={'RECEBIDO GERAL ': 'RECEBIDO GERAL'}, inplace=True)
        self.conciliacao.rename(columns={'TIPO OPERAÇÃO': 'PRODUTO', 'NOVO TIPO DE OPERAÇÃO': 'PRODUTO', 'PRODUTOS PELO D8': 'PRODUTO', 
                                         'PRODUTO D8': 'PRODUTO', 'PRODUTO PELO D8': 'PRODUTO', 'PRODUTO ATUALIZADO': 'PRODUTO',
                                         'TIPO DE OPERAÇÃO': 'PRODUTO'}, inplace=True)
        
        self.condicoes_1 = load_esteiras()

        self.front_tratado = self.tratamento_front()

        self.unifica_averbados()

    def unifica_front_funcao(self):
        front = self.front
        funcao = self.funcao

        contrato_front = front['Contrato']
        ccb_tratado = front['CCB'].astype(str).str.slice(0, 9)
        ccb_tratado = ccb_tratado.astype('int64')

        # Verifica se o que é andamento no front está no função, se tiver transforma em integrado
        contrato_funcao = funcao['NR_PROP']
        front.loc[front['Contrato'].isin(contrato_funcao) & (front['Esteira'].str.contains('ANDAMENTO|PENDENTE')), 'Esteira'] = 'INTEGRADO'

        # Tira os contratos do Front que já existem no Função
        funcao = funcao[~funcao['NR_PROP'].isin(contrato_front)].copy()

        # Tira os contratos CCB do Front que também existem no Função
        funcao_tratado = funcao[~funcao['NR_PROP'].isin(ccb_tratado)].copy()


        # Juntar Funcao com Front
        # 1. Defina o mapeamento de nomes (De: Para)
        mapeamento = {
            'NR_PROP': 'Contrato',
            'CPF': 'CPF',
            'MATRICULA': 'Matricula',
            'CLIENTE': 'Nome',
            'PARC': 'Prazo',
            'VLR_PARC': 'Prestacao',
            'PRODUTO': 'Tipo Operacao',
            'ORIGEM_4': 'Convenio'
        }

        # 2. Filtre apenas as colunas necessárias de Funcao e renomeie-as
        # Isso garante que você só traga o que mapeou, evitando colunas extras indesejadas
        funcao_ajustado = funcao_tratado[list(mapeamento.keys())].rename(columns=mapeamento)

        # 3. Use o concat para unir os dois DataFrames
        # O ignore_index=True serve para gerar um novo índice sequencial no DF final
        front_unif = pd.concat([front, funcao_ajustado], ignore_index=True)

        # Coloca Preenche o resto das colunas necessárias com valores genéricos, para não ficarem vazias
        front_unif['Esteira'] = front_unif['Esteira'].fillna("INTEGRADO")
        front_unif['Orbital'] = front_unif['Orbital'].fillna("NAO")
        front_unif['Status'] = front_unif['Status'].fillna("INTEGRADO")
        front_unif['Acao Judicial'] = front_unif['Acao Judicial'].fillna("NAO")
        front_unif['Obito'] = front_unif['Obito'].fillna("NAO")

        # print(front_unif.tail())

        # front_unif.to_excel(rf"{self.caminho}\Teste_front.xlsx", index=False)

        return front_unif
    
    def tratamento_front_preliminar(self):
        front_consig = self.unifica_front_funcao()

        conciliacao = self.conciliacao.copy()


        # Insere as colunas vazias necessárias
        front_consig.insert(21, 'Saldo', '', True)
        front_consig.insert(22, 'Valor a lançar', '', True)
        front_consig.insert(23, 'OBS', '', True)

        print(f'Esteiras Únicas do front: {front_consig["Esteira"].unique()}')
        
        # Vamos renomear a primeira coluna da conciliação
        conciliacao.rename(columns={conciliacao.columns[0]: 'CONTRATOS'}, inplace=True)
        # Converte para lista de colunas
        cols = list(conciliacao.columns)

        # Atualiza o DataFrame com novos nomes
        conciliacao.columns = cols
        conciliacao['CONTRATOS'] = conciliacao['CONTRATOS'].astype('Int64')
        
        # Adiciona só as esteiras que podem ser lançadas
        front_consig_esteiras = front_consig[front_consig['Esteira'].isin(self.condicoes_1)].copy()

        # Casos que não lançamos de esteira
        front_esteiras_erradas = front_consig[~front_consig['Esteira'].isin(self.condicoes_1)].copy()

        front_esteiras_erradas.to_excel(fr'{self.caminho}\Esteiras Erradas do Front.xlsx', index=False)

        # Tentar transformar em string com virgula
        front_consig_esteiras.rename(columns={'Prestracao': 'Prestacao'}, inplace=True)

        front_consig_esteiras['Prestacao'] = front_consig_esteiras['Prestacao'].astype(str).replace('.', ',', regex=False)
        front_consig_esteiras['Valor a lançar'] = front_consig_esteiras['Valor a lançar'].astype(str).replace('.', ',', regex=False)


        # -------------------------------- MARCAR TUDO QUE NÃO LANÇA ---------------------------------- #
        # Marca saldo positivo
        front_consig_validado_termino = self.validacao_termino(front_consig_esteiras)
        front_consig_validado_termino.loc[front_consig_validado_termino['Saldo'] > -0.01, 'OBS'] = 'NÃO LANÇAR - SALDO POSITIVO'

        # Marca o que é ação judicial
        # No caso de Obito estiver estiver SIM e NÃO ao invés de 1 e 0
        front_consig_validado_termino['Acao Judicial'] = front_consig_validado_termino['Acao Judicial'].replace({'SIM': 1, 'NAO': 0})
        front_consig_validado_termino.loc[front_consig_validado_termino['Acao Judicial'] == 1, 'OBS'] = 'NÃO LANÇAR - AÇÃO JUDICIAL'

        # ------------------------------------- ESCOLHE CONSIGNATÁRIA -------------------------------------- #
        front_consig_validado_termino['Consignataria'].fillna('', inplace=True)

        # Renomear nomes dos bancos no front porque estão vindo com 0 na frente
        front_consig_validado_termino['Consignataria'] = front_consig_validado_termino['Consignataria'].astype(str).str.replace("CAPITAL CONSIG ", "CAPITAL CONSIG")
        front_consig_validado_termino['Consignataria'] = front_consig_validado_termino['Consignataria'].astype(str).str.replace("CLICKBANK ", "CLICKBANK")
        front_consig_validado_termino['Consignataria'] = front_consig_validado_termino['Consignataria'].astype(str).str.replace("CIASPREV ", "CIASPREV")
        front_consig_validado_termino['Consignataria'] = front_consig_validado_termino['Consignataria'].astype(str).str.replace("HOJE PREVIDENCIA PRIVADA ", "HOJE PREVIDÊNCIA PRIVADA")
        front_consig_validado_termino['Consignataria'] = front_consig_validado_termino['Consignataria'].astype(str).str.replace("HOJE PREVIDÊNCIA PRIVADA", "HOJE PREVIDÊNCIA PRIVADA")

        # Marca o que é Óbito
        # No caso de ação judicial estiver estiver SIM e NÃO ao invés de 1 e 0
        # front_consig_validado_termino['Obito'] = front_consig_validado_termino['Obito'].replace({'SIM': 1, 'NÃO': 0})
        # front_consig_validado_termino.loc[front_consig_validado_termino['Obito'] == 1, 'OBS'] = 'NÃO LANÇAR - ÓBITO'

        # Marcar liquidados em StatusContrato
        front_consig_validado_termino.loc[(front_consig_validado_termino['Status'].str.contains('Liquidado|CANCELADO', na=False)), 'OBS'] = 'NÃO LANÇAR - LIQUIDADO'

        # TIRAR BANCO OUTROS
        front_consig_validado_termino.loc[(front_consig_validado_termino['Consignataria'].str.contains('OUTROS', na=False)), 'OBS'] = 'NÃO LANÇAR - BANCO OUTROS'  

        # Salva com os NÃO LANÇAR
        print(f"tratamento_front_preliminar: Tentando salvar FRONT SEMI TRABALHADO em: {self.caminho}")
        try:
            front_consig_validado_termino.to_excel(fr'{self.caminho}\FRONT SEMI TRABALHADO {datetime.now().strftime("%m-%Y")}.xlsx', index=False)
            print("tratamento_front_preliminar: Arquivo salvo com sucesso!")
        except Exception as e:
            print(f"DEBUG: ERRO AO SALVAR FRONT SEMI TRABALHADO: {e}")

        return front_consig_validado_termino

    def tratamento_front(self):
        front_semi_tratado = self.tratamento_front_preliminar()

        # Separa na planilha somente o que está vazio na coluna OBS
        front_tratado = front_semi_tratado[front_semi_tratado['OBS'].fillna('') == '']

        # Colunas necessárias
        colunas_necessarias = ["Contrato", "CPF", "Matricula", "Nome", "Prestacao", "Prazo", "Convenio", "Consignataria", "Tipo Operacao", "Esteira", "Saldo", 
                               "Valor a lançar", "OBS", "Orbital", "Status", "Acao Judicial", "Obito"]
        front_tratado = front_tratado[colunas_necessarias]

        return front_tratado

    def validacao_termino(self, front):
        front_copy = front.copy()
        teste_conciliacao = TRATA_CONCILIACAO(self.conciliacao, self.kobraki)
        conciliacao_tratado = teste_conciliacao.trata_conciliacao()

        # Certifica que todos os contratos no Credbase trabalhado são do mesmo tipo
        # cred['Codigo_Credbase'] = cred['Codigo_Credbase'].astype(str)

        conciliacao_tratado['CONTRATOS'] = conciliacao_tratado['CONTRATOS'].astype('float').astype('Int64')
        # conciliacao_tratado['CONTRATOS'] = conciliacao_tratado['CONTRATOS'].astype('Int64')

        print('DEBUG: Colunas da conciliação tratada')
        try:
            conciliacao_tratado.to_excel(os.path.join(self.caminho, f"Conciliacao_TESTE.xlsx"), index=False)
        except Exception as e:
            print(f"DEBUG: ERRO AO SALVAR Conciliacao_TESTE.xlsx: {e}")


        # print(f'status \n{cred_copy[cred_copy['Codigo_Credbase'] == 300846910]}')

        # Puxar o saldo para o credbase
        front_copy['Saldo'] = front_copy['Contrato'].map(conciliacao_tratado.set_index('CONTRATOS')['Saldo']).to_dict()
        # front_copy['Saldo'] = pd.to_numeric(front_copy['Saldo'], errors='coerce')

        front_copy.rename(columns={'Prestracao': 'Prestacao'}, inplace=True)
        if front_copy['Prestacao'].dtype != 'float64':
            front_copy['Prestacao'] = front_copy['Prestacao'].astype(str).str.replace('.', '', regex=False)
            front_copy['Prestacao'] = front_copy['Prestacao'].str.replace(',', '.', regex=False)
            front_copy['Prestacao'] = pd.to_numeric(front_copy['Prestacao'], errors='coerce')

        # Valor que vai ser lançado
        # Substitui NaN em "Saldo" por um valor muito alto (para que "Parcela" seja escolhida)
        valor_a_lancar = np.minimum(np.abs(front_copy['Saldo']).fillna(float('inf')), front_copy['Prestacao'])

        front_copy['Valor a lançar'] = valor_a_lancar

        return front_copy
    
    def remove_peculios_indesejados(self, d8_unificado, front):
        # Separa só os valores de peculio do d8
        try:
            # 1. Criar o 'CONTSE SEQ' e o 'CONCAT' de uma vez só
            # Usamos o cumcount direto no agrupamento de CPF e Parcela
            d8_unificado['CONTSE SEQ'] = d8_unificado.groupby(['CPF', 'R$ PARCELA']).cumcount() + 1

            # 2. Gerar a chave final concatenada
            d8_unificado['CONCAT CPF PARCELA'] = (
                d8_unificado['CPF'].astype(str) + 
                d8_unificado['R$ PARCELA'].astype(str) + 
                d8_unificado['CONTSE SEQ'].astype(str)
            )
            # 3. Correção do .isin (precisa de uma lista [])
            # valores_peculio = [20, 40, 60, 80, 100, 120]
            valores_peculio = [20]
            d8_peculios = d8_unificado[d8_unificado['R$ PARCELA'].isin(valores_peculio)].copy()
            convenio = 'GOV. TO'
            
        except Exception as e:
            try:
                # 1. Criar o 'CONTSE SEQ' e o 'CONCAT' de uma vez só
                # Usamos o cumcount direto no agrupamento de CPF e Parcela
                d8_unificado['CONTSE SEQ'] = d8_unificado.groupby(['CPF', 'VLR.  ADE']).cumcount() + 1

                # 2. Gerar a chave final concatenada
                d8_unificado['CONCAT CPF PARCELA'] = (
                    d8_unificado['CPF'].astype(str) + 
                    d8_unificado['VLR.  ADE'].astype(str) + 
                    d8_unificado['CONTSE SEQ'].astype(str)
                )
                # 3. Correção do .isin (precisa de uma lista [])
                # valores_peculio = [20, 40, 60, 80, 100, 120]
                valores_peculio = [20]
                d8_peculios = d8_unificado[d8_unificado['VLR.  ADE'].isin(valores_peculio)].copy()

                convenio = 'IGEPREV'
                
            except Exception as e:
                print(f'Erro ao separar 20', e)

        # CONTSE SEQ
        front['CONTSE SEQ'] = front.groupby(['CPF', 'Prestacao']).cumcount() + 1
        # CONCAT FRONT
        front['CONCAT CPF PARCELA'] = (
            front['CPF'].astype(str) +
            front['Prestacao'].astype(str) +
            front['CONTSE SEQ'].astype(str)
            )
        
        # Separa os valores de 20 no front
        # front_peculios = front[front['Prestacao'].isin([20, 40, 60, 80, 100, 120])]
        front_peculios = front[front['Prestacao'].isin([20])]
        
        # 1. Pegamos a lista de chaves (CONCAT) que EXISTEM no front
        chaves_no_front = front_peculios['CONCAT CPF PARCELA'].unique()

        # 2. Identificamos as chaves de valor 20, 40, 60, 80, 100, 120 que estão no D8
        # (Você já tem o d8_peculios, vamos usar a coluna dele)
        chaves_no_d8_vinte = d8_peculios['CONCAT CPF PARCELA'].unique()

        # 3. Criamos a lista de quem deve ser APAGADO:
        # São as chaves que são de valor 20, 40, 60, 80, 100, 120 no D8, mas NÃO estão no front
        excluir_casos_d8 = [c for c in chaves_no_d8_vinte if c not in chaves_no_front]

        # 4. Removemos do d8_unificado original
        d8_unificado = d8_unificado[~d8_unificado['CONCAT CPF PARCELA'].isin(excluir_casos_d8)].copy()

        return d8_unificado
        
    
    def unifica_d8_gov_to(self):
        d8_gov_to_unificado = self.d8_to

        if d8_gov_to_unificado['R$ PARCELA'].dtype != 'float64':
            d8_gov_to_unificado['R$ PARCELA'] = d8_gov_to_unificado['R$ PARCELA'].astype(str).str.replace("R$ ", "")
            d8_gov_to_unificado['R$ PARCELA'] = d8_gov_to_unificado['R$ PARCELA'].astype(str).str.replace(".", "")
            d8_gov_to_unificado['R$ PARCELA'] = d8_gov_to_unificado['R$ PARCELA'].astype(str).str.replace(",", ".")
            d8_gov_to_unificado['R$ PARCELA'] = pd.to_numeric(d8_gov_to_unificado['R$ PARCELA'], errors='coerce')

        # Testa d8 sem peculios errados
        d8_govto_sem_peculios_errados = self.remove_peculios_indesejados(d8_gov_to_unificado, self.front_tratado)


        d8_govto_sem_peculios_errados.to_excel(fr'{self.caminho}\D8 UNIFICADO DE GOV TO.xlsx', index=False)

        return d8_govto_sem_peculios_errados

    def unifica_d8_igeprev(self):
        d8_igeprev_unificado = self.d8_igeprev

        '''igeprev_d8_capital = d8_igeprev_capital.copy()
        # Tira as últimas 5 linhas 
        igeprev_d8_capital_reduzido = igeprev_d8_capital[:-4]
        igeprev_d8_capital_reduzido['CONSIGNATARIA'] = 'CAPITAL'

        igeprev_d8_ciasprev = d8_igeprev_ciasprev.copy()
        # Tira as últimas 5 linhas 
        igeprev_d8_ciasprev_reduzido = igeprev_d8_ciasprev[:-4]
        igeprev_d8_ciasprev_reduzido['CONSIGNATARIA'] = 'CIASPREV'

        # Acho que dá para concatenar de boas
        d8_igeprev_unificado = pd.concat([igeprev_d8_capital_reduzido, igeprev_d8_ciasprev_reduzido], ignore_index=True)'''

        if d8_igeprev_unificado['VLR.  ADE'].dtype != 'float64':
            d8_igeprev_unificado['VLR.  ADE'] = d8_igeprev_unificado['VLR.  ADE'].astype(str).str.replace(".", "")
            d8_igeprev_unificado['VLR.  ADE'] = d8_igeprev_unificado['VLR.  ADE'].astype(str).str.replace(",", ".")
            d8_igeprev_unificado['VLR.  ADE'] = pd.to_numeric(d8_igeprev_unificado['VLR.  ADE'], errors='coerce')

        # Testa d8 sem peculios errados
        d8_igeprev_sem_peculios_errados = self.remove_peculios_indesejados(d8_igeprev_unificado, self.front_tratado)

        # Transforma  em excel
        d8_igeprev_sem_peculios_errados.to_excel(fr'{self.caminho}\D8 UNIFICADO DE IGEPREV.xlsx', index=False)

        return d8_igeprev_sem_peculios_errados
 
    def d8_com_prazo(self):
        d8_unificado_govt_to = self.unifica_d8_gov_to()
        d8_unificado_igeprev = self.unifica_d8_igeprev()

        # Separar prazo de d8 gov to
        d8_govto_prazo = d8_unificado_govt_to[(d8_unificado_govt_to['PARCELA'].str.contains('/')) & (~d8_unificado_govt_to['RUBRICA'].isin(['3620_2023', '3620_2024', '3620_2025']))]

        # Separar prazo de d8 igeprev
        d8_igeprev_prazo = d8_unificado_igeprev[~d8_unificado_igeprev['PRZ.'].isin([1, '1','Indeter.'])]
        d8_igeprev_prazo.to_excel(fr'{self.caminho}\D8 UNIFICADO DE IGEPREV COM PRAZO.xlsx', index=False)
        d8_govto_prazo.to_excel(fr'{self.caminho}\D8 UNIFICADO DE GOV TO COM PRAZO.xlsx', index=False)

        return d8_govto_prazo, d8_igeprev_prazo

    def front_com_d8(self):
        front_tratado = self.front_tratado
        d8_govto_prazo, d8_igeprev_prazo = self.d8_com_prazo()

        # Criar colunas no front
        front_tratado['SOMASE D8 GOV TO'] = ''
        front_tratado['SOMASE IGEPREV'] = ''
        front_tratado['SOMAS DE D8'] = ''
        front_tratado['SOMASE LOCAL'] = ''
        front_tratado['DIFF D8'] = ''
        
        # Vamos reordenar o arquivo para HP ficar em primeiro
        front_tratado = front_tratado.sort_values(by=['Consignataria'], ascending=False)

        # Somase de d8 gov to
        somase_d8_govto = d8_govto_prazo.groupby('CPF')['R$ PARCELA'].sum()
        front_tratado['SOMASE D8 GOV TO'] = front_tratado['CPF'].map(somase_d8_govto).fillna(0)
        

        # Somase de d8 igeprev
        somase_d8_igeprev = d8_igeprev_prazo.groupby('CPF')['VLR.  ADE'].sum()
        front_tratado['SOMASE IGEPREV'] = front_tratado['CPF'].map(somase_d8_igeprev).fillna(0)

        # Soma dos d8
        front_tratado['SOMAS DE D8'] = front_tratado['SOMASE D8 GOV TO'] + front_tratado['SOMASE IGEPREV']

        # Adiciona mais 20 em cada cpf de hp
        front_tratado.loc[front_tratado['Consignataria'] == 'HOJE PREVIDÊNCIA PRIVADA', 'Valor a lançar'] += 20

        # SOMASE LOCAL
        front_tratado['SOMASE LOCAL'] = front_tratado.groupby("CPF")['Valor a lançar'].transform('sum')

        # Diff entre somas dos SOMASES de D8 e SOMASE LOCAL
        front_tratado['DIFF D8'] = front_tratado['SOMASE LOCAL'] - front_tratado['SOMAS DE D8']
        front_tratado['DIFF D8'] = front_tratado['DIFF D8'].round(2)

        # Coluna Gêmea de Diff para não alterar os valores originais
        front_tratado['Lançar'] = front_tratado['DIFF D8'].copy()

        # Transforma valores negativos em 0
        front_tratado.loc[front_tratado['DIFF D8'] < 0, 'Lançar'] = 0
        
        # Contse seq no front para pegar só os primeiros
        front_tratado['Contse seq'] = front_tratado.groupby(['CPF', 'Lançar']).cumcount() + 1

        front_tratado.to_excel(fr'{self.caminho}\FRONT MEIO TRATADO.xlsx', index=False)


        # Vamos salvar e retornar somente o que é maior que 0
        front_trabalhado = front_tratado[(front_tratado['Lançar'] > 0) & (front_tratado['Contse seq'] == 1)]
        
        front_trabalhado.to_excel(fr'{self.caminho}\FRONT TOTALMENTE TRABALHADO.xlsx', index=False)

        return front_trabalhado # [front_trabalhado['Contse seq'] == 1]
    
    def unifica_averbados(self):
        gov_to_averbado_unificado = self.averbados_to
        '''gov_to_capital_averbado = averbado_gov_to_capital
        gov_to_ciasprev_averbado = averbado_gov_to_ciasprev
        gov_to_hp_averbado = averbado_gov_to_hp
        gov_to_capital_averbado['Consignataria'] = 'CAPITAL'
        gov_to_ciasprev_averbado['Consignataria'] = 'CIASPREV'
        gov_to_hp_averbado['Consignataria'] = "HP"'''

        front_trabalhado = self.front_com_d8()

        # Unifica averbações de GOV TO
        # gov_to_averbado_unificado = pd.concat([gov_to_capital_averbado, gov_to_ciasprev_averbado, gov_to_hp_averbado], ignore_index=True)

        if gov_to_averbado_unificado['VALOR_PARCELA'].dtype != "float64":
            gov_to_averbado_unificado['VALOR_PARCELA'] = gov_to_averbado_unificado['VALOR_PARCELA'].astype(str).str.replace(".", "")
            gov_to_averbado_unificado['VALOR_PARCELA'] = gov_to_averbado_unificado['VALOR_PARCELA'].astype(str).str.replace(",", ".")
            gov_to_averbado_unificado['VALOR_PARCELA'] = pd.to_numeric(gov_to_averbado_unificado['VALOR_PARCELA'], errors='coerce')

        # Status ADF
        gov_to_averbado_unificado = gov_to_averbado_unificado[gov_to_averbado_unificado['STATUS_ADF'].isin(['CONSOLIDADO', 'INSERIDO'])]

        # PRAZo
        gov_to_averbado_unificado = gov_to_averbado_unificado[gov_to_averbado_unificado['PRAZO'].isin(['INDETERMINADO'])]

        # Vamos gerar o arquivo para averiguar melhor
        gov_to_averbado_unificado.to_excel(fr'{self.caminho}\AVERBADOS DE GOV TO UNIFICADOS.xlsx', index=False)

        # 1. Resolver os casos de valores iguais (remover duplicados exatos)
        # Isso remove as linhas onde MATRICULA, Consignataria e VALOR_PARCELA são idênticos,
        # mantendo apenas a primeira ocorrência.
        total_duplicados_anterior = gov_to_averbado_unificado.duplicated(subset=['MATRICULA', 'Consignataria', 'VALOR_PARCELA']).sum()
        # print(f'Quantos duplicados de MATRICULA, CONSIGNATARIA E PARCELA foram removidos antes da soma: {total_duplicados_anterior}')

        '''gov_to_averbado_unificado = gov_to_averbado_unificado.drop_duplicates(
            subset=['MATRICULA', 'Consignataria', 'RUBRICA_CODIGO', 'VALOR_PARCELA'], 
            keep='first'
        )



        # Ele calcula a soma por grupo e "espalha" o resultado nas linhas originais
        gov_to_averbado_unificado['VALOR_PARCELA'] = gov_to_averbado_unificado.groupby(['MATRICULA', 'RUBRICA_CODIGO', 'Consignataria'])['VALOR_PARCELA'].transform('sum')
        
        total_duplicados_posterior = gov_to_averbado_unificado.duplicated(subset=['MATRICULA', 'Consignataria', 'VALOR_PARCELA']).sum()
        # print(f'Quantos duplicados de MATRICULA, CONSIGNATARIA E PARCELA foram removidos depois da soma: {total_duplicados_posterior}')

        gov_to_averbado_unificado = gov_to_averbado_unificado.drop_duplicates(
            subset=['MATRICULA', 'Consignataria', 'RUBRICA_CODIGO', 'VALOR_PARCELA'], 
            keep='first'
        )'''

        # 1. Identificamos os grupos e contamos quantos valores únicos de 'VALOR_PARCELA' existem em cada um
        '''gov_to_averbado_unificado = gov_to_averbado_unificado.groupby(['MATRICULA', 'Consignataria', 'RUBRICA_CODIGO']).filter(
            lambda x: x['VALOR_PARCELA'].nunique() == 1 or len(x) == 1
        )'''

        # 1. Garantir que a coluna de valor seja numérica para ordenação correta
        gov_to_averbado_unificado['VALOR_PARCELA'] = pd.to_numeric(gov_to_averbado_unificado['VALOR_PARCELA'], errors='coerce').fillna(0)

        # 2. ORDENAÇÃO É A CHAVE: 
        # Colocamos as colunas de agrupamento e o VALOR_PARCELA em ordem DECRESCENTE (ascending=False)
        # Isso coloca o maior valor de cada grupo no topo da lista.
        gov_to_averbado_unificado_sorted = gov_to_averbado_unificado.sort_values(
            by=['MATRICULA', 'Consignataria', 'RUBRICA_CODIGO', 'VALOR_PARCELA'], 
            ascending=[True, True, True, False]
        )

        # 3. IDENTIFICAÇÃO DAS DUPLICATAS DE GRUPO
        # Marcamos todas as linhas que têm o mesmo grupo (sem olhar o valor ainda)
        gov_to_averbado_unificado_sorted['is_duplicate_group'] = gov_to_averbado_unificado_sorted.duplicated(
            subset=['MATRICULA', 'Consignataria', 'RUBRICA_CODIGO'], 
            keep=False
        )

        # 4. IDENTIFICAÇÃO DE VALORES IGUAIS
        # Marcamos se o valor da parcela é idêntico dentro do grupo
        gov_to_averbado_unificado_sorted['is_value_match'] = gov_to_averbado_unificado_sorted.duplicated(
            subset=['MATRICULA', 'Consignataria', 'RUBRICA_CODIGO', 'VALOR_PARCELA'], 
            keep=False
        )

        # 5. FILTRAGEM FINAL
        # Mantemos a linha se:
        # - Não for uma duplicata de grupo (é única)
        # - OU se o valor for igual ao de outras do mesmo grupo (conforme seu pedido anterior)
        # - OU se for a PRIMEIRA de um grupo de valores diferentes (que por causa do sort, é a maior)

        resultado = gov_to_averbado_unificado_sorted[
            (~gov_to_averbado_unificado_sorted['is_duplicate_group']) |      # Caso 1: Linha única
            (gov_to_averbado_unificado_sorted['is_value_match']) |           # Caso 2: Valores iguais permanecem
            (~gov_to_averbado_unificado_sorted.duplicated(subset=['MATRICULA', 'Consignataria', 'RUBRICA_CODIGO'], keep='first')) # Caso 3: Maior valor
        ].copy()

        # Limpeza final
        gov_to_averbado_unificado_resultado = resultado.drop(columns=['is_duplicate_group', 'is_value_match'])

        # Adiciona ponto e traço
        cpf_tratado = gov_to_averbado_unificado_resultado['CPF'].astype(str).str.zfill(11).str.replace(r'(\d{3})(\d{3})(\d{3})(\d{2})',  r'\1.\2.\3-\4', regex=True)
        gov_to_averbado_unificado_resultado['CPF'] = cpf_tratado



        gov_to_averbado_unificado_resultado['Convenio'] = 'Governo de Tocantins'

        # Pega só o que é cartão de GOV TO
        gov_to_averbado_unificado_resultado = gov_to_averbado_unificado_resultado[(gov_to_averbado_unificado_resultado['PRAZO'].isin(['INDETERMINADO'])) & (gov_to_averbado_unificado_resultado['STATUS_ADF'].isin(['CONSOLIDADO', 'INSERIDO']))]

        '''igeprev_capital_averbado = averbado_igeprev_capital.iloc[:-6]
        igeprev_ciasprev_averbado = averbado_igeprev_ciasprev.iloc[:-6]'''

        # Remove apenas as colunas que estão 100% vazias
        '''igeprev_capital_averbado = igeprev_capital_averbado.dropna(axis=1, how='all')
        igeprev_capital_averbado['Consignataria'] = 'CAPITAL'
        igeprev_ciasprev_averbado['Consignataria'] = 'CIASPREV'
        igeprev_ciasprev_averbado = igeprev_ciasprev_averbado.dropna(axis=1, how='all')'''

        # Unifica averbações de IGEPREV
        igeprev_averbado_unificado = self.averbados_igeprev
        igeprev_averbado_unificado.rename(columns={"SERVIDOR": "SERVIDOR + MATRICULA"}, inplace=True)

        igeprev_averbado_unificado.insert(1, "MATRICULA", "", True)
        igeprev_averbado_unificado.insert(2, "SERVIDOR", "", True)
        igeprev_averbado_unificado.insert(7, "PRAZO", 1, True)
        igeprev_averbado_unificado.insert(8, "RUBRICA_CODIGO", 1, True)

        # Divide a coluna de SERVIDOR que vem matricula e o nome dos clientes, em duas colunas distintas
        igeprev_averbado_unificado[["MATRICULA", "SERVIDOR"]] = igeprev_averbado_unificado['SERVIDOR + MATRICULA'].str.split(" - ", n=1, expand=True)

        igeprev_averbado_unificado.to_excel(fr'{self.caminho}\IGEPREV AVERBADO TESTE.xlsx', index=False)

        # Renomeia as colunas de GOV TO
        igeprev_averbado_unificado.rename(columns={'SERVIDOR': 'NOME', 'ÓRGÃO': 'Convenio', 'SERVIÇO': 'RUBRICA_DESCRICAO', 'VLR RESERV.': 'VALOR_PARCELA'}, inplace=True)

        # Mapeamento novo
        mapeamento = ['MATRICULA', 'CPF', 'NOME', 'PRAZO', 'VALOR_PARCELA', 'RUBRICA_DESCRICAO', 'RUBRICA_CODIGO', 'Convenio', 'Consignataria']

        gov_to_remapeado = gov_to_averbado_unificado_resultado[mapeamento]
        
        igeprev_remapeado = igeprev_averbado_unificado[mapeamento]
        if igeprev_remapeado['VALOR_PARCELA'].dtype != 'float64':
            igeprev_remapeado['VALOR_PARCELA'] = igeprev_remapeado['VALOR_PARCELA'].str.replace(".", '')
            igeprev_remapeado['VALOR_PARCELA'] = igeprev_remapeado['VALOR_PARCELA'].str.replace(",", '.')
            igeprev_remapeado['VALOR_PARCELA'] = pd.to_numeric(igeprev_remapeado['VALOR_PARCELA'], errors='coerce')
        
        # print(f'COLUNAS DE GOV TO REMAPEADO {gov_to_remapeado.columns}\n')
        # print(f'COLUNAS DE IGEPREV REMAPEADO {igeprev_remapeado.columns}')
        to_igeprev_unificado = pd.concat([gov_to_remapeado, igeprev_remapeado], ignore_index=True)
        # print(f'VALOR_PARCELA TERCEIRO:\n{gov_to_remapeado['VALOR_PARCELA']}')

        # CRIAÇÃO DE COLUNAS QUE SERÃO USADAS NO PRÓXIMO MÓDULO
        to_igeprev_unificado['CONTSE CPF'] = ''
        to_igeprev_unificado['CONTSE SEQ'] = ''
        to_igeprev_unificado['PARCELA FRONT'] = ''
        to_igeprev_unificado['SOMASE CRED'] = ''
        to_igeprev_unificado['OBS'] = ''

        somase_cred = front_trabalhado.groupby('CPF')['Lançar'].sum().to_dict()
        # print(f'TIPO SOMASE_CRED:\n{somase_cred}')

        to_igeprev_unificado['SOMASE CRED'] = to_igeprev_unificado['CPF'].map(somase_cred).fillna(0)

        def distribuicao_valores(averbado_para_distribuir):
            # IMPORTANTE: Garanta que as colunas de valores são numéricas, não texto.
            # O .to_numeric(errors='coerce') converte o que for possível para número e põe NaN no que não for.
            to_igeprev_averbado_final = averbado_para_distribuir.copy()
            to_igeprev_averbado_final['VALOR_PARCELA'] = pd.to_numeric(to_igeprev_averbado_final['VALOR_PARCELA'], errors='coerce').fillna(0)

            '''if to_igeprev_averbado_final['SOMASE CRED'].dtype != 'float64':
                to_igeprev_averbado_final['SOMASE CRED'] = to_igeprev_averbado_final['SOMASE CRED'].str.replace(".", "")
                to_igeprev_averbado_final['SOMASE CRED'] = to_igeprev_averbado_final['SOMASE CRED'].str.replace(",", ".")
                to_igeprev_averbado_final['SOMASE CRED'] = pd.to_numeric(to_igeprev_averbado_final['SOMASE CRED'], errors='coerce').fillna(0)'''

            # 1. Calcula a soma ACUMULADA da reserva dentro de cada grupo de CPF.
            # Esta é a "mágica" que substitui a necessidade de um loop.
            to_igeprev_averbado_final['SOMA ACUMULADA DA RESERVA'] = to_igeprev_averbado_final.groupby('CPF')['VALOR_PARCELA'].cumsum()

            # 2. Calcula o valor que JÁ FOI ALOCADO para as linhas ANTERIORES.
            # É a soma acumulada até a linha atual, menos o valor da própria linha.
            alocado_anteriormente = to_igeprev_averbado_final['SOMA ACUMULADA DA RESERVA'] - to_igeprev_averbado_final['VALOR_PARCELA']
            to_igeprev_averbado_final['ALOCADO ANTERIORMENTE'] = alocado_anteriormente

            # 3. Calcula o saldo restante do SOMASE ANTES de processar a linha atual.
            saldo_restante = to_igeprev_averbado_final['SOMASE CRED'] - alocado_anteriormente

            # 4. O valor a lançar é o MÍNIMO entre o que a reserva da linha pede e o saldo que ainda temos.
            # Usamos .clip(0) para garantir que o saldo não seja negativo (se já estourou, é 0).
            valor_a_lancar = np.minimum(to_igeprev_averbado_final['VALOR_PARCELA'], saldo_restante.clip(0))

            to_igeprev_averbado_final['VALOR LANÇAR'] = valor_a_lancar.round(2)

            # averbado_novo.loc[averbado_novo['VALOR A LANÇAR CPF'] == 0, 'OBS'] = 'NÃO'

            # 7. Vamos criar a coluna Diff para lançar os parciais
            somase_lancar = to_igeprev_averbado_final.groupby('CPF')['VALOR LANÇAR'].transform('sum')
            to_igeprev_averbado_final['DIFF'] = somase_lancar - to_igeprev_averbado_final['SOMASE CRED']
            to_igeprev_averbado_final['DIFF'] = to_igeprev_averbado_final['DIFF'].round(2)

            # 8. Adiciona a coluna de SITUAÇÃO DE DESCONTO para TOTAL ou PARCIAL
            to_igeprev_averbado_final['SITUAÇÃO DE DESCONTO'] = ''
            to_igeprev_averbado_final.loc[to_igeprev_averbado_final['DIFF'] < 0, 'SITUAÇÃO DE DESCONTO'] = 'PARCIAL'
            to_igeprev_averbado_final.loc[to_igeprev_averbado_final['DIFF'] >= 0, 'SITUAÇÃO DE DESCONTO'] = 'TOTAL'

            # 9. Novo Lançar total
            # to_igeprev_averbado_final['LANÇAR TOTAL'] = to_igeprev_averbado_final['VALOR_PARCELA'] - to_igeprev_averbado_final['DIFF']

            return to_igeprev_averbado_final

        to_igeprev_finalizado = distribuicao_valores(to_igeprev_unificado)

        print('DEBUG: Averbados após cálculo vetorizado:')
        try:
            to_igeprev_finalizado.to_excel(os.path.join(self.caminho, f"GOV TO E IGEPREV TRABALHADO {str(datetime.now().month).zfill(2)}-{datetime.now().year}.xlsx"), index=False)
        except Exception as e:
            print(f"DEBUG: ERRO AO SALVAR AVERBADOS TRABALHADO: {e}")

'''teste = IGEPREV_GOVTO(front, funcao, conciliacao_df, kobraki_df)

resultado = teste.unifica_averbados()'''



    