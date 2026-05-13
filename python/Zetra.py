import pandas as pd
import zipfile
import numpy as np
from python.ESTEIRAS import load_esteiras
from python.trata_conciliacao import TRATA_CONCILIACAO
import re
from thefuzz import fuzz
from datetime import datetime
import os
import io
from io import StringIO
import openpyxl


class ZETRA:
    def __init__(self, portal_file_path, convenio, front, consignataria, caminho, funcao=None, historico=None, conciliacao=None, kobraki=None, orbital=None):

        self.caminho = caminho

        self.convenio = convenio

        self.consignataria = consignataria

        self.averbados = self.processar_arquivos_zip(portal_file_path)

        self.front = front

        self.kobraki = kobraki

        self.funcao = funcao if funcao is not None else None

        self.historico = historico if historico is not None else None

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
        self.conciliacao.rename(columns={'NOVO TIPO DE OPERAÇÃO': 'PRODUTO', 'TIPO OPERAÇÃO': 'PRODUTO', 'PRODUTOS PELO D8': 'PRODUTO', 'PRODUTO ATUALIZADO': 'PRODUTO'}, inplace=True)

        self.orbital = orbital if orbital is not None else None

        self.condicoes_1 = load_esteiras()

        # --- TABELA DE CONFIGURAÇÃO (Baseada na sua imagem) ---
        # 0 significa que o campo não existe ou deve ser ignorado
        self.LAYOUT_CONFIG = {
            "PREF. AÇAILÂNDIA": {"MAT": 12, "CPF": 11, "NOME": 50, "EST": 3, "ORG": 3, "COD": 3, "VAL": 10, "PRZ": 3,
                                "COMP": 6, "OP": 1},
            "PREF. BELO HORIZONTE": {"MAT": 10, "CPF": 11, "NOME": 50, "EST": 3, "ORG": 3, "COD": 4, "VAL": 10, "PRZ": 3,
                                    "COMP": 6, "OP": 1},
            "PREF. MACAÉ": {"MAT": 10, "CPF": 11, "NOME": 50, "EST": 3, "ORG": 3, "COD": 4, "VAL": 10, "PRZ": 3,
                           "COMP": 6, "OP": 1},
            "PREF. PIRACICABA": {"MAT": 10, "CPF": 11, "NOME": 0, "EST": 3, "ORG": 3, "COD": 4, "VAL": 10, "PRZ": 3,
                                "COMP": 6, "OP": 1},
            "PREVIPALMAS": {"MAT": 10, "CPF": 11, "NOME": 50, "EST": 3, "ORG": 4, "COD": 5, "VAL": 10, "PRZ": 3,
                            "COMP": 6, "OP": 1},
            "IGEPREV": {"MAT": 20, "CPF": 11, "NOME": 50, "EST": 3, "ORG": 3, "COD": 5, "VAL": 10, "PRZ": 3, "COMP": 6,
                        "OP": 1},
            "GOV. ESPÍRITO SANTO": {"MAT": 12, "CPF": 11, "NOME": 50, "EST": 0, "ORG": 0, "COD": 24, "VAL": 10, "PRZ": 3, "COMP": 6,
                       "OP": 1},
            "PREF. CAMPINAS": {"MAT": 10, "ORG": 2, "COD": 3, "OP": 1, "PRZ": 2, "VAL": 10, "COMP": 8},

            "GOV. PARANÁ": {"MAT": 20, "CPF": 11, "NOME": 50, "EST": 3, "ID_ORG": 10, "COD": 4, "VAL": 10, "PRZ": 3, "COMP": 6,
                            "OP": 1}
        }

        self.arquivo_lancamento()

    def processar_arquivos_zip(self, lista_zips):
        lista_dfs = []

        print(f'Lista Zips: {lista_zips}')
        
        # Se não for uma lista (ex: um único arquivo), transforma em lista
        if not isinstance(lista_zips, list):
            lista_zips = [lista_zips]

        for arquivo_upload in lista_zips:
            try:
                # O pulo do gato: lemos o conteúdo do upload para a memória (BytesIO)
                conteudo_zip = io.BytesIO(arquivo_upload.file.read())
                
                with zipfile.ZipFile(conteudo_zip) as zf:
                    for arquivo_interno in zf.namelist():
                        nome_upper = arquivo_interno.upper()
                        
                        if arquivo_interno.lower().endswith('.csv') and \
                        ("ALTERACAO" in nome_upper or "INCLUSAO" in nome_upper or 'PROVISIONAMENTO' in nome_upper):
                            
                            with zf.open(arquivo_interno) as f:
                                # Lendo o CSV direto da memória
                                df_temp = pd.read_csv(f, sep=';', encoding='latin1')
                                # df_temp = df_temp.dropna(axis=1, how='all')
                                # Expand=True transforma o resultado em duas colunas novas
                                # n=1 garante que ele só separe no PRIMEIRO separador encontrado
                                df_temp.insert(1, "Matrícula", "", True)
                                df_temp.insert(2, "Servidor", "", True)
                                df_temp[['Matrícula', 'Servidor']] = df_temp['SERVIDOR'].str.split(' - ', n=1, expand=True)
                                df_temp.rename(columns={'VLR RESERV.': 'Vlr novo'}, inplace=True)
                                print(f'Colunas de df_temp: {df_temp.columns}')

                                
                                if len(df_temp) > 3:
                                    df_temp = df_temp.iloc[:-3]
                                    lista_dfs.append(df_temp)
                                    
            except Exception as e:
                print(f"Erro ao processar arquivo vindo do navegador: {e}")

        if not lista_dfs:
            return pd.DataFrame()

        df_final = pd.concat(lista_dfs, ignore_index=True)

        nome_averbado = f"RELATORIO CARTAO {self.convenio} {self.consignataria} {datetime.now().strftime("%m-%Y")}"
        df_final.to_excel(fr'{self.caminho}\{nome_averbado}.xlsx', index=False)

        return df_final

    def unifica_historico_averb(self):
        averbados_atual = self.averbados
        colunas = averbados_atual.columns

        # FORMA CORRETA
        hist_df = self.historico if self.historico is not None else pd.DataFrame(columns=colunas)

        hist_df_reduzido = hist_df[colunas].copy()

        averbados_atual_reduzido = averbados_atual[colunas].copy()

        averbacao_completa = pd.concat([averbados_atual_reduzido, hist_df_reduzido], ignore_index=True)

        # --- TRATAMENTO DE DATA E HORA ---
        # Verifica se a coluna existe antes de tentar processar
        if 'Data ocor.' in averbacao_completa.columns:
            # Converte para datetime (formato dd/mm/aaaa hh:mm)
            # errors='coerce' vai transformar em NaT se a data estiver zoada
            averbacao_completa['Data_Completa_Temp'] = pd.to_datetime(
                averbacao_completa['Data ocor.'],
                format='%d/%m/%Y %H:%M:%S',
                errors='coerce'
            )

            # Separa Data e Hora
            averbacao_completa['Data'] = averbacao_completa['Data_Completa_Temp'].dt.date
            averbacao_completa['Hora'] = averbacao_completa['Data_Completa_Temp'].dt.time

            # Remove a coluna temporária (opcional)
            averbacao_completa.drop(columns=['Data_Completa_Temp'], inplace=True)

            # --- ORDENAÇÃO ---
            # Ordena pelos mais recentes (Decrescente)
            averbacao_completa = averbacao_completa.sort_values(by=['Data', 'Hora'], ascending=[False, False])

            # Remove duplicatas por Matrícula
            # averbacao_completa.drop_duplicates(subset=['Matrícula'], keep='first', inplace=True)

            # Transforma toda a coluna de Vlr novo em string
            averbacao_completa['Vlr novo'] = averbacao_completa['Vlr novo'].astype(str).str.replace(".", ",")
        else:
            print("Aviso: Coluna 'Data ocor.' não encontrada no DataFrame final.")

        nome_averbacao_completa = f"HISTÓRICO DE AVERBAÇÕES {self.convenio} {self.consignataria} {datetime.now().strftime("%m-%Y")}"

        averbacao_completa.to_excel(fr'{self.caminho}\{nome_averbacao_completa}.xlsx', index=False)

        return averbacao_completa
    
    def unifica_front_funcao(self):
        front = self.front
        funcao = self.funcao

        if funcao is None:
            return front

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
        front_consig = self.front.copy()

        if "OBS" in front_consig.columns:
            front_consig = front_consig.drop(columns=['OBS'])

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
        # print(f'colunas de front consig: {front_consig.columns}')
        try:
            tipo_conci = front_consig['Contrato'].map(conciliacao.set_index('CONTRATOS')['PRODUTO'].to_dict())
        except Exception as e:
            print(f'Coluna PRODUTO não se encontra na conciliação. Erro: {e}')
            return False
        
        front_consig.insert(19, 'Tipo Conciliação', tipo_conci, True)

        # Adiciona só as esteiras que podem ser lançadas
        front_consig_esteiras = front_consig[front_consig['Esteira'].isin(self.condicoes_1)].copy()

        # Trata coluna de Tipo da Conciliação
        front_consig_esteiras.loc[front_consig_esteiras['Tipo Conciliação'].isin([np.nan, '', ' - ']), 'Tipo Conciliação'] = front_consig_esteiras['Tipo Operacao']

        # --------------------------------------------- ORBITAL --------------------------------------------- #
        # --- ETAPA 1: Garantir que as chaves são do mesmo tipo (Texto) ---
        # Isso evita o erro clássico onde um lado é número e o outro é texto
        if orbital is not None:
            front_consig_esteiras['Contrato'] = front_consig_esteiras['Contrato'].astype(str).str.strip()
            # orbital.rename(columns={'id_contr_banco': 'Numero de Contrato'}, inplace=True)

            if orbital['VALID DESCONTO FINAL'].dtype != "float64":
                orbital['VALID DESCONTO FINAL'] = orbital['VALID DESCONTO FINAL'].astype(str).str.replace(".", "")
                orbital['VALID DESCONTO FINAL'] = orbital['VALID DESCONTO FINAL'].astype(str).str.replace(",", ".")
                orbital['VALID DESCONTO FINAL'] = pd.to_numeric(orbital['VALID DESCONTO FINAL'], errors='coerce')

            for col in orbital.columns:
                if "contrato" in col or "Contrato" in col:
                    orbital.rename(columns={col:"CONTRATO"}, inplace=True)
            orbital['CONTRATO'] = orbital['CONTRATO'].astype(str)
            

            orbital['CONTRATO'] = orbital['CONTRATO'].astype(str)
            '''print(f'\nContrato 301268942 na coluna Numero de Contrato: {orbital.loc[orbital["Numero de Contrato"] == "301268942", "Validação  desconto final"]}\n')
            print(f'Contrato 301268942 no front: {front_consig_esteiras.loc[front_consig_esteiras["Contrato"] == "301268942", "Prestacao"]}\n')'''


            # --- ETAPA 2: Criar o "Dicionário de Busca" da Orbital ---
            # Transforma a Orbital em uma série onde Índice = Contrato e Valor = Desconto
            mapa_orbital = orbital.set_index('CONTRATO')['Valor da Parcela']
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

        if self.consignataria == 'CIASPREV':
            front_consig_validado_termino.loc[(front_consig_validado_termino['Consignataria'] != 'CIASPREV') & (front_consig_validado_termino['OBS'] == ''), 'OBS'] = 'NÃO LANÇAR - CONSIGNATÁRIA ERRADA'
        elif self.consignataria == 'HOJE PREVIDENCIA PRIVADA':
            front_consig_validado_termino.loc[(front_consig_validado_termino['Consignataria'] != 'HOJE PREVIDENCIA PRIVADA') & (front_consig_validado_termino['OBS'] == ''), 'OBS'] = 'NÃO LANÇAR - CONSIGNATÁRIA ERRADA'
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
        if self.convenio in ['PREF. BELO HORIZONTE', 'PREF. CAMPINAS', 'GOV. PARANÁ']:
            print(f'Convenio é {self.convenio}')
            print(f'Convenio está em PREF. BELO HORIZONTE? {self.convenio in ['PREF. BELO HORIZONTE', 'PREF. CAMPINAS', 'GOV. PARANÁ']}')
            front_consig_validado_termino.loc[(~front_consig_validado_termino['Tipo Operacao'].str.contains('Cartão de Crédito|CARTAO DE CREDITO|CARTÃO DE CRÉDITO|CARTAO BENEFICIO', na=False)), 'OBS'] = 'NÃO LANÇAR - NÃO CARTÃO'
        else:
            front_consig_validado_termino.loc[(~front_consig_validado_termino['Tipo Conciliação'].str.contains('Cartão de Crédito|CARTAO DE CREDITO|CARTÃO DE CRÉDITO', na=False)), 'OBS'] = 'NÃO LANÇAR - NÃO CARTÃO'

        # Marcar liquidados em StatusContrato
        front_consig_validado_termino.loc[(front_consig_validado_termino['Status'].str.contains('Liquidado|CANCELADO', na=False)), 'OBS'] = 'NÃO LANÇAR - LIQUIDADO'

        # TIRAR BANCO OUTROS
        front_consig_validado_termino.loc[(front_consig_validado_termino['Consignataria'].str.contains('OUTROS', na=False)), 'OBS'] = 'NÃO LANÇAR - BANCO OUTROS'  

        # Salva com os NÃO LANÇAR
        print(f"tratamento_front_preliminar: Tentando salvar FRONT SEMI TRABALHADO em: {self.caminho}")
        try:
            front_consig_validado_termino.to_excel(fr'{self.caminho}\FRONT SEMI TRABALHADO {self.convenio} {self.consignataria} {datetime.now().strftime("%m-%Y")}.xlsx', index=False)
            print("tratamento_front_preliminar: Arquivo salvo com sucesso!")
        except Exception as e:
            print(f"DEBUG: ERRO AO SALVAR FRONT SEMI TRABALHADO: {e}")

        # --------------------------------------------------------------------------------------------- #
        return front_consig_validado_termino
        

    def trata_conciliacao(self):
        print(f'trata_conciliacao foi acionado')
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

    def validacao_termino(self, front):
        print(f'validacao_termino acionado')
        front_copy = front.copy()
        teste_conciliacao = TRATA_CONCILIACAO(self.conciliacao, self.kobraki)
        conciliacao_tratado = teste_conciliacao.trata_conciliacao()

        conciliacao_tratado['CONTRATOS'] = conciliacao_tratado['CONTRATOS'].astype('float64')
        conciliacao_tratado['CONTRATOS'] = conciliacao_tratado['CONTRATOS'].astype('Int64')

        # Puxar o último status para o front
        status = conciliacao_tratado.filter(like='ST ')
        status_name = status.columns[-1]
        '''print(f'Tipo do contrato no front: {type(front_copy.loc[1, 'Contrato'])}')
        print(f'Tipo do contrato da conciliação: {type(conciliacao_tratado.loc[1, 'CONTRATOS'])}')'''

        # Certifica que todos os contratos no Credbase trabalhado são do mesmo tipo
        # front['Contrato'] = front['Contrato'].astype(str)

        # 1. Garante que a coluna aceite qualquer tipo de dado (evita o erro de dtype 'str')
        front_copy['Status'] = front_copy['Status'].astype(str)

        # 2. Cria o mapeamento sem o .to_dict()
        # O .map() já devolve uma Series alinhada ao index, o que é o correto
        mapeamento = conciliacao_tratado.set_index('CONTRATOS')[status_name]
        front_copy['Status'] = front_copy['Contrato'].map(mapeamento).fillna('NÃO ENCONTRADO')
        conciliacao_tratado.to_excel(fr'{self.caminho}\Conciliacao_TESTE.xlsx', index=False)


        # print(f'status \n{front_copy[front_copy['Contrato'] == 300846910]}')

        # Puxar o saldo para o front
        if not front_copy['Saldo'].dtype != 'float64':
            front_copy['Saldo'] = front_copy['Saldo'].astype(str).replace('.', '', regex=False).replace(',', '.', regex=False)
            front_copy['Saldo'] = pd.to_numeric(front_copy['Saldo'], errors='coerce')

        print(f'Tipo da coluna Contrato no front: {front_copy['Contrato'].dtype}')
        print(f'Tipo da coluna Contrato na conciliação: {conciliacao_tratado['CONTRATOS'].dtype}')
        mapeamento_saldo = conciliacao_tratado.set_index('CONTRATOS')['Saldo']
        front_copy['Saldo'] = front_copy['Contrato'].map(mapeamento_saldo).fillna(-np.inf)

        # Valor que vai ser lançado
        # Substitui NaN em "Saldo" por um valor muito alto (para que "Prestacao" seja escolhida)
        if front_copy['Prestacao'].dtype != 'float64':
            front_copy['Prestacao'] = front_copy['Prestacao'].astype(str).str.replace(".", "")
            front_copy['Prestacao'] = front_copy['Prestacao'].astype(str).str.replace(",", ".")
            front_copy['Prestacao'] = pd.to_numeric(front_copy['Prestacao'], errors='coerce')
        print(f'\nTeste de Prestacao:\n{front_copy['Prestacao'].head()}\n')
        print(f'Tipo de prestacao: {front_copy['Prestacao'].dtype}')
        valor_a_lancar = np.minimum(np.abs(front_copy['Saldo']).fillna(float('inf')), front_copy['Prestacao'])

        front_copy['Valor a lançar'] = valor_a_lancar

        return front_copy

    def extrair_contratos_com_referencia(self, df_sujo: pd.DataFrame, df_limpo: pd.DataFrame) -> pd.DataFrame:
        """
        Extrai e limpa números de contrato de um DataFrame usando outro como referência.

        Args:
            df_sujo (pd.DataFrame): O DataFrame correspondente à "Planilha A",
                                    com a coluna de contratos poluída (ex: 'CONTRATOS')
                                    e uma coluna de CPF (ex: 'CPF').
            df_limpo (pd.DataFrame): O DataFrame correspondente à "Planilha B",
                                     com colunas de contratos limpos e CPF.

        Returns:
            pd.DataFrame: O DataFrame original (df_sujo) com novas colunas para cada
                          contrato encontrado e limpo.
        """


        print("Iniciando o processo de extração de contratos...")

        # Função de limpeza (pode ser definida aqui ou fora)
        def limpar_contrato(texto: str) -> str:
            if not isinstance(texto, str):
                texto = str(texto)
                texto = texto.replace(" ", "")
            return re.sub(r'[^0-9a-zA-Z]', '', texto)  # Mantém letras e números

        # --- Passo 1: Criar o mapa de referência (sem alterações) ---
        print(f'df_limpo: {df_limpo}')
        df_limpo['Contrato'] = df_limpo['Contrato'].astype(str).str.strip()
        print("Criando mapa de referência CPF -> Contratos...")
        cpf_contratos = df_limpo.groupby('CPF')['Contrato'].apply(list).to_dict()
        # print(f'Mapa contratos:\n{cpf_contratos}')

        # --- Passo 2: Definir a função que será aplicada em cada linha (LÓGICA ALTERADA) ---
        def encontrar_contratos_na_linha(row):
            cpf = row['CPF']
            texto_contratos_sujo = str(row['Id. ADE'])

            # Garante que as listas existam
            contratos_validos_para_cpf = cpf_contratos.get(cpf, [])

            if not contratos_validos_para_cpf:
                return []

            # 1. DIVIDIR: Mesma lógica de limpeza
            partes_sujas = [p for p in re.split(r'[-/,;\s]+', texto_contratos_sujo) if p]

            if not partes_sujas:
                return []

            encontrados_nesta_linha = []

            # Listas de controle
            contratos_disponiveis = list(contratos_validos_para_cpf)

            # --- MUDANÇA: LIMIAR ALTO ---
            # Agora podemos exigir quase perfeição porque mudamos o método de comparação
            LIMIAR_SEGURO = 70

            for parte in partes_sujas:
                parte_limpa = limpar_contrato(parte)
                if not parte_limpa or len(parte_limpa) < 3:
                    continue

                melhor_match_para_parte = None
                maior_score_ponderado = 0  # Mudamos o nome para deixar claro

                for i, contrato_valido in enumerate(contratos_disponiveis):

                    # Vamos testar os dois alvos separadamente
                    alvos = [
                        (contrato_valido, 'CONTRATO'),
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
        df_sujo['Id. ADE'] = df_sujo['Id. ADE'].astype(str).str.replace('nan', '')

        lista_de_contratos_encontrados = df_sujo.apply(encontrar_contratos_na_linha, axis=1)

        df_contratos_novos = pd.DataFrame(lista_de_contratos_encontrados.tolist(), index=df_sujo.index)
        df_contratos_novos.columns = [f'Contrato Editado {i + 1}' for i in df_contratos_novos.columns]

        df_resultado = pd.concat([df_sujo, df_contratos_novos], axis=1)

        print("Processo concluído com sucesso!")
        r'''df_resultado.to_excel(fr'{self.caminho}\Relatório Averbados Contratos tratados.xlsx', index=False)'''
        return df_resultado

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
        data_averbados['Lançar'] = np.minimum(data_averbados['Soma_Calculada'], data_averbados['Vlr novo'])
        print(f'\ndata_averbados_peculio\n{data_averbados['Vlr novo']}\n')

        # (Opcional) Remove a coluna temporária se não precisar mais
        data_averbados = data_averbados.drop(columns=['Soma_Calculada'])

        return data_averbados

    def orbital_tratado(self, orbital, front_so_orbital):
        if orbital is None:
            return None
        
        orbital_preparado = pd.DataFrame(columns=['CONTRATO', 'nome_mutuario', 'num_cpf_mutuario', 'VALID DESCONTO FINAL'])

        if self.convenio == 'PREF. PIRACICABA':
            orbital_preparado = orbital.loc[
                orbital['DESCRIÇÃO DO EMPREG'].str.contains('PREF PIRACICABA', case=False, na=False),
                ['CONTRATO', 'nome_mutuario', 'num_cpf_mutuario', 'VALID DESCONTO FINAL']
            ].copy()
        elif self.convenio == 'PREF. PIRACICABA SEMAE':
            orbital_preparado = orbital.loc[
                orbital['DESCRIÇÃO DO EMPREG'].str.contains('PREF PIRA SEMAE', case=False, na=False),
                ['CONTRATO', 'nome_mutuario', 'num_cpf_mutuario', 'VALID DESCONTO FINAL']
            ].copy()

        elif self.convenio == 'PREF. CAMPINAS':
            orbital_preparado = orbital.loc[
                orbital['DESCRIÇÃO DO EMPREG'].str.contains('PREF CAMPINAS', case=False, na=False),
                ['CONTRATO', 'nome_mutuario', 'num_cpf_mutuario', 'VALID DESCONTO FINAL']
            ].copy()
        elif self.convenio == 'GOV. PARANÁ':
            orbital_preparado = orbital.loc[
                orbital['DESCRIÇÃO DO EMPREG'].str.contains('GOV PR DG|GOV PARANA|GOV PARANA SEG', case=False, na=False),
                ['CONTRATO', 'nome_mutuario', 'num_cpf_mutuario', 'VALID DESCONTO FINAL']
            ].copy()

        orbital_preparado.columns = ['Proposta', 'Cliente', 'CPF/CNPJ', 'VALOR DESCONTO']

        if 'NÃO LANÇAR - ORBITAL' not in front_so_orbital['OBS'].values:
            print('Não há registros de ORBITAL para tratar.')
            return None

        # front_so_orbital['Proposta'] = front_so_orbital['Proposta'].astype(str).str.strip()

        front_so_orbital = front_so_orbital.loc[
            front_so_orbital['OBS'] == 'NÃO LANÇAR - ORBITAL',
            ['Contrato', 'Nome', 'CPF', 'Prestacao']].copy()
        
        front_so_orbital.columns = ['Proposta', 'Cliente', 'CPF/CNPJ', 'VALOR DESCONTO']

        # front_so_orbital['VALOR DESCONTO'] = front_so_orbital['VALOR DESCONTO'].astype(str).str.replace('.', '', regex=False)
        front_so_orbital['VALOR DESCONTO'] = front_so_orbital['VALOR DESCONTO'].astype(str).str.replace(',', '.', regex=False)
        front_so_orbital['VALOR DESCONTO'] = pd.to_numeric(front_so_orbital['VALOR DESCONTO'], errors='coerce')

        orbital_final = pd.concat([front_so_orbital, orbital_preparado])

        orbital_final = orbital_final.drop_duplicates(subset=['Proposta'], keep='first')

        print(f"orbital_tratado: Salvando arquivo de orbital tratado teste com front")
        try:
            orbital_final.to_excel(os.path.join(self.caminho, f"ORBITAL TRABALHADO {self.convenio}.xlsx"), index=False)
            print(f"orbital_tratado: ORBITAL TRABALHADO {self.convenio} salvo com sucesso!")
        except Exception as e:
            print(f"orbital_tratado: ERRO AO SALVAR ORBITAL TRABALHADO {self.convenio}: {e}")

        return orbital_final

    def trata_averbacao(self):
        # PUXA OS ARQUIVOS À SEREM TRATADOS
        print('trata_averbacao foi acionado')
        data = self.unifica_historico_averb()
        front = self.tratamento_front_preliminar()
        consig = self.consignataria
        orbital_tratado = self.orbital_tratado(self.orbital, front)
        convenio = self.convenio

        '''if self.convenio == 'GOV. PARANÁ':
            data.insert(14, 'Id. serviço', '', True)
            data.insert(15, 'Serviço', '', True)'''

        data_averbados_bruto = data

        # Vou tentar colocar a coluna de Orbital aqui no meio mesmo
        if orbital_tratado is not None:
            mask_orbital = orbital_tratado.groupby('CPF/CNPJ')['VALOR DESCONTO'].sum()
            data_averbados_bruto['ORBITAL'] = ''
            data_averbados_bruto['ORBITAL'] = data_averbados_bruto['CPF'].map(mask_orbital)

        def distribuicao_valores(averbado_trabalhado, front_trabalhar):
            # IMPORTANTE: Garanta que as colunas de valores são numéricas, não texto.
            # O .to_numeric(errors='coerce') converte o que for possível para número e põe NaN no que não for.
            averbado_novo = averbado_trabalhado
            # Remoção de duplicatas por matrícula
            # averbado_novo.drop_duplicates(subset=['Matrícula'], keep='first', inplace=True)
            
            front_preliminar = front_trabalhar.copy()

            soma_series_averb = front_preliminar.groupby('CPF')['Valor a lançar'].sum()

            # 2. Agora o .add() vai funcionar, pois soma_series_averb ainda é um objeto Pandas
            # Supondo que mask_orbital também seja uma Series de CPFs e valores
            # soma_total = soma_series_averb.add(mask_orbital, fill_value=0)

            if averbado_novo['Vlr novo'].dtype != 'float64':
                averbado_novo['Vlr novo'] = averbado_novo['Vlr novo'].astype(str).str.replace(".", "")
                averbado_novo['Vlr novo'] = averbado_novo['Vlr novo'].astype(str).str.replace(",", ".")
                averbado_novo['Vlr novo'] = pd.to_numeric(averbado_novo['Vlr novo'], errors='coerce').fillna(0)

            averbado_novo['SOMASE FRONT'] = averbado_novo['CPF'].map(soma_series_averb)
            averbado_novo['SOMASE FRONT'] = pd.to_numeric(averbado_novo['SOMASE FRONT'], errors='coerce').fillna(0)

            # NOTA: Como não há coluna de prioridade, a ordem de distribuição dependerá
            # da ordem atual do DataFrame. Se precisar de uma ordem específica,
            # um .sort_values() viria aqui.

            # 1. Calcula a soma ACUMULADA da reserva dentro de cada grupo de CPF.
            # Esta é a "mágica" que substitui a necessidade de um loop.
            averbado_novo['SOMA ACUMULADA DA RESERVA'] = averbado_novo.groupby('CPF')['Vlr novo'].cumsum()

            # 2. Calcula o valor que JÁ FOI ALOCADO para as linhas ANTERIORES.
            # É a soma acumulada até a linha atual, menos o valor da própria linha.
            alocado_anteriormente = averbado_novo['SOMA ACUMULADA DA RESERVA'] - averbado_novo['Vlr novo']
            averbado_novo['ALOCADO ANTERIORMENTE'] = alocado_anteriormente

            # 3. Calcula o saldo restante do SOMASE ANTES de processar a linha atual.
            saldo_restante = averbado_novo['SOMASE FRONT'] - alocado_anteriormente

            # 4. O valor a lançar é o MÍNIMO entre o que a reserva da linha pede e o saldo que ainda temos.
            # Usamos .clip(0) para garantir que o saldo não seja negativo (se já estourou, é 0).
            valor_a_lancar = np.minimum(averbado_novo['Vlr novo'], saldo_restante.clip(0))

            # 5. Atribui o resultado final arredondado às colunas.
            averbado_novo['Lançar'] = valor_a_lancar.round(2)

            # 6. Preenche a coluna OBS para linhas que não receberam nada.
            averbado_novo.loc[averbado_novo['Lançar'] == 0, 'OBS'] = 'NÃO'

            return averbado_novo
        
        if self.convenio != 'GOV. RIO DE JANEIRO':
            data_averbados = distribuicao_valores(data_averbados_bruto, front)

            # print("Cálculos de Soma e Diferença finalizados.")
            data_averbados.to_excel(fr'{self.caminho}\TRABALHADO CARTAO {convenio} {self.consignataria} {datetime.now().strftime("%m-%Y")}.xlsx', index=False)

            return data_averbados

        data_averbados = self.extrair_contratos_com_referencia(data_averbados_bruto, front)

        semi_front = front[front['Esteira'].isin(self.condicoes_1)]

        teste_conciliacao = TRATA_CONCILIACAO(self.conciliacao, self.kobraki)
        conciliacao_tratado = teste_conciliacao.trata_conciliacao()

        # Operações liquidadas. Tratando NRº OPER EDITADO
        # OP LIQUIDADO
        try:
            oper_liq = front[front['Status'].str.contains('Liquidado|CANCELADO')]
            contratos_tratados_liq = oper_liq['Contrato'].astype(str).str.slice(0, 9)
            oper_liq.insert(1, "Nº OPERAÇÃO EDITADO", contratos_tratados_liq, True)
        except ValueError:
            oper_liq = pd.DataFrame()
            oper_liq["Nº OPERAÇÃO EDITADO"] = ''
            oper_liq["Contrato"] = ''

        tutela = front[front['Acao Judicial'] == 'SIM']

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
                conciliacao_tratado.set_index('CONTRATOS')['Saldo'].to_dict()
            )

            # Puxando os contratos liquidados (FORMA CORRIGIDA)
            # Cria a nova coluna 'OP LIQ {i}' com o resultado do map
            data_averbados[f'OP LIQ {i}'] = data_averbados[nome_coluna_contrato].map(
                oper_liq.set_index('Nº OPERAÇÃO EDITADO')['Contrato'].to_dict()
            )

            # --- PASSO 2: PREPARAÇÃO E LIMPEZA DE DADOS ---
            # Agora que todas as colunas foram criadas, garantimos que sejam numéricas para os cálculos.
            if data_averbados[f'Valor_Unif_{i}'].dtype != 'float64':
                data_averbados[f'Valor_Unif_{i}'] = data_averbados[f'Valor_Unif_{i}'].astype(str).str.replace(".", '')
                data_averbados[f'Valor_Unif_{i}'] = data_averbados[f'Valor_Unif_{i}'].astype(str).str.replace(",", '.')

            data_averbados[f'Valor_Unif_{i}'] = pd.to_numeric(data_averbados[f'Valor_Unif_{i}'],
                                                            errors='coerce').fillna(0)
            data_averbados[f'Saldo {i}'] = pd.to_numeric(data_averbados[f'Saldo {i}'], errors='coerce').fillna(-np.inf)

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
        data_averbados["LIMINAR"] = data_averbados['CPF'].map(tutela.set_index('CPF')['Contrato'].to_dict())
        condicao_liminar = data_averbados['LIMINAR'].notna()

        # --- 3. Soma todos os valores encontrados (forma eficiente) ---

        # Pega a lista de todas as colunas de valor que acabamos de criar

        # colunas_valores_unificados = [col for col in data_averbados.columns if 'Valor_Unif_' in col]
        colunas_valores_unificados = data_averbados.filter(like='Valor_Unif_')

        # NOVO PASSO: Adiciona a coluna 'ORBITAL' ao DataFrame de colunas para soma
        colunas_para_somar = colunas_valores_unificados.copy()  # Cria uma cópia para garantir a segurança

        # Verifica se 'ORBITAL' já existe antes de adicionar (apenas por garantia, embora o código garanta)
        if 'ORBITAL' in data_averbados.columns:
            # Usa .loc para garantir que a coluna seja adicionada
            colunas_para_somar.loc[:, 'ORBITAL'] = data_averbados['ORBITAL']


        '''if colunas_valores_unificados:
            # print(f"Somando os valores das colunas: {colunas_valores_unificados}")
            data_averbados['Soma'] = colunas_para_somar.sum(axis=1)
        else:
            print("Nenhuma coluna de valor encontrada. A coluna 'Soma' será inicializada com 0.")
            data_averbados['Soma'] = 0'''

        data_averbados['Soma'] = colunas_para_somar.sum(axis=1)

        # --- 4. Cálculo da Diferença e Formatação Final ---

        # Garante que a coluna de Vlr novo é numérica antes do cálculo
        data_averbados['Vlr novo'] = data_averbados['Vlr novo'].str.replace('.', '')
        data_averbados['Vlr novo'] = data_averbados['Vlr novo'].str.replace(',', '.')
        data_averbados['Vlr novo'] = pd.to_numeric(data_averbados['Vlr novo'], errors='coerce').fillna(0)

        data_averbados['Diff'] = data_averbados['Soma'] - data_averbados['Vlr novo']
        data_averbados['Diff'] = data_averbados['Diff'].round(2)

        # --- 5. Cria a coluna Lançar ---
        print(f'CONSIGNATARIA: {self.consignataria}')
        if consig == 'HOJE PREVIDENCIA PRIVADA':
            data_averbados = self.adiciona_peculio(data_averbados)
        else:
            data_averbados['Lançar'] = np.minimum(data_averbados['Soma'], data_averbados['Vlr novo'])
            data_averbados.loc[condicao_liminar, 'Lançar'] = 0

        # Remoção de duplicatas por matrícula
        # data_averbados.drop_duplicates(subset=['Matrícula'], keep='first', inplace=True)

        # print("Cálculos de Soma e Diferença finalizados.")
        data_averbados.to_excel(fr'{self.caminho}\TRABALHADO CARTAO {convenio} {self.consignataria} {datetime.now().strftime("%m-%Y")}.xlsx', index=False)

        return data_averbados

    def tratamento_front(self, averbado_trabalhado):
        print('tratamento_front foi acionado.')
        front_consig = self.tratamento_front_preliminar()

        if front_consig is False:
            print("tratamento_front: O tratamento preliminar do front falhou. Verifique os erros anteriores.")
            return False

        # CORREÇÃO 2: Garante que a coluna-chave principal seja string e sem espaços
        front_consig['Contrato'] = front_consig['Contrato'].astype(str).str.strip()
        print(f'comprimento de front_consig\n{len(front_consig)}')

        # ----------------------------- TRATAR AS ESTEIRAS DE CREDBASE TRABALHADO --------------------------------------

        # --- CORREÇÃO 1: Limpa os valores da Esteira, substituindo por NaN (NULO) ---
        # Usar .loc é mais seguro e evita avisos (SettingWithCopyWarning)
        # Trocamos '' por np.nan para que o .fillna() dentro do loop funcione.
        '''condicao_limpeza = cred['Codigo_Credbase'].str.len() > 6
        cred.loc[condicao_limpeza, 'Esteira'] = np.nan'''

        # REMOVIDO: A linha cred['Esteira'] = cred['Esteira'].fillna('') foi removida.
        # É ela que quebrava a lógica.

        # Encontra as colunas de contrato em 'averbado_trabalhado'
        colunas_contratos = [col for col in averbado_trabalhado.columns if 'Contrato Editado' in col]

        # Loop corrigido
        for nome_coluna_contrato in colunas_contratos:
            try:
                idx = nome_coluna_contrato.split(' ')[-1]
                coluna_esteira_correspondente = f'Esteira_{idx}'

                print(f"Mapeando com '{nome_coluna_contrato}' para preencher 'Esteira'...")

                # CORREÇÃO 2: Garante que a coluna-chave do mapa também seja string
                # Fazemos a conversão ANTES de criar o dicionário.
                chaves_mapa = averbado_trabalhado[nome_coluna_contrato].astype(str).str.strip()
                valores_mapa = averbado_trabalhado[coluna_esteira_correspondente]

                # Cria o mapa de Contrato -> Esteira para esta iteração
                mapa = pd.Series(valores_mapa.values, index=chaves_mapa).to_dict()

                # Usa o mapa para criar uma série de novos valores
                # A conversão aqui é uma segurança extra, mas a principal é na linha de cima
                novas_esteiras = front_consig['Contrato'].map(mapa)

                # AGORA VAI FUNCIONAR: preenche APENAS os vazios (NaN) em 'Esteira' com os novos valores
                front_consig['Esteira'] = front_consig['Esteira'].fillna(novas_esteiras)

            except (IndexError, KeyError) as e:
                print(f"Aviso: Não foi possível processar o par de colunas para '{nome_coluna_contrato}'. Erro: {e}")

                # print(type(cred.loc[cred['Codigo_Credbase'] == '301361499', 'Codigo_Credbase']))

            except (IndexError, KeyError) as e:
                print(f"Aviso: Não foi possível processar o par de colunas para '{nome_coluna_contrato}'. Erro: {e}")

        # --------------------------------------------------------------------------------------------------------------

        # Separa apenas o que retornou como "cartão de crédito" no tipo de conciliação
        if self.convenio in ['PREF. GOIÂNIA', 'PREF. DUQUE DE CAXIAS', 'PREF. BELO HORIZONTE', 'PREF. CAMPINAS', 'GOV. PARANÁ']:
            front_consig_cartao_conciliacao = front_consig[front_consig['Tipo Operacao'].str.contains('Cartão de Crédito|CARTAO DE CREDITO|CARTÃO DE CRÉDITO|CARTAO BENEFICIO', na=False)].copy()
        else:
            front_consig_cartao_conciliacao = front_consig[front_consig['Tipo Conciliação'].str.contains('Cartão de Crédito|CARTAO DE CREDITO|CARTÃO DE CRÉDITO', na=False)].copy()

        print(f'comprimento de front_consig_cartao_conciliacao de Separa apenas o que retornou como "cartão de crédito"\n{len(front_consig_cartao_conciliacao)}')

        # Separar o que não é cartão de crédito da conciliação
        # front_consig_nao_cartao = front_consig[~front_consig['Tipo Conciliação'].str.contains('Cartão de Crédito', na=False)].copy()

        # Pegar o que é CARTAO DE CREDITO do front
        # condicao_cartao = ['CARTAO DE CREDITO']
        # front_consig_cartao_front = front_consig_nao_cartao[front_consig_nao_cartao['dsTipoOperacao'].isin(condicao_cartao)].copy()
        # Faz concat dos dois dataframes
        front_consig_trabalhado = front_consig_cartao_conciliacao.copy()

        # ---------------------------------- TIRAR AÇÃO JUDICIAL DO FRONT ---------------------------------- #
        front_consig_trabalhado = front_consig_trabalhado.loc[front_consig_trabalhado['Acao Judicial'] != 1].copy()

        print(f'comprimento de front_consig_trabalhado de tirar ação judicial\n{len(front_consig_trabalhado)}')

        # ---------------------------------- TIRAR ÓBITO DO FRONT ---------------------------------- #
        # front_consig_trabalhado = front_consig_trabalhado.loc[front_consig_trabalhado['Obito'] != 1].copy()
        
        # ------------------------------------ INSERE A COLUNA DE SALDO ------------------------------------- #

        front_consig_trabalhado.loc[front_consig_trabalhado['Saldo'] > -0.01, 'Valor a lançar'] = 0
        front_consig_trabalhado = front_consig_trabalhado[front_consig_trabalhado['Valor a lançar'] > 0].copy()

        print(f'comprimento de front_consig_trabalhado de insere coluna de saldo\n{len(front_consig_trabalhado)}')

        # ---------------------------------------- AJUSTE PECÚLIO HOJE --------------------------------------- #
        '''mask_peculio = front_consig_trabalhado['Consignataria'] == 'HOJE PREVIDENCIA PRIVADA'
        front_consig_trabalhado.loc[mask_peculio, 'Valor a lançar'] += 20'''

        # ------------------------------------- ESCOLHE CONSIGNATÁRIA -------------------------------------- #
        front_consig_trabalhado['Consignataria'].fillna('', inplace=True)

        if self.consignataria == 'CIASPREV':
            front_consig_trabalhado = front_consig_trabalhado[front_consig_trabalhado['Consignataria'].str.contains('CIASPREV', na=False)].copy()
        elif self.consignataria == 'HOJE PREVIDENCIA PRIVADA':
            front_consig_trabalhado = front_consig_trabalhado[front_consig_trabalhado['Consignataria'].str.contains('HOJE PREVIDENCIA PRIVADA', na=False)].copy()
        elif self.consignataria == 'CAPITAL CONSIG':
            front_consig_trabalhado = front_consig_trabalhado[front_consig_trabalhado['Consignataria'].str.contains('CAPITAL CONSIG', na=False)].copy()
        elif self.consignataria == 'CLICKBANK':
            front_consig_trabalhado = front_consig_trabalhado[front_consig_trabalhado['Consignataria'].str.contains('CLICKBANK', na=False)].copy()
        else:
            print('Consignatária inválida.')
            return
        
        print(f'comprimento de front_consig_trabalhado de escolhe consignatária\n{len(front_consig_trabalhado)}')


        # --------------------------------------- TIRA BANCO OUTROS ----------------------------------------- #
        front_consig_trabalhado = front_consig_trabalhado[~front_consig_trabalhado['Consignataria'].str.contains('OUTROS', na=False)].copy()

        # ----------------------------------------- TIRA LIQUIDADOS ----------------------------------------- #
        front_consig_trabalhado = front_consig_trabalhado[~front_consig_trabalhado['Status'].str.contains('Liquidado|CANCELADO', na=False)].copy()

        print(f'comprimento de front_consig_trabalhado de tira liquidados\n{len(front_consig_trabalhado)}')

        # Salva com os NÃO LANÇAR
        print(f"tratamento_front: Tentando salvar FRONT TRABALHADO em: {self.caminho}")
        try:
            front_consig_trabalhado.to_excel(fr'{self.caminho}\FRONT TRABALHADO {self.convenio} {self.consignataria} {datetime.now().strftime("%m-%Y")}.xlsx', index=False)
            print("tratamento_front: Arquivo salvo com sucesso!")
        except Exception as e:
            print(f"DEBUG: ERRO AO SALVAR FRONT TRABALHADO: {e}")

        return front_consig_trabalhado

    def arquivo_lancamento(self):
        print(f'arquivo_lancamento foi acionado')
        data_averbados = self.trata_averbacao()
        
        convenio = self.convenio

        codigo_desconto_dict = {"PREF. AÇAILÂNDIA": "382", "GOV. RIO DE JANEIRO": "4541CARTAO DE CREDITO I", "IGEPREV CAPITAL": "04072",
                                "IGEPREV CIASPREV": "02470", "PREF. PIRACICABA": "5600", "PREF. PIRACICABA - SEMAE": "675",
                                "PREV. PIRACICABA": "6277", "PREF. BELO HORIZONTE CB": "204U", "PREF. BELO HORIZONTE CC": "204V",
                                "PREF. MACAÉ": "11Q0", "PREVIPALMAS CAPITAL": "10243", "PREVIPALMAS CIASPREV": "894", "PREF. CAMPINAS": "435",
                                "GOV. PARANÁ": "5408"}

        estab_dict = {"PREF. AÇAILÂNDIA": "001", "IGEPREV CAPITAL": "001", "IGEPREV CIASPREV": "001",
                      "PREF. PIRACICABA": "001", "PREF. PIRACICABA - SEMAE": "002", "PREF. CAMPINAS": "",
                      "PREV. PIRACICABA": "001", "PREF. BELO HORIZONTE CB": "001", "PREF. BELO HORIZONTE CC": "001",
                      "PREF. MACAÉ": "001", "PREVIPALMAS CAPITAL": "001", "PREVIPALMAS CIASPREV": "001",
                      "GOV. PARANÁ": "002"}

        emp_dict_gov_rj = {"ADMINISTRAÇÃO DIRETA (GOVERNO ESTADO)": "01",
                           "ENCARGOS GERAIS DO ESTADO": "01",
                           "SECRETARIA DE ESTADO DE DEFESA CIVIL": "01",
                           "SECRETARIA DE ESTADO DE ADMINISTRACAO PENITENCIARIA": "01",
                           "SECRETARIA DE ESTADO DE EDUCACAO": "01",
                           "SECRETARIA DE ESTADO DE FAZENDA": "01",
                           "SECRETARIA DE ESTADO DE POLICIA CIVIL": "01",
                           "SECRETARIA DE ESTADO DE POLICIA MILITAR": "01",
                           "SECRETARIA DE ESTADO DE SAÚDE": "01",
                           "DEPARTAMENTO DE TRANSITO DO ESTADO DO RJ": "03",
                           "FUNDACAO DE APOIO A ESCOLA TECNICA DO ESTADO RJ": "04",
                           "INSTITUTO DE ASSISTENCIA DOS SERVIDORES DO EST RJ": "08",
                           "FUNDACAO LEAO X I I I": "09",  # Atenção aos espaços no XIII
                           "FUNDACAO LEAO XIII": "09",      # Adicionei essa variação por segurança
                           "FUNDACAO UNIVERSIDADE DO ESTADO RJ": "15",
                           "EMPRESA DE ASSISTÊNCIA TÉCNICA E EXTESÃO E RURAL": "23", # "EXTESÃO" mantido conforme imagem
                           "INSTITUTO VITAL BRAZIL S/A": "24",
                           "CENTRAIS DE ABASTECIMENTO DO ESTADO RJ": "44",
                           "INSTITUTO DE PESOS E MEDIDAS": "48",
                           "FUNDAÇÃO DEPARTAMENTO DE ESTRADAS DE RODAGEM": "53",
                           "EMPRESA DE OBRAS PÚBLICAS DO EST DO RJ": "54",
                           "FUNDAÇÃO PARA INFÂNCIA E ADOLESCÊNCIA": "55",
                           "RIOPREVIDENCIA PENSOES": "77",
                           "UNIVERSIDADE EST DO NORTE FLUMINENSE DARCY RIBEIRO": "86",
                           "DEPARTAMENTO DE TRANSPORTES RODOVIARIOS DO EST RJ": "19",
                           "ADMINISTRAÇÃO DIRETA": "01"
                    }


        try:
            codigo_de_desconto = codigo_desconto_dict[convenio]
        except KeyError:
            print(f'\nConvênio {convenio} não consta no dicionário de "Códigos de Desconto!"')
            return

        estabelecimento = estab_dict[convenio] if convenio != "GOV. RIO DE JANEIRO" else None

        # Cria o novo DataFrame
        data_averbados['Matrícula'] = data_averbados['Matrícula'].astype(int)
        # print(f'\ndata_averbados - matricula\n{data_averbados['Matrícula']}')
        front_trabalhado = self.tratamento_front(data_averbados)
        
        temp = data_averbados[data_averbados['Lançar'] > 0]
        if self.convenio == 'GOV. RIO DE JANEIRO':
            colunas_alancar = ['Órgão', 'Matrícula', 'Servidor', 'CPF', 'Situação', 'Categoria', 'Consignatária', 'Id. órgão',
                    'Órgão.1', 'Id. serviço', 'Serviço', 'Nº ADE', 'Id. ADE', 'Data inc.', 'Vlr ant.', 'Vlr novo', 'Lançar']
        else:
            colunas_alancar = ['CORRESPONDENTE', 'Matrícula', 'Servidor', 'CPF', 'SITUAÇÃO', 'CATEGORIA', 'SERVIÇO', 'DATA', 'Vlr novo', 'Lançar']
        a_lancar = pd.DataFrame(temp[colunas_alancar])

        # Calcule a SOMASE para cada categoria no Averbacoes Trabalhadas
        somas_por_categoria = data_averbados.groupby('CPF')['Lançar'].transform('sum')
        data_averbados['SOMASE'] = somas_por_categoria
        data_averbados['SOMASE'] = data_averbados['SOMASE'].astype(float)

        # Calcula o Somase Cred
        data_averbados['SOMASE CRED'] = ''

        soma_condicional_dict_averb = front_trabalhado.groupby('CPF')['Valor a lançar'].sum().to_dict()
        data_averbados['SOMASE CRED'] = data_averbados['CPF'].map(soma_condicional_dict_averb)
        data_averbados['SOMASE CRED'] = data_averbados['SOMASE CRED'].map('{:.2f}'.format).astype(float)

        # DIFF
        data_averbados['DIFF'] = data_averbados['SOMASE CRED'] - data_averbados['SOMASE']

        # SOMASE NO CREDBASE TRABALHADO
        cred_somase = front_trabalhado.groupby('CPF')['Valor a lançar'].transform('sum')
        front_trabalhado.insert(16, 'SOMASE CRED', cred_somase, True)
        front_trabalhado['SOMASE CRED'] = front_trabalhado['SOMASE CRED'].map('{:.2f}'.format).astype(float)

        front_trabalhado.insert(17, 'SOMASE AVERB', '', True)
        front_trabalhado.insert(18, 'DIFF', '', True)

        # Somase Averb no Credbase Trabalhado
        soma_condicional_dict_cred = data_averbados.groupby('CPF')['Lançar'].sum().to_dict()
        front_trabalhado['SOMASE AVERB'] = front_trabalhado['CPF'].map(soma_condicional_dict_cred)
        front_trabalhado['DIFF'] = front_trabalhado['SOMASE CRED'] - front_trabalhado['SOMASE AVERB'].astype(
            float)

        # Arredonda os números
        a_lancar['Lançar'] = a_lancar['Lançar'].astype(float)
        a_lancar['Lançar'] = a_lancar['Lançar'].map('{:.2f}'.format)

        # Adiciona algumas colunas
        a_lancar.insert(3, "ESTABELECIMENTO", "", True)
        a_lancar.insert(4, "ÓRGÃO", "", True)
        a_lancar.insert(5, "CÓDIGO DE DESCONTO", "", True)
        a_lancar.insert(7, "PRAZO TOTAL", "", True)
        a_lancar.insert(8, "COMPETÊNCIA", "", True)
        a_lancar.insert(9, "CÓDIGO DA OPERAÇÃO", "", True)

        a_lancar["ESTABELECIMENTO"] = estabelecimento if self.convenio != 'GOV. RIO DE JANEIRO' else a_lancar['Órgão.1'].map(emp_dict_gov_rj)
        if self.convenio not in ['GOV. RIO DE JANEIRO']:
            a_lancar['ÓRGÃO'] = '1'
        else:
            a_lancar['ÓRGÃO'] = a_lancar['Id. órgão'] if self.convenio != 'GOV. RIO DE JANEIRO' else a_lancar['Órgão.1']

        a_lancar['CÓDIGO DE DESCONTO'] = codigo_de_desconto

        self.process_layout(a_lancar, self.caminho)


    # --- FUNÇÕES DE FORMATAÇÃO (Mantive as seguras) ---
    def format_number(self, series, length):
        if length == 0: return ""

        if isinstance(series, (str, int, float)):
            series = [series]

        # 1. Garante que é número (transforma erros/texto em NaN) e preenche vazios com 0
        s = pd.to_numeric(series, errors='coerce').fillna(0)

        # 2. Converte para INTEIRO (Aqui é a mágica: 382.0 vira 382)
        s = s.astype(int)

        # 3. Agora converte para string e aplica o zero à esquerda
        return s.astype(str).str.zfill(length).str[-length:]

    def format_cpf(self, series, length):
        if length == 0: return ""  # Se o tamanho for 0, retorna vazio

        s = series.astype(str).str.replace(r'[.\-]', '', regex=True)

        return s.str.zfill(length).str[-length:]

    def format_text(self, series, length):
        if length == 0: return ""
        s = series.astype(str).str.upper().apply(lambda x: x.ljust(length))
        return s.str[:length]
    
    def format_id_orgao(self, series, length):
        if length == 0: return ""
        s = series.astype(str).str.upper().apply(lambda x: x.ljust(length))
        return s.str[:length]

    def format_currency(self, series, length):
        """
        Formata moeda MANTENDO o ponto decimal.
        Ex: 150.5 vira 0000150.50 (se length=10)
        """
        if length == 0: return ""

        # 1. Garante que é número e preenche vazios com 0
        s = pd.to_numeric(series, errors='coerce').fillna(0)

        # 2. Formata para string forçando SEMPRE 2 casas decimais
        # Isso garante que 150 vira "150.00" e 150.5 vira "150.50"
        s = s.apply(lambda x: "{:.2f}".format(x))

        # 3. Preenche com zeros à esquerda até atingir o tamanho
        # Importante: O ponto conta como 1 caractere no tamanho total
        return s.str.zfill(length) if self.convenio != 'PREF. CAMPINAS' else s.str.replace(".", ",", regex=False).str.zfill(length)

    def format_constant(self, valor, length):
        """Para campos fixos como Competência, Prazo ou Operação"""
        if length == 0: return ""
        return str(valor).zfill(length)[:length]

    # --- LÓGICA PRINCIPAL ADAPTADA ---
    def create_layout(self, df):
        # 1. Pega a configuração do convênio atual
        regras = self.LAYOUT_CONFIG.get(self.convenio)

        if not regras:
            raise ValueError(f"ERRO: Layout não configurado para o convênio '{self.convenio}'")

        # 2. Gera os campos usando as regras dinâmicas
        # Note que agora o segundo argumento vem do dicionário 'regras'
        print(f'O que está em ÓRGÃO?\n{df['ÓRGÃO']}')

        matricula = self.format_number(df['Matrícula'], regras['MAT'])
        cpf = self.format_cpf(df['CPF'], regras['CPF']) if not self.convenio == 'PREF. CAMPINAS' else ''
        nome = self.format_text(df['Servidor'], regras['NOME']) if not self.convenio == 'PREF. CAMPINAS' else ''
        estab = self.format_number(df['ESTABELECIMENTO'], regras['EST']) if not self.convenio in ['PREF. CAMPINAS', 'GOV. PARANÁ'] else ''
        id_orgao = self.format_id_orgao(df['Id. órgão'], regras['ID_ORG']) if self.convenio == 'GOV. PARANÁ' else ''
        orgao = self.format_number(df['ÓRGÃO'], regras['ORG']) if not self.convenio == 'GOV. PARANÁ' else '' 
        cod_desc = self.format_number(df['CÓDIGO DE DESCONTO'], regras['COD']) if not self.convenio in ['GOV. RIO DE JANEIRO', 'PREF. MACAÉ'] else self.format_text(df['CÓDIGO DE DESCONTO'], regras['COD'])
        valor = self.format_currency(df['Lançar'], regras['VAL'])

        # Campos calculados na hora (Data e Constantes)
        competencia_atual = f'{str(datetime.now().month).zfill(2)}{datetime.now().year}' if not self.convenio == 'PREF. CAMPINAS' else f'{str(datetime.now().day).zfill(2)}{str(datetime.now().month).zfill(2)}{datetime.now().year}'

        # Como Prazo e Operação são constantes mas podem ter tamanho variável:
        prazo = self.format_constant('1', regras['PRZ'])  # Assumi '1' como padrão, ajuste se for coluna
        comp = self.format_constant(competencia_atual, regras['COMP'])
        operacao = self.format_constant('I', regras['OP']) if self.convenio != 'PREF. CAMPINAS' else self.format_constant('7', regras['OP'])  # 'I' de Inclusão

        # 3. Concatena tudo
        if self.convenio in ['PREF. AÇAILÂNDIA', 'PREF. MACAÉ', 'PREVIPALMAS', 'PREF. BELO HORIZONTE']:
            layout = (matricula + cpf + nome + estab + orgao + cod_desc + valor + prazo + comp + operacao)
        elif self.convenio == 'GOV. RIO DE JANEIRO':
            layout = (matricula + cpf + nome + cod_desc + estab + valor + comp + operacao)
        elif 'PIRACICABA' in self.convenio :
            layout = (matricula + cpf + estab + orgao + cod_desc + valor + prazo + comp + operacao)
        elif self.convenio == 'GOV. ESPÍRITO SANTO':
            layout = (matricula + cpf + nome + cod_desc + valor + prazo + comp + operacao)
        elif self.convenio == 'PREF. CAMPINAS':
            layout = (matricula + orgao + cod_desc + operacao + prazo + valor + comp)
        elif self.convenio == 'GOV. PARANÁ':
            layout = (matricula + cpf + nome + estab + cod_desc + id_orgao + valor + prazo + comp + operacao)
        else:
            print('Nenhum convênio conhecido foi apresentado para criar o arquivo de lançamento...')
            print(f'Convênio solicitado: {self.convenio}')
            return

        return layout

    def save_layout(self, layout, output_dir):
        # Nome do arquivo agora usa o convênio dinâmico
        print('save_layout processado')
        file_name = f'LANCAMENTO {self.convenio} {self.consignataria} {datetime.now().strftime("%m-%Y")}.txt'
        file_path = f'{output_dir}/{file_name}'
        np.savetxt(file_path, layout.values, fmt='%s')

    def process_layout(self, arquivo, output_dir):
        averbados = arquivo.copy()  # Boa prática trabalhar com cópia

        # Filtragem mais robusta (converte para float antes de comparar)
        # Assim evita erros se '0.00' vier como '0' ou 0 (int)
        averbados['Lançar_Float'] = pd.to_numeric(averbados['Lançar'], errors='coerce').fillna(0)
        averbados = averbados[averbados['Lançar_Float'] > 0]

        if averbados.empty:
            print("Nenhum registro para lançar.")
            return

        layout = self.create_layout(averbados)
        self.save_layout(layout, output_dir)

