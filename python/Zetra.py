from idlelib.autocomplete import TRY_A

import pandas as pd
import rarfile
import zipfile
import numpy as np
import re
from thefuzz import fuzz
from datetime import datetime
import os
from io import StringIO
import openpyxl


class ZETRA:
    def __init__(self, portal_file_path, convenio, credbase, consignataria, caminho, historico=None, funcao=None, conciliacao=None, tutela=None, liquidados=None, orbital=None):

        self.caminho = caminho

        self.convenio = convenio

        self.consignataria = consignataria

        self.averbados = self.processar_arquivos_rar(portal_file_path)

        if isinstance(credbase, str):  # Caso seja apenas um arquivo
            self.creds_unificados = pd.read_csv(credbase, encoding="ISO-8859-1", sep=";", on_bad_lines="skip")
        elif isinstance(credbase, list):  # Caso seja lista de arquivos
            lista_df = []
            for cred in credbase:
                try:
                    df = pd.read_csv(
                        cred,
                        encoding="utf-8-sig",  # tenta UTF-8 com BOM
                        sep=";",
                        on_bad_lines="skip",
                        low_memory=False
                    )
                except UnicodeDecodeError:
                    df = pd.read_csv(
                        cred,
                        encoding="ISO-8859-1",  # se falhar, tenta latin1
                        sep=";",
                        on_bad_lines="skip",
                        low_memory=False
                    )
                lista_df.append(df)
            self.creds_unificados = pd.concat(lista_df, ignore_index=True)

        try:
            self.funcao_bruto = pd.read_csv(funcao, encoding='utf-8', sep=';', on_bad_lines='skip') if funcao else None
        except UnicodeDecodeError:
            self.funcao_bruto = pd.read_csv(funcao, encoding='ISO-8859-1', sep=';', on_bad_lines='skip') if funcao else None

        conciliacao_falso = pd.DataFrame(
            columns=['CONTRATOS', 'CPF', 'PRESTAÇÃO', 'PRAZO', 'D8 JUN 25', 'ST JUL 25', 'RECEBIDO GERAL'])
        conciliacao_falso['CONTRATOS'] = 123
        conciliacao_falso['CPF'] = '123.456'
        conciliacao_falso['PRESTAÇÃO'] = 10
        conciliacao_falso['PRAZO'] = 96
        conciliacao_falso['D8 JUN 25'] = 10
        conciliacao_falso['ST JUL 25'] = 'DESCONTO TOTAL'
        conciliacao_falso['RECEBIDO GERAL'] = 0

        self.historico = pd.read_excel(historico) if historico else None

        self.conciliacao = pd.read_excel(conciliacao) if conciliacao else conciliacao_falso

        self.liquidados_file = pd.read_excel(liquidados) if liquidados else None

        if not self.liquidados_file is None:
            if len(self.liquidados_file) == 0:
                self.liquidados_file = None
            else:
                self.liquidados_file = self.liquidados_file

        if self.liquidados_file is not None:
            # Certificando que o tipo dos contratos do Operações Liquidadas
            self.liquidados_file['Nº OPERAÇÃO'] = self.liquidados_file['Nº OPERAÇÃO'].astype(str)

        self.tutela = pd.read_excel(tutela, sheet_name='DEMAIS CONVÊNIOS') if tutela else None

        self.orbital = pd.read_excel(orbital) if orbital else None

        self.condicoes_1 = ['11 FORMALIZAÇÃO ', '07.0 QUITAÇÃO - LIBERAÇÃO TROCO', '07.4 ENVIA CESSÃO FUNDO',
                            '11.2  DETERMINAÇÃO JUDICIAL', '11.2 ACORDO CLIENTE',
                            '10.7.0 INGRESSAR COM PROCESSO OU AÇÃO JURIDICO',
                            '10.7.1 ACORDO EM ANDAMENTO', '02.03 AGUARDANDO PROCESSAMENTO CARTÃO',
                            '02.3 AGUARDANDO PROCESSAMENTO DE CARTÃO',
                            '07.0 QUITACAO – ENVIO DE CESSAO', '07.1 – QUITACAO – PAGAMENTO AO CLIENTE',
                            '07.1.1 QUITACAO - CORRECAO DE CCB', '07.2 TED DEVOLVIDA – PAGAMENTO AO CLIENTE',
                            '10.3.1 CONTRATO AVERBADO AGUARDANDO LIQUIDAÇÃO REFIN',
                            '08.0 LIBERAÇÃO TROCO', '09.0 PAGO', '09.1 - APOSENTADORIA IGEPREV - AVERB. TOTAL',
                            '09.2 - APOSENTADORIA IGEPREV - AVERB. PARCIAL',
                            '07.1 \x96 QUITACAO \x96 PAGAMENTO AO CLIENTE',
                            '10.3.1 CONTRATO AVERBADO AGUARDANDO LIQUIDAÇÃO REFIN',
                            '07.2 TED DEVOLVIDA \x96 PAGAMENTO AO CLIENTE',
                            '10.5 AGUARDANDO AVERBACAO COMPRA OUTROS CONVENIOS', '07.0 QUITACAO \x96 ENVIO DE CESSAO',
                            '10.6 CONTRATO AVERBADO - AGUARDANDO COMPROVANTE DE RESERVA',
                            '02.03 AGUARDANDO PROCESSAMENTO CARTÃO', 'INTEGRADO', 'RISCO DA OPERAÇÃO - ÓBITO',
                            'RISCO DA OPERAÇÂO-DEMAIS SITUAÇÕES',
                            '10.7 CONTRATO NÃO AVERBADO - AGUARDANDO RESOLUÇÃO',
                            '11.1 CONTRATO FÍSICO ENVIADO AO BANCO ',
                            '11.PROBLEMAS DE AVERBAÇÃO', '15.0\tRISCO DA OPERAÇÂO-DEMAIS SITUAÇÕES',
                            '15.0	RISCO DA OPERAÇÂO-DEMAIS SITUAÇÕES', '14.0 RISCO DA OPERAÇÃO - ÓBITO',
                            '07.4 ENVIA CESSAO FUNDO', '08.0 LIBERACAO TROCO', '07.1 AGUARDANDO AVERBACAO',
                            '11.PROBLEMAS DE AVERBACAO', '07.2 AGUARDANDO DESAVERBACAO IF',
                            '07.5 AGUARDANDO DESAVERBACAO BENEFICIO', '10.7.0 INGRESSAR COM PROCESSO OU AÇÃO JURIDICO',
                            '10.3 AGUARDANDO AVERBACAO COMPRA EMPRESTIMO SIAPE']

        # --- TABELA DE CONFIGURAÇÃO (Baseada na sua imagem) ---
        # 0 significa que o campo não existe ou deve ser ignorado
        self.LAYOUT_CONFIG = {
            "PREF ACAILANDIA": {"MAT": 12, "CPF": 11, "NOME": 50, "EST": 3, "ORG": 3, "COD": 3, "VAL": 10, "PRZ": 3,
                                "COMP": 6, "OP": 1},
            "PREF BELO HORIZONTE": {"MAT": 10, "CPF": 11, "NOME": 50, "EST": 3, "ORG": 3, "COD": 4, "VAL": 10, "PRZ": 3,
                                    "COMP": 6, "OP": 1},
            "PREF MACAE": {"MAT": 10, "CPF": 11, "NOME": 50, "EST": 3, "ORG": 3, "COD": 4, "VAL": 10, "PRZ": 3,
                           "COMP": 6, "OP": 1},
            "PREF PIRACICABA": {"MAT": 10, "CPF": 11, "NOME": 0, "EST": 3, "ORG": 3, "COD": 4, "VAL": 10, "PRZ": 3,
                                "COMP": 6, "OP": 1},
            "PREVIPALMAS": {"MAT": 10, "CPF": 11, "NOME": 50, "EST": 3, "ORG": 4, "COD": 5, "VAL": 10, "PRZ": 3,
                            "COMP": 6, "OP": 1},
            "IGEPREV": {"MAT": 20, "CPF": 11, "NOME": 50, "EST": 3, "ORG": 3, "COD": 5, "VAL": 10, "PRZ": 3, "COMP": 6,
                        "OP": 1},
            "GOV RJ": {"MAT": 13, "CPF": 11, "NOME": 50, "EST": 2, "ORG": 0, "COD": 25, "VAL": 10, "PRZ": 0, "COMP": 6,
                       "OP": 1},
            "GOV ES": {"MAT": 12, "CPF": 11, "NOME": 50, "EST": 0, "ORG": 0, "COD": 24, "VAL": 10, "PRZ": 3, "COMP": 6,
                       "OP": 1},
        }

        self.arquivo_lancamento()

    def processar_arquivos_rar(self, diretorio_alvo):
        """
        Lê arquivos .rar, extrai CSVs específicos, remove as 3 últimas linhas,
        concatena e trata as colunas de data.
        """
        lista_dfs = []
        print(f'diretorio_alvo: {diretorio_alvo}\n')
        # Verifica se o diretório existe
        if not os.path.exists(diretorio_alvo):
            print(f"Erro: O diretório '{diretorio_alvo}' não foi encontrado.")
            return None

        # Percorre todos os arquivos da pasta
        for nome_arquivo in os.listdir(diretorio_alvo):
            if nome_arquivo.lower().endswith('.zip'):
                caminho_completo = os.path.join(diretorio_alvo, nome_arquivo)
                print(f"Lendo arquivo: {nome_arquivo}")

                try:
                    # Abre o arquivo RAR
                    with zipfile.ZipFile(caminho_completo) as zf:
                        # Percorre os arquivos dentro do RAR
                        for arquivo_interno in zf.namelist():
                            nome_upper = arquivo_interno.upper()

                            # Verifica critérios: ser CSV e ter as palavras chaves
                            # Assumi que é para pegar arquivos que tenham OU Alteração OU Inclusão
                            if arquivo_interno.lower().endswith('.csv') and \
                                    ("ALTERACAO" in nome_upper or "INCLUSAO" in nome_upper):

                                print(f"  -> Processando CSV interno: {arquivo_interno}")

                                # Lê o conteúdo do arquivo diretamente da memória
                                with zf.open(arquivo_interno) as f:
                                    # Dica: CSVs brasileiros geralmente usam encoding 'latin1' ou 'ansi' e separador ';'
                                    # Se der erro de leitura, tente encoding='utf-8'
                                    df_temp = pd.read_csv(f, sep=';', encoding='latin1')

                                    # --- REMOVE AS 3 ÚLTIMAS LINHAS ---
                                    if len(df_temp) > 3:
                                        df_temp = df_temp.iloc[:-3]
                                    else:
                                        print(
                                            f"     Aviso: Arquivo {arquivo_interno} tem menos de 3 linhas. Ignorado.")
                                        continue

                                    lista_dfs.append(df_temp)

                except zipfile.BadZipfile:
                    print("ERRO CRÍTICO: UnRAR não encontrado. Verifique a configuração do rarfile.UNRAR_TOOL.")
                    return None
                except Exception as e:
                    print(f"Erro ao processar {nome_arquivo}: {e}")

        # Se não encontrou nada, retorna vazio
        if not lista_dfs:
            print("Nenhum arquivo correspondente foi encontrado ou processado.")
            return pd.DataFrame()

        # --- CONCATENAÇÃO ---
        print("Concatenando DataFrames...")
        df_final = pd.concat(lista_dfs, ignore_index=True)

        nome_averbado = f"RELATORIO CARTAO {self.convenio} {self.consignataria} {datetime.now().strftime("%m-%Y")}"
        df_final.to_excel(fr'{self.caminho}\{nome_averbado}.xlsx', index=False)

        return df_final

    def unifica_historico_averb(self):
        averbados_atual = self.averbados
        colunas = averbados_atual.columns

        hist_df = self.historico if self.historico is not None else pd.DataFrame(columns=[colunas])

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

            # Remove duplicatas por ID.ADE
            averbacao_completa.drop_duplicates(subset=['Id. ADE'], keep='first', inplace=True)
        else:
            print("Aviso: Coluna 'Data ocor.' não encontrada no DataFrame final.")

        nome_averbacao_completa = f"HISTÓRICO DE AVERBAÇÕES {self.convenio} {self.consignataria} {datetime.now().strftime("%m-%Y")}"

        averbacao_completa.to_excel(fr'{self.caminho}\{nome_averbacao_completa}.xlsx', index=False)

        return averbacao_completa

    def unificacao_creds(self):

        # RENOMEIA A COLUNA CODIGO_CREDBASE
        if 'Codigo Credbase' in self.creds_unificados.columns or 'ï»¿Codigo_Credbase' in self.creds_unificados.columns:
            cred = self.creds_unificados.rename(columns={'Codigo Credbase': 'Codigo_Credbase', 'ï»¿Codigo_Credbase': 'Codigo_Credbase'})
            self.creds_unificados = cred

        credbase_reduzido = self.creds_unificados[['Codigo_Credbase', 'Banco(s) quitado(s)', 'Filial', 'Esteira',
                                                 'Esteira(dias)', 'Tipo', 'Operacao', 'Situacao', 'Inicio', 'Cliente',
                                                 'Data Averbacao', 'CPF', 'Convenio', 'Banco', 'Parcela', 'Prazo',
                                                 'Tabela', 'Matricula']]

        # Vamos alterar o tipo do Codigo_Credbase já que agora a coluna está com o nome certo
        credbase_reduzido['Codigo_Credbase'] = credbase_reduzido['Codigo_Credbase'].astype(str)


        credbase_reduzido['Parcela'] = credbase_reduzido['Parcela'].str.replace('.', '')
        credbase_reduzido['Parcela'] = credbase_reduzido['Parcela'].str.replace(',', '.')
        credbase_reduzido['Parcela'] = pd.to_numeric(credbase_reduzido['Parcela'], errors='coerce')

        credbase_reduzido = credbase_reduzido.sort_values(by='Data Averbacao', ascending=True)

        credbase_reduzido.to_excel(fr'{self.caminho}\CREDBASE UNIFICADO.xlsx', index=False)

        # print(self.creds_unificados)

        return credbase_reduzido

    def tratamento_funcao(self):
        funcao = self.funcao_bruto
        colunas_excluir = ['NR_OPER_EDITADO', 'CONTSE SEMI TRABALHADO', 'CONTSE LOCAL', 'Diff', 'OP_LIQ', 'CONTRATO CONCILIACAO', 'OBS', 'has_conciliacao']
        funcao.drop(columns=colunas_excluir, errors='ignore', inplace=True)

        if funcao is None:
            '''cred = self.unificacao_creds()
            credbase_reduzido = cred[
                ['Codigo_Credbase', 'Banco(s) quitado(s)', 'Filial', 'Esteira', 'Esteira(dias)', 'Tipo',
                 'Operacao', 'Situacao', 'Inicio', 'Cliente', 'Data Averbacao', 'CPF', 'Convenio', 'Banco',
                 'Parcela', 'Prazo', 'Tabela', 'Matricula']]

            credbase_reduzido.to_excel(rf'{self.caminho}\Teste Credbase Reduzido.xlsx', index=False)

            self.validacao_termino(credbase_reduzido)'''

            return None

        # print(cred_unificado['Esteira'].unique())

        if 'ï»¿NR_OPER' in funcao.columns:
            funcao = funcao.rename(columns={'ï»¿NR_OPER': 'NR_OPER'})

        # Alterar o tipo do número de contrato do Função para String e da parcela para float
        funcao['NR_OPER'] = funcao['NR_OPER'].astype(str)
        # funcao['VLR_PARC'] = pd.to_numeric(funcao['VLR_PARC'], errors="coerce")

        codigo_editado = funcao['NR_OPER'].replace(r"\D", "", regex=True)
        if 'NR_OPER_EDITADO' in funcao.columns:
            funcao = funcao.drop(columns=['NR_OPER_EDITADO'])
        funcao.insert(1, 'NR_OPER_EDITADO', codigo_editado, True)
        funcao['NR_OPER_EDITADO'] = funcao['NR_OPER_EDITADO'].astype(str).str.slice(0, 9)

        funcao['NR_OPER_EDITADO'] = funcao['NR_OPER_EDITADO'].astype(str)

        # <-- CORREÇÃO: A linha "funcao.insert(3, 'CONCAT', '', True)" foi REMOVIDA daqui.

        # Insere as outras colunas vazias
        funcao.insert(4, 'CONTSE SEMI TRABALHADO', '', True)
        if 'CONTSE LOCAL' not in funcao.columns:
            funcao.insert(5, 'CONTSE LOCAL', '', True)
        funcao.insert(6, 'Diff', '', True)
        funcao.insert(7, 'OP_LIQ', '', True)
        funcao.insert(8, 'CONTRATO CONCILIACAO', '', True)
        if 'OBS' not in funcao.columns:
            funcao.insert(10, 'OBS', '', True)

        # Concat de CPF + PARCELA
        try:
            funcao['VLR_PARC'] = funcao['VLR_PARC'].str.replace('.', '', regex=False)
            funcao['VLR_PARC'] = funcao['VLR_PARC'].str.replace(',', '.', regex=False)
        except Exception as e:
            pass
        funcao['VLR_PARC'] = pd.to_numeric(funcao['VLR_PARC'], errors='coerce').fillna(0)

        # Esta linha agora é a ÚNICA que cria a coluna 'CONCAT', o que é o correto.
        funcao['CONCAT'] = funcao['CPF'].astype(str) + funcao['VLR_PARC'].astype(str)

        cred_unificado = self.unificacao_creds()

        # Garante que a coluna 'Esteira' exista antes de filtrar
        if 'Esteira' in cred_unificado.columns:
            cred_semi = cred_unificado[cred_unificado['Esteira'].isin(self.condicoes_1)].copy()

            # Cria a coluna CONCAT CPF PARC apenas se cred_semi não for vazio
            if not cred_semi.empty:
                concat_CPF_parc = cred_semi['CPF'].astype(str) + cred_semi['Parcela'].astype(str)
                cred_semi.insert(12, 'CONCAT CPF PARC', concat_CPF_parc, True)

                # Contse Semi Trabalhado
                contse_concat_semi_cred = cred_semi.groupby('CONCAT CPF PARC')['CONCAT CPF PARC'].count().to_dict()

                # <-- CORREÇÃO 2: Garantido que o .map é chamado na coluna ['CONCAT'] e não no DataFrame 'funcao'
                funcao['CONTSE SEMI TRABALHADO'] = funcao['CONCAT'].map(contse_concat_semi_cred)
                funcao['CONTSE SEMI TRABALHADO'] = funcao['CONTSE SEMI TRABALHADO'].fillna(0)
        # print(funcao['CONTSE SEMI TRABALHADO'])

        # Contse Local
        funcao['CONTSE LOCAL'] = funcao.groupby('CONCAT')['CONCAT'].transform('count')

        # OP LIQUIDADO
        try:
            op_liq = self.liquidados_file
            n_operacao_liq = op_liq
            n_operacao_liq['Número Operação'] = op_liq['Nº OPERAÇÃO']
            funcao['OP_LIQ'] = funcao['NR_OPER'].map(n_operacao_liq.set_index('Nº OPERAÇÃO')['Número Operação'].to_dict())

        except Exception as e :
            op_liq = pd.DataFrame(columns=['Nº OPERAÇÃO'])
            print(f"Planilha de Operações Liquidadas está vazia {e}")


        funcao['OP_LIQ'] = funcao['OP_LIQ'].fillna('')


        funcao.loc[(funcao['OBS'] == '') & (funcao['OP_LIQ'] != ''), 'OBS'] = 'NÃO'

        for idx, row in funcao.iterrows():
            if funcao.loc[idx, 'CONTSE LOCAL'] > funcao.loc[idx, 'CONTSE SEMI TRABALHADO']:
                funcao.loc[idx, 'Diff'] = 'VERDADEIRO'
            else:
                funcao.loc[idx, 'Diff'] = 'FALSO'

        # Condição 1: Coluna 'Diff' contém 'FALSO'
        mask_diff = funcao['Diff'].str.contains('FALSO', na=False)

        # Condição 2: Coluna 'PRODUTO' contém 'EMPRESTIMO'
        mask_produto = funcao['PRODUTO'].str.contains('EMPRESTIMO', na=False)

        # A máscara final é Verdadeira se QUALQUER uma das condições for Verdadeira
        mask_final = mask_diff | mask_produto

        # Agora, aplique o 'NÃO' nos locais corretos usando a máscara
        funcao.loc[mask_final, 'OBS'] = 'NÃO'

        # print(funcao['OBS'][funcao['OBS'] == "NÃO"])

        # CONCILIAÇÃO
        conciliacao_tratado = self.conciliacao

        conciliacao_tratado.rename(columns={conciliacao_tratado.columns[0]: 'CONTRATOS'}, inplace=True)

        # Converte para lista de colunas
        cols = list(conciliacao_tratado.columns)

        # Encontra o índice da primeira ocorrência de "CONTRATO" e altera
        for i, c in enumerate(cols):
            if c == "CONTRATO" and c != "CONTRATOS":
                cols[i] = "CONTRATOS"  # só a primeira vez
                break
            else:
                break

        # Atualiza o DataFrame com novos nomes
        conciliacao_tratado.columns = cols
        conciliacao_tratado['CONTRATOS'] = conciliacao_tratado['CONTRATOS'].astype('Int64').astype(str)

        contratos_conciliacao = pd.DataFrame()

        '''Precisei fazer um Dataframe separado porque por algum motivo ele não conseguia usar os contratos como índice,
           e puxar os mesmos contratos... Eu poderia criar uma coluna de contratos dentro da propria conciliacao mas resolvi
           criar um DataFrame novo só com essas colunas já que é tudo que vamos precisar delas'''

        contratos_conciliacao['CONTRATO'] = conciliacao_tratado['CONTRATOS']
        contratos_conciliacao['CONTRATO PUXAR'] = conciliacao_tratado['CONTRATOS']
        funcao['CONTRATO CONCILIACAO'] = funcao['NR_OPER_EDITADO'].map(contratos_conciliacao.set_index('CONTRATO')['CONTRATO PUXAR'].to_dict())
        # Precisei transformar os códigos da coluna "CONTRATO CONCILIACAO" em número, mas para isso precisei transformar os vazios em 0
        # funcao['CONTRATO CONCILIACAO'] = pd.to_numeric(funcao['CONTRATO CONCILIACAO'], errors='coerce').fillna(0).astype(int)

        # Agora preciso transformar os zeros em NaN
        funcao.loc[funcao['CONTRATO CONCILIACAO'] == 0, 'CONTRATO CONCILIACAO'] = np.nan

        # E de NaN para vazio mesmo... Quem sabe assim ele reconhece o número de contrato. PS: Não era esse o problema
        funcao['CONTRATO CONCILIACAO'] = funcao['CONTRATO CONCILIACAO'].fillna('')

        # Criar coluna auxiliar (1 = preenchido, 0 = vazio)
        funcao['has_conciliacao'] = funcao['CONTRATO CONCILIACAO'].notna() & (funcao['CONTRATO CONCILIACAO'] != '')

        # Ordenar colocando os contratos da conciliação preenchidos primeiro
        funcao = funcao.sort_values(by="has_conciliacao", ascending=False).drop(columns="has_conciliacao")
        funcao = funcao.sort_values(by='CPF', ascending=True)

        # Verifica se CONTSE LOCAL é igual á CONTSE SEMI CRED e se existe na concilicação
        for idx, row in funcao.iterrows():
            if (
                    row['CONTSE LOCAL'] == row['CONTSE SEMI TRABALHADO']
                    and row['CONTRATO CONCILIACAO'] != ''
                    and "EMPRESTIMO" not in str(row['PRODUTO'])
            ):
                funcao.loc[idx, 'OBS'] = ''

        # FUNÇÃO INTERMEDIARIO
        funcao.to_excel(fr'{self.caminho}\FUNÇÃO INTERMEDIÁRIO.xlsx', index=False)

        funcao_tratado = funcao[funcao['OBS'] == '']

        return funcao_tratado

    def unificacao_cred_funcao(self):
        creds_unificados = self.unificacao_creds()
        credbase_reduzido = creds_unificados[['Codigo_Credbase', 'Banco(s) quitado(s)', 'Filial', 'Esteira',
                                                 'Esteira(dias)', 'Tipo', 'Operacao', 'Situacao', 'Inicio', 'Cliente',
                                                 'Data Averbacao', 'CPF', 'Convenio', 'Banco', 'Parcela', 'Prazo',
                                                 'Tabela', 'Matricula']]
        cred = credbase_reduzido.copy()
        cred['Codigo_Credbase'] = cred['Codigo_Credbase'].astype(str)

        '''cred['Parcela'] = cred['Parcela'].str.replace('.', '')
        cred['Parcela'] = cred['Parcela'].str.replace(',', '.')'''
        cred['Parcela'] = pd.to_numeric(cred['Parcela'], errors='coerce')
        funcao = self.tratamento_funcao()

        # Transforma a coluna de NR_OPER_EDITADO EM NúMERO
        # funcao['NR_OPER_EDITADO'] = funcao['NR_OPER_EDITADO'].astype(int)


        # Cria a coluna Esteira no Função
        if not funcao is None:
            funcao.insert(5, 'Esteira', '', True)
            funcao['Esteira'] = 'INTEGRADO'

            funcao.to_excel(fr'{self.caminho}\FUNCAO TRATADO {self.convenio} AUTOMATIZADO {str(datetime.now().month).zfill(2)}{datetime.now().year}.xlsx', index=False)

            # Certificar-se de que as colunas 'Código' e 'NR_OPER' estão presentes
            if 'Codigo_Credbase' in cred.columns and 'NR_OPER_EDITADO' in funcao.columns:
                # Empilhar os valores da coluna 'NR_OPER' abaixo dos valores da coluna 'Código'
                nova_coluna_codigo = cred['Codigo_Credbase'].tolist() + funcao['NR_OPER_EDITADO'].tolist()
                nova_coluna_matricula = cred['Matricula'].tolist() + funcao['MATRICULA'].tolist()
                nova_coluna_esteira = cred['Esteira'].tolist() + funcao['Esteira'].tolist()
                nova_coluna_inicio = cred['Inicio'].tolist() + funcao['DT_BASE'].tolist()
                nova_coluna_cliente = cred['Cliente'].tolist() + funcao['CLIENTE'].tolist()
                nova_coluna_CPF = cred['CPF'].tolist() + funcao['CPF'].tolist()
                nova_coluna_banco = cred['Banco'].tolist() + funcao['ORIGEM_2'].tolist()
                nova_coluna_produto = cred['Tipo'].tolist() + funcao['PRODUTO'].tolist()
                nova_coluna_prazo = cred['Prazo'].tolist() + funcao['PARC'].tolist()
                nova_coluna_convenio = cred['Convenio'].tolist() + funcao['ORIGEM_4'].tolist()
                nova_coluna_parcela = cred['Parcela'].tolist() + funcao['VLR_PARC'].tolist()

                # Criar um novo DataFrame para armazenar o resultado
                nova_planilha_codigo = pd.DataFrame(nova_coluna_codigo, columns=['Codigo_Credbase'])

                # Manter as outras colunas da planilha A
                outras_colunas_codigo = cred.drop(columns=['Codigo_Credbase'])

                # Resetar os índices de ambos antes do concat
                nova_planilha_codigo.reset_index(drop=True, inplace=True)
                outras_colunas_codigo.reset_index(drop=True, inplace=True)

                # cred = cred.drop('Esteira', axis=1)
                cred = pd.concat([nova_planilha_codigo, outras_colunas_codigo.reindex(nova_planilha_codigo.index)], axis=1)

                # Adiciona Integrado e Não Integrado na coluna esteira do Credbase
                cred['Esteira'] = nova_coluna_esteira

                # Adiciona as matriculas na coluna de matricula
                cred['Matricula'] = nova_coluna_matricula

                # Junta os clientes do Função junto a coluna de clientes do Credbase
                cred['Cliente'] = nova_coluna_cliente

                # Junta os CPFs do Função junto a coluna de CPFs do Credbase
                cred['CPF'] = nova_coluna_CPF

                # Adiciona o convenio devido na coluna Convenio
                cred['Convenio'] = nova_coluna_convenio

                # Adiciona os bancos junto do cred
                cred['Banco'] = nova_coluna_banco

                # Junta a coluna de VLR_PARC do função junto à coluna Parcela do Credbase
                cred['Parcela'] = nova_coluna_parcela

                # Junta a coluna de PRODUTO do função junto à coluna Tipo do Credbase
                cred['Tipo'] = nova_coluna_produto

                # Junta a coluna DataBase do função junto à coluna Inicio do Credbase
                cred['Inicio'] = nova_coluna_inicio

                # Junta a coluna PARC do função junto à coluna Prazo do Credbase
                cred['Prazo'] = nova_coluna_prazo

        cred['Tabela'] = cred['Tabela'].fillna('CARTÃO')

        cred_tratado = self.validacao_termino(cred)

        credbase_reduzido = cred_tratado[['Codigo_Credbase', 'Banco(s) quitado(s)', 'Filial', 'Esteira', 'Esteira(dias)', 'Tipo',
                                 'Operacao', 'Situacao', 'Inicio', 'Cliente', 'Data Averbacao', 'CPF', 'Convenio', 'Banco',
                                 'Parcela', 'Prazo', 'Tabela', 'Matricula']]

        credbase_reduzido.to_excel(rf'{self.caminho}\Teste Credbase Reduzido.xlsx', index=False)

        return credbase_reduzido

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

    def validacao_termino(self, cred):
        cred_copy = cred.copy()
        conciliacao_tratado = self.trata_conciliacao()

        # Puxar o último status para o credbase
        status = conciliacao_tratado.filter(like='ST ')
        status_name = status.columns[-1]
        '''print(f'Tipo do contrato no cred: {type(cred_copy.loc[1, 'Codigo_Credbase'])}')
        print(f'Tipo do contrato da conciliação: {type(conciliacao_tratado.loc[1, 'CONTRATOS'])}')'''

        # Certifica que todos os contratos no Credbase trabalhado são do mesmo tipo
        # cred['Codigo_Credbase'] = cred['Codigo_Credbase'].astype(str)

        cred_copy.loc[:, 'Status'] = cred_copy['Codigo_Credbase'].map(conciliacao_tratado.set_index('CONTRATOS')[status_name]).to_dict()
        conciliacao_tratado.to_excel(fr'{self.caminho}\Conciliacao_TESTE.xlsx', index=False)


        # print(f'status \n{cred_copy[cred_copy['Codigo_Credbase'] == 300846910]}')

        # Puxar o saldo para o credbase
        cred_copy.loc[:, 'Saldo'] = cred_copy['Codigo_Credbase'].map(conciliacao_tratado.set_index('CONTRATOS')['Saldo']).to_dict()

        # Valor que vai ser lançado
        # Substitui NaN em "Saldo" por um valor muito alto (para que "Parcela" seja escolhida)
        valor_a_lancar = np.minimum(np.abs(cred_copy['Saldo']).fillna(float('inf')), cred_copy['Parcela'])

        cred_copy['Valor a lançar'] = valor_a_lancar

        return cred_copy

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
        df_limpo['Codigo_Credbase'] = df_limpo['Codigo_Credbase'].astype(str).str.strip()
        df_limpo['Operacao'] = df_limpo['Operacao'].astype(str).str.strip()
        print("Criando mapa de referência CPF -> Contratos...")
        cpf_contratos = df_limpo.groupby('CPF')['Codigo_Credbase'].apply(list).to_dict()
        cpf_operacao = df_limpo.groupby('CPF')['Operacao'].apply(list).to_dict()
        # print(f'Mapa contratos:\n{cpf_contratos}')

        # --- Passo 2: Definir a função que será aplicada em cada linha (LÓGICA ALTERADA) ---
        def encontrar_contratos_na_linha(row):
            cpf = row['CPF']
            texto_contratos_sujo = str(row['Id. ADE'])

            # Garante que as listas existam
            contratos_validos_para_cpf = cpf_contratos.get(cpf, [])
            operacoes_validas_para_cpf = cpf_operacao.get(cpf, [])


            if not contratos_validos_para_cpf:
                return []

            # 1. DIVIDIR: Mesma lógica de limpeza
            partes_sujas = [p for p in re.split(r'[-/,;\s]+', texto_contratos_sujo) if p]

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
                        if index_remocao < len(operacoes_disponiveis):
                            del operacoes_disponiveis[index_remocao]

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

    def orbital_tratado(self, orbital, funcao_para_separar):
        if orbital is None:
            return None

        if self.convenio == 'PREF PIRACICABA':
            orbital_preparado = orbital.loc[
                orbital['Descrição EMPREGADOR'].str.contains('PREF PIRACICABA', case=False, na=False),
                ['Numero Contrato', 'nome_mutuario', 'num_cpf_mutuario', 'Valor da Parcela']
            ].copy()
        elif self.convenio == 'PREF PIRACICABA SEMAE':
            orbital_preparado = orbital.loc[
                orbital['Descrição EMPREGADOR'].str.contains('PREF PIRA SEMAE', case=False, na=False),
                ['Numero Contrato', 'nome_mutuario', 'num_cpf_mutuario', 'Valor da Parcela']
            ].copy()
        elif self.convenio == 'GOV RJ':
            orbital_preparado = orbital.loc[
                orbital['Descrição EMPREGADOR'].str.contains('GOV RJ|GOV RJ DG|GOV RJ SEG|GOV RJ M NEG', case=False, na=False),
                ['Numero Contrato', 'nome_mutuario', 'num_cpf_mutuario', 'Valor da Parcela']
            ].copy()
        orbital_preparado.columns = ['Proposta', 'Cliente', 'CPF/CNPJ', 'VALOR DESCONTO']

        funcao_so_orbital = funcao_para_separar.loc[
            funcao_para_separar['PRODUTO'].isin(['000061 - CARTÃO PLÁSTICO', '000094 - CARTÃO PLÁSTICO - RE']),
            ['NR_PROP', 'CLIENTE', 'CPF', 'VLR_PARC']
        ].copy()

        funcao_so_orbital.columns = ['Proposta', 'Cliente', 'CPF/CNPJ', 'VALOR DESCONTO']

        orbital_final = pd.concat([funcao_so_orbital, orbital_preparado])

        orbital_final = orbital_final.drop_duplicates(subset=['Proposta'], keep='first')

        orbital_final.to_excel(fr'{self.caminho}\ORBITAL TRABALHADO {self.convenio}.xlsx', index=False)

        return orbital_final

    def trata_averbacao(self):
        # PUXA OS ARQUIVOS À SEREM TRATADOS
        data = self.unifica_historico_averb()
        cred = self.unificacao_cred_funcao()
        consig = self.consignataria
        orbital_tratado = self.orbital_tratado(self.orbital, self.funcao_bruto)
        convenio = self.convenio

        # PEGA APENAS AS COLUNAS NECESSÁRIAS DO ARQUIVO BRUTO
        colunas = ['Órgão', 'Matrícula', 'Servidor', 'CPF', 'Situação', 'Categoria', 'Consignatária', 'Id. órgão',
                   'Órgão.1', 'Id. serviço', 'Serviço', 'Nº ADE', 'Id. ADE', 'Data inc.', 'Vlr ant.', 'Vlr novo']

        data_averbados_bruto = data[colunas]

        data_averbados = self.extrair_contratos_com_referencia(data_averbados_bruto, cred)

        semi_cred = cred[cred['Esteira'].isin(self.condicoes_1)]

        conciliacao_tratado = self.trata_conciliacao()

        # Operações liquidadas. Tratando NRº OPER EDITADO
        # OP LIQUIDADO
        try:
            oper_liq = self.liquidados_file
            contratos_tratados_liq = oper_liq['Nº OPERAÇÃO'].str.slice(0, 9)
            oper_liq.insert(1, "Nº OPERAÇÃO EDITADO", contratos_tratados_liq, True)

        except Exception as e:
            oper_liq = pd.DataFrame(columns=['Nº OPERAÇÃO', 'Nº OPERAÇÃO EDITADO'])
            print(f"Planilha de Operações Liquidadas está vazia {e}")

        tutela = self.tutela

        # consig = self.consignataria

        # --- 1. Identifica TODAS as colunas que contêm contratos ---
        # Inclui a coluna original e as que foram extraídas pela função anterior.
        # Ajuste 'Contrato' se a sua coluna original tiver um nome diferente (ex: 'Identificador')
        # colunas_com_contratos = ['Contrato'] + [col for col in data_averbados.columns if 'Contrato Editado' in col]
        colunas_com_contratos = [col for col in data_averbados.columns if 'Contrato Editado' in col]

        # Remove duplicatas, caso o nome 'Contrato' já esteja na lista
        colunas_com_contratos = list(dict.fromkeys(colunas_com_contratos))

        # print(f"Colunas de contrato identificadas para análise: {colunas_com_contratos}")

        # Vou tentar colocar a coluna de Orbital aqui no meio mesmo
        if orbital_tratado is not None:
            mask_orbital = orbital_tratado.groupby('CPF/CNPJ')['VALOR DESCONTO'].sum()
            data_averbados_bruto['ORBITAL'] = ''
            data_averbados_bruto['ORBITAL'] = data_averbados_bruto['CPF_Formatado'].map(mask_orbital)

        # --- 2. Loop único para criar as colunas de Esteira e Valor para CADA contrato ---
        # O enumerate nos dá um índice numérico (i) para criar nomes de coluna únicos.
        for i, nome_coluna_contrato in enumerate(colunas_com_contratos, start=1):
            # print(f"Processando coluna '{nome_coluna_contrato}'...")

            # Cria a coluna de Esteira correspondente
            data_averbados[f'Esteira_{i}'] = data_averbados[nome_coluna_contrato].map(
                cred.set_index('Codigo_Credbase')['Esteira'].to_dict()
            )

            # Cria a coluna de Valor da Parcela correspondente
            data_averbados[f'Valor_Unif_{i}'] = data_averbados[nome_coluna_contrato].map(
                semi_cred.set_index('Codigo_Credbase')['Parcela'].to_dict()
            )

            # Puxa os valores de saldo da conciliação
            data_averbados[f'Saldo {i}'] = data_averbados[nome_coluna_contrato].map(
                conciliacao_tratado.set_index('CONTRATOS')['Saldo'].to_dict()
            )

            # Puxando os contratos liquidados (FORMA CORRIGIDA)
            # Cria a nova coluna 'OP LIQ {i}' com o resultado do map
            data_averbados[f'OP LIQ {i}'] = data_averbados[nome_coluna_contrato].map(
                oper_liq.set_index('Nº OPERAÇÃO EDITADO')['Nº OPERAÇÃO'].to_dict()
            )

            # --- PASSO 2: PREPARAÇÃO E LIMPEZA DE DADOS ---
            # Agora que todas as colunas foram criadas, garantimos que sejam numéricas para os cálculos.
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
        data_averbados["LIMINAR"] = data_averbados['CPF'].map(tutela.set_index('CPF')['PROCESSO'].to_dict())
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
        if consig == 'HOJE':
            data_averbados = self.adiciona_peculio(data_averbados)
        else:
            data_averbados['Lançar'] = np.minimum(data_averbados['Soma'], data_averbados['Vlr novo'])
            data_averbados.loc[condicao_liminar, 'Lançar'] = 0

        # print("Cálculos de Soma e Diferença finalizados.")
        data_averbados.to_excel(fr'{self.caminho}\TRABALHADO CARTAO {self.convenio} {self.consignataria} {datetime.now().strftime("%m-%Y")}.xlsx', index=False)

        return data_averbados

    def credbase_trabalhado_func(self, averbado_trabalhado):

        cred = self.unificacao_cred_funcao()

        # CORREÇÃO 2: Garante que a coluna-chave principal seja string e sem espaços
        cred['Codigo_Credbase'] = cred['Codigo_Credbase'].astype(str).str.strip()

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
                novas_esteiras = cred['Codigo_Credbase'].map(mapa)

                # AGORA VAI FUNCIONAR: preenche APENAS os vazios (NaN) em 'Esteira' com os novos valores
                cred['Esteira'] = cred['Esteira'].fillna(novas_esteiras)

            except (IndexError, KeyError) as e:
                print(f"Aviso: Não foi possível processar o par de colunas para '{nome_coluna_contrato}'. Erro: {e}")

                # print(type(cred.loc[cred['Codigo_Credbase'] == '301361499', 'Codigo_Credbase']))

            except (IndexError, KeyError) as e:
                print(f"Aviso: Não foi possível processar o par de colunas para '{nome_coluna_contrato}'. Erro: {e}")

        # --------------------------------------------------------------------------------------------------------------


        conciliacao_tratado = self.trata_conciliacao()

        cred_esteira = cred[cred['Esteira'].isin(self.condicoes_1)]
        cred_esteiras = cred

        # Separa as tabelas de lançamento
        condicoes_2 = cred_esteira['Tabela'].str.contains('CART')
        cred_tab_cart = cred_esteira[condicoes_2]

        # Seleciona Tipo Cartão
        condicoes_3 = ['Cartão']
        cred_tipo = cred_esteira[cred_esteira['Tipo'].isin(condicoes_3)]

        # Tira tabela Cartão
        condicoes_4 = ~cred_tipo['Tabela'].str.contains('CART')
        cred_tipo = cred_tipo[condicoes_4]

        # Tira tipo Cartão
        cred_amor = cred_esteira[~cred_esteira['Tipo'].isin(condicoes_3)]

        # Tira tabela Cartão
        condicoes_5 = ~cred_amor['Tabela'].str.contains('CART')
        cred_amor = cred_amor[condicoes_5]

        # Verifica Amortização em Bancos quitados depois de tirar tipo e tabela cartão
        cred_amor['Banco(s) quitado(s)'] = cred_amor['Banco(s) quitado(s)'].astype(str)
        condicoes_6 = cred_amor['Banco(s) quitado(s)'].str.contains('AMOR', na=False)
        cred_amor['Banco(s) quitado(s)'] = cred_amor['Banco(s) quitado(s)']
        cred_amor = cred_amor[condicoes_6]
        credbase_trabalhado = pd.concat([cred_tab_cart, cred_tipo, cred_amor], ignore_index=True)

        # Seleciona a consignatária correta
        if self.consignataria == 'CIASPREV':
            consig_list = ['BANCO ACC', 'CIASPREV', 'QUERO MAIS CRÉDITO']
        elif self.consignataria == 'CAPITAL':
            consig_list = ['BANCO CAPITAL', 'BANCO CAPITAL S.A.', 'CB/CAPITAL', 'CB/CAPITAL	',
                           'CC BANCO CAPITAL S.A. ',
                           'CAPITAL', 'Banco CB DIGITAL', 'QUERO MAIS CRÉDITO', 'AKI CAPITAL', 'J.A BANK ', 'J.A BANK',
                           'CAPITAL*', 'AKRK']
        elif self.consignataria == 'CLICKBANK':
            consig_list = ['CB/CLICK BANK', 'CB/CLICK BANK	', 'Banco CB DIGITAL', 'QUERO MAIS CRÉDITO', 'CLICK']
        elif self.consignataria == 'HOJE':
            consig_list = ['BANCO HP', 'QUERO MAIS CRÉDITO', 'AKI CAPITAL']
        elif self.consignataria == 'ABCCARD':
            consig_list = ['ABCCARD', 'QUERO MAIS CRÉDITO', 'AKI CAPITAL']
        elif self.consignataria == 'CB/BEM CARTÕES':
            consig_list = ['CB/BEM CARTÕES', 'QUERO MAIS CRÉDITO', 'BEM CARTÕES', 'AKI CAPITAL']

        credbase_trabalhado = credbase_trabalhado[credbase_trabalhado['Banco'].isin(consig_list)]

        # Tira ponto e traço do CPF

        credbase_trabalhado.loc[:, 'Saldo'] = credbase_trabalhado['Codigo_Credbase'].map(
            conciliacao_tratado.set_index('CONTRATOS')['Saldo']).to_dict()

        # Muda o Tipo da coluna Parcela
        '''credbase_trabalhado['Parcela'] = credbase_trabalhado['Parcela'].str.replace('.', '')
        credbase_trabalhado['Parcela'] = credbase_trabalhado['Parcela'].str.replace(',', '.')'''
        credbase_trabalhado['Parcela'] = pd.to_numeric(credbase_trabalhado['Parcela'], errors='coerce').fillna(0)

        # Valor que vai ser lançado
        # Substitui NaN em "Saldo" por um valor muito alto (para que "Parcela" seja escolhida)
        valor_a_lancar = np.minimum(np.abs(credbase_trabalhado['Saldo']).fillna(float('inf')),
                                    credbase_trabalhado['Parcela'])

        credbase_trabalhado['Valor a lançar'] = valor_a_lancar

        nome_credbase_trabalhado = f"CREDBASE TRABALHADO {self.convenio} {self.consignataria} {datetime.now().strftime("%m-%Y")}.xlsx"
        credbase_trabalhado.to_excel(fr"{self.caminho}\{nome_credbase_trabalhado}", index=False)

        return credbase_trabalhado

    def arquivo_lancamento(self):
        data_averbados = self.trata_averbacao()

        codigo_desconto_dict = {"PREF ACAILANDIA": "382", "GOV. RJ": "4541CARTAO DE CREDITO I", "IGEPREV CAPITAL": "04072",
                                "IGEPREV CIASPREV": "02470", "PREF PIRACICABA": "5600", "PREF PIRACICABA - SEMAE": "675",
                                "PREV PIRACICABA": "6277", "PREF BELO HORIZONTE CB": "204U", "BELO HORIZONTE CC": "204V",
                                "PREF MACAE": "11Q0", "PREVIPALMAS CAPITAL": "10243", "PREVIPALMAS CIASPREV": "894"}

        estab_dict = {"PREF ACAILANDIA": "001", "IGEPREV CAPITAL": "001", "IGEPREV CIASPREV": "001",
                      "PREF PIRACICABA": "001", "PREF PIRACICABA - SEMAE": "002",
                      "PREV PIRACICABA": "001", "PREF BELO HORIZONTE CB": "001", "BELO HORIZONTE CC": "001",
                      "PREF MACAE": "001", "PREVIPALMAS CAPITAL": "001", "PREVIPALMAS CIASPREV": "001"}

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
            codigo_de_desconto = codigo_desconto_dict[self.convenio]
        except KeyError:
            print(f'\nConvênio {self.convenio} não consta no dicionário de "Códigos de Desconto!"')
            return

        estabelecimento = estab_dict[self.convenio]

        # Cria o novo DataFrame
        data_averbados['Matrícula'] = data_averbados['Matrícula'].astype(int)
        # print(f'\ndata_averbados - matricula\n{data_averbados['Matrícula']}')
        credbase_trabalhado = self.credbase_trabalhado_func(data_averbados)
        temp = data_averbados[data_averbados['Lançar'] > 0]
        colunas_alancar = ['Órgão', 'Matrícula', 'Servidor', 'CPF', 'Situação', 'Categoria', 'Consignatária', 'Id. órgão',
                   'Órgão.1', 'Id. serviço', 'Serviço', 'Nº ADE', 'Id. ADE', 'Data inc.', 'Vlr ant.', 'Vlr novo', 'Lançar']
        a_lancar = pd.DataFrame(temp[colunas_alancar])

        # Calcule a SOMASE para cada categoria no Averbacoes Trabalhadas
        somas_por_categoria = data_averbados.groupby('CPF')['Lançar'].transform('sum')
        data_averbados['SOMASE'] = somas_por_categoria
        data_averbados['SOMASE'] = data_averbados['SOMASE'].astype(float)

        # Calcula o Somase Cred
        data_averbados['SOMASE CRED'] = ''

        soma_condicional_dict_averb = credbase_trabalhado.groupby('CPF')['Valor a lançar'].sum().to_dict()
        data_averbados['SOMASE CRED'] = data_averbados['CPF'].map(soma_condicional_dict_averb)
        data_averbados['SOMASE CRED'] = data_averbados['SOMASE CRED'].map('{:.2f}'.format).astype(float)

        # DIFF
        data_averbados['DIFF'] = data_averbados['SOMASE CRED'] - data_averbados['SOMASE']

        # SOMASE NO CREDBASE TRABALHADO
        cred_somase = credbase_trabalhado.groupby('CPF')['Valor a lançar'].transform('sum')
        credbase_trabalhado.insert(16, 'SOMASE CRED', cred_somase, True)
        credbase_trabalhado['SOMASE CRED'] = credbase_trabalhado['SOMASE CRED'].map('{:.2f}'.format).astype(float)

        credbase_trabalhado.insert(17, 'SOMASE AVERB', '', True)
        credbase_trabalhado.insert(18, 'DIFF', '', True)

        # Somase Averb no Credbase Trabalhado
        soma_condicional_dict_cred = data_averbados.groupby('CPF')['Lançar'].sum().to_dict()
        credbase_trabalhado['SOMASE AVERB'] = credbase_trabalhado['CPF'].map(soma_condicional_dict_cred)
        credbase_trabalhado['DIFF'] = credbase_trabalhado['SOMASE CRED'] - credbase_trabalhado['SOMASE AVERB'].astype(
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

        a_lancar["ESTABELECIMENTO"] = estabelecimento if self.convenio != 'GOV RJ' else a_lancar['Órgão.1'].map(emp_dict_gov_rj)
        a_lancar['ÓRGÃO'] = a_lancar['Id. órgão'] if self.convenio != 'GOV RJ' else a_lancar['Órgão.1']
        a_lancar['CÓDIGO DE DESCONTO'] = codigo_de_desconto

        self.process_layout(a_lancar, self.caminho)


    # --- FUNÇÕES DE FORMATAÇÃO (Mantive as seguras) ---
    def format_number(self, series, length):
        if length == 0: return ""

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
        return s.str.zfill(length)

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

        matricula = self.format_number(df['Matrícula'], regras['MAT'])
        cpf = self.format_cpf(df['CPF'], regras['CPF'])
        nome = self.format_text(df['Servidor'], regras['NOME'])
        estab = self.format_number(df['ESTABELECIMENTO'], regras['EST'])
        orgao = self.format_number(df['ÓRGÃO'], regras['ORG'])
        cod_desc = self.format_number(df['CÓDIGO DE DESCONTO'], regras['COD']) if not self.convenio in ['GOV RJ', 'PREF MACAE'] else self.format_text(df['CÓDIGO DE DESCONTO'], regras['COD'])
        valor = self.format_currency(df['Lançar'], regras['VAL'])

        # Campos calculados na hora (Data e Constantes)
        competencia_atual = f'{str(datetime.now().month).zfill(2)}{datetime.now().year}'

        # Como Prazo e Operação são constantes mas podem ter tamanho variável:
        prazo = self.format_constant('1', regras['PRZ'])  # Assumi '1' como padrão, ajuste se for coluna
        comp = self.format_constant(competencia_atual, regras['COMP'])
        operacao = self.format_constant('I', regras['OP'])  # 'I' de Inclusão

        # 3. Concatena tudo
        if self.convenio in ['PREF ACAILANDIA', 'PREF MACAE', 'PREVIPALMAS', 'PREF BELO HORIZONTE']:
            layout = (matricula + cpf + nome + estab + orgao + cod_desc + valor + prazo + comp + operacao)
        elif self.convenio == 'GOV RJ':
            layout = (matricula + cpf + nome + cod_desc + estab + valor + comp + operacao)
        elif self.convenio.astype(str).str.contains('PIRACICABA'):
            layout = (matricula + cpf + estab + orgao + cod_desc + valor + prazo + comp + operacao)
        elif self.convenio == 'GOV ES':
            layout = (matricula + cpf + nome + cod_desc + valor + prazo + comp + operacao)
        else:
            print('Nenhum convênio conhecido foi apresentado para criar o arquivo de lançamento...')
            print(f'Convênio solicitado: {self.convenio}')
            return

        return layout

    def save_layout(self, layout, output_dir):
        # Nome do arquivo agora usa o convênio dinâmico
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

