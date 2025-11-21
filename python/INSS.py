import pandas as pd
import numpy as np
from datetime import datetime
import warnings
import os

# Ignora avisos de versões futuras do Pandas para manter o log limpo
warnings.filterwarnings("ignore", category=FutureWarning)

class INSS:
    def __init__(self, portal_file_list, funcao, conciliacao, liquidados, caminho, tutela=None, orbital=None, casos_capital=None):
        
        # --- ADAPTAÇÃO: Recebendo DataFrames do server.py ---
        
        # Orbital
        self.orbital = orbital if orbital is not None else pd.DataFrame()
        
        # Função
        self.funcao_bruto = funcao if funcao is not None else pd.DataFrame()
        
        # Averbados (portal_file_list)
        self.averbados = portal_file_list if portal_file_list is not None else pd.DataFrame()
        
        # Casos Capital
        self.casos_capital = casos_capital if casos_capital is not None else pd.DataFrame()
        
        # Liquidados (Operações Liquidadas)
        self.op_liq = liquidados if liquidados is not None else pd.DataFrame()
        
        # Conciliação
        self.conciliacao = conciliacao if conciliacao is not None else pd.DataFrame()
        
        # Tutela (Liminar)
        self.tutela = tutela if tutela is not None else pd.DataFrame()
        
        self.caminho = caminho

        # Inicia o processamento
        if not self.funcao_bruto.empty:
            self.tratamento_funcao()
        else:
            print("ERRO: O arquivo 'FUNÇÃO' está vazio ou não foi enviado. O processamento não pode continuar.")

    def trata_conciliacao(self):
        conciliacao_tratado = self.conciliacao.copy()
        
        if conciliacao_tratado.empty:
            return pd.DataFrame()

        # Renomeia a primeira coluna para CONTRATOS
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
        conciliacao_tratado['PRESTAÇÃO'] = pd.to_numeric(conciliacao_tratado['PRESTAÇÃO'], errors='coerce').fillna(0)
        conciliacao_tratado['PRAZO'] = pd.to_numeric(conciliacao_tratado['PRAZO'], errors='coerce').fillna(0)
        conciliacao_tratado['RECEBIDO GERAL'] = pd.to_numeric(conciliacao_tratado['RECEBIDO GERAL'], errors='coerce').fillna(0)

        # Cálculos
        prestacao_vezes_prazo = conciliacao_tratado['PRESTAÇÃO'] * conciliacao_tratado['PRAZO']
        conciliacao_tratado['Pago'] = soma_d8 - prestacao_vezes_prazo
        conciliacao_tratado['Saldo'] = conciliacao_tratado['Pago'] + conciliacao_tratado['RECEBIDO GERAL']

        return conciliacao_tratado

    def tratamento_funcao(self):
        funcao = self.funcao_bruto.copy()

        # Normaliza nomes de colunas
        funcao.columns = funcao.columns.str.strip().str.replace('ï»¿', '')
        
        if 'NR_OPER' not in funcao.columns and 'ï»¿NR_OPER' in funcao.columns:
            funcao = funcao.rename(columns={'ï»¿NR_OPER': 'NR_OPER'})

        if 'NR_OPER' not in funcao.columns:
            print("ERRO CRÍTICO: Coluna NR_OPER não encontrada no arquivo Função.")
            return

        # Tratamento NR_OPER
        funcao['NR_OPER'] = funcao['NR_OPER'].astype(str)
        
        codigo_editado = funcao['NR_OPER'].replace(r"\D", "", regex=True)
        funcao.insert(1, 'NR_OPER_EDITADO', codigo_editado, True)
        funcao['NR_OPER_EDITADO'] = funcao['NR_OPER_EDITADO'].str.slice(0, 9)
        funcao['NR_OPER_EDITADO'] = funcao['NR_OPER_EDITADO'].astype(str)

        # Insere colunas vazias se não existirem
        cols_to_add = [
            'CASOS CAPITAL', 'OP_LIQ', 'CONTRATO CONCILIACAO', 'STATUS CONCILIACAO', 
            'LIMINAR', 'Saldo', 'SITUAÇÃO', 'Valor Averbado Reajustado'
        ]
        for col in cols_to_add:
            if col not in funcao.columns:
                funcao[col] = ''
                
        if 'Análise' not in funcao.columns:
            funcao.insert(2, 'Análise', '', True)

        funcao['Análise'] = funcao['Análise'].fillna('')
        funcao['SITUAÇÃO'] = funcao['SITUAÇÃO'].fillna('')

        # Tratamento VLR_PARC
        if 'VLR_PARC' in funcao.columns:
            funcao['VLR_PARC'] = funcao['VLR_PARC'].astype(str).str.replace('.', '', regex=False)
            funcao['VLR_PARC'] = funcao['VLR_PARC'].str.replace(',', '.', regex=False)
            funcao['VLR_PARC'] = pd.to_numeric(funcao['VLR_PARC'], errors='coerce').fillna(0)

        # OP LIQUIDADO
        if not self.op_liq.empty and 'Nº OPERAÇÃO' in self.op_liq.columns:
            self.op_liq['Nº OPERAÇÃO'] = self.op_liq['Nº OPERAÇÃO'].astype(str)
            funcao['OP_LIQ'] = funcao['NR_OPER'].map(
                self.op_liq.set_index('Nº OPERAÇÃO')['Número Operação'].to_dict() if 'Número Operação' in self.op_liq.columns else self.op_liq.set_index('Nº OPERAÇÃO').index.to_series().to_dict()
            )
        
        funcao['OP_LIQ'] = funcao['OP_LIQ'].fillna('')

        # Máscaras de Produto (Logica Original)
        mask_produto_orbital = (
                funcao['PRODUTO'].str.contains('000061 - CARTÃO PLÁSTICO', na=False)
                | funcao['PRODUTO'].str.contains('000094 - CARTÃO PLÁSTICO - RE', na=False)
                | funcao['PRODUTO'].str.contains('CARTÃ\x83O PLÃ\x81STICO - RE', na=False)
                | funcao['PRODUTO'].str.contains('000061 - CARTÃ\x83O PLÃ\x81STICO', na=False)
        )
        mask_produto_complementar = (
                funcao['PRODUTO'].str.contains('000012 - DIG INSS REP LEGAL', na=False)
                | funcao['PRODUTO'].str.contains('000015 - DIG INSS', na=False)
                | funcao['PRODUTO'].str.contains('000106 - CARTÃO TS', na=False)
                | funcao['PRODUTO'].str.contains('CARTÃ\x83O TS', na=False)
                | funcao['PRODUTO'].str.contains('000098 - DIG INSS 30%', na=False)
                | funcao['PRODUTO'].str.contains('000104 - CARTAO SEGURO - A VISTA', na=False)
                | funcao['PRODUTO'].str.contains('000105 - CARTAO - SEG PARC', na=False)
        )

        # CASOS CAPITAL
        if not self.casos_capital.empty and 'NR. OPER.' in self.casos_capital.columns:
            self.casos_capital['NR. OPER.'] = self.casos_capital['NR. OPER.'].astype(str)
            # Se não tiver a coluna 'Numero Operacao' explícita, usa o próprio 'NR. OPER.' como valor
            self.casos_capital['Numero Operacao'] = self.casos_capital['NR. OPER.']
            
            funcao['CASOS CAPITAL'] = funcao['NR_OPER'].map(
                self.casos_capital.set_index('NR. OPER.')['Numero Operacao'].to_dict()
            )
        funcao['CASOS CAPITAL'] = funcao['CASOS CAPITAL'].fillna('')

        # CONCILIAÇÃO
        conciliacao_tratado = self.trata_conciliacao()

        if not conciliacao_tratado.empty:
            # Criando DF auxiliar para mapeamento
            contratos_conciliacao = pd.DataFrame()
            contratos_conciliacao['CONTRATO'] = conciliacao_tratado['CONTRATOS']
            contratos_conciliacao['CONTRATO PUXAR'] = conciliacao_tratado['CONTRATOS'] # Para ter valor não nulo
            
            funcao['CONTRATO CONCILIACAO'] = funcao['NR_OPER_EDITADO'].map(
                contratos_conciliacao.set_index('CONTRATO')['CONTRATO PUXAR'].to_dict()
            )
            funcao['CONTRATO CONCILIACAO'] = funcao['CONTRATO CONCILIACAO'].fillna('')

            # Criar coluna auxiliar (1 = preenchido, 0 = vazio)
            funcao['has_conciliacao'] = funcao['CONTRATO CONCILIACAO'].notna() & (funcao['CONTRATO CONCILIACAO'] != '')

            # Ordenar
            funcao = funcao.sort_values(by="has_conciliacao", ascending=False).drop(columns="has_conciliacao")

            # Puxar status e saldo
            status_cols = conciliacao_tratado.filter(like='ST ')
            if not status_cols.empty:
                status_name = status_cols.columns[-1]
                funcao['STATUS CONCILIACAO'] = funcao['NR_OPER_EDITADO'].map(
                    conciliacao_tratado.set_index('CONTRATOS')[status_name].to_dict()
                )

            funcao['Saldo'] = funcao['NR_OPER_EDITADO'].map(
                conciliacao_tratado.set_index('CONTRATOS')['Saldo'].to_dict()
            )

        # Lógica de Análise
        def obs_situacao(row):
            situacao = str(row['SITUAÇÃO']).strip()
            if situacao not in ['0 - Ativo', 'Ativo', 'nan', '']:
                return f'NÃO - {situacao}'
            elif situacao in ['0 - Ativo', 'Ativo']:
                return 'LANÇAR'
            else:
                return row['Análise']

        if not self.averbados.empty:
            averbados = self.averbados.copy()
            if 'NR_OPER_EDITADO' in averbados.columns:
                averbados['NR_OPER_EDITADO'] = averbados['NR_OPER_EDITADO'].astype(str)
                
                if 'SITUAÇÃO' in averbados.columns:
                    funcao['SITUAÇÃO'] = funcao['NR_OPER_EDITADO'].map(averbados.set_index("NR_OPER_EDITADO")['SITUAÇÃO'].to_dict())
                
                if 'MARGEM REAJUSTADA' in averbados.columns:
                    funcao['Valor Averbado Reajustado'] = funcao['NR_OPER_EDITADO'].map(
                        averbados.set_index("NR_OPER_EDITADO")['MARGEM REAJUSTADA'].to_dict())

        funcao['Análise'] = funcao.apply(obs_situacao, axis=1)
        funcao['Análise'] = funcao['Análise'].replace('NÃO - nan', '')

        # LIMINAR
        if not self.tutela.empty and 'CPF' in self.tutela.columns:
            liminares = self.tutela
            mask_liminar = funcao['CPF'].isin(liminares['CPF'])
            if "CONTRATO" in liminares.columns:
                funcao['LIMINAR'] = funcao['CPF'].map(liminares.set_index("CPF")["CONTRATO"].to_dict())
            funcao.loc[mask_liminar, 'Análise'] = 'NÃO - LIMINAR'

        # Lógicas Finais de Análise
        condicao_liminar = (funcao['LIMINAR'].fillna('') == '')
        condicao_op_liq = (funcao['OP_LIQ'].fillna('') != '')
        funcao.loc[condicao_liminar & condicao_op_liq, 'Análise'] = 'NÃO - LIQUIDADO'

        funcao.loc[(funcao['Análise'] == '') & (funcao['CASOS CAPITAL'] != ''), 'Análise'] = 'NÃO LANÇAR - ENVIADO CAPITAL'

        mask_positivo = (pd.to_numeric(funcao['Saldo'], errors='coerce').fillna(-1) >= 0) & (funcao['NR_OPER'].str.startswith('600', na=False))
        funcao.loc[((funcao['LIMINAR'] == '') | (funcao['OP_LIQ'] == '')) & mask_positivo, 'Análise'] = "NÃO - SALDO"

        funcao.loc[((funcao['LIMINAR'] == '') | (funcao['OP_LIQ'] == '')) & mask_produto_orbital, 'Análise'] = 'NÃO LANÇAR - ORBITAL'
        
        funcao.loc[((funcao['LIMINAR'] == '') | (funcao['OP_LIQ'] == '')) & (funcao['Análise'] == '') & mask_produto_complementar, 'Análise'] = 'NÃO LANÇAR - COMPLEMENTAR'

        funcao.loc[funcao['Análise'] == '', 'Análise'] = 'NÃO LANÇAR - COMPLEMENTAR EXTRA'

        # Salva arquivos
        funcao.to_excel(os.path.join(self.caminho, 'FUNÇÃO INTERMEDIÁRIO.xlsx'), index=False)

        funcao_tratado = funcao[funcao['Análise'] == 'LANÇAR'].copy()
        
        valores_desejados = ['NÃO LANÇAR - COMPLEMENTAR', 'NÃO LANÇAR - COMPLEMENTAR EXTRA']
        funcao_complementos = funcao[funcao['Análise'].isin(valores_desejados)].copy()

        funcao_tratado.to_excel(os.path.join(self.caminho, 'FUNCAO COM NÃO.xlsx'), index=False)

        self.trata_funcao_final(funcao_tratado, funcao_complementos)

    def trata_funcao_final(self, funcao, funcao_complementos):
        complementares = funcao_complementos.copy()

        # Seleciona apenas colunas que existem no DF para evitar erro
        cols_target = ['NR_OPER', 'NR_OPER_EDITADO', 'Análise', 'CPF', 'MATRICULA','CLIENTE', 'DT_BASE',
                         'VLR_PARC', 'Saldo', 'SITUAÇÃO', 'Valor Averbado Reajustado', 'PRODUTO','ORIGEM_4']
        cols_existentes = [c for c in cols_target if c in funcao.columns]
        funcao = funcao[cols_existentes].copy()

        funcao["VLR_PARC_ORIGINAL"] = funcao["VLR_PARC"]
        funcao["VALOR_COMPLEMENTADO"] = 0.0
        funcao["STATUS_COMPLEMENTO"] = "" 
        funcao.insert(len(funcao.columns), "VALOR A LANÇAR", '')

        # Somas (com verificação se DFs não estão vazios)
        if not complementares.empty:
            soma_complementar = complementares.groupby('CPF')['VLR_PARC'].sum().reset_index(name="SOMA_COMPLEMENTAR")
        else:
            soma_complementar = pd.DataFrame(columns=['CPF', 'SOMA_COMPLEMENTAR'])

        if not self.orbital.empty:
            soma_orbital = self.orbital.groupby('CPF/CNPJ')['VALOR DESCONTO'].sum().reset_index(name="SOMA_ORBITAL")
            soma_orbital = soma_orbital.rename(columns={"CPF/CNPJ": "CPF"})
        else:
            soma_orbital = pd.DataFrame(columns=['CPF', 'SOMA_ORBITAL'])

        # Merge
        funcao_final = funcao.merge(soma_complementar, on="CPF", how="left")
        funcao_final = funcao_final.merge(soma_orbital, on="CPF", how="left")

        funcao_final["SOMA_COMPLEMENTAR"] = funcao_final["SOMA_COMPLEMENTAR"].fillna(0)
        funcao_final["SOMA_ORBITAL"] = funcao_final["SOMA_ORBITAL"].fillna(0)
        funcao_final["SOMA SOMASE"] = funcao_final["SOMA_COMPLEMENTAR"] + funcao_final["SOMA_ORBITAL"]

        funcao_final = funcao_final.drop(columns=["SOMA_COMPLEMENTAR", "SOMA_ORBITAL"])
        funcao = funcao_final

        # Conversão Numérica
        colunas_para_converter = ['Valor Averbado Reajustado', 'VLR_PARC']
        for coluna in colunas_para_converter:
            if coluna in funcao.columns:
                funcao[coluna] = pd.to_numeric(funcao[coluna], errors='coerce').fillna(0)

        # Lógica Vetorizada de Complemento
        funcao['ESPACO_PARA_COMPLEMENTO'] = (funcao['Valor Averbado Reajustado'] - funcao['VLR_PARC']).clip(lower=0)
        
        funcao['CUM_PEDIDO_COMPLEMENTO'] = funcao.groupby('CPF')['ESPACO_PARA_COMPLEMENTO'].cumsum()
        
        alocado_anteriormente = funcao['CUM_PEDIDO_COMPLEMENTO'] - funcao['ESPACO_PARA_COMPLEMENTO']
        
        saldo_restante_complemento = funcao['SOMA SOMASE'] - alocado_anteriormente
        
        funcao['COMPLEMENTO_REAL'] = np.minimum(funcao['ESPACO_PARA_COMPLEMENTO'], saldo_restante_complemento.clip(lower=0))
        
        funcao['PARCELA COMPLEMENTO REAL'] = funcao['VLR_PARC'] + funcao['COMPLEMENTO_REAL']
        
        funcao['VALOR A LANÇAR'] = np.minimum(funcao['PARCELA COMPLEMENTO REAL'], funcao['Valor Averbado Reajustado'])

        # Salva arquivo final
        funcao.to_excel(os.path.join(self.caminho, "LANÇAMENTO DE INSS TRATADO.xlsx"), index=False)

        self.arquivo_lancamento(funcao)

    def arquivo_lancamento(self, funcao_tratado):
        print('Preparando arquivo de lançamento...')
        
        if self.averbados.empty:
            print("Aviso: Arquivo Averbados vazio. Pulando geração de lançamento final.")
            return

        funcao = funcao_tratado.copy()
        averbados = self.averbados.copy()

        # Prepara chaves
        if 'NR_OPER' in funcao.columns:
            funcao['NR_OPER_CURTO'] = funcao['NR_OPER'].astype(str).str.slice(0, 9)
        else:
            funcao['NR_OPER_CURTO'] = ''
            
        if 'NR_OPER_EDITADO' in averbados.columns:
            averbados['NR_OPER_EDITADO'] = averbados['NR_OPER_EDITADO'].astype(str)

        # Verifica colunas necessárias no averbados
        cols_averbados = ['NR_OPER_EDITADO']
        if 'EMPREGADOR' in averbados.columns: cols_averbados.append('EMPREGADOR')
        else: averbados['EMPREGADOR'] = ''
        
        if 'MATRÍCULA' in averbados.columns: cols_averbados.append('MATRÍCULA')
        else: averbados['MATRÍCULA'] = ''

        df_final = pd.merge(
            left=funcao,
            right=averbados[cols_averbados],
            left_on='NR_OPER_CURTO',
            right_on='NR_OPER_EDITADO',
            how='left'
        )

        inclusao_desconto = df_final.rename(columns={
            'NR_OPER': 'NR. OPER.',
            'CPF': 'CPF',
            'CLIENTE': 'CLIENTE',
            'VALOR A LANÇAR': 'VLR.PARC',
            'EMPREGADOR': 'EMPREGADOR',
            'NR_OPER_CURTO': 'PROPOSTA',
            'MATRÍCULA': 'MATRICULA/BENEFÍCIO'
        })

        # Garante colunas finais
        for col in ['NR. OPER.', 'CPF', 'CLIENTE', 'VLR.PARC', 'EMPREGADOR', 'PROPOSTA', 'MATRICULA/BENEFÍCIO']:
            if col not in inclusao_desconto.columns:
                inclusao_desconto[col] = ''

        inclusao_desconto['VLR.PARC'] = inclusao_desconto['VLR.PARC'].astype(str).str.replace(',', '.', regex=False)
        # Converte para float seguro
        inclusao_desconto['VLR.PARC'] = pd.to_numeric(inclusao_desconto['VLR.PARC'], errors='coerce')
        
        inclusao_desconto['PRAZO'] = ''

        colunas_finais = ['NR. OPER.', 'CPF', 'CLIENTE', 'VLR.PARC', 'EMPREGADOR', 'PROPOSTA',
                          'MATRICULA/BENEFÍCIO', 'PRAZO']
        inclusao_desconto = inclusao_desconto[colunas_finais]

        timestamp = datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
        caminho_arquivo = os.path.join(self.caminho, f'INSS_INCLUIR_DESCONTO_CARTÃO_{timestamp}.xlsx')

        inclusao_desconto.to_excel(caminho_arquivo, index=False)
        print(f'Arquivo de lançamento salvo em: {caminho_arquivo}')