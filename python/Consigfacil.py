import pandas as pd
import numpy as np
from datetime import datetime
import re
from thefuzz import fuzz
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
        self.conciliacao.rename(columns={'PRESTAÇÃO ORIGINAL': 'PRESTAÇÃO'}, inplace=True)
        self.conciliacao.rename(columns={'RECEBIDO GERAL ': 'RECEBIDO GERAL'}, inplace=True)
        self.conciliacao.rename(columns={'TIPO OPERAÇÃO': 'PRODUTO', 'NOVO TIPO DE OPERAÇÃO': 'PRODUTO', 'PRODUTOS PELO D8': 'PRODUTO', 
                                         'PRODUTO D8': 'PRODUTO', 'PRODUTO PELO D8': 'PRODUTO', 'PRODUTO ATUALIZADO': 'PRODUTO'}, inplace=True)
        
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
                               "RISCO DA OPERAA\x87A\x82O-DEMAIS SITUAA\x87A\x95ES", "RISCO DA OPERACAO - DEMAIS SITUACOES"
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

        # Marca Prazo - Já está marcando "NÃO LANÇAR - PRAZO" dentro da função andamento_func_front
        front_consig_validado_termino = self.andamento_func_front(front_consig_validado_termino)

        # Marcar tudo que contem prazo como Não cartão
        # 1. Cria a máscara para quem está com o PRAZO vazio (ou NaN)
        mask_vazio_prazo = front_consig_validado_termino['PRAZO'].isna() | (front_consig_validado_termino['PRAZO'] == '') | (front_consig_validado_termino['PRAZO'] == 1) | (front_consig_validado_termino['PRAZO'] == 0)

        # 2. Quem NÃO tem prazo (vazio) -> É Cartão
        front_consig_validado_termino.loc[mask_vazio_prazo, 'Tipo Operacao'] = 'CARTAO DE CREDITO'

        # 3. Quem TEM prazo (não vazio) -> NÃO é cartão (ex: Empréstimo ou Operação Comum)
        # Usamos o ~ dentro do .loc para inverter a máscara
        front_consig_validado_termino.loc[~mask_vazio_prazo, 'Tipo Operacao'] = 'CARTAO BENEFICIO' # Ou o nome que desejar

        # Marcar o que não é cartão Conciliação
        front_consig_validado_termino.loc[(~front_consig_validado_termino['Tipo Operacao'].str.contains('Cartão de Crédito|CARTAO DE CREDITO|CARTÃO DE CRÉDITO', na=False)), 'OBS'] = 'NÃO LANÇAR - NÃO CARTÃO'


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
        front_consig_cartao_conciliacao = front_consig[front_consig['Tipo Operacao'].str.contains('Cartão de Crédito|CARTAO DE CREDITO|CARTÃO DE CRÉDITO', na=False)].copy()

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

        andam_file, front_base = self.adiciona_contratos_faltando(self.andamento, front)

        andam_file = self.extrair_contratos_com_referencia(andam_file, self.front)

        # Novamente usar o adiciona_contratos_faltando só que dessa vez para o Contrato Editado 1 que tem celulas vazias
        andam_file, front_base = self.adiciona_contratos_faltando(andam_file, front_base, "Contrato Editado 1")

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
    
    def adiciona_contratos_faltando(self, andamento_contratos_faltantes, front_semi, esteira='Código na instituição'):
        # 1. Preparação do DataFrame B (Front)
        # Removemos duplicatas de contrato para garantir unicidade real no B
        front_base = front_semi[['CPF', 'Prestacao', 'Contrato']].drop_duplicates(subset=['Contrato']).copy()
        
        # Criamos a contagem de ocorrência para CPF + Valor no Front (B)
        front_base['id_ocorrencia'] = front_base.groupby(['CPF', 'Prestacao']).cumcount()

        # 2. Preparação do DataFrame A (Andamento)
        # Criamos a contagem de ocorrência no A também para servir de chave de busca
        # Importante: A contagem deve ser baseada nas mesmas colunas que usaremos no merge
        if esteira == 'Código na instituição':
            contratos_de_andamento = andamento_contratos_faltantes['Código na instituição']
            andamento_contratos_faltantes.insert(2, "Contrato de Andamento", contratos_de_andamento, True)
            esteira = "Contrato de Andamento"
        andamento_contratos_faltantes = andamento_contratos_faltantes.drop_duplicates(subset='Código', keep='first')

        front_base['Contrato'] = front_base['Contrato'].astype(str)

        # 1. Identificamos quais células são puramente numéricas (floats ou ints)
        # O errors='coerce' transforma textos em NaN (vazio) apenas para esta validação

        print(f'Dtype Contrato de Andamento:\n{andamento_contratos_faltantes[esteira].dtype}')
        print(f'Dtype Front:\n{front_base['Contrato'].dtype}')

        # 1. Pegamos a lista (ou Series) de contratos que já estão no andamento
        contratos_ja_existentes = andamento_contratos_faltantes[esteira]

        #Contrato 302009782 existe em contratos já existentes?
        print(f'Contrato 302009782 existe em contratos_ja_existentes?\n{'302009782' in contratos_ja_existentes}')

        # 2. Filtramos o front_base: "Mantenha apenas onde o Contrato NÃO ESTÁ nos existentes"
        front_base = front_base[~front_base['Contrato'].isin(contratos_ja_existentes)]

        # Contrato 302009782 existe em front_base?
        contratos_em_front_base = front_base['Contrato']
        print(f'Contrato 302009782 existe em front_base?\n{'302009782' in contratos_em_front_base}')

        # Quais contratos estão atrelados ao CPF 691.960.954-15 em andamento_contratos_faltantes?
        print(f'CPF 691.960.954-15 está em andamento_contratos_faltantes?\n{andamento_contratos_faltantes[andamento_contratos_faltantes['CPF'] == '691.960.954-15']}')

        # Quais contratos estão atrelados ao CPF 691.960.954-15 em front_base?
        print(f'CPF 691.960.954-15 está em front_base?\n{front_base[front_base['CPF'] == '691.960.954-15']}')

        if andamento_contratos_faltantes['Valor da Parcela'].dtype != 'float64':
            andamento_contratos_faltantes['Valor da Parcela'] = andamento_contratos_faltantes['Valor da Parcela'].astype(str).str.replace(".", "")
            andamento_contratos_faltantes['Valor da Parcela'] = andamento_contratos_faltantes['Valor da Parcela'].astype(str).str.replace(",", ".")
            andamento_contratos_faltantes['Valor da Parcela'] = pd.to_numeric(andamento_contratos_faltantes['Valor da Parcela'], errors='coerce')
        andamento_contratos_faltantes['id_ocorrencia'] = andamento_contratos_faltantes.groupby(['CPF', 'Valor da Parcela']).cumcount()


        # --- LÓGICA DE MERGE ---

        # Função auxiliar para evitar repetição de código nos 3 cenários (+0, +20, +40)
        def executa_merge_ajustado(df_alvo, df_fonte, valor_ajuste=0):
            df_fonte_temp = df_fonte.copy()
            if valor_ajuste != 0:
                df_fonte_temp['Prestacao'] = df_fonte_temp['Prestacao'] + valor_ajuste
            
            # Merge considerando CPF, Valor E o ID da ocorrência
            res = df_alvo.merge(
                df_fonte_temp,
                left_on=['CPF', 'Valor da Parcela', 'id_ocorrencia'],
                right_on=['CPF', 'Prestacao', 'id_ocorrencia'],
                how='left',
                suffixes=('', f'_{valor_ajuste}')
            )
            
            # Preenche o código e limpa colunas temporárias
            res[esteira] = res[esteira].fillna(res['Contrato'])
            return res.drop(columns=['Prestacao', 'Contrato'], errors='ignore')

        # Execução dos 3 cenários
        # Cenário 1: Valor Exato
        andamento_contratos_faltantes = executa_merge_ajustado(andamento_contratos_faltantes, front_base, 0)
        
        # Cenário 2: +20 reais
        andamento_contratos_faltantes = executa_merge_ajustado(andamento_contratos_faltantes, front_base, 20)
        
        # Cenário 3: +40 reais
        andamento_contratos_faltantes = executa_merge_ajustado(andamento_contratos_faltantes, front_base, 40)

        # Limpeza final
        if 'id_ocorrencia' in andamento_contratos_faltantes.columns:
            andamento_contratos_faltantes.drop(columns=['id_ocorrencia'], inplace=True)

        # 1. Identificamos o que é numérico
        mask_numerico = pd.to_numeric(andamento_contratos_faltantes[esteira], errors='coerce').notna()

        # 2. Convertemos apenas as linhas da máscara
        if mask_numerico.any():
            # Convertemos para float, arredondamos para evitar 123.0000004 e transformamos em int
            valores_convertidos = (
                pd.to_numeric(andamento_contratos_faltantes.loc[mask_numerico, esteira])
                .round(0)          # Garante que 123.0 vire 123
                .astype(np.int64)  # Usa o int do numpy que é mais direto
                .astype(str)       # Transforma em texto para remover o .0 definitivo
            )
            
            andamento_contratos_faltantes.loc[mask_numerico, esteira] = valores_convertidos
            
        return andamento_contratos_faltantes, front_base

    
    def extrair_contratos_com_referencia(self, df_sujo: pd.DataFrame, df_limpo: pd.DataFrame) -> pd.DataFrame:
        print("Iniciando o processo de extração de contratos...")

        def limpar_contrato(texto: str) -> str:
            if not isinstance(texto, str):
                texto = str(texto)
            return re.sub(r'[^0-9a-zA-Z]', '', texto).replace(" ", "")

        # --- Passo 1: Preparar Mapas de Referência ---
        df_limpo['Contrato'] = df_limpo['Contrato'].astype(str).str.strip()
        df_limpo['CCB'] = df_limpo['CCB'].astype(str).str.strip()
        
        # Novo Mapa para Parcela (Melhoria 1)
        # Criamos um dicionário onde a chave é o CPF e o valor é uma lista de tuplas (Valor, Contrato)
        df_limpo['Prestacao'] = df_limpo['Prestacao'].astype(str).str.replace(".", "")
        df_limpo['Prestacao'] = df_limpo['Prestacao'].astype(str).str.replace(",", ".")
        df_limpo['Prestacao'] = pd.to_numeric(df_limpo['Prestacao'], errors='coerce')
        cpf_parcelas = df_limpo.groupby('CPF').apply(
            lambda x: list(zip(x['Prestacao'].round(2), x['Contrato']))
        ).to_dict()

        cpf_contratos = df_limpo.groupby('CPF')['Contrato'].apply(list).to_dict()
        cpf_operacao = df_limpo.groupby('CPF')['CCB'].apply(list).to_dict()

        # --- Passo 2: Lógica de Extração ---
        def encontrar_contratos_na_linha(row):
            cpf = row['CPF']
            texto_contratos_sujo = str(row['Contrato de Andamento']).strip()
            valor_parcela_suja = round(float(row.get('Valor da Parcela', 0)), 2)

            # MELHORIA 1: Se o código estiver vazio, tenta achar pela parcela
            if not texto_contratos_sujo or texto_contratos_sujo.lower() == 'nan' or texto_contratos_sujo == '':
                lista_parcelas_validas = cpf_parcelas.get(cpf, [])
                for valor_ref, contrato_ref in lista_parcelas_validas:
                    if valor_parcela_suja == valor_ref:
                        return [contrato_ref] # Retorna o contrato da parcela idêntica
                return []

            # (Mantém a lógica original de Fuzzy para quem tem texto no código)
            contratos_validos_para_cpf = cpf_contratos.get(cpf, [])
            operacoes_validas_para_cpf = cpf_operacao.get(cpf, [])
            if not contratos_validos_para_cpf: return []

            partes_sujas = [p for p in re.split(r'[/,;\s]+', texto_contratos_sujo) if p]
            encontrados_nesta_linha = []
            contratos_disponiveis = list(contratos_validos_para_cpf)
            operacoes_disponiveis = list(operacoes_validas_para_cpf)
            LIMIAR_SEGURO = 80

            for parte in partes_sujas:
                parte_limpa = limpar_contrato(parte)
                if not parte_limpa or len(parte_limpa) < 3: continue

                melhor_match_para_parte = None
                maior_score_ponderado = 0

                for i, contrato_valido in enumerate(contratos_disponiveis):
                    operacao_valida = operacoes_disponiveis[i] if i < len(operacoes_disponiveis) else ""
                    alvos = [(contrato_valido, 'CONTRATO'), (operacao_valida, 'OPERACAO')]

                    for alvo_texto, tipo_alvo in alvos:
                        if not alvo_texto: continue
                        alvo_limpo = limpar_contrato(alvo_texto)
                        score_base = 0

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

                        if score_base >= LIMIAR_SEGURO:
                            score_final = score_base + (1 if tipo_alvo == 'CONTRATO' else 0)
                            if score_final > maior_score_ponderado:
                                maior_score_ponderado = score_final
                                melhor_match_para_parte = contrato_valido

                if melhor_match_para_parte:
                    encontrados_nesta_linha.append(melhor_match_para_parte)
                    if melhor_match_para_parte in contratos_disponiveis:
                        idx = contratos_disponiveis.index(melhor_match_para_parte)
                        del contratos_disponiveis[idx]
                        if idx < len(operacoes_disponiveis): del operacoes_disponiveis[idx]

            return encontrados_nesta_linha

        # --- Passo 3: Aplicação e Reordenação (Melhoria 2) ---
        df_sujo['Contrato de Andamento'] = df_sujo['Contrato de Andamento'].astype(str).str.replace('nan', '')
        if df_sujo['Valor da Parcela'].dtype != 'float64':
            df_sujo['Valor da Parcela'] = df_sujo['Valor da Parcela'].astype(str).str.replace(".", "")
            df_sujo['Valor da Parcela'] = df_sujo['Valor da Parcela'].astype(str).str.replace(",", ".")
            df_sujo['Valor da Parcela'] = pd.to_numeric(df_sujo['Valor da Parcela'], errors='coerce')
        lista_de_contratos_encontrados = df_sujo.apply(encontrar_contratos_na_linha, axis=1)

        df_contratos_novos = pd.DataFrame(lista_de_contratos_encontrados.tolist(), index=df_sujo.index)
        novas_colunas = [f'Contrato Editado {i + 1}' for i in df_contratos_novos.columns]
        df_contratos_novos.columns = novas_colunas

        # Reordenação Dinâmica
        cols_originais = df_sujo.columns.tolist()
        if 'Contrato de Andamento' in cols_originais:
            idx_ref = cols_originais.index('Contrato de Andamento') + 1
            # Reconstrói a ordem: Tudo até o código + Novos Contratos + Resto
            ordem_final = cols_originais[:idx_ref] + novas_colunas + cols_originais[idx_ref:]
            df_resultado = pd.concat([df_sujo, df_contratos_novos], axis=1)[ordem_final]
        else:
            df_resultado = pd.concat([df_sujo, df_contratos_novos], axis=1)

        # --- Salvar ---
        try:
            caminho_final = os.path.join(self.caminho, "Relatório Averbados Contratos tratados.xlsx")
            df_resultado.to_excel(caminho_final, index=False)
        except Exception as e:
            print(f"ERRO AO SALVAR: {e}")

        return df_resultado

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

        acha_matriculas = ACHA_MATRICULA_CONSIGFACIL(averbados, front_consig)
        front_preliminar = acha_matriculas.acha_matricula()
        print(f'FRONT COM MATRICULAS TRATADAS:\n{front_preliminar}')

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
        mask_nao = (averbados['Valor da reserva'] == 0) | (averbados['Valor da reserva'].isna())
        averbados.loc[mask_nao, 'OBS'] = 'NÃO'
        averbados = averbados[averbados['OBS'] != "NÃO"]

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
            averbado_novo['Matrícula'] = averbado_novo['Matrícula'].astype('int64')
        except Exception as e:
            averbado_novo['Matrícula'] = pd.to_numeric(averbado_novo['Matrícula'].astype('int64'), errors='coerce')


        # SOMASE
        # Apenas remove o ".0" das matrículas que são números, mantendo os textos
        front_preliminar['MATRICULA_ENCONTRADA_1'] = pd.to_numeric(front_preliminar['MATRICULA_ENCONTRADA_1'], errors='coerce').astype('Int64')
        
        front_preliminar['SOMASE LOCAL POR MATRICULA']  = front_preliminar.groupby('MATRICULA_ENCONTRADA_1')['Valor a lançar'].transform('sum')
        soma_condicional_dict_averb = front_preliminar.groupby('CPF')['SOMASE LOCAL POR MATRICULA'].sum().to_dict()

        # A mesma coisa de cima só que com CPF
        front_preliminar['SOMASE LOCAL POR CPF']  = front_preliminar.groupby('CPF')['Valor a lançar'].transform('sum')
        # soma_condicional_dict_averb_cpf = front_preliminar.groupby('CPF')['SOMASE LOCAL POR CPF'].sum().to_dict()

        if self.convenio in ['PREF CAJAMAR', 'GOV MT']:
            # Orbitall
            orbitall = self.orbital_tratado(front_preliminar)
            
            averbado_novo['PARCELA FRONT'] = averbado_novo['CPF'].map(soma_condicional_dict_averb)
            # averbado_novo['PARCELA_CPF'] = averbado_novo['CPF'].map(soma_condicional_dict_averb_cpf)
            # 3. Soma por CPF no orbital
            somase_orbital = orbitall.groupby('CPF/CNPJ')['VALOR DESCONTO'].sum()

            # 4. Combina tudo em um único dataframe
            soma_total = (
                soma_condicional_dict_averb
                .add(somase_orbital, fill_value=0)
            )
            # soma_total_cpf = (soma_condicional_dict_averb_cpf.add(somase_orbital, fill_value=0))

            averbado_novo['PARCELA FRONT'] = averbado_novo['CPF'].map(soma_total)
            # averbado_novo['PARCELA CPF'] = averbado_novo['CPF'].map(soma_total_cpf)
            # print(type(averbado_novo.loc[0, 'SOMASE']))
            averbado_novo['PARCELA FRONT'] = averbado_novo['PARCELA FRONT'].fillna(0)
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
            averbado_novo['ALOCADO ANTERIORMENTE'] = alocado_anteriormente

            # 3. Calcula o saldo restante do SOMASE ANTES de processar a linha atual.
            saldo_restante = averbado_novo['SOMASE CRED'] - alocado_anteriormente

            # 4. O valor a lançar é o MÍNIMO entre o que a reserva da linha pede e o saldo que ainda temos.
            # Usamos .clip(0) para garantir que o saldo não seja negativo (se já estourou, é 0).
            valor_a_lancar = np.minimum(averbado_novo['Valor da reserva'], saldo_restante.clip(0))

            # 5. Atribui o resultado final arredondado às colunas.
            averbado_novo['VALOR A LANÇAR MATRICULA'] = averbado_novo['VALOR A LANÇAR MATRICULA'].round(2)
            # averbado_novo['VALOR A LANÇAR CPF'] = averbado_novo['VALOR A LANÇAR CPF'].round(2)
            averbado_novo['VALOR ATRIBUIDO'] = valor_a_lancar.round(2)

            # 6. Preenche a coluna OBS para linhas que não receberam nada.
            averbado_novo.loc[averbado_novo['VALOR A LANÇAR MATRICULA'] == 0, 'OBS'] = 'NÃO'
            # averbado_novo.loc[averbado_novo['VALOR A LANÇAR CPF'] == 0, 'OBS'] = 'NÃO'

            # 7. Vamos criar a coluna Diff para lançar os parciais
            somase_lancar = averbado_novo.groupby('CPF')['VALOR ATRIBUIDO'].transform('sum')
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
        
        if (averbado_finalizado['SITUAÇÃO DE DESCONTO'] == 'PARCIAL').any():
            averbado_finalizado.loc[averbado_finalizado['SITUAÇÃO DE DESCONTO'] == 'PARCIAL', 'Valor da reserva'] = averbado_finalizado['NOVO LANÇAR TOTAL']
            averbado_finalizado = distribuicao_valores(averbado_finalizado)
        

        try:
            front_preliminar.to_excel(os.path.join(self.caminho, f'FRONT COM MATRICULAS TRATADAS {self.convenio}.xlsx'), index=False)
        except Exception as e:
            print(f'DEBUG: ERRO AO SALVAR FRONT COM MATRICULAS TRATADAS: {e}')

        print('DEBUG: Averbados após cálculo vetorizado:')
        try:
            averbado_finalizado.to_excel(os.path.join(self.caminho, f"AVERBADO TRABALHADO {self.convenio}.xlsx"), index=False)
        except Exception as e:
            print(f"DEBUG: ERRO AO SALVAR AVERBADOS TRABALHADO: {e}")