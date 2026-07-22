import pandas as pd
import re
from thefuzz import fuzz
import os
from python.ESTEIRAS import load_esteiras
from python.funcoes_comuns import FRONT_TRABALHADO
import itertools
import numpy as np

# front_bruto = r"F:\Dados\NOVA ESTRUTURA\LANÇAMENTO CARTÕES\TRABALHANDO\2026\05 - Maio\GUIDO ROBOTO\PAIUI\relatorio_2026-04-16_13-19-47_parte_1.csv"
# andamento_bruto = r"F:\Dados\NOVA ESTRUTURA\LANÇAMENTO CARTÕES\TRABALHANDO\2026\05 - Maio\GUIDO ROBOTO\PAIUI\ANDAMENTO UNIFICADO GOV PI.csv"
# caminho = r"F:\Dados\NOVA ESTRUTURA\LANÇAMENTO CARTÕES\TRABALHANDO\2026\05 - Maio\GUIDO ROBOTO\PAIUI\TRABALHADOS"
# funcao_bruto = r"F:\Dados\NOVA ESTRUTURA\LANÇAMENTO CARTÕES\TRABALHANDO\2026\05 - Maio\GUIDO ROBOTO\PAIUI\FUNÇÃO GOV PI 04.2026.csv"

# front = pd.read_csv(front_bruto, encoding="utf-8-sig", sep=";", on_bad_lines="skip", low_memory=False)
# andamento = pd.read_csv(andamento_bruto, encoding="latin1", sep=";", on_bad_lines="skip", low_memory=False)
# funcao = pd.read_csv(funcao_bruto, encoding="utf-8-sig", sep=";", on_bad_lines="skip", low_memory=False)


