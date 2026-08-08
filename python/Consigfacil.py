import pandas as pd
import numpy as np
from datetime import datetime
import re
from thefuzz import fuzz
from python.ESTEIRAS import load_esteiras
from python.trata_conciliacao import TRATA_CONCILIACAO
from python.Andamento import ANDAMENTO
from python.TrataOrbital import TRATA_ORBITAL
from python.funcoes_comuns import UNIFICA_FRONT_FUNC_ESTEIRAS
from python.Tratador_Front_Base import TratadorConsigfacil
import os
import logging
import chardet
from itertools import combinations
from python.acha_matriculas_consigfacil import ACHA_MATRICULA_CONSIGFACIL

# Mantendo variáveis globais do original
rejeitados = ['/']

class CONSIGFACIL:
    # O init foi adaptado para receber os DataFrames do server.py, mas prepara os dados
    # exatamente como o original esperava (convertendo tipos, etc.)
    def __init__(self, front, portal_file_list, convenio,  caminho, andamento_funcao=None, funcao=None, conciliacao=None, orbital=None,kobraki=None, extra_judicial=None, tacs=None, andamento_list=None):
        
        self.convenio = convenio
        self.caminho = caminho
        
        # --- ADAPTAÇÃO: Recebendo DataFrames do server.py ao invés de ler do disco ---

        # 1. Averbados
        self.averbados = portal_file_list if portal_file_list is not None else pd.DataFrame()
        # Mantendo a conversão de tipo original:
        if 'Valor da reserva' in self.averbados.columns:
            # Parcela de Averbados já serão floats
            if self.averbados['Valor da reserva'].dtype != 'float64':
                self.averbados['Valor da reserva'] = self.averbados['Valor da reserva'].astype(str).str.replace(".", "")
                self.averbados['Valor da reserva'] = self.averbados['Valor da reserva'].str.replace(",", ".")
                self.averbados['Valor da reserva'] = pd.to_numeric(self.averbados['Valor da reserva'], errors="coerce")
                self.averbados['Valor da reserva'] = pd.to_numeric(self.averbados['Valor da reserva'], errors="coerce")
        else:
            # Garante a coluna caso venha vazio, para não quebrar a lógica original
            self.averbados['Valor da reserva'] = 0.0

        # 2. Front
        self.front = front if front is not None else pd.DataFrame()

        # 3. Funcao
        self.funcao = funcao if funcao is not None else None
        self.andamento_funcao = andamento_funcao if andamento_funcao is not None else None


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
        
        self.orbital = orbital if orbital is not None else None
        
        self.kobraki = kobraki if kobraki is not None else None

        self.extra_judicial = extra_judicial if extra_judicial is not None else None

        self.tacs = tacs if tacs is not None else None
        
        # 5. Andamento
        self.andamento = andamento_list if andamento_list is not None else pd.DataFrame()

        # Esteiras
        self.condicoes_1 = load_esteiras()

        # 1. Instancia a classe
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
        self.front_final_consig.to_excel(os.path.join(self.caminho, f"FRONT FINAL CONSIG {self.convenio} {datetime.now().strftime("%m-%Y")}.xlsx"), index=False)

        front_semi_trabalhado_preliminar = TratadorConsigfacil(front=self.front_final_consig, conciliacao=self.conciliacao, convenio=self.convenio,
                                                               caminho=self.caminho, condicoes_1=self.condicoes_1, kobraki=self.kobraki, tacs=tacs, andamento=self.andamento)
        self.front_semi_trabalhado = front_semi_trabalhado_preliminar.tratamento_front_preliminar_base()
        self.front_trabalhado = self.front_semi_trabalhado[self.front_semi_trabalhado['OBS'].isin([pd.NA, np.nan, '', 'NÃO LANÇAR - ORBITAL'])]


        # Salvando Front Trabalhado
        print('DEBUG: Esteiras finais do front trabalhado')
        try:
            self.front_trabalhado.to_excel(
                os.path.join(self.caminho, f"FRONT TRABALHADO {self.convenio} {datetime.now().strftime("%m-%Y")}.xlsx"),
                index=False, 
            )
        except Exception as e:
            print(f"DEBUG: ERRO AO SALVAR FRONT TRABALHADO: {e}")

        # --- GATILHO: Inicia a lógica original automaticamente ---
        logging.info("Iniciando lógica original do Consigfacil...")


        # forma experimental de fazer o front trabalhado
        # =======================================================================================================================================================
        # =======================================================================================================================================================
        '''instancia_front = TratadorFrontBase(front=self.front_final_consig, conciliacao=self.conciliacao, convenio=self.convenio, caminho=self.caminho, orbital=self.orbital,
                                            condicoes_1=self.condicoes_1, kobraki=self.kobraki, tacs=self.tacs, extra_judicial=self.extra_judicial)

        # Criação do Front Semi Trabalhado
        self.front_semi_trabalhado = instancia_front.tratamento_front_preliminar_base()
        print(f"DEBUG: Tentando salvar FRONT SEMI TRABALHADO em: {self.caminho}")
        try:
            self.front_semi_trabalhado.to_excel(os.path.join(self.caminho, f"FRONT SEMI TRABALHADO {self.convenio} {datetime.now().strftime("%m-%Y")}.xlsx"), index=False)
            print("DEBUG: Arquivo salvo com sucesso!")
        except Exception as e:
            print(f"DEBUG: ERRO AO SALVAR: {e}")

        # Criação do Front Semi Trabalhado
        self.front_trabalhado_sem_obs = self.front_semi_trabalhado[self.front_semi_trabalhado["OBS"].isin([pd.NA, np.nan, ''])]

        self.front_trabalhado = self.verificacao_peculio_front(self.front_trabalhado_sem_obs)

        print('DEBUG: Esteiras finais do front trabalhado')
        try:
            self.front_trabalhado.to_excel(
                os.path.join(self.caminho, f"FRONT TRABALHADO {self.convenio} {datetime.now().strftime("%m-%Y")}.xlsx"),
                index=False, 
            )
        except Exception as e:
            print(f"DEBUG: ERRO AO SALVAR FRONT TRABALHADO: {e}")'''

        # =======================================================================================================================================================
        # =======================================================================================================================================================
        
        self.front_trabalhado = self.verificacao_peculio_front(self.front_trabalhado)
        self.averbados_func()


    # =========================================================================
    # DAQUI PARA BAIXO É A LÓGICA ORIGINAL INTACTA (Copy-Paste do seu arquivo)
    # =========================================================================

    def unifica_front_funcao(self):
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
        return self._processar_unificacao_front(
            base_adicional=self.funcao, 
            coluna_contrato='NR_PROP', 
            mapeamento=mapeamento, 
            verificar_ccb=True
        )
    
    def unifica_front_funcao_esteiras_andamento(self):
        mapeamento = {
            'Proposta': 'Contrato',
            'CPF/CNPJ': 'CPF',
            'MatrÍcula': 'Matricula',
            'Cliente': 'Nome',
            'Quantidade de Parcelas': 'Prazo',
            'Valor da Parcela': 'Prestacao',
            'Descrição do Produto': 'Tipo Operacao',
            'Descrição da Atividade': 'Esteira',
            'Descrição EMPREGADOR': 'Convenio'
        }
        return self._processar_unificacao_front(
            base_adicional=self.andamento_funcao, 
            coluna_contrato='Proposta', 
            mapeamento=mapeamento, 
            verificar_ccb=False
        )

    # =====================================================================
    # FUNÇÃO MESTRE QUE PROCESSA A LÓGICA (EVITANDO REPETIÇÃO)
    # =====================================================================
    def _processar_unificacao_front(self, base_adicional, coluna_contrato, mapeamento, verificar_ccb=False):
        front = self.front

        if base_adicional is None or base_adicional.empty:
            print('\nDEBUG -> Base adicional é nula ou vazia. Retornando "front" sem tratamento.\n')
            return front

        contrato_front = front['Contrato']
        contratos_base = base_adicional[coluna_contrato].astype('int64')

        # 1. Transforma em INTEGRADO o que for andamento/pendente no front e constar na base
        front.loc[front['Contrato'].isin(contratos_base) & (front['Esteira'].str.contains('ANDAMENTO|PENDENTE')), 'Esteira'] = 'INTEGRADO'

        # 2. Remove da base adicional os contratos que já existem no Front
        base_tratada = base_adicional[~base_adicional[coluna_contrato].isin(contrato_front)].copy()

        # 3. Filtro extra de CCB (usado apenas pela unifica_front_funcao)
        if verificar_ccb:
            ccb_tratado = front['CCB'].astype(str).str.slice(0, 9).fillna(0).astype('float64').astype('int64')
            base_tratada = base_tratada[~base_tratada[coluna_contrato].isin(ccb_tratado)].copy()

        # 4. Filtra e renomeia as colunas usando o mapeamento fornecido
        base_ajustada = base_tratada[list(mapeamento.keys())].rename(columns=mapeamento)

        # DEBUG: Verifica o contrato 301120431 na base já ajustada (buscando pela coluna certa: 'Contrato')
        print(f'Contrato 301120431 está na base ainda?\n{base_ajustada.loc[base_ajustada["Contrato"] == 301120431, "Contrato"]}')

        # 5. Junta o Front com a Base Tratada
        front_unif = pd.concat([front, base_ajustada], ignore_index=True)

        # 6. Preenche valores genéricos onde ficou nulo
        front_unif['Esteira'] = front_unif['Esteira'].fillna("INTEGRADO")
        front_unif['Orbital'] = front_unif['Orbital'].fillna("NAO")
        front_unif['Consignataria'] = front_unif['Consignataria'].fillna("CAPITAL CONSIG")
        front_unif['Status'] = front_unif['Status'].fillna("INTEGRADO")
        front_unif['Acao Judicial'] = front_unif['Acao Judicial'].fillna("NAO")
        front_unif['Obito'] = front_unif['Obito'].fillna("NAO")

        print('front unif finalzin:\n', front_unif.tail())

        return front_unif

    def tratamento_front_preliminar(self):
        front_consig = self.front_final_consig
        # front_consig = self.unifica_front_funcao()

        conciliacao = self.conciliacao.copy()

        orbital = self.orbital

        # Insere as colunas vazias necessárias
        front_consig.insert(21, 'Saldo', '', True)
        front_consig.insert(22, 'Valor a lançar', '', True)
        front_consig.insert(23, 'PRAZO', '', True)
        front_consig.insert(24, 'OBS', '', True)

        print(f'Esteiras Únicas do front: {front_consig["Esteira"].unique()}')
        
        
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
        front_consig_esteiras = front_consig.copy()

        front_consig_esteiras.loc[~front_consig_esteiras['Esteira'].isin(self.condicoes_1), 'OBS'] = 'NÃO LANÇAR - ESTEIRA NÃO PERMITIDA'

        # Trata coluna de Tipo da Conciliação
        front_consig_esteiras.loc[front_consig_esteiras['Tipo Conciliação'].isin([np.nan, '', ' - ']), 'Tipo Conciliação'] = front_consig_esteiras['Tipo Operacao']
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
            valores_encontrados_str = valores_encontrados.astype(str)
            front_consig.loc[filtro_esteira, 'Prestacao'] = valores_encontrados_str 

        # front_consig = front_consig[front_consig['Esteira'].isin(esteiras_permitidas)].copy()

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

        # Marca Prazo - Já está marcando "NÃO LANÇAR - PRAZO" dentro da função andamento_func_front
        objeto_andamento = ANDAMENTO(self.front_final_consig, self.convenio, self.caminho, self.andamento, self.funcao) # if self.convenio != 'GOV. MATO GROSSO' else ANDAMENTO_PROVISORIO(self.front, self.convenio, self.caminho, self.andamento, self.funcao)
        front_com_prazo = objeto_andamento.andamento_func_front()
        front_consig_validado_termino['PRAZO'] = front_consig_validado_termino['Contrato'].astype(str).map(front_com_prazo.set_index('Contrato')['PRAZO'])
        front_consig_validado_termino['Contrato'] = front_consig_validado_termino['Contrato'].astype('int64')

        # Marca para tirar o que é ADIANTAMENTO SALARIAL de Tipo Operacao
        if self.convenio not in ['PREF. PALMAS']:
            front_consig_validado_termino.loc[front_consig_validado_termino['Tipo Operacao'].str.contains('ADIANTAMENTO SALARIAL', na=False), 'OBS'] = 'NÃO LANÇAR - ADIANTAMENTO SALARIAL'

        # Marcar tudo que contem prazo como Não cartão
        '''front_com_prazo = front_consig_validado_termino[
        (front_consig_validado_termino['PRAZO'].notna()) & 
        (front_consig_validado_termino['PRAZO'] != '') & 
        (front_consig_validado_termino['PRAZO'] != 1) & 
        (front_consig_validado_termino['PRAZO'] != 0)
        ]'''

        front_com_prazo = front_consig_validado_termino[
        (front_consig_validado_termino['PRAZO'].notna()) & 
        (front_consig_validado_termino['PRAZO'] != '')
        ]

        if self.convenio in ['GOV. MARANHÃO']:
            front_consig_validado_termino = front_consig_validado_termino[(front_consig_validado_termino['PRAZO'].isna()) | (front_consig_validado_termino['PRAZO'] == '') | (front_consig_validado_termino['PRAZO'] == 1)]
        else:
            front_consig_validado_termino = front_consig_validado_termino[(front_consig_validado_termino['PRAZO'].isna()) | (front_consig_validado_termino['PRAZO'] == '')]
        '''else:
            front_consig_validado_termino = front_consig_validado_termino[(front_consig_validado_termino['PRAZO'].isna()) | (front_consig_validado_termino['PRAZO'] == '') | (front_consig_validado_termino['PRAZO'] == 1) | (front_consig_validado_termino['PRAZO'] == 0)]'''
        
        front_com_prazo.to_excel(fr'{self.caminho}\FRONT COM PRAZOS PORQUE EU SOU MUITO BURRO {datetime.now().strftime("%m-%Y")}.xlsx', index=False)
        # front_consig_validado_termino.to_excel(fr'{self.caminho}\front_consig_validado_termino.xlsx', index=False)
        front_consig_validado_termino.insert(22, 'Novo Tipo Operacao', 'CARTAO DE CREDITO')
        # print(f'O que está escrito na linha com contrato 512377\n{front_consig_validado_termino.loc[front_consig_validado_termino['Contrato'] == 512377, 'Novo Tipo Operacao']}')

        # 3. Quem TEM prazo (não vazio) -> NÃO é cartão (ex: Empréstimo ou Operação Comum)
        # Usamos o ~ dentro do .loc para inverter a máscara
        '''if self.convenio not in ['PREF. CAMPINA GRANDE', 'PREF. RECIFE', 'PREF. PORTO VELHO']:
            front_consig_validado_termino.loc[~mask_vazio_prazo, 'Novo Tipo Operacao'] = "CARTAO BENEFICIO"''' # Ou o nome que desejar


        # Salva com os NÃO LANÇAR
        # Dentro do seu validador (ex: python/Consigfacil.py)
        print(f"DEBUG: Tentando salvar FRONT SEMI TRABALHADO em: {self.caminho}")
        try:
            front_consig_validado_termino.to_excel(os.path.join(self.caminho, f"FRONT SEMI TRABALHADO {self.convenio} {datetime.now().strftime("%m-%Y")}.xlsx"), index=False)
            print("DEBUG: Arquivo salvo com sucesso!")
        except Exception as e:
            print(f"DEBUG: ERRO AO SALVAR: {e}")

        # --------------------------------------------------------------------------------------------- #
        return front_consig_validado_termino
        
    def tratamento_front(self):
        # front_consig = self.tratamento_front_preliminar()
        front_consig = self.front_semi_trabalhado
        print(f'Comprimento de front_consig: {len(front_consig)}')

        # Adiciona só as esteiras que podem ser lançadas
        esteiras_permitidas = load_esteiras()
        front_consig = front_consig[front_consig['Esteira'].isin(esteiras_permitidas)].copy()


        if front_consig is False:
            print("DEBUG: O tratamento preliminar do front falhou. Verifique os erros anteriores.")
            return False

        # Separa apenas o que retornou como "cartão de crédito" no tipo de conciliação
        front_consig_cartao_conciliacao = front_consig[front_consig['Novo Tipo Operacao'].str.contains('Cartão de Crédito|CARTAO DE CREDITO|CARTÃO DE CRÉDITO', na=False)].copy()
        print(f'Comprimento de front_consig_cartao_conciliacao: {len(front_consig_cartao_conciliacao)}')

        # Separar o que não é cartão de crédito da conciliação
        # front_consig_nao_cartao = front_consig[~front_consig['Tipo Conciliação'].str.contains('Cartão de Crédito', na=False)].copy()

        # Pegar o que é CARTAO DE CREDITO do front
        # condicao_cartao = ['CARTAO DE CREDITO']
        # front_consig_cartao_front = front_consig_nao_cartao[front_consig_nao_cartao['Tipo Operacao'].isin(condicao_cartao)].copy()
        # Faz concat dos dois dataframes
        front_consig_trabalhado = front_consig_cartao_conciliacao.copy()

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


        # -------------------------------------- TIRA O PRAZO ----------------------------------------------- #
        front_consig_trabalhado = front_consig_trabalhado[~front_consig_trabalhado['OBS'].str.contains('NÃO LANÇAR - PRAZO', na=False)].copy()
        print(f'Comprimento de front_consig_trabalhado pós prazo: {len(front_consig_trabalhado)}')
        # --------------------------------------- TIRA BANCO OUTROS ----------------------------------------- #
        front_consig_trabalhado = front_consig_trabalhado[~front_consig_trabalhado['Consignataria'].str.contains('OUTROS|FUTURO', na=False)].copy()
        print(f'Comprimento de front_consig_trabalhado pós outros bancos: {len(front_consig_trabalhado)}')

        # ----------------------------------------- TIRA LIQUIDADOS ----------------------------------------- #
        front_consig_trabalhado = front_consig_trabalhado[~front_consig_trabalhado['Status'].str.contains('Liquidado|CANCELADO', na=False)].copy()
        print(f'Comprimento de front_consig_trabalhado pós liquidados: {len(front_consig_trabalhado)}')

        # ---------------------------------------- AJUSTE PECÚLIO HOJE --------------------------------------- #
        front_consig_trabalhado = self.verificacao_peculio_front(front_consig_trabalhado)


        print('DEBUG: Esteiras finais do front trabalhado')
        try:
            front_consig_trabalhado.to_excel(
                os.path.join(self.caminho, f"FRONT TRABALHADO {self.convenio} {datetime.now().strftime("%m-%Y")}.xlsx"),
                index=False, 
            )
        except Exception as e:
            print(f"DEBUG: ERRO AO SALVAR FRONT TRABALHADO: {e}")

        return front_consig_trabalhado


    def validacao_termino_front(self, front):
        front_copy = front.copy()
        teste_conciliacao = TRATA_CONCILIACAO(self.conciliacao, self.kobraki, self.tacs)
        conciliacao_tratado = teste_conciliacao.trata_conciliacao()

        # Certifica que todos os contratos no Credbase trabalhado são do mesmo tipo
        # cred['Codigo_Credbase'] = cred['Codigo_Credbase'].astype(str)

        conciliacao_tratado['CONTRATOS'] = conciliacao_tratado['CONTRATOS'].astype('float').astype('Int64')
        # conciliacao_tratado['CONTRATOS'] = conciliacao_tratado['CONTRATOS'].astype('Int64')

        print('DEBUG: Colunas da conciliação tratada')
        try:
            conciliacao_tratado.to_excel(os.path.join(self.caminho, f"Conciliacao_TESTE {datetime.now().strftime("%m-%Y")}.xlsx"), index=False)
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
    

    def orbital_tratado(self, front_para_separar):
        if self.convenio == 'PREF CAJAMAR':
            orbital_preparado = front_para_separar.loc[
                front_para_separar['Convenio'].str.contains('PREF.CAJAMAR CC', case=False, na=False),
                ['Contrato', 'Nome', 'CPF', 'vlPrestacao']
            ].copy()
        elif self.convenio == 'GOV MT':
            orbital_preparado = front_para_separar.loc[
                front_para_separar['Convenio'].str.contains('GOV MT PL CAPIT|GOV MT PLCARTOS|GOV MT CB|GOV MT CARTOS C|GOVMT CARTOS CB', case=False, na=False),
                ['Contrato', 'Nome', 'CPF', 'vlPrestacao']
            ].copy()
        orbital_preparado.columns = ['Proposta', 'Cliente', 'CPF/CNPJ', 'VALOR DESCONTO']

        orbital_final = orbital_preparado

        orbital_final = orbital_final.drop_duplicates(subset=['Proposta'], keep='first')

        try:
            orbital_final.to_excel(os.path.join(self.caminho, f"ORBITAL TRABALHADO {self.convenio} {datetime.now().strftime("%m-%Y")}.xlsx"), index=False)
            print(f"DEBUG: ORBITAL TRABALHADO {self.convenio} salvo com sucesso!")
        except Exception as e:
            print(f"DEBUG: ERRO AO SALVAR ORBITAL TRABALHADO {self.convenio}: {e}")

        return orbital_final
    
    def verificacao_peculio_front(self, front_trabalhado):
        # Usando .copy() para não afetar o original por acidente
        averbados_unif = self.averbados
        if self.convenio in ['PREF. CAMPINA GRANDE', 'PREF. RECIFE', 'PREF. PORTO VELHO', 'PREF. NATAL']:
            averbados_unif = averbados_unif[averbados_unif['Modalidade'].isin(['Cartão de Crédito', 'Cartão Benefício (Compras)', 'Cartão Benefício', 'Cartão Benefício(96)', 'Cartão Benefício Compra'])]
        else:
            averbados_unif = averbados_unif[averbados_unif['Modalidade'] == 'Cartão de Crédito']

        front = front_trabalhado.copy()

        # 1. Preparar contagens (Calculamos nos averbados e mapeamos para o front)
        contagem_geral = averbados_unif['CPF'].value_counts()
        
        averbados_hp = averbados_unif[averbados_unif['Login'].str.contains('HOJE|HOJEPREV')]
        contagem_hp = averbados_hp['CPF'].value_counts()

        # 2. Mapear para o front (Garante que os dados alinhem pelo CPF)
        front['CONTSE HP'] = front['CPF'].map(contagem_hp).fillna(0)
        front['CONTSE GERAL'] = front['CPF'].map(contagem_geral).fillna(0)

        # 3. Garantir que 'Valor a lançar' é numérico para poder somar
        if front['Valor a lançar'].dtype != "float64":
            front['Valor a lançar'] = front['Valor a lançar'].astype(str).str.replace(".", "").str.replace(",", ".")
            front['Valor a lançar'] = pd.to_numeric(front['Valor a lançar'], errors='coerce').fillna(0)

        # 4. Aplicar a lógica com parênteses corretos
        # Se HP > 0 E Geral > 0 E HP == Geral (Ou seja, ele é 100% HP nos averbados)
        mask_peculio = (
            ((front['CONTSE HP'] > 0) & 
            (front['CONTSE GERAL'] > 0) & 
            (front['CONTSE HP'] == front['CONTSE GERAL'])) |
            (front['Consignataria'] == 'HOJE PREVIDÊNCIA PRIVADA')
        )
        
        front.loc[mask_peculio, 'Valor a lançar'] += 20

        # 5. Limpeza e retorno
        return front #.drop(columns=['CONTSE HP', 'CONTSE GERAL'])


    def averbados_func(self):
        # Contse do Credbase no relatório de averbados
        front_consig = self.front_trabalhado
        averbados = self.averbados

        if front_consig is False:
            print("DEBUG: O tratamento preliminar do front falhou. Verifique os erros anteriores.")
            return False
        
        if self.convenio in ['PREF. CAMPINA GRANDE', 'PREF. RECIFE', 'PREF. PORTO VELHO', 'PREF. NATAL','PREF. SANTA RITA']:
            averbados = averbados[averbados['Modalidade'].isin(['Cartão de Crédito', 'Cartão Benefício (Compras)', 'Cartão Benefício', 'Cartão Benefício(96)', 'Cartão Benefício Compra'])]
        else:
            averbados = averbados[averbados['Modalidade'].isin(['Cartão de Crédito', 'Cartão de Crédito [Previdência]', 'Cartão de Crédito [Prefeitura]'])]

        # Realoca a coluna "Login" para o início da planilha
        if averbados.columns[0] != 'Login':
            # 1. Cria a nova ordem: a coluna 'Login' + todas as outras colunas que não são 'Login'
            nova_ordem = ['Login'] + [col for col in averbados.columns if col != 'Login']

            # 2. Reorganiza o DataFrame com a nova lista
            averbados = averbados[nova_ordem]

        acha_matriculas = ACHA_MATRICULA_CONSIGFACIL(averbados, front_consig)
        front_preliminar = acha_matriculas.acha_matricula()

        # Remover de Averbados algumas colunas
        colunas_para_remover = ['Validade', 'Saldo de reserva', 'Data', 'IP', 'Código', '%']

        averbados = averbados.drop(columns=colunas_para_remover, errors='ignore')

        # Adicionar outras colunas em Averbados
        # averbados.insert(5, 'CONCAT', '', True)
        averbados['VALOR A LANÇAR MATRICULA'] = ''
        # averbados['VALOR A LANÇAR CPF'] = ''
        averbados['CONTSE MAT'] = ''
        averbados['CONTSE CPF'] = ''
        averbados['CONTSE SEQ'] = ''
        averbados['PARCELA FRONT'] = ''
        averbados['SOMASE CRED'] = ''
        # averbados['PARCELA CPF'] = ''
        # averbados['VALOR ATRIBUIDO'] = ''
        # averbados['FALTA ATRIBUIR'] = ''
        # averbados['DIFF'] = ''
        averbados['OBS'] = ''

        # Tira valor vazio do Valor da Reserva
        averbados['Valor da reserva'] = averbados['Valor da reserva'].fillna('')
        mask_nao = (averbados['Valor da reserva'] == 0) | \
                   (averbados['Valor da reserva'] == '0') | \
                   (averbados['Valor da reserva'] == '')

        # 3. Aplicamos a marcação e o filtro
        averbados.loc[mask_nao, 'OBS'] = 'NÃO'
        averbados = averbados[averbados['OBS'] != "NÃO"].copy()

        # Separa o que não é NÃO em outra planilha
        # averbado_novo = averbados[averbados['OBS'] != 'NÃO'].copy()
        averbado_novo = averbados.copy()

        # CONTSEs
        averbado_novo['CONTSE MAT'] = averbado_novo.groupby('Matrícula')['Matrícula'].transform('count')
        averbado_novo['CONTSE CPF'] = averbado_novo.groupby('CPF')['CPF'].transform('count')


        # Se for PREF. BAYEUX adiciona mais 20 reais para cada contrato
        '''if self.convenio in ['PREF. BAYEUX', 'PREF. PAÇO DO LUMIAR']:
            for idx, row in credbase.iterrows():
                credbase.loc[idx, 'Valor a lançar'] = credbase.loc[idx, 'Valor a lançar'] + 20
        elif self.convenio == 'GOV. MA':
            credbase.loc[credbase['Banco'] == 'BANCO HP', 'Valor a lançar'] += 20'''
        
         # Transforma matricula de averbados em inteiro
        try:
            averbado_novo['Matrícula'] = averbado_novo['Matrícula'].astype(str)
        except Exception as e:
            averbado_novo['Matrícula'] = pd.to_numeric(averbado_novo['Matrícula'].astype('int64'), errors='coerce')


        # SOMASE
        # Apenas remove o ".0" das matrículas que são números, mantendo os textos
        # front_preliminar['MATRICULA_ENCONTRADA_1'] = pd.to_numeric(front_preliminar['MATRICULA_ENCONTRADA_1'], errors='coerce').astype('Int64')
        front_preliminar['MATRICULA_ENCONTRADA_1'] = front_preliminar['MATRICULA_ENCONTRADA_1'].astype(str)
        
        front_preliminar['SOMASE LOCAL POR MATRICULA']  = front_preliminar.groupby('MATRICULA_ENCONTRADA_1')['Valor a lançar'].transform('sum')
        soma_condicional_dict_averb = front_preliminar.groupby('CPF')['SOMASE LOCAL POR MATRICULA'].sum().to_dict()

        # A mesma coisa de cima só que com CPF
        front_preliminar['SOMASE LOCAL POR CPF']  = front_preliminar.groupby('CPF')['Valor a lançar'].transform('sum')
        soma_condicional_dict_averb_cpf = front_preliminar.groupby('CPF')['Valor a lançar'].sum().to_dict()

        if self.orbital is not None:
            # Orbitall
            # orbitall = self.orbital_tratado(front_preliminar)

            prepara_orbital = TRATA_ORBITAL(self.orbital, self.front_semi_trabalhado, self.convenio, self.caminho)
            # complementar_orbital_df = front_trabalhado[front_trabalhado['Análise'].str.contains('NÃO LANÇAR - COMPLEMENTAR|NÃO LANÇAR - TELESAQUE|NÃO LANÇAR - ORBITAL', na=False)].copy()
            orbitall = prepara_orbital.orbital_tratado()
            
            averbado_novo['PARCELA FRONT'] = averbado_novo['CPF'].map(soma_condicional_dict_averb)
            # averbado_novo['PARCELA_CPF'] = averbado_novo['CPF'].map(soma_condicional_dict_averb_cpf)
            # 3. Soma por CPF no orbital
            somase_orbital = orbitall.groupby('CPF/CNPJ')['VALOR DESCONTO'].sum()

            front_preliminar = front_preliminar[front_preliminar['OBS'] != 'NÃO LANÇAR - ORBITAL'].copy()

            soma_condicional_dict_averb_cpf = front_preliminar.groupby('CPF')['Valor a lançar'].sum().to_dict()

            # 4. Combina tudo em um único dataframe
            soma_total = (
                pd.Series(soma_condicional_dict_averb_cpf)
                .add(somase_orbital, fill_value=0)
            )
            # soma_total_cpf = (soma_condicional_dict_averb_cpf.add(somase_orbital, fill_value=0))

            averbado_novo['SOMASE CRED'] = averbado_novo['CPF'].map(soma_total)
            # averbado_novo['PARCELA CPF'] = averbado_novo['CPF'].map(soma_total_cpf)
            # print(type(averbado_novo.loc[0, 'SOMASE']))
            averbado_novo['SOMASE CRED'] = averbado_novo['SOMASE CRED'].fillna(0)
            # averbado_novo['PARCELA CPF'] = averbado_novo['PARCELA CPF'].fillna(0)
        else:
            # Puxa para o averbado_novo o valor que está no Front
            # front_preliminar['MATRICULA_ENCONTRADA_1'] = front_preliminar['MATRICULA_ENCONTRADA_1'].astype('int64')
            parcelas_front = front_preliminar.groupby('MATRICULA_ENCONTRADA_1')['Valor a lançar'].sum().to_dict()
            somase_cred = front_preliminar.groupby('CPF')['Valor a lançar'].sum().to_dict()
            parcelas_front_cpf = front_preliminar.groupby('CPF')['Valor a lançar'].sum().to_dict()
            averbado_novo['PARCELA FRONT'] = averbado_novo['Matrícula'].map(parcelas_front).fillna(0)
            averbado_novo['SOMASE CRED'] = averbado_novo['CPF'].map(somase_cred).fillna(0)
            # averbado_novo['PARCELA CPF'] = averbado_novo['CPF'].map(parcelas_front_cpf).fillna(0)

        # Remove a coluna de SOMASE LOCAL POR MATRICULA
        front_preliminar.drop(columns=['SOMASE LOCAL POR MATRICULA'], inplace=True)
        # front_preliminar.drop(columns=['SOMASE LOCAL POR CPF'], inplace=True)


        # =============================================================================
        #                  LANÇAR PELO O QUE O CLIENTE DEVE DO FRONT
        # =============================================================================
        averbado_novo['Valor da reserva'] = pd.to_numeric(averbado_novo['Valor da reserva'], errors='coerce').fillna(0)
        averbado_novo['VALOR A LANÇAR MATRICULA'] = averbado_novo['PARCELA FRONT'] / averbado_novo['CONTSE MAT']
        # averbado_novo['VALOR A LANÇAR CPF'] = averbado_novo['PARCELA CPF'] / averbado_novo['CONTSE CPF']


        # =============================================================================
        #        INÍCIO DA NOVA LÓGICA VETORIZADA (SUBSTITUI O SEU LOOP 'FOR')
        # =============================================================================

        def distribuicao_valores(averbado_trabalhado):
            # IMPORTANTE: Garanta que as colunas de valores são numéricas, não texto.
            # O .to_numeric(errors='coerce') converte o que for possível para número e põe NaN no que não for.
            averbado_novo = averbado_trabalhado

            averbado_novo['Valor da reserva'] = pd.to_numeric(averbado_novo['Valor da reserva'], errors='coerce').fillna(0)
            if averbado_novo['SOMASE CRED'].dtype != "float64":
                averbado_novo['SOMASE CRED'] = averbado_novo['SOMASE CRED'].astype(str).str.replace(".", "").str.replace(",", ".")
                averbado_novo['SOMASE CRED'] = pd.to_numeric(averbado_novo['SOMASE CRED'], errors='coerce').fillna(0)

            # 1. Calcula a soma ACUMULADA da reserva dentro de cada grupo de CPF.
            # Esta é a "mágica" que substitui a necessidade de um loop.
            averbado_novo['SOMA ACUMULADA DA RESERVA'] = averbado_novo.groupby('CPF')['Valor da reserva'].cumsum()

            # 2. Calcula o valor que JÁ FOI ALOCADO para as linhas ANTERIORES.
            # É a soma acumulada até a linha atual, menos o valor da própria linha.
            alocado_anteriormente = averbado_novo['SOMA ACUMULADA DA RESERVA'] - averbado_novo['Valor da reserva']
            averbado_novo['ALOCADO ANTERIORMENTE'] = alocado_anteriormente

            # 3. Calcula o saldo restante do SOMASE ANTES de processar a linha atual.
            saldo_restante = averbado_novo['SOMASE CRED'] - alocado_anteriormente

            # 4. O valor a lançar é o MÍNIMO entre o que a reserva da linha pede e o saldo que ainda temos.
            # Usamos .clip(0) para garantir que o saldo não seja negativo (se já estourou, é 0).
            valor_a_lancar = np.minimum(averbado_novo['Valor da reserva'], saldo_restante.clip(0))

            # 5. Atribui o resultado final arredondado às colunas.
            averbado_novo['VALOR A LANÇAR MATRICULA'] = averbado_novo['VALOR A LANÇAR MATRICULA'].round(2)
            # averbado_novo['VALOR A LANÇAR CPF'] = averbado_novo['VALOR A LANÇAR CPF'].round(2)
            averbado_novo['VALOR A LANÇAR'] = valor_a_lancar.round(2)

            # 6. Preenche a coluna OBS para linhas que não receberam nada.
            averbado_novo.loc[averbado_novo['VALOR A LANÇAR MATRICULA'] == 0, 'OBS'] = 'NÃO'
            # averbado_novo.loc[averbado_novo['VALOR A LANÇAR CPF'] == 0, 'OBS'] = 'NÃO'

            # 7. Vamos criar a coluna Diff para lançar os parciais
            somase_lancar = averbado_novo.groupby('CPF')['VALOR A LANÇAR'].transform('sum')
            averbado_novo['DIFF'] = somase_lancar - averbado_novo['SOMASE CRED']
            averbado_novo['DIFF'] = averbado_novo['DIFF'].round(2)

            # 8. Adiciona a coluna de SITUAÇÃO DE DESCONTO para TOTAL ou PARCIAL
            averbado_novo['SITUAÇÃO DE DESCONTO'] = ''
            averbado_novo.loc[averbado_novo['DIFF'] < 0, 'SITUAÇÃO DE DESCONTO'] = 'PARCIAL'
            averbado_novo.loc[averbado_novo['DIFF'] >= 0, 'SITUAÇÃO DE DESCONTO'] = 'TOTAL'

            # 9. Novo Lançar total
            averbado_novo['NOVO LANÇAR TOTAL'] = averbado_novo['Valor da reserva'] - averbado_novo['DIFF']

            return averbado_novo

            # 7. (Opcional) Remove a coluna auxiliar que criamos.
        # averbado_novo = averbado_novo.drop(columns=['SOMA ACUMULADA DA RESERVA'])

        averbado_finalizado = distribuicao_valores(averbado_novo)
        

        if self.convenio in ['GOV. PIAUÍ',]:
            if (averbado_finalizado['SITUAÇÃO DE DESCONTO'] == 'PARCIAL').any():
                averbado_finalizado.loc[averbado_finalizado['SITUAÇÃO DE DESCONTO'] == 'PARCIAL', 'Valor da reserva'] = averbado_finalizado['NOVO LANÇAR TOTAL']
                averbado_finalizado = distribuicao_valores(averbado_finalizado)
        

        try:
            front_preliminar.to_excel(os.path.join(self.caminho, f'FRONT COM MATRICULAS TRATADAS {self.convenio} {datetime.now().strftime("%m-%Y")}.xlsx'), index=False)
        except Exception as e:
            print(f'DEBUG: ERRO AO SALVAR FRONT COM MATRICULAS TRATADAS: {e}')

        print('DEBUG: Averbados após cálculo vetorizado:')
        try:
            averbado_finalizado.to_excel(os.path.join(self.caminho, f"AVERBADO TRABALHADO {self.convenio} {datetime.now().strftime("%m-%Y")}.xlsx"), index=False)
        except Exception as e:
            print(f"DEBUG: ERRO AO SALVAR AVERBADOS TRABALHADO: {e}")