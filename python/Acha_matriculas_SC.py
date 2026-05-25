import pandas as pd
import openpyxl
import numpy as np
from itertools import combinations
from datetime import datetime
import os

class ACHA_MATRICULAS_SC:
    def __init__(self, front_orbital, averbado_capital, averbado_click, caminho):
        self.front_orbital = front_orbital
        self.averbado_capital = averbado_capital
        self.averbado_click = averbado_click
        self.caminho = caminho

        # Contse capital
        contagem_cpf_capital = self.averbado_capital['CPF'].value_counts()
        self.front_orbital['CONT.SE CAPITAL'] = self.front_orbital['CPF'].map(contagem_cpf_capital).fillna(0).astype(int)

        # Contse click
        contagem_cpf_click = self.averbado_click['CPF'].value_counts()
        self.front_orbital['CONT.SE CLICK'] = self.front_orbital['CPF'].map(contagem_cpf_click).fillna(0).astype(int)

        self.df_final = None

    def busca_direta(self):
        '''
        Função que verifica quais matrículas existem na Capital e não existem na Click, e vice versa, por meio de
        Cont.se.
        :return:
        '''
        arq_matricula_base = self.front_orbital.copy()
        arq_matricula_capital = self.averbado_capital.copy()
        arq_matricula_click = self.averbado_click.copy()

        # 1. Crie a máscara na base
        mask_capital = (arq_matricula_base['CONT.SE CAPITAL'] == 1) & (arq_matricula_base['CONT.SE CLICK'] == 0)

        # 2. Crie o dicionário de mapeamento: CPF -> matrícula (vindo do outro DF)
        cpf_para_matricula = arq_matricula_capital.set_index('CPF')['matrícula'].to_dict()

        # 3. Aplique somente nas linhas da máscara
        arq_matricula_base.loc[mask_capital, 'MATRÍCULA CAPITAL'] = (
            arq_matricula_base.loc[mask_capital, 'CPF'].map(cpf_para_matricula)
        )

        # 1. Crie a máscara na base
        mask_click = (arq_matricula_base['CONT.SE CLICK'] == 1) & (arq_matricula_base['CONT.SE CAPITAL'] == 0)

        # 2. Crie o dicionário de mapeamento: CPF -> matrícula (vindo do outro DF)
        cpf_para_matricula_click = arq_matricula_click.set_index('CPF')['matrícula'].to_dict()

        # 3. Aplique somente nas linhas da máscara
        arq_matricula_base.loc[mask_click, 'MATRÍCULA CLICK'] = (
            arq_matricula_base.loc[mask_click, 'CPF'].map(cpf_para_matricula_click)
        )

        arq_matricula_base['METODO'] = ''

        # 4. Aplique nas linhas de máscara "BUSCA DIRETA"
        arq_matricula_base.loc[mask_capital, 'METODO'] = "ATRIBUIÇÃO DIRETA CAPITAL"
        arq_matricula_base.loc[mask_click, 'METODO'] = "ATRIBUIÇÃO DIRETA CLICK"

        # print(arq_matricula_base)
        self.busca_por_parcela(arq_matricula_base, arq_matricula_capital, arq_matricula_click)

        return self.df_final

    def busca_por_parcela(self, base, capital, click):
        df_base = base.copy()
        df_capital = capital.copy()
        df_click = click.copy()

        # Concatena CPF com parcela na base
        base_concat = df_base['CPF'].astype(str) + df_base['PARCELA BASE'].astype(str)
        df_base['CONCAT'] = base_concat

        # Concatena CPF com parcela na capital
        capital_concat = df_capital['CPF'].astype(str) + df_capital['parcela 100'].astype(str)
        df_capital['CONCAT'] = capital_concat

        # Concatena CPF com parcela na capital 70
        capital_concat_70 = df_capital['CPF'].astype(str) + df_capital['parcela 70'].astype(str)
        df_capital['CONCAT 70'] = capital_concat_70

        # Concatena CPF com parcela na capital 30
        capital_concat_30 = df_capital['CPF'].astype(str) + df_capital['parcela 30'].astype(str)
        df_capital['CONCAT 30'] = capital_concat_30

        # Concatena CPF com parcela na click
        click_concat = df_click['CPF'].astype(str) + df_click['parcela 100'].astype(str)
        df_click['CONCAT'] = click_concat

        # Concatena CPF com parcela na click 70
        click_concat_70 = df_click['CPF'].astype(str) + df_click['parcela 70'].astype(str)
        df_click['CONCAT 70'] = click_concat_70

        # Concatena CPF com parcela na click 30
        click_concat_30 = df_click['CPF'].astype(str) + df_click['parcela 30'].astype(str)
        df_click['CONCAT 30'] = click_concat_30

        print('CPF 342.772.349-68\n', df_click[df_click['CPF'] == '342.772.349-68'])


        # =======================================================================
        #                             CRIA DICIONÁRIOS
        # =======================================================================

        # Cria os dicionários de mapeamento por CONCAT
        mapa_capital = df_capital.set_index('CONCAT')['matrícula'].to_dict()
        mapa_click = df_click.set_index('CONCAT')['matrícula'].to_dict()

        # Cria os dicionários de mapeamento por CONCAT 70
        mapa_capital_70 = df_capital.set_index('CONCAT 70')['matrícula'].to_dict()
        mapa_click_70 = df_click.set_index('CONCAT 70')['matrícula'].to_dict()

        # Cria os dicionários de mapeamento por CONCAT 30
        mapa_capital_30 = df_capital.set_index('CONCAT 30')['matrícula'].to_dict()
        mapa_click_30 = df_click.set_index('CONCAT 30')['matrícula'].to_dict()

        # =======================================================================
        #                               MAPEAMENTO
        # =======================================================================

        # Preenche apenas onde MATRÍCULA CAPITAL está vazia
        mask_vazia = df_base['MATRÍCULA CAPITAL'].isna() | (df_base['MATRÍCULA CAPITAL'] == '')

        # Tenta preencher da aba CAPITAL
        df_base.loc[mask_vazia, 'MATRÍCULA CAPITAL'] = (
            df_base.loc[mask_vazia, 'CONCAT'].map(mapa_capital)
        )

        # Mascara para os casos de CAPITAL 70
        mask_vazia_capital_70 = df_base['MATRÍCULA CAPITAL'].isna() | (df_base['MATRÍCULA CAPITAL'] == '')

        # Tenta preencher da aba CAPITAL com 70 por cento
        df_base.loc[mask_vazia_capital_70, 'MATRÍCULA CAPITAL'] = (
            df_base.loc[mask_vazia_capital_70, 'CONCAT'].map(mapa_capital_70)
        )

        # Mascara para os casos de capital 30
        mask_vazia_capital_30 = df_base['MATRÍCULA CAPITAL'].isna() | (df_base['MATRÍCULA CAPITAL'] == '')

        # Tenta preencher da aba CAPITAL com 30 por cento
        df_base.loc[mask_vazia_capital_30, 'MATRÍCULA CAPITAL'] = (
            df_base.loc[mask_vazia_capital_30, 'CONCAT'].map(mapa_capital_30)
        )

        # Atualiza a máscara (ainda vazios)
        mask_ainda_vazia = df_base['MATRÍCULA CLICK'].isna() | (df_base['MATRÍCULA CLICK'] == '')

        # Tenta preencher da aba CAPITAL
        df_base.loc[mask_ainda_vazia, 'MATRÍCULA CLICK'] = (
            df_base.loc[mask_ainda_vazia, 'CONCAT'].map(mapa_click)
        )

        # Mascara para os casos de click 70
        # Atualiza a máscara (ainda vazios)
        mask_ainda_vazia_70 = df_base['MATRÍCULA CLICK'].isna() | (df_base['MATRÍCULA CLICK'] == '')

        # Tenta preencher da aba CLICK com 70 por cento
        df_base.loc[mask_ainda_vazia_70, 'MATRÍCULA CLICK'] = (
            df_base.loc[mask_ainda_vazia_70, 'CONCAT'].map(mapa_click_70)
        )

        # Mascara para os casos de click 30
        # Atualiza a máscara (ainda vazios)
        mask_ainda_vazia_30 = df_base['MATRÍCULA CLICK'].isna() | (df_base['MATRÍCULA CLICK'] == '')

        # Tenta preencher da aba CLICK com 30 por cento
        df_base.loc[mask_ainda_vazia_30, 'MATRÍCULA CLICK'] = (
            df_base.loc[mask_ainda_vazia_30, 'CONCAT'].map(mapa_click_30)
        )

        # (Opcional) Preenche vazio com ''
        df_base['MATRÍCULA CAPITAL'] = df_base['MATRÍCULA CAPITAL'].fillna('')

        # (Opcional) Preenche vazio com ''
        df_base['MATRÍCULA CLICK'] = df_base['MATRÍCULA CLICK'].fillna('')

        # print(df_base[['PARCELA BASE', 'MATRÍCULA CAPITAL', 'MATRÍCULA CLICK', 'CONCAT']])

        # ===========================================================================
        #                       COLOCA O METODO UTILIZADO
        # ===========================================================================
        mask_metodo_vazio = (df_base['METODO'] == '') & ((df_base['MATRÍCULA CAPITAL'] != '') | (df_base['MATRÍCULA CLICK'] != ''))

        df_base.loc[mask_metodo_vazio, 'METODO'] = 'ATRIBUIDO CONCAT'

        self.atribuir_por_combinacao_de_soma_exata(df_base, df_capital, df_click)


    def soma_atribuido(self, base, capital, click):
        """
        Função refatorada e otimizada para atribuir matrículas baseando-se na soma de parcelas.
        Ela itera sobre as parcelas 100, 70 e 30, evitando repetição de código.
        """
        print("Iniciando a atribuição por soma de parcelas...")

        # 1. PREPARAÇÃO INICIAL
        df_base = base.copy()
        df_capital = capital.copy()
        df_click = click.copy()

        # Garante que os tipos de dados sejam consistentes para o merge
        for df in [df_capital, df_click]:
            df['CPF'] = df['CPF'].astype(str)
            df['matrícula'] = df['matrícula'].astype(str)

        df_base['CPF'] = df_base['CPF'].astype(str)

        # Lista das colunas de parcela para iterar
        parcelas_a_checar = ['parcela 100', 'parcela 70', 'parcela 30']

        # 2. LOOP PRINCIPAL PARA CADA TIPO DE PARCELA
        for parcela_col in parcelas_a_checar:
            print(f"\n--- Tentando correspondência com a coluna: {parcela_col} ---")

            # Filtra pelas linhas que AINDA estão vazias no início de cada iteração
            filtro_vazias = (df_base['MATRÍCULA CAPITAL'].fillna('') == '') & (df_base['MATRÍCULA CLICK'].fillna('') == '')

            # Se não há mais linhas vazias, podemos parar o processo
            if not filtro_vazias.any():
                print("Não há mais matrículas vazias para preencher. Encerrando o loop.")
                break

            df_para_somar = df_base[filtro_vazias]

            # Agrupa por CPF e soma os valores das linhas restantes
            soma_valores = df_para_somar.groupby('CPF')['PARCELA BASE'].sum().reset_index()
            soma_valores = soma_valores.rename(columns={'PARCELA BASE': 'VALOR_TOTAL'})

            if soma_valores.empty:
                print("Nenhuma parcela para somar nesta iteração.")
                continue

            # CORREÇÃO CRÍTICA: Arredonda os valores para garantir a correspondência de floats
            soma_valores['VALOR_TOTAL_ROUND'] = soma_valores['VALOR_TOTAL'].round(2)
            df_capital[f'{parcela_col}_ROUND'] = df_capital[parcela_col].round(2)
            df_click[f'{parcela_col}_ROUND'] = df_click[parcela_col].round(2)

            # 3. BUSCA DAS MATRÍCULAS (PARA A PARCELA ATUAL DO LOOP)

            # Junta com CAPITAL
            matriculas_capital = pd.merge(
                soma_valores,
                df_capital[['CPF', 'matrícula', f'{parcela_col}_ROUND']],
                how='inner',
                left_on=['CPF', 'VALOR_TOTAL_ROUND'],
                right_on=['CPF', f'{parcela_col}_ROUND']
            )[['CPF', 'matrícula']].rename(columns={'matrícula': 'MATRICULA_CAPITAL_ENCONTRADA'}).drop_duplicates(
                subset='CPF')

            # Junta com CLICK
            matriculas_click = pd.merge(
                soma_valores,
                df_click[['CPF', 'matrícula', f'{parcela_col}_ROUND']],
                how='inner',
                left_on=['CPF', 'VALOR_TOTAL_ROUND'],
                right_on=['CPF', f'{parcela_col}_ROUND']
            )[['CPF', 'matrícula']].rename(columns={'matrícula': 'MATRICULA_CLICK_ENCONTRADA'}).drop_duplicates(
                subset='CPF')

            # 4. ATRIBUIÇÃO VETORIZADA (MUITO MAIS RÁPIDA QUE O .apply())

            # Preenche CAPITAL
            if not matriculas_capital.empty:
                df_base = pd.merge(df_base, matriculas_capital, on='CPF', how='left')
                # Preenche a matrícula somente nas linhas que estavam vazias
                df_base['MATRÍCULA CAPITAL'] = np.where(
                    filtro_vazias,
                    df_base['MATRICULA_CAPITAL_ENCONTRADA'],
                    df_base['MATRÍCULA CAPITAL']
                )
                df_base = df_base.drop(columns=['MATRICULA_CAPITAL_ENCONTRADA'])
                print(f"Encontradas e atribuídas {len(matriculas_capital)} matrículas para CAPITAL.")

            # Preenche CLICK
            if not matriculas_click.empty:
                df_base = pd.merge(df_base, matriculas_click, on='CPF', how='left')
                # A condição agora precisa ser reavaliada para não sobrescrever o que acabamos de preencher
                filtro_ainda_vazio = (df_base['MATRÍCULA CAPITAL'].fillna('') == '') & (
                            df_base['MATRÍCULA CLICK'].fillna('') == '')
                df_base['MATRÍCULA CLICK'] = np.where(
                    filtro_ainda_vazio,
                    df_base['MATRICULA_CLICK_ENCONTRADA'],
                    df_base['MATRÍCULA CLICK']
                )
                df_base = df_base.drop(columns=['MATRICULA_CLICK_ENCONTRADA'])
                print(f"Encontradas e atribuídas {len(matriculas_click)} matrículas para CLICK.")



        # 5. ATUALIZAÇÃO FINAL DO MÉTODO
        # Preenche os nulos com strings vazias para consistência
        df_base[['MATRÍCULA CAPITAL', 'MATRÍCULA CLICK']] = df_base[['MATRÍCULA CAPITAL', 'MATRÍCULA CLICK']].fillna('')

        # Define o método para as linhas que foram alteradas nesta função
        # (Ou seja, estavam vazias no início e agora não estão mais)
        # ===========================================================================
        #                       COLOCA O METODO UTILIZADO
        # ===========================================================================

        # (Opcional) Preenche vazio com ''
        df_base['MATRÍCULA CAPITAL'] = df_base['MATRÍCULA CAPITAL'].fillna('')

        # (Opcional) Preenche vazio com ''
        df_base['MATRÍCULA CLICK'] = df_base['MATRÍCULA CLICK'].fillna('')

        mask_metodo_vazio = (df_base['METODO'] == '') & (
                (df_base['MATRÍCULA CAPITAL'] != '') | (df_base['MATRÍCULA CLICK'] != ''))

        # print(mask_metodo_vazio)

        df_base.loc[mask_metodo_vazio, 'METODO'] = 'ATRIBUIDO POR PARCELAS SOMADAS'

        # atribuir_por_combinacao_de_soma_exata(df_base, df_capital, df_click)


    def valor_proximo(self, base, capital, click):
        df_base = base.copy()
        df_capital = capital.copy()
        df_click = click.copy()
        limite_similaridade_percentual = 0.20  # 20%

        # Garante que os tipos de dados sejam consistentes para o merge e comparações
        for df in [df_capital, df_click]:
            if 'CPF' in df.columns:
                df['CPF'] = df['CPF'].astype(str).str.strip()
        df_base['CPF'] = df_base['CPF'].astype(str).str.strip()

        # 2. FILTRO: IDENTIFICA AS LINHAS A SEREM PROCESSADAS
        # Usamos .fillna('') para tratar tanto nulos (NaN) quanto strings vazias de forma segura
        filtro_vazias = (df_base['MATRÍCULA CAPITAL'].fillna('') == '') & \
                        (df_base['MATRÍCULA CLICK'].fillna('') == '')

        # Se não houver linhas para processar, retorna a base sem alterações.
        if not filtro_vazias.any():
            print("Nenhuma linha com matrículas vazias para processar. Função encerrada.")
            return df_base

        print(f"Encontradas {filtro_vazias.sum()} linhas com matrículas vazias para processar.")

        # 3. PREPARAÇÃO DOS DADOS DE BUSCA (Lógica mantida, pois está ótima)
        colunas_parcela = ['parcela 100', 'parcela 70', 'parcela 30']

        df_capital_long = pd.melt(df_capital, id_vars=['CPF', 'matrícula'], value_vars=colunas_parcela,
                                value_name='Valor Parcela')
        df_capital_long['Fonte'] = 'Capital'

        df_click_long = pd.melt(df_click, id_vars=['CPF', 'matrícula'], value_vars=colunas_parcela,
                                value_name='Valor Parcela')
        df_click_long['Fonte'] = 'Click'

        df_fontes_combinadas = pd.concat([df_capital_long, df_click_long], ignore_index=True)
        df_fontes_combinadas.dropna(subset=['Valor Parcela'], inplace=True)
        df_fontes_combinadas = df_fontes_combinadas[df_fontes_combinadas['Valor Parcela'] > 0]

        print("Fontes de dados 'CAPITAL' e 'CLICK' foram preparadas.")

        # 4. LÓGICA PRINCIPAL: ITERAR E ATUALIZAR O DATAFRAME ORIGINAL

        # Iteramos apenas nas linhas que correspondem ao nosso filtro de vazias
        for index, linha_base in df_base[filtro_vazias].iterrows():
            cpf_base = linha_base['CPF']
            parcela_base = linha_base['PARCELA BASE']

            if pd.isna(cpf_base) or pd.isna(parcela_base) or parcela_base <= 0:
                continue

            df_candidatos = df_fontes_combinadas[df_fontes_combinadas['CPF'] == cpf_base].copy()

            if df_candidatos.empty:
                continue

            df_candidatos['Diferenca'] = (df_candidatos['Valor Parcela'] - parcela_base).abs()
            limite_diferenca_valor = parcela_base * limite_similaridade_percentual
            df_candidatos_validos = df_candidatos[df_candidatos['Diferenca'] <= limite_diferenca_valor]

            if df_candidatos_validos.empty:
                continue

            melhor_match = df_candidatos_validos.loc[df_candidatos_validos['Diferenca'].idxmin()]
            matricula_encontrada = melhor_match['matrícula']
            fonte_encontrada = melhor_match['Fonte']

            # CORREÇÃO PRINCIPAL: Atualiza o df_base original usando o 'index' da linha
            if fonte_encontrada == 'Capital':
                df_base.loc[index, 'MATRÍCULA CAPITAL'] = matricula_encontrada
                df_base.loc[index, 'METODO'] = 'ATRIBUIDO VALOR PROXIMO'
            elif fonte_encontrada == 'Click':
                df_base.loc[index, 'MATRÍCULA CLICK'] = matricula_encontrada
                df_base.loc[index, 'METODO'] = 'ATRIBUIDO VALOR PROXIMO'

            '''print(
                f"Progresso: {index + 1}/{total_linhas} | CPF: {cpf_base} -> Matrícula encontrada na fonte '{fonte_encontrada}'")'''

        # ===========================================================================
        #                       COLOCA O METODO UTILIZADO
        # ===========================================================================

        # (Opcional) Preenche vazio com ''
        df_base['MATRÍCULA CAPITAL'] = df_base['MATRÍCULA CAPITAL'].fillna('')

        # (Opcional) Preenche vazio com ''
        df_base['MATRÍCULA CLICK'] = df_base['MATRÍCULA CLICK'].fillna('')

        mask_metodo_vazio = (df_base['METODO'] == '') & (
                (df_base['MATRÍCULA CAPITAL'] != '') | (df_base['MATRÍCULA CLICK'] != ''))

        # print(mask_metodo_vazio)

        df_base.loc[mask_metodo_vazio, 'METODO'] = 'ATRIBUIDO PROXIMIDADE DE PARCELA'


    def calcular_saldos_restantes(self, base, capital, click):
        """
        Calcula o saldo restante para cada matrícula em CAPITAL e CLICK,
        subtraindo o valor já atribuído na BASE do valor total (parcela 100).
        """
        print("Calculando saldos remanescentes das matrículas...")

        df_base = base.copy()
        df_capital_original = capital.copy()
        df_click_original = click.copy()

        # Isola as linhas da BASE que já tiveram uma matrícula atribuída
        base_com_capital = df_base[df_base['MATRÍCULA CAPITAL'].notna() & (df_base['MATRÍCULA CAPITAL'] != '')]
        base_com_click = df_base[df_base['MATRÍCULA CLICK'].notna() & (df_base['MATRÍCULA CLICK'] != '')]

        # Calcula o total já usado para cada matrícula
        uso_capital = base_com_capital.groupby('MATRÍCULA CAPITAL')['PARCELA BASE'].sum().reset_index().rename(
            columns={'MATRÍCULA CAPITAL': 'matrícula', 'PARCELA BASE': 'Valor_Ja_Usado'})
        uso_click = base_com_click.groupby('MATRÍCULA CLICK')['PARCELA BASE'].sum().reset_index().rename(
            columns={'MATRÍCULA CLICK': 'matrícula', 'PARCELA BASE': 'Valor_Ja_Usado'})

        # Junta o valor usado de volta aos dataframes originais
        capital_com_uso = pd.merge(df_capital_original, uso_capital, on='matrícula', how='left')
        print(f'Colunas de capital_com_uso: {capital_com_uso.columns}')
        click_com_uso = pd.merge(df_click_original, uso_click, on='matrícula', how='left')

        # Preenche com 0 o valor usado para matrículas que ainda não foram utilizadas
        capital_com_uso['Valor_Ja_Usado'] = capital_com_uso['Valor_Ja_Usado'].fillna(0)
        click_com_uso['Valor_Ja_Usado'] = click_com_uso['Valor_Ja_Usado'].fillna(0)

        # Calcula o SALDO REMANESCENTE
        capital_com_uso['Saldo_Remanescente'] = (capital_com_uso['parcela 100'] - capital_com_uso['Valor_Ja_Usado']).round(
            2)
        click_com_uso['Saldo_Remanescente'] = (click_com_uso['parcela 100'] - click_com_uso['Valor_Ja_Usado']).round(2)

        print("Cálculo de saldos finalizado.")

        # Retorna os dataframes de CAPITAL e CLICK com a nova coluna de saldo
        return capital_com_uso, click_com_uso


    # Daremos um novo nome para ficar claro que ela usa o saldo
    def atribuir_por_combinacao_de_soma_exata(self, base, capital, click):
        """
        Versão modificada que usa o 'Saldo_Remanescente' como alvo,
        em vez do valor estático da 'parcela 100'.
        """
        print("Iniciando atribuição por combinação de soma exata (usando saldo remanescente)...")

        df_base = base.copy()
        capital_com_saldo, click_com_saldo = self.calcular_saldos_restantes(df_base, capital, click)

        df_capital = capital.copy()
        df_click = click.copy()

        # --- ALTERAÇÃO PRINCIPAL AQUI ---
        # Prepara as fontes de dados usando a coluna 'Saldo_Remanescente'

        df_capital_alvo = capital_com_saldo[['CPF', 'matrícula', 'Saldo_Remanescente']].copy()
        df_capital_alvo.rename(columns={'Saldo_Remanescente': 'Valor_Target'}, inplace=True)
        df_capital_alvo['Fonte'] = 'Capital'

        df_click_alvo = click_com_saldo[['CPF', 'matrícula', 'Saldo_Remanescente']].copy()
        df_click_alvo.rename(columns={'Saldo_Remanescente': 'Valor_Target'}, inplace=True)
        df_click_alvo['Fonte'] = 'Click'

        # O resto da função continua exatamente igual à anterior...
        df_fontes = pd.concat([df_capital_alvo, df_click_alvo], ignore_index=True)
        df_fontes.dropna(subset=['Valor_Target'], inplace=True)
        # Permite saldos maiores que zero
        df_fontes = df_fontes[df_fontes['Valor_Target'] > 0.001]


        filtro_vazias = (df_base['MATRÍCULA CAPITAL'].fillna('') == '') & (df_base['MATRÍCULA CLICK'].fillna('') == '')
        if not filtro_vazias.any():
            print("Nenhuma linha com matrículas vazias para processar.")
            return df_base

        base_agrupada = df_base[filtro_vazias].groupby('CPF').apply(
            lambda x: list(zip(x['PARCELA BASE'], x.index))
        ).reset_index(name='Parcelas_Base')

        matches_encontrados = []

        # 3. LOOP PRINCIPAL - ITERA SOBRE CADA CPF QUE TEM PARCELAS VAZIAS
        for _, row in base_agrupada.iterrows():
            cpf_atual = row['CPF']
            parcelas_disponiveis = row['Parcelas_Base']

            alvos_disponiveis = df_fontes[df_fontes['CPF'] == cpf_atual].to_dict('records')

            # print('parcelas disponiveis:\n', parcelas_disponiveis)
            # print('alvos disponiveis:\n', alvos_disponiveis)

            houve_match_nesta_rodada = True
            while houve_match_nesta_rodada and parcelas_disponiveis and alvos_disponiveis:
                houve_match_nesta_rodada = False

                for tamanho_combinacao in range(2, len(parcelas_disponiveis) + 1):
                    if houve_match_nesta_rodada: break

                    for combo in combinations(parcelas_disponiveis, tamanho_combinacao):
                        soma_combo = sum(p[0] for p in combo)

                        for alvo in alvos_disponiveis:
                            if np.isclose(soma_combo, alvo['Valor_Target']):
                                indices_do_match = [p[1] for p in combo]
                                # print(
                                #     f"MATCH! CPF {cpf_atual}: {len(indices_do_match)} parcelas somando {soma_combo:.2f} bateram com a matrícula {alvo['matrícula']} da fonte {alvo['Fonte']}.")

                                matches_encontrados.append({
                                    'indices': indices_do_match,
                                    'matricula': alvo['matrícula'],
                                    'fonte': alvo['Fonte']
                                })

                                parcelas_disponiveis = [p for p in parcelas_disponiveis if p not in combo]
                                alvos_disponiveis.remove(alvo)

                                houve_match_nesta_rodada = True
                                break

                        if houve_match_nesta_rodada: break

        # 4. ATUALIZAÇÃO FINAL DO DATAFRAME BASE
        if not matches_encontrados:
            print("Nenhuma combinação de soma exata foi encontrada.")
            return df_base

        print(f"\nForam encontradas {len(matches_encontrados)} combinações. Atualizando a base de dados...")
        for match in matches_encontrados:
            indices = match['indices']
            matricula = match['matricula']
            fonte = match['fonte']

            coluna_alvo = f"MATRÍCULA {fonte.upper()}"
            df_base.loc[indices, coluna_alvo] = matricula
            df_base.loc[indices, 'METODO'] = 'COMBINACAO SOMA EXATA'

        self.atribuir_por_combinacao_soma_proxima(df_base, df_capital, df_click)
        return None


    def atribuir_por_combinacao_soma_proxima(self, base, capital, click):
        """
        Versão modificada que usa o 'Saldo_Remanescente' como alvo para encontrar a
        combinação de parcelas com a soma MAIS PRÓXIMA.
        """
        print("Iniciando estratégia final com saldo: Atribuição por combinação de soma mais próxima...")

        # 1. PREPARAÇÃO
        df_base = base.copy()
        capital_com_saldo, click_com_saldo = self.calcular_saldos_restantes(df_base, capital, click)
        df_capital = capital.copy()
        df_click = click.copy()

        df_capital_alvo = capital_com_saldo[['CPF', 'matrícula', 'Saldo_Remanescente']].copy().rename(
            columns={'Saldo_Remanescente': 'Valor_Target'})
        df_capital_alvo['Fonte'] = 'Capital'
        df_click_alvo = click_com_saldo[['CPF', 'matrícula', 'Saldo_Remanescente']].copy().rename(
            columns={'Saldo_Remanescente': 'Valor_Target'})
        df_click_alvo['Fonte'] = 'Click'

        df_fontes = pd.concat([df_capital_alvo, df_click_alvo], ignore_index=True)
        df_fontes.dropna(subset=['Valor_Target'], inplace=True)
        # df_fontes = df_fontes[df_fontes['Valor_Target'] > 0.001]
        df_fontes = df_fontes[df_fontes['Valor_Target'] > 0.001]

        # 2. AGRUPAR PARCELAS (Sem alterações)
        filtro_vazias = (df_base['MATRÍCULA CAPITAL'].fillna('') == '') & (df_base['MATRÍCULA CLICK'].fillna('') == '')
        if not filtro_vazias.any():
            print("Nenhuma linha com matrículas vazias para processar.")
            return df_base

        base_agrupada = df_base[filtro_vazias].groupby('CPF').apply(
            lambda x: list(zip(x['PARCELA BASE'], x.index))
        ).reset_index(name='Parcelas_Base')

        matches_encontrados_geral = []

        # 3. LOOP PRINCIPAL
        for _, row in base_agrupada.iterrows():
            cpf_atual = row['CPF']
            parcelas_disponiveis = row['Parcelas_Base']
            alvos_disponiveis = df_fontes[df_fontes['CPF'] == cpf_atual].to_dict('records')

            while True:
                if not parcelas_disponiveis or not alvos_disponiveis:
                    break

                melhor_match_rodada = {'diferenca': np.inf, 'indices': None, 'matricula': None, 'fonte': None,
                                    'combo': None, 'alvo': None}

                for tamanho_combinacao in range(1, len(parcelas_disponiveis) + 1):
                    for combo in combinations(parcelas_disponiveis, tamanho_combinacao):
                        soma_combo = round(sum(p[0] for p in combo), 2)

                        for alvo in alvos_disponiveis:
                            valor_alvo = alvo['Valor_Target']

                            # <<< NOVA VALIDAÇÃO APLICADA AQUI >>>
                            # A soma da combinação não pode ser maior que o saldo do alvo.
                            # Adicionamos uma pequena tolerância (0.001) para segurança com floats.
                            if soma_combo <= valor_alvo + 0.001:

                                # A diferença agora é calculada sem o valor absoluto, pois já garantimos que não será negativa.
                                diferenca_atual = valor_alvo - soma_combo

                                # Compara com o melhor match válido encontrado até agora.
                                if diferenca_atual < melhor_match_rodada['diferenca']:
                                    melhor_match_rodada.update({
                                        'diferenca': diferenca_atual,
                                        'indices': [p[1] for p in combo],
                                        'matricula': alvo['matrícula'],
                                        'fonte': alvo['Fonte'],
                                        'combo': combo,
                                        'alvo': alvo
                                    })

                if melhor_match_rodada['matricula'] is not None:
                    matches_encontrados_geral.append(melhor_match_rodada)
                    # print(
                    #     f"MATCH (Rodada)! CPF {cpf_atual}: {len(melhor_match_rodada['indices'])} parcelas encontraram matrícula {melhor_match_rodada['matricula']}.")
                    parcelas_disponiveis = [p for p in parcelas_disponiveis if p not in melhor_match_rodada['combo']]
                    alvos_disponiveis.remove(melhor_match_rodada['alvo'])
                else:
                    break

        # 4. ATUALIZAÇÃO FINAL (Sem alterações)
        if not matches_encontrados_geral:
            print("Nenhuma correspondência por combinação foi encontrada.")
            return df_base

        print(f"\nForam encontradas {len(matches_encontrados_geral)} combinações no total. Atualizando a base...")
        for match in matches_encontrados_geral:
            indices = match['indices']
            if filtro_vazias.loc[indices].all():
                matricula = match['matricula']
                fonte = match['fonte']

                coluna_alvo = f"MATRÍCULA {fonte.upper()}"
                df_base.loc[indices, coluna_alvo] = matricula
                df_base.loc[indices, 'METODO'] = 'COMBINACAO SOMA PROXIMA'

        # print(df_base.loc[df_base['CPF'] == '741.699.399-72'], ['CPF', 'MATRÍCULA CAPITAL', 'MATRÍCULA CLICK'])

        self.atribuir_por_valor_individual_proximo(df_base, df_capital, df_click)

    def atribuir_por_valor_individual_proximo(self, base, capital, click):
        """
        Função final de "limpeza". Para as linhas restantes, busca individualmente
        a matrícula cujo Saldo Remanescente seja o mais próximo da PARCELA BASE,
        usando a diferença absoluta.
        """
        print("Iniciando última etapa: Atribuição por valor individual mais próximo...")

        # 1. PREPARAÇÃO
        df_base = base.copy()
        capital_com_saldo, click_com_saldo = self.calcular_saldos_restantes(df_base, capital, click)

        # Prepara as fontes de dados com o Saldo Remanescente
        df_capital_alvo = capital_com_saldo[['CPF', 'matrícula', 'parcela 100', 'parcela 70', 'parcela 30', 'Saldo_Remanescente']].copy().rename(
            columns={'Saldo_Remanescente': 'Valor_Target'})
        df_capital_alvo['Fonte'] = 'Capital'
        df_capital_alvo['parcela 100'] = capital_com_saldo['parcela 100']
        df_capital_alvo['parcela 70'] = capital_com_saldo['parcela 70']
        df_capital_alvo['parcela 30'] = capital_com_saldo['parcela 30']
        df_click_alvo = click_com_saldo[['CPF', 'matrícula', 'parcela 100', 'parcela 70', 'parcela 30', 'Saldo_Remanescente']].copy().rename(
            columns={'Saldo_Remanescente': 'Valor_Target'})
        df_click_alvo['Fonte'] = 'Click'
        df_click_alvo['parcela 100'] = click_com_saldo['parcela 100']
        df_click_alvo['parcela 70'] = click_com_saldo['parcela 70']
        df_click_alvo['parcela 30'] = click_com_saldo['parcela 30']

        df_fontes = pd.concat([df_capital_alvo, df_click_alvo], ignore_index=True)
        df_fontes.dropna(subset=['Valor_Target'], inplace=True)
        # Nesta função, podemos até considerar alvos com saldo zero ou negativo se a regra de negócio permitir
        # Mas manteremos > 0 por segurança.
        df_fontes = df_fontes[df_fontes['Valor_Target'] > 0]

        # 2. FILTRO E LOOP
        filtro_vazias = (df_base['MATRÍCULA CAPITAL'].fillna('') == '') & (df_base['MATRÍCULA CLICK'].fillna('') == '')
        if not filtro_vazias.any():
            print("Nenhuma linha restante para processar.")
            return df_base

        print(f"Tentando encontrar matrículas para as {filtro_vazias.sum()} linhas restantes...")

        # Iteramos individualmente sobre cada linha que ainda está vazia
        for index, linha_base in df_base[filtro_vazias].iterrows():
            cpf_base = linha_base['CPF']
            parcela_base = linha_base['PARCELA BASE']

            if pd.isna(cpf_base) or pd.isna(parcela_base):
                continue

            # Pega todos os alvos disponíveis para o CPF da linha
            alvos_do_cpf = df_fontes[df_fontes['CPF'] == cpf_base].to_dict('records')

            if not alvos_do_cpf:
                continue

            melhor_match_linha = {'diferenca': np.inf, 'matricula': None, 'fonte': None}

            # Para cada alvo, calcula a diferença absoluta
            for alvo in alvos_do_cpf:
                # <<< LÓGICA PRINCIPAL: Usa abs() para encontrar o mais próximo, sem restrições >>>
                diferenca_atual = abs(parcela_base - alvo['Valor_Target'])

                if diferenca_atual < melhor_match_linha['diferenca']:
                    melhor_match_linha.update({
                        'diferenca': diferenca_atual,
                        'matricula': alvo['matrícula'],
                        'fonte': alvo['Fonte']
                    })

            # Se um melhor match foi encontrado para esta linha, atribui o resultado
            if melhor_match_linha['matricula'] is not None:
                fonte = melhor_match_linha['fonte']
                matricula = melhor_match_linha['matricula']
                coluna_alvo = f"MATRÍCULA {fonte.upper()}"

                df_base.loc[index, coluna_alvo] = matricula
                df_base.loc[index, 'METODO'] = 'VALOR INDIVIDUAL PROXIMO'

        # Caminho do novo arquivo Excel
        # arquivo_saida = fr'{self.caminho}\MATRÍCULAS ENCONTRADAS DE GOV SC - {str(datetime.now().month).zfill(2)}-{datetime.now().year}.xlsx'
        arquivo_saida = os.path.join(self.caminho, f'MATRÍCULAS ENCONTRADAS DE GOV SC - {str(datetime.now().month).zfill(2)}-{datetime.now().year}.xlsx')

        # Cria o arquivo Excel com várias abas
        try:
            with pd.ExcelWriter(arquivo_saida, engine='openpyxl') as writer:
                df_base.to_excel(writer, sheet_name='BASE', index=False)
                df_capital_alvo.to_excel(writer, sheet_name='CAPITAL', index=False)
                df_click_alvo.to_excel(writer, sheet_name='CLICK', index=False)
        except Exception as e:
            print(f'Erro ao salvar as matrículas tratadas: ', e)

        self.df_final = df_base

