import pandas as pd
from trata_conciliacao import TRATA_CONCILIACAO
from ESTEIRAS import load_esteiras
import openpyxl
import numpy as np
from datetime import datetime
import os

def abas(excel_file):
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
planilha_linhas, planilha_parciais = abas(d8_gov_to_amostra)

# print(f'planilhas linhas: {planilha_linhas}\nplanilhas parciais: {planilha_parciais}')


front = pd.read_csv(r"P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\FRONT GOV TO - IGEPREV 04-2026.csv", encoding="utf-8-sig", sep=";", on_bad_lines="skip", low_memory=False)
funcao = pd.read_csv(r"P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\FUNCAO GOV TO - IGEPREV 04-2026.csv", encoding="utf-8-sig", sep=";", on_bad_lines="skip", low_memory=False)
averbado_gov_to_capital = pd.read_excel(r"P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\AVERBADOSGOVTOCAPITAL942026_13_10.xlsx")
averbado_gov_to_ciasprev = pd.read_excel(r"P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\AVERBADOSGOVTOCIASPREV942026_13_11.xlsx")
averbado_gov_to_hp = pd.read_excel(r"P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\AVERBADOSGOVTOHOJE942026_13_9.xlsx")
averbado_igeprev_capital = pd.read_excel(r"P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\provisionamento_margem_CAPITAL.xlsx")
averbado_igeprev_ciasprev = pd.read_excel(r"P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\provisionamento_margem_CIASPREV.xlsx")
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

# , portal_file_list, d8_to, d8_igeprev, conciliacao=None,  kobraki=None
# averbado_unif = pd.concat()

