import os
import sys
import pandas as pd
import xlrd
import openpyxl
from python.ESTEIRAS import load_esteiras
from python.trata_conciliacao import TRATA_CONCILIACAO
from python.Andamento import ANDAMENTO
from datetime import datetime
import numpy as np
import xlsxwriter

rejeitados = ['/']

class CODATA:
# Dentro de python/Codata.py

    def __init__(self, portal_file_list, convenio, front, consignataria, conciliacao, caminho, kobraki=None, funcao=None, andamento_list=None, orbital=None):

        # A API FastAPI já leu, unificou e tratou a codificação. 
        # Aqui, apenas atribuímos o DataFrame ou inicializamos como vazio se for None.
        self.caminho = caminho
        
        # Averbados (portal_file_list)
        self.averbados = portal_file_list if portal_file_list is not None else pd.DataFrame()
        
        # Front
        self.front = front if front is not None else pd.DataFrame()

        # Funcao
        self.funcao = funcao if funcao is not None else None

        # Andamento
        self.andamento = andamento_list if andamento_list is not None else None

        self.convenio = convenio
        self.consignataria = consignataria

        # Conciliação - CORREÇÃO: Trata None para evitar pd.read_excel(None, ...)
        self.conciliacao = conciliacao if conciliacao is not None else pd.DataFrame()
        self.conciliacao.rename(columns={'TIPO OPERACAO': 'PRODUTO', 'TIPO OPERAÇÃO': 'PRODUTO', 'PRODUTOS PELO D8': 'PRODUTO'}, inplace=True)

        # Kobrakai
        self.kobraki = kobraki

        # Orbital
        self.orbital = orbital if orbital is not None else None

        # Chama a primeira função da cadeia de processamento
        front_trabalhado = self.tratamento_front()
        self.averbados_func(front_trabalhado)
        # self.tratamento_funcao()

    def unifica_front_funcao(self):
        front = self.front
        funcao = self.funcao

        print(f"colunas de funcao: {funcao.columns}")

        contrato_front = front['Contrato']
        ccb_tratado = front['CCB'].astype(str).str.slice(0, 9)
        ccb_tratado = ccb_tratado.astype('int64')

        # Verifica se o que é andamento no front está no função, se tiver transforma em integrado
        contrato_funcao = funcao['NR_PROP']
        front.loc[front['Contrato'].isin(contrato_funcao) & (front['Esteira'].str.contains('ANDAMENTO')), 'Esteira'] = 'INTEGRADO'

        # Tira os contratos do Front que já existem no Função
        funcao = funcao[(~funcao['NR_PROP'].isin(contrato_front)) & (~funcao["ORIGEM_3"].str.contains("IV PROMOTORA"))].copy()

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
            'ORIGEM_2': 'Consignataria',
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
        # Coloca SIM onde é orbital no função
        front_unif.loc[front_unif['Tipo Operacao'].isin(['CARTÃO PLÁSTICO', 'CARTÃO PLÁSTICO - RE']), 'Orbital'] = 'SIM'

        # Preenche INSPFEM ONDE DEVE
        front_unif.loc[front_unif['Convenio'].isin(['INSPFEM']), 'Consignataria'] = 'INSPFEM - CARD' 

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

        orbital = self.orbital

        # Insere as colunas vazias necessárias
        front_consig.insert(21, 'Saldo', '', True)
        front_consig.insert(22, 'Valor a lançar', '', True)
        front_consig.insert(23, 'PRAZO', '', True)
        front_consig.insert(24, 'OBS', '', True)

        # Aqui foi a resolução de um problema que me consumiu muitas horas, entender porque algumas parcelas de orbital no front
        # e no orbital trabalhado estavam vindo com virgula, e outros sem. Acontece que o Prestacao estava em string, enquanto trazia os valores de orbital em float.
        # Quando puxava  o valor de orbital para o front e fazia o tratamento de transformação de string para float, ele tirava o ponto das parcelas tratadas que vieram
        # de orbital, enquanto corrigia os valores da Prestacao no front... Resumindo, para corrigir isso, tratei os valores de Prestacao no front, antes de juntar
        # com orbital
        if front_consig['Prestacao'].dtype != "float64":
            front_consig['Prestacao'] = front_consig['Prestacao'].str.replace('.', '', regex=False)
            front_consig['Prestacao'] = front_consig['Prestacao'].str.replace(',', '.', regex=False)
            front_consig['Prestacao'] = pd.to_numeric(front_consig['Prestacao'], errors='coerce')

        # Esteiras
        esteiras_permitidas = load_esteiras()
        
        
        print(f'Esteiras Únicas do front: {front_consig["Esteira"].unique()}')

        # Vamos renomear a primeira coluna da conciliação
        conciliacao.rename(columns={conciliacao.columns[0]: 'CONTRATOS'}, inplace=True)
        # Converte para lista de colunas
        cols = list(conciliacao.columns)

        # Atualiza o DataFrame com novos nomes
        conciliacao.columns = cols
        conciliacao['CONTRATOS'] = conciliacao['CONTRATOS'].astype('float64')
        conciliacao['CONTRATOS'] = conciliacao['CONTRATOS'].astype('Int64')

        # Adiciona a coluna de tipo da Conciliação
        print(f'colunas de front consig: {front_consig.columns}')
        try:
            tipo_conci = front_consig['Contrato'].map(conciliacao.set_index('CONTRATOS')['PRODUTO'].to_dict())
        except Exception as e:
            print(f'Coluna PRODUTO não se encontra na conciliação. Erro: {e}')
            return False
        
        front_consig.insert(19, 'Tipo Conciliação', tipo_conci, True)


        # Adiciona só as esteiras que podem ser lançadas
        # --------------------------------------------- ORBITAL --------------------------------------------- #
        # --- ETAPA 1: Garantir que as chaves são do mesmo tipo (Texto) ---
        # Isso evita o erro clássico onde um lado é número e o outro é texto
        if orbital is not None:
            front_consig['Contrato'] = front_consig['Contrato'].astype(str).str.strip()
            # orbital.rename(columns={'id_contr_banco': 'Numero de Contrato'}, inplace=True)

            if orbital['VALID DESCONTO FINAL'].dtype != "float64":
                orbital['VALID DESCONTO FINAL'] = orbital['VALID DESCONTO FINAL'].astype(str).str.replace(".", "")
                orbital['VALID DESCONTO FINAL'] = orbital['VALID DESCONTO FINAL'].astype(str).str.replace(",", ".")
                orbital['VALID DESCONTO FINAL'] = pd.to_numeric(orbital['VALID DESCONTO FINAL'], errors='coerce')

            for col in orbital.columns:
                if "contrato" in col or "Contrato" in col:
                    orbital.rename(columns={col:"CONTRATO"}, inplace=True)
            orbital['CONTRATO'] = orbital['CONTRATO'].astype(str)

            # --- ETAPA 2: Criar o "Dicionário de Busca" da Orbital ---
            # Transforma a Orbital em uma série onde Índice = Contrato e Valor = Desconto
            mapa_orbital = orbital.set_index('CONTRATO')['VALID DESCONTO FINAL']
            # --- ETAPA 3: Definir quem vai ser alterado ---
            filtro_esteira = front_consig['Esteira'] == '99 CARTAO UTILIZADO'

            # --- ETAPA 4: Fazer a mágica (Buscar valores) ---
            # .loc[filtro, coluna] -> Seleciona só as linhas da esteira certa
            # .map(mapa_orbital)   -> Faz o "PROCV" buscando no dicionário criado
            valores_encontrados = front_consig.loc[filtro_esteira, 'Contrato'].map(mapa_orbital)

            # --- ETAPA 5: Tratar quem não foi achado ---
            # Se o contrato não existe na Orbital, o map devolve NaN.
            # Usamos fillna(0) para trocar NaN por 0, conforme você pediu.
            valores_encontrados = valores_encontrados.fillna(0)

            # --- ETAPA 6: Gravar no DataFrame original ---
            valores_encontrados_str = valores_encontrados # .astype(str)
            front_consig.loc[filtro_esteira, 'Prestacao'] = valores_encontrados_str 

        front_consig = front_consig[front_consig['Esteira'].isin(esteiras_permitidas)].copy()


        # ------------------------------------ ESTEIRAS REMOVIDAS ------------------------------------- #
        front_consig_esteiras_removidas = front_consig[~front_consig['Esteira'].isin(esteiras_permitidas)].copy()
        try:
            front_consig_esteiras_removidas.to_excel(os.path.join(self.caminho, f'FRONT ESTEIRAS REMOVIDAS GOV PB {self.consignataria}.xlsx'), index=False)
        except Exception as e:
            print(f"Erro ao salvar o arquivo de esteiras removidas: {e}")

        # Adiciona só as esteiras que podem ser lançadas
        front_consig_esteiras = front_consig[front_consig['Esteira'].isin(esteiras_permitidas)].copy()

        # Trata coluna de Tipo da Conciliação
        front_consig_esteiras.loc[front_consig_esteiras['Tipo Conciliação'].isin([np.nan, '', ' - ']), 'Tipo Conciliação'] = front_consig_esteiras['Tipo Operacao']

        # -------------------------------- MARCAR TUDO QUE NÃO LANÇA ---------------------------------- #
        # Marca saldo positivo
        front_consig_validado_termino = self.validacao_termino_front(front_consig_esteiras)
        front_consig_validado_termino.loc[front_consig_validado_termino['Saldo'] > -0.01, 'OBS'] = 'NÃO LANÇAR - SALDO POSITIVO'

        # Marca o que é ação judicial
        front_consig_validado_termino['Acao Judicial'] = front_consig_validado_termino['Acao Judicial'].replace({'SIM': 1, 'NAO': 0})
        front_consig_validado_termino.loc[front_consig_validado_termino['Acao Judicial'] == 1, 'OBS'] = 'NÃO LANÇAR - AÇÃO JUDICIAL'

        # Marca o que é Óbito
        # front_consig_validado_termino.loc[front_consig_validado_termino['Obito'] == 1, 'OBS'] = 'NÃO LANÇAR - ÓBITO'
 
        # Marca tudo que é orbital
        front_consig_validado_termino.loc[(front_consig_validado_termino['Orbital'].str.contains('SIM', na=False) & (front_consig_validado_termino['OBS'] == '')), 'OBS'] = 'NÃO LANÇAR - ORBITAL'

        # Marcar o que não é cartão
        '''if self.consignataria == 'CAPITAL CONSIG':
            front_consig_validado_termino.loc[(~front_consig_validado_termino['Novo Tipo Operacao'].str.contains('Cartão de Crédito|CARTAO DE CREDITO', na=False)), 'OBS'] = 'NÃO LANÇAR - NÃO CARTÃO'
        elif self.consignataria == 'INSPFEM':
            front_consig_validado_termino.loc[(~front_consig_validado_termino['Consignataria'].str.contains('INSPFEM - CARD', na=False) & (front_consig_validado_termino['OBS'] == '')), 'OBS'] = "NÃO LANÇAR - NÃO INSPFEM"'''

        # Marca consignatária errada
        if self.consignataria == 'CAPITAL CONSIG':
            front_consig_validado_termino.loc[(front_consig_validado_termino['Consignataria'].str.contains('INSPFEM', na=False) & (front_consig_validado_termino['OBS'] == '')), 'OBS'] = 'NÃO LANÇAR - INSPFEM'
        elif self.consignataria == 'INSPFEM':
            front_consig_validado_termino.loc[(~front_consig_validado_termino['Consignataria'].str.contains('INSPFEM', na=False) & (front_consig_validado_termino['OBS'] == '')), 'OBS'] = 'NÃO LANÇAR - CAPITAL'

        # Marcar liquidados em StatusContrato
        if self.consignataria == 'CAPITAL CONSIG':
            front_consig_validado_termino.loc[(front_consig_validado_termino['Status'].str.contains('Liquidado|CANCELADO', na=False)), 'OBS'] = 'NÃO LANÇAR - LIQUIDADO'
        elif self.consignataria == 'INSPFEM':
            front_consig_validado_termino.loc[(front_consig_validado_termino['Status'].str.contains('Liquidado|CANCELADO', na=False)), 'OBS'] = 'NÃO LANÇAR - LIQUIDADO'

        # Marca Prazo - Já está marcando "NÃO LANÇAR - PRAZO" dentro da função andamento_func_front
        if self.consignataria == 'CAPITAL CONSIG':
            objeto_andamento = ANDAMENTO(self.front, self.convenio, self.caminho, self.andamento, self.funcao)
            front_consig_validado_termino = objeto_andamento.andamento_func_front()

            front_com_prazo = front_consig_validado_termino[
            (front_consig_validado_termino['PRAZO'].notna()) & 
            (front_consig_validado_termino['PRAZO'] != '')
            ]

            front_consig_validado_termino = front_consig_validado_termino[(front_consig_validado_termino['PRAZO'].isna()) | (front_consig_validado_termino['PRAZO'] == '')]
            front_com_prazo.to_excel(fr'{self.caminho}\FRONT COM PRAZOS PORQUE EU SOU MUITO BURRO.xlsx', index=False)
            # front_consig_validado_termino.to_excel(fr'{self.caminho}\front_consig_validado_termino.xlsx', index=False)
            front_consig_validado_termino.insert(22, 'Novo Tipo Operacao', 'CARTAO DE CREDITO')
        else:
            front_consig_validado_termino = front_consig_validado_termino[front_consig_validado_termino['Consignataria'] == 'INSPFEM - CARD']
            front_consig_validado_termino.insert(22, 'Novo Tipo Operacao', 'CARTAO DE CREDITO')

        # Salva com os NÃO LANÇAR
        print(f"DEBUG: Tentando salvar FRONT SEMI TRABALHADO em: {self.caminho}")
        try:
            front_consig_validado_termino.to_excel(os.path.join(self.caminho, f"FRONT SEMI TRABALHADO {self.convenio}.xlsx"), index=False)
            print("DEBUG: Arquivo salvo com sucesso!")
        except Exception as e:
            print(f"DEBUG: ERRO AO SALVAR: {e}")

        # --------------------------------------------------------------------------------------------- #
        return front_consig_validado_termino
        
    def tratamento_front(self):
        front_consig = self.tratamento_front_preliminar()

        if front_consig is False:
            print("tratamento_front: O tratamento preliminar do front falhou. Verifique os erros anteriores.")
            return False

        if self.consignataria == 'CAPITAL CONSIG':
            # Se houver cartão de crédito no Tipo Operacao do Front, mas estiver diferente no 

            # Separa apenas o que retornou como "cartão de crédito" no tipo de conciliação
            front_consig_cartao_conciliacao = front_consig[front_consig['Novo Tipo Operacao'].str.contains('Cartão de Crédito|CARTAO DE CREDITO', na=False)].copy()

            front_consig_trabalhado = front_consig_cartao_conciliacao
        elif self.consignataria == 'INSPFEM':
            # Separa apenas o que retornou como "INSPFEM - CARD" no tipo de conciliação
            front_consig_cartao_conciliacao = front_consig[(front_consig['Consignataria'].str.contains('INSPFEM - CARD', na=False)) & (front_consig['OBS'] != 'NÃO LANÇAR - ORBITAL')].copy()
            front_consig_trabalhado = front_consig_cartao_conciliacao

        # ---------------------------------- TIRAR AÇÃO JUDICIAL DO FRONT ---------------------------------- #
        front_consig_trabalhado = front_consig_trabalhado.loc[front_consig_trabalhado['Acao Judicial'] != 1].copy()

        # ---------------------------------- TIRAR ÓBITO DO FRONT ---------------------------------- #
        # front_consig_trabalhado = front_consig_trabalhado.loc[front_consig_trabalhado['Obito'] != 1].copy()
        

        # ------------------------------------- ESCOLHE CONSIGNATÁRIA -------------------------------------- #
        if self.consignataria == 'CAPITAL CONSIG':
            front_consig_trabalhado = front_consig_trabalhado[~front_consig_trabalhado['Consignataria'].str.contains('INSPFEM', na=False)].copy()
        elif self.consignataria == 'INSPFEM':
            front_consig_trabalhado = front_consig_trabalhado[front_consig_trabalhado['Consignataria'].str.contains('INSPFEM', na=False)].copy()
        else:
            print('Consignatária inválida.')
            return
        
        # ------------------------------------ INSERE A COLUNA DE SALDO ------------------------------------- #

        front_consig_trabalhado.loc[front_consig_trabalhado['Saldo'] > -0.01, 'Valor a lançar'] = 0
        front_consig_trabalhado = front_consig_trabalhado[front_consig_trabalhado['Valor a lançar'] > 0].copy()

        # -------------------------------------- TIRA O PRAZO ----------------------------------------------- #
        front_consig_trabalhado = front_consig_trabalhado[~front_consig_trabalhado['OBS'].str.contains('NÃO LANÇAR - PRAZO', na=False)].copy()

        # ----------------------------------------- TIRA LIQUIDADOS ----------------------------------------- #
        front_consig_trabalhado = front_consig_trabalhado[~front_consig_trabalhado['OBS'].str.contains('NÃO LANÇAR - LIQUIDADO', na=False)].copy()

        print('DEBUG: Esteiras finais do front trabalhado')
        try:
            front_consig_trabalhado.to_excel(
                os.path.join(self.caminho, f"FRONT TRABALHADO {self.convenio} {self.consignataria}.xlsx"),
                index=False, 
            )
        except Exception as e:
            print(f"DEBUG: ERRO AO SALVAR FRONT TRABALHADO: {e}")

        return front_consig_trabalhado

    def orbital_tratado(self, orbital, front_para_separar):


        if orbital['VALID DESCONTO FINAL'].dtype != 'float64':
            orbital['VALID DESCONTO FINAL'] = orbital['VALID DESCONTO FINAL'].astype(str).str.replace(".", "")
            orbital['VALID DESCONTO FINAL'] = orbital['VALID DESCONTO FINAL'].astype(str).str.replace(",", ".")
            orbital['VALID DESCONTO FINAL'] = pd.to_numeric(orbital['VALID DESCONTO FINAL'], errors='coerce')
            

        orbital_preparado = orbital.loc[
            orbital['DESCRIÇÃO DO EMPREG'].str.contains('INSPFEM', case=False, na=False),
            ['CONTRATO', 'nome_mutuario', 'num_cpf_mutuario', 'VALID DESCONTO FINAL']
        ].copy()
        orbital_preparado.columns = ['Proposta', 'Cliente', 'CPF/CNPJ', 'VALOR DESCONTO']
        

        front_so_orbital = front_para_separar.loc[
            front_para_separar['OBS'] == 'NÃO LANÇAR - ORBITAL',
            ['Contrato', 'Nome', 'CPF', 'Prestacao']].copy()
        
        front_so_orbital.columns = ['Proposta', 'Cliente', 'CPF/CNPJ', 'VALOR DESCONTO']

        # front_so_orbital['Proposta'] = front_so_orbital['Proposta'].astype(str).str.strip()

        # front_so_orbital['VALOR DESCONTO'] = front_so_orbital['VALOR DESCONTO'].astype(str).str.replace('.', '', regex=False)
        if front_so_orbital['VALOR DESCONTO'].dtype != "float64":
            front_so_orbital['VALOR DESCONTO'] = front_so_orbital['VALOR DESCONTO'].astype(str).str.replace('.', '', regex=False)
            front_so_orbital['VALOR DESCONTO'] = front_so_orbital['VALOR DESCONTO'].astype(str).str.replace(',', '.', regex=False)
            front_so_orbital['VALOR DESCONTO'] = pd.to_numeric(front_so_orbital['VALOR DESCONTO'], errors='coerce')

        orbital_final = pd.concat([front_so_orbital, orbital_preparado])

        orbital_final = orbital_final.drop_duplicates(subset=['Proposta'], keep='first')

        print(f"últimas linhas de orbital:\n{orbital_final[['CPF/CNPJ', 'VALOR DESCONTO']].tail()}")
        
        print(f"orbital_tratado: Salvando arquivo de orbital tratado teste com front")
        try:
            orbital_final.to_excel(os.path.join(self.caminho, f"ORBITAL TRABALHADO {self.convenio}.xlsx"), index=False)
            print(f"orbital_tratado: ORBITAL TRABALHADO {self.convenio} salvo com sucesso!")
        except Exception as e:
            print(f"orbital_tratado: ERRO AO SALVAR ORBITAL TRABALHADO {self.convenio}: {e}")

        return orbital_final


    def validacao_termino_front(self, front):
        front_copy = front.copy()
        teste_conciliacao = TRATA_CONCILIACAO(self.conciliacao, self.kobraki)
        conciliacao_tratado = teste_conciliacao.trata_conciliacao()

        # Certifica que todos os contratos no Credbase trabalhado são do mesmo tipo
        # cred['Codigo_Credbase'] = cred['Codigo_Credbase'].astype(str)

        conciliacao_tratado['CONTRATOS'] = conciliacao_tratado['CONTRATOS'].astype('float64')
        conciliacao_tratado['CONTRATOS'] = conciliacao_tratado['CONTRATOS'].astype('Int64')

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
        if front['Prestacao'].dtype != "float64":
            front_copy['Prestacao'] = front_copy['Prestacao'].str.replace('.', '', regex=False)
            front_copy['Prestacao'] = front_copy['Prestacao'].str.replace(',', '.', regex=False)
            front_copy['Prestacao'] = pd.to_numeric(front_copy['Prestacao'], errors='coerce')

        # Valor que vai ser lançado
        # Substitui NaN em "Saldo" por um valor muito alto (para que "Parcela" seja escolhida)
        valor_a_lancar = np.minimum(np.abs(front_copy['Saldo']).fillna(float('inf')), front_copy['Prestacao'])

        front_copy['Valor a lançar'] = valor_a_lancar

        return front_copy

    def andamento_func_front(self, front):
        # Andamento
        if self.andamento is None:
            return front


        # Primeiro, criamos um dicionário de correspondência
        # modalidade_dict = andam_file.set_index('Código na instituição')['Modalidade'].to_dict()
        # prazo_dict = andam_file.set_index('Código na instituição')['Prazo Total'].to_dict()

        andam_file = self.trata_cod_and(self.andamento)
        print(f"DEBUG: Tentando salvar ANDAMENTO em: {self.caminho}")
        try:
            andam_file.to_excel(os.path.join(self.caminho, f"ANDAMENTO_TESTE {self.convenio}.xlsx"), index=False)
            print("DEBUG: Arquivo salvo com sucesso!")
        except Exception as e:
            print(f"DEBUG: ERRO AO SALVAR: {e}")

        # Função para decidir o valor da nova modalidade
        def substituir_modalidade():
            # 1. Identifica todas as colunas com 'Contrato' no nome
            colunas_contratos = [col for col in andam_file.columns if 'Contrato' in col]

            # 2. Cria um dicionário auxiliar: contrato → prazo
            contrato_para_prazo = {}

            if andam_file['Valor da Parcela'].dtype != "float64":
                andam_file['Valor da Parcela'] = andam_file['Valor da Parcela'].str.replace(".", '')
                andam_file['Valor da Parcela'] = andam_file['Valor da Parcela'].str.replace(",", '.')
                andam_file['Valor da Parcela'] = pd.to_numeric(andam_file['Valor da Parcela'], errors='coerce')
            # print(f'Modalidade e Parcela do Código 407337: {andam_file.loc[andam_file['Código'] == 407337, ['Modalidade', 'Valor da Parcela']]}')

            # Para cada linha no arquivo de andamentos, verifica todas as colunas de contrato
            for _, row in andam_file.iterrows():
                prazo = row.get('Prazo')  # Pode ser 'Prazo Total' dependendo do nome
                for col in colunas_contratos:
                    contrato = row.get(col)
                    if pd.notna(contrato):
                        contrato_para_prazo[str(contrato).strip()] = prazo

            # 4. Aplica a busca no Front
            return front['Contrato'].astype(str).str.strip().map(contrato_para_prazo)

        # Aplica a função ao DataFrame front
        front['PRAZO'] = substituir_modalidade()

        status_andamento = front['PRAZO'].fillna('')

        cond_prazo = ~status_andamento.isin(['', '0', '1', 0, 1])

        # Aplica a condição: se qualquer uma for verdadeira, OBS = 'NÃO'; caso contrário, OBS = ''
        front.loc[cond_prazo & (front['OBS'] == '') & (~front['Tipo Conciliação'].str.contains('Cartão de Crédito|CARTAO DE CREDITO', na=False)), 'OBS'] = 'NÃO LANÇAR - PRAZO'

        return front

    def trata_cod_and(self, andamentos):
        # PUXA OS ARQUIVOS À SEREM TRATADOS
        data_averbados = andamentos

        # REMOVE A ÚLTIMA LINHA DE ANDAMENTO
        data_averbados = data_averbados[:-1]

        # SUBSTITUIMOS CARACTER POR NADA
        contrato_editado = data_averbados['Contrato'].astype(str).apply(
            lambda x: ''.join(char for char in x if char.isdigit() or char in rejeitados))

        contrato_editado = contrato_editado.replace('//', '/', regex=True)

        # INSERE A COLUNA CONTRATO EDITADO COM OS NÚMEROS JÁ TRATADOS
        data_averbados.insert(8, "Contrato Editado", contrato_editado, True)

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

        # 2. Calcular prestação * prazo
        prestacao_vezes_prazo = conciliacao_tratado['PRESTAÇÃO'] * conciliacao_tratado['PRAZO']

        # 3. Calcular o resultado final
        conciliacao_tratado['Pago'] = soma_d8 - prestacao_vezes_prazo
        conciliacao_tratado['Saldo'] = conciliacao_tratado['Pago'] + conciliacao_tratado['RECEBIDO GERAL']

        return conciliacao_tratado

    def averbados_func(self, front):
        # RELATORIO
        front_preliminar = self.tratamento_front_preliminar()
        front_consig = front.copy()
        averbados = self.averbados
        # Remove a última linha que contém o valor total das parcelas
        averbados = averbados.drop(averbados.index[-1])

        if front is False:
            print("averbados_func: O tratamento preliminar do front falhou. Verifique os erros anteriores.")
            return False

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
        orbitall = self.orbital_tratado(self.orbital, front_preliminar)

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

        if self.consignataria == 'CAPITAL CONSIG':
            soma_condicional_dict_averb = front_consig.groupby('CPF')['Valor a lançar'].sum().to_dict()
            averbado_novo['SOMASE'] = averbado_novo['CPF'].map(soma_condicional_dict_averb)
            averbado_novo['SOMASE'] = averbado_novo['SOMASE'].fillna(0)
        elif self.consignataria == 'INSPFEM':
            # 1. Soma por CPF no front_consig
            somase_front_consig = front_consig.groupby('CPF')['Valor a lançar'].sum()

            # 2. Contagem de contratos no front_consig (para somar 25 por contrato)
            qtd_contratos = front_consig.groupby('CPF').size() * 25

            # 3. Soma por CPF no orbital
            somase_orbital = orbitall.groupby('CPF/CNPJ')['VALOR DESCONTO'].sum()

            # 4. Combina tudo em um único dataframe
            soma_total = (
                somase_front_consig.add(qtd_contratos, fill_value=0)
                .add(somase_orbital, fill_value=0)
            )

            # 5. Mapeia no dataframe final
            averbado_novo['SOMASE'] = averbado_novo['CPF'].map(soma_total).fillna(0)

        # =============================================================================
        #        INÍCIO DA NOVA LÓGICA VETORIZADA (SUBSTITUI O SEU LOOP 'FOR')
        # =============================================================================

        # IMPORTANTE: Garanta que as colunas de valores são numéricas, não texto.
        # O .to_numeric(errors='coerce') converte o que for possível para número e põe NaN no que não for.
        if averbado_novo['Valor da Reserva'].dtype != "float64": 
            averbado_novo['Valor da Reserva'] = averbado_novo['Valor da Reserva'].astype(str).str.replace(".", "")
            averbado_novo['Valor da Reserva'] = averbado_novo['Valor da Reserva'].astype(str).str.replace(",", ".")
            averbado_novo['Valor da Reserva'] = pd.to_numeric(averbado_novo['Valor da Reserva'], errors='coerce').fillna(0)
        
        if averbado_novo['SOMASE'].dtype != "float64":
            averbado_novo['SOMASE'] = averbado_novo['SOMASE'].astype(str).str.replace(".", "")
            averbado_novo['SOMASE'] = averbado_novo['SOMASE'].astype(str).str.replace(",", ".")
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

        averbado_novo.to_excel(os.path.join(self.caminho, f"TRABALHADO CARTÃO {self.convenio} {self.consignataria} {str(datetime.now().month).zfill(2)}-{datetime.now().year}.xlsx"), index=False)
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

