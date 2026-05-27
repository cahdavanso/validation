import pandas as pd
from io import StringIO
from python.trata_conciliacao import TRATA_CONCILIACAO
from python.TrataOrbital import TRATA_ORBITAL
from python.ESTEIRAS import load_esteiras
from python.Acha_matriculas_SC import ACHA_MATRICULAS_SC
import openpyxl
import xlrd
import numpy as np
from datetime import datetime
import logging
import re
from typing import List, Optional, Tuple
import math
import os

# ARQUIVOS PARA TESTE
# front_bruto = r"P:\PESSOAL\VALIDAÇÃO DOS LANÇAMENTOS\2026\MAIO\GOV SC\RELATORIOS\FRONT GOV SC 05.2026.csv"
# averbado_capital_bruto = r"P:\PESSOAL\VALIDAÇÃO DOS LANÇAMENTOS\2026\MAIO\GOV SC\RELATORIOS\AVERBADOS CAPITAL GOV SC 05.2026.xls"
# averbado_click_bruto = r"P:\PESSOAL\VALIDAÇÃO DOS LANÇAMENTOS\2026\MAIO\GOV SC\RELATORIOS\AVERBADOS CLICK GOV SC 05.2026.xls"
# convenios = 'GOV. SANTA CATARINA'
# consig = 'CAPITAL CONSIG'
# caminho = r'P:\PESSOAL\VALIDAÇÃO DOS LANÇAMENTOS\2026\MAIO\GOV SC\TRABALHADOS'
# funcao_bruto = r"P:\PESSOAL\VALIDAÇÃO DOS LANÇAMENTOS\2026\MAIO\GOV SC\RELATORIOS\FUNÇÃO GOV SC 05.2026.csv"
# conciliacao_bruto = r"P:\PESSOAL\VALIDAÇÃO DOS LANÇAMENTOS\2026\MAIO\GOV SC\RELATORIOS\Conciliação-Governo de Santa Catarina- 032026.xlsx"
# kobraki_bruto = r"P:\PESSOAL\VALIDAÇÃO DOS LANÇAMENTOS\2026\MAIO\GOV SC\RELATORIOS\RECEBIVEIS KOBRAKI - ABRIL 2026.xlsx"
# orbital_bruto = r"P:\PESSOAL\VALIDAÇÃO DOS LANÇAMENTOS\2026\MAIO\GOV SC\RELATORIOS\Orbital_Ativos cartão orbital - fechamento 04.26.xlsx"
# tacs_bruto = r"P:\PESSOAL\VALIDAÇÃO DOS LANÇAMENTOS\2026\MAIO\GOV SC\RELATORIOS\TACS MAIO 2026 - CONSOLIDADO.xlsx"
# andamento_capital_bruto = r"P:\PESSOAL\VALIDAÇÃO DOS LANÇAMENTOS\2026\MAIO\GOV SC\RELATORIOS\BASE DE CONSIGNAÇOES CAPITAL GOV SC 05.2026.xls"
# andamento_click_bruto = r"P:\PESSOAL\VALIDAÇÃO DOS LANÇAMENTOS\2026\MAIO\GOV SC\RELATORIOS\BASE DE CONSIGNACOES CLICK GOV SC 05.2026.xls"

# def read_and_unify_files(file_list: List, convenio: Optional[str] = None, filename_override: Optional[str] = None) -> Tuple[Optional[pd.DataFrame], list]:
#     if not file_list:
#         return None, []
        
#     lista_df = []
#     erros = []
    
#     for uploaded_file in file_list:
#         try:
#             # 1. Identificar se é uma String (Caminho) ou Objeto de Upload
#             if isinstance(uploaded_file, str):
#                 nome_real = os.path.basename(uploaded_file) # Pega só o fim: "TACS MAIO 2026 - CONSOLIDADO.xlsx"
#             else:
#                 nome_real = getattr(uploaded_file, 'name', filename_override or '')
            
#             nome_real_lower = nome_real.lower()

#             # 2. Se foi passado um override genérico (ex: 'tacs'), mas o arquivo real tem extensão,
#             # nós garantimos que a extensão seja preservada para os testes do endswith.
#             if filename_override and not nome_real_lower.endswith(('.xlsx', '.xls', '.csv', '.txt')):
#                 # Se o arquivo real for string, a extensão já veio nele. Se for objeto, tentamos mapear.
#                 extensao = os.path.splitext(getattr(uploaded_file, 'name', ''))[1]
#                 nome_real_lower = f"{filename_override.lower()}{extensao}"

#             # 3. Fluxos de Leitura Baseados no Nome e Extensão Verdadeiros
#             if "kobraki" in nome_real_lower and nome_real_lower.endswith(('.xlsx', '.xls')):
#                 df = pd.read_excel(uploaded_file, sheet_name='CONSOLIDADO')
                
#             elif "orbital" in nome_real_lower:
#                 df = pd.read_excel(uploaded_file, header=3)
                
#             elif nome_real_lower.endswith(('.xlsx', '.xls')):
#                 try:
#                     # 1. Tentativa padrão como Excel verdadeiro
#                     df = pd.read_excel(uploaded_file) 
#                 except Exception as e:
#                     if "Excel file format cannot be determined" in str(e):
#                         print(f"Caiu no tratamento de HTML disfarçado para: {nome_real_lower}")
#                         try:
#                             df = pd.read_html(uploaded_file)[0]
#                             # 2. Define a linha 0 como o nome das colunas
#                             df.columns = df.iloc[0]

#                             # 3. Remove a linha 0 do corpo dos dados e reseta o índice
#                             df = df[1:].reset_index(drop=True)
#                             print(f"Sucesso ao ler HTML de: {nome_real_lower}")
                           
#                         except Exception as erro_html:
#                             print(f'Falhou no read_html também. Erro original: {erro_html}')
#                             print(f'Indo para o fluxo de segurança (CSV): {nome_real_lower}')
                            
