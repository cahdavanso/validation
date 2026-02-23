from thefuzz import fuzz
import pandas as pd
import openpyxl
import numpy as np
from datetime import datetime
import os
import logging
import re

class SERHA:
    def __init__(self, portal_file_list, convenio, front, conciliacao, trabalhado_anterior, rubrica, caminho, complementar=None, orbital=None):
        # isso é apenas para caso seja um arquivo de averbação
        self.averbados = portal_file_list if portal_file_list is not None else None
        if self.averbados is not None:
            self.averbados.rename(columns={'Num Ipsemg': 'MASP     '}, inplace=True)
            self.averbados.rename(columns={'N_IPSEMG ': 'MASP     '}, inplace=True)
            print(f'Colunas do arquivo de averbados: {self.averbados.columns if self.averbados is not None else "None"}')

        # Isso é apenas para caso o front seja um arquivo apenas
        self.front_unificados = front if front is not None else None

        self.convenio = convenio

        conciliacao_falso = pd.DataFrame(
            columns=['CONTRATOS', 'CPF', 'PRESTAÇÃO', 'PRAZO', 'D8 JUN 25', 'ST JUL 25', 'RECEBIDO GERAL'])
        conciliacao_falso['CONTRATOS'] = 123
        conciliacao_falso['CPF'] = '123.456'
        conciliacao_falso['PRESTAÇÃO'] = 10
        conciliacao_falso['PRAZO'] = 96
        conciliacao_falso['D8 JUN 25'] = 10
        conciliacao_falso['ST JUL 25'] = 'DESCONTO TOTAL'
        conciliacao_falso['RECEBIDO GERAL'] = 0

        self.conciliacao = conciliacao if conciliacao is not None else conciliacao_falso
        self.conciliacao.rename(columns={'TIPO OPERAÇÃO': 'PRODUTO', 'PRODUTOS PELO D8': 'PRODUTO'}, inplace=True)
        # Vamos renomear a primeira coluna da conciliação
        self.conciliacao.rename(columns={conciliacao.columns[0]: 'CONTRATOS'}, inplace=True)

        # TRABALHADOS DO MÊS ANTERIOR
        self.trabalhado_anterior = trabalhado_anterior if trabalhado_anterior is not None else None

        # LÊ A RUBRICA
        self.rubrica = rubrica

        # COMPLEMENTOS MÊS ANTERIOR
        self.complementares = complementar if complementar is not None else None

        self.caminho = caminho

        self.orbital = orbital if orbital is not None else None

        self.main()

    def tratamento_front_preliminar(self):
        front_consig = self.front_unificados.copy()

        conciliacao = self.conciliacao.copy()

        orbital = self.orbital.copy() if self.orbital is not None else None

        # Insere as colunas vazias necessárias
        front_consig.insert(21, 'Saldo', '', True)
        front_consig.insert(22, 'Valor a lançar', '', True)
        front_consig.insert(23, 'PRAZO', '', True)
        front_consig.insert(24, 'OBS', '', True)

        front_consig.rename(columns={'Prestracao': 'Prestacao'}, inplace=True)

        print(f'Esteiras Únicas do front: {front_consig["Esteira"].unique()}')

        # Colocar 11 FORMALIZACAO em todas as células que começarem com 11 FOR
        '''front_consig['Esteira'] = front_consig['Esteira'].apply(lambda x: '11 FORMALIZACAO' if isinstance(x, str) and x.startswith('11 FOR') else x)
        front_consig['Esteira'] = front_consig['Esteira'].apply(lambda x: '07.0 QUITACAO ENVIO DE CESSAO' if isinstance(x, str) and x.startswith('07.0 QUITACAO') else x)
        front_consig['Esteira'] = front_consig['Esteira'].apply(lambda x: '07.2 TED DEVOLVIDA PAGAMENTO AO CLIENTE' if isinstance(x, str) and x.startswith('07.2 TED DEVOLVIDA') else x)'''

        # Esteiras
        esteiras_permitidas = ['02.03 AGUARDANDO PROCESSAMENTO CARTAO', '11 FORMALIZACAO', '11 FORMALIZAA\x87A\x83O', '09.0 PAGO', 'RISCO DA OPERACAO - OBITO', "11 FORMALIZAAÂ\x87AÂ\x83O",
                               '14.0 RISCO DA OPERACAO - OBITO', 'RISCO DA OPERACAO-DEMAIS SITUACOES', '11.PROBLEMAS DE AVERBACAO', '10.7.0 INGRESSAR COM PROCESSO OU ACAO JURIDICO',
                               '07.1 \x96 QUITACAO \x96 PAGAMENTO AO CLIENTE', '10.7 CONTRATO NAO AVERBADO - AGUARDANDO RESOLUCAO', '11.2  DETERMINACAO JUDICIAL',
                               "15.0\tRISCO DA OPERACAO-DEMAIS SITUACOES", "11.1 CONTRATO FISICO ENVIADO AO BANCO", "07.0 QUITACAO \x96 ENVIO DE CESSAO", "07.2 TED DEVOLVIDA PAGAMENTO AO CLIENTE",
                               "07.2 TED DEVOLVIDA A\x80\x93 PAGAMENTO AO CLIENTE", "99 CARTAO UTILIZADO", "11 FORMALIZAA\x87A\x83O", "07.1.1 QUITACAO - CORRECAO DE CCB",
                               "RISCO DA OPERAA\x87A\x82O-DEMAIS SITUAA\x87A\x95ES", "10.7 CONTRATO NA\x83O AVERBADO - AGUARDANDO RESOLUA\x87A\x83O", "11 FORMALIZAAÂ‡AÂƒO",
                               "10.5 AGUARDANDO AVERBACAO COMPRA OUTROS CONVENIOS", "RISCO DA OPERAA\x87A\x82O-DEMAIS SITUAA\x87A\x95ES", "07.2 TED DEVOLVIDA AÂ\x80Â\x93 PAGAMENTO AO CLIENTE",
                               "RISCO DA OPERAAÂ\x87AÂ\x82O-DEMAIS SITUAAÂ\x87AÂ\x95ES", "10.7 CONTRATO NAÂ\x83O AVERBADO - AGUARDANDO RESOLUAÂ\x87AÂ\x83O"
                              ]
        
        
        # Converte para lista de colunas
        cols = list(conciliacao.columns)

        # Atualiza o DataFrame com novos nomes
        conciliacao.columns = cols
        conciliacao['CONTRATOS'] = conciliacao['CONTRATOS'].astype('Int64')

        # Adiciona a coluna de tipo da Conciliação
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

        # ------------------------------------ ESTEIRAS REMOVIDAS ------------------------------------- #
        front_consig_esteiras_removidas = front_consig[~front_consig['Esteira'].isin(esteiras_permitidas)].copy()
        try:
            front_consig_esteiras_removidas.to_excel(os.path.join(self.caminho, f'FRONT ESTEIRAS REMOVIDAS {self.convenio}.xlsx'), index=False)
        except Exception as e:
            print(f"Erro ao salvar o arquivo de esteiras removidas: {e}")

        # Trata coluna de Tipo da Conciliação
        front_consig_esteiras.loc[front_consig_esteiras['Tipo Conciliação'].isin([np.nan, '', ' - ']), 'Tipo Conciliação'] = front_consig_esteiras['Tipo Operacao']

        # --------------------------------------------- ORBITAL --------------------------------------------- #
        # --- ETAPA 1: Garantir que as chaves são do mesmo tipo (Texto) ---
        # Isso evita o erro clássico onde um lado é número e o outro é texto
        if orbital is not None:
            front_consig_esteiras['Contrato'] = front_consig_esteiras['Contrato'].astype(str).str.strip()
            # orbital.rename(columns={'id_contr_banco': 'Numero de Contrato'}, inplace=True)

            

            orbital['Numero de Contrato'] = orbital['Numero de Contrato'].astype(str)
            '''print(f'\nContrato 301268942 na coluna Numero de Contrato: {orbital.loc[orbital["Numero de Contrato"] == "301268942", "Validação  desconto final"]}\n')
            print(f'Contrato 301268942 no front: {front_consig_esteiras.loc[front_consig_esteiras["Contrato"] == "301268942", "Prestacao"]}\n')'''


            # --- ETAPA 2: Criar o "Dicionário de Busca" da Orbital ---
            # Transforma a Orbital em uma série onde Índice = Contrato e Valor = Desconto
            mapa_orbital = orbital.set_index('Numero de Contrato')['Validação  desconto final']
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
        # front_consig_validado_termino['Obito'] = front_consig_validado_termino['Obito'].replace({'SIM': 1, 'NÃO': 0})
        # front_consig_validado_termino.loc[front_consig_validado_termino['Obito'] == 1, 'OBS'] = 'NÃO LANÇAR - ÓBITO'
 
        # Marca tudo que é orbital
        front_consig_validado_termino.loc[(front_consig_validado_termino['Orbital'].str.contains('SIM', na=False) & (front_consig_validado_termino['OBS'] == '')), 'OBS'] = 'NÃO LANÇAR - ORBITAL'

        # Marcar o que não é cartão Conciliação
        if self.rubrica == 'CARTÃO':
            # front_consig_validado_termino.loc[(~front_consig_validado_termino['Tipo Conciliação'].str.contains('Cartão de Crédito|CARTAO DE CREDITO', na=False) & (front_consig_validado_termino['OBS'] == '')), 'OBS'] = 'NÃO LANÇAR - NÃO CARTÃO'
            # front_consig_validado_termino.loc[(~front_consig_validado_termino['Tipo Operacao'].str.contains('Cartão de Crédito|CARTAO DE CREDITO', na=False) & (front_consig_validado_termino['OBS'] == '')), 'OBS'] = 'NÃO LANÇAR - NÃO CARTÃO'
            pass
        else:
            # front_consig_validado_termino.loc[(~front_consig_validado_termino['Tipo Conciliação'].str.contains('CARTAO BENEFICIO', na=False) & (front_consig_validado_termino['OBS'] == '')), 'OBS'] = 'NÃO LANÇAR - NÃO BENEFÍCIO'
            front_consig_validado_termino.loc[(~front_consig_validado_termino['Tipo Operacao'].str.contains('CARTAO BENEFICIO', na=False) & (front_consig_validado_termino['OBS'] == '')), 'OBS'] = 'NÃO LANÇAR - NÃO BENEFÍCIO'
        # Marcar liquidados em StatusContrato
        front_consig_validado_termino.loc[(front_consig_validado_termino['Status'].str.contains('Liquidado', na=False)), 'OBS'] = 'NÃO LANÇAR - LIQUIDADO'

        # TIRAR BANCO OUTROS
        front_consig_validado_termino.loc[(front_consig_validado_termino['Consignataria'].str.contains('OUTROS', na=False)), 'OBS'] = 'NÃO LANÇAR - BANCO OUTROS'

        # Salva com os NÃO LANÇAR
        print(f"DEBUG: Tentando salvar FRONT SEMI TRABALHADO em: {self.caminho}")
        try:
            front_consig_validado_termino.to_excel(os.path.join(self.caminho, f"FRONT SEMI TRABALHADO {self.convenio} {self.rubrica}.xlsx"), index=False)
            print("DEBUG: Arquivo salvo com sucesso!")
        except Exception as e:
            print(f"DEBUG: ERRO AO SALVAR: {e}")

        # --------------------------------------------------------------------------------------------- #
        return front_consig_validado_termino
        
    def tratamento_front(self):
        front_consig = self.tratamento_front_preliminar()

        if front_consig is False:
            print("tratamento_funcao: O tratamento preliminar do front falhou. Verifique os erros anteriores.")
            return False

        # Separa apenas o que retornou como "cartão de crédito" no tipo de conciliação
        if self.rubrica == 'CARTÃO':
            # front_consig_cartao_conciliacao = front_consig[front_consig['Tipo Conciliação'].str.contains('Cartão de Crédito|CARTAO DE CREDITO', na=False)].copy()
            # front_consig_cartao_conciliacao = front_consig[front_consig['Tipo Operacao'].str.contains('Cartão de Crédito|CARTAO DE CREDITO', na=False)].copy()
            front_consig_cartao_conciliacao = front_consig.copy()
            pass
        else:
            # front_consig_cartao_conciliacao = front_consig[front_consig['Tipo Conciliação'].str.contains('CARTAO BENEFICIO', na=False)].copy()
            front_consig_cartao_conciliacao = front_consig[front_consig['Tipo Operacao'].str.contains('CARTAO BENEFICIO', na=False)].copy()

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

        # --------------------------------------- TIRA BANCO OUTROS ----------------------------------------- #
        front_consig_trabalhado = front_consig_trabalhado[~front_consig_trabalhado['Consignataria'].str.contains('OUTROS', na=False)].copy()

        # ----------------------------------------- TIRA LIQUIDADOS ----------------------------------------- #
        front_consig_trabalhado = front_consig_trabalhado[~front_consig_trabalhado['Status'].str.contains('Liquidado', na=False)].copy()

        print('DEBUG: Esteiras finais do front trabalhado')
        try:
            front_consig_trabalhado.to_excel(
                os.path.join(self.caminho, f"FRONT TRABALHADO {self.convenio} {self.rubrica}.xlsx"),
                index=False, 
            )
        except Exception as e:
            print(f"DEBUG: ERRO AO SALVAR FRONT TRABALHADO: {e}")       

        return front_consig_trabalhado


    def trata_conciliacao(self):
        conciliacao_tratado = self.conciliacao

        if 'PRODUTO' not in conciliacao_tratado.columns:
            print("A coluna 'PRODUTO' não foi encontrada na conciliação. Verifique os nomes das colunas e tente novamente.")
            return False


        # Encontra o índice da primeira ocorrência de "CONTRATO" e altera
        # print(f'primeira coluna de conciliação {conciliacao_tratado.columns[0]}')
        conciliacao_tratado.rename(columns={conciliacao_tratado.columns[0]: 'CONTRATOS'}, inplace=True)
        # Converte para lista de colunas
        cols = list(conciliacao_tratado.columns)
        conciliacao_tratado.columns = cols
        conciliacao_tratado['CONTRATOS'] = conciliacao_tratado['CONTRATOS'].astype(str)
        conciliacao_tratado = conciliacao_tratado.drop_duplicates(subset='CONTRATOS')
        # Atualiza o DataFrame com novos nomes

        conciliacao_tratado = conciliacao_tratado

        # 1. Selecionar colunas com "d8" no nome e somar por linha (axis=1)
        # "D8 " precisa ficar com espaço para que a coluna "CONVENIO D8" não atrapalhe na hora da soma
        colunas_d8 = conciliacao_tratado.filter(like='D8 ').columns
        for col in colunas_d8:
            tipos = conciliacao_tratado[col].apply(type).value_counts()
            '''print(f"Coluna {col}:")
            print(tipos)
            print()'''
        conciliacao_tratado[colunas_d8] = conciliacao_tratado[colunas_d8].apply(pd.to_numeric, errors='coerce')

        soma_d8 = conciliacao_tratado.filter(like='D8 ').sum(axis=1)

        # 2. Calcular prestação * prazo
        prestacao_vezes_prazo = conciliacao_tratado['PRESTAÇÃO'] * conciliacao_tratado['PRAZO']

        # 3. Calcular o resultado final
        conciliacao_tratado['Pago'] = soma_d8 - prestacao_vezes_prazo
        conciliacao_tratado['Saldo'] = conciliacao_tratado['Pago'] + conciliacao_tratado['RECEBIDO GERAL']

        return conciliacao_tratado

    def validacao_termino_front(self, front):
        front_copy = front.copy()
        conciliacao_tratado = self.trata_conciliacao()
        if conciliacao_tratado is False:
            print("validacao_termino_front: O tratamento da conciliação falhou. Verifique os erros anteriores.")
            return False

        # Certifica que todos os contratos no Credbase trabalhado são do mesmo tipo
        # cred['Codigo_Credbase'] = cred['Codigo_Credbase'].astype(str)

        conciliacao_tratado['CONTRATOS'] = conciliacao_tratado['CONTRATOS'].astype('Int64')

        print('DEBUG: Colunas da conciliação tratada')
        try:
            conciliacao_tratado.to_excel(os.path.join(self.caminho, f"Conciliacao_TESTE {self.convenio} {self.rubrica}.xlsx"), index=False)
        except Exception as e:
            print(f"DEBUG: ERRO AO SALVAR Conciliacao_TESTE.xlsx: {e}")


        # print(f'status \n{cred_copy[cred_copy['Codigo_Credbase'] == 300846910]}')

        # Puxar o saldo para o credbase
        front_copy['Saldo'] = front_copy['Contrato'].map(conciliacao_tratado.set_index('CONTRATOS')['Saldo']).to_dict()
        # front_copy['Saldo'] = pd.to_numeric(front_copy['Saldo'], errors='coerce')

        # front_copy['Prestacao'] = front_copy['Prestacao'].astype(str).str.replace('.', '', regex=False)
        try:
            front_copy['Prestacao'] = front_copy['Prestacao'].astype(str).str.replace(',', '.', regex=False)
        except AttributeError as e:
            print(f"Prestacao não está como string. Erro: {e}\n Valores em Prestacao: \n{front_copy['Prestacao']}\n")

        front_copy['Prestacao'] = pd.to_numeric(front_copy['Prestacao'], errors='coerce')

        # Valor que vai ser lançado
        # Substitui NaN em "Saldo" por um valor muito alto (para que "Parcela" seja escolhida)
        valor_a_lancar = np.minimum(np.abs(front_copy['Saldo']).fillna(float('inf')), front_copy['Prestacao'])

        front_copy['Valor a lançar'] = valor_a_lancar

        return front_copy


    def trata_contratos(self, averbados_df, front_base):
        '''
        :param averbados_df:
        :param front_base:
        :return: df_codigos_tratados
        Função que faz o tratamento dos números de contrato do Relatório de Averbados
        '''

        print('Iniciando o tratamento dos contratos da averbação...')
        averbados_puro = averbados_df[['DATA', 'MASP', 'CPF Consignado', 'CPF Ponto e Traço',
                                       'Nome Consignado', 'ContratoOriginal']].copy()

        front_feito = front_base.copy()

        front_feito['Contrato'] = front_feito['Contrato'].astype(str)

        # print(f'Contratos da averbação:\n{averbados_puro['Contrato            ']}')

        def extrair_contratos_com_referencia(df_sujo: pd.DataFrame, df_limpo: pd.DataFrame) -> pd.DataFrame:
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
                cpf = row['CPF Ponto e Traço']
                texto_contratos_sujo = str(row['ContratoOriginal'])

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
            df_sujo['ContratoOriginal'] = df_sujo['ContratoOriginal'].astype(str).str.replace('nan', '')


            lista_de_contratos_encontrados = df_sujo.apply(encontrar_contratos_na_linha, axis=1)

            df_contratos_novos = pd.DataFrame(lista_de_contratos_encontrados.tolist(), index=df_sujo.index)
            df_contratos_novos.columns = [f'Contrato {i + 1}' for i in df_contratos_novos.columns]

            df_resultado = pd.concat([df_sujo, df_contratos_novos], axis=1)

            print("Processo concluído com sucesso!")
            try:
                df_resultado.to_excel(os.path.join(self.caminho, f"Relatório Averbados Contratos tratados {self.convenio} {self.rubrica}.xlsx"), index=False)
            except Exception as e:
                print(f"DEBUG: ERRO AO SALVAR RELATÓRIO AVERBADO CONTRATOS TRATADOS: {e}")
            return df_resultado


        # Chama a função principal com os dataframes preparados
        df_codigos_tratados = extrair_contratos_com_referencia(averbados_puro, front_feito)
        return df_codigos_tratados

    def trata_orbital(self, front_para_separar, orbital):
        '''
        Função que faz o tratamento do arquivo de Orbitall. Por enquanto ele ainda não tem utilidade
        :return:
        '''

        # Pegar do hífen para frente para conseguir pegar a autarquia do self.convenio, porque tem um padrão de "GOV. MG - IPSEMG" ou "GOV. MG - CBMMG"
        autarquia = self.convenio.split('-')[-1].strip()

        orbital_preparado = orbital.loc[
            orbital['Descrição EMPREGADOR'].str.contains(autarquia, case=False, na=False),
            ['Numero de Contrato', 'nome_mutuario', 'num_cpf_mutuario', 'Validação  desconto final']
        ].copy()
        orbital_preparado.columns = ['Proposta', 'Cliente', 'CPF/CNPJ', 'VALOR DESCONTO']


        if 'NÃO LANÇAR - ORBITAL' not in front_para_separar['OBS'].values:
            print('Não há registros de ORBITAL para tratar.')
            return None

        front_so_orbital = front_para_separar.loc[
            front_para_separar['OBS'] == 'NÃO LANÇAR - ORBITAL',
            ['Contrato', 'Nome', 'CPF', 'Prestacao']].copy()
        
        front_so_orbital.columns = ['Proposta', 'Cliente', 'CPF/CNPJ', 'VALOR DESCONTO']

        # front_so_orbital['Proposta'] = front_so_orbital['Proposta'].astype(str).str.strip()

        # front_so_orbital['VALOR DESCONTO'] = front_so_orbital['VALOR DESCONTO'].astype(str).str.replace('.', '', regex=False)
        front_so_orbital['VALOR DESCONTO'] = front_so_orbital['VALOR DESCONTO'].astype(str).str.replace(',', '.', regex=False)
        front_so_orbital['VALOR DESCONTO'] = pd.to_numeric(front_so_orbital['VALOR DESCONTO'], errors='coerce')

        orbital_final = pd.concat([front_so_orbital, orbital])

        orbital_final = orbital_final.drop_duplicates(subset=['Proposta'], keep='first')

        print(f"orbital_tratado: Salvando arquivo de orbital tratado teste com front")
        try:
            orbital_final.to_excel(os.path.join(self.caminho, f"ORBITAL TRABALHADO {self.convenio}.xlsx"), index=False)
            print(f"orbital_tratado: ORBITAL TRABALHADO {self.convenio} salvo com sucesso!")
        except Exception as e:
            print(f"orbital_tratado: ERRO AO SALVAR ORBITAL TRABALHADO {self.convenio}: {e}")

        return orbital_final

    def averbados_func(self, front, trabalhado_ant, complemento, front_trab):
        front_tudo = front.copy()
        # print(front_tudo['Esteira'].unique())
        trabalhado_mes_passado = trabalhado_ant.copy()
        trabalhado_mes_passado = trabalhado_mes_passado.rename(columns={'Cpf': 'CPF Consignado'})
        trabalhado_mes_passado = trabalhado_mes_passado.rename(columns={'Num Ipsemg': 'MASP'})
        trabalhado_mes_passado = trabalhado_mes_passado.rename(columns={'N_IPSEMG ': 'MASP'})
        trabalhado_mes_passado = trabalhado_mes_passado.rename(columns={'Contrato original': 'ContratoOriginal'})
        trabalhado_mes_passado = trabalhado_mes_passado.rename(columns={'Data': 'DATA'})
        trabalhado_mes_passado = trabalhado_mes_passado.rename(columns={'Data + Hora': 'DATA'})
        trabalhado_mes_passado = trabalhado_mes_passado.rename(columns={'CPF': 'CPF Consignado'})
        # trabalhado_mes_passado = trabalhado_mes_passado.iloc[:-2]
        front_trabalhado = front_trab.copy()

        if self.rubrica == 'CARTÃO':
            trabalhado_mes_passado.loc[
                ~trabalhado_mes_passado['ContratoOriginal'].astype(str).str.contains('/'),
                'ContratoOriginal'
            ] = trabalhado_mes_passado['ContratoOriginal'].astype(str).str[:9]

            averbados = self.averbados.copy()
            if complemento is None:
                complemento = pd.DataFrame(columns=['DATA', 'MASP', 'CPF Consignado', 'Nome Consignado', 'ContratoOriginal'])
                print('Nenhum complemento foi fornecido para o mês anterior.')
            else:
                complemento = complemento.rename(columns={'Data': 'DATA'})
                complemento = complemento.rename(columns={'Data + Hora': 'DATA'})

            # Remove a última linha do relatório de averbados
            averbados = averbados.loc[~averbados.iloc[:, 0].astype(str).str.contains('Auditoria Reservas Geral', na=False)].copy()

            # print(f'Relatorio de averbados:\n{averbados[['Contrato            ', 'Acao        ']]}')

            # No relatório de averbações abriremos o filtro da coluna "Acao", selecionaremos tudo que é Cancelamento e excluiremos da planilha
            averbados_sem_cancelamento = averbados.loc[averbados['Acao        '] != 'Cancelamento']

            # print(averbados_sem_cancelamento[['Contrato            ', 'Acao        ']])

            # Colocar os casos complementares
            # A partir da complementar vou fazer um contse para saber se já existe no Trabalhado Cartão atual
            contse_la_complementar = trabalhado_mes_passado.groupby("CPF Consignado")["CPF Consignado"].count().to_dict()
            complemento['Contse lá'] = complemento['CPF Consignado'].map(contse_la_complementar)

            complemento_final = complemento.loc[complemento['Contse lá'].isna()]

            # CADÊ O AGUINALDO!!!
            try:
                complemento_final.to_excel(os.path.join(self.caminho, f"COMPLEMENTO TRATADO {self.convenio} {self.rubrica}.xlsx"), index=False)
            except Exception as e:
                print(f"DEBUG: ERRO AO SALVAR COMPLEMENTO TRATADO {self.convenio}: {e}")

            nova_coluna_data = trabalhado_mes_passado['DATA'].tolist() + complemento_final['DATA'].tolist()
            nova_coluna_masp = trabalhado_mes_passado['MASP'].tolist() + complemento_final['MASP'].tolist()
            nova_coluna_CPF = trabalhado_mes_passado['CPF Consignado'].tolist() + complemento_final['CPF Consignado'].tolist()
            nova_coluna_nome = trabalhado_mes_passado['Nome Consignado'].tolist() + complemento_final['Nome Consignado'].tolist()
            nova_coluna_contrato_original = trabalhado_mes_passado['ContratoOriginal'].tolist() + complemento_final['ContratoOriginal'].tolist()

            nova_planilha_data = pd.DataFrame(nova_coluna_data, columns=['DATA'])

            outras_colunas_data = trabalhado_mes_passado.drop(columns=['DATA'])

            nova_planilha_data.reset_index(drop=True, inplace=True)
            outras_colunas_data.reset_index(drop=True, inplace=True)

            trabalhado_mes_passado = pd.concat([nova_planilha_data, outras_colunas_data.reindex(nova_planilha_data.index)], axis=1)

            trabalhado_mes_passado['MASP'] = nova_coluna_masp

            trabalhado_mes_passado['CPF Consignado'] = nova_coluna_CPF

            trabalhado_mes_passado['Nome Consignado'] = nova_coluna_nome

            trabalhado_mes_passado['ContratoOriginal'] = nova_coluna_contrato_original

            try:
                trabalhado_mes_passado.to_excel(os.path.join(self.caminho, f"TRABALHADO MÊS PASSADO COM COMPLEMENTO {self.convenio} {self.rubrica}.xlsx"), index=False)
                print(f"DEBUG: TRABALHADO MÊS PASSADO COM COMPLEMENTO {self.convenio} salvo com sucesso!")
            except Exception as e:
                print(f"DEBUG: ERRO AO SALVAR TRABALHADO MÊS PASSADO COM COMPLEMENTO {self.convenio}: {e}")

            # =================================== UPDATE DOS CONTRATOS DE COMPLEMENTO ==================================
            mapa_de_contratos = complemento.set_index('CPF Consignado')['ContratoOriginal']

            novos_contratos = trabalhado_mes_passado['CPF Consignado'].map(mapa_de_contratos)

            trabalhado_mes_passado = trabalhado_mes_passado.copy()
            trabalhado_mes_passado['ContratoOriginal'] = novos_contratos.fillna(trabalhado_mes_passado['ContratoOriginal'])
            # ==========================================================================================================


            # Cria a coluna de CPF com ponto e traço
            averbados_sem_cancelamento= averbados_sem_cancelamento.copy()
            averbados_sem_cancelamento['CPF Consig.'] = averbados_sem_cancelamento['CPF Consig.'].astype(int)
            cpf_tratado = averbados_sem_cancelamento['CPF Consig.'].astype(str).str.zfill(11).str.replace(r'(\d{3})(\d{3})(\d{3})(\d{2})',  r'\1.\2.\3-\4', regex=True)

            averbados_sem_cancelamento.insert(4, 'CPF Ponto e Traço', cpf_tratado, True)

            # Criação da coluna DATA, que é a junção de Data com Hora
            try:
                data_hora = averbados_sem_cancelamento['Data      '] + " " + averbados_sem_cancelamento['Hora    ']
            except Exception as e:
                averbados_sem_cancelamento['Data      '] = pd.to_datetime(averbados_sem_cancelamento['Data      '], format='ISO8601', errors='coerce').dt.strftime('%d/%m/%Y')
                averbados_sem_cancelamento['Data      '] = averbados_sem_cancelamento['Data      '].astype(str).str.strip()
                averbados_sem_cancelamento['Hora    '] = averbados_sem_cancelamento['Hora    '].astype(str).str.strip()
                print(f'Tipo da coluna Data {averbados_sem_cancelamento["Data      "].dtype}')
                print(f'Tipo da coluna Hora {averbados_sem_cancelamento["Hora    "].dtype}')
                data_hora = averbados_sem_cancelamento['Data      '] + " " + averbados_sem_cancelamento['Hora    ']
                print(f"Apuração de data e hora: {e}")
            

            averbados_sem_cancelamento.insert(2, 'DATA', '', True)
            averbados_sem_cancelamento['DATA'] = pd.to_datetime(data_hora, format='%d/%m/%Y %H:%M:%S')

            averbados_sem_cancelamento = averbados_sem_cancelamento.sort_values(by='DATA', ascending=False)

            # Contse aqui e Contse lá
            averbados_sem_cancelamento.insert(10, 'cont aq', '', True)
            averbados_sem_cancelamento.insert(11, 'cont la', '', True)

            averbados_sem_cancelamento['cont aq'] = averbados_sem_cancelamento.groupby('CPF Consig.')['CPF Consig.'].transform('count')

            cont_la = trabalhado_mes_passado.groupby('CPF Consignado')['CPF Consignado'].count().to_dict()
            averbados_sem_cancelamento['cont la'] = averbados_sem_cancelamento['CPF Consig.'].map(cont_la)
            averbados_sem_cancelamento['cont la'] = averbados_sem_cancelamento['cont la'].fillna(0)

            print(f'Averbados sem cancelamento cont igual a 1:\n{averbados_sem_cancelamento.loc[averbados_sem_cancelamento['cont la']>= 1, ['CPF Consig.', 'Contrato            ','cont la']]}')

            # Vamos remover os cont la que forem iguais ou maiores que 1
            averbados_cont_la_zero = averbados_sem_cancelamento.loc[averbados_sem_cancelamento['cont la'] == 0].copy()

            print(f"DEBUG: Tentando salvar AVERBADOS GOV MG")
            try:
                averbados_sem_cancelamento.to_excel(os.path.join(self.caminho, f"AVERBADOS GOV MG PMMG {self.convenio} {self.rubrica}.xlsx"), index=False)
            except Exception as e:
                print(f"DEBUG: ERRO AO SALVAR AVERBADOS GOV MG PMMG {self.convenio}: {e}")

            # print(averbados_cont_la_zero[['CPF Consig.', 'Contrato            ', 'cont la']])

            nova_coluna_data = trabalhado_mes_passado['DATA'].tolist() + averbados_cont_la_zero['DATA'].tolist()
            nova_coluna_masp = trabalhado_mes_passado['MASP'].tolist() + averbados_cont_la_zero['MASP     '].tolist()
            nova_coluna_CPF = trabalhado_mes_passado['CPF Consignado'].tolist() + averbados_cont_la_zero['CPF Consig.'].tolist()
            nova_coluna_nome = trabalhado_mes_passado['Nome Consignado'].tolist() + averbados_cont_la_zero['Nome Consignado                         '].tolist()
            nova_coluna_contrato_original = trabalhado_mes_passado['ContratoOriginal'].tolist() + averbados_cont_la_zero['Contrato            '].tolist()

            nova_planilha_data = pd.DataFrame(nova_coluna_data, columns=['DATA'])

            outras_colunas_data = trabalhado_mes_passado.drop(columns=['DATA'])

            nova_planilha_data.reset_index(drop=True, inplace=True)
            outras_colunas_data.reset_index(drop=True, inplace=True)

            trabalhado_mes_passado = pd.concat([nova_planilha_data, outras_colunas_data.reindex(nova_planilha_data.index)],
                                               axis=1)

            trabalhado_mes_passado['MASP'] = nova_coluna_masp

            trabalhado_mes_passado['CPF Consignado'] = nova_coluna_CPF

            trabalhado_mes_passado['Nome Consignado'] = nova_coluna_nome

            trabalhado_mes_passado['ContratoOriginal'] = nova_coluna_contrato_original

            try:
                trabalhado_mes_passado.to_excel(os.path.join(self.caminho, f"TRABALHADO MÊS PASSADO {self.convenio} {self.rubrica}.xlsx"), index=False)
                print(f"DEBUG: TRABALHADO MÊS PASSADO {self.convenio} salvo com sucesso!")
            except Exception as e:
                print(f"DEBUG: ERRO AO SALVAR TRABALHADO MÊS PASSADO {self.convenio}: {e}")

            # Faremos a mesma coisa para o cont la que são iguais ou maiores que 1
            averbados_cont_la_um = averbados_sem_cancelamento.loc[averbados_sem_cancelamento['cont la'] >= 1].copy()


            # Transforma as duas colunas em str
            averbados_cont_la_um['Contrato            '] = averbados_cont_la_um['Contrato            '].astype(str).str.strip()
            trabalhado_mes_passado['ContratoOriginal'] = trabalhado_mes_passado['ContratoOriginal'].astype(str)

            # Verifica quais contratos que permanecem iguais
            trabalhado_mes_passado['Contrato para copiar'] = trabalhado_mes_passado['ContratoOriginal']
            # print(trabalhado_mes_passado['Contrato para copiar'])

            '''print(f'Tipo da coluna Contrato para copiar: {trabalhado_mes_passado['Contrato para copiar'].loc[trabalhado_mes_passado['CPF Consignado'] == 99140187691]}')
            print(f'Tipo da coluna Contato do averbados_cont_la: {averbados_cont_la_um['Contrato            '].loc[averbados_cont_la_um['CPF Consig.'] == 99140187691]}')'''

            trabalhado_mes_passado['DATA'] = pd.to_datetime(trabalhado_mes_passado['DATA'], errors='coerce')
            trabalhado_mes_passado = trabalhado_mes_passado.sort_values(by='DATA', ascending=False)
            trabalhado_mes_passado = trabalhado_mes_passado.drop_duplicates(subset='ContratoOriginal', keep='first')
            trabalhado_mes_passado = trabalhado_mes_passado.drop_duplicates(subset='MASP', keep='first')


            averbados_cont_la_um['contratos passados'] = averbados_cont_la_um['Contrato            '].map(trabalhado_mes_passado.set_index('ContratoOriginal')['Contrato para copiar'])
            # print(averbados_cont_la_um)
            averbados_cont_la_um = averbados_cont_la_um.drop_duplicates(subset='CPF Consig.', keep='first')

            # FAZER NOVAMENTO O TRATAMENTO DO TRABALHADO COMO SE FOSSE UM NOVO EM FOLHA
            trabalhado_mes_atual = trabalhado_mes_passado[['DATA', 'MASP', 'CPF Consignado', 'Nome Consignado', 'ContratoOriginal']].copy()
            trabalhado_mes_atual['CPF Consignado'] = trabalhado_mes_atual['CPF Consignado'].fillna(0).astype(int)
            cpf_tratado = trabalhado_mes_atual['CPF Consignado'].astype(str).str.zfill(11).str.replace(
                r'(\d{3})(\d{3})(\d{3})(\d{2})', r'\1.\2.\3-\4', regex=True)

            trabalhado_mes_atual.insert(4, 'CPF Ponto e Traço', cpf_tratado, True)

            # -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=- UPDATE DOS CONTRATOS -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
            # Criar o "mapa" de busca a partir do df_B
            # (Transforma averbados_cont_la_um em um "dicionário": {CPF: Contrato})
            mapa_de_contratos = averbados_cont_la_um.set_index('CPF Consig.')['Contrato            ']

            # Use o .map() para criar uma coluna de "Novos Contratos"
            #    A coluna 'CPF' do df_A é usada como chave de busca no 'mapa'
            novos_contratos = trabalhado_mes_atual['CPF Consignado'].map(mapa_de_contratos)
            trabalhado_mes_atual = trabalhado_mes_atual.copy()

            # Atualize a coluna 'Contrato'
            # Use .fillna() para preencher os 'NaN' (vazios)
            # com os valores da coluna antiga ('df_A['Contrato']')
            trabalhado_mes_atual['ContratoOriginal'] = novos_contratos.fillna(trabalhado_mes_atual['ContratoOriginal'])
            # -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=


        elif self.rubrica == 'BENEFÍCIO':
            trabalhado_mes_passado.loc[
                ~trabalhado_mes_passado['ContratoOriginal'].astype(str).str.contains('/'),
                'ContratoOriginal'
            ] = trabalhado_mes_passado['ContratoOriginal'].astype(str).str[:9]

            # 1. Lista de colunas a verificar
            cols_contratos = ['ContratoOriginal'] + [col for col in trabalhado_mes_passado.columns if
                                                     str(col).startswith('Contrato')]
            
            # 2. SELEÇÃO CRUCIAL: Remove colunas com nomes duplicados da nossa lista de interesse
            # Isso garante que se houver dois "ContratoOriginal", apenas o primeiro será pego
            df_filtrado = trabalhado_mes_passado[cols_contratos]
            df_filtrado = df_filtrado.loc[:, ~df_filtrado.columns.duplicated()]
            
            
            cols = trabalhado_mes_passado[cols_contratos].columns
            dup_cols = cols[cols.duplicated()].unique()
            logging.error(f"Colunas duplicadas encontradas: {dup_cols}")

            # 2. Cria a lista unificada e limpa o ".0"
            lista_bloqueio = (
                df_filtrado
                .apply(lambda x: x.astype(str))  # Converte tudo para texto
                .stack()  # Empilha
                .unique()  # Remove duplicatas
            )

            # --- A CORREÇÃO MÁGICA AQUI ---
            # Transforma em Series para poder usar métodos de string (.str)
            lista_bloqueio = pd.Series(lista_bloqueio)

            # Remove o ".0" apenas se ele estiver no FINAL da string
            lista_bloqueio = lista_bloqueio.str.replace(r'\.0$', '', regex=True)

            # 3. Aplica o filtro
            beneficio_filter = ~front_trabalhado['Contrato'].astype(str).isin(lista_bloqueio)

            front_ben_filter = front_trabalhado[beneficio_filter].loc[front_trabalhado['CPF'] != '054.873.956-08']
            # print(front_ben_filter['Cliente'])
            '''print(f'Codigo_Credbase do front trabalhado \n{type(front_trabalhado.loc[0, "Contrato"])}')
            print(f'ContratoOriginal do trabalhado_mes_passado \n{type(trabalhado_mes_passado.loc[0, "ContratoOriginal"])}')

            print(f'São iguais? {front_trabalhado.loc[0, "Contrato"] == trabalhado_mes_passado.loc[0, "ContratoOriginal"]}')'''

            nova_coluna_data = trabalhado_mes_passado['DATA'].tolist() + front_ben_filter['Data Cessão'].tolist()
            nova_coluna_masp = trabalhado_mes_passado['MASP'].tolist() + front_ben_filter['Matricula'].tolist()
            nova_coluna_CPF = trabalhado_mes_passado['CPF Consignado'].tolist() + front_ben_filter[
                'CPF'].tolist()
            nova_coluna_nome = trabalhado_mes_passado['Nome Consignado'].tolist() + front_ben_filter[
                'Nome'].tolist()
            nova_coluna_contrato_original = trabalhado_mes_passado['ContratoOriginal'].tolist() + front_ben_filter[
                'Contrato'].tolist()
            nova_planilha_data = pd.DataFrame(nova_coluna_data, columns=['DATA'])

            outras_colunas_data = trabalhado_mes_passado.drop(columns=['DATA'])

            nova_planilha_data.reset_index(drop=True, inplace=True)
            outras_colunas_data.reset_index(drop=True, inplace=True)

            trabalhado_mes_passado = pd.concat(
                [nova_planilha_data, outras_colunas_data.reindex(nova_planilha_data.index)], axis=1)

            trabalhado_mes_passado['MASP'] = nova_coluna_masp

            trabalhado_mes_passado['CPF Consignado'] = nova_coluna_CPF
            trabalhado_mes_passado['CPF Consignado'] = trabalhado_mes_passado['CPF Consignado'].replace(r"\D", "", regex=True)

            trabalhado_mes_passado['Nome Consignado'] = nova_coluna_nome

            trabalhado_mes_passado['ContratoOriginal'] = nova_coluna_contrato_original

            # FAZER NOVAMENTO O TRATAMENTO DO TRABALHADO COMO SE FOSSE UM NOVO EM FOLHA
            trabalhado_mes_atual = trabalhado_mes_passado[['DATA', 'MASP', 'CPF Consignado', 'Nome Consignado', 'ContratoOriginal']].copy()

            trabalhado_mes_atual['CPF Consignado'] = trabalhado_mes_atual['CPF Consignado'].fillna(0).astype(int)
            cpf_tratado = trabalhado_mes_atual['CPF Consignado'].astype(str).str.zfill(11).str.replace(
                r'(\d{3})(\d{3})(\d{3})(\d{2})', r'\1.\2.\3-\4', regex=True)

            trabalhado_mes_atual.insert(4, 'CPF Ponto e Traço', cpf_tratado, True)

        # Vamos separar só os NaN
        # Aqui é feito o tratamento dos números de contrato
        trabalhado_mes_atual_tratado = self.trata_contratos(trabalhado_mes_atual, front)

        # Só por precaução transforma os Codigos Credbase de novo em string
        front_tudo['Contrato'] = front_tudo['Contrato'].astype(str)

        # Inserir colunas de esteira
        # 1. Encontra todas as colunas que batem com o padrão "Contrato [número]"
        # O regex r'^Contrato \d+$' significa:
        # ^          -> Começa com
        # Contrato   -> A palavra "Contrato"
        # \d+        -> Um ou mais dígitos
        # $          -> Termina aqui
        colunas_contrato = trabalhado_mes_atual_tratado.filter(regex=r'^Contrato \d+$').columns


        for col_contrato in colunas_contrato:

            # 3. Extrai o número do nome da coluna
            # Ex: "Contrato 1".split(' ') -> ["Contrato", "1"] -> [1] == "1"
            try:
                numero = col_contrato.split(' ')[1]

                # Monta o nome da nova coluna
                col_esteira = f'Esteira {numero}'

                # Verifica se há contratos duplicados
                duplicados = front_tudo[front_tudo.duplicated(subset=['Contrato'], keep=False)]
                if not duplicados.empty:
                    logging.warning(f"Atenção! Existem {len(duplicados)} contratos duplicados no Front que causarão erro no map.")
                    # print(duplicados['Contrato'].unique()) # Para ver quais são

                # Puxa as esteiras
                # Mantém apenas a primeira ocorrência de cada contrato
                front_unico = front_tudo.drop_duplicates(subset=['Contrato'])

                trabalhado_mes_atual_tratado[col_esteira] = trabalhado_mes_atual_tratado[col_contrato].map(
                    front_unico.set_index('Contrato')['Esteira']
                )


                # Cria a nova coluna no DataFrame
                #    (Aqui, estou preenchendo com pd.NA (nulo),
                #     mas você pode usar '' (vazio) ou 0 se preferir)
                if col_esteira not in trabalhado_mes_atual_tratado.columns:
                    trabalhado_mes_atual_tratado[col_esteira] = pd.NA



            except IndexError:
                # Caso de segurança, se a coluna for "Contrato" sem número
                print(f"Aviso: A coluna '{col_contrato}' não segue o padrão 'Contrato [número]'.")

        # PUXA TABELA
        # trabalhado_mes_atual_tratado['TABELA 1'] = trabalhado_mes_atual_tratado['Contrato 1'].map(front_unico.set_index('Contrato')['Tipo Conciliação'])
        trabalhado_mes_atual_tratado['TABELA 1'] = trabalhado_mes_atual_tratado['Contrato 1'].map(front_unico.set_index('Contrato')['Tipo Operacao'])

        # PUXA VALOR A LANÇAR
        for col in colunas_contrato:
            # Ex: "Contrato 1".split(' ') -> ["Contrato", "1"] -> [1] == "1"
            try:
                numero = col.split(' ')[1]

                # Monta o nome da nova coluna
                col_parcela = f'Parcela {numero}'

                # Puxa as esteiras
                front_trabalhado['Contrato'] = front_trabalhado['Contrato'].astype(str)
                trabalhado_mes_atual_tratado[col_parcela] = trabalhado_mes_atual_tratado[col].map(
                    front_trabalhado.set_index('Contrato')['Valor a lançar'])

                # Cria a nova coluna no DataFrame
                #    (Aqui, estou preenchendo com pd.NA (nulo),
                #     mas você pode usar '' (vazio) ou 0 se preferir)
                if col_parcela not in trabalhado_mes_atual_tratado.columns:
                    trabalhado_mes_atual_tratado[col_parcela] = pd.NA

            except IndexError:
                # Caso de segurança, se a coluna for "Contrato" sem número
                print(f"Aviso: A coluna '{col}' não segue o padrão 'Contrato [número]'."),

        # Orbitall
        orbital = self.trata_orbital(front, self.orbital)
        if orbital is not None:
            # 1. Mapeamento da coluna ORBITAL (já existente)
            trabalhado_mes_atual_tratado['ORBITAL'] = trabalhado_mes_atual_tratado["CPF Ponto e Traço"].map(
                orbital.set_index('CPF/CNPJ')['VALOR DESCONTO']
            )

            # 2. Filtra todas as colunas que começam com "Parcela "
            colunas_parcelas = trabalhado_mes_atual_tratado.filter(like='Parcela ')

            # NOVO PASSO: Adiciona a coluna 'ORBITAL' ao DataFrame de colunas para soma
            colunas_para_somar = colunas_parcelas.copy()  # Cria uma cópia para garantir a segurança

            # Verifica se 'ORBITAL' já existe antes de adicionar (apenas por garantia, embora o código garanta)
            if 'ORBITAL' in trabalhado_mes_atual_tratado.columns:
                # Usa .loc para garantir que a coluna seja adicionada
                colunas_para_somar.loc[:, 'ORBITAL'] = trabalhado_mes_atual_tratado['ORBITAL']

            # 3. Soma as colunas horizontalmente (axis=1)
            trabalhado_mes_atual_tratado['Valor a Lançar'] = colunas_para_somar.sum(axis=1)
        else:
            # Valor a lançar
            # 1. Filtra todas as colunas que começam com "Parcela "
            colunas_parcelas = trabalhado_mes_atual_tratado.filter(like='Parcela ')

            # 2. Soma essas colunas horizontalmente (axis=1) e cria a nova coluna
            trabalhado_mes_atual_tratado['Valor a Lançar'] = colunas_parcelas.sum(axis=1)

        try:
            trabalhado_mes_atual_tratado.to_excel(os.path.join(self.caminho, f"TRABALHADO MÊS ATUAL {self.convenio} {self.rubrica}.xlsx"), index=False)
        except Exception as e:
            print(f"DEBUG: ERRO AO SALVAR TRABALHADO MÊS ATUAL {self.convenio} {self.rubrica}: {e}")

    def main(self):

        # =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=- FLUXO PRINCIPAL -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= #

        front_preliminar = self.tratamento_front_preliminar()
        
        if front_preliminar is False:
            print("Erro: O tratamento preliminar do front retornou None. Verifique os logs anteriores para mais detalhes.")
            return

        front_trabalhado = self.tratamento_front()

        self.averbados_func(front_preliminar, self.trabalhado_anterior, self.complementares, front_trabalhado)



