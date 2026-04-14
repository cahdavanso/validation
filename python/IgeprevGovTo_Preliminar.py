import pandas as pd
from python.trata_conciliacao import TRATA_CONCILIACAO

front = pd.read_csv("P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\FRONT GOV TO - IGEPREV 04-2026.csv", encoding="utf-8-sig", sep=";", on_bad_lines="skip", low_memory=False)
funcao = pd.read_csv("P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\FUNCAO GOV TO - IGEPREV 04-2026.csv", "P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\FUNCAO GOV TO - IGEPREV 04-2026.csv")
averbado_gov_to_capital = pd.read_excel("P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\AVERBADOSGOVTOCAPITAL942026_13_10.xlsx")
averbado_gov_to_ciasprev = pd.read_excel("P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\AVERBADOSGOVTOCIASPREV942026_13_11.xlsx")
averbado_gov_to_hp = pd.read_excel("P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\AVERBADOSGOVTOHOJE942026_13_9.xlsx")
averbado_igeprev_capital = pd.read_excel("P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\provisionamento_margem_CAPITAL.xlsx")
averbado_igeprev_ciasprev = pd.read_excel("P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\provisionamento_margem_CIASPREV.xlsx")
d8_gov_to_capital = pd.read_excel("P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\RETORNO-GOV_TOCANTINS-CAPITAL-032026.xlsx")
d8_gov_to_ciasprev = pd.read_excel("P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\RETORNO-GOV_TOCANTINS-CIASPREV-032026.xlsx")
d8_gov_to_hp = pd.read_excel("P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\RETORNO-GOV_TOCANTINS-CLICKBANK-032026.xlsx")
d8_gov_to_click = pd.read_excel("P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\RETORNO-GOV_TOCANTINS-HOJE-032026.xlsx")
d8_igeprev_capital = pd.read_csv("P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\Movimento_Financeiro-IGEPREV-CAPITAL-032026.csv", encoding="utf-8-sig", sep=";", on_bad_lines="skip", low_memory=False)
d8_igeprev_ciasprev = pd.read_csv("P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\Movimento_Financeiro-IGEPREV-CIASPREV-032026.csv", encoding="utf-8-sig", sep=";", on_bad_lines="skip", low_memory=False)
conciliacao_df = pd.read_excel("P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\Conciliação-Governo do Tocantins + IGEPREV - 032026.xlsx")
kobraki_df = pd.read_excel("P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\RECEBIVEIS KOBRAKI - ABRIL 2026.xlsx")

averbado_unif = pd.concat()

class IGEPREV_GOVTO_PRELIMINAR:
    def __init__(self, front, funcao, portal_file_list, d8_to, d8_igeprev, conciliacao=None,  kobraki=None):
        self.front = front
        self.averbados = portal_file_list
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
        self.conciliacao.rename(columns={'PRESTAÇÃO ORIGINAL': 'PRESTAÇÃO'}, inplace=True)
        self.conciliacao.rename(columns={'RECEBIDO GERAL ': 'RECEBIDO GERAL'}, inplace=True)
        self.conciliacao.rename(columns={'TIPO OPERAÇÃO': 'PRODUTO', 'NOVO TIPO DE OPERAÇÃO': 'PRODUTO', 'PRODUTOS PELO D8': 'PRODUTO', 
                                         'PRODUTO D8': 'PRODUTO', 'PRODUTO PELO D8': 'PRODUTO', 'PRODUTO ATUALIZADO': 'PRODUTO',
                                         'TIPO DE OPERAÇÃO': 'PRODUTO'}, inplace=True)
        
    def unifica_front_funcao(self):
        front = self.front.copy()
        funcao = self.funcao.copy()

        contrato_front = front['Contrato']
        ccb_tratado = front['CCB'].astype(str).str.slice(0, 9)

        # Tira os contratos do Front que já existem no Função
        funcao = funcao[~funcao['NR_PROP'].isin(contrato_front)].copy()

        # Tira os contratos CCB do Front que também existem no Função
        funcao = funcao[~funcao['NR_PROP'].isin(ccb_tratado)].copy()



    