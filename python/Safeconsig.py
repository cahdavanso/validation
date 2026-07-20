from thefuzz import fuzz
import pandas as pd
import openpyxl
import numpy as np
from python.ESTEIRAS import load_esteiras
from python.trata_conciliacao import TRATA_CONCILIACAO
from python.TrataOrbital import TRATA_ORBITAL
from python.funcoes_comuns import UNIFICA_FRONT_FUNC_ESTEIRAS
from python.funcoes_comuns import TRATA_CONTRATOS
from datetime import datetime
import os
import logging
import re

class SAFECONSIG:
    def __init__(self, front, portal_file_list, convenio,  caminho, andamento_funcao=None, funcao=None, conciliacao=None, orbital=None,kobraki=None, extra_judicial=None, tacs=None):
        
        self.convenio = convenio
        self.caminho = caminho
        
        # --- ADAPTAÇÃO: Recebendo DataFrames do server.py ao invés de ler do disco ---

        # 1. Averbados
        self.averbados = portal_file_list if portal_file_list is not None else pd.DataFrame()
        # Mantendo a conversão de tipo original:
        if 'Parc. Reservada' in self.averbados.columns:
            # Parcela de Averbados já serão floats
            if self.averbados['Parc. Reservada'].dtype != 'float64':
                self.averbados['Parc. Reservada'] = self.averbados['Parc. Reservada'].astype(str).str.replace(".", "")
                self.averbados['Parc. Reservada'] = self.averbados['Parc. Reservada'].str.replace(",", ".")
                self.averbados['Parc. Reservada'] = pd.to_numeric(self.averbados['Parc. Reservada'], errors="coerce")
                self.averbados['Parc. Reservada'] = pd.to_numeric(self.averbados['Parc. Reservada'], errors="coerce")
        else:
            # Garante a coluna caso venha vazio, para não quebrar a lógica original
            self.averbados['Parc. Reservada'] = 0.0

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
        self.andamento = self.averbados[self.averbados['Prazo'] != "ROTATIVO"].copy()

        # --- GATILHO: Inicia a lógica original automaticamente ---
        logging.info("Iniciando lógica original do Consigfacil...")

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

        self.front_semi_trabalhado = self.tratamento_front_preliminar()
        self.front_trabalhado = self.tratamento_front()
        prepara_conciliacao = TRATA_CONCILIACAO(self.conciliacao, self.kobraki, self.tacs, self.extra_judicial)
        self.conciliacao_tratada = prepara_conciliacao.trata_conciliacao()
        
        self.averbados_func()

    def tratamento_front_preliminar(self):

        # O seu resultado final
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
        
        if 'Tipo Conciliação' not in front_consig.columns:
            front_consig.insert(19, 'Tipo Conciliação', tipo_conci, True)

        # Adiciona só as esteiras que podem ser lançadas
        # front_consig_esteiras = front_consig[front_consig['Esteira'].isin(esteiras_permitidas)].copy()
        front_consig_esteiras = front_consig
        front_consig_esteiras.loc[~front_consig_esteiras['Esteira'].isin(esteiras_permitidas), 'OBS'] = 'NÃO LANÇAR - ESTEIRA NÃO PERMITIDA'

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

        front_consig_validado_termino['Contrato'] = front_consig_validado_termino['Contrato'].astype('int64')

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
        
        front_consig = front_consig[front_consig['OBS'] == 'NÃO LANÇAR - ESTEIRA NÃO PERMITIDA'].copy()

        # Separa apenas o que retornou como "cartão de crédito" no tipo de conciliação
        front_consig_cartao_conciliacao = front_consig[~front_consig['Tipo Operacao'].str.contains('EMPRESTIMO|EMPRÉSTIMO', na=False)].copy()
        print(f'Comprimento de front_consig_cartao_conciliacao: {len(front_consig_cartao_conciliacao)}')

        # Separar o que não é cartão de crédito da conciliação
        # front_consig_nao_cartao = front_consig[~front_consig['Tipo Conciliação'].str.contains('Cartão de Crédito', na=False)].copy()

        # Pegar o que é CARTAO DE CREDITO do front
        # condicao_cartao = ['CARTAO DE CREDITO']
        # front_consig_cartao_front = front_consig_nao_cartao[front_consig_nao_cartao['Tipo Operacao'].isin(condicao_cartao)].copy()
        # Faz concat dos dois dataframes
        front_consig_trabalhado = front_consig_cartao_conciliacao.copy()


        # ---------------------------------- TIRAR AÇÃO JUDICIAL DO FRONT ---------------------------------- #
        front_consig_trabalhado = front_consig_trabalhado.loc[front_consig_trabalhado['Acao Judicial'] != 1].copy()
        print(f'Comprimento de front_consig_trabalhado pós ação judicial: {len(front_consig_trabalhado)}')

        # ---------------------------------- TIRAR ÓBITO DO FRONT ---------------------------------- #
        # front_consig_trabalhado = front_consig_trabalhado.loc[front_consig_trabalhado['Obito'] != 1].copy()
        
        # ------------------------------------ INSERE A COLUNA DE SALDO ------------------------------------- #

        front_consig_trabalhado.loc[front_consig_trabalhado['Saldo'] > -0.01, 'Valor a lançar'] = 0
        front_consig_trabalhado = front_consig_trabalhado[front_consig_trabalhado['Valor a lançar'] > 0].copy()
        print(f'Comprimento de front_consig_trabalhado pós saldo: {len(front_consig_trabalhado)}')

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
                os.path.join(self.caminho, f"FRONT TRABALHADO {self.convenio}.xlsx"),
                index=False, 
            )
        except Exception as e:
            print(f"DEBUG: ERRO AO SALVAR FRONT TRABALHADO: {e}")

        return front_consig_trabalhado
    
    def validacao_termino_front(self, front):
        # TRAVA DE SEGURANÇA: Remove qualquer coluna duplicada que tenha vindo dos merges anteriores
        front_copy = front.loc[:, ~front.columns.duplicated()].copy()
        
        teste_conciliacao = TRATA_CONCILIACAO(self.conciliacao, self.kobraki, self.tacs, self.extra_judicial)
        conciliacao_tratado = teste_conciliacao.trata_conciliacao()

        # Certifica que todos os contratos no Credbase trabalhado são do mesmo tipo
        conciliacao_tratado['CONTRATOS'] = conciliacao_tratado['CONTRATOS'].astype('float').astype('Int64')

        print('DEBUG: Colunas da conciliação tratada')
        try:
            conciliacao_tratado.to_excel(os.path.join(self.caminho, f"Conciliacao_TESTE.xlsx"), index=False)
        except Exception as e:
            print(f"DEBUG: ERRO AO SALVAR Conciliacao_TESTE.xlsx: {e}")

        # CORREÇÃO DO MAP: O .to_dict() agora está no lugar certo (dentro do parêntese do map)
        front_copy['Saldo'] = front_copy['Contrato'].map(conciliacao_tratado.set_index('CONTRATOS')['Saldo'].to_dict())

        front_copy.rename(columns={'Prestracao': 'Prestacao'}, inplace=True)
        
        # Garante que não tenhamos colunas duplicadas novamente após o rename
        front_copy = front_copy.loc[:, ~front_copy.columns.duplicated()]

        if front_copy['Prestacao'].dtype != 'float64':
            front_copy['Prestacao'] = front_copy['Prestacao'].astype(str).str.replace('.', '', regex=False)
            front_copy['Prestacao'] = front_copy['Prestacao'].str.replace(',', '.', regex=False)
            front_copy['Prestacao'] = pd.to_numeric(front_copy['Prestacao'], errors='coerce')

        print(f'Colunas de front_copy: {front_copy.columns}')
        
        # Valor que vai ser lançado
        # Agora o Pandas sabe que está lidando com uma Series vs Series
        valor_a_lancar = np.minimum(np.abs(front_copy['Saldo']).fillna(float(np.inf)), front_copy['Prestacao'])

        front_copy['Valor a lançar'] = valor_a_lancar

        return front_copy
    
    
    def verificacao_peculio_front(self, front_trabalhado):
        # Usando .copy() para não afetar o original por acidente
        front = front_trabalhado.copy()
        
        front.loc[front['Consignataria'] == 'HOJE PREVIDÊNCIA PRIVADA', 'Valor a lançar'] += 20

        # 5. Limpeza e retorno
        return front #.drop(columns=['CONTSE HP', 'CONTSE GERAL'])

    def adiciona_peculio(self, averbacoes):
        averbado_finalizado = averbacoes.copy()

        # 1. Cria uma coluna inicial zerada para acumular a soma
        averbado_finalizado['Soma_Calculada'] = 0.0

        # 2. Define o limite máximo de colunas que você criou (ajuste esse range se tiver mais que 10)
        # Se você tiver 'Esteira_1' até 'Esteira_5', o range deve ser range(1, 6)
        # Coloquei até 20 para garantir, o código verifica se a coluna existe.
        for i in range(1, 20):
            col_esteira = f'Esteira_{i}'
            col_valor = f'Valor_Unif_{i}'

            # Verifica se esse par de colunas existe no DataFrame
            if col_esteira in averbado_finalizado.columns and col_valor in averbado_finalizado.columns:
                # --- A LÓGICA MÁGICA ---
                # 1. Cria uma máscara: Linhas onde a Esteira X está na lista de permitidas
                mascara_esteira_valida = averbado_finalizado[col_esteira].isin(self.condicoes_1)

                # 2. Pega os valores correspondentes, preenche NaN com 0 para evitar erros
                valores_validos = averbado_finalizado.loc[mascara_esteira_valida, col_valor].fillna(0)

                # 3. Adiciona (Valor + 20) na coluna acumuladora
                # Importante: Só somamos nas linhas onde a máscara é Verdadeira
                averbado_finalizado.loc[mascara_esteira_valida, 'Soma_Calculada'] += (valores_validos + 20)

        # 3. Aplica a comparação final com o Valor Prestação (Teto)
        averbado_finalizado['Lançar'] = np.minimum(averbado_finalizado['Soma_Calculada'], averbado_finalizado['Parc. Reservada'])
        print(f'\naverbado_finalizado_peculio\n{averbado_finalizado['Parc. Reservada']}\n')

        # (Opcional) Remove a coluna temporária se não precisar mais
        averbado_finalizado = averbado_finalizado.drop(columns=['Soma_Calculada'])

        return averbado_finalizado
    
    def averbados_func(self):
        # Contse do Credbase no relatório de averbados
        front_consig = self.front_trabalhado
        if front_consig is False:
            print("DEBUG: O tratamento preliminar do front falhou. Verifique os erros anteriores.")
            return False
        averbado_a_tratar = TRATA_CONTRATOS(front_semi_trabalhado=self.front_semi_trabalhado, averbados=self.averbados, conciliacao_tratada=self.conciliacao_tratada, 
                                            nome_coluna_cpf="CPF", nome_coluna_contrato="Nº de Controle", nome_coluna_parcela="Parc. Reservada")
        averbados = averbado_a_tratar.trata_averbacao()
        averbados_prazo = averbados[averbados['Prazo'] != 'Prazo Rotativo'].copy()
        averbados = averbados[averbados['Prazo'] == 'Prazo Rotativo'].copy()

        

        front_preliminar = front_consig.copy()

        # Remover de Averbados algumas colunas
        colunas_para_remover = ['Regime de Contratação', 'Órgão / Secretaria', 'Lotação', 'Cargo/Função', 'Reservado em', 'Usuário Responsável pela Reserva', 'Validade da Reserva', 'Usuário Responsável pela Averbação', 
                                'CET Mensal', 'Valor do IOF', 'Valor Total de Extras', 'Início do Contrato', 'Final do Contrato', 'Prazo', 'Qtde. de Parcelas Descontadas', 'Valor Total a Pagar', 'Cód. Correspondente', 'Correspondente']

        averbados = averbados.drop(columns=colunas_para_remover, errors='ignore')

        cpf_tratado = averbados['CPF'].astype(str).str.zfill(11).str.replace(r'(\d{3})(\d{3})(\d{3})(\d{2})',  r'\1.\2.\3-\4', regex=True)

        averbados.insert(2, 'CPF Ponto e Traço', cpf_tratado, True)

        print(f'Amostra de averbados:\n{averbados.head()}')

        # Adicionar outras colunas em Averbados
        # averbados.insert(5, 'CONCAT', '', True)
        averbados['CONTSE CPF'] = ''
        averbados['CONTSE SEQ'] = ''
        averbados['SOMASE CRED'] = ''
        # averbados['PARCELA CPF'] = ''
        # averbados['VALOR ATRIBUIDO'] = ''
        # averbados['FALTA ATRIBUIR'] = ''
        # averbados['DIFF'] = ''
        averbados['OBS'] = ''

        # Tira valor vazio do Valor da Reserva
        averbados['Parc. Reservada'] = averbados['Parc. Reservada'].fillna('')
        mask_nao = (averbados['Parc. Reservada'] == 0) | \
                   (averbados['Parc. Reservada'] == '0') | \
                   (averbados['Parc. Reservada'] == '')

        # 3. Aplicamos a marcação e o filtro
        averbados.loc[mask_nao, 'OBS'] = 'NÃO'
        averbados = averbados[averbados['OBS'] != "NÃO"].copy()

        # Separa o que não é NÃO em outra planilha
        # averbado_novo = averbados[averbados['OBS'] != 'NÃO'].copy()
        averbado_novo = averbados.copy()

        # CONTSEs
        averbado_novo['CONTSE CPF'] = averbado_novo.groupby('CPF Ponto e Traço')['CPF Ponto e Traço'].transform('count')


        # A mesma coisa de cima só que com CPF
        front_preliminar['SOMASE LOCAL POR CPF']  = front_preliminar.groupby('CPF')['Valor a lançar'].transform('sum')
        # soma_condicional_dict_averb_cpf = front_preliminar.groupby('CPF')['SOMASE LOCAL POR CPF'].sum().to_dict()

        somase_cred = front_preliminar.groupby('CPF')['Valor a lançar'].sum().to_dict()
        averbado_novo['SOMASE CRED'] = averbado_novo['CPF Ponto e Traço'].map(somase_cred).fillna(0)


        # =============================================================================
        #        INÍCIO DA NOVA LÓGICA VETORIZADA (SUBSTITUI O SEU LOOP 'FOR')
        # =============================================================================

        def distribuicao_valores(averbado_trabalhado):
            # IMPORTANTE: Garanta que as colunas de valores são numéricas, não texto.
            # O .to_numeric(errors='coerce') converte o que for possível para número e põe NaN no que não for.
            averbado_novo = averbado_trabalhado

            averbado_novo['Parc. Reservada'] = pd.to_numeric(averbado_novo['Parc. Reservada'], errors='coerce').fillna(0)

            '''if averbado_novo['SOMASE CRED'].dtype != 'float64':
                averbado_novo['SOMASE CRED'] = averbado_novo['SOMASE CRED'].astype(str).str.replace('.', '').str.replace(',', '.')'''
            averbado_novo['SOMASE CRED'] = pd.to_numeric(averbado_novo['SOMASE CRED'], errors='coerce').fillna(0)

            # 1. Calcula a soma ACUMULADA da reserva dentro de cada grupo de CPF.
            # Esta é a "mágica" que substitui a necessidade de um loop.
            averbado_novo['SOMA ACUMULADA DA RESERVA'] = averbado_novo.groupby('CPF Ponto e Traço')['Parc. Reservada'].cumsum()

            # 2. Calcula o valor que JÁ FOI ALOCADO para as linhas ANTERIORES.
            # É a soma acumulada até a linha atual, menos o valor da própria linha.
            alocado_anteriormente = averbado_novo['SOMA ACUMULADA DA RESERVA'] - averbado_novo['Parc. Reservada']
            averbado_novo['ALOCADO ANTERIORMENTE'] = alocado_anteriormente

            # 3. Calcula o saldo restante do SOMASE ANTES de processar a linha atual.
            saldo_restante = averbado_novo['SOMASE CRED'] - alocado_anteriormente

            # 4. O valor a lançar é o MÍNIMO entre o que a reserva da linha pede e o saldo que ainda temos.
            # Usamos .clip(0) para garantir que o saldo não seja negativo (se já estourou, é 0).
            valor_a_lancar = np.minimum(averbado_novo['Parc. Reservada'], saldo_restante.clip(0))

            # averbado_novo['VALOR A LANÇAR CPF'] = averbado_novo['VALOR A LANÇAR CPF'].round(2)
            averbado_novo['VALOR A LANÇAR'] = valor_a_lancar.round(2)

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
            averbado_novo['NOVO LANÇAR TOTAL'] = averbado_novo['Parc. Reservada'] - averbado_novo['DIFF']

            return averbado_novo

            # 7. (Opcional) Remove a coluna auxiliar que criamos.
        # averbado_novo = averbado_novo.drop(columns=['SOMA ACUMULADA DA RESERVA'])

        if self.convenio == 'PREF. TAUBATÉ':
            averbado_finalizado = distribuicao_valores(averbado_novo)

            try:
                averbado_finalizado.to_excel(os.path.join(self.caminho, f"AVERBADO TRABALHADO {self.convenio}.xlsx"), index=False)
            except Exception as e:
                print(f"DEBUG: ERRO AO SALVAR AVERBADOS TRABALHADO: {e}")

            return

        averbado_finalizado = averbado_novo.copy()

        # colunas_valores_unificados = [col for col in averbado_finalizado.columns if 'Valor_Unif_' in col]
        colunas_valores_unificados = averbado_finalizado.filter(like='Valor_Unif_')

        # NOVO PASSO: Adiciona a coluna 'ORBITAL' ao DataFrame de colunas para soma
        colunas_para_somar = colunas_valores_unificados.copy()  # Cria uma cópia para garantir a segurança

        # Verifica se 'ORBITAL' já existe antes de adicionar (apenas por garantia, embora o código garanta)
        if 'ORBITAL' in averbado_finalizado.columns:
            # Usa .loc para garantir que a coluna seja adicionada
            colunas_para_somar.loc[:, 'ORBITAL'] = averbado_finalizado['ORBITAL']


        '''if colunas_valores_unificados:
            # print(f"Somando os valores das colunas: {colunas_valores_unificados}")
            averbado_finalizado['Soma'] = colunas_para_somar.sum(axis=1)
        else:
            print("Nenhuma coluna de valor encontrada. A coluna 'Soma' será inicializada com 0.")
            averbado_finalizado['Soma'] = 0'''

        averbado_finalizado['Soma'] = colunas_para_somar.sum(axis=1)

        # --- 4. Cálculo da Diferença e Formatação Final ---

        # Garante que a coluna de Parc. Reservada é numérica antes do cálculo
        if averbado_finalizado['Parc. Reservada'].dtype != 'float64':
            averbado_finalizado['Parc. Reservada'] = averbado_finalizado['Parc. Reservada'].str.replace('.', '')
            averbado_finalizado['Parc. Reservada'] = averbado_finalizado['Parc. Reservada'].str.replace(',', '.')
            averbado_finalizado['Parc. Reservada'] = pd.to_numeric(averbado_finalizado['Parc. Reservada'], errors='coerce').fillna(0)

        averbado_finalizado['Diff'] = averbado_finalizado['Soma'] - averbado_finalizado['Parc. Reservada']
        averbado_finalizado['Diff'] = averbado_finalizado['Diff'].round(2)

        # --- 5. Cria a coluna Lançar ---
        '''print(f'CONSIGNATARIA: {self.consignataria}')
        if self.consignataria == 'HOJE PREVIDENCIA PRIVADA':
            averbado_finalizado = self.adiciona_peculio(averbado_finalizado)
        else:'''

        # Vamos criar a coluna lancado_prazo para subtrair de Soma
        averbado_finalizado['lancado_prazo'] = averbados_prazo.groupby('CPF')['Parc. Reservada'].transform('sum')
        averbado_finalizado['lancado_prazo'] = averbado_finalizado['lancado_prazo'].fillna(0)

        averbado_finalizado['Soma Final'] = averbado_finalizado['Soma'] - averbado_finalizado['lancado_prazo']

        averbado_finalizado['Lançar'] = np.minimum(averbado_finalizado['Soma'], averbado_finalizado['Parc. Reservada'])
            
        averbado_finalizado.loc[averbado_finalizado['LIMINAR'] == "SIM", 'Lançar'] = 0

        # Remoção de duplicatas por matrícula
        # averbado_finalizado.drop_duplicates(subset=['Matrícula'], keep='first', inplace=True)


        print('DEBUG: Averbados após cálculo vetorizado:')
        try:
            averbado_finalizado.to_excel(os.path.join(self.caminho, f"AVERBADO TRABALHADO {self.convenio}.xlsx"), index=False)
        except Exception as e:
            print(f"DEBUG: ERRO AO SALVAR AVERBADOS TRABALHADO: {e}")