class IGEPREV_GOVTO_PRELIMINAR:
    def __init__(self, front, funcao, conciliacao=None, kobraki=None):
        self.caminho = caminho
        self.front = front
        # self.averbados = portal_file_list
        self.funcao = funcao
        self.kobraki = kobraki if kobraki is not None else None
        
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

        
        
    def unifica_front_funcao(self):
        front = self.front.copy()
        funcao = self.funcao.copy()

        contrato_front = front['Contrato']
        ccb_tratado = front['CCB'].astype(str).str.slice(0, 9)
        ccb_tratado = ccb_tratado.astype('int64')

        # Tira os contratos do Front que já existem no Função
        funcao = funcao[(~funcao['NR_PROP'].isin(contrato_front)) & (~funcao["ORIGEM_3"].str.contains("IV PROMOTORA"))].copy()

        # Tira os contratos CCB do Front que também existem no Função
        funcao = funcao[~funcao['NR_PROP'].isin(ccb_tratado)].copy()

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
        funcao_ajustado = funcao[list(mapeamento.keys())].rename(columns=mapeamento)

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

        front_unif.to_excel(rf"{self.caminho}\Teste_front.xlsx", index=False)

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
        front_consig_validado_termino['Consignataria'] = front_consig_validado_termino['Consignataria'].astype(str).str.replace("HOJE PREVIDENCIA PRIVADA ", "HOJE PREVIDENCIA PRIVADA")

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

        front_tratado.to_excel(fr'{self.caminho}\FRONT TRABALHADO {datetime.now().strftime("%m-%Y")}.xlsx', index=False)

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
    
    def unifica_d8_gov_to(self):
        gov_to_d8_capital = d8_gov_to_capital
        gov_to_d8_ciasprev = d8_gov_to_ciasprev
        gov_to_d8_hp = d8_gov_to_hp
        gov_to_d8_click = d8_gov_to_click
        gov_to_d8_capital_parcial = d8_gov_to_capital_parciais
        gov_to_d8_ciasprev_parcial = d8_gov_to_ciasprev_parciais
        gov_to_d8_hp_parcial = d8_gov_to_hp_parciais
        gov_to_d8_click_parcial = d8_gov_to_click_parciais

        # Adiciona CONSIGNATARIA no final de cada DataFrame
        gov_to_d8_capital['CONSIGNATARIA'] = 'CAPITAL'
        gov_to_d8_ciasprev['CONSIGNATARIA'] = 'CIASPREV'
        gov_to_d8_hp['CONSIGNATARIA'] = 'HP'
        gov_to_d8_click['CONSIGNATARIA'] = 'CLICK'

        # Adiciona CONSIGNATARIA no final de cada DataFrame Parcial
        gov_to_d8_capital_parcial['CONSIGNATARIA'] = 'CAPITAL'
        gov_to_d8_ciasprev_parcial['CONSIGNATARIA'] = 'CIASPREV'
        gov_to_d8_hp_parcial['CONSIGNATARIA'] = 'HP'
        gov_to_d8_click_parcial['CONSIGNATARIA'] = 'CLICK'

        '''print(f'd8 parcial de gov to Capital\n{d8_gov_to_capital_parciais}\n')
        print(f'd8 parcial de gov to Ciasprev\n{d8_gov_to_ciasprev_parciais}\n')
        print(f'd8 parcial de gov to HP\n{d8_gov_to_hp_parciais}\n')
        print(f'd8 parcial de gov to Click\n{d8_gov_to_click_parciais}\n')'''

        d8_gov_to_unificado_linhas = pd.concat([gov_to_d8_capital, gov_to_d8_ciasprev, gov_to_d8_hp, gov_to_d8_click], ignore_index=True)
        d8_gov_to_unificado_parciais = pd.concat([gov_to_d8_capital_parcial, gov_to_d8_ciasprev_parcial, gov_to_d8_hp_parcial, gov_to_d8_click_parcial], ignore_index=True)

        # Muda o nome da coluna R$ PARCELA DESCONTADA da aba de Parciais para R$ PARCELA
        d8_gov_to_unificado_parciais.rename(columns={'R$ PARCELA DESCONTADA': 'R$ PARCELA'}, inplace=True)
        print(f'Colunas de d8_gov_to_unificado_parciais: {d8_gov_to_unificado_parciais.columns}')

        # Mapeamento das colunas para concatenar
        mapeamento_d8 = ["ORDEM", "REFERENCIA", "CPF", "MATRICULA", "NOME", "RUBRICA", "PARCELA", "ADF", "R$ PARCELA", "CONSIGNATARIA"]

        d8_gov_to_unificado_linhas = d8_gov_to_unificado_linhas[mapeamento_d8]
        d8_go_to_unificado_parciais_reduzido = d8_gov_to_unificado_parciais[mapeamento_d8]

        d8_gov_to_unificado = pd.concat([d8_gov_to_unificado_linhas, d8_go_to_unificado_parciais_reduzido], ignore_index=True)


        d8_gov_to_unificado.to_excel(fr'{self.caminho}\D8 UNIFICADO DE GOV TO.xlsx', index=False)

    def unifica_d8_igeprev(self):
        igeprev_d8_capital = d8_igeprev_capital.copy()
        # Tira as últimas 5 linhas 
        igeprev_d8_capital_reduzido = igeprev_d8_capital[:-4]
        igeprev_d8_capital_reduzido['CONSIGNATARIA'] = 'CAPITAL'

        igeprev_d8_ciasprev = d8_igeprev_ciasprev.copy()
        # Tira as últimas 5 linhas 
        igeprev_d8_ciasprev_reduzido = igeprev_d8_ciasprev[:-4]
        igeprev_d8_ciasprev_reduzido['CONSIGNATARIA'] = 'CIASPREV'

        # Acho que dá para concatenar de boas
        d8_igeprev_unificado = pd.concat([igeprev_d8_capital_reduzido, igeprev_d8_ciasprev_reduzido], ignore_index=True)

        # Transforma  em excel
        d8_igeprev_unificado.to_excel(fr'{self.caminho}\D8 UNIFICADO DE IGEPREV.xlsx', index=False)
 
        

teste = IGEPREV_GOVTO_PRELIMINAR(front, funcao, conciliacao_df, kobraki_df)

resultado = teste.unifica_d8_igeprev()




    