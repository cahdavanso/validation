import pandas as pd
import numpy as np
from datetime import datetime
from python.TrataOrbital import TRATA_ORBITAL
from python.trata_conciliacao import TRATA_CONCILIACAO
from python.ESTEIRAS import load_esteiras
import warnings
import os

# Ignora avisos de versões futuras do Pandas para manter o log limpo
warnings.filterwarnings("ignore", category=FutureWarning)

class INSS:
    def __init__(self, portal_file_list, front, conciliacao, caminho, funcao=None, kobraki=None, tacs=None, casos_capital=None, orbital=None, d8=None):
        
        # --- ADAPTAÇÃO: Recebendo DataFrames do server.py ---
        
        # Averbados (portal_file_list)
        self.averbados = portal_file_list if portal_file_list is not None else pd.DataFrame()

        # Front
        self.front = front if front is not None else None
        
        # Casos Capital
        self.casos_capital = casos_capital if casos_capital is not None else None
        
        # Conciliação
        self.conciliacao = conciliacao if conciliacao is not None else pd.DataFrame()
        
        self.caminho = caminho

        self.funcao = funcao

        self.kobraki = kobraki

        self.tacs = tacs
        
        self.orbital = orbital

        self.d8 = d8

        self.trata_front_final()

    def trata_conciliacao(self):
        conciliacao_tratado = self.conciliacao.copy()
        
        if conciliacao_tratado.empty:
            return pd.DataFrame()

        # Renomeia a primeira coluna para CONTRATOS
        conciliacao_tratado.rename(columns={'RECEBIDO GERAL ': 'RECEBIDO GERAL'}, inplace=True)
        conciliacao_tratado.rename(columns={'NOVO TIPO DE OPERAÇÃO': 'PRODUTO', 'TIPO OPERAÇÃO': 'PRODUTO', 'PRODUTOS PELO D8': 'PRODUTO', 'PRODUTO ATUALIZADO': 'PRODUTO'}, inplace=True)
        conciliacao_tratado.rename(columns={conciliacao_tratado.columns[0]: 'CONTRATOS'}, inplace=True)
        
        # Padroniza colunas
        cols = list(conciliacao_tratado.columns)
        conciliacao_tratado.columns = cols
        
        conciliacao_tratado['CONTRATOS'] = conciliacao_tratado['CONTRATOS'].astype(str)
        conciliacao_tratado = conciliacao_tratado.drop_duplicates(subset='CONTRATOS')

        # Selecionar colunas com "d8" no nome (Regex)
        colunas_d8 = conciliacao_tratado.filter(regex=r'^(?!.*PRODUTO)D8').columns
        
        # Converte para numérico
        conciliacao_tratado[colunas_d8] = conciliacao_tratado[colunas_d8].apply(pd.to_numeric, errors='coerce')

        soma_d8 = conciliacao_tratado[colunas_d8].sum(axis=1)

        # Conversão segura para cálculos
        conciliacao_tratado['PMT'] = pd.to_numeric(conciliacao_tratado['PMT'], errors='coerce').fillna(0)
        conciliacao_tratado['PRAZO'] = pd.to_numeric(conciliacao_tratado['PRAZO'], errors='coerce').fillna(0)
        conciliacao_tratado['RECEBIDO GERAL'] = pd.to_numeric(conciliacao_tratado['RECEBIDO GERAL'], errors='coerce').fillna(0)

        # Cálculos
        prestacao_vezes_prazo = conciliacao_tratado['PMT'] * conciliacao_tratado['PRAZO']
        conciliacao_tratado['Pago'] = soma_d8 - prestacao_vezes_prazo
        conciliacao_tratado['Saldo'] = conciliacao_tratado['Pago'] + conciliacao_tratado['RECEBIDO GERAL']

        return conciliacao_tratado
    
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
        front_unif.loc[front_unif['Tipo Operacao'].str.contains('CARTÃO PLÁSTICO|CARTÃO PLÁSTICO - RE|CARTAO SEGURO - A VISTA|CARTAO - SEG PARC|' \
                                                                '000061 - CARTÃ\x83O PLÃ\x81STICO|CARTÃ\x83O PLÃ\x81STICO - RE'), 'Orbital'] = 'SIM'
        
        front_unif.loc[front_unif['Tipo Operacao'].str.contains('000012 - DIG INSS REP LEGAL|000015 - DIG INSS|000106 - CARTÃO TS|' \
                                                                'CARTÃ\x83O TS|000098 - DIG INSS 30%'), 'Tipo Operacao'] = 'CARTAO TS'


        # Altera para cartão
        # front_unif['Tipo Operacao'] = front_unif['Tipo Operacao'].fillna('') # -> Só para ter certeza que ele vai preencher corretamente nos vazios
        # front_unif.loc[~front_unif['Tipo Operacao'].str.contains('', na=False) & (front_unif['Operação'] == ''), 'Tipo Operacao'] = 'CARTAO DE CREDITO'

        front_unif['Orbital'] = front_unif['Orbital'].fillna("NAO")
        front_unif['Status'] = front_unif['Status'].fillna("INTEGRADO")
        front_unif['Acao Judicial'] = front_unif['Acao Judicial'].fillna("NAO")
        front_unif['Obito'] = front_unif['Obito'].fillna("NAO")
        front_unif['Consignataria'] = front_unif['Consignataria'].fillna("CAPITAL CONSIG")
        


        print(f'FRONT UNIFICADO FINALZIN:\n{front_unif.tail()}')

        front_unif.to_excel(rf"{self.caminho}\Teste_front INSS {"CAPITAL CONSIG"} {datetime.now().strftime("%m-%Y")}.xlsx", index=False)

        return front_unif
    
    def tratamento_front_preliminar(self):
        front_consig = self.unifica_front_funcao()
        orbital = self.orbital

        # Trasnforma Prestacao em numérico
        # front_consig['Prestacao'] = front_consig['Prestacao'].astype(str).str.replace('.', '', regex=False)
        front_consig.rename(columns={'Prestracao': 'Prestacao'}, inplace=True)
        front_consig['Prestacao'] = front_consig['Prestacao'].astype(str).str.replace(',', '.', regex=False)
        front_consig['Prestacao'] = pd.to_numeric(front_consig['Prestacao'], errors='coerce').fillna(0)

        conciliacao = self.conciliacao.copy()

        # Colocar traços nos contratos xxxxxxxxx-x
        contratos_com_traço = front_consig['CCB'].astype(str).str.zfill(10).str.slice(0, 9) + '-' + front_consig['CCB'].astype(str).str.zfill(10).str.slice(9, 10)

        # Insere as colunas vazias necessárias
        front_consig.insert(0, 'NR_OPER', contratos_com_traço,True)
        front_consig.insert(21, 'Saldo', '', True)
        front_consig.insert(22, 'Valor a lançar', '', True)
        front_consig.insert(23, 'Análise', '', True)

        print(f'Quais contratos estão atrelados ao CPF: 277.507.524-04? {self.averbados.loc[self.averbados['CPF'] == '277.507.524-04', 'NR_OPER_EDITADO']}')
        print(f'O Contrato 300119744 string está no Averbados? {300119744 in self.averbados['NR_OPER_EDITADO'].values}')
        print(f'O Contrato 300119744 inteiro está no Averbados? {'300119744' in self.averbados['NR_OPER_EDITADO'].values}')

        situacao_averbado_index = self.averbados.set_index('NR_OPER_EDITADO')['SITUAÇÃO'].copy()
        situacao_averbado_map = front_consig['Contrato'].map(situacao_averbado_index.to_dict())
        front_consig.insert(24, 'SITUAÇÃO', situacao_averbado_map, True)

        valor_reajustado_index = self.averbados.set_index('NR_OPER_EDITADO')['MARGEM REAJUSTADA'].copy()
        valor_reajustado = front_consig['Contrato'].map(valor_reajustado_index.to_dict())
        front_consig.insert(25, 'Valor Averbado Reajustado', valor_reajustado, True)

        print(f'Esteiras Únicas do front: {front_consig["Esteira"].unique()}')

        # Esteiras
        '''esteiras_permitidas = ['11 FORMALIZACAO', '09.0 PAGO', 'RISCO DA OPERACAO - OBITO', '14.0 RISCO DA OPERACAO - OBITO',
                               'RISCO DA OPERACAO-DEMAIS SITUACOES', '11.PROBLEMAS DE AVERBACAO', '10.7.0 INGRESSAR COM PROCESSO OU ACAO JURIDICO',
                               '07.1 \x96 QUITACAO \x96 PAGAMENTO AO CLIENTE', '10.7 CONTRATO NAO AVERBADO - AGUARDANDO RESOLUCAO', '11.2  DETERMINACAO JUDICIAL',
                               "15.0\tRISCO DA OPERACAO-DEMAIS SITUACOES", "11.1 CONTRATO FISICO ENVIADO AO BANCO", "07.0 QUITACAO \x96 ENVIO DE CESSAO",
                               "99 CARTAO UTILIZADO", "15.0 RISCO DA OPERACAO-DEMAIS SITUACOES"
                              ]'''
        
        esteiras_permitidas = load_esteiras()
        
        # Vamos renomear a primeira coluna da conciliação
        conciliacao.rename(columns={conciliacao.columns[0]: 'CONTRATOS'}, inplace=True)
        # Converte para lista de colunas
        cols = list(conciliacao.columns)

        # Atualiza o DataFrame com novos nomes
        conciliacao.columns = cols
        conciliacao['CONTRATOS'] = conciliacao['CONTRATOS'].astype('Int64')

        # Adiciona a coluna de tipo da Conciliação
        print(f'colunas de front consig: {front_consig.columns}')
        # Adiciona só as esteiras que podem ser lançadas
        # front_consig_esteiras = front_consig[front_consig['dsEsteira'].isin(esteiras_permitidas)].copy()

        # Substituir contratos que tem menos de 9 dígitos por contratos CCB pegando os primeiros 9 dígitos
        front_consig['Contrato'] = front_consig['Contrato'].astype(str)
        front_consig.loc[front_consig['Contrato'].str.len() < 9, 'Contrato'] = front_consig['CCB'].astype(str).str.slice(0, 9)

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
            valores_encontrados_str = valores_encontrados # .astype(str)
            front_consig.loc[filtro_esteira, 'Prestacao'] = valores_encontrados_str 

        front_consig = front_consig[front_consig['Esteira'].isin(esteiras_permitidas)].copy()


        # -------------------------------- MARCAR TUDO QUE NÃO LANÇA ---------------------------------- #
        # Tira tudo que é excluído do arquivo de Averbação
        def obs_situacao(row):
            # 1. Pega o valor bruto primeiro
            valor_bruto = row['SITUAÇÃO']
            
            # 2. Verifica se é nulo (NaN) ANTES de converter para string
            if pd.isna(valor_bruto) or valor_bruto == '':
                return ''

            # 3. Agora sim converte para string com segurança
            situacao = str(valor_bruto).strip()
            
            # 4. Verifica se a string virou 'nan' ou 'None' por acidente na conversão
            if situacao.lower() in ['nan', 'none', '']:
                return ''

            # 5. Lógica de Negócio
            if situacao in ['0 - Ativo', 'Ativo']:
                return 'LANÇAR'
            else:
                return f'NÃO - {situacao}'
            
        front_consig['Análise'] = front_consig.apply(obs_situacao, axis=1)

        # Marca saldo positivo
        # conciliacao_tatado = self.trata_conciliacao()
        prepara_conciliacao = TRATA_CONCILIACAO(self.conciliacao, self.kobraki, self.tacs)
        conciliacao_tratado = prepara_conciliacao.trata_conciliacao()
        conciliacao_tratado['CONTRATOS'] = conciliacao_tratado['CONTRATOS'] # .astype('Int64')
        front_consig['Saldo'] = front_consig['Contrato'].map(conciliacao_tratado.set_index('CONTRATOS')['Saldo'].to_dict())
        front_consig_validado_termino = front_consig.copy()
        front_consig_validado_termino.loc[front_consig_validado_termino['Saldo'] > -0.01, 'Análise'] = 'NÃO LANÇAR - SALDO POSITIVO'
        # Valor que vai ser lançado
        # Substitui NaN em "Saldo" por um valor muito alto (para que "Parcela" seja escolhida)
        valor_a_lancar = np.minimum(np.abs(front_consig_validado_termino['Saldo']).fillna(float('inf')), front_consig_validado_termino['Prestacao'])

        front_consig_validado_termino['Valor a lançar'] = valor_a_lancar

        # Marca o que é Ação Judicial
        # No caso de Ação Judicial estiver estiver SIM e NÃO ao invés de 1 e 0
        front_consig_validado_termino['Acao Judicial'] = front_consig_validado_termino['Acao Judicial'].replace({'SIM': 1, 'NAO': 0})
        front_consig_validado_termino['Análise'] = front_consig_validado_termino['Análise'].fillna('')
        front_consig_validado_termino.loc[front_consig_validado_termino['Acao Judicial'] == 1, 'Análise'] = "NÃO LANÇAR - AÇÃO JUDICIAL"
        '''liminares = front_consig_validado_termino[front_consig_validado_termino['Acao Judicial'] == 1]
        mask_liminar = front_consig_validado_termino['CPF'].isin(liminares['CPF'])
        front_consig_validado_termino['LIMINAR'] = front_consig_validado_termino['CPF'].map(liminares.set_index("CPF")["Contrato"].to_dict())
        front_consig_validado_termino.loc[mask_liminar, 'Análise'] = "NÃO LANÇAR - AÇÃO JUDICIAL"'''


        # Marca o que é Obito
        # No caso de óbito estiver estiver SIM e NÃO ao invés de 1 e 0
        
        # front_consig_validado_termino['Obito'] = front_consig_validado_termino['Obito'].replace({'SIM': 1, 'NÃƒO': 0})
        # front_consig_validado_termino.loc[front_consig_validado_termino['Obito'] == 1, 'Análise'] = 'NÃO LANÇAR - ÓBITO'


        # Marca tudo que é orbital
        front_consig_validado_termino.loc[(front_consig_validado_termino['Orbital'].str.contains('SIM', na=False) & (front_consig_validado_termino['Análise'].isin(['', np.nan]))), 'Análise'] = 'NÃO LANÇAR - ORBITAL'
        
        # Marca Casos Patrick
        if not self.casos_capital is None:
            # print(f'casos capital:\n{self.casos_capital}')
            numero_operacao = self.casos_capital['NR. OPER.'].astype(str).str.slice(0, 9).tolist()
            self.casos_capital.insert(1, 'NR_OPER_EDITADO', numero_operacao, True)
            casos_capital_lista = self.casos_capital['NR_OPER_EDITADO'].astype(str).tolist()
            front_consig_validado_termino.loc[(front_consig_validado_termino['Contrato'].astype(str).str.slice(0, 9).isin(casos_capital_lista)), 'Análise'] = 'NÃO LANÇAR - CASOS PATRICK'

        # Marcar liquidados em StatusContrato
        front_consig_validado_termino.loc[(front_consig_validado_termino['Status'].str.contains('Liquidado|CANCELADO', na=False)), 'Análise'] = 'NÃO LANÇAR - LIQUIDADO'
        # Marca tudo que é Empréstimo
        # front_consig_validado_termino.loc[(front_consig_validado_termino['Tipo Operacao'].str.contains('EMPRÉSTIMO|EMPRESTIMO', na=False) & (front_consig_validado_termino['Análise'] == '')), 'Análise'] = 'NÃO LANÇAR - EMPRÉSTIMO'

        # Marca tudo que é Telesaque
        front_consig_validado_termino.loc[(front_consig_validado_termino['Tipo Operacao'].str.contains('CARTÃO TS|CARTAO TS', na=False) & (front_consig_validado_termino['Análise'] == '')), 'Análise'] = 'NÃO LANÇAR - TELESAQUE'
    
        # Marca "NÃO LANÇAR - COMPLEMENTAR" nas células vazias da coluna Análise onde veio vazio na coluna de SITUAÇÃO
        front_consig_validado_termino.loc[(front_consig_validado_termino['Análise'] == '') & (front_consig_validado_termino['SITUAÇÃO'].isna()), 'Análise'] = 'NÃO LANÇAR - COMPLEMENTAR'

        front_consig_validado_termino.to_excel(
            fr'{self.caminho}\FRONT SEMI TRABALHADO INSS.xlsx',
            index=False, 
        )

        return front_consig_validado_termino

    def front_trabalhado(self):
        front_trabalhado = self.tratamento_front_preliminar()

        # Renomear colunas
        front_trabalhado.rename(columns={'Contrato': 'NR_OPER_EDITADO', 'CPF': 'CPF', 'Matricula': 'MATRICULA', 'Nome': 'CLIENTE', 
                                         'Data Cessão': 'DT_BASE', 'Prestacao': 'VLR_PARC', 'Esteira': 'ESTEIRA','Tipo Operacao': 'PRODUTO', 'Convenio': 'ORIGEM_4'}, inplace=True)

        # Filtra só os que vão lançar
        front_trabalhado_lancar = front_trabalhado[front_trabalhado['Análise'] == 'LANÇAR'].copy()
        front_trabalhado_lancar.to_excel(
            fr'{self.caminho}\FRONT PARA LANÇAMENTO INSS.xlsx',
            index=False, 
        )

        # Cria arquivo de complementares + telesaque + orbital
        prepara_complementar_orbital = TRATA_ORBITAL(self.orbital, front_trabalhado, "INSS", self.caminho)
        # complementar_orbital_df = front_trabalhado[front_trabalhado['Análise'].str.contains('NÃO LANÇAR - COMPLEMENTAR|NÃO LANÇAR - TELESAQUE|NÃO LANÇAR - ORBITAL', na=False)].copy()
        complementar_orbital_df = prepara_complementar_orbital.orbital_tratado()
        complementar_orbital_df.to_excel(
            fr'{self.caminho}\FRONT COMPLEMENTARES TELESAQUE ORBITAL INSS.xlsx',
            index=False, 
        )

        return front_trabalhado_lancar, complementar_orbital_df

    def trata_front_final(self):
        front_trabalhado_lancar, complementar_orbital_df = self.front_trabalhado()

        # Separar as colunas necessárias
        front_trabalhado_lancar = front_trabalhado_lancar[['NR_OPER', 'NR_OPER_EDITADO', 'CPF', 'Análise', 'MATRICULA', 'CLIENTE', 'DT_BASE', 'VLR_PARC', 
                                                           'ESTEIRA', 'Saldo', 'SITUAÇÃO', 'Valor Averbado Reajustado', 'PRODUTO', 'ORIGEM_4']].copy()
        

        # Faz uma cópia do valor original, para controle
        front_trabalhado_lancar["VLR_PARC_ORIGINAL"] = front_trabalhado_lancar["VLR_PARC"]

        # Nova coluna para anotar quanto foi usado do "banco" de 30%
        front_trabalhado_lancar["VALOR_COMPLEMENTADO"] = 0.0
        front_trabalhado_lancar["STATUS_COMPLEMENTO"] = ""  # Total, Parcial, Nenhum
        front_trabalhado_lancar.insert(9, "VALOR A LANÇAR", '', True)

        # Soma dos valores de Complementar e Orbital
        soma_complementar = complementar_orbital_df.groupby('CPF/CNPJ')['VALOR DESCONTO'].sum().reset_index(name="SOMA_COMPLEMENTAR_ORBITAL")

        # Renomeia para ficar igual ao front_trabalhado_lancar
        soma_complementar.rename(columns={'CPF/CNPJ': 'CPF'}, inplace=True)

        # Junta os dados com a planilha principal
        front_final = front_trabalhado_lancar.merge(soma_complementar, on="CPF", how="left")

        # Preenche os NaN com zero (caso algum CPF não esteja em uma das duas planilhas)
        front_final["SOMA_COMPLEMENTAR_ORBITAL"] = front_final["SOMA_COMPLEMENTAR_ORBITAL"].fillna(0)

        # Calcula a soma total
        front_final["SOMA SOMASE"] = front_final["SOMA_COMPLEMENTAR_ORBITAL"]
        front_final["SOMA SOMASE"] = pd.to_numeric(front_final["SOMA SOMASE"], errors='coerce').fillna(0)

        # Remove colunas do Arquivo
        front_final = front_final.drop(columns=["SOMA_COMPLEMENTAR_ORBITAL"])

        front_trabalhado_lancar = front_final.copy()

        print(front_trabalhado_lancar[['Valor Averbado Reajustado', 'VLR_PARC']].dtypes)

        # 1. Converta as colunas para um formato numérico.
        #    Use os parâmetros 'decimal' e 'thousands' se seus dados usarem vírgula para decimal e ponto para milhar.
        #    'errors='coerce'' é muito útil: se ele não conseguir converter um valor, ele o transformará em NaN (nulo).

        colunas_para_converter = ['Valor Averbado Reajustado', 'VLR_PARC']
        for coluna in colunas_para_converter:
            # Ajuste os parâmetros decimal e milhar, conforme seus dados
            front_trabalhado_lancar[coluna] = pd.to_numeric(front_trabalhado_lancar[coluna], errors='coerce')

        # Preencha quaisquer valores que não puderam ser convertidos com 0 (ou outra estratégia que preferir)
        front_trabalhado_lancar[colunas_para_converter] = front_trabalhado_lancar[colunas_para_converter].fillna(0)

        # Calcula o "espaço" disponível em cada linha para receber um complemento.
        # .clip(0) garante que o resultado não seja negativo.
        front_trabalhado_lancar['ESPACO_PARA_COMPLEMENTO'] = (front_trabalhado_lancar['Valor Averbado Reajustado'] - front_trabalhado_lancar['VLR_PARC']).clip(0)
        print('Espaço Para Complemento, criado...\n\n')

        # a. Soma acumulada dos "pedidos" de complemento para cada CPF
        front_trabalhado_lancar['CUM_PEDIDO_COMPLEMENTO'] = front_trabalhado_lancar.groupby('CPF')['ESPACO_PARA_COMPLEMENTO'].cumsum()
        print('Espaço Para Complemento Acumulado, criado... \n\n')

        # b. Quanto já foi alocado para as linhas ANTERIORES do mesmo CPF
        alocado_anteriormente = front_trabalhado_lancar['CUM_PEDIDO_COMPLEMENTO'] - front_trabalhado_lancar['ESPACO_PARA_COMPLEMENTO']
        print('Acumulado Anteriormente, criado...\n\n')

        # c. Saldo restante do SOMA SOMASE disponível para a linha ATUAL
        saldo_restante_complemento = front_trabalhado_lancar['SOMA SOMASE'] - alocado_anteriormente
        print('Saldo Restante, calculado...\n\n')

        # d. O complemento REAL a ser adicionado é o MENOR entre o que a linha PODE RECEBER e o que nós TEMOS DE SALDO
        front_trabalhado_lancar['COMPLEMENTO_REAL'] = np.minimum(front_trabalhado_lancar['ESPACO_PARA_COMPLEMENTO'], saldo_restante_complemento.clip(0))
        print('Complemento Real, criado...\n\n')

        front_trabalhado_lancar['PARCELA COMPLEMENTO REAL'] = front_trabalhado_lancar['VLR_PARC'] + front_trabalhado_lancar['COMPLEMENTO_REAL']
        print('Parcela Complemento Real, calculado...\n\n')

        front_trabalhado_lancar['VALOR A LANÇAR'] = np.minimum(front_trabalhado_lancar['PARCELA COMPLEMENTO REAL'], front_trabalhado_lancar['Valor Averbado Reajustado'])
        print('Valor a Lançar, alocado...\n\n')

        print('Salvando Função tratado...')
        # Exporta os resultados
        front_trabalhado_lancar.to_excel(fr"{self.caminho}\LANÇAMENTO DE INSS TRATADO.xlsx", index=False)

        self.arquivo_lancamento(front_trabalhado_lancar)

    def trata_prazo_averb(self, averb_arrumar_prazo):
        d8_bruto = self.d8
        averbacao = averb_arrumar_prazo.copy()

        averbacao['NR_OPER_EDITADO'] = averbacao['NR_OPER_EDITADO'].astype(str)

        print(f'\nTipo da Averbacao: {averbacao['NR_OPER_EDITADO'].dtype}')
        print(f'Tipo do d8_bruto: {d8_bruto['NÚMERO DE CONTRATO TRATADO'].dtype}')

        # averbacao['NR_OPER_EDITADO'] = averbacao['NR_OPER_EDITADO'].astype(int)
        averbacao['PRAZO ÚLT. D8'] = averbacao['NR_OPER_EDITADO'].map(
            d8_bruto.set_index('NÚMERO DE CONTRATO TRATADO')['PRAZO MAIS ATUAL'])

        # Garante que as colunas são numéricas
        averbacao.loc[
            averbacao['PRAZO ATUAL'].isin(['NÃO TEM PRAZO', '']),
            'PRAZO ATUAL'
        ] = 0

        # Converte para numérico
        averbacao['PRAZO ATUAL'] = pd.to_numeric(
            averbacao['PRAZO ATUAL'], errors='coerce'
        )

        averbacao['PRAZO ÚLT. D8'] = pd.to_numeric(
            averbacao['PRAZO ÚLT. D8'], errors='coerce'
        )

        # Substitui PRAZO por ÚLT. PRAZO + 1 apenas onde ÚLT. PRAZO não é NaN
        averbacao.loc[averbacao['PRAZO ÚLT. D8'].notna(), 'PRAZO ATUAL'] = averbacao.loc[averbacao[
            'PRAZO ÚLT. D8'].notna(), 'PRAZO ÚLT. D8'] + 1

        averbacao.to_excel(fr'{self.caminho}\AVERBAÇÃO TESTE PRAZO D8.xlsx', index=False)

        return averbacao

    def arquivo_lancamento(self, funcao_tratado):
        """
            Versão refatorada da função, utilizando pd.merge para mais eficiência e legibilidade.
            """
        print('Preparando arquivo de lançamento...')

        # 1. Prepara os DataFrames para a junção (merge)
        funcao = funcao_tratado.copy()
        averbados = self.trata_prazo_averb(self.averbados)

        # Garante que as chaves de junção sejam do mesmo tipo (string)
        funcao['NR_OPER_CURTO'] = funcao['NR_OPER'].astype(str).str.slice(0, 9)
        averbados['NR_OPER_EDITADO'] = averbados['NR_OPER_EDITADO'].astype(str)

        # 2. Usa pd.merge para buscar 'EMPREGADOR' e 'MATRÍCULA' de uma só vez
        # Isso substitui todo o processo de .map()
        df_final = pd.merge(
            left=funcao,
            right=averbados[['NR_OPER_EDITADO', 'EMPREGADOR', 'MATRÍCULA', 'PRAZO ATUAL']],
            left_on='NR_OPER_CURTO',
            right_on='NR_OPER_EDITADO',
            how='left'  # 'left' garante que nenhuma linha de 'funcao' seja perdida
        )

        # 3. Cria o DataFrame de lançamento com os nomes de coluna corretos
        # Selecionando e renomeando as colunas necessárias em um único passo
        inclusao_desconto = df_final.rename(columns={
            'NR_OPER': 'NR. OPER.',
            'CPF': 'CPF',
            'CLIENTE': 'CLIENTE',
            'VALOR A LANÇAR': 'VLR.PARC',
            'EMPREGADOR': 'EMPREGADOR',
            'NR_OPER_CURTO': 'PROPOSTA',
            'MATRÍCULA': 'MATRICULA/BENEFÍCIO',
            'PRAZO ATUAL': 'PRAZO'
        })

        # 4. Ajusta os tipos de dados e valores finais
        inclusao_desconto['VLR.PARC'] = inclusao_desconto['VLR.PARC'].astype(str).str.replace(',', '.').astype(float)

        # 5. Seleciona apenas as colunas na ordem desejada
        colunas_finais = ['NR. OPER.', 'CPF', 'CLIENTE', 'VLR.PARC', 'EMPREGADOR', 'PROPOSTA',
                          'MATRICULA/BENEFÍCIO', 'PRAZO']
        inclusao_desconto = inclusao_desconto[colunas_finais]

        # 6. Gera o nome do arquivo com data e hora para evitar sobreposição
        timestamp = datetime.now().strftime("%d_%m_%Y_%H_%M")
        caminho_arquivo = fr'{self.caminho}\INSS_INCLUIR_DESCONTO_CARTÃO_{timestamp}.xlsx'

        inclusao_desconto.to_excel(caminho_arquivo, index=False)
        print(f'Arquivo de lançamento salvo em: {caminho_arquivo}')