# É possível que para testes futuros eu precise desse ambiente de testes
r'''SERHA(r"P:\PESSOAL\VALIDAÇÃO DOS LANÇAMENTOS\2025\DEZEMBRO\GOV MG IPSEMG\RELATORIOS\RELATORIOS UNIFICADOS GOV MG IPSEMG 11-2025.csv",
      'GOV. MG',
      [r"P:\PESSOAL\VALIDAÇÃO DOS LANÇAMENTOS\2025\DEZEMBRO\GOV MG IPSEMG\RELATORIOS\CREDBASE AKRK GOV MG - IPSEMG 11.2025.csv",
                r"P:\PESSOAL\VALIDAÇÃO DOS LANÇAMENTOS\2025\DEZEMBRO\GOV MG IPSEMG\RELATORIOS\CREDBASE DIG GOV MG - IPSEMG 11.2025.csv"],
      r"P:\PESSOAL\VALIDAÇÃO DOS LANÇAMENTOS\2025\DEZEMBRO\GOV MG IPSEMG\RELATORIOS\RL167_v4 (1).csv",
      "CAPITAL",
      r"P:\PESSOAL\VALIDAÇÃO DOS LANÇAMENTOS\2025\DEZEMBRO\GOV MG IPSEMG\RELATORIOS\Conciliação-Governo de Minas Gerais- IPSEMG-102025.xlsx",
      r"P:\PESSOAL\VALIDAÇÃO DOS LANÇAMENTOS\2025\DEZEMBRO\GOV MG IPSEMG\RELATORIOS\TRABALHADO FUNÇÃO GOV MG IPSEMG 10.2025.xlsx",
    r"P:\PESSOAL\VALIDAÇÃO DOS LANÇAMENTOS\2025\DEZEMBRO\GOV MG IPSEMG\RELATORIOS\TRABALHADO BENEFICIO GOV MG IPSEMG 10.2025.xlsx",
      "BENEFÍCIO",
      r'P:\PESSOAL\VALIDAÇÃO DOS LANÇAMENTOS\2025\DEZEMBRO\GOV MG IPSEMG\TRABALHADOS\BENEFICIO',
      tutela=r"P:\PESSOAL\VALIDAÇÃO DOS LANÇAMENTOS\2025\DEZEMBRO\GOV MG IPSEMG\RELATORIOS\LIMINAR - GERAL.xlsx")'''