class ANDAMENTO:
    def __init__(self, front, convenio, caminho, andamento=None, funcao=None):
        self.front = front
        self.andamento = andamento
        self.convenio = convenio
        self.caminho = caminho
        self.esteiras = load_esteiras()
        self.funcao = funcao

    def unifica_front_funcao(self):
        front = self.front
        funcao = self.funcao

        if funcao is None:
            print('\nDEBUG class ANDAMENTO -> funcao unifica_fron_funcao -> Arquivo "Função" é nulo, retornando "front" sem tratamento\n')
            return front
        # tipos dos contratos de cada dataframe
        '''print('Tipo da coluna Contrato do Front', front['Contrato'].dtype)
        print('Tipo da coluna NR_PROP do Funcao', funcao['NR_PROP'].dtype)'''

        contrato_front = front['Contrato']
        ccb_tratado = front['CCB'].astype(str).str.slice(0, 9).fillna(0).astype('float64')

        ccb_tratado = ccb_tratado.astype('int64')

        # Tira os contratos do Front que já existem no Função
        funcao = funcao[(~funcao['NR_PROP'].isin(contrato_front)) & (~funcao["ORIGEM_3"].str.contains("IV PROMOTORA"))].copy()

        # Tira os contratos CCB do Front que também existem no Função
        funcao = funcao[~funcao['NR_PROP'].isin(ccb_tratado)].copy()

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
        funcao_ajustado = funcao[list(mapeamento.keys())].rename(columns=mapeamento)

        # 3. Use o concat para unir os dois DataFrames
        # O ignore_index=True serve para gerar um novo índice sequencial no DF final
        front_unif = pd.concat([front, funcao_ajustado], ignore_index=True)

        # Preenche o resto das colunas necessárias com valores genéricos, para não ficarem vazias
        front_unif['Esteira'] = front_unif['Esteira'].fillna("INTEGRADO")
        front_unif['Orbital'] = front_unif['Orbital'].fillna("NAO")
        front_unif['Consignataria'] = front_unif['Consignataria'].fillna("CAPITAL CONSIG ")
        front_unif['Status'] = front_unif['Status'].fillna("INTEGRADO")
        front_unif['Acao Judicial'] = front_unif['Acao Judicial'].fillna("NAO")
        front_unif['Obito'] = front_unif['Obito'].fillna("NAO")

        print('front unif finalzin:\n', front_unif.tail())

        # front_unif.to_excel(rf"{self.caminho}\Teste_front.xlsx", index=False)

        return front_unif
    
    def andamento_func_front(self):
        front = self.front
        # 1. VALIDAÇÃO E TRATAMENTO INICIAL
        if self.andamento is None:
            return front

        # --- NOVO FILTRO DE OBS ---
        # Separamos o que já tem OBS (não mexe) do que está vazio (será processado)
        # Garantimos que tratamos NaN como string vazia para o filtro funcionar
        if "OBS" not in front.columns and "PRAZO" not in front.columns:
            front.insert(23, 'PRAZO', '', True)
            front.insert(24, 'OBS', '', True)

        front['OBS'] = front['OBS'].fillna('')
        front_preenchido = front[front['OBS'] != ''].copy()
        front_para_processar = front[front['OBS'] == ''].copy()

        # Se não houver nada para processar, já retorna o original
        if front_para_processar.empty:
            return front
        # --------------------------

        # Ordenar as esteiras de A-Z
        # Puxa a lista de esteiras prioritárias
        esteiras_lancar = self.esteiras

        # 1. Ordem de prioridade para o Tipo de Operação
        ordem = {
            'CARTAO BENEFICIO': 1,
            'EMPRESTIMO': 2
        }
        front_para_processar['prioridade_operacao'] = front_para_processar['Tipo Operacao'].map(ordem).fillna(3)

        # 2. NOVA LÓGICA: Ordem de prioridade para a Esteira
        # Se a 'Esteira' atual estiver dentro da lista 'esteiras_lancar', recebe 1. Senão, recebe 2.

        front_para_processar['prioridade_esteira'] = np.where(front_para_processar['Esteira'].isin(esteiras_lancar), 1, 2)

        # 3. Ordenação combinada
        # Ele vai ordenar primeiro pelo Tipo Operação, depois vai puxar as esteiras_lancar para cima, 
        # e por último vai desempatar por ordem alfabética da própria coluna 'Esteira'
        front_para_processar = front_para_processar.sort_values(
            by=['prioridade_esteira', 'prioridade_operacao', 'Esteira'],
            ascending=[True, True, True]
        )
        
        front_para_processar.to_excel(os.path.join(self.caminho, f'FRONT DO ANDAMENTO COM AS PRIORIDADES {self.convenio}.xlsx'), index=False)

        if front_para_processar['Prestacao'].dtype != 'float64':
            front_para_processar['Prestacao'] = front_para_processar['Prestacao'].astype(str).str.replace('.', '').str.replace(',', '.')
            front_para_processar['Prestacao'] = pd.to_numeric(front_para_processar['Prestacao'], errors='coerce')
            


        # Criamos cópias para evitar SettingWithCopyWarning
        # self.andamento = self.andamento[self.andamento['Prazo Total'] != 1].copy()

        # Remoção de cartão de crédito com prazo 0 ou 1
        self.andamento = self.andamento[~((self.andamento['Modalidade'].isin(['Cartão de Crédito', 'Cartão de Crédito [Prefeitura]', 'Cartão de Crédito [Previdência]'])) & (self.andamento['Prazo Total'].isin([0, 1])))].copy()

        '''if 'Clone na instituição' not in self.andamento.columns:
            self.andamento.insert(2, 'Clone na instituição', self.andamento['Código na instituição'])'''


        if 'Contrato de Andamento' not in self.andamento.columns:
            self.andamento.insert(2, 'Contrato de Andamento', self.andamento['Código na instituição'])
        
        # Padronização de valores numéricos para os filtros funcionarem
        if self.andamento['Valor da Parcela'].dtype != 'float64':
            self.andamento['Valor da Parcela'] = self.andamento['Valor da Parcela'].astype(str)\
                .str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
            self.andamento['Valor da Parcela'] = pd.to_numeric(self.andamento['Valor da Parcela'], errors='coerce')

        self.andamento = self.andamento.drop_duplicates(subset=['Código']).copy()
        # Filtro de Previdência/Seguros/Mensalidade (Valores 20, 40, 60)

        andam_referencia_prazos = self.andamento[~(((self.andamento['Modalidade'] == 'Previdência') | 
                                                    (self.andamento['Modalidade'] == 'Seguros') | 
                                                    (self.andamento['Modalidade'] == 'Mensalidade')) 
                                                & ((self.andamento['Valor da Parcela'] <= 20) | 
                                                    (self.andamento['Valor da Parcela'] == 40) | 
                                                    (self.andamento['Valor da Parcela'] == 60)))].copy()
        
        # andam_file_simples = self.extrair_contratos_simples(andam_referencia_prazos, front_para_processar)
            
        
        front_trabalhado_funcao = FRONT_TRABALHADO(front=front, convenio=self.convenio, caminho=self.caminho)

        front_trabalhado_puro = front_trabalhado_funcao.tratamento_front()

        # 2. PROCESSAMENTO DE CONTRATOS (Usando apenas o front_para_processar)
        andam_file = self.processar_contrato_simples(andam_referencia_prazos, front_para_processar, tolerancia_bool=False, trabalhados_so_ativos=front_trabalhado_puro)
        andam_file = self.processar_contrato_simples(andam_file, front_para_processar, tolerancia_bool=True, trabalhados_so_ativos=None)
        andam_file = self.associar_por_soma_andamento(andam_file, front_para_processar, tolerancia_bool=False, front_so_ativos=front_trabalhado_puro)
        andam_file = self.associar_por_soma_andamento(andam_file, front_para_processar, tolerancia_bool=True, front_so_ativos=None)
        andam_file, front_base = self.processar_contratos_otimizado(andam_file, front_para_processar)
        andam_file = self.extrair_contratos_com_referencia(andam_file, front_para_processar, 'Contrato de Andamento')
        print(f'Andamento depois de extrair_contratos\n{andam_file.columns}')

        # Terceira passada
        andam_file, front_base = self.processar_contratos_otimizado(andam_file, front_para_processar)
        andam_file = self.extrair_contratos_com_referencia(andam_file, front_para_processar, 'Contrato Editado 1')

        # 3. EXTRAÇÃO DOS PRAZOS
        # colunas_contratos = [col for col in andam_file.columns if 'Contrato' in col or 'Código' in col]
        colunas_contratos = [col for col in andam_file.columns if 'Contrato Editado' in col]
        print(f'Colunas contrato {colunas_contratos}')
        
        contrato_para_prazo = {}
        for _, row in andam_file.iterrows():
            prazo = row.get('Prazo Total')
            if pd.notna(prazo):
                for col in colunas_contratos:
                    id_contrato = row.get(col)
                    if pd.notna(id_contrato):
                        contrato_para_prazo[str(id_contrato).strip()] = prazo

        # Aplica o mapeamento APENAS no que foi processado
        front_para_processar['PRAZO'] = front_para_processar['Contrato'].astype(str).str.strip().map(contrato_para_prazo)
        
        # Regra de Negócio Final: Marcação de OBS
        status_prazo = front_para_processar['PRAZO'].fillna('')
        front_para_processar['PRAZO'] = front_para_processar['PRAZO'].fillna('')
        '''if self.convenio in ['PREF. NATAL', 'PREF. PALMAS', 'PREV. PALMAS']:
            cond_prazo = ~status_prazo.isin(['', '0', 0, '1', 1])
        else:
            cond_prazo = ~status_prazo.isin(['', '1', 1])'''
        # front_para_processar.loc[cond_prazo & (front_para_processar['OBS'] == ''), 'OBS'] = 'NÃO LANÇAR - PRAZO'
        cond_prazo = ~status_prazo.isin([''])
        front_para_processar.loc[cond_prazo & (front_para_processar['OBS'] == ''), 'OBS'] = 'NÃO LANÇAR - PRAZO'

        # --- FINALIZAÇÃO ---
        # Unimos o que filtramos no início com o que acabamos de processar
        front_final = pd.concat([front_preenchido, front_para_processar], ignore_index=True)

        try:
            andam_file.to_excel(os.path.join(self.caminho, f"ANDAMENTO GERAL {self.convenio}.xlsx"), index=False)
        except Exception as e:
            print(f"DEBUG: ERRO AO SALVAR ANDAMENTO GERAL: {e}")

        front_final.to_excel(rf"{self.caminho}\Teste_front.xlsx", index=False)

        return front_final
    
    def processar_contrato_simples(self, df_andamento, df_front_puro, tolerancia_bool=False, trabalhados_so_ativos=None):
        # 1. Limpeza e Padronização
        df_andamento = df_andamento.drop_duplicates(subset=['Código']).copy()

        if trabalhados_so_ativos is not None:
            df_front = trabalhados_so_ativos
        else:
            df_front = df_front_puro

        
        for df in [df_andamento, df_front]:
            df['CPF'] = df['CPF'].astype(str).str.strip()

        # Tratamento de valores numéricos (Andamento)
        if df_andamento['Valor da Parcela'].dtype != 'float64':
            df_andamento['Valor da Parcela'] = df_andamento['Valor da Parcela'].astype(str).str.replace(".", "").str.replace(",", ".")
            df_andamento['Valor da Parcela'] = pd.to_numeric(df_andamento['Valor da Parcela'], errors='coerce')
        df_andamento['Valor da Parcela'] = df_andamento['Valor da Parcela'].astype(float).round(2)

        # Tratamento de valores numéricos (Front)
        if df_front['Prestacao'].dtype != 'float64':
            df_front['Prestacao'] = df_front['Prestacao'].astype(str).str.replace(".", "").str.replace(",", ".")
            df_front['Prestacao'] = pd.to_numeric(df_front['Prestacao'], errors='coerce')
        df_front['Prestacao'] = df_front['Prestacao'].astype(float).round(2)

        # 2. Configuração de colunas de destino
        if 'Contrato de Andamento' not in df_andamento.columns:
            df_andamento.insert(2, 'Contrato de Andamento', df_andamento['Código na instituição'])

        col_destino = 'Contrato Editado 1' if 'Contrato Editado 1' in df_andamento.columns else 'Contrato de Andamento'
        
        # 3. Filtrar Front disponível
        ocupados = df_andamento['Código na instituição'].dropna().unique()
        df_front_dispo = df_front[~df_front['Contrato'].astype(str).isin(map(str, ocupados))].copy()

        # 4. Criar dicionário indexado por CPF
        # O valor será uma lista de tuplas: [(contrato, valor_prestacao), ...]
        dict_front = {}
        for _, row in df_front_dispo.iterrows():
            cpf = row['CPF']
            if cpf not in dict_front:
                dict_front[cpf] = []
            dict_front[cpf].append((row['Contrato'], row['Prestacao']))

        # INJEÇÃO DE DEBUG AQUI:
        cpf_teste = '505.029.723-00' # Coloque o CPF que está puxando errado
        if cpf_teste in dict_front:
            print(f"DEBUG - Opções para o CPF {cpf_teste}: {dict_front[cpf_teste]}")
        else:
            print(f"DEBUG - CPF {cpf_teste} não tem contratos disponíveis no Front.")

        # 5. Busca com Tolerância (0.10)
        vazios = df_andamento[df_andamento[col_destino].isna() | (df_andamento[col_destino] == "")].copy()
        tolerancia = 0.10 if tolerancia_bool else 0

        for idx, row in vazios.iterrows():
            cpf_busca = row['CPF']
            valor_alvo = float(row['Valor da Parcela'])
            
            if cpf_busca in dict_front:
                lista_opcoes = dict_front[cpf_busca]

                '''if cpf_busca == '037.685.094-94':
                    print(f'Valor da Parcela\n{valor_alvo}\n')
                    print(f'Prestacao\n{dict_front.loc[dict_front['CPF'] == cpf_busca, 'Prestacao']}')'''
                
                # Procurar na lista de contratos deste CPF um que esteja na margem
                for i, (contrato_front, valor_front) in enumerate(lista_opcoes):
                    if abs(valor_alvo - valor_front) <= tolerancia:
                        # Match encontrado dentro da tolerância!
                        # Force a conversão para string no momento da atribuição
                        df_andamento.at[idx, col_destino] = str(contrato_front)
                        
                        # Remove esse contrato da lista para não ser usado de novo
                        lista_opcoes.pop(i)
                        break 

        sobraram = df_andamento[df_andamento[col_destino].isna() | (df_andamento[col_destino] == "")].shape[0]
        print(f'Quantos vazios sobraram após busca com tolerância? {sobraram}')

        return df_andamento.fillna('')
    
    # Cole esta função dentro da sua classe, junto com as outras
    def associar_por_soma_andamento(self, df_andamento: pd.DataFrame, df_front_puro: pd.DataFrame,  max_linhas_somadas: int = 5, tolerancia_bool=False, front_so_ativos=None) -> pd.DataFrame:
        """
        Busca no Front os contratos que podem ser formados pela SOMA de múltiplas linhas 
        no df_andamento para o mesmo CPF.
        """
        print("\nIniciando busca por soma de parcelas (Subset Sum)...")

        tolerancia = 1 if tolerancia_bool else 0

        if front_so_ativos is not None:
            df_front = front_so_ativos
        else:
            df_front = df_front_puro

        # df_front = df_front.drop(columns='prioridade')
        
        # Garante que as colunas alvo existem e preenche os vazios do Andamento
        col_destino = 'Contrato de Andamento'
        if col_destino not in df_andamento.columns:
            df_andamento[col_destino] = None
            
        # Converter para float para garantir cálculos precisos
        col_v_andamento = 'Valor da Parcela'
        col_v_front = 'Prestacao'
        
        # Otimização: Lista de contratos do Front que já foram usados no Andamento
        # para não tentar alocá-los novamente.
        contratos_ja_usados = set(df_andamento[col_destino].dropna().astype(str).unique())
        
        # Agrupar os cpfs que ainda têm linhas vazias no Andamento
        vazios_andamento = df_andamento[df_andamento[col_destino].isna() | (df_andamento[col_destino] == "")]
        cpfs_com_pendencia = vazios_andamento['CPF'].unique()

        # Joga só o que está nas esteiras corretas
        df_front = df_front[df_front['Esteira'].isin(self.esteiras)].copy()

        match_count = 0

        '''if df_front['Prestacao'].dtype != 'float64':
                df_front['Prestacao'] = df_front['Prestacao'].astype(str).str.replace('.', '').str.replace(',', '.')
                df_front['Prestacao'] = pd.to_numeric(df_front['Prestacao'], errors='coerce')'''
            

        for cpf in cpfs_com_pendencia:
            # 1. Pega os contratos do Front disponíveis para este CPF
            front_cpf = df_front[
                (df_front['CPF'] == cpf) & 
                (~df_front['Contrato'].astype(str).isin(contratos_ja_usados))
            ]

            
            if front_cpf.empty:
                continue
                
            # 2. Iterar sobre cada contrato disponível no Front para este CPF
            for _, row_front in front_cpf.iterrows():
                contrato_alvo = str(row_front['Contrato']).strip()
                valor_alvo = float(row_front[col_v_front])
                
                # 3. Pega os índices e valores das linhas do Andamento que AINDA estão vazias
                # Atualizamos isso a cada iteração, pois um contrato anterior pode ter preenchido linhas
                linhas_disponiveis = df_andamento[
                    (df_andamento['CPF'] == cpf) & 
                    (df_andamento[col_destino].isna() | (df_andamento[col_destino] == ""))
                ]
                
                if linhas_disponiveis.empty:
                    break # Acabaram as linhas vazias para este CPF no Andamento
                    
                # Cria um dicionário {index_no_dataframe: valor_da_parcela}
                dicionario_valores = linhas_disponiveis[col_v_andamento].to_dict()
                
                encontrou_match = False
                
                # 4. Testa combinações: primeiro de 2 em 2 linhas, depois 3 em 3... até max_linhas_somadas
                # (Se o seu Andamento tiver muitas linhas do mesmo CPF, testar até 4 ou 5 é super rápido.
                # Mais do que isso pode demorar, por isso o limite max_linhas_somadas).
                tamanho_maximo_busca = min(len(dicionario_valores) + 1, max_linhas_somadas + 1)
                
                for r in range(2, tamanho_maximo_busca):
                    # itertools.combinations gera todas as combinações possíveis de tamanho 'r'
                    for combinacao in itertools.combinations(dicionario_valores.items(), r):
                        # combinacao é uma tupla de tuplas: ((index1, valor1), (index2, valor2), ...)
                        soma_combinacao = sum(item[1] for item in combinacao)
                        
                        # Verifica se a soma está dentro da tolerância
                        if abs(soma_combinacao - valor_alvo) <= tolerancia:
                            # Achamos a combinação!
                            indices_para_preencher = [item[0] for item in combinacao]
                            
                            # Preenche o contrato nas linhas do Andamento
                            df_andamento.loc[indices_para_preencher, col_destino] = contrato_alvo
                            
                            # Adiciona ao set de usados para pular no futuro
                            contratos_ja_usados.add(contrato_alvo)
                            match_count += 1
                            encontrou_match = True
                            
                            # print(f"Match por soma encontrado: CPF {cpf} | Contrato {contrato_alvo} | Front: R${valor_alvo} | Somas: {[item[1] for item in combinacao]}")
                            break # Para a busca de combinações para ESTE contrato
                            
                    if encontrou_match:
                        break # Pula para o próximo contrato do Front
                        
        print(f"Concluído. Total de contratos do Front alocados por soma de parcelas: {match_count}")
        return df_andamento
    
    

    def busca_greedy_backtracking(self, alvo, itens, max_contratos=5):
        """
        Busca a combinação de contratos que resulte na menor diferença absoluta
        em relação ao valor alvo.
        """
        # print('BUSCA GREEDY ATIVADO')
        # Escala de centavos para evitar erros de float
        alvo_int = int(round(alvo * 100))
        opcoes = sorted([(c, int(round(v * 100))) for c, v in itens], 
                        key=lambda x: x[1], reverse=True)
        
        # Variáveis para rastrear a melhor aproximação
        self.melhor_resultado = None
        self.menor_delta = float('inf')

        def buscar(index_inicio, alvo_restante, caminho):
            delta_atual = abs(alvo_restante)
            
            # Atualiza o recorde se encontrarmos uma combinação mais próxima
            if delta_atual < self.menor_delta:
                self.menor_delta = delta_atual
                self.melhor_resultado = "/".join(map(str, caminho))
            
            # Se for um match perfeito, interrompemos a busca (melhor impossível)
            if delta_atual == 0:
                return True
                
            if len(caminho) >= max_contratos:
                return False

            for i in range(index_inicio, len(opcoes)):
                contrato, valor = opcoes[i]
                
                # Poda lógica: se o valor atual sozinho já piora o delta atual 
                # mais do que o nosso melhor recorde, podemos pular.
                if valor > (alvo_restante + self.menor_delta):
                    continue
                
                caminho.append(contrato)
                if buscar(i + 1, alvo_restante - valor, caminho):
                    return True
                caminho.pop()
                
            return False

        buscar(0, alvo_int, [])
        # Retorna o melhor que conseguiu encontrar dentro do limite de contratos
        return self.melhor_resultado

    def processar_contratos_otimizado(self, df_andamento, df_front):
        # --- 1. Padronização ---
        # df_andamento = df_andamento.drop_duplicates(subset=['Código']).copy()

        print('PROCESSAR CONTRATOS OTIMIZADO ATIVADO')


        for df in [df_andamento, df_front]:
            # Garante colunas numéricas
            col_v = 'Valor da Parcela' if 'Valor da Parcela' in df.columns else 'Prestacao'
            if df[col_v].dtype != 'float64':
                df[col_v] = df[col_v].astype(str).str.replace(".", "").str.replace(",", ".")
                df[col_v] = pd.to_numeric(df[col_v], errors='coerce')
            df[col_v] = df[col_v].astype(float).round(2)

        col_destino = 'Contrato Editado 1' if 'Contrato Editado 1' in df_andamento.columns else 'Contrato de Andamento'
        contratos_usados_andamento = df_andamento['Contrato Editado 1'] if 'Contrato Editado 1' in df_andamento.columns else df_andamento['Contrato de Andamento']

        df_andamento[col_destino] = df_andamento[col_destino].astype(object)
        
        # 2. Filtrar Front disponível
        ocupados = df_andamento['Código na instituição'].dropna().unique()
        df_front_dispo = df_front[~df_front['Contrato'].astype(str).isin(map(str, ocupados))].copy()
        
        contratos_usados = set()

        
        # --- DEBUG CPF ESPECÍFICO ---
        cpf_alvo = "780.865.073-00"
        print(f"\n[DEBUG] processar_contratos_otimizado - ANTES da busca para o CPF {cpf_alvo}:")
        colunas_verificar = ['Código na instituição', 'Contrato de Andamento', 'Valor da Parcela', col_destino]
        colunas_existentes = [c for c in colunas_verificar if c in df_andamento.columns]
        
        filtro_cpf = df_andamento[df_andamento['CPF'] == cpf_alvo]
        if not filtro_cpf.empty:
            print(filtro_cpf[colunas_existentes])
        else:
            print("CPF não encontrado em df_andamento neste momento.")
        print("-" * 50)

        # 3. Busca por Grupo (Backtracking por CPF)
        # Processamos primeiro os grupos para resolver somas de parcelas
        vazios = df_andamento[df_andamento[col_destino].isna() | (df_andamento[col_destino] == "")]

        # Contratos de "565.475.873-04"
        # print(f'Contratos do CPF 565.475.873-04\n{df_andamento.loc[df_andamento['CPF'] == '565.475.873-04', col_destino]}')

        # Contrato 617393 já está na coluna de col_destino?
        # print(df_andamento[col_destino].astype(str).str.contains('617393').any())
        
        for cpf, grupo in vazios.groupby('CPF'):
            soma_alvo = round(grupo['Valor da Parcela'].sum(), 2)
            
            # Criamos um conjunto (set) de contratos únicos para busca ultra rápida
            contratos_usados_andamento = set(
                df_andamento[col_destino]
                .astype(str)
                .str.split('/')   # Divide se houver barras
                .explode()         # Transforma cada item da lista em uma linha
                .str.strip()       # Remove espaços
                .unique()
            )
            # 2. Filtra opções disponíveis para este CPF específico
            # Usamos parênteses para garantir a ordem das operações lógicas
            possibilidades = df_front_dispo[
                (df_front_dispo['CPF'] == cpf) & 
                (~df_front_dispo['Contrato'].astype(str).isin(contratos_usados_andamento)) &
                (~df_front_dispo['Contrato'].astype(str).isin(contratos_usados))
            ]
            

            if possibilidades.empty: continue

            # Joga só o que está nas esteiras corretas
            possibilidades = possibilidades[possibilidades['Esteira'].isin(self.esteiras)]
            
            lista_itens = list(possibilidades[['Contrato', 'Prestacao']].itertuples(index=False, name=None))
            
            # A busca agora sempre retornará a melhor combinação disponível
            resultado = self.busca_greedy_backtracking(soma_alvo, lista_itens)
            
            if resultado:
                df_andamento.loc[grupo.index, col_destino] = resultado
                for c in resultado.split("/"):
                    contratos_usados.add(c)

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
            texto_original = str(row['Clone na instituição']).strip()
            
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
        df_sujo['Clone na instituição'] = df_sujo['Clone na instituição'].astype(str).replace('nan', '')
        
        # Sobrescreve a coluna com os valores tratados
        df_sujo['Clone na instituição'] = df_sujo.apply(processar_linha_unificada, axis=1)

        # --- Salvar ---
        try:
            caminho_final = os.path.join(self.caminho, "Relatório Averbados Contratos tratados.xlsx")
            df_sujo.to_excel(caminho_final, index=False)
            print(f"Arquivo salvo com sucesso em: {caminho_final}")
        except Exception as e:
            print(f"ERRO AO SALVAR: {e}")

        return df_sujo

    
    def extrair_contratos_com_referencia(self, df_sujo: pd.DataFrame, df_limpo: pd.DataFrame, coluna_destino) -> pd.DataFrame:
        print("Iniciando o processo de extração de contratos...")
        
        def limpar_contrato(texto: str) -> str:
            if not isinstance(texto, str):
                texto = str(texto)
            return re.sub(r'[^0-9a-zA-Z]', '', texto).replace(" ", "")
        
        # --- Passo 1: Preparar Mapas de Referência ---
        df_limpo['Contrato'] = df_limpo['Contrato'].astype(str).str.strip() # -> Transforma a coluna de Contrato no Front em string
        
        
        if df_limpo['Prestacao'].dtype != 'float64': # -> Transforma a coluna Prestacao do Front em número
            df_limpo['Prestacao'] = df_limpo['Prestacao'].astype(str).str.replace(".", "").str.replace(",", ".")
            df_limpo['Prestacao'] = pd.to_numeric(df_limpo['Prestacao'], errors='coerce')
        
        cpf_parcelas = df_limpo.groupby('CPF').apply(
            lambda x: list(zip(x['Prestacao'].round(2), x['Contrato'], x['Esteira']))
        ).to_dict() # -> Cria um grupo organizado por CPF, onde estão organizados as colunas Prestacao; Contrato; e Esteira

        cpf_contratos = df_limpo.groupby('CPF')['Contrato'].apply(list).to_dict() # -> Cria um grupo organizado por CPF ordenando os Contratos

        # --- Passo 2: Lógica de Extração com Rastreamento de Método ---
        def encontrar_contratos_na_linha(row):
            cpf = row['CPF'] # -> Pegamos um CPF
            if '443.xxx.xxx-xx' in row['CPF']:
                print(f'Como está o contrato sujo do CPF 443.911.370-20: {row[coluna_destino]}')
            # texto_contratos_sujo = str(row['Contrato de Andamento']).strip() # -> Pegamos contrato
            texto_contratos_sujo = str(row[coluna_destino]).strip() # -> Pegamos contrato
            valor_parcela_suja = round(float(row.get('Valor da Parcela', 0)), 2) # -> Pegamos a parcela
            
            resultados = [] # Lista de tuplas: (contrato, metodo)

            # MÉTODO 1: Se o código estiver vazio, busca apenas pela parcela
            if not texto_contratos_sujo or texto_contratos_sujo.lower() == 'nan': # -> Aqui é para as linhas de Contrato vazias; 
                                                                                  # então vamos usar a parcela para fazer a busca
                lista_parcelas_validas = cpf_parcelas.get(cpf, []) # -> Eu preciso verificar com o Gemini, mas acredito que usando o CPF, a gente armazena 
                                                                   # x['Prestacao'].round(2), x['Contrato'], x['Esteira'] do cpf_parcelas que contém dados do front

                for valor_ref, contrato_ref, _ in lista_parcelas_validas: # -> Vamos iterar por essa variável
                    if valor_parcela_suja == valor_ref: # -> uma comparação suave entre o valor do andamento com o do front
                        return [(contrato_ref, "Valor da Parcela")] # -> Retornamos o contrato de referência e o método usado
                return [] # -> Isso eu não entendi... Mas acredito que para essa condição  funcionar, usamos o valor de parcela da linha que está atrelado a um CPF, 
                          # e procuramos no Front algo que seja do mesmo valor no mesmo CPF para então nos retornar um número de contrato; senão, retorna nada

            # Lógica de Fuzzy/Texto
            contratos_validos_para_cpf = cpf_contratos.get(cpf, []) # -> Armazenamos os contratos pelo CPF do Front
            if not contratos_validos_para_cpf: return [] # -> Se nada for armazenado retorna vazio

            # Teste de contrato_sujo
            if '443.911.370-20' in row['CPF']:
                print(f'Como está o contrato sujo do CPF 443.911.370-20: {texto_contratos_sujo}')

            partes_sujas = [p for p in re.split(r'[/,;\s]+', texto_contratos_sujo) if p] # -> Aqui é onde eu acho que os contratos que tem barra são separados, 
                                                                                         # minha principal suspeita do porque algumas linhas permanecerem juntas... 
                                                                                         # Só não consigo deduzir o que pode estar errado.
                                                                                         # Talvez, antes dessa linha eu faça um print. Se cpf x estiver contido na linha, imprime.
            
            contratos_disponiveis = list(contratos_validos_para_cpf)
            LIMIAR_SEGURO = 97

            for parte in partes_sujas:
                parte_limpa = limpar_contrato(parte)
                if not parte_limpa or len(parte_limpa) < 3: continue

                melhor_match = None
                metodo_aplicado = ""
                maior_score = 0

                for contrato_valido in contratos_disponiveis:
                    alvo_limpo = limpar_contrato(contrato_valido)
                    score = 0

                    if alvo_limpo.endswith(parte_limpa):
                        score = 100
                    else:
                        score = max(fuzz.partial_ratio(parte_limpa, alvo_limpo), 
                                fuzz.ratio(parte_limpa, alvo_limpo))

                    if score >= LIMIAR_SEGURO and score > maior_score:
                        maior_score = score
                        melhor_match = contrato_valido
                        metodo_aplicado = f"Fuzzy Match ({score}%)"

                if melhor_match:
                    # 1. Extrair a lista de contratos do CPF que estão nas esteiras permitidas E batem o valor
                    # Cada 'item' em cpf_parcelas.get(cpf) agora é (valor, contrato, esteira)
                    possiveis_pelo_valor_e_esteira = [
                        (c, e) for v, c, e in cpf_parcelas.get(cpf, []) 
                        if v == valor_parcela_suja and e in self.esteiras
                    ]
                    
                    # 2. Verificar a esteira do 'melhor_match' (o que veio do fuzzy/texto)
                    # Procuramos nos dados de referência qual a esteira desse contrato específico
                    info_match_texto = next(((v, e) for v, c, e in cpf_parcelas.get(cpf, []) if c == melhor_match), None)
                    
                    valor_match_texto = info_match_texto[0] if info_match_texto else None
                    esteira_match_texto = info_match_texto[1] if info_match_texto else None

                    # --- Lógica de Decisão ---
                    
                    # Caso A: O contrato do texto está na esteira certa e o valor bate
                    # --- Lógica de Decisão Corrigida ---
                    if melhor_match:
                        # Se achou por texto/fuzzy, mantemos o contrato encontrado e apenas classificamos o motivo
                        if esteira_match_texto in self.esteiras and valor_match_texto == valor_parcela_suja:
                            metodo_aplicado = "Texto + Valor + Esteira Confirmados"
                        elif esteira_match_texto in self.esteiras:
                            metodo_aplicado = f"Fuzzy Match (Esteira {esteira_match_texto}) - Valor Divergente"
                        else:
                            metodo_aplicado = f"Fuzzy Match ({maior_score}%) - Esteira Divergente"
                    
                    # Caso NÃO tenha achado por texto, aí sim recorremos ao reserva pelo valor
                    elif possiveis_pelo_valor_e_esteira:
                        contrato_reserva, esteira_reserva = possiveis_pelo_valor_e_esteira[0]
                        melhor_match = contrato_reserva
                        metodo_aplicado = f"Correção por Valor + Esteira ({esteira_reserva})"

                    # Caso C: O contrato do texto está na esteira certa, mas o valor diverge 
                    # (e não achamos nenhum outro contrato que bata o valor na esteira certa)
                    '''elif esteira_match_texto in self.esteiras:
                        metodo_aplicado = f"Fuzzy Match (Esteira {esteira_match_texto}) - Valor Divergente"'''
                        
                    # Caso D: Nada bate com as esteiras permitidas
                    '''else:
                        melhor_match = None'''

                    # --- Finalização ---
                    if melhor_match:
                        resultados.append((melhor_match, metodo_aplicado))
                        if melhor_match in contratos_disponiveis:
                            contratos_disponiveis.remove(melhor_match)

            return resultados

        # --- Passo 3: Aplicação e Expansão de Colunas ---
        df_sujo[coluna_destino] = df_sujo[coluna_destino].astype(str).replace('nan', '')

        # --- DEBUG CPF ESPECÍFICO ---
        cpf_alvo = "780.865.073-00"
        print(f"\n[DEBUG] extrair_contratos_com_referencia - Lendo as colunas para o CPF {cpf_alvo}:")
        colunas_verificar = ['Código na instituição', 'Contrato de Andamento', 'Valor da Parcela']
        colunas_existentes = [c for c in colunas_verificar if c in df_sujo.columns]
        
        filtro_cpf = df_sujo[df_sujo['CPF'] == cpf_alvo]
        if not filtro_cpf.empty:
            print(filtro_cpf[colunas_existentes])
        else:
            print("CPF não encontrado em df_sujo neste momento.")
        print("-" * 50)

        
        # Processa a busca
        res_raw = df_sujo.apply(encontrar_contratos_na_linha, axis=1)

        # Criar DataFrames separados para Contratos e Métodos
        contratos_data = []
        metodos_data = []

        for lista in res_raw:
            contratos_data.append([item[0] for item in lista])
            metodos_data.append([item[1] for item in lista])

        df_cont = pd.DataFrame(contratos_data, index=df_sujo.index)
        df_meto = pd.DataFrame(metodos_data, index=df_sujo.index)

        # Renomear colunas dinamicamente
        df_cont.columns = [f'Contrato Editado {i+1}' for i in df_cont.columns]
        df_meto.columns = [f'Metodo {i+1}' for i in df_meto.columns]

        # =========================================================================
        # REESTRUTURAÇÃO INTELIGENTE: CONSOLIDAÇÃO CIRÚRGICA DE DADOS
        # =========================================================================
        
        # 1. Separamos apenas as colunas "fixas/base" do seu DataFrame original
        cols_base = [c for c in df_sujo.columns if not c.startswith('Contrato Editado ') and not c.startswith('Metodo ')]
        df_base_limpo = df_sujo[cols_base].copy()

        # 2. Resgatamos o histórico de colunas já editadas (se existirem)
        cols_editadas_antigas = [c for c in df_sujo.columns if c.startswith('Contrato Editado ') or c.startswith('Metodo ')]
        if cols_editadas_antigas:
            df_editadas_consolidado = df_sujo[cols_editadas_antigas].copy()
        else:
            # Na primeiríssima passada, iniciamos um DataFrame vazio estruturado com o mesmo índice
            df_editadas_consolidado = pd.DataFrame(index=df_sujo.index)

        # 3. ATUALIZAÇÃO CIRÚRGICA: Só mexe na linha se tiver um contrato real ali
        # Isso impede que os NaNs gerados na rodada atual apaguem o histórico das passadas anteriores!
        for col in df_cont.columns:
            # Máscara booleana: Garante que só vamos ler o que for string válida e populada
            novo_valido = df_cont[col].notna() & (df_cont[col].astype(str).str.strip() != "") & (df_cont[col].astype(str).str.strip() != "nan")
            
            if col in df_editadas_consolidado.columns:
                # Atualiza EXCLUSIVAMENTE as linhas onde encontramos um novo contrato válido
                df_editadas_consolidado.loc[novo_valido, col] = df_cont.loc[novo_valido, col]
            else:
                # Se a coluna acabou de nascer (ex: Contrato Editado 3), cria vazia e insere os válidos
                df_editadas_consolidado[col] = ""
                df_editadas_consolidado.loc[novo_valido, col] = df_cont.loc[novo_valido, col]

        # Repete a mesma segurança cirúrgica para a coluna de Métodos
        for col in df_meto.columns:
            novo_valido = df_meto[col].notna() & (df_meto[col].astype(str).str.strip() != "") & (df_meto[col].astype(str).str.strip() != "nan")
            
            if col in df_editadas_consolidado.columns:
                df_editadas_consolidado.loc[novo_valido, col] = df_meto.loc[novo_valido, col]
            else:
                df_editadas_consolidado[col] = ""
                df_editadas_consolidado.loc[novo_valido, col] = df_meto.loc[novo_valido, col]

        # Garante a limpeza de eventuais resíduos nulos que sobraram
        df_editadas_consolidado = df_editadas_consolidado.fillna("")

        # 4. Definimos o ponto cirúrgico de inserção (sempre após o Contrato de Andamento)
        idx_base = cols_base.index('Contrato de Andamento') + 1

        # 5. Juntamos as colunas base com as colunas editadas consolidadas
        df_resultado = pd.concat([df_base_limpo, df_editadas_consolidado], axis=1)
        
        # 6. Descobrimos o número máximo de pares para ordenar perfeitamente na tela
        cols_contratos = [c for c in df_editadas_consolidado.columns if c.startswith('Contrato Editado ')]
        max_pares = max([int(c.split()[-1]) for c in cols_contratos], default=0)

        cols_finais = cols_base.copy()
        for i in range(max_pares):
            c_name = f'Contrato Editado {i+1}'
            m_name = f'Metodo {i+1}'
            
            if c_name in df_resultado.columns:
                cols_finais.insert(idx_base + (i * 2), c_name)
            if m_name in df_resultado.columns:
                cols_finais.insert(idx_base + (i * 2) + 1, m_name)

        # 7. Filtra o DataFrame final pela ordenação estrita
        df_resultado = df_resultado[cols_finais]

        # Remover duplicatas de colunas que possam ter surgido na reordenação
        # df_resultado = df_resultado.loc[:, ~df_resultado.columns.duplicated()]
        
        # Garantir que todas as colunas originais existam antes de filtrar pela ordem final
        ordem_existente = [c for c in cols_finais if c in df_resultado.columns]
        df_resultado = df_resultado[ordem_existente]

        # --- Salvar ---
        try:
            caminho_final = os.path.join(self.caminho, "Relatório Averbados Contratos tratados.xlsx")
            df_resultado.to_excel(caminho_final, index=False)
        except Exception as e:
            print(f"ERRO AO SALVAR: {e}")

        return df_resultado.fillna('')