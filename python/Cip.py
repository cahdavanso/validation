import pandas as pd
from thefuzz import fuzz
from datetime import datetime
from python.ESTEIRAS import load_esteiras
from python.trata_conciliacao import TRATA_CONCILIACAO
from python.TrataOrbital import TRATA_ORBITAL
from datetime import datetime
import openpyxl
import numpy as np
import os
import re

class CIP:
    def __init__(self, portal_file_list, convenio, front, caminho, funcao=None, conciliacao=None, kobraki=None, extra_judicial=None, tacs=None, orbital=None):
        self.averbados = portal_file_list

        self.convenio = convenio

        self.front= front

        # Funcao
        self.funcao = funcao if funcao is not None else None

        self.kobraki = kobraki if kobraki is not None else None

        self.extra_judicial = extra_judicial if extra_judicial is not None else None

        self.tacs = tacs if tacs is not None else None


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
        self.conciliacao.rename(columns={'RECEBIDO GERAL ': 'RECEBIDO GERAL'}, inplace=True)
        self.conciliacao.rename(columns={'TIPO OPERAÇÃO': 'PRODUTO', 'NOVO TIPO DE OPERAÇÃO': 'PRODUTO', 'PRODUTOS PELO D8': 'PRODUTO', 
                                         'PRODUTO D8': 'PRODUTO', 'PRODUTO PELO D8': 'PRODUTO', 'PRODUTO ATUALIZADO': 'PRODUTO'}, inplace=True)
        self.orbital = orbital

        self.caminho = caminho

        self.condicoes_1 = load_esteiras()


        self.criacao_xml()

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
            front_unif['Operação'] = front_unif['Operação'].fillna('') # -> Só para ter certeza que essa coluna está vazia da forma certa
            front_unif.loc[~front_unif['Tipo Operacao'].str.contains('EMPRESTIMO', na=False) & (front_unif['Operação'] == ''), 'Tipo Operacao'] = 'CARTAO BENEFICIO'

            front_unif['Orbital'] = front_unif['Orbital'].fillna("NAO")
            front_unif['Status'] = front_unif['Status'].fillna("INTEGRADO")
            front_unif['Acao Judicial'] = front_unif['Acao Judicial'].fillna("NAO")
            front_unif['Obito'] = front_unif['Obito'].fillna("NAO")
            front_unif['Consignataria'] = front_unif['Consignataria'].fillna('CAPITAL')
            


            print(f'FRONT UNIFICADO FINALZIN: {front_unif.tail()}')

            front_unif.to_excel(rf"{self.caminho}\Teste_front {self.convenio} CAPITAL {datetime.now().strftime("%m-%Y")}.xlsx", index=False)

            return front_unif


    def tratamento_front_preliminar(self):
        front_consig = self.unifica_front_funcao()

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

        
        # Adiciona só as esteiras que podem ser lançadas
        front_consig_esteiras = front_consig[front_consig['Esteira'].isin(self.condicoes_1)].copy()

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

        # Marca o que é Óbito
        # No caso de ação judicial estiver estiver SIM e NÃO ao invés de 1 e 0
        # front_consig_validado_termino['Obito'] = front_consig_validado_termino['Obito'].replace({'SIM': 1, 'NÃO': 0})
        # front_consig_validado_termino.loc[front_consig_validado_termino['Obito'] == 1, 'OBS'] = 'NÃO LANÇAR - ÓBITO'
 
        # Marca tudo que é orbital
        front_consig_validado_termino.loc[(front_consig_validado_termino['Orbital'].str.contains('SIM', na=False) & (front_consig_validado_termino['OBS'] == '')), 'OBS'] = 'NÃO LANÇAR - ORBITAL'

        # Marcar o que não é cartão Conciliação
        front_consig_validado_termino.loc[(~front_consig_validado_termino['Tipo Operacao'].str.contains('Cartão de Crédito|CARTAO DE CREDITO|CARTÃO DE CRÉDITO|CARTAO BENEFICIO', na=False)), 'OBS'] = 'NÃO LANÇAR - NÃO CARTÃO'

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
        front_consig_cartao_conciliacao = front_consig[front_consig['Tipo Operacao'].str.contains('Cartão de Crédito|CARTAO DE CREDITO|CARTAO BENEFICIO|CARTÃO DE CRÉDITO', na=False)].copy()

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

        # print(f'Contrato 301268942 no front no validacao_termino: {front_copy.loc[front_copy["Contrato"] == "301268942", "Prestacao"]}\n')
 

        # Valor que vai ser lançado
        # Substitui NaN em "Saldo" por um valor muito alto (para que "Parcela" seja escolhida)
        # front_copy['Saldo'] = front_copy['Saldo'].fillna(np.nan)
        # 1. Altera a coluna Saldo de verdade
        front_copy['Saldo'] = front_copy['Saldo'].fillna(-np.inf)

        # 2. Faz o cálculo (agora não precisa mais do fillna aqui dentro)
        valor_a_lancar = np.minimum(np.abs(front_copy['Saldo']), front_copy['Prestacao'])

        front_copy['Valor a lançar'] = valor_a_lancar

        # 3. Agora seu print vai mostrar -1000
        # print(front_copy.loc[front_copy["Contrato"] == "302298345", "Saldo"])

        return front_copy
    
    def busca_greedy_backtracking(self, alvo, itens, max_contratos=5):
        """
        Busca a combinação de contratos que resulte na menor diferença absoluta
        em relação ao valor alvo. Exige match exato (tolerância zero).
        """
        # Escala de centavos para evitar erros de float
        alvo_int = int(round(alvo * 100))
        
        opcoes = sorted([(c, int(round(v * 100))) for c, v in itens], 
                        key=lambda x: x[1], reverse=True)
        
        # Variáveis para rastrear a melhor aproximação
        self.melhor_resultado = None
        self.menor_delta = float('inf')

        def buscar(index_inicio, alvo_restante, caminho_atual):
            delta_atual = abs(alvo_restante)
            
            # Atualiza o recorde
            if delta_atual < self.menor_delta:
                self.menor_delta = delta_atual
                self.melhor_resultado = list(caminho_atual)
            
            # Match perfeito (Diferença exata de ZERO centavos)
            if delta_atual == 0:
                return True
                
            if len(caminho_atual) >= max_contratos:
                return False

            for i in range(index_inicio, len(opcoes)):
                contrato, valor = opcoes[i]
                
                # Poda lógica
                if valor > (alvo_restante + self.menor_delta):
                    continue
                
                caminho_atual.append((contrato, valor))
                if buscar(i + 1, alvo_restante - valor, caminho_atual):
                    return True
                caminho_atual.pop()
                
            return False

        buscar(0, alvo_int, [])
        
        # Só devolve a lista de contratos se a diferença for rigorosamente zero
        if self.menor_delta == 0:
            return [(c, v / 100) for c, v in self.melhor_resultado]
        
        # Se sobrou ou faltou qualquer centavo, rejeita a operação
        return None
    
    def processar_contratos_otimizado(self, df_andamento, df_front):
        # --- 1. Padronização ---
        print('PROCESSAR CONTRATOS OTIMIZADO ATIVADO')

        for df in [df_andamento, df_front]:
            # Garante colunas numéricas
            col_v = 'Valor da Parcela' if 'Valor da Parcela' in df.columns else 'Prestacao'
            if df[col_v].dtype != 'float64':
                df[col_v] = df[col_v].astype(str).str.replace(".", "").str.replace(",", ".")
                df[col_v] = pd.to_numeric(df[col_v], errors='coerce')
            df[col_v] = df[col_v].astype(float).round(2)

        # Identifica dinamicamente todas as colunas que começam com "Contrato Editado"
        colunas_editadas = [col for col in df_andamento.columns if str(col).startswith('Contrato Editado')]
        
        # Cria a lista de todas as colunas onde os contratos podem estar armazenados
        colunas_leitura = colunas_editadas.copy()
        if 'Número do Contrato' in df_andamento.columns:
            colunas_leitura.append('Número do Contrato')

        # Define a coluna de destino para gravar os resultados da busca (prioriza a primeira "Editada")
        col_destino = colunas_editadas[0] if colunas_editadas else 'Número do Contrato'
        df_andamento[col_destino] = df_andamento[col_destino].astype(object)
        
        # 2. Filtrar Front disponível
        ocupados = df_andamento['Número do Contrato'].dropna().unique()
        df_front_dispo = df_front[~df_front['Contrato'].astype(str).isin(map(str, ocupados))].copy()
        
        contratos_usados = set()

        # 3. Busca por Grupo (Backtracking por CPF)
        col_v = 'Valor da Parcela' if 'Valor da Parcela' in df_andamento.columns else 'Prestacao'

        # Calcula de forma dinâmica a soma de todas as colunas 'Valor_Unif_' já criadas por linha
        colunas_valores_unif = [col for col in df_andamento.columns if str(col).startswith('Valor_Unif_')]
        if colunas_valores_unif:
            soma_atual_unif = df_andamento[colunas_valores_unif].sum(axis=1).round(2)
        else:
            soma_atual_unif = pd.Series(0.0, index=df_andamento.index)

        # Define as duas regras de captura para o Pente Fino
        regra_vazio_absoluto = df_andamento[col_destino].isna() | (df_andamento[col_destino] == "")
        regra_incompleto = (~regra_vazio_absoluto) & (soma_atual_unif != df_andamento[col_v].round(2))

        # O DataFrame 'vazios' agora conterá tanto os casos sem nada quanto os casos incompletos
        vazios = df_andamento[regra_vazio_absoluto | regra_incompleto]

        # Debug rápido seguro
        # print(f"Contratos do CPF 311.970.528-44\n{df_andamento.loc[df_andamento['CPF'] == '311.970.528-44', col_destino]}")
        
        for cpf, grupo in vazios.groupby('CPF'):
            soma_alvo = round(grupo['Valor da Parcela'].sum(), 2)

            # --- BLOCO DE DEBUG E LIMPEZA CIRÚRGICA ---
            if cpf == '311.970.528-44': # <-- Substitua pelo CPF do cliente
                print(f"\n{'='*60}")
                print(f"🔬 DEBUG CPF: {cpf}")
                print(f"🎯 ALVO TOTAL: {soma_alvo} (O algoritmo tentará fechar esse valor do zero)")
                
                # 1. Apagamos as colunas Editadas desta linha específica no df_andamento
                for col in df_andamento.columns:
                    if str(col).startswith('Contrato Editado') or str(col).startswith('Valor_Unif'):
                        df_andamento.loc[grupo.index, col] = pd.NA
                
                # 2. Como apagamos da planilha, precisamos garantir que aquele contrato parcial 
                # (302157943) não fique preso na lista negra (contratos_usados) do código.
                contratos_deste_cliente = df_front[df_front['CPF'] == cpf]['Contrato'].astype(str).tolist()
                for c in contratos_deste_cliente:
                    contratos_usados.discard(c)
                    if c in contratos_usados:
                        contratos_usados.remove(c)
                        
                print(f"✅ Terreno limpo! Contratos do Front liberados para uso.")
                print(f"{'='*60}\n")
            # ------------------------------------------

            # --- ROTINA DE LIMPEZA PARA REPESCAGEM ---
            colunas_editadas_loc = [col for col in df_andamento.columns if str(col).startswith('Contrato Editado')]
            colunas_unif_loc = [col for col in df_andamento.columns if str(col).startswith('Valor_Unif_')]
            
            colunas_para_leitura = colunas_editadas_loc.copy()
            if 'Número do Contrato' in df_andamento.columns:
                colunas_para_leitura.append('Número do Contrato')
            
            valores_atuais_cpf = df_andamento.loc[grupo.index, colunas_para_leitura].astype(str).values.flatten()
            
            # (1/3) BLINDAGEM DO ASTYPE:
            contratos_para_libertar = set(pd.Series(valores_atuais_cpf).astype(str).str.split('/').explode().str.strip().unique())
            contratos_para_libertar -= {'nan', 'None', '', '<NA>'}
            
            for c in contratos_para_libertar:
                if c in contratos_usados:
                    contratos_usados.remove(c)
            
            colunas_para_resetar = colunas_editadas_loc + colunas_unif_loc
            if colunas_para_resetar:
                for col in colunas_para_resetar:
                    df_andamento.loc[grupo.index, col] = pd.NA
            # --------------------------------------------------------
            
            todos_valores = df_andamento[colunas_leitura].astype(str).values.flatten()

            # (2/3) BLINDAGEM DO ASTYPE APLICADA AQUI:
            contratos_usados_andamento = set(
                pd.Series(todos_valores)
                .astype(str)       # <-- A MÁGICA DE PROTEÇÃO ENTRA AQUI
                .str.split('/')    
                .explode()         
                .str.strip()       
                .unique()
            )
            contratos_usados_andamento -= {'nan', 'None', '', '<NA>'}

            valores_deste_cpf = df_andamento.loc[grupo.index, colunas_leitura].astype(str).values.flatten()
            
            # (3/3) BLINDAGEM DO ASTYPE APLICADA AQUI:
            contratos_deste_cpf = set(
                pd.Series(valores_deste_cpf)
                .astype(str)       # <-- E AQUI TAMBÉM
                .str.split('/')
                .explode()
                .str.strip()
                .unique()
            )
            
            lista_negra_filtrada = contratos_usados_andamento - contratos_deste_cpf

            possibilidades = df_front_dispo[
                (df_front_dispo['CPF'] == cpf) & 
                (~df_front_dispo['Contrato'].astype(str).isin(lista_negra_filtrada)) & 
                (~df_front_dispo['Contrato'].astype(str).isin(contratos_usados))
            ]

            if cpf == '311.970.528-44':
                df_front_cpf = df_front_dispo[df_front_dispo['CPF'] == cpf]
                print(f"Contratos do CPF: {cpf}\n{df_front_cpf['Contrato']} \nParcelas somadas do CPF: {cpf}: {df_front_cpf['Prestacao'].sum()}")
            
            if possibilidades.empty: continue

            # Joga só o que está nas esteiras corretas
            possibilidades = possibilidades[possibilidades['Esteira'].isin(self.condicoes_1)]
            
            lista_itens = list(possibilidades[['Contrato', 'Prestacao']].itertuples(index=False, name=None))
            
            resultado = self.busca_greedy_backtracking(soma_alvo, lista_itens)
            
            if resultado:
                for i, (contrato, valor) in enumerate(resultado):
                    col_contrato = f'Contrato Editado {i + 1}'
                    col_valor = f'Valor_Unif_{i + 1}'
                    
                    if col_contrato not in df_andamento.columns:
                        df_andamento[col_contrato] = ""
                    if col_valor not in df_andamento.columns:
                        df_andamento[col_valor] = pd.NA

                    df_andamento.loc[grupo.index, col_contrato] = contrato
                    df_andamento.loc[grupo.index, col_valor] = valor
                    
                    contratos_usados.add(contrato)

        # 4. Limpeza Final
        df_front_final = df_front_dispo[~df_front_dispo['Contrato'].isin(contratos_usados)]
        return df_andamento, df_front_final
    
    def extrair_contratos_simples(self, df_sujo: pd.DataFrame, df_limpo: pd.DataFrame) -> pd.DataFrame:
        print("Iniciando o processo de extração e unificação de contratos...")
        
        def limpar_contrato(texto: str) -> str:
            if not isinstance(texto, str):
                texto = str(texto)
            return re.sub(r'[^0-9a-zA-Z]', '', texto).replace(" ", "")
        
        # --- Passo 1: Preparar Mapas de Referência ---
        df_limpo['Contrato'] = df_limpo['Contrato'].astype(str).str.strip()
        
        if df_limpo['Prestacao'].dtype != 'float64':
            df_limpo['Prestacao'] = df_limpo['Prestacao'].astype(str).str.replace(".", "").str.replace(",", ".")
            df_limpo['Prestacao'] = pd.to_numeric(df_limpo['Prestacao'], errors='coerce')
        
        # Dicionário de contratos por CPF para busca rápida
        cpf_contratos = df_limpo.groupby('CPF')['Contrato'].apply(list).to_dict()

        # --- Passo 2: Lógica de Substituição na Própria String ---
        def processar_linha_unificada(row):
            cpf = row['CPF']
            texto_original = str(row['Número do Contrato']).strip()
            
            if not texto_original or texto_original.lower() == 'nan':
                return texto_original

            contratos_validos = cpf_contratos.get(cpf, [])
            if not contratos_validos:
                return texto_original

            # Dividimos a string pelo separador "/"
            partes_sujas = texto_original.split('/')
            resultados_finais = []
            LIMIAR_SEGURO = 97

            for parte in partes_sujas:
                parte_strip = parte.strip()
                parte_limpa = limpar_contrato(parte_strip)
                
                if not parte_limpa or len(parte_limpa) < 3:
                    resultados_finais.append(parte_strip) # Mantém o original se for irrelevante
                    continue

                melhor_match = None
                maior_score = 0

                for contrato_ref in contratos_validos:
                    alvo_limpo = limpar_contrato(contrato_ref)
                    
                    # Prioridade 1: Match exato de final (comum em contratos)
                    if alvo_limpo.endswith(parte_limpa) or parte_limpa.endswith(alvo_limpo):
                        score = 100
                    else:
                        # Prioridade 2: Fuzzy
                        score = max(fuzz.partial_ratio(parte_limpa, alvo_limpo), 
                                    fuzz.ratio(parte_limpa, alvo_limpo))

                    if score >= LIMIAR_SEGURO and score > maior_score:
                        maior_score = score
                        melhor_match = contrato_ref

                # Se achou um match melhor no Front, substitui. Senão, mantém a parte original.
                if melhor_match:
                    resultados_finais.append(melhor_match)
                else:
                    resultados_finais.append(parte_strip)

            # Une tudo de volta com "/"
            return "/".join(resultados_finais)

        # --- Passo 3: Aplicação Direta ---
        df_sujo['Número do Contrato'] = df_sujo['Número do Contrato'].astype(str).replace('nan', '')
        
        # Sobrescreve a coluna com os valores tratados
        df_sujo['Número do Contrato'] = df_sujo.apply(processar_linha_unificada, axis=1)

        # --- Salvar ---
        try:
            caminho_final = os.path.join(self.caminho, "Relatório Averbados Contratos tratamento simples.xlsx")
            df_sujo.to_excel(caminho_final, index=False)
            print(f"Arquivo salvo com sucesso em: {caminho_final}")
        except Exception as e:
            print(f"ERRO AO SALVAR: {e}")

        return df_sujo

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

            # --- Passo 2: Definir a função que será aplicada em cada linha ---
            
            # 1. Mapeia as colunas fonte (Número do Contrato + qualquer Contrato Editado que já exista)
            colunas_fonte = ['Número do Contrato'] + [col for col in df_sujo.columns if str(col).startswith('Contrato Editado')]

            def encontrar_contratos_na_linha(row):
                cpf = row['CPF']
                
                # 2. Em vez de ler só uma coluna, varremos todas as colunas fonte e juntamos o texto
                valores_sujos = []
                for col in colunas_fonte:
                    val = str(row[col]).strip()
                    if val.lower() not in ['nan', 'none', '']:
                        valores_sujos.append(val)
                
                # Junta tudo com um espaço (se tiver barras no meio, elas vão junto para serem fatiadas abaixo)
                texto_contratos_sujo = " ".join(valores_sujos)

                # Garante que as listas existam
                contratos_validos_para_cpf = cpf_contratos.get(cpf, [])
                operacoes_validas_para_cpf = cpf_operacao.get(cpf, [])

                if not contratos_validos_para_cpf or not texto_contratos_sujo:
                    return []

                # 3. DIVIDIR: A mesma lógica vai fatiar os espaços e as barras (/) de TODAS as colunas lidas
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

            # --- Passo 3: Aplicar a função e criar as novas colunas ---
            print("Analisando a Planilha e extraindo/separando os contratos...")
            
            # Aplica a nossa nova função que lê e consolida todas as colunas
            lista_de_contratos_encontrados = df_sujo.apply(encontrar_contratos_na_linha, axis=1)

            # Transforma a lista de resultados em Dataframe
            df_contratos_novos = pd.DataFrame(lista_de_contratos_encontrados.tolist(), index=df_sujo.index)
            df_contratos_novos.columns = [f'Contrato Editado {i + 1}' for i in df_contratos_novos.columns]

            # Agora sim é 100% seguro apagar as antigas, pois os dados delas já foram processados 
            # e estão salvos de forma fatiada e limpa dentro do 'df_contratos_novos'
            colunas_antigas_para_remover = [col for col in df_sujo.columns if str(col).startswith('Contrato Editado')]
            if colunas_antigas_para_remover:
                df_sujo = df_sujo.drop(columns=colunas_antigas_para_remover)

            # Cola as novas colunas organizadas no DataFrame original
            df_resultado = pd.concat([df_sujo, df_contratos_novos], axis=1)

            print("extrair_contratos_com_referencia: Salvando relatório de averbados com contratos tratados")
            try:
                df_resultado.to_excel(os.path.join(self.caminho, f"Relatório Averbados Contratos tratados.xlsx"), index=False)
            except Exception as e:
                print(f"DEBUG: ERRO AO SALVAR RELATÓRIO AVERBADO CONTRATOS TRATADOS: {e}")
                
            return df_resultado

    
    def adiciona_contratos_faltando(self, averbado_contratos_faltantes, front_semi):
        # 0. TRAVA DE SEGURANÇA: Remove colunas duplicadas que possam ter vindo de fora
        # Se você tinha um 'CPF' antigo e renomeou o Formatado para 'CPF', isso mantém só o correto
        averbado_contratos_faltantes = averbado_contratos_faltantes.loc[:, ~averbado_contratos_faltantes.columns.duplicated()]

        # 1. Preparação do DataFrame B 
        front_semi_base = front_semi[['CPF', 'Prestacao', 'Contrato']].drop_duplicates(subset=['CPF', 'Prestacao'])

        # Criamos as variações no B para "fingir" que o valor já tem o seguro embutido
        front_semi_exact = front_semi_base.copy()
        
        front_semi_plus20 = front_semi_base.copy()
        front_semi_plus20['Prestacao_Ajustada'] = front_semi_plus20['Prestacao'] + 20
        
        front_semi_plus40 = front_semi_base.copy()
        front_semi_plus40['Prestacao_Ajustada'] = front_semi_plus40['Prestacao'] + 40

        # =====================================================================
        # 3. Execução dos Merges no DataFrame A
        # =====================================================================
        if averbado_contratos_faltantes['Valor da Parcela'].dtype != 'float64':
            averbado_contratos_faltantes['Valor da Parcela'] = averbado_contratos_faltantes['Valor da Parcela'].astype(str).str.replace(".", "").str.replace(",", ".")
            averbado_contratos_faltantes['Valor da Parcela'] = pd.to_numeric(averbado_contratos_faltantes['Valor da Parcela'], errors='coerce')

        print(f'Tipo front_semi_exact :{front_semi_exact['Prestacao'].dtype}')
        print(f'Tipo averbado_contratos_faltantes :{averbado_contratos_faltantes['Valor da Parcela'].dtype}')

        # Primeiro merge: Match exato (valor igual)
        averbado_contratos_faltantes = averbado_contratos_faltantes.merge(
            front_semi_exact, 
            left_on=['CPF', 'Valor da Parcela'],   # Alterado para CPF
            right_on=['CPF', 'Prestacao'], 
            how='left'
        )

        # Preenchemos a coluna "Número do Contrato"
        averbado_contratos_faltantes['Número do Contrato'] = averbado_contratos_faltantes['Número do Contrato'].fillna(averbado_contratos_faltantes['Contrato'])
        
        # IMPORTANTE: Removi o 'CPF' do drop. Ele agora é a chave principal e não pode ser apagado!
        averbado_contratos_faltantes.drop(columns=['Prestacao', 'Contrato'], inplace=True)


        # Segundo merge: Caso de +20 reais
        averbado_contratos_faltantes = averbado_contratos_faltantes.merge(
            front_semi_plus20, 
            left_on=['CPF', 'Valor da Parcela'],   # Alterado para CPF
            right_on=['CPF', 'Prestacao_Ajustada'], 
            how='left', 
            suffixes=('', '_20')
        )

        averbado_contratos_faltantes['Número do Contrato'] = averbado_contratos_faltantes['Número do Contrato'].fillna(averbado_contratos_faltantes['Contrato'])
        # Novamente, sem dar drop no CPF
        averbado_contratos_faltantes.drop(columns=['Prestacao', 'Contrato', 'Prestacao_Ajustada'], inplace=True)


        # Terceiro merge: Caso de +40 reais
        averbado_contratos_faltantes = averbado_contratos_faltantes.merge(
            front_semi_plus40, 
            left_on=['CPF', 'Valor da Parcela'],   # Alterado para CPF
            right_on=['CPF', 'Prestacao_Ajustada'], 
            how='left', 
            suffixes=('', '_40')
        )

        averbado_contratos_faltantes['Número do Contrato'] = averbado_contratos_faltantes['Número do Contrato'].fillna(averbado_contratos_faltantes['Contrato'])
        averbado_contratos_faltantes.drop(columns=['Prestacao', 'Contrato', 'Prestacao_Ajustada'], inplace=True)

        return averbado_contratos_faltantes

    def trata_averbacao(self):
        # PUXA OS ARQUIVOS À SEREM TRATADOS
        data = self.averbados
        # Cria coluna de CPF com ponto e traço
        cpf_tratado = data['CPF do Servidor'].astype(str).str.zfill(11).str.replace(r'(\d{3})(\d{3})(\d{3})(\d{2})',  r'\1.\2.\3-\4', regex=True)
        data.insert(1, 'CPF', cpf_tratado)

        front = self.tratamento_front_preliminar()
        front['Contrato'] = front['Contrato'].astype(str).str.strip()

        teste_conciliacao = TRATA_CONCILIACAO(self.conciliacao, self.kobraki, self.tacs, self.extra_judicial)
        # conciliacao_tratado = teste_conciliacao.trata_conciliacao()

        if front is False:
            print("trata_averbacao_1: O tratamento preliminar do front falhou. Verifique os erros anteriores.")
            return False

        print(f'Contrato 301268942 no front em trata_averbacao: {front.loc[front["Contrato"] == "301268942", "Prestacao"]}\n')

        convenio = self.convenio

        # PEGA APENAS AS COLUNAS NECESSÁRIAS DO ARQUIVO BRUTO
        # colunas = ['A D E', 'SERVIDOR', 'MATRÍCULA', 'CPF', 'Valor da Parcela', 'Número do Contrato']
        colunas = ['CONSIGNATÁRIA', 'PRODUTO','SERVIDOR', 'MATRÍCULA', 'CPF', 'Valor da Parcela', 'Número do Contrato']
        data_averbados_bruto = data.copy()

        data_averbados_bruto['Número do Contrato'] = data_averbados_bruto['Número do Contrato'].fillna('')
        data_averbados_bruto = data_averbados_bruto[data_averbados_bruto['Número do Contrato'] != '']

        semi_front = self.tratamento_front()
        if semi_front is False:
            print("trata_averbacao_2: O tratamento preliminar do front falhou. Verifique os erros anteriores.")
            return False
        
        data_averbados_bruto = self.adiciona_contratos_faltando(data_averbados_bruto, front)

        semi_front['Contrato'] = semi_front['Contrato'].astype(str).str.strip()

        # data_averbados = self.extrair_contratos_simples(data_averbados_bruto, semi_front)

        data_averbados, front_base = self.processar_contratos_otimizado(data_averbados_bruto, front)
        data_averbados = self.extrair_contratos_com_referencia(data_averbados, front)
        # Terceira passada
        data_averbados, front_base = self.processar_contratos_otimizado(data_averbados, front)
        data_averbados = self.extrair_contratos_com_referencia(data_averbados, front)

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
                semi_front.set_index('Contrato')['Valor a lançar'].to_dict()
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
            condicao_op_liq = data_averbados[f'OP LIQ {i}'] == 1

            # Ação: Nessas linhas, define o 'Valor_Unif' correspondente como 0
            # O operador | significa OU (se uma condição OU a outra for verdadeira)
            data_averbados.loc[(condicao_saldo_positivo | condicao_op_liq), f'Valor_Unif_{i}'] = 0
            # --- FIM DA NOVA LÓGICA ---

            # Condição de Operações Liquidadas, se a linha estiver preenchida vai lançar 0

        # --- 2.5 Puxa as liminares ---
        data_averbados["LIMINAR"] = data_averbados['CPF'].map(tutela.set_index('CPF')['Acao Judicial'].to_dict())
        condicao_liminar = data_averbados['LIMINAR'] == 1

        # --- 3. Soma todos os valores encontrados (forma eficiente) ---

        # Pega a lista de todas as colunas de valor que acabamos de criar
        colunas_valores_unificados = data_averbados.filter(like='Valor_Unif_')

        if colunas_valores_unificados is not None:
            if self.orbital is not None:
                # prepara_orbital = self.trata_orbital(front, trabalhado_mes_atual_tratado, self.orbital)
                prepara_orbital = TRATA_ORBITAL(orbital=self.orbital, front=front, convenio=self.convenio, caminho=self.caminho, averbado_final=data_averbados)
                orbital = prepara_orbital.orbital_tratado()
                # Vou tentar fazer somase de orbital
                somase_orbital = orbital.groupby('CPF/CNPJ')['VALOR DESCONTO'].sum().to_dict()

                # 1. Mapeamento da coluna ORBITAL (já existente)
                '''data_averbados['ORBITAL'] = data_averbados["CPF Ponto e Traço"].map(
                    orbital.set_index('CPF/CNPJ')['VALOR DESCONTO']
                )'''
                data_averbados['ORBITAL'] = data_averbados['CPF'].map(somase_orbital)
                # print(f'VALOR SOMASE DE 867.972.636-20\n{somase_orbital['867.972.636-20']}')
                # print(f"Somando os valores das colunas: {colunas_valores_unificados}")
                # Verifica se 'ORBITAL' já existe antes de adicionar (apenas por garantia, embora o código garanta)
                if 'ORBITAL' in data_averbados.columns:
                    # Usa .loc para garantir que a coluna seja adicionada
                    colunas_valores_unificados.loc[:, 'ORBITAL'] = data_averbados['ORBITAL']
                data_averbados['Soma'] = colunas_valores_unificados.sum(axis=1)
        else:
            print("Nenhuma coluna de valor encontrada. A coluna 'Soma' será inicializada com 0.")
            data_averbados['Soma'] = 0

        # --- 4. Cálculo da Diferença e Formatação Final ---

        # Garante que a coluna de Valor da Parcela é numérica antes do cálculo
        data_averbados['Valor da Parcela'] = pd.to_numeric(data_averbados['Valor da Parcela'], errors='coerce').fillna(0)

        data_averbados['Diff'] = data_averbados['Soma'] - data_averbados['Valor da Parcela']
        data_averbados['Diff'] = data_averbados['Diff'].round(2)

        data_averbados['Lançar'] = np.minimum(data_averbados['Soma'], data_averbados['Valor da Parcela'])
        data_averbados.loc[condicao_liminar, 'Lançar'] = 0

        # print("Cálculos de Soma e Diferença finalizados.")

        return data_averbados

    def arquivo_lancamento(self):
        # Cria o novo DataFrame
        data_averbados = self.trata_averbacao()
        front_trabalhado = self.tratamento_front()
        data_averbados.loc[data_averbados['Lançar'] < 5, 'Lançar'] = 0
        temp = data_averbados[data_averbados['Lançar'] != 0]
        colunas_alancar = ['CPF', 'Número da Averbação', 'Lançar', 'Número do Contrato']
        a_lancar = pd.DataFrame(temp[colunas_alancar])
        a_lancar = a_lancar.rename(columns={'Número da Averbação': 'Nº AVERBAÇÃO SCC', 'Lançar': 'VALOR AVERBADO', 'Número do Contrato': 'Nº CONTRATO'})


        # Calcule a SOMASE para cada categoria no Averbacoes Trabalhadas
        somas_por_categoria = data_averbados.groupby('CPF')['Lançar'].transform('sum')
        data_averbados['SOMASE'] = somas_por_categoria
        data_averbados['SOMASE'] = data_averbados['SOMASE'].astype(float)


        # Calcula o Somase Front para cada CPF no DataFrame de Averbados, usando o front_trabalhado como referência
        data_averbados['SOMASE FRONT'] = ''

        soma_condicional_dict_averb = front_trabalhado.groupby('CPF')['Valor a lançar'].sum().to_dict()
        data_averbados['SOMASE FRONT'] = data_averbados['CPF'].map(soma_condicional_dict_averb)

        
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
        soma_condicional_dict_front = data_averbados.groupby('CPF')['Lançar'].sum().to_dict()
        front_trabalhado['SOMASE AVERB'] = front_trabalhado['CPF'].map(soma_condicional_dict_front)
        front_trabalhado['DIFF'] = front_trabalhado['SOMASE FRONT'] - front_trabalhado['SOMASE AVERB'].astype(
            float)
    

        # Arredonda os números
        a_lancar['VALOR AVERBADO'] = a_lancar['VALOR AVERBADO'].astype(float)
        a_lancar['VALOR AVERBADO'] = a_lancar['VALOR AVERBADO'].map('{:.2f}'.format)
    
        # --- 1. data_averbados ---

        # SOMASE Interno (Averbados)
        # transform('sum') já mantém o índice alinhado, perfeito.
        data_averbados['SOMASE'] = data_averbados.groupby('CPF')['Lançar'].transform('sum').round(2)

        # SOMASE Externo (Vem do Front)
        soma_condicional_dict_averb = front_trabalhado.groupby('CPF')['Valor a lançar'].sum().to_dict()

        # Mapeia e já preenche com 0 quem não for encontrado (fillna)
        data_averbados['SOMASE FRONT'] = data_averbados['CPF'].map(soma_condicional_dict_averb).fillna(0).round(2)

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
        soma_condicional_dict_front = data_averbados.groupby('CPF')['Lançar'].sum().to_dict()

        # Cria a coluna SOMASE AVERB mapeando e preenchendo vazios com 0
        # Nota: Certifique-se que front_trabalhado['CPF'] e data_averbados['CPF'] são idênticos (pontos/traços)
        front_trabalhado['SOMASE AVERB'] = front_trabalhado['CPF'].map(soma_condicional_dict_front).fillna(0).round(2)
        # Cálculo do DIFF
        front_trabalhado['DIFF'] = front_trabalhado['SOMASE FRONT'] - front_trabalhado['SOMASE AVERB']
    
        # Cria o arquivo Averbações Trabalhadas
        file_name = f'TRABALHADO CARTÃO {self.convenio} CAPITAL {str(datetime.now().month).zfill(2)}-{datetime.now().year}.xlsx'
    
        # Salva o DataFrame no arquivo Excel
        print(f"arquivo_lancamento: Salvando o arquivo de Averbados Trabalhados")
        try:
            data_averbados.to_excel(os.path.join(self.caminho, file_name), index=False)
        except Exception as e:
            print(f"arquivo_lancamento: ERRO AO SALVAR TRABALHADO CARTÃO {self.convenio}: {e}")
    
        # Cria o arquivo Averbações a Lançar
        file_lancar = f'LANCAMENTO CARTÃO {self.convenio} CAPITAL {str(datetime.now().month).zfill(2)}-{datetime.now().year}.xlsx'
    
        # Salva o arquivo de lancamento
        print(f"arquivo_lancamento: Salvando o arquivo de Lançamento Cartão")
        try:
            a_lancar.to_excel(os.path.join(self.caminho, file_lancar), index=False)
        except Exception as e:
            print(f"arquivo_lancamento: ERRO AO SALVAR LANCAMENTO CARTÃO {self.convenio}: {e}")

        # Cria o Front Trabalhado
        file_front = f'FRONT TRABALHADO {self.convenio} CAPITAL {str(datetime.now().month).zfill(2)}-{datetime.now().year}.xlsx'
            
        print(f"arquivo_lancamento: Salvando o arquivo de Front Trabalhado")
        try:
            front_trabalhado.to_excel(os.path.join(self.caminho, file_front), index=False)
        except Exception as e:
            print(f"DEBUG: ERRO AO SALVAR FRONT TRABALHADO {self.convenio}: {e}")
        
        return a_lancar

    def criacao_xml(self):
        # 1. Carrega a sua planilha (ajuste o caminho e o nome da aba se necessário)
        # Dica: Ler o contrato como string ('str') evita que o Pandas transforme "599529" em "599529.0"
        arquivo_preparado = self.arquivo_lancamento()
        arquivo_preparado['Nº CONTRATO'] = arquivo_preparado['Nº CONTRATO'].astype(str)
        df = arquivo_preparado

        # 2. Configurações e Variáveis de Cabeçalho
        # Podemos automatizar as datas para o momento da geração
        agora = datetime.now()
        data_hora_arq = agora.strftime('%Y-%m-%dT%H:%M:%S')
        data_ref = agora.strftime('%Y-%m-%d')
        mes_ano_margem = agora.strftime('%m%Y') # Pode ser estático ou vir de uma variável (ex: agora.strftime('%m%Y'))

        # 3. Laço para montar os blocos repetitivos de cada contrato
        blocos_consignacao = ""

        for index, linha in df.iterrows():
            # Limpeza básica para garantir que não vão espaços em branco pro XML
            cpf = str(linha['CPF']).strip()
            averbacao = str(linha['Nº AVERBAÇÃO SCC']).strip()
            contrato = str(linha['Nº CONTRATO']).strip()
            
            # Formata o valor monetário para ter sempre 2 casas decimais e usar ponto (padrão XML/EUA)
            valor_averbado = f"{linha['VALOR AVERBADO']}"

            # Monta o "miolo" do XML para essa linha específica
            bloco = f"""            <Grupo_ASCC024_Consigrio>
                        <IdentdPartAdmdo>40083667</IdentdPartAdmdo>
                        <NumCtrlConsigrio>00001</NumCtrlConsigrio>
                        <CNPJBaseEnte>46379400</CNPJBaseEnte>
                        <NumConsigrioEnte>097340</NumConsigrioEnte>
                        <Grupo_ASCC024_Consignc>
                            <NumCPFServdr>{cpf}</NumCPFServdr>
                            <NUAvebcSCC>{averbacao}</NUAvebcSCC>
                            <MesAnoRefMarg>{mes_ano_margem}</MesAnoRefMarg>
                            <VlrFinlParclAvebc>{valor_averbado}</VlrFinlParclAvebc>
                            <NumContrto>{contrato}</NumContrto>
                        </Grupo_ASCC024_Consignc>
                    </Grupo_ASCC024_Consigrio>\n"""
                    
            # Adiciona esse bloco na nossa string acumuladora
            blocos_consignacao += bloco

        # 4. Monta o XML Final abraçando os blocos com o Cabeçalho e Rodapé
        # Nota: As chaves duplas {{ }} são usadas se você precisasse escapar chaves num f-string, 
        # mas aqui os dados entram direto nas tags.
        xml_completo = f"""<?xml version="1.0" encoding="utf-16BE"?>
        <ASCCDOC xmlns="http://www.cip-bancos.org.br/ARQ/ASCC024.xsd">
            <BCARQ>
                <NomArq>ASCC024_40083667_20260609_00001</NomArq>
                <NumCtrlEmis>00001</NumCtrlEmis>
                <ISPBEmissor>40083667</ISPBEmissor>
                <ISPBDestinatario>02992335</ISPBDestinatario>
                <DtHrArq>{data_hora_arq}</DtHrArq>
                <DtRef>{data_ref}</DtRef>
            </BCARQ>
            <SISARQ>
                <ASCC024>
        {blocos_consignacao}        </ASCC024>
            </SISARQ>
        </ASCCDOC>"""

        # 5. Salva o arquivo no disco
        # IMPORTANTE: Como o cabeçalho do XML exige "utf-16BE", devemos salvar exatamente com esse encoding no Python.
        with open("ASCC024_Gerado.xml", "w", encoding="utf-16-be") as arquivo_xml:
            arquivo_xml.write(xml_completo)

        print("Arquivo XML gerado com sucesso!")

