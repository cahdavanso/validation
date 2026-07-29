import pandas as pd
from thefuzz import fuzz
from datetime import datetime
from python.ESTEIRAS import load_esteiras
from python.trata_conciliacao import TRATA_CONCILIACAO
from python.TrataOrbital import TRATA_ORBITAL
from python.funcoes_comuns import TRATA_CONTRATOS
from python.funcoes_comuns import UNIFICA_FRONT_FUNC_ESTEIRAS
from python.Tratador_Front_Base import TratadorNeoconsig
import openpyxl
import numpy as np
import os
import re


class NEOCONSIG:
    def __init__(self, portal_file_list, convenio, front, consignataria, caminho, andamento_funcao=None, funcao=None, conciliacao=None, extra_judicial=None, kobraki=None, tacs=None, orbital=None):
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
            columns=['CONTRATOS', 'CPF', 'PRESTAÇÃO', 'PRAZO', 'D8 JUN 25', 'ST JUL 25', 'RECEBIDO GERAL'])
        conciliacao_falso['CONTRATOS'] = 123
        conciliacao_falso['CPF'] = '123.456'
        conciliacao_falso['PRESTAÇÃO'] = 10
        conciliacao_falso['PRAZO'] = 96
        conciliacao_falso['PRODUTO'] = 'CARTÃO DE CRÉDITO'
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

        front_semi_trabalhado_preliminar = TratadorNeoconsig(front=self.front_final_consig, conciliacao=self.conciliacao, convenio=self.convenio,
                                                             caminho=self.caminho, condicoes_1=self.condicoes_1, consignataria=self.consignataria,
                                                             kobraki=self.kobraki, tacs=tacs)
        self.front_semi_trabalhado = front_semi_trabalhado_preliminar.tratamento_front_preliminar_base()
        self.front_trabalhado = self.front_semi_trabalhado[self.front_semi_trabalhado['OBS'].isin([pd.NA, np.nan, ''])]


        self.arquivo_lancamento()


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

            # --- Passo 2: Definir a função que será aplicada em cada linha (LÓGICA ALTERADA) ---
            def encontrar_contratos_na_linha(row):
                cpf = row['CPF_Formatado']
                texto_contratos_sujo = str(row['N CONTRATO']).strip()
            
                cpf = row['CPF_Formatado']
                texto_contratos_sujo = str(row['N CONTRATO'])

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
                                score_base = 200
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
            df_sujo['N CONTRATO'] = df_sujo['N CONTRATO'].astype(str).str.replace('nan', '')


            lista_de_contratos_encontrados = df_sujo.apply(encontrar_contratos_na_linha, axis=1)

            df_contratos_novos = pd.DataFrame(lista_de_contratos_encontrados.tolist(), index=df_sujo.index)
            df_contratos_novos.columns = [f'Contrato Editado {i + 1}' for i in df_contratos_novos.columns]

            df_resultado = pd.concat([df_sujo, df_contratos_novos], axis=1)

            print("extrair_contratos_com_referencia: Salvando relatório de averbados com contratos tratados")
            try:
                df_resultado.to_excel(os.path.join(self.caminho, f"Relatório Averbados Contratos tratados.xlsx"), index=False)
            except Exception as e:
                print(f"DEBUG: ERRO AO SALVAR RELATÓRIO AVERBADO CONTRATOS TRATADOS: {e}")
            return df_resultado


    def substituir_virgula_por_ponto(self, valor):
        return valor.replace(',', '.')

    # FUNÇÃO QUE SUBSTITUI CARACTER POR NADA
    def replace_characters(self, file, coluna, localizar, substituir):
        column = file[coluna].replace(localizar, substituir, regex=True)
        return column

    # FUNÇÃO QUE FAZ PARTE DO PROCX COM O FRONT COMO BASE
    def mapeamento_front(self, interval, criteria):
        maping = self.front.set_index(interval)[criteria].to_dict()
        return maping


    # DIVIDE A STRING EM PARTES DE 6
    def inserir_barras(self, numero):
        partes = [numero[i:i + 6] for i in range(0, len(numero), 6)]
        return '/'.join(partes)

    # Função para distribuir os valores da coluna de origem para as colunas-alvo
    def distribuir_valores(self, df, coluna_origem, colunas_alvo):
        for i, coluna_alvo in enumerate(colunas_alvo):
            df[coluna_alvo] = df[coluna_origem].str.split('/').str[i]

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
        data_averbados['Lançar'] = np.minimum(data_averbados['Soma_Calculada'], data_averbados['VALOR PARCELA'])

        # (Opcional) Remove a coluna temporária se não precisar mais
        data_averbados = data_averbados.drop(columns=['Soma_Calculada'])

        return data_averbados

    def orbital_tratado(self, orbital, front_para_separar):

        orbital_preparado = orbital.loc[
            orbital['DESCRIÇÃO DO EMPREG'].str.contains('PREF GOIÂNIA|PM GOIANIA SEG', case=False, na=False),
            ['CONTRATO', 'nome_mutuario', 'num_cpf_mutuario', 'VALID DESCONTO FINAL']
        ].copy()
        orbital_preparado.columns = ['Proposta', 'Cliente', 'CPF/CNPJ', 'VALID DESCONTO FINAL']

        front_so_orbital = front_para_separar.loc[
            front_para_separar['OBS'] == 'NÃO LANÇAR - ORBITAL',
            ['Contrato', 'Nome', 'CPF', 'Prestacao']].copy()
        
        front_so_orbital.columns = ['Proposta', 'Cliente', 'CPF/CNPJ', 'VALID DESCONTO FINAL']

        # front_so_orbital['Proposta'] = front_so_orbital['Proposta'].astype(str).str.strip()

        # front_so_orbital['VALID DESCONTO FINAL'] = front_so_orbital['VALID DESCONTO FINAL'].astype(str).str.replace('.', '', regex=False)
        front_so_orbital['VALID DESCONTO FINAL'] = front_so_orbital['VALID DESCONTO FINAL'].astype(str).str.replace(',', '.', regex=False)
        front_so_orbital['VALID DESCONTO FINAL'] = pd.to_numeric(front_so_orbital['VALID DESCONTO FINAL'], errors='coerce')

        orbital_final = pd.concat([front_so_orbital, orbital_preparado])

        orbital_final = orbital_final.drop_duplicates(subset=['Proposta'], keep='first')

        print(f"orbital_tratado: Salvando arquivo de orbital tratado teste com front")
        try:
            orbital_final.to_excel(os.path.join(self.caminho, f"ORBITAL TRABALHADO {self.convenio}.xlsx"), index=False)
            print(f"orbital_tratado: ORBITAL TRABALHADO {self.convenio} salvo com sucesso!")
        except Exception as e:
            print(f"orbital_tratado: ERRO AO SALVAR ORBITAL TRABALHADO {self.convenio}: {e}")

        return orbital_final
    
    def adiciona_contratos_faltando(self, averbado_contratos_faltantes, front_semi):
        # 1. Normalização do CPF no DataFrame B (Removendo caracteres não numéricos)
        # front_semi['CPF_clean'] = front_semi['CPF'].astype(str).str.replace(r'\D', '', regex=True)

        # 2. Preparação do DataFrame B para os diferentes cenários de valor
        # Vamos criar DataFrames auxiliares para cada regra de negócio
        # Isso evita confusão com múltiplos joins no mesmo objeto
        front_semi_base = front_semi[['CPF', 'Prestacao', 'Contrato']].drop_duplicates(subset=['CPF', 'Prestacao'])

        # Criamos as variações no B para "fingir" que o valor já tem o seguro embutido
        front_semi_exact = front_semi_base.copy()
        front_semi_plus20 = front_semi_base.copy()
        front_semi_plus20['Prestacao_Ajustada'] = front_semi_plus20['Prestacao'] + 20
        front_semi_plus40 = front_semi_base.copy()
        front_semi_plus40['Prestacao_Ajustada'] = front_semi_plus40['Prestacao'] + 40

        # 3. Execução dos Merges no DataFrame A
        # Primeiro, tentamos o match exato (valor igual)
        averbado_contratos_faltantes = averbado_contratos_faltantes.merge(
            front_semi_exact, 
            left_on=['CPF_Formatado', 'VALOR PARCELA'], 
            right_on=['CPF', 'Prestacao'], 
            how='left'
        )

        # Preenchemos a coluna "N CONTRATO" com o que achamos no primeiro merge
        averbado_contratos_faltantes['N CONTRATO'] = averbado_contratos_faltantes['N CONTRATO'].fillna(averbado_contratos_faltantes['Contrato'])
        averbado_contratos_faltantes.drop(columns=['CPF', 'Prestacao', 'Contrato'], inplace=True)

        # Segundo merge: Caso de +20 reais
        averbado_contratos_faltantes = averbado_contratos_faltantes.merge(
            front_semi_plus20, 
            left_on=['CPF_Formatado', 'VALOR PARCELA'], 
            right_on=['CPF', 'Prestacao_Ajustada'], 
            how='left', 
            suffixes=('', '_20')
        )

        averbado_contratos_faltantes['N CONTRATO'] = averbado_contratos_faltantes['N CONTRATO'].fillna(averbado_contratos_faltantes['Contrato'])
        averbado_contratos_faltantes.drop(columns=['CPF', 'Prestacao', 'Contrato', 'Prestacao_Ajustada'], inplace=True)

        # Terceiro merge: Caso de +40 reais
        averbado_contratos_faltantes = averbado_contratos_faltantes.merge(
            front_semi_plus40, 
            left_on=['CPF_Formatado', 'VALOR PARCELA'], 
            right_on=['CPF', 'Prestacao_Ajustada'], 
            how='left', 
            suffixes=('', '_40')
        )

        averbado_contratos_faltantes['N CONTRATO'] = averbado_contratos_faltantes['N CONTRATO'].fillna(averbado_contratos_faltantes['Contrato'])

        averbado_contratos_faltantes.drop(columns=['CPF', 'Prestacao', 'Contrato', 'Prestacao_Ajustada'], inplace=True)

        # Limpeza final das colunas auxiliares
        # averbado_contratos_faltantes = averbado_contratos_faltantes[['CPF SERVIDOR', 'Valor Prestação', 'N CONTRATO']]

        return averbado_contratos_faltantes

    def trata_averbacao(self):
        # PUXA OS ARQUIVOS À SEREM TRATADOS
        data = self.averbados
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

        if convenio in ['GOV. GOIÁS', 'PREF. SOROCABA']:
            # O ARQUIVO DE AVERBAÇÕES PRECISA TER OS DOIS TIPOS. COMPRA E SAQUE
            # PEGA APENAS AS COLUNAS NECESSÁRIAS DO ARQUIVO BRUTO

            
            colunas = ['NOME SERVIDOR', 'MATRICULA', 'CREDENCIADO', 'CPF SERVIDOR', 'VALOR PARCELA', 'PRODUTO', 'N OPERACAO', 
                       'N CONTRATO', 'RUBRICA', 'QTD PARCELAS OPERACAO']
            data_averbados_bruto = data[colunas]

            # Passo 1: Garantir que a coluna é do tipo string
            cpf_str = data_averbados_bruto['CPF SERVIDOR'].astype(str)
            cpf_str_ajustado = cpf_str.str.zfill(11)
            cpf_formatado = cpf_str_ajustado.str.slice(0, 3) + '.' + \
                            cpf_str_ajustado.str.slice(3, 6) + '.' + \
                            cpf_str_ajustado.str.slice(6, 9) + '-' + \
                            cpf_str_ajustado.str.slice(9, 11)

            data_averbados_bruto.insert(2, 'CPF_Formatado', cpf_formatado, True)

            if self.orbital is not None:
                preparando_orbital = TRATA_ORBITAL(self.orbital, front, self.convenio, self.caminho)
                orbital_tratado = preparando_orbital.orbital_tratado()
                orbital_tratado['VALOR DESCONTO'] = pd.to_numeric(orbital_tratado['VALOR DESCONTO'], errors='coerce')
                mask_orbital = orbital_tratado.groupby('CPF/CNPJ')['VALOR DESCONTO'].sum()
                data_averbados_bruto['ORBITAL'] = ''
                data_averbados_bruto['ORBITAL'] = data_averbados_bruto['CPF_Formatado'].map(mask_orbital)
                data_averbados_bruto['ORBITAL'] = data_averbados_bruto['ORBITAL'].fillna(0)

                print(f"trata_averbacao: Salvando arquivo de averbacao teste com orbital")
                try:
                    data_averbados_bruto.to_excel(os.path.join(self.caminho, f"Averbacao com orbital teste {self.convenio}.xlsx"), index=False)
                except Exception as e:
                    print(f"trata_averbacao: ERRO AO SALVAR AVERBAÇÃO COM ORBITAL TESTE: {e}")

            # data_averbados_bruto = data_averbados_bruto.loc[(data_averbados_bruto['QTD PARCELAS OPERACAO'] != 96) | (data_averbados_bruto['QTD PARCELAS OPERACAO'] != '96')]

            # --- 3. Soma todos os valores encontrados (forma eficiente) ---

            prepara_data_averbados = TRATA_CONTRATOS(front_semi_trabalhado=self.front_semi_trabalhado, averbados=data_averbados_bruto, convenio=self.convenio,
                                                     conciliacao_tratada=self.conciliacao, nome_coluna_cpf='CPF SERVIDOR', nome_coluna_contrato='N CONTRATO',
                                                     nome_coluna_parcela='VALOR PARCELA')
            data_averbados = prepara_data_averbados.trata_averbacao()

            # Pega a lista de colunas de valor
            colunas_valores_unificados = [col for col in data_averbados.columns if 'Valor_Unif_' in col]

            # --- 4. Cálculo da Diferença e Formatação Final ---

            # Garante que a coluna de VALOR PARCELA é numérica antes do cálculo
            data_averbados['VALOR PARCELA'] = pd.to_numeric(data_averbados['VALOR PARCELA'],
                                                              errors='coerce').fillna(0)

            # 2. Filtra todas as colunas que começam com "Parcela "
            colunas_parcelas = data_averbados.filter(like='Valor_Unif_')

            # NOVO PASSO: Adiciona a coluna 'ORBITAL' ao DataFrame de colunas para soma
            colunas_para_somar = colunas_parcelas.copy()  # Cria uma cópia para garantir a segurança

            # 3. Soma as colunas horizontalmente (axis=1)
            data_averbados['Soma'] = colunas_para_somar.sum(axis=1)

            # 4. Criação da coluna SOMASES pelo benefício saque 70
            # 1. Criamos um "filtro temporário" apenas com as linhas do produto desejado
            filtro_produto = data_averbados[data_averbados['PRODUTO'].isin(['BENEFÍCIO SAQUE 70', 'CARTÃO BENEFÍCIO SAQUE'])]

            # 2. Agrupamos esse filtro por CPF e somamos o valor da parcela
            # Isso cria um dicionário/série onde o índice é o CPF e o valor é a soma
            somas_por_cpf = filtro_produto.groupby('CPF_Formatado')['VALOR PARCELA'].sum()
            print(f'Tipo de Valor da Parcela: {data_averbados['VALOR PARCELA'].dtype}\n')
            print(f'somas_por_cpf:\n{somas_por_cpf}')

            # 3. Mapeamos esse resultado de volta para o DataFrame original
            # O .fillna(0) garante que CPFs que não têm esse produto fiquem com 0 em vez de vazio (NaN)
            data_averbados['SOMASES'] = data_averbados['CPF_Formatado'].map(somas_por_cpf).fillna(0)

            # 4. Diferença entre o Valor_Unif ou seja "soma" menos o "SOMASES" pra saber se tudo do front já está sendo descontado com prazo
            data_averbados['DIFF Soma E SOMASES'] =  data_averbados['Soma'] - data_averbados['SOMASES']

            # 5. Coluna de DIFF Soma E SOMASES mais orbital
            data_averbados['DIFF MAIS ORBITAL'] = data_averbados['DIFF Soma E SOMASES'] + data_averbados['ORBITAL']

            # 6. Finalmente a coluna de Lançar
            data_averbados['Lançar'] = np.minimum(data_averbados['DIFF MAIS ORBITAL'], data_averbados['VALOR PARCELA'])
            # data_averbados.loc[condicao_liminar, 'Lançar'] = 0

            data_averbados_lancar = data_averbados[data_averbados['PRODUTO'].isin(['BENEFÍCIO COMPRAS 30', 'CARTÃO BENEFÍCIO COMPRAS'])]

            print(f'averbado trabalhado PREF. SÃO GONÇALO:\n{data_averbados}')

            data_averbados.to_excel(os.path.join(self.caminho, f'AVERBADO QUASE TRABALHADO {self.convenio}.xlsx'), index=False)


            return data_averbados_lancar[data_averbados_lancar['Lançar'] > 0]

        # PEGA APENAS AS COLUNAS NECESSÁRIAS DO ARQUIVO BRUTO
        colunas = ['N OPERACAO', 'NOME SERVIDOR', 'MATRICULA', 'CREDENCIADO', 'CPF SERVIDOR', 'VALOR PARCELA', 'PRODUTO', 'N OPERACAO', 
                       'N CONTRATO', 'RUBRICA', 'QTD PARCELAS OPERACAO']
        data_averbados_bruto = data[colunas]

        # Passo 1: Garantir que a coluna é do tipo string
        # Criar coluna de CPF com ponto e traço
        cpf_str = data_averbados_bruto['CPF SERVIDOR'].astype(str)
        cpf_str_ajustado = cpf_str.str.zfill(11)
        cpf_formatado = cpf_str_ajustado.str.slice(0, 3) + '.' + \
                              cpf_str_ajustado.str.slice(3, 6) + '.' + \
                              cpf_str_ajustado.str.slice(6, 9) + '-' + \
                              cpf_str_ajustado.str.slice(9, 11)

        data_averbados_bruto.insert(4, 'CPF_Formatado', cpf_formatado, True)

        # --- 3. Soma todos os valores encontrados (forma eficiente) ---

        prepara_data_averbados = TRATA_CONTRATOS(front_semi_trabalhado=self.front_semi_trabalhado, averbados=data_averbados_bruto, convenio=self.convenio,
                                                         conciliacao_tratada=self.conciliacao, nome_coluna_cpf='CPF SERVIDOR', nome_coluna_contrato='N CONTRATO',
                                                         nome_coluna_parcela='VALOR PARCELA')
        data_averbados = prepara_data_averbados.trata_averbacao()

        print(f'Amostra de data_averbados:\n{data_averbados.head()}')

        # Pega a lista de todas as colunas de valor que acabamos de criar
        colunas_valores_unificados = [col for col in data_averbados.columns if 'Valor_Unif_' in col]

        if colunas_valores_unificados:
            # print(f"Somando os valores das colunas: {colunas_valores_unificados}")
            data_averbados['Soma'] = data_averbados[colunas_valores_unificados].sum(axis=1)
        else:
            print("Nenhuma coluna de valor encontrada. A coluna 'Soma' será inicializada com 0.")
            data_averbados['Soma'] = 0

        # --- 4. Cálculo da Diferença e Formatação Final ---

        # Garante que a coluna de VALOR PARCELA é numérica antes do cálculo
        if data_averbados['VALOR PARCELA'].dtype != 'float64':
            data_averbados['VALOR PARCELA'] = data_averbados['VALOR PARCELA'].astype(str).str.replace('.', '').str.replace(',', '')
            data_averbados['VALOR PARCELA'] = pd.to_numeric(data_averbados['VALOR PARCELA'], errors='coerce').fillna(0)

        data_averbados['Diff'] = data_averbados['Soma'] - data_averbados['VALOR PARCELA']
        data_averbados['Diff'] = data_averbados['Diff'].round(2)

        # --- 5. Cria a coluna Lançar ---
        if consig == 'HOJE PREVIDÊNCIA PRIVADA':
            data_averbados = self.adiciona_peculio(data_averbados)
        else:
            data_averbados['Lançar'] = np.minimum(data_averbados['Soma'], data_averbados['VALOR PARCELA'])

        # print("Cálculos de Soma e Diferença finalizados.")

        return data_averbados

    def arquivo_lancamento(self):
        # Cria o novo DataFrame
        data_averbados = self.trata_averbacao()
        
        # front_trabalhado = self.tratamento_front()
        front_trabalhado = self.front_trabalhado
        temp = data_averbados[data_averbados['Lançar'] != 0]
        colunas_alancar = ['MATRICULA', 'CPF SERVIDOR', 'Lançar', 'N OPERACAO', 'RUBRICA']
        a_lancar = pd.DataFrame(temp[colunas_alancar])
        a_lancar = a_lancar.rename(columns={'MATRICULA': 'Matricula', 'Lançar': 'Parcela', 'CPF SERVIDOR': 'CPF', 'N OPERACAO': 'ADE'})


        # Calcule a SOMASE para cada categoria no Averbacoes Trabalhadas
        somas_por_categoria = data_averbados.groupby('CPF_Formatado')['Lançar'].transform('sum')
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
        a_lancar['Parcela'] = a_lancar['Parcela'].astype(str).str.replace('.', '').str.replace(',', '')
        # a_lancar['Parcela'] = a_lancar['Parcela'].map('{:.2f}'.format)

        # Cria colunas no meio do Averbações a Lançar
        if self.convenio in ['PREF. SÃO GONÇALO', 'PREF. SÃO LUÍS']:
            if datetime.now().month == 12 and datetime.now().day > 10:
                folha_inclusao = f'01{datetime.now().year + 1}'
            elif datetime.now().day < 10:
                folha_inclusao = f'{str(datetime.now().month).zfill(2)}{datetime.now().year}'
            else:
                folha_inclusao = f'{str(datetime.now().month + 1).zfill(2)}{datetime.now().year}'
        else:
            folha_inclusao = f'{str(datetime.now().month).zfill(2)}{datetime.now().year}'
        
        a_lancar.insert(2, 'COMPETENCIA', folha_inclusao, True)
    
        # --- 1. data_averbados ---

        # SOMASE Interno (Averbados)
        # transform('sum') já mantém o índice alinhado, perfeito.
        data_averbados['SOMASE'] = data_averbados.groupby('CPF_Formatado')['Lançar'].transform('sum').round(2)

        # SOMASE Externo (Vem do Front)
        soma_condicional_dict_averb = front_trabalhado.groupby('CPF')['Valor a lançar'].sum().to_dict()

        # Mapeia e já preenche com 0 quem não for encontrado (fillna)
        data_averbados['SOMASE FRONT'] = data_averbados['CPF_Formatado'].map(soma_condicional_dict_averb).fillna(0).round(2)

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
        soma_condicional_dict_front = data_averbados.groupby('CPF_Formatado')['Lançar'].sum().to_dict()

        # Cria a coluna SOMASE AVERB mapeando e preenchendo vazios com 0
        # Nota: Certifique-se que front_trabalhado['CPF'] e data_averbados['CPF_Formatado'] são idênticos (pontos/traços)
        front_trabalhado['SOMASE AVERB'] = front_trabalhado['CPF'].map(soma_condicional_dict_front).fillna(0).round(2)
        # Cálculo do DIFF
        front_trabalhado['DIFF'] = front_trabalhado['SOMASE FRONT'] - front_trabalhado['SOMASE AVERB']
    
        # Cria o arquivo Averbações Trabalhadas
        if self.convenio in ['PREF. SÃO GONÇALO', 'GOV. GOIÁS']:
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
        if self.convenio in ['PREF. SÃO GONÇALO', 'GOV. GOIÁS']:
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
        if self.convenio in ['PREF SAO GONCALO', 'PREF DUQUE DE CAXIAS']:
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
