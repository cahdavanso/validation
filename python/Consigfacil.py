import pandas as pd
import numpy as np
from datetime import datetime
import re
import logging
import os
import chardet
from python.acha_matriculas_consigfacil import ACHA_MATRICULA_CONSIGFACIL

# Mantendo variáveis globais do original
rejeitados = ['/']

class CONSIGFACIL:
    # O init foi adaptado para receber os DataFrames do server.py, mas prepara os dados
    # exatamente como o original esperava (convertendo tipos, etc.)
    def __init__(self, front, portal_file_list, convenio,  caminho, conciliacao=None, andamento_list=None):
        
        self.convenio = convenio
        self.caminho = caminho
        
        # --- ADAPTAÇÃO: Recebendo DataFrames do server.py ao invés de ler do disco ---

        # 1. Averbados
        self.averbados = portal_file_list if portal_file_list is not None else pd.DataFrame()
        # Mantendo a conversão de tipo original:
        if 'Valor da reserva' in self.averbados.columns:
            # Parcela de Averbados já serão floats
            self.averbados['Valor da reserva'] = self.averbados['Valor da reserva'].astype(str).str.replace(".", "")
            self.averbados['Valor da reserva'] = self.averbados['Valor da reserva'].str.replace(",", ".")
            self.averbados['Valor da reserva'] = pd.to_numeric(self.averbados['Valor da reserva'], errors="coerce")
            self.averbados['Valor da reserva'] = pd.to_numeric(self.averbados['Valor da reserva'], errors="coerce")
        else:
            # Garante a coluna caso venha vazio, para não quebrar a lógica original
            self.averbados['Valor da reserva'] = 0.0

        # 2. Front
        self.front = front if front is not None else pd.DataFrame()

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
        self.conciliacao.rename(columns={'TIPO OPERAÇÃO': 'PRODUTO', 'PRODUTOS PELO D8': 'PRODUTO'}, inplace=True)
        
        # 5. Andamento
        self.andamento = andamento_list if andamento_list is not None else pd.DataFrame()

        # --- GATILHO: Inicia a lógica original automaticamente ---
        logging.info("Iniciando lógica original do Consigfacil...")
        front_trabalhado = self.tratamento_front()
        self.averbados_func(front_trabalhado)


    # =========================================================================
    # DAQUI PARA BAIXO É A LÓGICA ORIGINAL INTACTA (Copy-Paste do seu arquivo)
    # =========================================================================

    def tratamento_front_preliminar(self):
        front_consig = self.front.copy()

        conciliacao = self.conciliacao.copy()

        # Insere as colunas vazias necessárias
        front_consig.insert(21, 'Saldo', '', True)
        front_consig.insert(22, 'Valor a lançar', '', True)
        front_consig.insert(23, 'PRAZO', '', True)
        front_consig.insert(24, 'OBS', '', True)

        print(f'Esteiras Únicas do front: {front_consig["Esteira"].unique()}')

        # Esteiras
        esteiras_permitidas = ['11 FORMALIZACAO', '11 FORMALIZAA\x87A\x83O','09.0 PAGO', 'RISCO DA OPERACAO - OBITO', '14.0 RISCO DA OPERACAO - OBITO',
                               'RISCO DA OPERACAO-DEMAIS SITUACOES', '11.PROBLEMAS DE AVERBACAO', '10.7.0 INGRESSAR COM PROCESSO OU ACAO JURIDICO',
                               '07.1 \x96 QUITACAO \x96 PAGAMENTO AO CLIENTE', '10.7 CONTRATO NAO AVERBADO - AGUARDANDO RESOLUCAO', '11.2  DETERMINACAO JUDICIAL',
                               "15.0\tRISCO DA OPERACAO-DEMAIS SITUACOES", "11.1 CONTRATO FISICO ENVIADO AO BANCO", "07.0 QUITACAO \x96 ENVIO DE CESSAO",
                               "07.1 AÂ– QUITACAO AÂ– PAGAMENTO AO CLIENTE", "99 CARTAO UTILIZADO", "15.0 RISCO DA OPERACAO-DEMAIS SITUACOES",
                               "RISCO DA OPERAA\x87A\x82O-DEMAIS SITUAA\x87A\x95ES"
                              ]
        
        
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

        # Marcar o que não é cartão Conciliação
        front_consig_validado_termino.loc[(~front_consig_validado_termino['Tipo Conciliação'].str.contains('Cartão de Crédito|CARTAO DE CREDITO|CARTÃO DE CRÉDITO', na=False)), 'OBS'] = 'NÃO LANÇAR - NÃO CARTÃO'

        # Marca Prazo - Já está marcando "NÃO LANÇAR - PRAZO" dentro da função andamento_func_front
        front_consig_validado_termino = self.andamento_func_front(front_consig_validado_termino)

        # Marcar liquidados em StatusContrato
        front_consig_validado_termino.loc[(front_consig_validado_termino['Status'].str.contains('Liquidado', na=False)), 'OBS'] = 'NÃO LANÇAR - LIQUIDADO'

        # TIRAR BANCO OUTROS
        front_consig_validado_termino.loc[(front_consig_validado_termino['Consignataria'].str.contains('OUTROS', na=False)), 'OBS'] = 'NÃO LANÇAR - BANCO OUTROS'

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

        if front_consig is False:
            print("DEBUG: O tratamento preliminar do front falhou. Verifique os erros anteriores.")
            return False

        # Separa apenas o que retornou como "cartão de crédito" no tipo de conciliação
        front_consig_cartao_conciliacao = front_consig[front_consig['Tipo Conciliação'].str.contains('Cartão de Crédito|CARTAO DE CREDITO|CARTÃO DE CRÉDITO', na=False)].copy()

        # Separar o que não é cartão de crédito da conciliação
        # front_consig_nao_cartao = front_consig[~front_consig['Tipo Conciliação'].str.contains('Cartão de Crédito', na=False)].copy()

        # Pegar o que é CARTAO DE CREDITO do front
        # condicao_cartao = ['CARTAO DE CREDITO']
        # front_consig_cartao_front = front_consig_nao_cartao[front_consig_nao_cartao['Tipo Operacao'].isin(condicao_cartao)].copy()
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
        mask_peculio = front_consig_trabalhado['Consignataria'] == 'HOJE PREVIDENCIA PRIVADA'
        front_consig_trabalhado.loc[mask_peculio, 'Valor a lançar'] += 20

        # -------------------------------------- TIRA O PRAZO ----------------------------------------------- #
        front_consig_trabalhado = front_consig_trabalhado[~front_consig_trabalhado['OBS'].str.contains('NÃO LANÇAR - PRAZO', na=False)].copy()

        # --------------------------------------- TIRA BANCO OUTROS ----------------------------------------- #
        front_consig_trabalhado = front_consig_trabalhado[~front_consig_trabalhado['Consignataria'].str.contains('OUTROS', na=False)].copy()

        # ----------------------------------------- TIRA LIQUIDADOS ----------------------------------------- #
        front_consig_trabalhado = front_consig_trabalhado[~front_consig_trabalhado['Status'].str.contains('Liquidado', na=False)].copy()

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
        conciliacao_tratado = self.trata_conciliacao()

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
        front_copy['Prestacao'] = front_copy['Prestacao'].astype(str).str.replace('.', '', regex=False)
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
        # andam_file.to_excel(rf'{self.caminho}\ANDAMENTO_TESTE {self.convenio} {str(datetime.now().month).zfill(2)}-{datetime.now().year}.xlsx', index=False)

        # Função para decidir o valor da nova modalidade
        def substituir_modalidade():
            # 1. Identifica todas as colunas com 'Contrato' no nome
            colunas_contratos = [col for col in andam_file.columns if 'Contrato' in col]

            # 2. Cria uma coluna 'Prazo' vazia no Credbase
            if 'PRAZO' not in front.columns:
                front['PRAZO'] = None

            # 3. Cria um dicionário auxiliar: contrato → prazo
            contrato_para_prazo = {}

            if andam_file['Valor da Parcela'].dtype == 'object':
                andam_file['Valor da Parcela'] = andam_file['Valor da Parcela'].str.replace(".", '')
                andam_file['Valor da Parcela'] = andam_file['Valor da Parcela'].str.replace(",", '.')
                andam_file['Valor da Parcela'] = pd.to_numeric(andam_file['Valor da Parcela'], errors='coerce')
                # print(f'Modalidade e Parcela do Código 407337: {andam_file.loc[andam_file['Código'] == 407337, ['Modalidade', 'Valor da Parcela']]}')

            # 4. Tira casos que são previdencia e igual a 20, 40, 60
            andam_file_sem_prev_seguro = andam_file[~(((andam_file['Modalidade'] == 'Previdência') | (
                    andam_file['Modalidade'] == 'Seguros') | (andam_file['Modalidade'] == 'Mensalidade'))
                                                    & ((andam_file['Valor da Parcela'] == 20) | (
                            andam_file['Valor da Parcela'] == 40)
                                                        | (andam_file['Valor da Parcela'] == 60)))]

            # print(andam_file_sem_prev_seguro['Serviço'].unique())

            '''print(f'Andamento completo: {len(andam_file)}')
            print(f'Andamento sem previdência: {len(andam_file_sem_prev_seguro)}')'''

            # Para cada linha no arquivo de andamentos, verifica todas as colunas de contrato
            for _, row in andam_file_sem_prev_seguro.iterrows():
                prazo = row.get('Prazo Total')  # Pode ser 'Prazo Total' dependendo do nome
                for col in colunas_contratos:
                    contrato = row.get(col)
                    if pd.notna(contrato):
                        contrato_para_prazo[str(contrato).strip()] = prazo

            print('DEBUG: Dicionário contrato - prazo criado a partir do andamento:')
            try:
                andam_file_sem_prev_seguro.to_excel(os.path.join(self.caminho, f"ANDAMENTO GERAL {self.convenio}.xlsx"), index=False)
            except Exception as e:
                print(f"DEBUG: ERRO AO SALVAR ANDAMENTO GERAL: {e}")

            # 4. Aplica a busca no Credbase
            return front['Contrato'].astype(str).str.strip().map(contrato_para_prazo)

        # Aplica a função ao DataFrame front
        front['PRAZO'] = substituir_modalidade()

        status_andamento = front['PRAZO'].fillna('')

        cond_prazo = ~status_andamento.isin(['', '0', '1', 0, 1])

        # Aplica a condição: se qualquer uma for verdadeira, OBS = 'NÃO'; caso contrário, OBS = ''
        front.loc[cond_prazo & (front['OBS'] == ''), 'OBS'] = 'NÃO LANÇAR - PRAZO'

        return front

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

    def trata_cod_and(self, andamentos):
        # PUXA OS ARQUIVOS À SEREM TRATADOS
        data_averbados = andamentos
        # print(data_averbados.columns)

        # SUBSTITUIMOS CARACTER POR NADA
        contrato_editado = data_averbados['Código na instituição'].fillna('').astype(str).apply(
            lambda x: ''.join(char for char in x if char.isdigit() or char in rejeitados))

        contrato_editado = contrato_editado.replace('//', '/', regex=True)

        # INSERE A COLUNA CONTRATO EDITADO COM OS NÚMEROS JÁ TRATADOS
        if "Contrato Editado" not in data_averbados.columns:
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
                    'Int64')  # Int64 permite nulos'''

            # Descobre a posição da coluna 'Contrato Editado'
            col_index = data_averbados.columns.get_loc('Contrato Editado')

            # Divide o DataFrame original em duas partes
            antes = data_averbados.iloc[:, :col_index + 1]  # Inclui 'Contrato Editado'
            depois = data_averbados.iloc[:, col_index + 1:]

            # Concatena com os novos dados no meio
            data_averbados = pd.concat([antes, df_contratos_separados, depois], axis=1)

        return data_averbados

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
            orbital_final.to_excel(os.path.join(self.caminho, f"ORBITAL TRABALHADO {self.convenio}.xlsx"), index=False)
            print(f"DEBUG: ORBITAL TRABALHADO {self.convenio} salvo com sucesso!")
        except Exception as e:
            print(f"DEBUG: ERRO AO SALVAR ORBITAL TRABALHADO {self.convenio}: {e}")

        return orbital_final


    def averbados_func(self, front):
        # Contse do Credbase no relatório de averbados
        front_consig = front.copy()
        front_preliminar = self.tratamento_front_preliminar
        averbados = self.averbados

        if front_consig is False:
            print("DEBUG: O tratamento preliminar do front falhou. Verifique os erros anteriores.")
            return False
        
        if self.convenio in ['PREF. CAMPINA GRANDE', 'PREF. RECIFE']:
            averbados = averbados[averbados['Modalidade'].isin(['Cartão de Crédito', 'Cartão Benefício (Compras)', 'Cartão Benefício'])]
        else:
            averbados = averbados[averbados['Modalidade'] == 'Cartão de Crédito']

        # Realoca a coluna "Login" para o início da planilha
        if averbados.columns[0] != 'Login':
            # 1. Cria a nova ordem: a coluna 'Login' + todas as outras colunas que não são 'Login'
            nova_ordem = ['Login'] + [col for col in averbados.columns if col != 'Login']

            # 2. Reorganiza o DataFrame com a nova lista
            averbados = averbados[nova_ordem]

        front_preliminar = ACHA_MATRICULA_CONSIGFACIL(averbados, front_consig)

        # Remover de Averbados algumas colunas
        colunas_para_remover = ['Validade', 'Saldo de reserva', 'Data', 'IP', 'Código', '%']

        averbados = averbados.drop(columns=colunas_para_remover, errors='ignore')

        # Adicionar outras colunas em Averbados
        # averbados.insert(5, 'CONCAT', '', True)
        averbados['VALOR A LANÇAR'] = ''
        averbados['CONTSE'] = ''
        averbados['CONTSE SEQ'] = ''
        averbados['SOMASE CRED'] = ''
        # averbados['VALOR ATRIBUIDO'] = ''
        # averbados['FALTA ATRIBUIR'] = ''
        # averbados['DIFF'] = ''
        averbados['OBS'] = ''

        # Tira valor vazio do Valor da Reserva
        mask_nao = (averbados['Valor da reserva'] == 0) | (averbados['Valor da reserva'].isna())
        averbados.loc[mask_nao, 'OBS'] = 'NÃO'

        # Separa o que não é NÃO em outra planilha
        # averbado_novo = averbados[averbados['OBS'] != 'NÃO'].copy()
        averbado_novo = averbados.copy()

        # CONTSE
        averbado_novo['CONTSE'] = averbado_novo.groupby('CPF')['CPF'].transform('count')

        # CONTSE SEQ
        averbado_novo['CONTSE SEQ'] = averbado_novo.groupby('CPF').cumcount() + 1

        # Se for PREF. BAYEUX adiciona mais 20 reais para cada contrato
        '''if self.convenio in ['PREF. BAYEUX', 'PREF. PAÇO DO LUMIAR']:
            for idx, row in credbase.iterrows():
                credbase.loc[idx, 'Valor a lançar'] = credbase.loc[idx, 'Valor a lançar'] + 20
        elif self.convenio == 'GOV. MA':
            credbase.loc[credbase['Banco'] == 'BANCO HP', 'Valor a lançar'] += 20'''

        # SOMASE
        soma_condicional_dict_averb = front_consig.groupby('CPF')['Valor a lançar'].sum().to_dict()

        if self.convenio in ['PREF CAJAMAR', 'GOV MT']:
            # Orbitall
            orbitall = self.orbital_tratado(front_preliminar)
            # 3. Soma por CPF no orbital
            somase_orbital = orbitall.groupby('CPF/CNPJ')['VALOR DESCONTO'].sum()

            # 4. Combina tudo em um único dataframe
            soma_total = (
                soma_condicional_dict_averb
                .add(somase_orbital, fill_value=0)
            )

            averbado_novo['SOMASE CRED'] = averbado_novo['CPF'].map(soma_total)
            # print(type(averbado_novo.loc[0, 'SOMASE']))
            averbado_novo['SOMASE CRED'] = averbado_novo['SOMASE CRED'].fillna(0)
        else:
            averbado_novo['SOMASE CRED'] = averbado_novo['CPF'].map(soma_condicional_dict_averb)
            averbado_novo['SOMASE CRED'] = averbado_novo['SOMASE CRED'].fillna(0)


        # =============================================================================
        #        INÍCIO DA NOVA LÓGICA VETORIZADA (SUBSTITUI O SEU LOOP 'FOR')
        # =============================================================================

        # IMPORTANTE: Garanta que as colunas de valores são numéricas, não texto.
        # O .to_numeric(errors='coerce') converte o que for possível para número e põe NaN no que não for.
        averbado_novo['Valor da reserva'] = pd.to_numeric(averbado_novo['Valor da reserva'], errors='coerce').fillna(0)
        averbado_novo['SOMASE CRED'] = pd.to_numeric(averbado_novo['SOMASE CRED'], errors='coerce').fillna(0)

        # NOTA: Como não há coluna de prioridade, a ordem de distribuição dependerá
        # da ordem atual do DataFrame. Se precisar de uma ordem específica,
        # um .sort_values() viria aqui.

        # 1. Calcula a soma ACUMULADA da reserva dentro de cada grupo de CPF.
        # Esta é a "mágica" que substitui a necessidade de um loop.
        averbado_novo['SOMA ACUMULADA DA RESERVA'] = averbado_novo.groupby('CPF')['Valor da reserva'].cumsum()

        # 2. Calcula o valor que JÁ FOI ALOCADO para as linhas ANTERIORES.
        # É a soma acumulada até a linha atual, menos o valor da própria linha.
        alocado_anteriormente = averbado_novo['SOMA ACUMULADA DA RESERVA'] - averbado_novo['Valor da reserva']

        # 3. Calcula o saldo restante do SOMASE ANTES de processar a linha atual.
        saldo_restante = averbado_novo['SOMASE CRED'] - alocado_anteriormente

        # 4. O valor a lançar é o MÍNIMO entre o que a reserva da linha pede e o saldo que ainda temos.
        # Usamos .clip(0) para garantir que o saldo não seja negativo (se já estourou, é 0).
        valor_a_lancar = np.minimum(averbado_novo['Valor da reserva'], saldo_restante.clip(0))

        # 5. Atribui o resultado final arredondado às colunas.
        averbado_novo['VALOR A LANÇAR'] = valor_a_lancar.round(2)
        # averbado_novo['VALOR ATRIBUIDO'] = valor_a_lancar.round(2)

        # 6. Preenche a coluna OBS para linhas que não receberam nada.
        averbado_novo.loc[averbado_novo['VALOR A LANÇAR'] == 0, 'OBS'] = 'NÃO'

        # 7. (Opcional) Remove a coluna auxiliar que criamos.
        # averbado_novo = averbado_novo.drop(columns=['SOMA ACUMULADA DA RESERVA'])

        print('DEBUG: Averbados após cálculo vetorizado:')
        try:
            averbado_novo.to_excel(os.path.join(self.caminho, f"AVERBADO TRABALHADO {self.convenio}.xlsx"), index=False)
        except Exception as e:
            print(f"DEBUG: ERRO AO SALVAR AVERBADOS TRABALHADO: {e}")