import pandas as pd
import numpy as np
import os
from datetime import datetime
from python.trata_conciliacao import TRATA_CONCILIACAO
from python.Andamento import ANDAMENTO
from python.Andamento_GOVPB import ANDAMENTO_CODATA

class TratadorFrontBase:
    def __init__(self, front, conciliacao, convenio, caminho, orbital=None, condicoes_1=None, consignataria=None, rubrica=None, kobraki=None, tacs=None, extra_judicial=None, andamento=None):
        self.front = front.copy()
        self.conciliacao = conciliacao.copy()
        self.orbital = orbital
        self.convenio = convenio
        self.caminho = caminho
        self.condicoes_1 = condicoes_1 if condicoes_1 else []
        self.consignataria = consignataria
        self.rubrica = rubrica
        self.kobraki = kobraki
        self.tacs = tacs
        self.extra_judicial = extra_judicial
        self.andamento = andamento

    def preparar_colunas(self, df):
        """Insere as colunas padrão que todos os convênios utilizam"""
        colunas_necessarias = {
            21: 'Saldo',
            22: 'Valor a lançar',
            23: 'PRAZO',
            24: 'OBS'
        }
        for pos, col_name in colunas_necessarias.items():
            if col_name not in df.columns:
                df.insert(pos, col_name, '')
            else:
                df[col_name] = '' # Limpa caso já exista
        return df

    def estipula_prioridades(self, df):

        bancos_nao_lancar = ["OUTROS", "FUTURO"]
        
        # Ordenar as esteiras de A-Z
        # Puxa a lista de esteiras prioritárias
        esteiras_lancar = self.condicoes_1

        # 1. Ordem de prioridade para o Tipo de Operação
        # Mapeia cada variação possível para a sua prioridade
        ordem = {
            # Prioridade 1
            'CARTAO DE CREDITO': 1,
            'CARTÃO DE CRÉDITO': 1,
            'CARTAO CONSIGNADO': 1,
            'CARTÃO CONSIGNADO': 1,
            'CARTAO CONSIGNAD': 1,
            
            # Prioridade 2
            'CARTAO BENEFICIO': 2,
            'CARTÃO BENEFICIO': 2,
            'CARTÃO BENEFÍCIO': 2
        }

        df['prioridade_operacao'] = df['Tipo Operacao'].map(ordem).fillna(3)

        # 2. NOVA LÓGICA: Ordem de prioridade para a Esteira
        # Se a 'Esteira' atual estiver dentro da lista 'esteiras_lancar', recebe 1. Senão, recebe 2.

        df['prioridade_esteira'] = np.where(df['Esteira'].isin(esteiras_lancar), 1, 2)

        # 2.1 NOVA LÓGICA: Oridem de prioridade por Consignataria
        df['prioridade_banco'] = np.where(df['Consignataria'].isin(bancos_nao_lancar), 2, 1)

        # 3. Ordenação combinada
        # Ele vai ordenar primeiro pela Esteira, depois vai puxar as prioridade_operacao para cima, 
        # e por último vai desempatar por ordem alfabética da própria coluna 'Esteira'
        df = df.sort_values(
            by=['prioridade_esteira', 'prioridade_banco', 'prioridade_operacao', 'Esteira'],
            ascending=[True, True, True, True]
        )

        return df

    def normalizar_valores_prestacao(self, df):
        """Padroniza a coluna Prestacao para float64 (evitando o bug da vírgula da Orbital)"""
        if 'Prestacao' in df.columns and df['Prestacao'].dtype != "float64":
            df['Prestacao'] = df['Prestacao'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
            df['Prestacao'] = pd.to_numeric(df['Prestacao'], errors='coerce')
        return df

    def cruzar_tipo_conciliacao(self, df):
        """Puxa a coluna PRODUTO da conciliação e insere no Front"""
        self.conciliacao.rename(columns={self.conciliacao.columns[0]: 'CONTRATOS'}, inplace=True)
        self.conciliacao['CONTRATOS'] = self.conciliacao['CONTRATOS'].astype('Int64')

        try:
            tipo_conci = df['Contrato'].map(self.conciliacao.set_index('CONTRATOS')['PRODUTO'].to_dict())
            
            if 'Tipo Conciliação' in df.columns:
                df.drop(columns=['Tipo Conciliação'], inplace=True)
                
            df.insert(19, 'Tipo Conciliação', tipo_conci)
            
            # Padroniza nulos para o Tipo Operacao
            df['Tipo Conciliação'] = df['Tipo Conciliação'].astype(object)
            df.loc[df['Tipo Conciliação'].isin([np.nan, '', ' - ']), 'Tipo Conciliação'] = df['Tipo Operacao']
            
        except Exception as e:
            print(f'Aviso: Coluna PRODUTO não encontrada na conciliação. Erro: {e}')
            
        return df

    def tratar_orbital_generico(self, df):
        """Lógica padrão de cruzamento com a base Orbital"""
        if self.orbital is None:
            return df
            
        df['Contrato'] = df['Contrato'].astype(str).str.strip()
        orbital_df = self.orbital.copy()

        # Normaliza valores na orbital
        if orbital_df['VALID DESCONTO FINAL'].dtype != "float64":
            orbital_df['VALID DESCONTO FINAL'] = orbital_df['VALID DESCONTO FINAL'].astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
            orbital_df['VALID DESCONTO FINAL'] = pd.to_numeric(orbital_df['VALID DESCONTO FINAL'], errors='coerce')

        # Normaliza nome da coluna de contrato na orbital
        for col in orbital_df.columns:
            if "contrato" in col.lower():
                orbital_df.rename(columns={col: "CONTRATO"}, inplace=True)
                
        orbital_df['CONTRATO'] = orbital_df['CONTRATO'].astype(str).str.strip()

        # Mapeamento
        mapa_orbital = orbital_df.set_index('CONTRATO')['VALID DESCONTO FINAL']
        filtro_esteira = df['Esteira'] == '99 CARTAO UTILIZADO'
        
        valores_encontrados = df.loc[filtro_esteira, 'Contrato'].map(mapa_orbital).fillna(0)
        
        df.loc[filtro_esteira, 'Valor a lançar'] = valores_encontrados.astype(str)
        # Se precisar gravar na 'Valor a lançar' como string (como em ZETRA/NEOCONSIG), a classe filha sobrepõe depois.
        
        return df

    def aplicar_marcacoes_universais(self, df):
        """Aplica as regras de OBS (NÃO LANÇAR) que servem para absolutamente todos os bancos"""
        
        # Esteiras não permitidas
        if self.condicoes_1:
            df.loc[~df['Esteira'].isin(self.condicoes_1), 'OBS'] = 'NÃO LANÇAR - ESTEIRA NÃO PERMITIDA'

        # Saldo Positivo
        df = self.validacao_termino_front(df)
        print(f'tipo de OBS antes de marcar OBS: {df["OBS"].dtype}')
        df.loc[df['Saldo'] > -0.01, 'OBS'] = 'NÃO LANÇAR - SALDO POSITIVO'

        if self.extra_judicial is not None:
            # 1. Garante que as colunas das duas bases sejam tratadas como string para comparação exata
            contratos_df = df['Contrato'].astype(str)
            contratos_extra = self.extra_judicial['CONTRATO'].astype(str)
            
            # 2. Cria a máscara booleana (True se o contrato do df estiver na lista da extra_judicial)
            mask_extra_judicial = contratos_df.isin(contratos_extra)
            
            # 3. Aplica o valor 'EXTRA JUDICIAL' na coluna 'OBS' usando o .loc corretamente
            df.loc[mask_extra_judicial, 'OBS'] = 'EXTRA JUDICIAL'

            df['OBS'] = df['OBS'].fillna('')

        # Ação Judicial e Óbito
        if 'Acao Judicial' in df.columns:
            df['Acao Judicial'] = df['Acao Judicial'].replace({'SIM': 1, 'NAO': 0, 'NÃO': 0})
            df.loc[df['Acao Judicial'] == 1, 'OBS'] = 'NÃO LANÇAR - AÇÃO JUDICIAL'
            
        # Orbital
        if 'Orbital' in df.columns:
            df.loc[(df['Orbital'].str.contains('SIM', na=False) & (df['OBS'] == '')), 'OBS'] = 'NÃO LANÇAR - ORBITAL'
            
        # Liquidados
        if 'Status' in df.columns:
            df.loc[df['Status'].str.contains('Liquidado|CANCELADO', na=False), 'OBS'] = 'NÃO LANÇAR - LIQUIDADO'
            
        return df
    
    def validacao_termino_front(self, front):
        front_copy = front.copy()
        teste_conciliacao = TRATA_CONCILIACAO(self.conciliacao, self.kobraki, self.tacs)
        conciliacao_tratado = teste_conciliacao.trata_conciliacao()

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
        if front_copy['Prestacao'].dtype != 'float64':
            front_copy['Prestacao'] = front_copy['Prestacao'].astype(str).str.replace('.', '', regex=False)
            front_copy['Prestacao'] = front_copy['Prestacao'].str.replace(',', '.', regex=False)
            front_copy['Prestacao'] = pd.to_numeric(front_copy['Prestacao'], errors='coerce')

        # Valor que vai ser lançado
        # Substitui NaN em "Saldo" por um valor muito alto (para que "Parcela" seja escolhida)
        valor_a_lancar = np.minimum(np.abs(front_copy['Saldo']).fillna(float('inf')), front_copy['Prestacao'])

        front_copy['Valor a lançar'] = valor_a_lancar

        return front_copy

    # ==========================================
    # MÉTODOS "HOOKS" (Para as classes filhas)
    # ==========================================
    def aplicar_regras_especificas(self, df):
        """Sobrescrever na classe filha com regras de banco (ex: INSPFEM, Banco Outros)"""
        return df

    def escolhe_consignataria(self, df):
        # ------------------------------------- ESCOLHE CONSIGNATÁRIA -------------------------------------- #
        df['Consignataria'].fillna('', inplace=True)

        # Renomear nomes dos bancos no front porque estão vindo com 0 na frente
        df['Consignataria'] = df['Consignataria'].astype(str).str.replace("CAPITAL CONSIG ", "CAPITAL CONSIG")
        df['Consignataria'] = df['Consignataria'].astype(str).str.replace("CLICKBANK ", "CLICKBANK")
        df['Consignataria'] = df['Consignataria'].astype(str).str.replace("CIASPREV ", "CIASPREV")
        df['Consignataria'] = df['Consignataria'].astype(str).str.replace("HOJE PREVIDÊNCIA PRIVADA ", "HOJE PREVIDÊNCIA PRIVADA")

        if self.consignataria is not None:
            if self.consignataria == 'CIASPREV':
                df.loc[(df['Consignataria'] != 'CIASPREV') & (df['OBS'] == ''), 'OBS'] = 'NÃO LANÇAR - CONSIGNATÁRIA ERRADA'
            elif self.consignataria == 'HOJE PREVIDÊNCIA PRIVADA':
                df.loc[(df['Consignataria'] != 'HOJE PREVIDÊNCIA PRIVADA') & (df['OBS'] == ''), 'OBS'] = 'NÃO LANÇAR - CONSIGNATÁRIA ERRADA'
            elif self.consignataria == 'CAPITAL CONSIG':
                df.loc[(df['Consignataria'] != 'CAPITAL CONSIG') & (df['OBS'] == ''), 'OBS'] = 'NÃO LANÇAR - CONSIGNATÁRIA ERRADA'
            elif self.consignataria == 'CLICKBANK':
                df.loc[(df['Consignataria'] != 'CLICKBANK') & (df['OBS'] == ''), 'OBS'] = 'NÃO LANÇAR - CONSIGNATÁRIA ERRADA'
            elif self.consignatria == 'INSPFEM':
                df.loc[(df['Consignataria'] != 'INSPFEM') & (df['OBS'] == ''), 'OBS'] = 'NÃO LANÇAR - CONSIGNATÁRIA ERRADA'
            elif self.consignatria == 'CARTOS':
                df.loc[(df['Consignataria'] != 'CARTOS') & (df['OBS'] == ''), 'OBS'] = 'NÃO LANÇAR - CONSIGNATÁRIA ERRADA'
            elif self.consignatria == 'BEM CARTÕES':
                df.loc[(df['Consignataria'] != 'BEM CARTÕES') & (df['OBS'] == ''), 'OBS'] = 'NÃO LANÇAR - CONSIGNATÁRIA ERRADA'
            elif self.consignatria == 'ABCCARD CARTOES LTDA':
                df.loc[(df['Consignataria'] != 'ABCCARD CARTOES LTDA') & (df['OBS'] == ''), 'OBS'] = 'NÃO LANÇAR - CONSIGNATÁRIA ERRADA'
            elif self.consignatria == 'CLICK ON CONSIG':
                df.loc[(df['Consignataria'] != 'CLICK ON CONSIG') & (df['OBS'] == ''), 'OBS'] = 'NÃO LANÇAR - CONSIGNATÁRIA ERRADA'
            else:
                print('Consignatária inválida.')
                return

        return df

    # ==========================================
    # ORQUESTRADOR PRINCIPAL
    # ==========================================
    def tratamento_front_preliminar_base(self):
        """Executa a linha de montagem na ordem correta"""
        print(f"Iniciando tratamento preliminar unificado para {self.convenio}...")
        
        df = self.preparar_colunas(self.front)
        df = self.normalizar_valores_prestacao(df)
        # df = self.cruzar_tipo_conciliacao(df) # -> DESATIVADO ATÉ SEGUNDA ORDEM
        df = self.estipula_prioridades(df)
        df = self.escolhe_consignataria(df)
        df = self.tratar_orbital_generico(df)
        df = self.aplicar_marcacoes_universais(df)
        # df = self.calcular_saldo_e_termino(df)

        # Chama as funções específicas que a classe filha definir
        df = self.aplicar_regras_especificas(df)

        nome_convenio = self.convenio if self.convenio is not None else ''
        consignataria = self.consignataria if self.consignataria is not None else ''
        df.to_excel(os.path.join(self.caminho, f"FRONT SEMI TRABALHADO {nome_convenio} {consignataria} {datetime.now().strftime("%m-%Y")}.xlsx"), index=False)
        
        return df
    
# 1. Defina as Expressões Regulares no topo do arquivo para padronizar e evitar erros de digitação
REGEX_CARTAO_COMPLETO = 'Cartão de Crédito|CARTAO DE CREDITO|CARTÃO DE CRÉDITO|CARTÃO CONSIGNADO|CARTAO CONSIGNADO|CARTAO CONSIGNAD|CARTAO BENEFICIO'
REGEX_CARTAO_SIMPLES = 'Cartão de Crédito|CARTAO DE CREDITO|CARTÃO DE CRÉDITO|CARTÃO CONSIGNADO|CARTAO CONSIGNADO|CARTAO CONSIGNAD'
REGEX_BENEFICIO = 'CARTAO BENEFICIO'


class TratadorConsigfacil(TratadorFrontBase):
    def aplicar_regras_especificas(self, df):
        if self.convenio not in ['PREF. PALMAS']:
            df.loc[df['Tipo Operacao'].str.contains('ADIANTAMENTO SALARIAL', na=False), 'OBS'] = 'NÃO LANÇAR - ADIANTAMENTO SALARIAL'

        print(f'TratadorConsigfacil ativado')

        # Marca Prazo - Já está marcando "NÃO LANÇAR - PRAZO" dentro da função andamento_func_front
        objeto_andamento = ANDAMENTO(df, self.convenio, self.caminho, self.andamento) # if self.convenio != 'GOV. MATO GROSSO' else ANDAMENTO_PROVISORIO(self.front, self.convenio, self.caminho, self.andamento, self.funcao)
        df = objeto_andamento.andamento_func_front()
        # df['PRAZO'] = df['Contrato'].astype(str).map(df.set_index('Contrato')['PRAZO'])
        df['Contrato'] = df['Contrato'].astype('int64')
        # CORREÇÃO: Sem o "df = " antes do loc. E trocado pd.na por pd.NA (maiúsculo)
        if self.convenio in ['GOV. MARANHÃO']:
            df.loc[~df['PRAZO'].isin([pd.NA, np.nan, '', 0, '0', 1]), 'OBS'] = 'NÃO LANÇAR - PRAZO'
        else:
            df.loc[~df['PRAZO'].isin([pd.NA, np.nan, '', 0, '0']), 'OBS'] = 'NÃO LANÇAR - PRAZO'

        df.loc[(df['Consignataria'].str.contains('OUTROS|FUTURO', na=False)), 'OBS'] = 'NÃO LANÇAR - BANCO ERRADO'

        df.drop_duplicates(subset=['Contrato'], keep='first', inplace=True)
            
        return df

class TratadorCodata(TratadorFrontBase):
    def aplicar_regras_especificas(self, df):

        print(f'TratadorCodata ativado')

        # Marca Prazo - Já está marcando "NÃO LANÇAR - PRAZO" dentro da função andamento_func_front
        objeto_andamento = ANDAMENTO_CODATA(df, self.convenio, self.caminho, self.andamento) # if self.convenio != 'GOV. MATO GROSSO' else ANDAMENTO_PROVISORIO(self.front, self.convenio, self.caminho, self.andamento, self.funcao)
        df = objeto_andamento.andamento_func_front()
        # df['PRAZO'] = df['Contrato'].astype(str).map(df.set_index('Contrato')['PRAZO'])
        df['Contrato'] = df['Contrato'].astype('int64')
        # CORREÇÃO: Sem o "df = " antes do loc. E trocado pd.na por pd.NA (maiúsculo)

        df.loc[~df['PRAZO'].isin([pd.NA, np.nan, '']), 'OBS'] = 'NÃO LANÇAR - PRAZO'
            
        return df


class TratadorZetra(TratadorFrontBase):
    def aplicar_regras_especificas(self, df):
        convenios_bh = ['PREF. BELO HORIZONTE', 'PREF. CAMPINAS', 'GOV. PARANÁ', 'PREF. SOBRAL']
        
        # CORREÇÃO: Aspas consertadas no print
        print(f"Convenio é {self.convenio}")
        print(f"Convenio está no grupo BH/PR? {self.convenio in convenios_bh}")
        
        if self.convenio in convenios_bh:
            df.loc[(~df['Tipo Operacao'].str.contains(REGEX_CARTAO_COMPLETO, na=False)), 'OBS'] = 'NÃO LANÇAR - NÃO CARTÃO'
        else:
            df.loc[(~df['Tipo Operacao'].str.contains(REGEX_CARTAO_SIMPLES, na=False)), 'OBS'] = 'NÃO LANÇAR - NÃO CARTÃO'

        return df


class TratadorSerhaInfoconsig(TratadorFrontBase):
    """Classe unificada para Serha e Infoconsig, pois as regras são idênticas"""
    def aplicar_regras_especificas(self, df):
        if self.rubrica == 'CARTÃO' and self.convenio in ['PREF. PIRACICABA', 'PREV. PIRACICABA IPASP', 'SEMAE - SERVIÇO MUNICIPAL DE ÁGUA E ESGOTO DE PIRACICABA']:
            df.loc[(~df['Tipo Operacao'].str.contains('Cartão de Crédito|CARTAO DE CREDITO|CARTAO CONSIGNADO|CARTAO BENEFICIO', na=False) & (df['OBS'] == '')), 'OBS'] = 'NÃO LANÇAR - NÃO CARTÃO'
            pass
        elif self.rubrica == 'CARTÃO':
            df.loc[(~df['Tipo Operacao'].str.contains('Cartão de Crédito|CARTAO DE CREDITO|CARTAO CONSIGNADO', na=False) & (df['OBS'] == '')), 'OBS'] = 'NÃO LANÇAR - NÃO CARTÃO'
        else:
            # df.loc[(~df['Tipo Conciliação'].str.contains('CARTAO BENEFICIO', na=False) & (df['OBS'] == '')), 'OBS'] = 'NÃO LANÇAR - NÃO BENEFÍCIO'
            df.loc[(~df['Tipo Operacao'].str.contains('CARTAO BENEFICIO', na=False) & (df['OBS'] == '')), 'OBS'] = 'NÃO LANÇAR - NÃO BENEFÍCIO'

        return df


class TratadorValidacaoSimples(TratadorFrontBase):
    """
    Classe genérica para sistemas que apenas barram o que não é cartão.
    Substitui ConsigiKonexia, Cip e Quantum de uma vez só.
    """
    def aplicar_regras_especificas(self, df):
        df.loc[(~df['Tipo Operacao'].str.contains(REGEX_CARTAO_COMPLETO, na=False)), 'OBS'] = 'NÃO LANÇAR - NÃO CARTÃO'
        return df


class TratadorNeoconsig(TratadorFrontBase):
    def aplicar_regras_especificas(self, df):
        # A diferença do Neoconsig é que ele avalia o "Tipo Conciliação" em vez do "Tipo Operacao"
        df.loc[(~df['Tipo Operacao'].str.contains(REGEX_CARTAO_COMPLETO, na=False)), 'OBS'] = 'NÃO LANÇAR - NÃO CARTÃO'
        return df

class TratadorSigrh(TratadorFrontBase):

    def aplicar_regras_especificas(self, df):
        # TIRAR BANCO OUTROS, FUTURO, CIASPREV E HP
        df.loc[(df['Consignataria'].str.contains('OUTROS|FUTURO|CIASPREV|HOJE PREVIDÊNCIA PRIVADA', na=False)), 'OBS'] = 'NÃO LANÇAR - BANCO ERRADO'

        return df

class TratadorRF1(TratadorFrontBase):
    def aplicar_regras_especificas(self, df):
        if self.convenio not in ['PREF. PALMAS']:
            df.loc[df['Tipo Operacao'].str.contains('ADIANTAMENTO SALARIAL', na=False), 'OBS'] = 'NÃO LANÇAR - ADIANTAMENTO SALARIAL'

        print(f'TratadorConsigfacil ativado')

        df.loc[(~df['Tipo Operacao'].str.contains(REGEX_CARTAO_COMPLETO, na=False)), 'OBS'] = 'NÃO LANÇAR - NÃO CARTÃO'

        return df