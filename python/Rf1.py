import pandas as pd
import numpy as np
from datetime import datetime
import re
from thefuzz import fuzz
from python.ESTEIRAS import load_esteiras
from python.trata_conciliacao import TRATA_CONCILIACAO
from python.Andamento import ANDAMENTO
import os
import logging
import chardet
from itertools import combinations

# Mantendo variáveis globais do original
rejeitados = ['/']

class RF1:
    # O init foi adaptado para receber os DataFrames do server.py, mas prepara os dados
    # exatamente como o original esperava (convertendo tipos, etc.)
    def __init__(self, front, portal_file_list, convenio,  caminho, funcao=None, conciliacao=None, tacs=None, kobraki=None, extra_judicial=None):
        
        self.convenio = convenio
        self.caminho = caminho
        
        # --- ADAPTAÇÃO: Recebendo DataFrames do server.py ao invés de ler do disco ---

        # 1. Averbados
        self.averbados = portal_file_list if portal_file_list is not None else pd.DataFrame()
        # Mantendo a conversão de tipo original:
        if 'Valor reservado' in self.averbados.columns:
            # Parcela de Averbados já serão floats
            if self.averbados['Valor reservado'].dtype != "float64":
                self.averbados['Valor reservado'] = self.averbados['Valor reservado'].astype(str).str.replace("R$ ", "")
                self.averbados['Valor reservado'] = self.averbados['Valor reservado'].astype(str).str.replace(".", "")
                self.averbados['Valor reservado'] = self.averbados['Valor reservado'].astype(str).str.replace(",", ".")
                self.averbados['Valor reservado'] = pd.to_numeric(self.averbados['Valor reservado'], errors='coerce')
        else:
            # Garante a coluna caso venha vazio, para não quebrar a lógica original
            self.averbados['Valor reservado'] = 0.0

        # 2. Front
        self.front = front if front is not None else pd.DataFrame()

        # 3. Funcao
        self.funcao = funcao if funcao is not None else None

        # 4. Conciliação
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
        
        self.conciliacao.rename(columns={'RECEBIDO GERAL ': 'RECEBIDO GERAL'}, inplace=True)
        self.conciliacao.rename(columns={'TIPO OPERAÇÃO': 'PRODUTO', 'NOVO TIPO DE OPERAÇÃO': 'PRODUTO', 'PRODUTOS PELO D8': 'PRODUTO', 
                                         'PRODUTO D8': 'PRODUTO', 'PRODUTO PELO D8': 'PRODUTO', 'PRODUTO ATUALIZADO': 'PRODUTO',
                                         'TIPO DE OPERAÇÃO': 'PRODUTO'}, inplace=True)
        
        self.kobraki = kobraki if kobraki is not None else None

        self.extra_judicial = extra_judicial if extra_judicial is not None else None

        self.tacs = tacs if tacs is not None else None

        # --- GATILHO: Inicia a lógica original automaticamente ---
        logging.info("Iniciando lógica original do Consigfacil...")
        self.front_trabalhado = self.tratamento_front()
        self.averbados_func()


    # =========================================================================
    # DAQUI PARA BAIXO É A LÓGICA ORIGINAL INTACTA (Copy-Paste do seu arquivo)
    # =========================================================================

    def unifica_front_funcao(self):
        front = self.front
        funcao = self.funcao

        if funcao is None:
            print('\nDEBUG class ANDAMENTO -> funcao unifica_fron_funcao -> Arquivo "Função" é nulo, retornando "front" sem tratamento\n')
            return front
        # tipos dos contratos de cada dataframe
        '''print('Tipo da coluna Contrato do Front', front['Contrato'].dtype)
        print('Tipo da coluna NR_PROP do Funcao', funcao['NR_PROP'].dtype)'''

        contrato_front = front['Contrato']
        ccb_tratado = front['CCB'].astype(str).str.slice(0, 9).fillna(0).astype('float64')

        ccb_tratado = ccb_tratado.astype('int64')

        # Verifica se o que é andamento no front está no função, se tiver transforma em integrado
        contrato_funcao = funcao['NR_PROP']
        front.loc[front['Contrato'].isin(contrato_funcao) & (front['Esteira'].str.contains('ANDAMENTO|PENDENTE')), 'Esteira'] = 'INTEGRADO'

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

        # Preenche o resto das colunas necessárias com valores genéricos, para não ficarem vazias
        front_unif['Esteira'] = front_unif['Esteira'].fillna("INTEGRADO")
        front_unif['Orbital'] = front_unif['Orbital'].fillna("NAO")
        front_unif['Consignataria'] = front_unif['Consignataria'].fillna("CAPITAL CONSIG ")
        front_unif['Status'] = front_unif['Status'].fillna("INTEGRADO")
        front_unif['Acao Judicial'] = front_unif['Acao Judicial'].fillna("NAO")
        front_unif['Obito'] = front_unif['Obito'].fillna("NAO")

        print('front unif finalzin:\n', front_unif.tail())

        # front_unif.to_excel(rf"{self.caminho}\Teste_front.xlsx", index=False)

        return front_unif

    def tratamento_front_preliminar(self):
        front_consig = self.unifica_front_funcao()

        conciliacao = self.conciliacao.copy()

        # Insere as colunas vazias necessárias
        front_consig.insert(21, 'Saldo', '', True)
        front_consig.insert(22, 'Valor a lançar', '', True)
        front_consig.insert(23, 'PRAZO', '', True)
        front_consig.insert(24, 'OBS', '', True)

        print(f'Esteiras Únicas do front: {front_consig["Esteira"].unique()}')

        # Esteiras
        esteiras_permitidas = load_esteiras()
        
        
        # Vamos renomear a primeira coluna da conciliação
        conciliacao.rename(columns={conciliacao.columns[0]: 'CONTRATOS'}, inplace=True)
        # Converte para lista de colunas
        cols = list(conciliacao.columns)

        # Atualiza o DataFrame com novos nomes
        conciliacao.columns = cols
        conciliacao['CONTRATOS'] = conciliacao['CONTRATOS'].astype('Int64')

        # Adiciona a coluna de tipo da Conciliação
        print(f'colunas da conciliacao: {conciliacao.columns}')
        try:
            tipo_conci = front_consig['Contrato'].map(conciliacao.set_index('CONTRATOS')['PRODUTO'].to_dict())
        except Exception as e:
            print(f'Coluna PRODUTO não se encontra na conciliação. Erro: {e}')
            return False
        
        front_consig.insert(19, 'Tipo Conciliação', tipo_conci, True)

        # Adiciona só as esteiras que podem ser lançadas
        front_consig_esteiras = front_consig[front_consig['Esteira'].isin(esteiras_permitidas)].copy()

        # Trata coluna de Tipo da Conciliação
        front_consig_esteiras.loc[front_consig_esteiras['Tipo Conciliação'].isin([np.nan, '', ' - ']), 'Tipo Conciliação'] = front_consig_esteiras['Tipo Operacao']

        # -------------------------------- MARCAR TUDO QUE NÃO LANÇA ---------------------------------- #
        # Marca saldo positivo
        front_consig_validado_termino = self.validacao_termino_front(front_consig_esteiras)
        print(f'tipo de OBS antes de marcar OBS: {front_consig_validado_termino["OBS"].dtype}')
        front_consig_validado_termino.loc[front_consig_validado_termino['Saldo'] > -0.01, 'OBS'] = 'NÃO LANÇAR - SALDO POSITIVO'

        # Marca o que é ação judicial
        # No caso de Obito estiver estiver SIM e NÃO ao invés de 1 e 0
        front_consig_validado_termino['Acao Judicial'] = front_consig_validado_termino['Acao Judicial'].replace({'SIM': 1, 'NAO': 0})
        front_consig_validado_termino.loc[front_consig_validado_termino['Acao Judicial'] == 1, 'OBS'] = 'NÃO LANÇAR - AÇÃO JUDICIAL'

        # Marca o que é Óbito
        # No caso de ação judicial estiver estiver SIM e NÃO ao invés de 1 e 0
        # front_consig_validado_termino['Obito'] = front_consig_validado_termino['Obito'].replace({'SIM': 1, 'NAO': 0})
        # front_consig_validado_termino.loc[front_consig_validado_termino['Obito'] == 1, 'OBS'] = 'NÃO LANÇAR - ÓBITO'
 
        # Marca tudo que é orbital
        front_consig_validado_termino.loc[(front_consig_validado_termino['Orbital'].str.contains('SIM', na=False) & (front_consig_validado_termino['OBS'] == '')), 'OBS'] = 'NÃO LANÇAR - ORBITAL'

        # Marcar liquidados em StatusContrato
        front_consig_validado_termino.loc[(front_consig_validado_termino['Status'].str.contains('Liquidado|CANCELADO', na=False)), 'OBS'] = 'NÃO LANÇAR - LIQUIDADO'

        # TIRAR BANCO OUTROS e FUTURO
        front_consig_validado_termino.loc[(front_consig_validado_termino['Consignataria'].str.contains('OUTROS|FUTURO', na=False)), 'OBS'] = 'NÃO LANÇAR - BANCO ERRADO'

        front_consig_validado_termino['Contrato'] = front_consig_validado_termino['Contrato'].astype('int64')

        # Marca para tirar o que é ADIANTAMENTO SALARIAL de Tipo Operacao
        front_consig_validado_termino.loc[front_consig_validado_termino['Tipo Operacao'].str.contains('ADIANTAMENTO SALARIAL', na=False), 'OBS'] = 'NÃO LANÇAR - ADIANTAMENTO SALARIAL'

        # Marca tudo que não é cartão
        front_consig_validado_termino.loc[front_consig_validado_termino['Tipo Operacao'] == 'EMPRESTIMO', 'OBS'] = "NÃO LANÇAR - EMPRESTIMO"

        # Salva com os NÃO LANÇAR
        # Dentro do seu validador (ex: python/Consigfacil.py)
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
        print(f'Comprimento de front_consig: {len(front_consig)}')


        if front_consig is False:
            print("DEBUG: O tratamento preliminar do front falhou. Verifique os erros anteriores.")
            return False

        # Separa apenas o que retornou como "cartão de crédito" no tipo de conciliação
        '''front_consig_cartao_conciliacao = front_consig[front_consig['Tipo Operacao'].str.contains('Cartão de Crédito|CARTAO DE CREDITO|CARTÃO DE CRÉDITO', na=False)].copy()
        print(f'Comprimento de front_consig_cartao_conciliacao: {len(front_consig_cartao_conciliacao)}')'''

        # Separar o que não é cartão de crédito da conciliação
        # front_consig_nao_cartao = front_consig[~front_consig['Tipo Conciliação'].str.contains('Cartão de Crédito', na=False)].copy()

        # Pegar o que é CARTAO DE CREDITO do front
        # condicao_cartao = ['CARTAO DE CREDITO']
        # front_consig_cartao_front = front_consig_nao_cartao[front_consig_nao_cartao['Tipo Operacao'].isin(condicao_cartao)].copy()
        # Faz concat dos dois dataframes
        front_consig_trabalhado = front_consig.copy()

        # ------------------------------- TIRA O QUE É ADIANTAMENTO SALARIAL ------------------------------- #
        front_consig_trabalhado = front_consig_trabalhado[~front_consig_trabalhado['OBS'].str.contains('NÃO LANÇAR - ADIANTAMENTO SALARIAL', na=False)].copy()
        print(f'Comprimento de front_consig_trabalhado: {len(front_consig_trabalhado)}')

        # ---------------------------------- TIRAR AÇÃO JUDICIAL DO FRONT ---------------------------------- #
        front_consig_trabalhado = front_consig_trabalhado.loc[front_consig_trabalhado['Acao Judicial'] != 1].copy()
        print(f'Comprimento de front_consig_trabalhado pós ação judicial: {len(front_consig_trabalhado)}')

        # ---------------------------------- TIRAR ÓBITO DO FRONT ---------------------------------- #
        # front_consig_trabalhado = front_consig_trabalhado.loc[front_consig_trabalhado['Obito'] != 1].copy()
        
        # ------------------------------------ INSERE A COLUNA DE SALDO ------------------------------------- #

        front_consig_trabalhado.loc[front_consig_trabalhado['Saldo'] > -0.01, 'Valor a lançar'] = 0
        front_consig_trabalhado = front_consig_trabalhado[front_consig_trabalhado['Valor a lançar'] > 0].copy()
        print(f'Comprimento de front_consig_trabalhado pós saldo: {len(front_consig_trabalhado)}')


        # -------------------------------------- TIRA EMPRESTIMO ----------------------------------------------- #
        front_consig_trabalhado = front_consig_trabalhado[~front_consig_trabalhado['OBS'].str.contains('NÃO LANÇAR - EMPRESTIMO', na=False)].copy()
        # --------------------------------------- TIRA BANCO OUTROS ----------------------------------------- #
        front_consig_trabalhado = front_consig_trabalhado[~front_consig_trabalhado['Consignataria'].str.contains('OUTROS|FUTURO', na=False)].copy()
        print(f'Comprimento de front_consig_trabalhado pós outros bancos: {len(front_consig_trabalhado)}')

        # ----------------------------------------- TIRA LIQUIDADOS ----------------------------------------- #
        front_consig_trabalhado = front_consig_trabalhado[~front_consig_trabalhado['Status'].str.contains('Liquidado|CANCELADO', na=False)].copy()
        print(f'Comprimento de front_consig_trabalhado pós liquidados: {len(front_consig_trabalhado)}')


        print('DEBUG: Esteiras finais do front trabalhado')
        try:
            front_consig_trabalhado.to_excel(
                os.path.join(self.caminho, f"FRONT TRABALHADO {self.convenio}.xlsx"),
                index=False, 
            )
        except Exception as e:
            print(f"DEBUG: ERRO AO SALVAR FRONT TRABALHADO: {e}")

        return front_consig_trabalhado

    def trata_conciliacao(self):
        # conciliacao_tratado_teste = teste_conciliacao.trata_conciliacao()
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
        colunas_inad = conciliacao_tratado.filter(like='INAD ').columns
        for col in colunas_d8:
            tipos = conciliacao_tratado[col].apply(type).value_counts()
            '''print(f"Coluna {col}:")
            print(tipos)
            print()'''
        conciliacao_tratado[colunas_d8] = conciliacao_tratado[colunas_d8].apply(pd.to_numeric, errors='coerce')
        conciliacao_tratado[colunas_inad] = conciliacao_tratado[colunas_inad].apply(pd.to_numeric, errors='coerce')

        soma_d8 = conciliacao_tratado.filter(like='D8 ').sum(axis=1)
        inad_d8 = conciliacao_tratado.filter(like='INAD ').sum(axis=1)

        super_saldo = soma_d8 + inad_d8

        # 2. Calcular prestação * prazo
        prestacao_vezes_prazo = conciliacao_tratado['PRESTAÇÃO'] * conciliacao_tratado['PRAZO']

        # 3. Calcular o resultado final
        conciliacao_tratado['Pago'] = super_saldo - prestacao_vezes_prazo
        conciliacao_tratado['Saldo'] = conciliacao_tratado['Pago'] + conciliacao_tratado['RECEBIDO GERAL']

        return conciliacao_tratado


    def validacao_termino_front(self, front):
        front_copy = front.copy()
        teste_conciliacao = TRATA_CONCILIACAO(self.conciliacao, self.kobraki, self.tacs, self.extra_judicial)
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


    def averbados_func(self):
        # Contse do Credbase no relatório de averbados
        front_consig = self.front_trabalhado
        averbados = self.averbados
        # Remove as linhas preenchidas de Data de finalização
        averbados['Data de finalização'] = averbados['Data de finalização'].fillna('')
        averbados = averbados[averbados['Data de finalização'] == '']

        if front_consig is False:
            print("DEBUG: O tratamento preliminar do front falhou. Verifique os erros anteriores.")
            return False

        # Remover de Averbados algumas colunas
        colunas_para_remover = ['Validade', 'Saldo de reserva', 'Data', 'IP', 'Código', '%']

        averbados = averbados.drop(columns=colunas_para_remover, errors='ignore')

        # Adicionar outras colunas em Averbados
        # averbados.insert(5, 'CONCAT', '', True)
        averbados['VALOR A LANÇAR MATRICULA'] = ''
        # averbados['VALOR A LANÇAR CPF'] = ''
        averbados['CONTSE CPF'] = ''
        averbados['SOMASE CRED'] = ''
        # averbados['PARCELA CPF'] = ''
        # averbados['LANÇAR'] = ''
        # averbados['FALTA ATRIBUIR'] = ''
        # averbados['DIFF'] = ''

        # Separa o que não é NÃO em outra planilha
        # averbado_novo = averbados[averbados['OBS'] != 'NÃO'].copy()
        averbado_novo = averbados.copy()

        # CONTSEs
        averbado_novo['CONTSE CPF'] = averbado_novo.groupby('CPF')['CPF'].transform('count')
        
        # A mesma coisa de cima só que com CPF
        front_consig['SOMASE LOCAL POR CPF']  = front_consig.groupby('CPF')['Valor a lançar'].transform('sum')
        # soma_condicional_dict_averb_cpf = front_preliminar.groupby('CPF')['SOMASE LOCAL POR CPF'].sum().to_dict()


        # Puxa para o averbado_novo o valor que está no Front
        # front_preliminar['MATRICULA_ENCONTRADA_1'] = front_preliminar['MATRICULA_ENCONTRADA_1'].astype('int64')
        somase_cred = front_consig.groupby('CPF')['Valor a lançar'].sum().to_dict()
        parcelas_front_cpf = front_consig.groupby('CPF')['Valor a lançar'].sum().to_dict()
        averbado_novo['SOMASE CRED'] = averbado_novo['CPF'].map(somase_cred).fillna(0)
        # averbado_novo['PARCELA CPF'] = averbado_novo['CPF'].map(parcelas_front_cpf).fillna(0)

        # front_preliminar.drop(columns=['SOMASE LOCAL POR CPF'], inplace=True)


        # =============================================================================
        #        INÍCIO DA NOVA LÓGICA VETORIZADA (SUBSTITUI O SEU LOOP 'FOR')
        # =============================================================================

        def distribuicao_valores(averbado_trabalhado):
            # IMPORTANTE: Garanta que as colunas de valores são numéricas, não texto.
            # O .to_numeric(errors='coerce') converte o que for possível para número e põe NaN no que não for.
            averbado_novo = averbado_trabalhado

            averbado_novo['Valor reservado'] = pd.to_numeric(averbado_novo['Valor reservado'], errors='coerce').fillna(0)
            averbado_novo['SOMASE CRED'] = pd.to_numeric(averbado_novo['SOMASE CRED'], errors='coerce').fillna(0)

            # 1. Calcula a soma ACUMULADA da reserva dentro de cada grupo de CPF.
            # Esta é a "mágica" que substitui a necessidade de um loop.
            averbado_novo['SOMA ACUMULADA DA RESERVA'] = averbado_novo.groupby('CPF')['Valor reservado'].cumsum()

            # 2. Calcula o valor que JÁ FOI ALOCADO para as linhas ANTERIORES.
            # É a soma acumulada até a linha atual, menos o valor da própria linha.
            alocado_anteriormente = averbado_novo['SOMA ACUMULADA DA RESERVA'] - averbado_novo['Valor reservado']
            averbado_novo['ALOCADO ANTERIORMENTE'] = alocado_anteriormente

            # 3. Calcula o saldo restante do SOMASE ANTES de processar a linha atual.
            saldo_restante = averbado_novo['SOMASE CRED'] - alocado_anteriormente

            # 4. O valor a lançar é o MÍNIMO entre o que a reserva da linha pede e o saldo que ainda temos.
            # Usamos .clip(0) para garantir que o saldo não seja negativo (se já estourou, é 0).
            valor_a_lancar = np.minimum(averbado_novo['Valor reservado'], saldo_restante.clip(0))
            # averbado_novo['VALOR A LANÇAR CPF'] = averbado_novo['VALOR A LANÇAR CPF'].round(2)
            averbado_novo['LANÇAR'] = valor_a_lancar.round(2)

            # averbado_novo.loc[averbado_novo['VALOR A LANÇAR CPF'] == 0, 'OBS'] = 'NÃO'

            # 7. Vamos criar a coluna Diff para lançar os parciais
            somase_lancar = averbado_novo.groupby('CPF')['LANÇAR'].transform('sum')
            averbado_novo['DIFF'] = somase_lancar - averbado_novo['SOMASE CRED']
            averbado_novo['DIFF'] = averbado_novo['DIFF'].round(2)

            # 8. Adiciona a coluna de SITUAÇÃO DE DESCONTO para TOTAL ou PARCIAL
            averbado_novo['SITUAÇÃO DE DESCONTO'] = ''
            averbado_novo.loc[averbado_novo['DIFF'] < 0, 'SITUAÇÃO DE DESCONTO'] = 'PARCIAL'
            averbado_novo.loc[averbado_novo['DIFF'] >= 0, 'SITUAÇÃO DE DESCONTO'] = 'TOTAL'

            return averbado_novo

            # 7. (Opcional) Remove a coluna auxiliar que criamos.
        # averbado_novo = averbado_novo.drop(columns=['SOMA ACUMULADA DA RESERVA'])

        averbado_finalizado = distribuicao_valores(averbado_novo)

        print('DEBUG: Averbados após cálculo vetorizado:')
        try:
            averbado_finalizado.to_excel(os.path.join(self.caminho, f"AVERBADO TRABALHADO {self.convenio}.xlsx"), index=False)
        except Exception as e:
            print(f"DEBUG: ERRO AO SALVAR AVERBADOS TRABALHADO: {e}")