import pandas as pd
import zipfile
import io
from io import StringIO
from python.trata_conciliacao import TRATA_CONCILIACAO
from python.ESTEIRAS import load_esteiras
from python.funcoes_comuns import UNIFICA_FRONT_FUNC_ESTEIRAS
from python.Tratador_Front_Base import TratadorIgeprevTo
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
recebimentos_df = pd.read_excel(r"P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\RELATORIOS\RECEBIVEIS RECEBIMENTOS - ABRIL 2026.xlsx", sheet_name="CONSOLIDADO")

caminho = r"P:\PESSOAL\2026\ABRIL\GOV TO - IGEPREV\teste_programa"
'''
# , portal_file_list, d8_to, d8_igeprev, conciliacao=None,  recebimentos=None
# averbado_unif = pd.concat()

class IGEPREV_GOVTO:
    def __init__(self, front, convenio, portal_file_path_to, portal_file_path_igeprev, d8_file_path_to, d8_file_path_igeprev, recusados_igeprev, caminho, funcao=None, andamento_funcao=None,conciliacao=None, recebimentos=None, extra_judicial=None, desconto_inadimplencia=None):
        self.caminho = caminho
        self.front = front
        self.convenio = convenio
        self.averbados_to = portal_file_path_to
        self.averbados_igeprev = portal_file_path_igeprev
        self.d8_to = d8_file_path_to
        self.recusados_igeprev = recusados_igeprev # -> É só o movimento financeiro de igeprev do mês anterior ao que estamos trabalhando
        self.d8_igeprev = d8_file_path_igeprev
        self.funcao = funcao
        self.andamento_funcao = andamento_funcao
        self.recebimentos = recebimentos if recebimentos is not None else None
        self.extra_judicial = extra_judicial if extra_judicial is not None else None
        self.desconto_inadimplencia = desconto_inadimplencia if desconto_inadimplencia is not None else None
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

        # self.front_tratado = self.tratamento_front()

        unificador = UNIFICA_FRONT_FUNC_ESTEIRAS(
                            front=self.front,
                            convenio=self.convenio,
                            funcao=self.funcao, 
                            andamento_funcao=self.andamento_funcao, caminho=self.caminho
                        )
                
        # 2. Chama a primeira unificação (Função pura)
        # Isso vai processar e preencher com verificar_ccb=True
        front_meio_caminho = unificador.unifica_front_funcao()

        # 3. Atualiza o front interno da classe para que a segunda unificação use os dados já combinados
        unificador.front = front_meio_caminho

        # 4. Chama a segunda unificação (Andamento Função)
        # Isso vai processar a segunda base com verificar_ccb=False
        self.front_final_consig = unificador.unifica_front_funcao_esteiras_andamento()

        front_semi_trabalhado_preliminar = TratadorIgeprevTo(front=self.front_final_consig, conciliacao=self.conciliacao, convenio=self.convenio,
                                                                    caminho=self.caminho, condicoes_1=self.condicoes_1,
                                                                    recebimentos=self.recebimentos, desconto_inadimplencia=desconto_inadimplencia)
        self.front_semi_trabalhado = front_semi_trabalhado_preliminar.tratamento_front_preliminar_base()
        self.front_tratado = self.front_semi_trabalhado[self.front_semi_trabalhado['OBS'].isin([pd.NA, np.nan, ''])]

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
        front_unif['Consignataria'] = front_unif['Consignataria'].fillna('HOJE PREVIDÊNCIA PRIVADA')

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

        front_esteiras_erradas.to_excel(fr'{self.caminho}\Esteiras Erradas do Front {str(datetime.now().month).zfill(2)}-{datetime.now().year}.xlsx', index=False)

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
        teste_conciliacao = TRATA_CONCILIACAO(self.conciliacao, self.recebimentos, self.desconto_inadimplencia)
        conciliacao_tratado = teste_conciliacao.trata_conciliacao()

        # Certifica que todos os contratos no Credbase trabalhado são do mesmo tipo
        # cred['Codigo_Credbase'] = cred['Codigo_Credbase'].astype(str)

        conciliacao_tratado['CONTRATOS'] = conciliacao_tratado['CONTRATOS'].astype('float').astype('Int64')
        # conciliacao_tratado['CONTRATOS'] = conciliacao_tratado['CONTRATOS'].astype('Int64')

        print('DEBUG: Colunas da conciliação tratada')
        try:
            conciliacao_tratado.to_excel(os.path.join(self.caminho, f"Conciliacao_TESTE {str(datetime.now().month).zfill(2)}-{datetime.now().year}.xlsx"), index=False)
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
    
    def remove_peculios_indesejados(self, d8_unificado: pd.DataFrame, front: pd.DataFrame) -> pd.DataFrame:
        valores_peculio = [20, 40, 60, 80, 100, 120]

        # --- 1. IDENTIFICA DINAMICAMENTE A COLUNA DE VALOR NO D8 ---
        col_valor_d8 = None
        if 'VALOR_PARCELA' in d8_unificado.columns:
            col_valor_d8 = 'VALOR_PARCELA'
            convenio = 'GOV. TO'
        elif 'VLR.  ADE' in d8_unificado.columns:
            col_valor_d8 = 'VLR.  ADE'
            convenio = 'IGEPREV'
        else:
            print("Coluna de valor de parcela não encontrada no D8.")
            return d8_unificado

        # Garante tipo numérico para o filtro isin funcionar com precisão
        d8_valor_num = pd.to_numeric(d8_unificado[col_valor_d8], errors='coerce')
        front_valor_num = pd.to_numeric(front['Prestacao'], errors='coerce')

        # --- 2. GERAÇÃO DAS CHAVES COM SEQUENCIAL (CUMCOUNT) NO D8 ---
        mask_d8 = d8_valor_num.isin(valores_peculio)
        d8_unificado['CONTSE'] = ""
        d8_unificado['CONCAT CPF PARCELA'] = ""

        if mask_d8.any():
            # Sequencial ordenado por CPF e Valor (1, 2, 3...)
            contse_d8 = d8_unificado[mask_d8].groupby(['CPF', col_valor_d8]).count()
            d8_unificado.loc[mask_d8, 'CONTSE'] = contse_d8.astype(str)
            
            # Concatenação da chave
            d8_unificado.loc[mask_d8, 'CONCAT CPF PARCELA'] = (
                d8_unificado.loc[mask_d8, 'CPF'].astype(str) + "_" +
                d8_unificado.loc[mask_d8, col_valor_d8].astype(str) + "_" +
                d8_unificado.loc[mask_d8, 'CONTSE'].astype(str)
            )

        # --- 3. GERAÇÃO DAS CHAVES COM SEQUENCIAL (CUMCOUNT) NO FRONT ---
        mask_front = front_valor_num.isin(valores_peculio)
        front['CONTSE'] = ""
        front['CONCAT CPF PARCELA'] = ""

        if mask_front.any():
            seq_front = front[mask_front].groupby(['CPF', 'Prestacao']).count()
            front.loc[mask_front, 'CONTSE'] = seq_front.astype(str)
            
            front.loc[mask_front, 'CONCAT CPF PARCELA'] = (
                front.loc[mask_front, 'CPF'].astype(str) + "_" +
                front.loc[mask_front, 'Prestacao'].astype(str) + "_" +
                front.loc[mask_front, 'CONTSE'].astype(str)
            )

        # --- 4. FILTRAGEM: ELIMINAÇÃO DOS EXCEDENTES NO D8 ---
        # Conjunto de chaves válidas que existem no Front (usando set para busca instantânea O(1))
        chaves_validas_front = set(front.loc[mask_front, 'CONCAT CPF PARCELA'])

        # Condição para manter a linha no d8_unificado:
        # 1. OU a linha NÃO é pecúlio (~mask_d8) -> mantemos intacta
        # 2. OU a linha é pecúlio E sua chave com sequencial existe no Front
        linhas_para_manter = (~mask_d8) | (d8_unificado['CONCAT CPF PARCELA'].isin(chaves_validas_front))

        d8_filtrado = d8_unificado[linhas_para_manter].copy()

        # Opcional: se quiser limpar as colunas auxiliares antes de retornar
        # d8_filtrado.drop(columns=['CONTSE SEQ', 'CONCAT CPF PARCELA'], inplace=True)

        return d8_filtrado
        
    
    def unifica_d8_gov_to(self):
        d8_gov_to_unificado = self.d8_to

        if d8_gov_to_unificado['R$ PARCELA'].dtype != 'float64':
            d8_gov_to_unificado['R$ PARCELA'] = d8_gov_to_unificado['R$ PARCELA'].astype(str).str.replace("R$ ", "")
            d8_gov_to_unificado['R$ PARCELA'] = d8_gov_to_unificado['R$ PARCELA'].astype(str).str.replace(".", "")
            d8_gov_to_unificado['R$ PARCELA'] = d8_gov_to_unificado['R$ PARCELA'].astype(str).str.replace(",", ".")
            d8_gov_to_unificado['R$ PARCELA'] = pd.to_numeric(d8_gov_to_unificado['R$ PARCELA'], errors='coerce')

        # Testa d8 sem peculios errados
        # d8_govto_sem_peculios_errados = self.remove_peculios_indesejados(d8_gov_to_unificado, self.front_tratado)


        # d8_govto_sem_peculios_errados.to_excel(fr'{self.caminho}\D8 UNIFICADO DE GOV TO {str(datetime.now().month).zfill(2)}-{datetime.now().year}.xlsx', index=False)
        d8_gov_to_unificado.to_excel(fr'{self.caminho}\D8 UNIFICADO DE GOV TO {str(datetime.now().month).zfill(2)}-{datetime.now().year}.xlsx', index=False)

        return d8_gov_to_unificado        

    def unifica_d8_igeprev(self, arquivo):
        d8_igeprev_unificado = arquivo.copy()

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
        # d8_igeprev_sem_peculios_errados = self.remove_peculios_indesejados(d8_igeprev_unificado, self.front_tratado)

        # Transforma  em excel
        d8_igeprev_unificado.to_excel(fr'{self.caminho}\D8 UNIFICADO DE IGEPREV {str(datetime.now().month).zfill(2)}-{datetime.now().year}.xlsx', index=False)

        return d8_igeprev_unificado
 
    def d8_com_prazo(self):
        # d8_unificado_govt_to = self.unifica_d8_gov_to()
        d8_unificado_igeprev = self.unifica_d8_igeprev(self.d8_igeprev)
        recusados_igeprev = self.unifica_d8_igeprev(self.recusados_igeprev) # -> Vai fazer o mesmo tratamento que é feito no

        # Separar prazo de d8 gov to
        # d8_govto_prazo = d8_unificado_govt_to[(d8_unificado_govt_to['PARCELA'].str.contains('/')) & (~d8_unificado_govt_to['RUBRICA'].isin(['3620_2023', '3620_2024', '3620_2025']))]

        # Separar prazo de d8 igeprev
        d8_igeprev_prazo = d8_unificado_igeprev[~d8_unificado_igeprev['PRZ.'].isin([1, '1','Indeter.'])]
        d8_igeprev_prazo.to_excel(fr'{self.caminho}\D8 UNIFICADO DE IGEPREV COM PRAZO {str(datetime.now().month).zfill(2)}-{datetime.now().year}.xlsx', index=False)

        # TRATAMENTO DO RECUSADO
        # 1. Filtra os rejeitados em folha e extrai a lista/conjunto de ADEs únicos
        ades_rejeitados = set(
            recusados_igeprev.loc[recusados_igeprev['SIT. DA  PARCELA'] == 'Rejeitada Folha', 'ADE']
            .dropna()
            .astype(str)
        )

        # 2. Garante o tipo string no d8 para evitar falha de casamento (ex: int vs str com zeros)
        d8_igeprev_prazo['ADE'] = d8_igeprev_prazo['ADE'].astype(str)

        # 3. Remove diretamente quem está no conjunto de rejeitados
        d8_igeprev_prazo = d8_igeprev_prazo[~d8_igeprev_prazo['ADE'].isin(ades_rejeitados)].copy()

        d8_igeprev_peculios_tratados = self.remove_peculios_indesejados(d8_igeprev_prazo, self.front_tratado)

        # d8_govto_prazo.to_excel(fr'{self.caminho}\D8 UNIFICADO DE GOV TO COM PRAZO {str(datetime.now().month).zfill(2)}-{datetime.now().year}.xlsx', index=False)

        # return d8_govto_prazo, d8_igeprev_prazo
        return d8_igeprev_peculios_tratados
    
    def averbados_com_prazo(self):
        averbados_gov_to = self.averbados_to
        d8_unificado_govt_to = self.unifica_d8_gov_to()

        # Adiciona ponto e traço nos CPFs do arquivo de averbado
        cpf_tratado = averbados_gov_to['CPF'].astype(str).str.zfill(11).str.replace(r'(\d{3})(\d{3})(\d{3})(\d{2})',  r'\1.\2.\3-\4', regex=True)
        averbados_gov_to['CPF'] = cpf_tratado

        # Separar apenas os prazos de gov_to
        if averbados_gov_to['VALOR_PARCELA'].dtype != "float64":
            averbados_gov_to['VALOR_PARCELA'] = averbados_gov_to['VALOR_PARCELA'].astype(str).str.replace(".", "")
            averbados_gov_to['VALOR_PARCELA'] = averbados_gov_to['VALOR_PARCELA'].astype(str).str.replace(",", ".")
            averbados_gov_to['VALOR_PARCELA'] = pd.to_numeric(averbados_gov_to['VALOR_PARCELA'], errors='coerce')

        averbados_gov_to = averbados_gov_to[averbados_gov_to['VALOR_PARCELA'] >= 20]

        # --------------------------------------------- TESTE DA ABA DE RECUSADOS ---------------------------------------------
        # ADFs para remover do arquivo de averbado
        d8_unificado_remocoes = d8_unificado_govt_to[~d8_unificado_govt_to['MOTIVO'].str.contains('CORTE PARCIAL')].copy()
        # Vamos criar uma coluna gêmea, porque por algum motivo usar a mesma coluna no .set_index('ADF')['ADF'] não retorna a coluna indicada
        d8_unificado_remocoes['ADF_PARA_REMOVER'] = d8_unificado_remocoes['ADF']
        # Filtra mantendo apenas os CODIGOADF que NÃO estão na coluna 'ADF' do d8_unificado_remocoes
        averbados_gov_to_teste_removidos = averbados_gov_to[~averbados_gov_to['CODIGOADF'].isin(d8_unificado_remocoes['ADF'])].copy()
        # Substituímos os valores integrais pelos parciais
        d8_recusados_parcialmente = d8_unificado_govt_to[d8_unificado_govt_to['MOTIVO'].str.contains('CORTE PARCIAL', na=False)]
        padrao_regex = r'Valor\s*Corte\s*:\s*([\d.,]+)'
        # Criamos a nova coluna extraindo o padrão da coluna MOTIVO
        d8_recusados_parcialmente['VALOR_DO_CORTE'] = d8_recusados_parcialmente['MOTIVO'].str.extract(padrao_regex)
        if d8_recusados_parcialmente['VALOR_DO_CORTE'].dtype != 'float64':
            d8_recusados_parcialmente['VALOR_DO_CORTE'] = d8_recusados_parcialmente['VALOR_DO_CORTE'].astype(str).str.replace(".", "").str.replace(",", ".")
            d8_recusados_parcialmente['VALOR_DO_CORTE'] = pd.to_numeric(d8_recusados_parcialmente['VALOR_DO_CORTE'], errors='coerce')
        # Aplica os valores parciais de volta no averbados sem as parcelas removidas
        # 1. Criamos o dicionário de mapeamento direto (ADF -> VALOR_DO_CORTE)
        # Tiramos duplicados do set_index para garantir que o mapeamento seja único e limpo
        mapa_cortes = d8_recusados_parcialmente.drop_duplicates(subset=['ADF']).set_index('ADF')['VALOR_DO_CORTE']

        # 2. Criamos uma máscara booleana para identificar quais linhas do averbado precisam sofrer alteração
        linhas_para_atualizar = averbados_gov_to_teste_removidos['CODIGOADF'].isin(mapa_cortes.index)

        # 3. Atualizamos exclusivamente essas linhas usando o .map() apenas nelas
        averbados_gov_to_teste_removidos.loc[linhas_para_atualizar, 'VALOR_PARCELA'] = (
            averbados_gov_to_teste_removidos.loc[linhas_para_atualizar, 'CODIGOADF'].map(mapa_cortes)
        )

        averbados_gov_to_teste_removidos.to_excel(f'{self.caminho}\TESTE AVERBADO COM PRAZO SEM OS CASOS REMOVIDOS E COM AS PARCELAS PARCIAIS.xlsx', index=False)

        # CASO A IDEIA DE USAR VALORES PARCIAIS NÃO VÁ PARA FRENTE, É SÓ EU COMENTAR ESSA LINHA ABAIXO
        averbados_gov_to = averbados_gov_to_teste_removidos.copy()

        # Status ADF
        averbados_gov_to = averbados_gov_to[averbados_gov_to['STATUS_ADF'].isin(['CONSOLIDADO', 'INSERIDO', 'AGUARDANDO PORTABILIDADE', 'REFINANCIADO', 'COMPRADO', 'PRÉ REFINANCIADO'])]

        # PRAZO
        averbados_gov_to = averbados_gov_to[~averbados_gov_to['PRAZO'].isin(['INDETERMINADO'])]

        # SEM PECULIOS
        averbados_gov_to_sem_peculios = self.remove_peculios_indesejados(averbados_gov_to, self.front_tratado)
        averbados_gov_to = averbados_gov_to_sem_peculios.copy()

        
        # RUBRICA_DESCRICAO
        averbados_gov_to = averbados_gov_to[~averbados_gov_to['RUBRICA_DESCRICAO'].str.contains('Mensalidade')]

        # RUBRICA_CODIGO
        averbados_gov_to = averbados_gov_to[~averbados_gov_to['RUBRICA_CODIGO'].str.contains('3620')]

        # Separar prazo de averbados gov to
        try:
            averbados_gov_to.to_excel(fr'{self.caminho}\AVERBADOS DE GOV TO COM PRAZO {str(datetime.now().month).zfill(2)}-{datetime.now().year}.xlsx', index=False)
            print(f'AVERBADOS DE GOV TO COM PRAZO salvo com sucesso!')
        except Exception as e:
            print(f'Não deu para salvar AVERBADOS DE GOV TO COM PRAZO')

        return averbados_gov_to

    def front_com_d8(self):
        front_tratado = self.front_tratado
        # d8_govto_prazo, d8_igeprev_prazo = self.d8_com_prazo()
        d8_igeprev_prazo = self.d8_com_prazo()
        govto_prazo = self.averbados_com_prazo()

        gov_to_separado = self.unifica_gov_to_averbados()

        # Criar colunas no front
        front_tratado['SOMASE D8 GOV TO'] = ''
        front_tratado['SOMASE IGEPREV'] = ''
        front_tratado['SOMAS DE D8'] = ''
        front_tratado['SOMASE LOCAL'] = ''
        front_tratado['DIFF D8'] = ''
        
        # Vamos reordenar o arquivo para HP ficar em primeiro
        front_tratado = front_tratado.sort_values(by=['Consignataria'], ascending=False)

        # Somase de d8 gov to
        somase_govto_averbado = govto_prazo.groupby('CPF')['VALOR_PARCELA'].sum()
        front_tratado['SOMASE D8 GOV TO'] = front_tratado['CPF'].map(somase_govto_averbado).fillna(0)
        

        # Somase de d8 igeprev
        somase_d8_igeprev = d8_igeprev_prazo.groupby('CPF')['VLR.  ADE'].sum()
        front_tratado['SOMASE IGEPREV'] = front_tratado['CPF'].map(somase_d8_igeprev).fillna(0)

        # Soma dos d8
        front_tratado['SOMAS DE D8'] = front_tratado['SOMASE D8 GOV TO'] + front_tratado['SOMASE IGEPREV']


        # SOMASE LOCAL
        front_tratado['SOMASE LOCAL'] = front_tratado.groupby("CPF")['Valor a lançar'].transform('sum')

        # Diff entre somas dos SOMASES de D8 e SOMASE LOCAL
        front_tratado['DIFF D8'] = front_tratado['SOMASE LOCAL'] - front_tratado['SOMAS DE D8']
        front_tratado['DIFF D8'] = front_tratado['DIFF D8'].round(2)

        # Ordernar CPF do menor para o maior
        front_tratado = front_tratado(by='CPF', ascending=False)

        # Marcar o que é Cartão de crédito
        REGEX_CARTAO_SIMPLES = 'Cartão de Crédito|CARTAO DE CREDITO|CARTÃO DE CRÉDITO|CARTÃO CONSIGNADO|CARTAO CONSIGNADO|CARTAO CONSIGNAD'

        # SOMASES de cartão
        filtro_cartao = front_tratado[front_tratado['Tipo Operacao'].str.contains(REGEX_CARTAO_SIMPLES)]

        somas_por_cpf = filtro_cartao.groupy('CPF')['Valor a lançar'].sum()

        front_tratado['SOMASES CART'] = front_tratado['CPF'].map(somas_por_cpf).fillna(0)

        # SOMASE CART TOCANTINS
        # Filtra e agrupa gerando a Series de soma por CPF
        soma_cartao = (
            gov_to_separado[gov_to_separado['RUBRICA'] == "Cartão crédito"]
            .groupby('CPF')['VALOR_PARCELA']
            .sum()
        )

        # Traz o valor somado para o front_tratado (CPFs sem lançamento viram 0.0)
        front_tratado['SOMASE CART GOV TO'] = front_tratado['CPF'].map(soma_cartao).fillna(0.0)

        # Verificar se o SOMASES CART é igual ao SOMASES CART ANDAMENTO TOCANTINS
        somases = pd.to_numeric(front_tratado['SOMASES CART'], errors='coerce').fillna(0)
        somase_govto = pd.to_numeric(front_tratado['SOMASE CART GOV TO'], errors='coerce').fillna(0)
        condicao = (somases != 0) & (somases == somase_govto)
        front_tratado['VALID'] = np.where(condicao, 'FALSO', 'VERDADEIRO')

        # Os que deram FALSO na coluna VALID, será feito uma comparação entre SOMASES CART e DIFF D8
        lancar_falso = front_tratado['VALID'] == 'FALSO'
        front_tratado.loc[lancar_falso, 'Lançar'] = np.maximum(front_tratado.loc[lancar_falso, 'SOMASES CART'], front_tratado.loc[lancar_falso, 'DIFF D8'])

        # Vamos separar CPF e Lançar dos que deram FALSO
        # 2. Isola o de-para de CPF -> Lançar dos casos FALSO
        # .drop_duplicates(subset='CPF') evita o InvalidIndexError caso o CPF apareça em mais de uma linha
        filtro_falso = front_tratado['VALID'] == 'FALSO'
        mapa_falso = (
            front_tratado.loc[filtro_falso, ['CPF', 'Lançar']]
            .dropna(subset=['Lançar'])
            .drop_duplicates(subset='CPF', keep='first')
            .set_index('CPF')['Lançar']
        )

        # 3. Mapeia o valor de lançamento do CPF
        valor_falso_por_cpf = front_tratado['CPF'].map(mapa_falso)

        # 4. Aplica a hierarquia de regras via np.select (vetorizado, rápido e limpo)
        condicoes = [
            valor_falso_por_cpf.notna(),           # 1ª prioridade: CPF tinha valor de FALSO mapeado
            front_tratado['DIFF D8'] > 0          # 2ª prioridade: DIFF D8 positivo
        ]

        escolhas = [
            valor_falso_por_cpf,                  # Assume o valor calculado do FALSO
            front_tratado['DIFF D8']              # Assume o DIFF D8
        ]

        # Caso nenhuma das duas seja atendida (ex: DIFF D8 <= 0), o valor default será 0.0
        front_tratado['Lançar'] = np.select(condicoes, escolhas, default=0.0)
        
        # Contse seq no front para pegar só os primeiros
        front_tratado['Contse seq'] = front_tratado.groupby('CPF').cumcount() + 1

        front_tratado.to_excel(fr'{self.caminho}\FRONT MEIO TRATADO {str(datetime.now().month).zfill(2)}-{datetime.now().year}.xlsx', index=False)


        # Vamos salvar e retornar somente o que é maior que 0
        front_trabalhado = front_tratado[(front_tratado['Lançar'] > 0) & (front_tratado['Contse seq'] == 1)]
        
        front_trabalhado.to_excel(fr'{self.caminho}\FRONT TOTALMENTE TRABALHADO {str(datetime.now().month).zfill(2)}-{datetime.now().year}.xlsx', index=False)

        return front_tratado, front_trabalhado # [front_trabalhado['Contse seq'] == 1]

    def front_final(self):

        front_tratado, front_para_lancamento = self.front_com_d8()
        # ==============================================================================
        # 1. TRATAMENTO DOS PECÚLIOS NO "FRONT TRATADO"
        # ==============================================================================
        # Regex consolidada para identificar variações de cartão
        REGEX_CARTAO = r'Cartão de Crédito|CARTAO DE CREDITO|CARTÃO DE CRÉDITO|CARTÃO CONSIGNADO|CARTAO CONSIGNADO|CARTAO CONSIGNAD'

        # Normaliza colunas textuais para evitar falhas com espaços extras
        tipo_op = front_tratado['Tipo Operacao'].astype(str).str.strip()
        consignataria = front_tratado['Consignatária'].astype(str).str.strip()

        # Máscara dos critérios: Cartão E HOJE PREVIDÊNCIA PRIVADA
        mascara_peculio = (
            tipo_op.str.contains(REGEX_CARTAO, case=False, na=False, regex=True) & 
            (consignataria.str.upper() == "HOJE PREVIDÊNCIA PRIVADA")
        )

        # Conforme solicitado pela sua colega: cria a coluna nova com esses CPFs (demais ficam vazios)
        front_tratado['CPF_PECULIO'] = np.where(mascara_peculio, front_tratado['CPF'].astype(str).str.strip(), np.nan)

        # CONT.SE por CPF: conta quantas vezes cada CPF aparece como pecúlio válido no front_tratado
        contagem_peculios_por_cpf = (
            front_tratado.dropna(subset=['CPF_PECULIO'])
            .groupby('CPF_PECULIO')
            .size()
        )


        # ==============================================================================
        # 2. SEPARAÇÃO DO "FRONT PARA LANÇAMENTO"
        # ==============================================================================
        # Normaliza a coluna 'Contse seq' (para aceitar 1 numérico ou '1' string)
        mask_seq_1 = front_tratado['Contse seq'].astype(str).str.strip() == '1'

        # Cria a nova base isolada com .copy() para evitar SettingWithCopyWarning
        front_para_lancamento = front_tratado[mask_seq_1].copy()


        # ==============================================================================
        # 3. CRIAÇÃO DAS COLUNAS DE CONT.SE, VALOR DE PECÚLIO E SOMA NO LANÇAR
        # ==============================================================================
        # Garante o CPF como string limpa para casamento de chaves
        cpf_lancamento = front_para_lancamento['CPF'].astype(str).str.strip()

        # CONT.SE dos CPFs elegíveis mapeados do front_tratado (quem não tiver vira 0)
        front_para_lancamento['QTD_PECULIO'] = cpf_lancamento.map(contagem_peculios_por_cpf).fillna(0).astype(int)

        # Multiplica a quantidade por 20 (ex: 3 contratos = R$ 60,00)
        front_para_lancamento['VALOR_PECULIO'] = front_para_lancamento['QTD_PECULIO'] * 20.0

        # Garante que a coluna 'Lançar' seja numérica
        front_para_lancamento['Lançar'] = pd.to_numeric(front_para_lancamento['Lançar'], errors='coerce').fillna(0.0)

        # Soma o valor do pecúlio com o que já existia na coluna 'Lançar'
        front_para_lancamento['Lançar'] = front_para_lancamento['Lançar'] + front_para_lancamento['VALOR_PECULIO']


        # ==============================================================================
        # 4. EXPORTAÇÃO PARA DUAS ABAS NO MESMO EXCEL (SE APLICÁVEL)
        # ==============================================================================
        # with pd.ExcelWriter('Resultado_Final.xlsx', engine='openpyxl') as writer:
        #     front_tratado.to_excel(writer, sheet_name='Front Tratado', index=False)
        #     front_para_lancamento.to_excel(writer, sheet_name='Front para Lançamento', index=False)

        return front_para_lancamento

    def unifica_gov_to_averbados(self):
        gov_to_averbado_unificado = self.averbados_to

        if gov_to_averbado_unificado['VALOR_PARCELA'].dtype != "float64":
            gov_to_averbado_unificado['VALOR_PARCELA'] = gov_to_averbado_unificado['VALOR_PARCELA'].astype(str).str.replace(".", "")
            gov_to_averbado_unificado['VALOR_PARCELA'] = gov_to_averbado_unificado['VALOR_PARCELA'].astype(str).str.replace(",", ".")
            gov_to_averbado_unificado['VALOR_PARCELA'] = pd.to_numeric(gov_to_averbado_unificado['VALOR_PARCELA'], errors='coerce')

        # Status ADF
        gov_to_averbado_unificado = gov_to_averbado_unificado[gov_to_averbado_unificado['STATUS_ADF'].isin(['CONSOLIDADO', 'INSERIDO'])]

        # PRAZo
        gov_to_averbado_unificado = gov_to_averbado_unificado[gov_to_averbado_unificado['PRAZO'].isin(['INDETERMINADO'])]

        # RUBRICA_CODIGO
        gov_to_averbado_unificado = gov_to_averbado_unificado[gov_to_averbado_unificado['RUBRICA_CODIGO'].str.contains('CC|CCI|CCB')]


        # Vamos gerar o arquivo para averiguar melhor
        gov_to_averbado_unificado.to_excel(fr'{self.caminho}\AVERBADOS DE GOV TO UNIFICADOS {str(datetime.now().month).zfill(2)}-{datetime.now().year}.xlsx', index=False)

        # 1. Resolver os casos de valores iguais (remover duplicados exatos)
        # Isso remove as linhas onde MATRICULA, Consignataria e VALOR_PARCELA são idênticos,
        # mantendo apenas a primeira ocorrência.
        total_duplicados_anterior = gov_to_averbado_unificado.duplicated(subset=['MATRICULA', 'Consignataria', 'VALOR_PARCELA']).sum()

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

        # Mapeamento novo
        mapeamento = ['MATRICULA', 'CPF', 'NOME', 'PRAZO', 'VALOR_PARCELA', 'RUBRICA_DESCRICAO', 'RUBRICA_CODIGO', 'Convenio', 'Consignataria']

        gov_to_remapeado = gov_to_averbado_unificado_resultado[mapeamento]

        gov_to_cartao_sem_peculios = self.remove_peculios_indesejados(gov_to_remapeado, self.front_tratado)

        return gov_to_cartao_sem_peculios

    def unifica_igeprev_averbados(self):
        # Unifica averbações de IGEPREV
        igeprev_averbado_unificado = self.averbados_igeprev
        igeprev_averbado_unificado.rename(columns={"SERVIDOR": "SERVIDOR + MATRICULA"}, inplace=True)

        igeprev_averbado_unificado.insert(1, "MATRICULA", "", True)
        igeprev_averbado_unificado.insert(2, "SERVIDOR", "", True)
        igeprev_averbado_unificado.insert(7, "PRAZO", 1, True)
        igeprev_averbado_unificado.insert(8, "RUBRICA_CODIGO", 1, True)

        # Divide a coluna de SERVIDOR que vem matricula e o nome dos clientes, em duas colunas distintas
        igeprev_averbado_unificado[["MATRICULA", "SERVIDOR"]] = igeprev_averbado_unificado['SERVIDOR + MATRICULA'].str.split(" - ", n=1, expand=True)

        igeprev_averbado_unificado.to_excel(fr'{self.caminho}\IGEPREV AVERBADO TESTE {str(datetime.now().month).zfill(2)}-{datetime.now().year}.xlsx', index=False)

        # Renomeia as colunas de GOV TO
        igeprev_averbado_unificado.rename(columns={'SERVIDOR': 'NOME', 'ÓRGÃO': 'Convenio', 'SERVIÇO': 'RUBRICA_DESCRICAO', 'VLR RESERV.': 'VALOR_PARCELA'}, inplace=True)
        
        # Mapeamento novo
        mapeamento = ['MATRICULA', 'CPF', 'NOME', 'PRAZO', 'VALOR_PARCELA', 'RUBRICA_DESCRICAO', 'RUBRICA_CODIGO', 'Convenio', 'Consignataria']


        igeprev_remapeado = igeprev_averbado_unificado[mapeamento]
        if igeprev_remapeado['VALOR_PARCELA'].dtype != 'float64':
            igeprev_remapeado['VALOR_PARCELA'] = igeprev_remapeado['VALOR_PARCELA'].str.replace(".", '')
            igeprev_remapeado['VALOR_PARCELA'] = igeprev_remapeado['VALOR_PARCELA'].str.replace(",", '.')
            igeprev_remapeado['VALOR_PARCELA'] = pd.to_numeric(igeprev_remapeado['VALOR_PARCELA'], errors='coerce')

        igeprev_remapeado = igeprev_remapeado[igeprev_remapeado['VALOR_PARCELA'] >= 20]

        return igeprev_remapeado

    def unifica_averbados(self):
        gov_to_averbado_unificado = self.averbados_to
        '''gov_to_capital_averbado = averbado_gov_to_capital
        gov_to_ciasprev_averbado = averbado_gov_to_ciasprev
        gov_to_hp_averbado = averbado_gov_to_hp
        gov_to_capital_averbado['Consignataria'] = 'CAPITAL'
        gov_to_ciasprev_averbado['Consignataria'] = 'CIASPREV'
        gov_to_hp_averbado['Consignataria'] = "HP"'''

        front_trabalhado = self.front_final()

        averbado_separado_gov_to = self.unifica_gov_to_averbados()
        averbado_separado_igeprev = self.unifica_igeprev_averbados()

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

        # RUBRICA_CODIGO
        gov_to_averbado_unificado = gov_to_averbado_unificado[gov_to_averbado_unificado['RUBRICA_CODIGO'].str.contains('CC|CCI|CCB')]


        # Vamos gerar o arquivo para averiguar melhor
        gov_to_averbado_unificado.to_excel(fr'{self.caminho}\AVERBADOS DE GOV TO UNIFICADOS {str(datetime.now().month).zfill(2)}-{datetime.now().year}.xlsx', index=False)

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

        igeprev_averbado_unificado.to_excel(fr'{self.caminho}\IGEPREV AVERBADO TESTE {str(datetime.now().month).zfill(2)}-{datetime.now().year}.xlsx', index=False)

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

        igeprev_remapeado = igeprev_remapeado[igeprev_remapeado['VALOR_PARCELA'] >= 20]
        
        # print(f'COLUNAS DE GOV TO REMAPEADO {gov_to_remapeado.columns}\n')
        # print(f'COLUNAS DE IGEPREV REMAPEADO {igeprev_remapeado.columns}')
        to_igeprev_unificado = pd.concat([averbado_separado_gov_to, averbado_separado_igeprev], ignore_index=True)
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

'''teste = IGEPREV_GOVTO(front, funcao, conciliacao_df, recebimentos_df)

resultado = teste.unifica_averbados()'''



    