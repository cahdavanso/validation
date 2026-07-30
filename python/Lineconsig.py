import pandas as pd
from thefuzz import fuzz
from datetime import datetime
from python.ESTEIRAS import load_esteiras
from python.TrataOrbital import TRATA_ORBITAL
from python.funcoes_comuns import UNIFICA_FRONT_FUNC_ESTEIRAS
from python.funcoes_comuns import TRATA_CONTRATOS
from python.Tratador_Front_Base import TratadorValidacaoSimples
import openpyxl
import numpy as np
import os
import re


class LINECONSIG:
    def __init__(self, portal_file_list, convenio, front, consignataria, caminho, andamento_funcao=None, funcao=None, conciliacao=None, kobraki=None, extra_judicial=None, tacs=None, orbital=None):

        self.averbados = portal_file_list

        self.convenio = convenio

        self.front= front

        # Funcao
        self.funcao = funcao if funcao is not None else None

        self.andamento_funcao = andamento_funcao if andamento_funcao is not None else None

        self.kobraki = kobraki if kobraki is not None else None

        self.extra_judicial = extra_judicial if extra_judicial is not None else None

        self.tacs = tacs if tacs is not None else None


        conciliacao_falso = pd.DataFrame(
            columns=['CONTRATOS', 'CPF', 'PRESTAÇÃO', 'PRAZO', 'PRODUTO','D8 JUN 25', 'ST JUL 25', 'RECEBIDO GERAL'])
        conciliacao_falso['CONTRATOS'] = 123
        conciliacao_falso['CPF'] = '123.456'
        conciliacao_falso['PRESTAÇÃO'] = 10
        conciliacao_falso['PRAZO'] = 96
        conciliacao_falso['PRODUTO'] = 'EMPRESTIMO'
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
                                                                    kobraki=self.kobraki, tacs=tacs)
        self.front_semi_trabalhado = front_semi_trabalhado_preliminar.tratamento_front_preliminar_base()
        self.front_trabalhado = self.front_semi_trabalhado[self.front_semi_trabalhado['OBS'].isin([pd.NA, np.nan, ''])]


        self.arquivo_lancamento()


    def trata_averbacao(self):
        # PUXA OS ARQUIVOS À SEREM TRATADOS
        data = self.averbados
        print(f'O que está no data:\n{data}')

        front = self.front_semi_trabalhado
        front['Contrato'] = front['Contrato'].astype(str).str.strip()


        if front is False:
            print("trata_averbacao_1: O tratamento preliminar do front falhou. Verifique os erros anteriores.")
            return False


        consig = self.consignataria
        convenio = self.convenio

        # PEGA APENAS AS COLUNAS NECESSÁRIAS DO ARQUIVO BRUTO
        # colunas = ['A D E', 'SERVIDOR', 'MATRÍCULA', 'CPF', 'CON_VLR_SOL', 'NRO. CGA']
        
        # 1. Remove os espaços invisíveis do começo e do fim de TODAS as colunas
        data.columns = data.columns.str.strip()

        # 3. O filtro vai funcionar perfeitamente
        data_averbados_bruto = data

        if data_averbados_bruto['VLR RESERVADO'].dtype != 'float64':
            data_averbados_bruto['VLR RESERVADO'] = data_averbados_bruto['VLR RESERVADO'].astype(str).str.replace('R$ ', '').str.replace('.', '').str.replace(',', '.')
            data_averbados_bruto['VLR RESERVADO'] = pd.to_numeric(data_averbados_bruto['VLR RESERVADO'], errors='coerce')

        # --- 3. Soma todos os valores encontrados (forma eficiente) ---


        prepara_data_averbados = TRATA_CONTRATOS(front_semi_trabalhado=self.front_semi_trabalhado, averbados=data_averbados_bruto, convenio=self.convenio,
                                                                 conciliacao_tratada=self.conciliacao, nome_coluna_cpf='CPF', nome_coluna_contrato='Nr CONTRATO',
                                                                 nome_coluna_parcela='VLR RESERVADO')
        data_averbados = prepara_data_averbados.trata_averbacao()

        # Passo 1: Garantir que a coluna é do tipo string
        cpf_str = data_averbados_bruto['CPF'].astype(str)
        cpf_str_ajustado = cpf_str.str.zfill(11)
        cpf_formatado = cpf_str_ajustado.str.slice(0, 3) + '.' + \
                        cpf_str_ajustado.str.slice(3, 6) + '.' + \
                        cpf_str_ajustado.str.slice(6, 9) + '-' + \
                        cpf_str_ajustado.str.slice(9, 11)

        data_averbados.insert(2, 'CPF_Formatado', cpf_formatado, True)

        if self.orbital is not None:
            preparando_orbital = TRATA_ORBITAL(self.orbital, front, self.convenio, self.caminho)
            orbital_tratado = preparando_orbital.orbital_tratado()
            
            # 1. Tratamento seguro das chaves antes do cruzamento
            orbital_tratado['VALOR DESCONTO'] = pd.to_numeric(orbital_tratado['VALOR DESCONTO'], errors='coerce')
            orbital_tratado['CPF/CNPJ'] = orbital_tratado['CPF/CNPJ'].astype(str)
            data_averbados['CPF_Formatado'] = data_averbados['CPF_Formatado'].astype(str)
            
            mask_orbital = orbital_tratado.groupby('CPF/CNPJ')['VALOR DESCONTO'].sum()
            
            # 2. Map e Fillna diretos
            data_averbados['ORBITAL'] = data_averbados['CPF_Formatado'].map(mask_orbital).fillna(0)

            # 3. Forma mais elegante de somar (Valor_Unif + ORBITAL)
            colunas_parcelas = data_averbados.filter(like='Valor_Unif')
            data_averbados['Soma'] = colunas_parcelas.sum(axis=1) + data_averbados['ORBITAL']

            print(f"trata_averbacao: Salvando arquivo de averbacao teste com orbital")
            try:
                data_averbados.to_excel(os.path.join(self.caminho, f"Averbacao com orbital teste {self.convenio}.xlsx"), index=False)
            except Exception as e:
                print(f"trata_averbacao: ERRO AO SALVAR AVERBAÇÃO COM ORBITAL TESTE: {e}")
                
        else:
            # 1. Filtra as parcelas e soma direto na própria variável bruto
            colunas_parcelas = data_averbados.filter(like='Valor_Unif')
            data_averbados['Soma'] = colunas_parcelas.sum(axis=1)

        # Pega a lista de todas as colunas de valor que acabamos de criar
        # colunas_valores_unificados = [col for col in data_averbados.columns if 'Valor_Unif_' in col]

        '''if colunas_valores_unificados:
            # print(f"Somando os valores das colunas: {colunas_valores_unificados}")
            data_averbados['Soma'] = data_averbados[colunas_valores_unificados].sum(axis=1)
        else:
            print("Nenhuma coluna de valor encontrada. A coluna 'Soma' será inicializada com 0.")
            data_averbados['Soma'] = 0'''

        # --- 4. Cálculo da Diferença e Formatação Final ---

        # Garante que a coluna de VALOR é numérica antes do cálculo
        data_averbados['VLR RESERVADO'] = pd.to_numeric(data_averbados['VLR RESERVADO'], errors='coerce').fillna(0)

        data_averbados['Diff'] = data_averbados['Soma'] - data_averbados['VLR RESERVADO']
        data_averbados['Diff'] = data_averbados['Diff'].round(2)

        # --- 5. Cria a coluna Lançar ---
        if consig == 'HOJE PREVIDÊNCIA PRIVADA':
            data_averbados = self.adiciona_peculio(data_averbados)
        else:
            data_averbados['Lançar'] = np.minimum(data_averbados['Soma'], data_averbados['VLR RESERVADO'])
            # data_averbados.loc[condicao_liminar, 'Lançar'] = 0

        # print("Cálculos de Soma e Diferença finalizados.")

        return data_averbados

    def arquivo_lancamento(self):
        # Cria o novo DataFrame
        data_averbados = self.trata_averbacao()
        front_trabalhado = self.front_trabalhado
        temp = data_averbados[data_averbados['Lançar'] != 0]
        colunas_alancar = ['MATRICULA','CPF', 'NOME', 'Lançar']
        a_lancar = pd.DataFrame(temp[colunas_alancar])
        a_lancar = a_lancar.rename(columns={'CPF': 'CPF', 'NOME': 'NOME', 'Lançar': 'Vlr parcela'})


        # Calcule a SOMASE para cada categoria no Averbacoes Trabalhadas
        somas_por_categoria = data_averbados.groupby('CPF')['Lançar'].transform('sum')
        data_averbados['SOMASE'] = somas_por_categoria
        data_averbados['SOMASE'] = data_averbados['SOMASE'].astype(float)


        # Calcula o Somase Front para cada CPF no DataFrame de Averbados, usando o front_trabalhado como referência
        data_averbados['SOMASE FRONT'] = ''

        soma_condicional_dict_averb = front_trabalhado.groupby('CPF')['Valor a lançar'].sum().to_dict()
        data_averbados['SOMASE FRONT'] = data_averbados['CPF_Formatado'].map(soma_condicional_dict_averb)

        
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
        soma_condicional_dict_front = data_averbados.groupby('CPF_Formatado')['Lançar'].sum().to_dict()
        front_trabalhado['SOMASE AVERB'] = front_trabalhado['CPF'].map(soma_condicional_dict_front)
        front_trabalhado['DIFF'] = front_trabalhado['SOMASE FRONT'] - front_trabalhado['SOMASE AVERB'].astype(
            float)
    

        # Arredonda os números
        a_lancar['Vlr parcela'] = a_lancar['Vlr parcela'].astype(float)
        a_lancar['Vlr parcela'] = a_lancar['Vlr parcela'].map('{:.2f}'.format)
        a_lancar['Vlr parcela'] = a_lancar['Vlr parcela'].astype(str).str.replace(".", "").str.replace(",", "")
        a_lancar['Vlr parcela'] = a_lancar['Vlr parcela'].astype(str).str.zfill(15)

        # Cria colunas no meio do Averbações a Lançar
        if self.convenio in ['PREF. SÃO JOSÉ DO RIO PRETO']:
            if datetime.now().month == 12 and datetime.now().day > 10:
                folha_inclusao = f'01{datetime.now().year + 1}'
            elif datetime.now().day < 10:
                folha_inclusao = f'{datetime.now().year}{str(datetime.now().month).zfill(2)}{datetime.now().day}'
            else:
                folha_inclusao = f'{datetime.now().year}{str(datetime.now().month + 1).zfill(2)}{datetime.now().day}'
        else:
            folha_inclusao = f'{datetime.now().year}{str(datetime.now().month).zfill(2)}{datetime.now().day}'

        # a_lancar['VLR RESERVADO'] =  a_lancar['VLR RESERVADO'].apply(substituir_virgula_por_ponto)
    
        # --- 1. data_averbados ---

        # SOMASE Interno (Averbados)
        # transform('sum') já mantém o índice alinhado, perfeito.
        data_averbados['SOMASE'] = data_averbados.groupby('CPF')['Lançar'].transform('sum').round(2)

        # SOMASE Externo (Vem do Front)
        '''soma_condicional_dict_averb = front_trabalhado.groupby('CPF_Formatado')['Valor a lançar'].sum().to_dict()

        # Mapeia e já preenche com 0 quem não for encontrado (fillna)
        data_averbados['SOMASE FRONT'] = data_averbados['CPF'].map(soma_condicional_dict_averb).fillna(0).round(2)'''

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
        if self.convenio in ['PREF. SÃO JOSÉ DO RIO PRETO']:
            if datetime.now().month == 12:
                if datetime.now().day > 10:
                    file_name = f'TRABALHADO CARTÃO {self.convenio} {self.consignataria} 01{datetime.now().year + 1}.xlsx'
                else:
                    file_name = f'TRABALHADO CARTÃO {self.convenio} {self.consignataria} {str(datetime.now().month).zfill(2)}-{datetime.now().year}.xlsx'
            else:
                if datetime.now().day > 10:
                    file_name = f'TRABALHADO CARTÃO {self.convenio} {self.consignataria} {str(datetime.now().month + 1).zfill(2)}-{datetime.now().year}.xlsx'
                else:
                    file_name = f'TRABALHADO CARTÃO {self.convenio} {self.consignataria} {str(datetime.now().month).zfill(2)}-{datetime.now().year}.xlsx'
        else:
            file_name = f'TRABALHADO CARTÃO {self.convenio} {self.consignataria} {str(datetime.now().month).zfill(2)}-{datetime.now().year}.xlsx'
    
        # Salva o DataFrame no arquivo Excel
        print(f"arquivo_lancamento: Salvando o arquivo de Averbados Trabalhados")
        try:
            data_averbados.to_excel(os.path.join(self.caminho, file_name), index=False)
        except Exception as e:
            print(f"arquivo_lancamento: ERRO AO SALVAR TRABALHADO CARTÃO {self.convenio}: {e}")
    
        # Cria o arquivo Averbações a Lançar
        if self.convenio in ['PREF. SÃO JOSÉ DO RIO PRETO']:
            if datetime.now().month == 12:
                if datetime.now().day > 10:
                    file_lancar = f'LANCAMENTO CARTAO {self.convenio} {self.consignataria} 01{datetime.now().year + 1}.xlsx'
                else:
                    file_lancar = f'LANCAMENTO CARTAO {self.convenio} {self.consignataria} {str(datetime.now().month).zfill(2)}-{datetime.now().year}.xlsx'
            else:
                if datetime.now().day > 10:
                    file_lancar = f'LANCAMENTO CARTAO {self.convenio} {self.consignataria} {str(datetime.now().month + 1).zfill(2)}-{datetime.now().year}.xlsx'
                else:
                    file_lancar = f'LANCAMENTO CARTAO {self.convenio} {self.consignataria} {str(datetime.now().month).zfill(2)}-{datetime.now().year}.xlsx'
        else:
            file_lancar = f'LANCAMENTO CARTÃO {self.convenio} {self.consignataria} {str(datetime.now().month).zfill(2)}-{datetime.now().year}.xlsx'
    
        # Salva o arquivo de lancamento
        print(f"arquivo_lancamento: Salvando o arquivo de Lançamento Cartão")
        try:
            a_lancar.to_excel(os.path.join(self.caminho, file_lancar), index=False)
        except Exception as e:
            print(f"arquivo_lancamento: ERRO AO SALVAR LANCAMENTO CARTÃO {self.convenio}: {e}")

        # Cria o Front Trabalhado
        if self.convenio in ['PREF. SÃO JOSÉ DO RIO PRETO']:
            if datetime.now().month == 12:
                if datetime.now().day > 10:
                    file_front = f'FRONT TRABALHADO {self.convenio} {self.consignataria} 01{datetime.now().year + 1}.xlsx'
                else:
                    file_front = f'FRONT TRABALHADO {self.convenio} {self.consignataria} {str(datetime.now().month).zfill(2)}-{datetime.now().year}.xlsx'
            else:
                if datetime.now().day > 10:
                    file_front = f'FRONT TRABALHADO {self.convenio} {self.consignataria} {str(datetime.now().month + 1).zfill(2)}-{datetime.now().year}.xlsx'
                else:
                    file_front = f'FRONT TRABALHADO {self.convenio} {self.consignataria} {str(datetime.now().month).zfill(2)}-{datetime.now().year}.xlsx'
        else:
            file_front = f'FRONT TRABALHADO {self.convenio} {self.consignataria} {str(datetime.now().month).zfill(2)}-{datetime.now().year}.xlsx'
            
        print(f"arquivo_lancamento: Salvando o arquivo de Front Trabalhado")
        try:
            front_trabalhado.to_excel(os.path.join(self.caminho, file_front), index=False)
        except Exception as e:
            print(f"DEBUG: ERRO AO SALVAR FRONT TRABALHADO {self.convenio}: {e}")


# print(tamanho_parte[0])
