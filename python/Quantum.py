import pandas as pd
from thefuzz import fuzz
from datetime import datetime
from python.ESTEIRAS import load_esteiras
from python.trata_conciliacao import TRATA_CONCILIACAO
from python.TrataOrbital import TRATA_ORBITAL
from python.funcoes_comuns import UNIFICA_FRONT_FUNC_ESTEIRAS
from python.funcoes_comuns import TRATA_CONTRATOS
from python.Tratador_Front_Base import TratadorValidacaoSimples
import openpyxl
import numpy as np
import os
import re


class QUANTUM:
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
            andamento_funcao=self.andamento_funcao
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

        teste_conciliacao = TRATA_CONCILIACAO(self.conciliacao, self.kobraki, self.tacs, self.extra_judicial)
        # conciliacao_tratado = teste_conciliacao.trata_conciliacao()

        if front is False:
            print("trata_averbacao_1: O tratamento preliminar do front falhou. Verifique os erros anteriores.")
            return False

        print(f'Contrato 301268942 no front em trata_averbacao: {front.loc[front["Contrato"] == "301268942", "Prestacao"]}\n')

        consig = self.consignataria
        convenio = self.convenio

        # PEGA APENAS AS COLUNAS NECESSÁRIAS DO ARQUIVO BRUTO
        # colunas = ['A D E', 'SERVIDOR', 'MATRÍCULA', 'CPF', 'CON_VLR_SOL', 'NRO. CGA']
        
        # 1. Remove os espaços invisíveis do começo e do fim de TODAS as colunas
        data.columns = data.columns.str.strip()

        # 2. Agora a sua lista pode ficar limpa e padronizada para qualquer convênio!
        '''colunas = [
            'CON_NRO_OPE_EXN', 
            'CSG_MAT_FUC', 
            'CSG_NOM_CLI', 
            'CSG_CPF_FUC', 
            'CSG_FMT_CPF', 
            'CON_NRO_CON_EXN_CGA',
            'CON_VLR_SOL'
        ]'''

        colunas = [
                'TEC', 
                'MAT.', 
                'NOME', 
                'CPF', 
                'NRO. CGA',
                'VALOR'
                ]

        # 3. O filtro vai funcionar perfeitamente
        data_averbados_bruto = data[colunas]

        '''data_averbados_bruto['CON_NRO_CON_EXN_CGA'] = data_averbados_bruto['CON_NRO_CON_EXN_CGA'].fillna('')
        data_averbados_bruto = data_averbados_bruto[data_averbados_bruto['CON_NRO_CON_EXN_CGA'] != '']

        semi_front = self.front_semi_trabalhado
        if semi_front is False:
            print("trata_averbacao_2: O tratamento preliminar do front falhou. Verifique os erros anteriores.")
            return False
        
        data_averbados_bruto = self.adiciona_contratos_faltando(data_averbados_bruto, semi_front)

        semi_front['Contrato'] = semi_front['Contrato'].astype(str).str.strip()


        data_averbados = self.extrair_contratos_com_referencia(data_averbados_bruto, semi_front)

        teste_conciliacao = TRATA_CONCILIACAO(self.conciliacao, self.kobraki, self.tacs, self.extra_judicial)
        conciliacao_tratado = teste_conciliacao.trata_conciliacao()

        # Operações liquidadas. Tratando NRº OPER EDITADO
        # OP LIQUIDADO
        try:
            oper_liq = self.front[self.front['Status'].astype(str).str.contains('Liquidado|CANCELADO', na=False)][['Contrato']].copy()
            contratos_tratados_liq = oper_liq['Contrato'].astype(str).str.slice(0, 9)
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

            # Cria a coluna de VALOR correspondente
            data_averbados[f'Valor_Unif_{i}'] = data_averbados[nome_coluna_contrato].map(
                semi_front.set_index('Contrato')['Prestacao'].to_dict()
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
            data_averbados[f'OP LIQ {i}'] = data_averbados[f'OP LIQ {i}'].fillna('')
            condicao_op_liq = data_averbados[f'OP LIQ {i}'] != ''

            # Ação: Nessas linhas, define o 'Valor_Unif' correspondente como 0
            # O operador | significa OU (se uma condição OU a outra for verdadeira)
            data_averbados.loc[(condicao_saldo_positivo | condicao_op_liq), f'Valor_Unif_{i}'] = 0
            # --- FIM DA NOVA LÓGICA ---

            # Condição de Operações Liquidadas, se a linha estiver preenchida vai lançar 0

        # --- 2.5 Puxa as liminares ---
        data_averbados["LIMINAR"] = data_averbados['CSG_FMT_CPF'].map(tutela.set_index('CPF')['Acao Judicial'].to_dict())
        condicao_liminar = data_averbados['LIMINAR'] == 1'''

        # --- 3. Soma todos os valores encontrados (forma eficiente) ---


        prepara_data_averbados = TRATA_CONTRATOS(front_semi_trabalhado=self.front_semi_trabalhado, averbados=data_averbados_bruto, convenio=self.convenio,
                                                                 conciliacao_tratada=self.conciliacao, nome_coluna_cpf='CPF', nome_coluna_contrato='NRO. CGA',
                                                                 nome_coluna_parcela='VALOR')
        data_averbados = prepara_data_averbados.trata_averbacao()

        # Pega a lista de todas as colunas de valor que acabamos de criar
        colunas_valores_unificados = [col for col in data_averbados.columns if 'Valor_Unif_' in col]

        if colunas_valores_unificados:
            # print(f"Somando os valores das colunas: {colunas_valores_unificados}")
            data_averbados['Soma'] = data_averbados[colunas_valores_unificados].sum(axis=1)
        else:
            print("Nenhuma coluna de valor encontrada. A coluna 'Soma' será inicializada com 0.")
            data_averbados['Soma'] = 0

        # --- 4. Cálculo da Diferença e Formatação Final ---

        # Garante que a coluna de VALOR é numérica antes do cálculo
        data_averbados['VALOR'] = pd.to_numeric(data_averbados['VALOR'], errors='coerce').fillna(0)

        data_averbados['Diff'] = data_averbados['Soma'] - data_averbados['VALOR']
        data_averbados['Diff'] = data_averbados['Diff'].round(2)

        # --- 5. Cria a coluna Lançar ---
        if consig == 'HOJE PREVIDÊNCIA PRIVADA':
            data_averbados = self.adiciona_peculio(data_averbados)
        else:
            data_averbados['Lançar'] = np.minimum(data_averbados['Soma'], data_averbados['VALOR'])
            # data_averbados.loc[condicao_liminar, 'Lançar'] = 0

        # print("Cálculos de Soma e Diferença finalizados.")

        return data_averbados

    def arquivo_lancamento(self):
        # Cria o novo DataFrame
        data_averbados = self.trata_averbacao()
        front_trabalhado = self.front_trabalhado
        temp = data_averbados[data_averbados['Lançar'] != 0]
        colunas_alancar = ['MAT.','CPF', 'NOME', 'Lançar']
        a_lancar = pd.DataFrame(temp[colunas_alancar])
        a_lancar = a_lancar.rename(columns={'MAT.': 'MATRICULA', 'CPF': 'CPF', 'NOME': 'NOME', 'Lançar': 'Vlr parcela'})


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
        a_lancar['Vlr parcela'] = a_lancar['Vlr parcela'].astype(float)
        a_lancar['Vlr parcela'] = a_lancar['Vlr parcela'].map('{:.2f}'.format)

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
    
        a_lancar.insert(3, 'cod orgão','', True)
    
        a_lancar.insert(0, 'Vencimento', folha_inclusao, True)

        # Criação da sequencia numérica
        a_lancar['N seq registro'] = [str(i).zfill(6) for i in range(1, len(a_lancar) + 1)]

        # a_lancar['VALOR'] =  a_lancar['VALOR'].apply(substituir_virgula_por_ponto)
    
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