#                             # Se tudo falhar, tenta resetar e ler como CSV
#                             if hasattr(uploaded_file, 'seek'): uploaded_file.seek(0)
#                             try:
#                                 df = pd.read_csv(uploaded_file, encoding="utf-8-sig", sep=";", on_bad_lines="skip", low_memory=False)
#                             except Exception:
#                                 df = pd.read_csv(uploaded_file, encoding="latin1", sep=";", on_bad_lines="skip", low_memory=False)
#                     else:
#                         raise e
#             else:
#                 # Fluxo robusto para arquivos de texto / CSV
#                 try:
#                     df = pd.read_csv(uploaded_file, encoding="utf-8-sig", sep=";", on_bad_lines="skip", low_memory=False)
#                 except Exception:
#                     try:
#                         df = pd.read_csv(uploaded_file, encoding="latin1", sep=";", on_bad_lines="skip", low_memory=False)
#                     except Exception:
#                         df = pd.read_csv(uploaded_file, encoding="latin1", sep=",", on_bad_lines="skip", low_memory=False)
            
#             lista_df.append(df)
            
#         except Exception as e:
#             logging.exception(f"Erro ao ler o arquivo {uploaded_file} {e}")
#             erros.append(f"Erro no arquivo {uploaded_file}: {str(e)}")
    
#     if not lista_df:
#         return None, erros
        
#     return pd.concat(lista_df, ignore_index=True), erros

# # =========================================================================
# # FORMA CORRETA DE CHAMAR AS FUNÇÕES (Sem usar 'List[...]' na execução)
# # =========================================================================

# # Se as variáveis abaixo forem os arquivos em si (ex: vindos de st.file_uploader)
# front_df, _ = read_and_unify_files([front_bruto], filename_override='front')

# averbado_capital_df, _ = read_and_unify_files([averbado_capital_bruto], filename_override='averbados')

# averbado_click_df, _ = read_and_unify_files([averbado_click_bruto], filename_override='averbados')

# funcao_df, _ = read_and_unify_files([funcao_bruto], filename_override='funcao')

# conciliacao_df, _ = read_and_unify_files([conciliacao_bruto])

# kobraki_df, _ = read_and_unify_files([kobraki_bruto], filename_override='kobraki')

# orbital_df, _ = read_and_unify_files([orbital_bruto], filename_override='orbital')

# tacs_df, _ = read_and_unify_files([tacs_bruto], filename_override='tacs')

# andamento_capital_df, _ = read_and_unify_files([andamento_capital_bruto], filename_override='andamento')

# andamento_click_df, _ = read_and_unify_files([andamento_click_bruto], filename_override='andamento')

# print(f'TACS_DF:\n{tacs_df}')

