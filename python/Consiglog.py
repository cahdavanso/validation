import pandas as pd
from thefuzz import fuzz
from datetime import datetime
from python.ESTEIRAS import load_esteiras
from python.trata_conciliacao import TRATA_CONCILIACAO
from python.TrataOrbital import TRATA_ORBITAL
from python.funcoes_comuns import UNIFICA_FRONT_FUNC_ESTEIRAS
import openpyxl
import numpy as np
import os
import re


class CONSIGLOG:
    def __init__(self, portal_file_list, convenio, front, consignataria, caminho, andamento_funcao, funcao=None, conciliacao=None, kobraki=None, extra_judicial=None, tacs=None, orbital=None):
        self.averbados = portal_file_list


        self.convenio = convenio

        self.front= front

        # Funcao
        self.funcao = funcao if funcao is not None else None

        self.andamento_funcao = andamento_funcao if andamento_funcao is not None else None

        self.kobraki = kobraki

        self.tacs = tacs if tacs is not None else None

        self.extra_judicial = extra_judicial if extra_judicial is not None else None


        conciliacao_falso = pd.DataFrame(
            columns=['CONTRATOS', 'CPF', 'PRESTAÇÃO', 'PRAZO', 'D8 JUN 25', 'ST JUL 25', 'RECEBIDO GERAL'])
        conciliacao_falso['CONTRATOS'] = 123
        conciliacao_falso['CPF'] = '123.456'
        conciliacao_falso['PRESTAÇÃO'] = 10
        conciliacao_falso['PRAZO'] = 96
        conciliacao_falso['D8 JUN 25'] = 10
        conciliacao_falso['ST JUL 25'] = 'DESCONTO TOTAL'
        conciliacao_falso['PRODUTO'] = 'Cartão de Crédito'
        conciliacao_falso['RECEBIDO GERAL'] = 0

        self.conciliacao = conciliacao if conciliacao is not None else conciliacao_falso
        self.conciliacao.rename(columns={'RECEBIDO GERAL ': 'RECEBIDO GERAL'}, inplace=True)
        self.conciliacao.rename(columns={'TIPO OPERAÇÃO': 'PRODUTO', 'NOVO TIPO DE OPERAÇÃO': 'PRODUTO', 'PRODUTOS PELO D8': 'PRODUTO', 
                                         'PRODUTO D8': 'PRODUTO', 'PRODUTO PELO D8': 'PRODUTO', 'PRODUTO ATUALIZADO': 'PRODUTO'}, inplace=True)
        self.orbital = orbital

        self.caminho = caminho

        self.consignataria = consignataria

        # 1. Instancia a classe
        unificador = UNIFICA_FRONT_FUNC_ESTEIRAS(
            front=self.front, 
            convenio=self.convenio, 
            funcao=self.funcao, 
            andamento_funcao=self.andamento_funcao
        )

        # 2. Chama a primeira unificação (Função pura)
        # Isso vai processar e preencher com verificar_ccb=True
        front_meio_caminho = unificador.unifica_front_funcao()

        # 3. Atualiza o front interno da classe para que a segunda unificação use os dados já combinados
        unificador.front = front_meio_caminho

        # 4. Chama a segunda unificação (Andamento Função)
        # Isso vai processar a segunda base com verificar_ccb=False
        self.front_final_consig = unificador.unifica_front_funcao_esteiras_andamento()
        self.front_final_consig.to_excel(os.path.join(self.caminho, f"FRONT FINAL CONSIG {self.convenio}.xlsx"), index=False)

        self.condicoes_1 = load_esteiras()


        self.arquivo_lancamento()

    def unifica_front_funcao(self):
            front = self.front
            funcao = self.funcao

            if funcao is None:
                print('\nFunção está vazio\n')
                return front

            print(f"colunas de funcao: {funcao.columns}")

            contrato_front = front['Contrato']
            ccb_tratado = front['CCB'].astype(str).str.slice(0, 9)
            ccb_tratado = ccb_tratado.astype('int64')

            # Verifica se o que é andamento no front está no função, se tiver transforma em integrado
            contrato_funcao = funcao['NR_PROP']
            front.loc[front['Contrato'].isin(contrato_funcao) & (front['Esteira'].str.contains('ANDAMENTO')), 'Esteira'] = 'INTEGRADO'

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
            # Coloca SIM onde é orbital no função
            front_unif.loc[front_unif['Tipo Operacao'].str.contains('CARTÃO PLÁSTICO|CARTÃO PLÁSTICO - RE|CARTAO SEGURO - A VISTA| CARTAO - SEG PARC'), 'Orbital'] = 'SIM'

            # Altera para cartão
            front_unif['Tipo Operacao'] = front_unif['Tipo Operacao'].fillna('') # -> Só para ter certeza que ele vai preencher corretamente nos vazios
            front_unif.loc[~front_unif['Tipo Operacao'].str.contains('EMPRESTIMO', na=False) & (front_unif['Operação'] == ''), 'Tipo Operacao'] = 'CARTAO DE CREDITO'

            front_unif['Orbital'] = front_unif['Orbital'].fillna("NAO")
            front_unif['Status'] = front_unif['Status'].fillna("INTEGRADO")
            front_unif['Acao Judicial'] = front_unif['Acao Judicial'].fillna("NAO")
            front_unif['Obito'] = front_unif['Obito'].fillna("NAO")
            front_unif['Consignataria'] = front_unif['Consignataria'].fillna(self.consignataria)
            


            print(f'FRONT UNIFICADO FINALZIN: {front_unif.tail()}')

            front_unif.to_excel(rf"{self.caminho}\Teste_front {self.convenio} {self.consignataria} {datetime.now().strftime("%m-%Y")}.xlsx", index=False)

            return front_unif


    def tratamento_front_preliminar(self):
        front_consig = self.front_final_consig

        conciliacao = self.conciliacao.copy()

        orbital = self.orbital


        # Insere as colunas vazias necessárias
        colunas_necessarias = {
            21: 'Saldo',
            22: 'Valor a lançar',
            23: 'PRAZO',
            24: 'OBS'
        }

        for pos, col_name in colunas_necessarias.items():
            if col_name in front_consig.columns:
                # Se já existe, apenas limpa os valores para evitar duplicidade
                front_consig[col_name] = ''
            else:
                # Se não existe, insere na posição desejada (sem allow_duplicates)
                front_consig.insert(pos, col_name, '')

        print(f'Esteiras Únicas do front: {front_consig["Esteira"].unique()}')
        
        # Vamos renomear a primeira coluna da conciliação
        conciliacao.rename(columns={conciliacao.columns[0]: 'CONTRATOS'}, inplace=True)
        # Converte para lista de colunas
        cols = list(conciliacao.columns)

        # Atualiza o DataFrame com novos nomes
        conciliacao.columns = cols
        conciliacao['CONTRATOS'] = conciliacao['CONTRATOS'].astype('Int64')

        # Adiciona a coluna de tipo da Conciliação
        # print(f'colunas de front consig: {front_consig.columns}')
        try:
            tipo_conci = front_consig['Contrato'].map(conciliacao.set_index('CONTRATOS')['PRODUTO'].to_dict())
        except Exception as e:
            print(f'Coluna PRODUTO não se encontra na conciliação. Erro: {e}')
            return False
        
        if 'Tipo Conciliação' in front_consig.columns:
            front_consig = front_consig.drop(columns=['Tipo Conciliação'])

        # Agora insira sem permitir duplicatas (o padrão é False)
        front_consig.insert(19, 'Tipo Conciliação', tipo_conci)
        
        # Adiciona só as esteiras que podem ser lançadas
        front_consig_esteiras = front_consig[front_consig['Esteira'].isin(self.condicoes_1)].copy()

        # Trata coluna de Tipo da Conciliação
        front_consig_esteiras.loc[front_consig_esteiras['Tipo Conciliação'].isin([np.nan, '', ' - ']), 'Tipo Conciliação'] = front_consig_esteiras['Tipo Operacao']

        # --------------------------------------------- ORBITAL --------------------------------------------- #
        # --- ETAPA 1: Garantir que as chaves são do mesmo tipo (Texto) ---
        # Isso evita o erro clássico onde um lado é número e o outro é texto
        if orbital is not None:
            front_consig_esteiras['Contrato'] = front_consig_esteiras['Contrato'].astype(str).str.strip()
            # orbital.rename(columns={'id_contr_banco': 'CONTRATO'}, inplace=True)

            if orbital['VALID DESCONTO FINAL'].dtype != "float64":
                orbital['VALID DESCONTO FINAL'] = orbital['VALID DESCONTO FINAL'].astype(str).str.replace(".", "")
                orbital['VALID DESCONTO FINAL'] = orbital['VALID DESCONTO FINAL'].astype(str).str.replace(",", ".")
                orbital['VALID DESCONTO FINAL'] = pd.to_numeric(orbital['VALID DESCONTO FINAL'], errors='coerce')

            for col in orbital.columns:
                if "contrato" in col or "Contrato" in col:
                    orbital.rename(columns={col:"CONTRATO"}, inplace=True)
            orbital['CONTRATO'] = orbital['CONTRATO'].astype(str)

            

            orbital['CONTRATO'] = orbital['CONTRATO'].astype(str)
            '''print(f'\nContrato 301268942 na coluna CONTRATO: {orbital.loc[orbital["CONTRATO"] == "301268942", "VALID DESCONTO FINAL"]}\n')
            print(f'Contrato 301268942 no front: {front_consig_esteiras.loc[front_consig_esteiras["Contrato"] == "301268942", "Prestacao"]}\n')'''


            # --- ETAPA 2: Criar o "Dicionário de Busca" da Orbital ---
            # Transforma a Orbital em uma série onde Índice = Contrato e Valor = Desconto
            mapa_orbital = orbital.set_index('CONTRATO')['VALID DESCONTO FINAL']
            # --- ETAPA 3: Definir quem vai ser alterado ---
            filtro_esteira = front_consig_esteiras['Esteira'] == '99 CARTAO UTILIZADO'

            # --- ETAPA 4: Fazer a mágica (Buscar valores) ---
            # .loc[filtro, coluna] -> Seleciona só as linhas da esteira certa
            # .map(mapa_orbital)   -> Faz o "PROCV" buscando no dicionário criado
            valores_encontrados = front_consig_esteiras.loc[filtro_esteira, 'Contrato'].map(mapa_orbital)

            # --- ETAPA 5: Tratar quem não foi achado ---
            # Se o contrato não existe na Orbital, o map devolve NaN.
            # Usamos fillna(0) para trocar NaN por 0, conforme você pediu.
            valores_encontrados = valores_encontrados.fillna(0)

            # --- ETAPA 6: Gravar no DataFrame original ---
            valores_encontrados_str = valores_encontrados.astype(str)
            front_consig_esteiras.loc[filtro_esteira, 'Prestacao'] = valores_encontrados_str 
            front_consig_esteiras.loc[filtro_esteira, 'Valor a lançar'] = valores_encontrados_str  

        # Tentar transformar em string com virgula
        front_consig_esteiras.rename(columns={'Prestracao': 'Prestacao'}, inplace=True)

        if front_consig_esteiras['Prestacao'].dtype != 'float64':
            front_consig_esteiras['Prestacao'] = front_consig_esteiras['Prestacao'].astype(str).str.replace('.', '', regex=False)
            front_consig_esteiras['Prestacao'] = front_consig_esteiras['Prestacao'].str.replace(',', '.', regex=False)
            front_consig_esteiras['Prestacao'] = pd.to_numeric(front_consig_esteiras['Prestacao'], errors='coerce')

        if front_consig_esteiras['Valor a lançar'].dtype != 'float64':
            front_consig_esteiras['Valor a lançar'] = front_consig_esteiras['Valor a lançar'].astype(str).str.replace('.', '', regex=False)
            front_consig_esteiras['Valor a lançar'] = front_consig_esteiras['Valor a lançar'].astype(str).str.replace(',', '.', regex=False)
            front_consig_esteiras['Valor a lançar'] = pd.to_numeric(front_consig_esteiras['Valor a lançar'], errors='coerce')


        # -------------------------------- MARCAR TUDO QUE NÃO LANÇA ---------------------------------- #
        # Marca saldo positivo
        front_consig_validado_termino = self.validacao_termino_front(front_consig_esteiras)
        front_consig_validado_termino.loc[front_consig_validado_termino['Saldo'] > -0.01, 'OBS'] = 'NÃO LANÇAR - SALDO POSITIVO'

        # Marca o que é ação judicial
        # No caso de Obito estiver estiver SIM e NÃO ao invés de 1 e 0
        front_consig_validado_termino['Acao Judicial'] = front_consig_validado_termino['Acao Judicial'].replace({'SIM': 1, 'NAO': 0})
        front_consig_validado_termino.loc[front_consig_validado_termino['Acao Judicial'] == 1, 'OBS'] = 'NÃO LANÇAR - AÇÃO JUDICIAL'

        # ------------------------------------- ESCOLHE CONSIGNATÁRIA -------------------------------------- #
        # Renomear nomes dos bancos no front porque estão vindo com 0 na frente
        front_consig_validado_termino['Consignataria'] = front_consig_validado_termino['Consignataria'].astype(str).str.replace("CAPITAL CONSIG ", "CAPITAL CONSIG")
        front_consig_validado_termino['Consignataria'] = front_consig_validado_termino['Consignataria'].astype(str).str.replace("CLICKBANK ", "CLICKBANK")
        front_consig_validado_termino['Consignataria'] = front_consig_validado_termino['Consignataria'].astype(str).str.replace("CIASPREV ", "CIASPREV")
        front_consig_validado_termino['Consignataria'] = front_consig_validado_termino['Consignataria'].astype(str).str.replace("HOJE PREVIDENCIA PRIVADA ", "HOJE PREVIDÊNCIA PRIVADA")

        front_consig_validado_termino['Consignataria'].fillna('', inplace=True)

        if self.consignataria == 'CIASPREV':
            front_consig_validado_termino.loc[(front_consig_validado_termino['Consignataria'] != 'CIASPREV') & (front_consig_validado_termino['OBS'] == ''), 'OBS'] = 'NÃO LANÇAR - CONSIGNATÁRIA ERRADA'
        elif self.consignataria == 'HOJE PREVIDÊNCIA PRIVADA':
            front_consig_validado_termino.loc[(front_consig_validado_termino['Consignataria'] != 'HOJE PREVIDÊNCIA PRIVADA') & (front_consig_validado_termino['OBS'] == ''), 'OBS'] = 'NÃO LANÇAR - CONSIGNATÁRIA ERRADA'
        elif self.consignataria == 'CAPITAL CONSIG':
            front_consig_validado_termino.loc[(front_consig_validado_termino['Consignataria'] != 'CAPITAL CONSIG') & (front_consig_validado_termino['OBS'] == ''), 'OBS'] = 'NÃO LANÇAR - CONSIGNATÁRIA ERRADA'
        elif self.consignataria == 'CLICKBANK':
            front_consig_validado_termino.loc[(front_consig_validado_termino['Consignataria'] != 'CLICKBANK') & (front_consig_validado_termino['OBS'] == ''), 'OBS'] = 'NÃO LANÇAR - CONSIGNATÁRIA ERRADA'
        else:
            print('Consignatária inválida.')
            return

        # Marca o que é Óbito
        # No caso de ação judicial estiver estiver SIM e NÃO ao invés de 1 e 0
        # front_consig_validado_termino['Obito'] = front_consig_validado_termino['Obito'].replace({'SIM': 1, 'NÃO': 0})
        # front_consig_validado_termino.loc[front_consig_validado_termino['Obito'] == 1, 'OBS'] = 'NÃO LANÇAR - ÓBITO'
 
        # Marca tudo que é orbital
        front_consig_validado_termino.loc[(front_consig_validado_termino['Orbital'].str.contains('SIM', na=False) & (front_consig_validado_termino['OBS'] == '')), 'OBS'] = 'NÃO LANÇAR - ORBITAL'

        # Marcar o que não é cartão Conciliação
        if self.convenio in ['PREF. GOIÂNIA', 'PREF. DUQUE DE CAXIAS']:
            print(f'Convenio é {self.convenio}')
            print(f'Convenio está em PREF GOIÂNIA ou PREF. DUQUE DE CAXIAS? {self.convenio in ["PREF. GOIÂNIA", "PREF. DUQUE DE CAXIAS"]}')
            front_consig_validado_termino.loc[(front_consig_validado_termino['Tipo Operacao'].str.contains('EMPRESTIMO|EMPRÉSTIMO', na=False)), 'OBS'] = 'NÃO LANÇAR - NÃO CARTÃO'
        else:
            front_consig_validado_termino.loc[(~front_consig_validado_termino['Tipo Conciliação'].str.contains('Cartão de Crédito|CARTAO DE CREDITO|CARTÃO DE CRÉDITO', na=False)), 'OBS'] = 'NÃO LANÇAR - NÃO CARTÃO'

        # Marcar liquidados em StatusContrato
        front_consig_validado_termino.loc[(front_consig_validado_termino['Status'].str.contains('Liquidado|CANCELADO', na=False)), 'OBS'] = 'NÃO LANÇAR - LIQUIDADO'

        # TIRAR BANCO OUTROS
        front_consig_validado_termino.loc[(front_consig_validado_termino['Consignataria'].str.contains('OUTROS', na=False)), 'OBS'] = 'NÃO LANÇAR - BANCO OUTROS'  

        # Salva com os NÃO LANÇAR
        print(f"tratamento_front_preliminar: Tentando salvar FRONT SEMI TRABALHADO em: {self.caminho}")
        try:
            front_consig_validado_termino.to_excel(os.path.join(self.caminho, f"FRONT SEMI TRABALHADO {self.convenio}.xlsx"), index=False)
            print("tratamento_front_preliminar: Arquivo salvo com sucesso!")
        except Exception as e:
            print(f"DEBUG: ERRO AO SALVAR: {e}")

        # --------------------------------------------------------------------------------------------- #
        return front_consig_validado_termino
        
    def tratamento_front(self):
        front_consig = self.tratamento_front_preliminar()

        if front_consig is False:
            print("tratamento_front: O tratamento preliminar do front falhou. Verifique os erros anteriores.")
            return False

        # Separa apenas o que retornou como "cartão de crédito" no tipo de conciliação
        if self.convenio == 'PREF. GOIÂNIA':
            front_consig_cartao_conciliacao = front_consig[front_consig['Tipo Operacao'].str.contains('Cartão de Crédito|CARTAO DE CREDITO|CARTÃO DE CRÉDITO', na=False)].copy()
        elif self.convenio == 'PREF. DUQUE DE CAXIAS':
            front_consig_cartao_conciliacao = front_consig[~front_consig['Tipo Operacao'].str.contains('EMPRESTIMO|EMPRÉSTIMO', na=False)].copy()
        else:
            front_consig_cartao_conciliacao = front_consig[front_consig['Tipo Conciliação'].str.contains('Cartão de Crédito|CARTAO DE CREDITO|CARTÃO DE CRÉDITO', na=False)].copy()

        # Separar o que não é cartão de crédito da conciliação
        # front_consig_nao_cartao = front_consig[~front_consig['Tipo Conciliação'].str.contains('Cartão de Crédito', na=False)].copy()

        # Pegar o que é CARTAO DE CREDITO do front
        # condicao_cartao = ['CARTAO DE CREDITO']
        # front_consig_cartao_front = front_consig_nao_cartao[front_consig_nao_cartao['dsTipoOperacao'].isin(condicao_cartao)].copy()
        # Faz concat dos dois dataframes
        front_consig_trabalhado = front_consig_cartao_conciliacao.copy()

        # ---------------------------------- TIRAR AÇÃO JUDICIAL DO FRONT ---------------------------------- #
        front_consig_trabalhado = front_consig_trabalhado.loc[front_consig_trabalhado['Acao Judicial'] != 1].copy()

        # ---------------------------------- TIRAR ÓBITO DO FRONT ---------------------------------- #
        # front_consig_trabalhado = front_consig_trabalhado.loc[front_consig_trabalhado['Obito'] != 1].copy()
        
        # ------------------------------------ INSERE A COLUNA DE SALDO ------------------------------------- #

        front_consig_trabalhado.loc[front_consig_trabalhado['Saldo'] > -0.01, 'Valor a lançar'] = 0
        front_consig_trabalhado = front_consig_trabalhado[front_consig_trabalhado['Valor a lançar'] > 0].copy()

        # ---------------------------------------- AJUSTE PECÚLIO HOJE --------------------------------------- #
        '''mask_peculio = front_consig_trabalhado['Consignataria'] == 'HOJE PREVIDÊNCIA PRIVADA'
        front_consig_trabalhado.loc[mask_peculio, 'Valor a lançar'] += 20'''

        # ------------------------------------- ESCOLHE CONSIGNATÁRIA -------------------------------------- #
        front_consig_trabalhado['Consignataria'].fillna('', inplace=True)

        if self.consignataria == 'CIASPREV':
            front_consig_trabalhado = front_consig_trabalhado[front_consig_trabalhado['Consignataria'].str.contains('CIASPREV', na=False)].copy()
        elif self.consignataria == 'HOJE PREVIDÊNCIA PRIVADA':
            front_consig_trabalhado = front_consig_trabalhado[front_consig_trabalhado['Consignataria'].str.contains('HOJE PREVIDÊNCIA PRIVADA', na=False)].copy()
        elif self.consignataria == 'CAPITAL CONSIG':
            front_consig_trabalhado = front_consig_trabalhado[front_consig_trabalhado['Consignataria'].str.contains('CAPITAL CONSIG', na=False)].copy()
        elif self.consignataria == 'CLICKBANK':
            front_consig_trabalhado = front_consig_trabalhado[front_consig_trabalhado['Consignataria'].str.contains('CLICKBANK', na=False)].copy()
        else:
            print('Consignatária inválida.')
            return


        # --------------------------------------- TIRA BANCO OUTROS ----------------------------------------- #
        front_consig_trabalhado = front_consig_trabalhado[~front_consig_trabalhado['Consignataria'].str.contains('OUTROS', na=False)].copy()

        # ----------------------------------------- TIRA LIQUIDADOS ----------------------------------------- #
        front_consig_trabalhado = front_consig_trabalhado[~front_consig_trabalhado['Status'].str.contains('Liquidado|CANCELADO', na=False)].copy()

        return front_consig_trabalhado

    def validacao_termino_front(self, front):
        front_copy = front.copy()
        teste_conciliacao = TRATA_CONCILIACAO(self.conciliacao, self.kobraki, self.tacs, self.extra_judicial)
        conciliacao_tratado = teste_conciliacao.trata_conciliacao()

        # Certifica que todos os contratos no Front trabalhado são do mesmo tipo
        front_copy['Contrato'] = front_copy['Contrato'].astype(str)

        conciliacao_tratado['CONTRATOS'] = conciliacao_tratado['CONTRATOS'].astype(str)

        print('trata_conciliacao: Colunas da conciliação tratada')
        try:
            conciliacao_tratado.to_excel(os.path.join(self.caminho, f"Conciliacao_TESTE.xlsx"), index=False)
        except Exception as e:
            print(f"trata_conciliacao: ERRO AO SALVAR Conciliacao_TESTE.xlsx: {e}")

        # Verifica o dtype de "Contrato" no front e de "CONTRATOS" na conciliação
        print(f'Dtype de Contrato no front: {front_copy["Contrato"].dtype}')
        print(f'Dtype de CONTRATOS na conciliação: {conciliacao_tratado["CONTRATOS"].dtype}')

        # print(f'status \n{front_copy[front_copy["Contrato"] == 300846910]}')

        # Puxar o saldo para o front usando o map, que é mais eficiente que o merge para esse tipo de operação
        front_copy['Saldo'] = front_copy['Contrato'].map(conciliacao_tratado.set_index('CONTRATOS')['Saldo']).to_dict()
        # front_copy['Saldo'] = pd.to_numeric(front_copy['Saldo'], errors='coerce')

        front_copy.rename(columns={'Prestracao': 'Prestacao'}, inplace=True)
        if front_copy['Prestacao'].dtype != 'float64':
            front_copy['Prestacao'] = front_copy['Prestacao'].astype(str).str.replace('.', '', regex=False)
            front_copy['Prestacao'] = front_copy['Prestacao'].str.replace(',', '.', regex=False)
            front_copy['Prestacao'] = pd.to_numeric(front_copy['Prestacao'], errors='coerce')

        print(f'Contrato 301268942 no front no validacao_termino: {front_copy.loc[front_copy["Contrato"] == "301268942", "Prestacao"]}\n')
 

        # Valor que vai ser lançado
        # Substitui NaN em "Saldo" por um valor muito alto (para que "Parcela" seja escolhida)
        # front_copy['Saldo'] = front_copy['Saldo'].fillna(np.nan)
        # 1. Altera a coluna Saldo de verdade
        front_copy['Saldo'] = front_copy['Saldo'].fillna(-1000)

        # 2. Faz o cálculo (agora não precisa mais do fillna aqui dentro)
        valor_a_lancar = np.maximum(front_copy['Saldo'], front_copy['Prestacao'])

        front_copy['Valor a lançar'] = valor_a_lancar

        # 3. Agora seu print vai mostrar -1000
        print(front_copy.loc[front_copy["Contrato"] == "302298345", "Saldo"])

        return front_copy

    def extrair_contratos_com_referencia(self, df_sujo: pd.DataFrame, df_limpo: pd.DataFrame) -> pd.DataFrame:
            print("Iniciando o processo de extração de contratos...")

            # Função de limpeza (pode ser definida aqui ou fora)
            def limpar_contrato(texto: str) -> str:
                if not isinstance(texto, str):
                    texto = str(texto)
                    texto = texto.replace(" ", "")
                return re.sub(r'[^0-9a-zA-Z]', '', texto)  # Mantém letras e números

            # --- Passo 1: Criar o mapa de referência (sem alterações) ---
            df_limpo['Contrato'] = df_limpo['Contrato'].astype(str).str.strip()
            df_limpo['CCB'] = df_limpo['CCB'].astype(str).str.strip()
            print("Criando mapa de referência CPF -> Contratos...")
            
            cpf_contratos = df_limpo.groupby('CPF')['Contrato'].apply(list).to_dict()
            cpf_operacao = df_limpo.groupby('CPF')['CCB'].apply(list).to_dict()
            # print(f'Mapa contratos:\n{cpf_contratos}')

            # --- Passo 2: Definir a função que será aplicada em cada linha (LÓGICA ALTERADA) ---
            def encontrar_contratos_na_linha(row):
                cpf = row['CPF_Formatado']
                texto_contratos_sujo = str(row['Contrato Original']).strip()
            
                cpf = row['CPF_Formatado']
                texto_contratos_sujo = str(row['Contrato Original'])

                # Garante que as listas existam
                contratos_validos_para_cpf = cpf_contratos.get(cpf, [])
                operacoes_validas_para_cpf = cpf_operacao.get(cpf, [])

                if not contratos_validos_para_cpf:
                    return []

                # 1. DIVIDIR: Mesma lógica de limpeza
                partes_sujas = [p for p in re.split(r'[/,;\s]+', texto_contratos_sujo) if p]

                if not partes_sujas:
                    return []

                encontrados_nesta_linha = []

                # Listas de controle
                contratos_disponiveis = list(contratos_validos_para_cpf)
                operacoes_disponiveis = list(operacoes_validas_para_cpf)

                # --- MUDANÇA: LIMIAR ALTO ---
                # Agora podemos exigir quase perfeição porque mudamos o método de comparação
                LIMIAR_SEGURO = 90

                for parte in partes_sujas:
                    parte_limpa = limpar_contrato(parte)
                    if not parte_limpa or len(parte_limpa) < 3:
                        continue

                    melhor_match_para_parte = None
                    maior_score_ponderado = 0  # Mudamos o nome para deixar claro

                    for i, contrato_valido in enumerate(contratos_disponiveis):

                        # Pega a operação correspondente (se existir)
                        operacao_valida = operacoes_disponiveis[i] if i < len(operacoes_disponiveis) else ""

                        # Vamos testar os dois alvos separadamente
                        alvos = [
                            (contrato_valido, 'CONTRATO'),
                            (operacao_valida, 'OPERACAO')
                        ]

                        for alvo_texto, tipo_alvo in alvos:
                            if not alvo_texto: continue

                            alvo_limpo = limpar_contrato(alvo_texto)
                            score_base = 0

                            # --- SUA LÓGICA NOVA (PERFEITA) ---
                            if alvo_limpo.endswith(parte_limpa):
                                score_base = 100
                            else:
                                score_partial = fuzz.partial_ratio(parte_limpa, alvo_limpo)
                                if score_partial >= LIMIAR_SEGURO:
                                    score_base = score_partial
                                else:
                                    score_ratio = fuzz.ratio(parte_limpa, alvo_limpo)
                                    if score_ratio >= LIMIAR_SEGURO:
                                        score_base = score_ratio
                            # ----------------------------------

                            # --- A CORREÇÃO DO DESEMPATE AQUI ---

                            # Se o score for bom (acima do limiar), calculamos o "Score Ponderado"
                            if score_base >= LIMIAR_SEGURO:

                                score_final = score_base

                                # Damos um BÔNUS se o match foi no CONTRATO
                                # Isso garante que 100 (Contrato) ganhe de 100 (Operação)
                                if tipo_alvo == 'CONTRATO':
                                    score_final += 1  # O "pulo do gato"

                                # Verifica se esse é o melhor match desta parte suja até agora
                                if score_final > maior_score_ponderado:
                                    maior_score_ponderado = score_final
                                    # IMPORTANTE: Independente se o match foi na operação ou contrato,
                                    # nós SEMPRE salvamos o 'contrato_valido' como o resultado.
                                    melhor_match_para_parte = contrato_valido

                    if melhor_match_para_parte:
                        encontrados_nesta_linha.append(melhor_match_para_parte)

                        # Remove das listas para não duplicar na mesma linha
                        if melhor_match_para_parte in contratos_disponiveis:
                            index_remocao = contratos_disponiveis.index(melhor_match_para_parte)
                            del contratos_disponiveis[index_remocao]

                return encontrados_nesta_linha

            # --- Passo 3: Aplicar a função e criar as novas colunas (sem alterações) ---
            print("Analisando a Planilha A e extraindo os contratos...")
            df_sujo['Contrato Original'] = df_sujo['Contrato Original'].astype(str).str.replace('nan', '')


            lista_de_contratos_encontrados = df_sujo.apply(encontrar_contratos_na_linha, axis=1)

            df_contratos_novos = pd.DataFrame(lista_de_contratos_encontrados.tolist(), index=df_sujo.index)
            df_contratos_novos.columns = [f'Contrato Editado {i + 1}' for i in df_contratos_novos.columns]

            df_resultado = pd.concat([df_sujo, df_contratos_novos], axis=1)

            print("extrair_contratos_com_referencia: Salvando relatório de averbados com contratos tratados")
            try:
                df_resultado.to_excel(os.path.join(self.caminho, f"Relatório Averbados Contratos tratados.xlsx"), index=False)
            except Exception as e:
                print(f"DEBUG: ERRO AO SALVAR RELATÓRIO AVERBADO CONTRATOS TRATADOS: {e}")
            return df_resultado


    def substituir_virgula_por_ponto(self, valor):
        return valor.replace(',', '.')

    # FUNÇÃO QUE SUBSTITUI CARACTER POR NADA
    def replace_characters(self, file, coluna, localizar, substituir):
        column = file[coluna].replace(localizar, substituir, regex=True)
        return column

    # FUNÇÃO QUE FAZ PARTE DO PROCX COM O FRONT COMO BASE
    def mapeamento_front(self, interval, criteria):
        maping = self.front.set_index(interval)[criteria].to_dict()
        return maping


    # DIVIDE A STRING EM PARTES DE 6
    def inserir_barras(self, numero):
        partes = [numero[i:i + 6] for i in range(0, len(numero), 6)]
        return '/'.join(partes)

    # Função para distribuir os valores da coluna de origem para as colunas-alvo
    def distribuir_valores(self, df, coluna_origem, colunas_alvo):
        for i, coluna_alvo in enumerate(colunas_alvo):
            df[coluna_alvo] = df[coluna_origem].str.split('/').str[i]

    def adiciona_peculio(self, averbacoes):
        data_averbados = averbacoes.copy()

        # 1. Cria uma coluna inicial zerada para acumular a soma
        data_averbados['Soma_Calculada'] = 0.0

        # 2. Define o limite máximo de colunas que você criou (ajuste esse range se tiver mais que 10)
        # Se você tiver 'Esteira_1' até 'Esteira_5', o range deve ser range(1, 6)
        # Coloquei até 20 para garantir, o código verifica se a coluna existe.
        for i in range(1, 20):
            col_esteira = f'Esteira_{i}'
            col_valor = f'Valor_Unif_{i}'

            # Verifica se esse par de colunas existe no DataFrame
            if col_esteira in data_averbados.columns and col_valor in data_averbados.columns:
                # --- A LÓGICA MÁGICA ---
                # 1. Cria uma máscara: Linhas onde a Esteira X está na lista de permitidas
                mascara_esteira_valida = data_averbados[col_esteira].isin(self.condicoes_1)

                # 2. Pega os valores correspondentes, preenche NaN com 0 para evitar erros
                valores_validos = data_averbados.loc[mascara_esteira_valida, col_valor].fillna(0)

                # 3. Adiciona (Valor + 20) na coluna acumuladora
                # Importante: Só somamos nas linhas onde a máscara é Verdadeira
                data_averbados.loc[mascara_esteira_valida, 'Soma_Calculada'] += (valores_validos + 20)

        # 3. Aplica a comparação final com o Valor Prestação (Teto)
        data_averbados['Lançar'] = np.minimum(data_averbados['Soma_Calculada'], data_averbados['Valor Prestacao'])

        # (Opcional) Remove a coluna temporária se não precisar mais
        data_averbados = data_averbados.drop(columns=['Soma_Calculada'])

        return data_averbados

    def orbital_tratado(self, orbital, front_para_separar):

        orbital_preparado = orbital.loc[
            orbital['DESCRIÇÃO DO EMPREG'].str.contains('PREF GOIÂNIA|PM GOIANIA SEG', case=False, na=False),
            ['CONTRATO', 'nome_mutuario', 'num_cpf_mutuario', 'VALID DESCONTO FINAL']
        ].copy()
        orbital_preparado.columns = ['Proposta', 'Cliente', 'CPF/CNPJ', 'VALID DESCONTO FINAL']

        front_so_orbital = front_para_separar.loc[
            front_para_separar['OBS'] == 'NÃO LANÇAR - ORBITAL',
            ['Contrato', 'Nome', 'CPF', 'Prestacao']].copy()
        
        front_so_orbital.columns = ['Proposta', 'Cliente', 'CPF/CNPJ', 'VALID DESCONTO FINAL']

        # front_so_orbital['Proposta'] = front_so_orbital['Proposta'].astype(str).str.strip()

        # front_so_orbital['VALID DESCONTO FINAL'] = front_so_orbital['VALID DESCONTO FINAL'].astype(str).str.replace('.', '', regex=False)
        front_so_orbital['VALID DESCONTO FINAL'] = front_so_orbital['VALID DESCONTO FINAL'].astype(str).str.replace(',', '.', regex=False)
        front_so_orbital['VALID DESCONTO FINAL'] = pd.to_numeric(front_so_orbital['VALID DESCONTO FINAL'], errors='coerce')

        orbital_final = pd.concat([front_so_orbital, orbital_preparado])

        orbital_final = orbital_final.drop_duplicates(subset=['Proposta'], keep='first')

        print(f"orbital_tratado: Salvando arquivo de orbital tratado teste com front")
        try:
            orbital_final.to_excel(os.path.join(self.caminho, f"ORBITAL TRABALHADO {self.convenio}.xlsx"), index=False)
            print(f"orbital_tratado: ORBITAL TRABALHADO {self.convenio} salvo com sucesso!")
        except Exception as e:
            print(f"orbital_tratado: ERRO AO SALVAR ORBITAL TRABALHADO {self.convenio}: {e}")

        return orbital_final
    
    def adiciona_contratos_faltando(self, averbado_contratos_faltantes, front_semi):
        # 1. Normalização do CPF no DataFrame B (Removendo caracteres não numéricos)
        # front_semi['CPF_clean'] = front_semi['CPF'].astype(str).str.replace(r'\D', '', regex=True)

        # 2. Preparação do DataFrame B para os diferentes cenários de valor
        # Vamos criar DataFrames auxiliares para cada regra de negócio
        # Isso evita confusão com múltiplos joins no mesmo objeto
        front_semi_base = front_semi[['CPF', 'Prestacao', 'Contrato']].drop_duplicates(subset=['CPF', 'Prestacao'])

        # Criamos as variações no B para "fingir" que o valor já tem o seguro embutido
        front_semi_exact = front_semi_base.copy()
        front_semi_plus20 = front_semi_base.copy()
        front_semi_plus20['Prestacao_Ajustada'] = front_semi_plus20['Prestacao'] + 20
        front_semi_plus40 = front_semi_base.copy()
        front_semi_plus40['Prestacao_Ajustada'] = front_semi_plus40['Prestacao'] + 40

        # 3. Execução dos Merges no DataFrame A
        # Primeiro, tentamos o match exato (valor igual)
        averbado_contratos_faltantes = averbado_contratos_faltantes.merge(
            front_semi_exact, 
            left_on=['CPF_Formatado', 'Valor Prestacao'], 
            right_on=['CPF', 'Prestacao'], 
            how='left'
        )

        # Preenchemos a coluna "Contrato Original" com o que achamos no primeiro merge
        averbado_contratos_faltantes['Contrato Original'] = averbado_contratos_faltantes['Contrato Original'].fillna(averbado_contratos_faltantes['Contrato'])
        averbado_contratos_faltantes.drop(columns=['CPF', 'Prestacao', 'Contrato'], inplace=True)

        # Segundo merge: Caso de +20 reais
        averbado_contratos_faltantes = averbado_contratos_faltantes.merge(
            front_semi_plus20, 
            left_on=['CPF_Formatado', 'Valor Prestacao'], 
            right_on=['CPF', 'Prestacao_Ajustada'], 
            how='left', 
            suffixes=('', '_20')
        )

        averbado_contratos_faltantes['Contrato Original'] = averbado_contratos_faltantes['Contrato Original'].fillna(averbado_contratos_faltantes['Contrato'])
        averbado_contratos_faltantes.drop(columns=['CPF', 'Prestacao', 'Contrato', 'Prestacao_Ajustada'], inplace=True)

        # Terceiro merge: Caso de +40 reais
        averbado_contratos_faltantes = averbado_contratos_faltantes.merge(
            front_semi_plus40, 
            left_on=['CPF_Formatado', 'Valor Prestacao'], 
            right_on=['CPF', 'Prestacao_Ajustada'], 
            how='left', 
            suffixes=('', '_40')
        )

        averbado_contratos_faltantes['Contrato Original'] = averbado_contratos_faltantes['Contrato Original'].fillna(averbado_contratos_faltantes['Contrato'])

        averbado_contratos_faltantes.drop(columns=['CPF', 'Prestacao', 'Contrato', 'Prestacao_Ajustada'], inplace=True)

        # Limpeza final das colunas auxiliares
        # averbado_contratos_faltantes = averbado_contratos_faltantes[['C P F', 'Valor Prestação', 'Contrato Original']]

        return averbado_contratos_faltantes

    def trata_averbacao(self):
        # PUXA OS ARQUIVOS À SEREM TRATADOS
        data = self.averbados
        front = self.tratamento_front_preliminar()
        front['Contrato'] = front['Contrato'].astype(str).str.strip()

        teste_conciliacao = TRATA_CONCILIACAO(self.conciliacao, self.kobraki, self.tacs, self.extra_judicial)
        # conciliacao_tratado = teste_conciliacao.trata_conciliacao()

        if front is False:
            print("trata_averbacao_1: O tratamento preliminar do front falhou. Verifique os erros anteriores.")
            return False

        print(f'Contrato 301268942 no front em trata_averbacao: {front.loc[front["Contrato"] == "301268942", "Prestacao"]}\n')

        consig = self.consignataria
        convenio = self.convenio

        if convenio == 'PREF. GOIÂNIA':
            # O ARQUIVO DE AVERBAÇÕES PRECISA TER OS DOIS TIPOS. COMPRA E SAQUE
            # PEGA APENAS AS COLUNAS NECESSÁRIAS DO ARQUIVO BRUTO
            colunas = ['A D E', 'Servidor', 'Matricula', 'C P F', 'Valor Prestacao', 'Contrato Original', 'Qt Prestacao']
            data_averbados_bruto = data[colunas]

            # Passo 1: Garantir que a coluna é do tipo string
            cpf_str = data_averbados_bruto['C P F'].astype(str)
            cpf_str_ajustado = cpf_str.str.zfill(11)
            cpf_formatado = cpf_str_ajustado.str.slice(0, 3) + '.' + \
                            cpf_str_ajustado.str.slice(3, 6) + '.' + \
                            cpf_str_ajustado.str.slice(6, 9) + '-' + \
                            cpf_str_ajustado.str.slice(9, 11)

            data_averbados_bruto.insert(4, 'CPF_Formatado', cpf_formatado, True)

            concat_cpf_parcela = data_averbados_bruto['C P F'].astype(str) + data_averbados_bruto['Valor Prestacao'].astype(str)

            data_averbados_bruto.insert(5, 'CONCAT', concat_cpf_parcela, True)

            print(f'Tipo do concat_cpf_parcela: {data_averbados_bruto['CONCAT'].dtype}')

            if self.orbital is not None:
                preparando_orbital = TRATA_ORBITAL(self.orbital, front, self.convenio, self.caminho)
                orbital_tratado = preparando_orbital.orbital_tratado()
            orbital_tratado['VALOR DESCONTO'] = pd.to_numeric(orbital_tratado['VALOR DESCONTO'], errors='coerce')
            mask_orbital = orbital_tratado.groupby('CPF/CNPJ')['VALOR DESCONTO'].sum()
            data_averbados_bruto['ORBITAL'] = ''
            data_averbados_bruto['ORBITAL'] = data_averbados_bruto['CPF_Formatado'].map(mask_orbital)


            data_averbados_bruto['CONTSE'] = data_averbados_bruto.groupby('CONCAT')['CONCAT'].transform('count')

            # 1. Cria a máscara Booleana (True/False)
            # Note os parênteses extras envolvendo cada comparação
            cont_orbital_mask = (data_averbados_bruto['CONTSE'] > 1) & \
                                ((data_averbados_bruto['ORBITAL'] == '') | (data_averbados_bruto['ORBITAL'].isna()))

            # 2. Filtra mantendo apenas o que NÃO (~) for Verdadeiro na máscara
            data_averbados_bruto = data_averbados_bruto.loc[~cont_orbital_mask]

            print(f"trata_averbacao: Salvando arquivo de averbacao teste com orbital")
            try:
                data_averbados_bruto.to_excel(os.path.join(self.caminho, f"Averbacao com orbital teste {self.convenio}.xlsx"), index=False)
            except Exception as e:
                print(f"trata_averbacao: ERRO AO SALVAR AVERBAÇÃO COM ORBITAL TESTE: {e}")

            data_averbados_bruto = data_averbados_bruto.loc[data_averbados_bruto['Qt Prestacao'] != 96]
            print(f'data_averbados_bruto tipo {data_averbados_bruto['Qt Prestacao'].dtype}')
            print(f'\ndata_averbados_bruto unico {data_averbados_bruto['Qt Prestacao'].unique()}')

            data_averbados = self.extrair_contratos_com_referencia(data_averbados_bruto, front)

            semi_front = front[front['Esteira'].isin(self.condicoes_1)]
            semi_front['Contrato'] = semi_front['Contrato'].astype(str).str.strip()

            conciliacao_tratado = teste_conciliacao.trata_conciliacao()

            # Operações liquidadas. Tratando NRº OPER EDITADO
            # OP LIQUIDADO
            try:
                oper_liq = self.front[self.front['Status'].astype(str).str.contains('Liquidado|CANCELADO', na=False)][['Contrato']].copy()
                contratos_tratados_liq = oper_liq['Contrato'].astype(str).str.slice(0, 9)
                oper_liq.insert(1, "Nº OPERAÇÃO EDITADO", contratos_tratados_liq, True)

            except Exception as e:
                oper_liq = pd.DataFrame(columns=['Contrato', 'Nº OPERAÇÃO EDITADO'])
                print(f"Planilha de Operações Liquidadas está vazia {e}")

            tutela = self.front[self.front['Acao Judicial'] == 1][['CPF', 'Acao Judicial']].copy()

            # consig = self.consignataria

            # --- 1. Identifica TODAS as colunas que contêm contratos ---
            # Inclui a coluna original e as que foram extraídas pela função anterior.
            # Ajuste 'Contrato' se a sua coluna original tiver um nome diferente (ex: 'Identificador')
            # colunas_com_contratos = ['Contrato'] + [col for col in data_averbados.columns if 'Contrato Editado' in col]
            colunas_com_contratos = [col for col in data_averbados.columns if 'Contrato Editado' in col]

            # Remove duplicatas, caso o nome 'Contrato' já esteja na lista
            colunas_com_contratos = list(dict.fromkeys(colunas_com_contratos))

            # print(f"Colunas de contrato identificadas para análise: {colunas_com_contratos}")

            # --- 2. Loop único para criar as colunas de Esteira e Valor para CADA contrato ---
            # O enumerate nos dá um índice numérico (i) para criar nomes de coluna únicos.
            for i, nome_coluna_contrato in enumerate(colunas_com_contratos, start=1):
                # print(f"Processando coluna '{nome_coluna_contrato}'...")

                # Cria a coluna de Esteira correspondente
                data_averbados[f'Esteira_{i}'] = data_averbados[nome_coluna_contrato].map(
                    front.set_index('Contrato')['Esteira'].to_dict()
                )

                # Cria a coluna de Valor da Parcela correspondente
                data_averbados[f'Valor_Unif_{i}'] = data_averbados[nome_coluna_contrato].map(
                    front.set_index('Contrato')['Prestacao'].to_dict()
                )

                # Puxa os valores de saldo da conciliação
                data_averbados[f'Saldo {i}'] = data_averbados[nome_coluna_contrato].map(
                    conciliacao_tratado.set_index('CONTRATOS')['Saldo'].to_dict()
                )

                # Puxando os contratos liquidados (FORMA CORRIGIDA)
                # Cria a nova coluna 'OP LIQ {i}' com o resultado do map
                data_averbados[f'OP LIQ {i}'] = data_averbados[nome_coluna_contrato].map(
                    oper_liq.set_index('Nº OPERAÇÃO EDITADO')['Contrato'].to_dict()
                )


                # --- PASSO 2: PREPARAÇÃO E LIMPEZA DE DADOS ---
                # Agora que todas as colunas foram criadas, garantimos que sejam numéricas para os cálculos.
                data_averbados[f'Valor_Unif_{i}'] = pd.to_numeric(data_averbados[f'Valor_Unif_{i}'],
                                                                  errors='coerce').fillna(0)
                data_averbados[f'Saldo {i}'] = pd.to_numeric(data_averbados[f'Saldo {i}'], errors='coerce').fillna(0)

                # --- PASSO 3: CONSTRUIR AS CONDIÇÕES E APLICAR A LÓGICA ---

                # Condição 1: Encontra todas as linhas onde o Saldo (já limpo) é >= 0
                condicao_saldo_positivo = data_averbados[f'Saldo {i}'] >= -1

                # Condição 2: Encontra onde um contrato liquidado foi efetivamente encontrado (FORMA CORRIGIDA E ROBUSTA)
                # .notna() garante que só pegamos as linhas onde o map retornou um valor, e não NaN.
                condicao_op_liq = data_averbados[f'OP LIQ {i}'].notna()

                # Ação: Nessas linhas, define o 'Valor_Unif' correspondente como 0
                # O operador | significa OU (se uma condição OU a outra for verdadeira)
                data_averbados.loc[(condicao_saldo_positivo | condicao_op_liq), f'Valor_Unif_{i}'] = 0
                # --- FIM DA NOVA LÓGICA ---

                # Condição de Operações Liquidadas, se a linha estiver preenchida vai lançar 0

            # --- 2.5 Puxa as liminares ---
            data_averbados["LIMINAR"] = data_averbados['CPF_Formatado'].map(
                self.front.set_index('CPF')['Acao Judicial'].to_dict())
            condicao_liminar = data_averbados['LIMINAR'] == 1

            # --- 3. Soma todos os valores encontrados (forma eficiente) ---

            # Pega a lista de colunas de valor
            colunas_valores_unificados = [col for col in data_averbados.columns if 'Valor_Unif_' in col]

            if colunas_valores_unificados:
                # 1. Define o filtro de quem deve ser ZERADO
                # Lógica: Se CONTSE for maior que 1, zeramos os valores.
                filtro_zerar = data_averbados['CONTSE'] > 1

                # 2. Zera todas as colunas de valor nessas linhas de uma vez só
                # .loc[linhas_ruins, colunas_alvo] = 0
                data_averbados.loc[filtro_zerar, colunas_valores_unificados] = 0.0

                # 3. Agora você pode fazer a soma simples (sem filtro),
                # pois os linhas indesejadas já valem 0.
                data_averbados['Soma'] = data_averbados[colunas_valores_unificados].sum(axis=1)
            else:
                print("Nenhuma coluna de valor encontrada. A coluna 'Soma' será inicializada com 0.")
                data_averbados['Soma'] = 0

            # --- 4. Cálculo da Diferença e Formatação Final ---

            # Garante que a coluna de Valor Prestacao é numérica antes do cálculo
            data_averbados['Valor Prestacao'] = pd.to_numeric(data_averbados['Valor Prestacao'],
                                                              errors='coerce').fillna(0)

            data_averbados['Diff'] = data_averbados['Soma'] - data_averbados['Valor Prestacao']
            data_averbados['Diff'] = data_averbados['Diff'].round(2)

            # 2. Filtra todas as colunas que começam com "Parcela "
            colunas_parcelas = data_averbados.filter(like='Valor_Unif_')

            # NOVO PASSO: Adiciona a coluna 'ORBITAL' ao DataFrame de colunas para soma
            colunas_para_somar = colunas_parcelas.copy()  # Cria uma cópia para garantir a segurança

            # Verifica se 'ORBITAL' já existe antes de adicionar (apenas por garantia, embora o código garanta)
            if 'ORBITAL' in data_averbados.columns:
                # Usa .loc para garantir que a coluna seja adicionada
                colunas_para_somar.loc[:, 'ORBITAL'] = data_averbados['ORBITAL']

            # 3. Soma as colunas horizontalmente (axis=1)
            data_averbados['Soma'] = colunas_para_somar.sum(axis=1)

            data_averbados['Lançar'] = np.minimum(data_averbados['Soma'], data_averbados['Valor Prestacao'])
            data_averbados.loc[condicao_liminar, 'Lançar'] = 0

            return data_averbados

        # PEGA APENAS AS COLUNAS NECESSÁRIAS DO ARQUIVO BRUTO
        colunas = ['A D E', 'Servidor', 'Matricula', 'C P F', 'Valor Prestacao', 'Contrato Original']
        data_averbados_bruto = data[colunas]

        # Passo 1: Garantir que a coluna é do tipo string
        cpf_str = data_averbados_bruto['C P F'].astype(str)
        cpf_str_ajustado = cpf_str.str.zfill(11)
        cpf_formatado = cpf_str_ajustado.str.slice(0, 3) + '.' + \
                              cpf_str_ajustado.str.slice(3, 6) + '.' + \
                              cpf_str_ajustado.str.slice(6, 9) + '-' + \
                              cpf_str_ajustado.str.slice(9, 11)

        data_averbados_bruto.insert(4, 'CPF_Formatado', cpf_formatado, True)

        semi_front = self.tratamento_front_preliminar()
        if semi_front is False:
            print("trata_averbacao_2: O tratamento preliminar do front falhou. Verifique os erros anteriores.")
            return False
        
        data_averbados_bruto = self.adiciona_contratos_faltando(data_averbados_bruto, semi_front)

        semi_front['Contrato'] = semi_front['Contrato'].astype(str).str.strip()


        data_averbados = self.extrair_contratos_com_referencia(data_averbados_bruto, semi_front)

        teste_conciliacao = TRATA_CONCILIACAO(self.conciliacao, self.kobraki, self.extra_judicial)
        conciliacao_tratado = teste_conciliacao.trata_conciliacao()

        # Operações liquidadas. Tratando NRº OPER EDITADO
        # OP LIQUIDADO
        try:
            oper_liq = self.front[self.front['Status'].str.contains('Liquidado|CANCELADO', na=False)][['Contrato']].copy()
            contratos_tratados_liq = oper_liq['Contrato'].str.slice(0, 9)
            oper_liq.insert(1, "Nº OPERAÇÃO EDITADO", contratos_tratados_liq, True)

        except Exception as e:
            oper_liq = pd.DataFrame(columns=['Contrato', 'Nº OPERAÇÃO EDITADO'])
            print(f"Planilha de Operações Liquidadas está vazia {e}")

        tutela = self.front[self.front['Acao Judicial'] == 1][['CPF', 'Acao Judicial']].copy()

        # consig = self.consignataria

        # --- 1. Identifica TODAS as colunas que contêm contratos ---
        # Inclui a coluna original e as que foram extraídas pela função anterior.
        # Ajuste 'Contrato' se a sua coluna original tiver um nome diferente (ex: 'Identificador')
        # colunas_com_contratos = ['Contrato'] + [col for col in data_averbados.columns if 'Contrato Editado' in col]
        colunas_com_contratos = [col for col in data_averbados.columns if 'Contrato Editado' in col]

        # Remove duplicatas, caso o nome 'Contrato' já esteja na lista
        colunas_com_contratos = list(dict.fromkeys(colunas_com_contratos))

        # print(f"Colunas de contrato identificadas para análise: {colunas_com_contratos}")

        # --- 2. Loop único para criar as colunas de Esteira e Valor para CADA contrato ---
        # O enumerate nos dá um índice numérico (i) para criar nomes de coluna únicos.
        for i, nome_coluna_contrato in enumerate(colunas_com_contratos, start=1):
            # print(f"Processando coluna '{nome_coluna_contrato}'...")

            # Cria a coluna de Esteira correspondente
            data_averbados[f'Esteira_{i}'] = data_averbados[nome_coluna_contrato].map(
                front.set_index('Contrato')['Esteira'].to_dict()
            )

            # Cria a coluna de Valor da Parcela correspondente
            data_averbados[f'Valor_Unif_{i}'] = data_averbados[nome_coluna_contrato].map(
                semi_front.set_index('Contrato')['Prestacao'].to_dict()
            )

            # Puxa os valores de saldo da conciliação
            data_averbados[f'Saldo {i}'] = data_averbados[nome_coluna_contrato].map(
                semi_front.set_index('Contrato')['Saldo'].to_dict()
            )

            # Puxando os contratos liquidados (FORMA CORRIGIDA)
            # Cria a nova coluna 'OP LIQ {i}' com o resultado do map
            data_averbados[f'OP LIQ {i}'] = data_averbados[nome_coluna_contrato].map(
                oper_liq.set_index('Nº OPERAÇÃO EDITADO')['Contrato'].to_dict()
            )

            print(f'Verificar qual é o saldo do contrato "302298345": {data_averbados.loc[data_averbados[f"Contrato Editado {i}"] == "302298345", f"Saldo {i}"]}')

            # --- PASSO 2: PREPARAÇÃO E LIMPEZA DE DADOS ---
            # Agora que todas as colunas foram criadas, garantimos que sejam numéricas para os cálculos.
            data_averbados[f'Valor_Unif_{i}'] = pd.to_numeric(data_averbados[f'Valor_Unif_{i}'],
                                                              errors='coerce').fillna(0)
            data_averbados[f'Saldo {i}'] = pd.to_numeric(data_averbados[f'Saldo {i}'], errors='coerce').fillna(0)

            # --- PASSO 3: CONSTRUIR AS CONDIÇÕES E APLICAR A LÓGICA ---

            # Condição 1: Encontra todas as linhas onde o Saldo (já limpo) é >= 0
            condicao_saldo_positivo = data_averbados[f'Saldo {i}'] >= -1

            # Condição 2: Encontra onde um contrato liquidado foi efetivamente encontrado (FORMA CORRIGIDA E ROBUSTA)
            # .notna() garante que só pegamos as linhas onde o map retornou um valor, e não NaN.
            data_averbados[f'OP LIQ {i}'] = data_averbados[f'OP LIQ {i}'].fillna('')
            condicao_op_liq = data_averbados[f'OP LIQ {i}'] != ''

            # Ação: Nessas linhas, define o 'Valor_Unif' correspondente como 0
            # O operador | significa OU (se uma condição OU a outra for verdadeira)
            data_averbados.loc[(condicao_saldo_positivo | condicao_op_liq), f'Valor_Unif_{i}'] = 0
            # --- FIM DA NOVA LÓGICA ---

            # Condição de Operações Liquidadas, se a linha estiver preenchida vai lançar 0

        # --- 2.5 Puxa as liminares ---
        data_averbados["LIMINAR"] = data_averbados['CPF_Formatado'].map(tutela.set_index('CPF')['Acao Judicial'].to_dict())
        condicao_liminar = data_averbados['LIMINAR'] == 1

        # --- 3. Soma todos os valores encontrados (forma eficiente) ---

        # Pega a lista de todas as colunas de valor que acabamos de criar
        colunas_valores_unificados = [col for col in data_averbados.columns if 'Valor_Unif_' in col]

        if colunas_valores_unificados:
            # print(f"Somando os valores das colunas: {colunas_valores_unificados}")
            data_averbados['Soma'] = data_averbados[colunas_valores_unificados].sum(axis=1)
        else:
            print("Nenhuma coluna de valor encontrada. A coluna 'Soma' será inicializada com 0.")
            data_averbados['Soma'] = 0

        # --- 4. Cálculo da Diferença e Formatação Final ---

        # Garante que a coluna de Valor Prestacao é numérica antes do cálculo
        data_averbados['Valor Prestacao'] = pd.to_numeric(data_averbados['Valor Prestacao'], errors='coerce').fillna(0)

        data_averbados['Diff'] = data_averbados['Soma'] - data_averbados['Valor Prestacao']
        data_averbados['Diff'] = data_averbados['Diff'].round(2)

        # --- 5. Cria a coluna Lançar ---
        if consig == 'HOJE PREVIDÊNCIA PRIVADA':
            data_averbados = self.adiciona_peculio(data_averbados)
        else:
            data_averbados['Lançar'] = np.minimum(data_averbados['Soma'], data_averbados['Valor Prestacao'])
            data_averbados.loc[condicao_liminar, 'Lançar'] = 0

        # print("Cálculos de Soma e Diferença finalizados.")

        return data_averbados

    def arquivo_lancamento(self):
        # Cria o novo DataFrame
        data_averbados = self.trata_averbacao()
        front_trabalhado = self.tratamento_front()
        temp = data_averbados[data_averbados['Lançar'] != 0]
        colunas_alancar = ['Servidor', 'C P F', 'Matricula', 'Lançar', 'A D E']
        a_lancar = pd.DataFrame(temp[colunas_alancar])
        a_lancar = a_lancar.rename(columns={'Lançar': 'VALOR', 'Servidor': 'NOME', 'Matricula': 'MATRICULA'})


        # Calcule a SOMASE para cada categoria no Averbacoes Trabalhadas
        somas_por_categoria = data_averbados.groupby('CPF_Formatado')['Lançar'].transform('sum')
        data_averbados['SOMASE'] = somas_por_categoria
        data_averbados['SOMASE'] = data_averbados['SOMASE'].astype(float)


        # Calcula o Somase Front para cada CPF no DataFrame de Averbados, usando o front_trabalhado como referência
        data_averbados['SOMASE FRONT'] = ''

        soma_condicional_dict_averb = front_trabalhado.groupby('CPF')['Valor a lançar'].sum().to_dict()
        data_averbados['SOMASE FRONT'] = data_averbados['CPF_Formatado'].map(soma_condicional_dict_averb)

        
        data_averbados['SOMASE FRONT'] = data_averbados['SOMASE FRONT'].map('{:.2f}'.format).astype(float)

        # DIFF
        data_averbados['DIFF'] = data_averbados['SOMASE FRONT'] - data_averbados['SOMASE']

        # SOMASE NO FRONT TRABALHADO
        front_somase = front_trabalhado.groupby('CPF')['Valor a lançar'].transform('sum')
        front_trabalhado.insert(16, 'SOMASE FRONT', front_somase, True)
        front_trabalhado['SOMASE FRONT'] = front_trabalhado['SOMASE FRONT'].map('{:.2f}'.format).astype(float)

        front_trabalhado.insert(17, 'SOMASE AVERB', '', True)
        front_trabalhado.insert(18, 'DIFF', '', True)

        # Somase Averb no Front Trabalhado
        soma_condicional_dict_front = data_averbados.groupby('CPF_Formatado')['Lançar'].sum().to_dict()
        front_trabalhado['SOMASE AVERB'] = front_trabalhado['CPF'].map(soma_condicional_dict_front)
        front_trabalhado['DIFF'] = front_trabalhado['SOMASE FRONT'] - front_trabalhado['SOMASE AVERB'].astype(
            float)
    

        # Arredonda os números
        a_lancar['VALOR'] = a_lancar['VALOR'].astype(float)
        a_lancar['VALOR'] = a_lancar['VALOR'].map('{:.2f}'.format)

        # Cria colunas no meio do Averbações a Lançar
        if self.convenio in ['PREF SAO GONCALO', 'PREF DUQUE DE CAXIAS']:
            if datetime.now().month == 12 and datetime.now().day > 10:
                folha_inclusao = f'01{datetime.now().year + 1}'
            elif datetime.now().day < 10:
                folha_inclusao = f'{str(datetime.now().month).zfill(2)}{datetime.now().year}'
            else:
                folha_inclusao = f'{str(datetime.now().month + 1).zfill(2)}{datetime.now().year}'
        else:
            folha_inclusao = f'{str(datetime.now().month).zfill(2)}{datetime.now().year}'
    
        a_lancar.insert(3, 'COD ORGAO','', True)
    
        a_lancar.insert(5, 'FOLHA INCLUSAO', folha_inclusao, True)
    
        if self.convenio == 'PREF ARAGUAINA':
            a_lancar.insert(6, 'CODIGO DA VERBA', '816', True)
        elif self.convenio == 'PREF GOIANIA':
            a_lancar.insert(6, 'CODIGO DA VERBA', '4925', True)
        elif self.convenio == 'PREF TAUBATE':
            a_lancar.insert(6, 'CODIGO DA VERBA', '388', True)
        elif self.convenio == 'PREF DUQUE DE CAXIAS':
            a_lancar.insert(6, 'CODIGO DA VERBA', '10321', True)
        elif self.convenio == 'PREF SAO GONCALO':
            a_lancar.insert(6, 'CODIGO DA VERBA', '1546', True)
        elif self.convenio == 'PREV SAO GONCALO':
            a_lancar.insert(6, 'CODIGO DA VERBA', '344', True)
        # a_lancar['Valor Prestacao'] =  a_lancar['Valor Prestacao'].apply(substituir_virgula_por_ponto)
    
        # --- 1. data_averbados ---

        # SOMASE Interno (Averbados)
        # transform('sum') já mantém o índice alinhado, perfeito.
        data_averbados['SOMASE'] = data_averbados.groupby('CPF_Formatado')['Lançar'].transform('sum').round(2)

        # SOMASE Externo (Vem do Front)
        soma_condicional_dict_averb = front_trabalhado.groupby('CPF')['Valor a lançar'].sum().to_dict()

        # Mapeia e já preenche com 0 quem não for encontrado (fillna)
        data_averbados['SOMASE FRONT'] = data_averbados['CPF_Formatado'].map(soma_condicional_dict_averb).fillna(0).round(2)

        # Cálculo do DIFF
        data_averbados['DIFF'] = data_averbados['SOMASE FRONT'] - data_averbados['SOMASE']


        # --- 2. front_trabalhado ---

        # SOMASE Interno (Front)
        # 1. Garante que separador decimal seja ponto (se seu Excel estiver usando vírgula)
        # Se os números já estiverem com ponto, essa linha não atrapalha.
        front_trabalhado['Valor a lançar'] = front_trabalhado['Valor a lançar'].astype(str).str.replace(',', '.')

        # 2. Converte para NÚMERO (Float)
        # O errors='coerce' transforma textos inválidos em NaN (vazio) para não travar
        front_trabalhado['Valor a lançar'] = pd.to_numeric(front_trabalhado['Valor a lançar'], errors='coerce').fillna(0.0)

        # 3. Agora sua linha original vai funcionar
        front_somase = front_trabalhado.groupby('CPF')['Valor a lançar'].transform('sum').round(2)

        # Inserindo já com os dados (mais limpo que criar vazio e depois preencher)
        if 'SOMASE FRONT' not in front_trabalhado.columns:
            front_trabalhado.insert(16, 'SOMASE FRONT', front_somase)
        else:
            front_trabalhado['SOMASE FRONT'] = front_somase

        # SOMASE Externo (Vem do Averbados)
        soma_condicional_dict_front = data_averbados.groupby('CPF_Formatado')['Lançar'].sum().to_dict()

        # Cria a coluna SOMASE AVERB mapeando e preenchendo vazios com 0
        # Nota: Certifique-se que front_trabalhado['CPF'] e data_averbados['CPF_Formatado'] são idênticos (pontos/traços)
        front_trabalhado['SOMASE AVERB'] = front_trabalhado['CPF'].map(soma_condicional_dict_front).fillna(0).round(2)
        # Cálculo do DIFF
        front_trabalhado['DIFF'] = front_trabalhado['SOMASE FRONT'] - front_trabalhado['SOMASE AVERB']
    
        # Cria o arquivo Averbações Trabalhadas
        if self.convenio in ['PREF SAO GONCALO', 'PREF DUQUE DE CAXIAS']:
            if datetime.now().month == 12:
                if datetime.now().day > 10:
                    file_name = f'TRABALHADO CARTÃO {self.convenio} {self.consignataria} 01{datetime.now().year + 1}.xlsx'
                else:
                    file_name = f'TRABALHADO CARTÃO {self.convenio} {self.consignataria} {str(datetime.now().month).zfill(2)}-{datetime.now().year}.xlsx'
            else:
                if datetime.now().day > 10:
                    file_name = f'TRABALHADO CARTÃO {self.convenio} {self.consignataria} {str(datetime.now().month + 1).zfill(2)}-{datetime.now().year}.xlsx'
                else:
                    file_name = f'TRABALHADO CARTÃO {self.convenio} {self.consignataria} {str(datetime.now().month).zfill(2)}-{datetime.now().year}.xlsx'
        else:
            file_name = f'TRABALHADO CARTÃO {self.convenio} {self.consignataria} {str(datetime.now().month).zfill(2)}-{datetime.now().year}.xlsx'
    
        # Salva o DataFrame no arquivo Excel
        print(f"arquivo_lancamento: Salvando o arquivo de Averbados Trabalhados")
        try:
            data_averbados.to_excel(os.path.join(self.caminho, file_name), index=False)
        except Exception as e:
            print(f"arquivo_lancamento: ERRO AO SALVAR TRABALHADO CARTÃO {self.convenio}: {e}")
    
        # Cria o arquivo Averbações a Lançar
        if self.convenio in ['PREF SAO GONCALO', 'PREF DUQUE DE CAXIAS']:
            if datetime.now().month == 12:
                if datetime.now().day > 10:
                    file_lancar = f'LANCAMENTO CARTAO {self.convenio} {self.consignataria} 01{datetime.now().year + 1}.xlsx'
                else:
                    file_lancar = f'LANCAMENTO CARTAO {self.convenio} {self.consignataria} {str(datetime.now().month).zfill(2)}-{datetime.now().year}.xlsx'
            else:
                if datetime.now().day > 10:
                    file_lancar = f'LANCAMENTO CARTAO {self.convenio} {self.consignataria} {str(datetime.now().month + 1).zfill(2)}-{datetime.now().year}.xlsx'
                else:
                    file_lancar = f'LANCAMENTO CARTAO {self.convenio} {self.consignataria} {str(datetime.now().month).zfill(2)}-{datetime.now().year}.xlsx'
        else:
            file_lancar = f'LANCAMENTO CARTÃO {self.convenio} {self.consignataria} {str(datetime.now().month).zfill(2)}-{datetime.now().year}.xlsx'
    
        # Salva o arquivo de lancamento
        print(f"arquivo_lancamento: Salvando o arquivo de Lançamento Cartão")
        try:
            a_lancar.to_excel(os.path.join(self.caminho, file_lancar), index=False)
        except Exception as e:
            print(f"arquivo_lancamento: ERRO AO SALVAR LANCAMENTO CARTÃO {self.convenio}: {e}")

        # Cria o Front Trabalhado
        if self.convenio in ['PREF SAO GONCALO', 'PREF DUQUE DE CAXIAS']:
            if datetime.now().month == 12:
                if datetime.now().day > 10:
                    file_front = f'FRONT TRABALHADO {self.convenio} {self.consignataria} 01{datetime.now().year + 1}.xlsx'
                else:
                    file_front = f'FRONT TRABALHADO {self.convenio} {self.consignataria} {str(datetime.now().month).zfill(2)}-{datetime.now().year}.xlsx'
            else:
                if datetime.now().day > 10:
                    file_front = f'FRONT TRABALHADO {self.convenio} {self.consignataria} {str(datetime.now().month + 1).zfill(2)}-{datetime.now().year}.xlsx'
                else:
                    file_front = f'FRONT TRABALHADO {self.convenio} {self.consignataria} {str(datetime.now().month).zfill(2)}-{datetime.now().year}.xlsx'
        else:
            file_front = f'FRONT TRABALHADO {self.convenio} {self.consignataria} {str(datetime.now().month).zfill(2)}-{datetime.now().year}.xlsx'
            
        print(f"arquivo_lancamento: Salvando o arquivo de Front Trabalhado")
        try:
            front_trabalhado.to_excel(os.path.join(self.caminho, file_front), index=False)
        except Exception as e:
            print(f"DEBUG: ERRO AO SALVAR FRONT TRABALHADO {self.convenio}: {e}")


# print(tamanho_parte[0])
