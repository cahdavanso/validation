import pandas as pd
import zipfile
import numpy as np
from python.ESTEIRAS import load_esteiras
from python.trata_conciliacao import TRATA_CONCILIACAO
from python.funcoes_comuns import UNIFICA_FRONT_FUNC_ESTEIRAS
from python.funcoes_comuns import limpar_moeda_universal
from python.TrataOrbital import TRATA_ORBITAL
from python.Tratador_Front_Base import TratadorValidacaoSimples
import re
from thefuzz import fuzz
from datetime import datetime
import os
import io
from io import StringIO
import openpyxl

class CONSIGNET:
    def __init__(self, portal_file_list, convenio, front, consignataria, caminho, andamento_funcao=None, funcao=None, conciliacao=None, recebimentos=None, desconto_inadimplencia=None, orbital=None):
        self.averbados = portal_file_list


        self.convenio = convenio

        self.front= front

        # Funcao
        self.funcao = funcao if funcao is not None else None

        self.andamento_funcao = andamento_funcao if andamento_funcao is not None else None

        self.recebimentos = recebimentos if recebimentos is not None else None

        self.desconto_inadimplencia = desconto_inadimplencia if desconto_inadimplencia is not None else None


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

        self.consignataria = consignataria

        self.condicoes_1 = load_esteiras()

        # 1. Instancia a classe
        unificador = UNIFICA_FRONT_FUNC_ESTEIRAS(
            front=self.front, 
            convenio=self.convenio, 
            consignataria=self.consignataria,
            funcao=self.funcao, 
            andamento_funcao=self.andamento_funcao,
            caminho=self.caminho
        )

        # 2. Chama a primeira unificação (Função pura)
        # Isso vai processar e preencher com verificar_ccb=True
        front_meio_caminho = unificador.unifica_front_funcao()

        # 3. Atualiza o front interno da classe para que a segunda unificação use os dados já combinados
        unificador.front = front_meio_caminho

        # 4. Chama a segunda unificação (Andamento Função)
        # Isso vai processar a segunda base com verificar_ccb=False
        self.front_final_consig = unificador.unifica_front_funcao_esteiras_andamento()
        self.front_final_consig.to_excel(os.path.join(self.caminho, f"FRONT FINAL CONSIG {self.convenio}.xlsx"), index=False)

        front_semi_trabalhado_preliminar = TratadorValidacaoSimples(front=self.front_final_consig, conciliacao=self.conciliacao, convenio=self.convenio,
                                                                    caminho=self.caminho, condicoes_1=self.condicoes_1, consignataria=self.consignataria,
                                                                    recebimentos=self.recebimentos, desconto_inadimplencia=desconto_inadimplencia)
        
        self.front_semi_trabalhado = front_semi_trabalhado_preliminar.tratamento_front_preliminar_base()
        self.front_trabalhado = self.front_semi_trabalhado[self.front_semi_trabalhado['OBS'].isin([pd.NA, np.nan, ''])]


        self.criacao_txt()

    def distribuicao_valores(self, averbado_trabalhado, front_trabalhar):
        # IMPORTANTE: Garanta que as colunas de valores são numéricas, não texto.
        # O .to_numeric(errors='coerce') converte o que for possível para número e põe NaN no que não for.
        averbado_novo = averbado_trabalhado
        cpf_tratado = averbado_novo['CPF'].astype(str).str.zfill(11).str.replace(r'(\d{3})(\d{3})(\d{3})(\d{2})',  r'\1.\2.\3-\4', regex=True)
        averbado_novo.insert(1, 'CPF Formatado', cpf_tratado)
        if self.orbital is not None:
            orbital_instancia = TRATA_ORBITAL(orbital=self.orbital, front=front_trabalhar, convenio=self.convenio, caminho=self.caminho)
            orbital_tratado = orbital_instancia.orbital_tratado()
            mask_orbital = orbital_tratado.groupby('CPF/CNPJ')['VALOR DESCONTO'].sum()
            averbado_novo['ORBITAL'] = ''
            averbado_novo['ORBITAL'] = averbado_novo['CPF Formatado'].map(mask_orbital)

        # Remoção de duplicatas por matrícula
        # averbado_novo.drop_duplicates(subset=['Matrícula'], keep='first', inplace=True)
        
        front_preliminar = front_trabalhar.copy()
        # Transforma vazios no OBS em aspas vazias
        front_preliminar['OBS'] = front_preliminar['OBS'].fillna('')
        front_preliminar = front_preliminar[front_preliminar['OBS'] == '']

        soma_series_averb = front_preliminar.groupby('CPF')['Valor a lançar'].sum()

        # 2. Agora o .add() vai funcionar, pois soma_series_averb ainda é um objeto Pandas
        # Supondo que mask_orbital também seja uma Series de CPFs e valores
        # soma_total = soma_series_averb.add(mask_orbital, fill_value=0)

        averbado_novo['Margem Solicitada'] = averbado_novo['Margem Solicitada'].apply(limpar_moeda_universal)

        '''if averbado_novo['Margem Solicitada'].dtype != 'float64':
            averbado_novo['Margem Solicitada'] = averbado_novo['Margem Solicitada'].astype(str).str.replace(".", "")
            averbado_novo['Margem Solicitada'] = averbado_novo['Margem Solicitada'].astype(str).str.replace(",", ".")
            averbado_novo['Margem Solicitada'] = pd.to_numeric(averbado_novo['Margem Solicitada'], errors='coerce').fillna(0)'''

        averbado_novo['SOMASE FRONT'] = averbado_novo['CPF Formatado'].map(soma_series_averb)
        averbado_novo['SOMASE FRONT'] = averbado_novo['SOMASE FRONT'].apply(limpar_moeda_universal)

        print(f'SOMASE FRONT (após mapeamento):\n{averbado_novo["SOMASE FRONT"]}')

        if 'ORBITAL' in averbado_novo.columns:
            # Usa .loc para garantir que a coluna seja adicionada
            averbado_novo['ORBITAL'] = averbado_novo['ORBITAL'].fillna(0)
            averbado_novo['SOMASE FRONT'] = averbado_novo['SOMASE FRONT'] + averbado_novo['ORBITAL']

        # NOTA: Como não há coluna de prioridade, a ordem de distribuição dependerá
        # da ordem atual do DataFrame. Se precisar de uma ordem específica,
        # um .sort_values() viria aqui.

        # 1. Calcula a soma ACUMULADA da reserva dentro de cada grupo de CPF.
        # Esta é a "mágica" que substitui a necessidade de um loop.
        averbado_novo['SOMA ACUMULADA DA RESERVA'] = averbado_novo.groupby('CPF Formatado')['Margem Solicitada'].cumsum()

        # 2. Calcula o valor que JÁ FOI ALOCADO para as linhas ANTERIORES.
        # É a soma acumulada até a linha atual, menos o valor da própria linha.
        alocado_anteriormente = averbado_novo['SOMA ACUMULADA DA RESERVA'] - averbado_novo['Margem Solicitada']
        averbado_novo['ALOCADO ANTERIORMENTE'] = alocado_anteriormente

        # 3. Calcula o saldo restante do SOMASE ANTES de processar a linha atual.
        saldo_restante = averbado_novo['SOMASE FRONT'] - alocado_anteriormente

        # 4. O valor a lançar é o MÍNIMO entre o que a reserva da linha pede e o saldo que ainda temos.
        # Usamos .clip(0) para garantir que o saldo não seja negativo (se já estourou, é 0).
        valor_a_lancar = np.minimum(averbado_novo['Margem Solicitada'], saldo_restante.clip(0))

        # 5. Atribui o resultado final arredondado às colunas.
        averbado_novo['Lançar'] = valor_a_lancar.round(2)

        # 6. Preenche a coluna OBS para linhas que não receberam nada.
        averbado_novo.loc[averbado_novo['Lançar'] == 0, 'OBS'] = 'NÃO'

        return averbado_novo

    def arquivo_lancamento(self):
        # Cria o novo DataFrame
        data_averbados = self.averbados
        # REMOVE AS LINHAS QUE CONTENHAM CANCELADA DA COLUNA Situação da Solicitação
        data_averbados = data_averbados[data_averbados['Situação da Solicitação'] != 'CANCELADA']

        data_averbados = self.distribuicao_valores(self.averbados, self.front_semi_trabalhado)
        # front_trabalhado = self.tratamento_front()
        front_trabalhado = self.front_trabalhado
        # data_averbados.loc[data_averbados['Lançar'] < 15, 'Lançar'] = 0

        data_averbados.insert(4,  'Código de Desconto', '4172')
        data_averbados.insert(5,  'Órgão', '1')
        data_averbados.insert(6,  'Prazo', '1')

        # Adiciona uma coluna de competência de mês corrente "mmAAAA"
        data_averbados['Competência'] = datetime.now().strftime('%m%Y')

        temp = data_averbados[data_averbados['Lançar'] != 0]
        colunas_alancar = ['Cod. Estabelecimento', 'Código de Desconto','Matrícula', 'Órgão', 'Prazo', 'Lançar', 'CPF', 'Competência']
        a_lancar = pd.DataFrame(temp[colunas_alancar])

        # Calcule a SOMASE para cada categoria no Averbacoes Trabalhadas
        somas_por_categoria = data_averbados.groupby('CPF')['Lançar'].transform('sum')
        data_averbados['SOMASE'] = somas_por_categoria
        data_averbados['SOMASE'] = data_averbados['SOMASE'].astype(float)

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
        a_lancar['Lançar'] = a_lancar['Lançar'].astype(float)
        a_lancar['Lançar'] = a_lancar['Lançar'].map('{:.2f}'.format)
    
        # --- 1. data_averbados ---

        # SOMASE Interno (Averbados)
        # transform('sum') já mantém o índice alinhado, perfeito.
        data_averbados['SOMASE'] = data_averbados.groupby('CPF')['Lançar'].transform('sum').round(2)

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

    def criacao_txt(self):
        # 1. Carrega a base processada pelo arquivo_lancamento
        # Nota: Certifique-se de que o seu método arquivo_lancamento() possui um 'return a_lancar' no final.
        arquivo_preparado = self.arquivo_lancamento()
        
        if arquivo_preparado is None or arquivo_preparado.empty:
            print("criacao_txt: Nenhum dado retornado para gerar o TXT.")
            return

        df = arquivo_preparado.copy()
        
        # 2. Tratamento e preenchimento com zeros à esquerda (zfill) conforme os tamanhos exigidos pelo layout:
        df['Cod. Estabelecimento'] = df['Cod. Estabelecimento'].astype(str).str.zfill(2)
        df['Código de Desconto'] = df['Código de Desconto'].astype(str).str.zfill(10)
        df['Matrícula'] = df['Matrícula'].astype(str).str.zfill(12)
        df['Órgão'] = df['Órgão'].astype(str).str.zfill(2)
        df['Prazo'] = df['Prazo'].astype(str).str.zfill(2)
        
        # Campo Lançar: converte para float, formata com 2 casas decimais e preenche até 15 caracteres
        df['Lançar'] = df['Lançar'].astype(float).map('{:.2f}'.format).str.zfill(15)
        
        df['CPF'] = df['CPF'].astype(str).str.zfill(11)
        df['Competência'] = df['Competência'].astype(str).str.zfill(6)

        # 3. Ordem exata das colunas para compor a linha posicional
        colunas_txt = [
            'Cod. Estabelecimento', 
            'Código de Desconto', 
            'Matrícula', 
            'Órgão', 
            'Prazo', 
            'Lançar', 
            'CPF', 
            'Competência'
        ]

        # 4. Concatena os campos de cada linha sem separadores
        linhas_txt = df[colunas_txt].agg(''.join, axis=1)

        # 5. Salva o arquivo .txt no diretório de saída
        nome_arquivo_txt = f"lancamento_{self.convenio}.txt"
        caminho_txt = os.path.join(self.caminho, nome_arquivo_txt)
        
        try:
            with open(caminho_txt, 'w', encoding='utf-8') as f:
                for linha in linhas_txt:
                    f.write(linha + '\n')
            print(f"criacao_txt: Arquivo TXT gerado com sucesso em {caminho_txt}")
        except Exception as e:
            print(f"criacao_txt: ERRO AO SALVAR TXT {self.convenio}: {e}")