class SIGRH:
    def __init__(self, front, averbado_capital, averbado_click, andamento_capital, andamento_click, convenio, consignataria, caminho, funcao=None, orbital=None, conciliacao=None, kobraki=None, tacs=None):
        self.convenio = convenio
        self.caminho = caminho

        self.consignataria = consignataria
        
        # --- ADAPTAÇÃO: Recebendo DataFrames do server.py ao invés de ler do disco ---

        # 1. Averbados
        self.averbados_capital = averbado_capital if averbado_capital is not None else None
        self.averbados_click = averbado_click if averbado_click is not None else None
        # Mantendo a conversão de tipo original:
        if 'VALOR' in self.averbados_capital.columns and 'VALOR' in self.averbados_click.columns:
            # Parcela de Averbados já serão floats
            if self.averbados_capital['VALOR'].dtype != 'float64':
                self.averbados_capital['VALOR'] = self.averbados_capital['VALOR'].astype(str).str.replace("R$ ", "").str.replace(".", "")
                self.averbados_capital['VALOR'] = self.averbados_capital['VALOR'].str.replace(",", ".")
                self.averbados_capital['VALOR'] = pd.to_numeric(self.averbados_capital['VALOR'], errors="coerce")
                self.averbados_capital['VALOR'] = pd.to_numeric(self.averbados_capital['VALOR'], errors="coerce")
            if self.averbados_click['VALOR'].dtype != 'float64':
                self.averbados_click['VALOR'] = self.averbados_click['VALOR'].astype(str).str.replace("R$ ", "").str.replace(".", "")
                self.averbados_click['VALOR'] = self.averbados_click['VALOR'].str.replace(",", ".")
                self.averbados_click['VALOR'] = pd.to_numeric(self.averbados_click['VALOR'], errors="coerce")
                self.averbados_click['VALOR'] = pd.to_numeric(self.averbados_click['VALOR'], errors="coerce")            
        else:
            # Garante a coluna caso venha vazio, para não quebrar a lógica original
            self.averbados_capital['VALOR'] = 0.0


        self.averbados_capital = self.arruma_matricula_averbacoes(self.averbados_capital)
        self.averbados_click = self.arruma_matricula_averbacoes(self.averbados_click)


        # 2. Front
        self.front = front if front is not None else pd.DataFrame()
        if self.front is not None:
            self.front['Consignataria'] = self.front['Consignataria'].str.replace('CAPITAL CONSIG ', 'CAPITAL CONSIG')
        else:
            print('FRONT NÃO IDENTIFICADO, ENCERRANDO O PROGRAMA!')
            return

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

        self.tacs = tacs if tacs is not None else None

        self.orbital = orbital
        
        # 5. Andamento
        self.andamento_capital = andamento_capital if andamento_capital is not None else None
        self.andamento_click = andamento_click if andamento_click is not None else None

        # --- GATILHO: Inicia a lógica original automaticamente ---
        logging.info("Iniciando lógica original do Consigfacil...")
        # self.front_trabalhado = self.tratamento_front()
        # self.averbados_func()

        self.layout_final()

    
    # =========================================================================
    # DAQUI PARA BAIXO É A LÓGICA ORIGINAL INTACTA (Copy-Paste do seu arquivo)
    # =========================================================================

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
    
    def arruma_matricula_averbacoes(self, averbado):
        # Fazemos uma cópia para evitar o aviso "SettingWithCopyWarning"
        averbado_mat = averbado.copy()
        
        print(f'cabeçalho de averbado_mat: {averbado_mat.columns}')

        matriculas = averbado_mat['MATRICULA']

        averbado_mat.insert(1, 'MATRICULA TRATADA', matriculas)

        # 1. Remove os hífens e garante que tudo é string
        averbado_mat['MATRICULA TRATADA'] = averbado_mat['MATRICULA TRATADA'].astype(str).str.replace("-", "")

        # 2. VETORIZAÇÃO: Fatiamento de string direto na coluna inteira
        # O .str[] do Pandas funciona exatamente como o fatiamento de strings do Python [inicio:fim]
        comeco = averbado_mat['MATRICULA TRATADA'].str[:7]
        meio_vai_pro_fim = averbado_mat['MATRICULA TRATADA'].str[7] # Índice 6 é o 7º caractere
        fim_vai_pro_meio = averbado_mat['MATRICULA TRATADA'].str[8:] # Índice 7 em diante

        # Concatenamos as colunas vetorizadas
        averbado_mat['MATRICULA TRATADA'] = comeco + fim_vai_pro_meio + meio_vai_pro_fim

        print(f"MATRICULAS ARRUMADAS:\n{averbado_mat['MATRICULA TRATADA']}")

        return averbado_mat
    
    def truncar_duas_casas(self, valor):
        if pd.isna(valor) or valor == 0:
            return 0.0
        
        # Força o formato com 4 casas em string para eliminar o lixo binário (.99999)
        # Ex: 184.399999999996 vira "184.4000"
        valor_str = f"{valor:.4f}"
        
        # Pega o número e corta estritamente após a segunda casa decimal
        parte_inteira, parte_decimal = valor_str.split('.')
        valor_truncado = float(f"{parte_inteira}.{parte_decimal[:2]}")
        
        return valor_truncado
    
    def truncar_duas_casas_round(self, valor):
        if pd.isna(valor): 
            return valor
        # Multiplica por 100, joga o resto fora com floor(), e divide por 100 de volta
        return round(valor)


    def tratamento_front_preliminar(self):
        front_consig = self.unifica_front_funcao()
        orbital = self.orbital

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

        # Adiciona só as esteiras que podem ser lançadas
        front_consig_esteiras = front_consig[front_consig['Esteira'].isin(esteiras_permitidas)].copy()

        # Arquivo contendo apenas as esteiras que ficaram de fora
        front_consig_esteiras_erradas = front_consig[~front_consig['Esteira'].isin(esteiras_permitidas)].copy()
        front_consig_esteiras_erradas.to_excel(os.path.join(self.caminho, f"ESTEIRAS ERRADAS {self.convenio} {self.consignataria} {datetime.now().strftime("%m-%Y")}.xlsx"), index=False)


        # --------------------------------------------- ORBITAL --------------------------------------------- #
        # --- ETAPA 0: Limpar as colunas de valor da Front ANTES de misturar com Orbital ---
        # Fazemos isso primeiro para que a coluna toda seja float64
        print(f'Series ou DataFrame? {type(front_consig_esteiras['Prestacao'])}')

        cols = front_consig_esteiras.columns

        # Filtrar apenas os que aparecem mais de uma vez
        '''duplicadas_por_nome = cols[cols.duplicated()].unique()

        if len(duplicadas_por_nome) > 0:
            print(f"⚠️ Colunas com nomes duplicados encontradas em front_consig_esteiras: {list(duplicadas_por_nome)}")
        else:
            print("✅ Não existem nomes de colunas duplicados em front_consig_esteiras.")'''
        
        for col in ['Prestacao', 'Valor a lançar']:
            # Selecionamos a coluna e garantimos que pegamos apenas a primeira caso haja duplicada
            coluna_data = front_consig_esteiras.loc[:, col]
            
            # Se o resultado for um DataFrame (duplicadas), pegamos a primeira coluna dele
            if isinstance(coluna_data, pd.DataFrame):
                coluna_data = coluna_data.iloc[:, 0]

            if not pd.api.types.is_float_dtype(coluna_data):
                # Fazemos o tratamento na Series auxiliar
                coluna_tratada = (
                    coluna_data.astype(str)
                    .str.replace('.', '', regex=False)
                    .str.replace(',', '.', regex=False)
                )
                # Devolvemos para o DataFrame original
                front_consig_esteiras[col] = pd.to_numeric(coluna_tratada, errors='coerce').fillna(0)

        # --- ETAPA 1: Preparar Orbital ---
        if orbital is not None:
            # Garantir que o valor da Orbital é numérico
            if orbital['VALID DESCONTO FINAL'].dtype != "float64":
                orbital['VALID DESCONTO FINAL'] = (
                    orbital['VALID DESCONTO FINAL']
                    .astype(str)
                    .str.replace('.', '', regex=False)
                    .str.replace(',', '.', regex=False)
                )
                orbital['VALID DESCONTO FINAL'] = pd.to_numeric(orbital['VALID DESCONTO FINAL'], errors='coerce').fillna(0)

            # Padronizar nomes de colunas de contrato
            for col_name in orbital.columns:
                if "contrato" in col_name.lower():
                    orbital.rename(columns={col_name: "CONTRATO"}, inplace=True)
            
            # Chaves como string para o DE-PARA
            orbital['CONTRATO'] = orbital['CONTRATO'].astype(str).str.strip()
            front_consig_esteiras['Contrato'] = front_consig_esteiras['Contrato'].astype(str).str.strip()

            # --- ETAPA 2: Mapeamento (O "PROCV") ---
            mapa_orbital = orbital.set_index('CONTRATO')['VALID DESCONTO FINAL']
            filtro_esteira = front_consig_esteiras['Esteira'] == '99 CARTAO UTILIZADO'

            # Buscamos os valores (eles virão como float/número)
            valores_encontrados = front_consig_esteiras.loc[filtro_esteira, 'Contrato'].map(mapa_orbital).fillna(0)

            # --- ETAPA 3: Gravar direto como número ---
            # Como limpamos a Front na ETAPA 0, agora é só atribuir o número direto
            front_consig_esteiras.loc[filtro_esteira, 'Prestacao'] = valores_encontrados
            front_consig_esteiras.loc[filtro_esteira, 'Valor a lançar'] = valores_encontrados

        print("Processamento concluído: Valores da Orbital integrados como numéricos.")

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

        # TIRAR BANCO OUTROS, FUTURO, CIASPREV E HP
        front_consig_validado_termino.loc[(front_consig_validado_termino['Consignataria'].str.contains('OUTROS|FUTURO|CIASPREV|HOJE PREVIDÊNCIA PRIVADA', na=False)), 'OBS'] = 'NÃO LANÇAR - BANCO ERRADO'

        front_consig_validado_termino['Contrato'] = front_consig_validado_termino['Contrato'].astype('int64')

        # Tira o que é emprestimo
        front_consig_validado_termino.loc[front_consig_validado_termino['Tipo Operacao'].str.contains('EMPRESTIMO') & (front_consig_validado_termino['OBS'] == ''), 'OBS'] = 'NÃO LANÇAR - EMPRÉSTIMO'

        # Marca para tirar o que é ADIANTAMENTO SALARIAL de Tipo Operacao
        front_consig_validado_termino.loc[front_consig_validado_termino['Tipo Operacao'].str.contains('ADIANTAMENTO SALARIAL', na=False), 'OBS'] = 'NÃO LANÇAR - ADIANTAMENTO SALARIAL'

        # print(f'O que está escrito na linha com contrato 512377\n{front_consig_validado_termino.loc[front_consig_validado_termino['Contrato'] == 512377, 'Novo Tipo Operacao']}')

        # 3. Quem TEM prazo (não vazio) -> NÃO é cartão (ex: Empréstimo ou Operação Comum)
        # Usamos o ~ dentro do .loc para inverter a máscara
        '''if self.convenio not in ['PREF. CAMPINA GRANDE', 'PREF. RECIFE', 'PREF. PORTO VELHO']:
            front_consig_validado_termino.loc[~mask_vazio_prazo, 'Novo Tipo Operacao'] = "CARTAO BENEFICIO"''' # Ou o nome que desejar


        # Salva com os NÃO LANÇAR
        # Dentro do seu validador (ex: python/Consigfacil.py)
        print(f"DEBUG: Tentando salvar FRONT SEMI TRABALHADO em: {self.caminho}")
        try:
            front_consig_validado_termino.to_excel(os.path.join(self.caminho, f"FRONT SEMI TRABALHADO {self.convenio} {self.consignataria} {datetime.now().strftime("%m-%Y")}.xlsx"), index=False)
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

        front_consig['OBS'] = front_consig['OBS'].fillna('')
        front_consig_trabalhado = front_consig[front_consig['OBS'] == ''].copy()

        # Orbital tratado
        if self.orbital is not None:
            preparando_orbital = TRATA_ORBITAL(self.orbital, front_consig, self.convenio, self.caminho)
            orbital_tratado = preparando_orbital.orbital_tratado()
            orbital_tratado = orbital_tratado[orbital_tratado['VALOR DESCONTO'] != 0]

        # Aí tentaremos concatenar o orbital com o front trabalhado para puxar as matriculas
        # Primeiro vamos separar as colunas do front e renomeá-los
        front_trabalhado_preparacao = front_consig_trabalhado[['Contrato', 'CPF', 'Valor a lançar']].copy()
        front_trabalhado_preparacao.columns = ['Contrato', 'CPF', 'PARCELA BASE']

        # Depois, separar as colunas do orbital_tratado e renomeá-los
        orbital_preparacao = orbital_tratado[['Proposta', 'CPF/CNPJ', 'VALOR DESCONTO']]
        orbital_preparacao.columns = ['Contrato', 'CPF', 'PARCELA BASE']

        # Concatenação
        front_com_orbital = pd.concat([front_trabalhado_preparacao, orbital_preparacao])  
        # Remove os 0's
        front_com_orbital= front_com_orbital[front_com_orbital['PARCELA BASE'] != 0]

        # Preparação de averbação tanto capital quando click
        averbado_preparacao_capital = self.averbados_capital[['MATRICULA TRATADA', 'CPF', 'VALOR']]
        averbado_preparacao_click = self.averbados_click[['MATRICULA TRATADA', 'CPF', 'VALOR']]

        averbado_preparacao_capital.columns = ['matrícula', 'CPF', 'parcela 100']
        averbado_preparacao_click.columns = ['matrícula', 'CPF', 'parcela 100']
        
        averbado_preparacao_capital['parcela 100'] = averbado_preparacao_capital['parcela 100']
        averbado_preparacao_capital['parcela 70'] = averbado_preparacao_capital['parcela 100'] * 0.7 # -> Criar as colunas de 70 e 30%
        averbado_preparacao_capital['parcela 30'] = averbado_preparacao_capital['parcela 100'] * 0.3

        averbado_preparacao_capital['parcela 70'] = averbado_preparacao_capital['parcela 70'].apply(self.truncar_duas_casas)
        averbado_preparacao_capital['parcela 30'] = averbado_preparacao_capital['parcela 30'].apply(self.truncar_duas_casas)

        averbado_preparacao_capital['parcela 100'] = averbado_preparacao_capital['parcela 100']
        averbado_preparacao_click['parcela 70'] = averbado_preparacao_click['parcela 100'] * 0.7 # -> Criar as colunas de 70 e 30%
        print(f'parcela 70 de 342.772.349-68: {averbado_preparacao_click.loc[averbado_preparacao_click['CPF'] == '342.772.349-68', 'parcela 70']}')
        averbado_preparacao_click['parcela 30'] = averbado_preparacao_click['parcela 100'] * 0.3

        averbado_preparacao_click['parcela 70'] = averbado_preparacao_click['parcela 70'].apply(self.truncar_duas_casas)
        print(f'parcela 70 de 342.772.349-68 arredondado para baixo: {averbado_preparacao_click.loc[averbado_preparacao_click['CPF'] == '342.772.349-68', 'parcela 70']}')
        averbado_preparacao_click['parcela 30'] = averbado_preparacao_click['parcela 30'].apply(self.truncar_duas_casas)


        acha_matricula_gov_sc = ACHA_MATRICULAS_SC(front_orbital=front_com_orbital, averbado_capital=averbado_preparacao_capital, averbado_click=averbado_preparacao_click, caminho=self.caminho)
        matriculas_encontradas = acha_matricula_gov_sc.busca_direta()
        print(f'matriculas_encontradas\n{matriculas_encontradas}')
        
        # Vamos transformar em arquivo só pra ver como ele fica tratado por completo?
        front_com_orbital.to_excel(os.path.join(self.caminho, f"FRONT COM ORBITAL {self.convenio}{self.consignataria} {datetime.now().strftime("%m-%Y")}.xlsx"), index=False)

        # 1. Mapeia cada uma na sua própria coluna de rastreio
        front_consig_trabalhado['MATRICULA_CAPITAL_ENC'] = front_consig_trabalhado['Contrato'].map(
            matriculas_encontradas.set_index('Contrato')['MATRÍCULA CAPITAL']
        )

        front_consig_trabalhado['MATRICULA_CLICK_ENC'] = front_consig_trabalhado['Contrato'].map(
            matriculas_encontradas.set_index('Contrato')['MATRÍCULA CLICK']
        )

        # 2. Cria a coluna final priorizando a Capital e usando a Click como segunda opção
        # Substitui strings vazias ou com espaços por NaN real do NumPy

        # Agora puxamos matrículas para orbital
        orbital_tratado['MATRICULA ENCONTRADO CAPITAL'] = orbital_tratado['Proposta'].map(matriculas_encontradas.set_index('Contrato')['MATRÍCULA CAPITAL'])
        orbital_tratado['MATRICULA ENCONTRADO CLICK'] = orbital_tratado['Proposta'].map(matriculas_encontradas.set_index('Contrato')['MATRÍCULA CLICK'])

        orbital_tratado.to_excel(os.path.join(self.caminho, f'ORBITAL TRATADO COM MATRICULAS {self.convenio}{self.consignataria} {datetime.now().strftime("%m-%Y")}.xlsx'), index=False)

        print('DEBUG: Esteiras finais do front trabalhado')
        try:
            front_consig_trabalhado.to_excel(
                os.path.join(self.caminho, f"FRONT TRABALHADO {self.convenio}{self.consignataria} {datetime.now().strftime("%m-%Y")}.xlsx"), index=False)
        except Exception as e:
            print(f"DEBUG: ERRO AO SALVAR FRONT TRABALHADO: {e}")

        return front_consig_trabalhado, orbital_tratado
    
    def validacao_termino_front(self, front):
        front_copy = front.copy()
        teste_conciliacao = TRATA_CONCILIACAO(self.conciliacao, self.kobraki, self.tacs)
        conciliacao_tratado = teste_conciliacao.trata_conciliacao()

        # Certifica que todos os contratos no Credbase trabalhado são do mesmo tipo
        # cred['Codigo_Credbase'] = cred['Codigo_Credbase'].astype(str)

        if front_copy['Contrato'].dtype != 'int64':
            front_copy['Contrato'] = front_copy['Contrato'].astype('int')

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
    
    def trata_averbacao(self):
        # PUXA O ARQUIVO DE AVERBAÇÕES QUE VAMOS TRATAR
        if self.consignataria == 'CAPITAL CONSIG':
            averbacoes = self.averbados_capital
            andamento = self.andamento_capital
            andamento = andamento[andamento['Consignação'].str.contains('0144')]
        elif self.consignataria == 'CLICKBANK':
            averbacoes = self.averbados_click
            andamento = self.andamento_click
            andamento = andamento[andamento['Consignação'].str.contains('0194')]
        else:
            print('Consignatária selecionada desconhecida!')
            return
        
        # ----------------------------------------- FRONT TRABALHADO ----------------------------------------- #
        front_trabalhado, orbital_tratado = self.tratamento_front()
        
        # Separando as colunas que vamos usar
        averbacoes_colunas_corretas = averbacoes[['MATRICULA', 'MATRICULA TRATADA', 'NOME', 'CPF', 'VALOR']]
        if averbacoes_colunas_corretas ['VALOR'].dtype != "float64":
            averbacoes_colunas_corretas ['VALOR'] = averbacoes_colunas_corretas['VALOR'].astype(str).str.replace(".", "").str.replace(",", ".")

        # Criação da coluna de 70%
        averbacoes_colunas_corretas ['VALOR 70'] = averbacoes_colunas_corretas['VALOR'] * 0.7
        
        averbacoes_colunas_corretas ['VALOR 70'] = averbacoes_colunas_corretas['VALOR 70'].apply(self.truncar_duas_casas)
        
        # Criação da coluna de 30%
        averbacoes_colunas_corretas ['VALOR 30'] = averbacoes_colunas_corretas['VALOR'] * 0.3
        averbacoes_colunas_corretas ['VALOR 30'] = averbacoes_colunas_corretas['VALOR 30'].apply(self.truncar_duas_casas)

        # Somase do front por matricula
        # Somase do front por matricula
        if self.consignataria == 'CAPITAL CONSIG':
            front_trabalhado = front_trabalhado[~front_trabalhado['MATRICULA_CAPITAL_ENC'].isna()]
            somase_front = front_trabalhado.groupby('MATRICULA_CAPITAL_ENC')['Valor a lançar'].sum().to_dict()
            
            averbacoes_colunas_corretas['SOMASE FRONT'] = averbacoes_colunas_corretas['MATRICULA TRATADA'].map(somase_front).fillna(0)
            print(f'front_trabalhado TUDO CAPITAL:\n{front_trabalhado}')
            
        elif self.consignataria == 'CLICKBANK':
            front_trabalhado = front_trabalhado[~front_trabalhado['MATRICULA_CLICK_ENC'].isna()]
            somase_front = front_trabalhado.groupby('MATRICULA_CLICK_ENC')['Valor a lançar'].sum().to_dict()
            
            averbacoes_colunas_corretas['SOMASE FRONT'] = averbacoes_colunas_corretas['MATRICULA TRATADA'].map(somase_front).fillna(0)
            print(f'somase_front click:\n{somase_front}')
        else:
            print(f'Consignatarias desconhecidas')
            return # Adicionado para interromper caso não entre em nenhuma

        print(f'front_trabalhado UNICOS:\n{front_trabalhado['Consignataria'].unique()}')
        # REMOVIDO A LINHA DO .map() REPETIDA DAQUI!
        
        print(f'tipo da coluna Matricula tratada da averbação\n{averbacoes_colunas_corretas["MATRICULA TRATADA"].dtype}')
        
        # Ajuste apenas no print para não quebrar quando for Clickbank
        coluna_front = 'MATRICULA_CAPITAL_ENC' if self.consignataria == 'CAPITAL CONSIG' else 'MATRICULA_CLICK_ENC'
        print(f'tipo da coluna Matricula tratada do front trabalhado\n{front_trabalhado[coluna_front].dtype}')
        
        # Garante que as exibições finais fiquem salvas antes do to_excel
        averbacoes_colunas_corretas['SOMASE FRONT'] = averbacoes_colunas_corretas['SOMASE FRONT'].fillna(0)

        # ----------------------------------------- ANDAMENTO TRABALHADO ----------------------------------------- #
        andamento['Valor_Mensal'] = pd.to_numeric(andamento['Valor_Mensal'], errors='coerce')

        print('matricula 0674351-0-01 do andamento:\n', andamento[andamento['Matrícula'] == '0674351-0-01'])

        # vamos fazer o somase do andamento e puxar para as averbações
        somase_andamento = andamento.groupby('Matrícula')['Valor_Mensal'].sum().to_dict()
        averbacoes_colunas_corretas['JÁ LANÇADO'] = averbacoes_colunas_corretas['MATRICULA'].map(somase_andamento)
        averbacoes_colunas_corretas['JÁ LANÇADO'] = averbacoes_colunas_corretas['JÁ LANÇADO'].fillna(0)

        # -------------------------------------------- FALTA LANÇAR 70 -------------------------------------------- #
        averbacoes_colunas_corretas['FALTA LANÇAR 70'] = averbacoes_colunas_corretas['SOMASE FRONT'] - averbacoes_colunas_corretas['JÁ LANÇADO']
        averbacoes_colunas_corretas['FALTA LANÇAR 70'] = averbacoes_colunas_corretas['FALTA LANÇAR 70'].apply(self.truncar_duas_casas)
        averbacoes_colunas_corretas['POSSIVEL70'] = averbacoes_colunas_corretas['VALOR 70'] - averbacoes_colunas_corretas['JÁ LANÇADO']

        averbacoes_colunas_corretas['POSSIVEL30'] = np.where(
        averbacoes_colunas_corretas['POSSIVEL70'] < 0,
        averbacoes_colunas_corretas['VALOR 30'] + averbacoes_colunas_corretas['POSSIVEL70'],
        averbacoes_colunas_corretas['VALOR 30']
        )

        condicoes = [
            averbacoes_colunas_corretas['FALTA LANÇAR 70'] < 0,
            averbacoes_colunas_corretas['POSSIVEL70'] < 0
        ]

        # 2. Definimos as respostas para cada condição na mesma ordem
        resultados = [
            0,  # Se FALTA LANÇAR < 0
            0   # Se POSSIVEL70 < 0
        ]

        # 3. O 'else' calcula o menor valor entre as duas colunas usando np.minimum
        resultado_else = np.minimum(
            averbacoes_colunas_corretas['FALTA LANÇAR 70'], 
            averbacoes_colunas_corretas['POSSIVEL70']
        )

        # 4. Cria a coluna aplicando a lógica de seleção
        averbacoes_colunas_corretas['LANÇAR 70'] = np.select(condicoes, resultados, default=resultado_else)
        averbacoes_colunas_corretas['LANÇAR 70'] = averbacoes_colunas_corretas['LANÇAR 70'].apply(self.truncar_duas_casas)

        averbacoes_colunas_corretas['FALTA LANÇAR'] = averbacoes_colunas_corretas['FALTA LANÇAR 70'] - averbacoes_colunas_corretas['LANÇAR 70']

        # -------------------------------------------- ORBITAL -------------------------------------------- #
        if self.consignataria == 'CAPITAL CONSIG':
            parcelas_orbital = orbital_tratado.groupby('MATRICULA ENCONTRADO CAPITAL')['VALOR DESCONTO'].sum().to_dict()
            averbacoes_colunas_corretas['ORBITAL'] = averbacoes_colunas_corretas['MATRICULA TRATADA'].map(parcelas_orbital)
            averbacoes_colunas_corretas['ORBITAL'] = averbacoes_colunas_corretas['ORBITAL'].fillna(0)
        else:
            parcelas_orbital = orbital_tratado.groupby('MATRICULA ENCONTRADO CAPITAL')['VALOR DESCONTO'].sum().to_dict()
            averbacoes_colunas_corretas['ORBITAL'] = averbacoes_colunas_corretas['MATRICULA TRATADA'].map(parcelas_orbital)
            averbacoes_colunas_corretas['ORBITAL'] = averbacoes_colunas_corretas['ORBITAL'].fillna(0)

        averbacoes_colunas_corretas['ORBITAL'] = averbacoes_colunas_corretas['ORBITAL'].apply(self.truncar_duas_casas)

        averbacoes_colunas_corretas['SOMA'] = averbacoes_colunas_corretas['FALTA LANÇAR'] + averbacoes_colunas_corretas['ORBITAL']

        # --------------------------------------------------LANÇAR 30 -------------------------------------------------#

        condicoes_30 = [averbacoes_colunas_corretas['SOMA'] < 0]
        resultados_30 = [0]

        resultados_30_else = np.minimum(averbacoes_colunas_corretas['SOMA'], averbacoes_colunas_corretas['POSSIVEL30'])

        averbacoes_colunas_corretas['LANÇAR 30'] = np.select(condicoes_30, resultados_30, default=resultados_30_else)
        # averbacoes_colunas_corretas.loc[averbacoes_colunas_corretas['LANÇAR 30'] < 0, 'LANÇAR 30'] = 0


        # -------------------------------------------- PRAZO DO FRONT ------------------------------------------------- #
        if self.consignataria == 'CAPITAL CONSIG':
            # Prazos maiores ficam em cima
            front_trabalhado_prazo = front_trabalhado.sort_values(by='Prazo', ascending=False)
            front_trabalhado_prazo.drop_duplicates(subset=['MATRICULA_CAPITAL_ENC'], keep='first', inplace=True)
            averbacoes_colunas_corretas['PRAZO'] = averbacoes_colunas_corretas['MATRICULA TRATADA'].map(front_trabalhado_prazo.set_index('MATRICULA_CAPITAL_ENC')['Prazo'])
            # averbacoes_colunas_corretas['PRAZO'] = averbacoes_colunas_corretas['PRAZO'].fillna('')
            # 1. Cria o dicionário de busca a partir do orbital_tratado
            # Substitua 'MATRICULA_ORBITAL' pela coluna de chave real do seu orbital_tratado
            busca_prazos_orbital = orbital_tratado.groupby('MATRICULA ENCONTRADO CAPITAL')['PRAZO'].first().to_dict()

            # 2. Cria uma série temporária com o mapeamento completo para todas as linhas
            prazos_mapeados = averbacoes_colunas_corretas['MATRICULA TRATADA'].map(busca_prazos_orbital)

            # 3. Preenche APENAS as lacunas (linhas vazias) da coluna original
            averbacoes_colunas_corretas['PRAZO'] = averbacoes_colunas_corretas['PRAZO'].fillna(prazos_mapeados)

        elif self.consignataria == 'CLICKBANK':
            front_trabalhado_prazo = front_trabalhado.sort_values(by='Prazo', ascending=False)
            front_trabalhado_prazo.drop_duplicates(subset=['MATRICULA_CLICK_ENC'], keep='first', inplace=True)
            averbacoes_colunas_corretas['PRAZO'] = averbacoes_colunas_corretas['MATRICULA TRATADA'].map(front_trabalhado_prazo.set_index('MATRICULA_CLICK_ENC')['Prazo'])
            # averbacoes_colunas_corretas['PRAZO'] = averbacoes_colunas_corretas['PRAZO'].fillna('')
            # 1. Cria o dicionário de busca a partir do orbital_tratado
            # Substitua 'MATRICULA_ORBITAL' pela coluna de chave real do seu orbital_tratado
            busca_prazos_orbital = orbital_tratado.groupby('MATRICULA ENCONTRADO CLICK')['PRAZO'].first().to_dict()

            # 2. Cria uma série temporária com o mapeamento completo para todas as linhas
            prazos_mapeados = averbacoes_colunas_corretas['MATRICULA TRATADA'].map(busca_prazos_orbital)

            # 3. Preenche APENAS as lacunas (linhas vazias) da coluna original
            averbacoes_colunas_corretas['PRAZO'] = averbacoes_colunas_corretas['PRAZO'].fillna(prazos_mapeados)
        else:
            print('trata_averbacao - CONSIGNATARIA SELECIONADA ERRADA!')
        
        averbacoes_colunas_corretas.to_excel(os.path.join(self.caminho, f"AVERBAÇÕES TRABALHADAS DE GOV. SANTA CATARINA {datetime.now().strftime("%m-%Y")}.xlsx"), index=False)
        return averbacoes_colunas_corretas

    def layout_final(self):
        averbacoes= self.trata_averbacao()

        nome_layout_dict = {'CAPITAL CONSIG': 'CAPITAL',
                            'CLICKBANK': 'CLICK',}
        
        consignataria_layout = nome_layout_dict[self.consignataria]

        def processar_layout(layout_para_txt, consig, produto, tipo='LANCAMENTO'):
            layout_tratamento = layout_para_txt
            mes = str(datetime.now().month).zfill(2)
            ano = datetime.now().year
            try:   
                linhas_formatadas = []

                for _, row in layout_tratamento.iterrows():
                    # CPF: Remove pontos/traços e preenche com zeros à esquerda (11 dígitos)
                    cpf_limpo = re.sub(r'\D', '', str(row['CPF']))
                    cpf = cpf_limpo.zfill(11)

                    # MATRICULA: Já lida como string, preenche com zeros à esquerda (15 dígitos)
                    matricula = str(row['MATRICULA']).zfill(15)

                    # PRAZO (Nº Parcelas): Preenche com zeros à esquerda (3 dígitos)
                    # Caso realmente não queira usar o prazo da planilha, troque por "000"
                    prazo = str(row['PRAZO']).zfill(3)

                    # VALOR: Remove vírgula/ponto e preenche com zeros à esquerda (16 dígitos)
                    # Multiplicamos por 100 para remover a vírgula mantendo os centavos
                    valor_num = float(row['VALOR'])
                    valor_formatado = str(int(round(valor_num * 100))).zfill(16)

                    # CONTRATO: Preenche com zeros à esquerda (20 dígitos) conforme exemplo
                    contrato = "0".zfill(20)

                    # Montagem da linha seguindo as posições da imagem
                    # Pos: 1(MM), 3(AAAA), 7(CPF), 18(Esp), 22(Matr), 37(Esp), 41(Parc), 44(Val), 60(Op), 61(Tipo), 63(Cont), 83(Esp), 133(ZZZ)
                    linha = (
                        f"{mes}"                # 1-2   (2)
                        f"{ano}"                # 3-6   (4)
                        f"{cpf}"                # 7-17  (11)
                        f"{' ' * 4}"            # 18-21 (4)
                        f"{matricula}"          # 22-36 (15)
                        f"{' ' * 4}"            # 37-40 (4)
                        f"{prazo}"              # 41-43 (3)
                        f"{valor_formatado}"    # 44-59 (16)
                        f"I"                    # 60    (1) - Operação: Inclusão
                        f"VL"                   # 61-62 (2) - Tipo: Valor Fixo
                        f"{contrato}"           # 63-82 (20)
                        f"{' ' * 50}"           # 83-132(50)
                        f"ZZZ"                  # 133-135(3)
                    )
                    linhas_formatadas.append(linha)

                # 4. Salvar arquivo TXT
                # Usamos o os.path.join para juntar as pastas de forma segura, sem se preocupar com barras individuais ou duplas
                nome_arquivo = f"{tipo} {consig} {produto} GOV SC {datetime.now().strftime('%m-%Y')}.txt"
                nome_txt = os.path.join(self.caminho, nome_arquivo)

                with open(nome_txt, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(linhas_formatadas))

                print(f"\nSucesso! Arquivo gerado: {os.path.basename(nome_txt)}")

            except Exception as e:
                print(f"Ocorreu um erro ao processar: {e}")

        # --- Função auxiliar para evitar a repetição de código ---
        def gerar_e_salvar_layout(df_filtrado, coluna_valor, tipo_layout, produto_layout):
            if df_filtrado.empty:
                return
            
            # 1. Seleciona e padroniza as colunas (Garante que a coluna de valor vire sempre 'VALOR_FORMATADO')
            colunas_finais = ['CPF', 'MATRICULA TRATADA', 'PRAZO', coluna_valor]
            layout = df_filtrado[colunas_finais].copy()
            
            # 2. Trata o teto do Prazo
            if produto_layout == 'SAQUE':
                layout['PRAZO'] = layout['PRAZO'].astype('int64')
                layout.loc[layout['PRAZO'] > 80, 'PRAZO'] = 80
            else:
                layout['PRAZO'] = 1
            
            # 3. Formata o valor com duas casas e troca ponto por vírgula (Padrão Excel/TXT)
            layout[coluna_valor] = layout[coluna_valor].map('{:.2f}'.format) # .str.replace(".", ",", regex=False)
            
            # 4. Processa o arquivo TXT (Envia o tipo apenas se for COMPLEMENTO)
            kwargs = {'tipo': tipo_layout} if tipo_layout else {}
            layout.rename(columns={coluna_valor: "VALOR", 'MATRICULA TRATADA': "MATRICULA"}, inplace=True)
            processar_layout(layout_para_txt=layout, consig=consignataria_layout, produto=produto_layout, **kwargs)
            
            # 5. Salva o Excel de conferência
            sufixo_tipo = f"{tipo_layout} " if tipo_layout else ""
            nome_excel = f"TESTE LAYOUT {sufixo_tipo}{produto_layout} {self.convenio} {self.consignataria} {datetime.now().strftime('%m-%Y')}.xlsx"
            layout.to_excel(os.path.join(self.caminho, nome_excel), index=False)

        # 1. COMPLEMENTO SAQUE
        filtro_comp_saque = averbacoes.loc[(averbacoes['LANÇAR 70'] >= 8.9) & (averbacoes['JÁ LANÇADO'] > 0)]
        gerar_e_salvar_layout(filtro_comp_saque, 'LANÇAR 70', tipo_layout='COMPLEMENTO', produto_layout='SAQUE')

        # 2. LANÇAMENTO SAQUE
        filtro_lanc_saque = averbacoes.loc[(averbacoes['LANÇAR 70'] >= 8.9) & (averbacoes['JÁ LANÇADO'] == 0)]
        gerar_e_salvar_layout(filtro_lanc_saque, 'LANÇAR 70', tipo_layout='LANCAMENTO', produto_layout='SAQUE')

        # 3. LANÇAMENTO COMPRA
        filtro_lanc_compra = averbacoes.loc[averbacoes['LANÇAR 30'] >= 8.9]
        gerar_e_salvar_layout(filtro_lanc_compra, 'LANÇAR 30', tipo_layout='LANCAMENTO', produto_layout='COMPRA')

                
# sigrh_obj = SIGRH(averbado_capital=averbado_capital_df, averbado_click=averbado_click_df, front=front_df, convenio='GOV. SANTA CATARINA', 
#                   consignataria='CAPITAL CONSIG', caminho=caminho, funcao=funcao_df, conciliacao=conciliacao_df, kobraki=kobraki_df, tacs=tacs_df, 
#                   orbital=orbital_df, andamento_capital=andamento_capital_df, andamento_click=andamento_capital_df)

# validacao = sigrh_obj.layout_final()


