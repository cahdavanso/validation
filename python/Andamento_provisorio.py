import pandas as pd
import re
from thefuzz import fuzz
import os
from python.ESTEIRAS import load_esteiras

# front_bruto = r"F:\Dados\NOVA ESTRUTURA\LANÇAMENTO CARTÕES\TRABALHANDO\2026\05 - Maio\GUIDO ROBOTO\PAIUI\relatorio_2026-04-16_13-19-47_parte_1.csv"
# andamento_bruto = r"F:\Dados\NOVA ESTRUTURA\LANÇAMENTO CARTÕES\TRABALHANDO\2026\05 - Maio\GUIDO ROBOTO\PAIUI\ANDAMENTO UNIFICADO GOV PI.csv"
# caminho = r"F:\Dados\NOVA ESTRUTURA\LANÇAMENTO CARTÕES\TRABALHANDO\2026\05 - Maio\GUIDO ROBOTO\PAIUI\TRABALHADOS"
# funcao_bruto = r"F:\Dados\NOVA ESTRUTURA\LANÇAMENTO CARTÕES\TRABALHANDO\2026\05 - Maio\GUIDO ROBOTO\PAIUI\FUNÇÃO GOV PI 04.2026.csv"

# front = pd.read_csv(front_bruto, encoding="utf-8-sig", sep=";", on_bad_lines="skip", low_memory=False)
# andamento = pd.read_csv(andamento_bruto, encoding="latin1", sep=";", on_bad_lines="skip", low_memory=False)
# funcao = pd.read_csv(funcao_bruto, encoding="utf-8-sig", sep=";", on_bad_lines="skip", low_memory=False)


class ANDAMENTO_PROVISORIO:
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
        front = self.unifica_front_funcao()
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
        front_para_processar = front_para_processar.sort_values(by=['Esteira'], ascending=[True])
        

        # Criamos cópias para evitar SettingWithCopyWarning
        # self.andamento = self.andamento[self.andamento['Prazo Total'] != 1].copy()

        # Remoção de cartão de crédito com prazo 0 ou 1
        # self.andamento = self.andamento[~((self.andamento['Modalidade'].isin(['Cartão de Crédito', 'Cartão de Crédito [Prefeitura]', 'Cartão de Crédito [Previdência]'])) & (self.andamento['Prazo Total'].isin([0, 1])))].copy()

        if 'Clone na instituição' not in self.andamento.columns:
            self.andamento.insert(2, 'Clone na instituição', self.andamento['Código na instituição'])


        if 'Contrato de Andamento' not in self.andamento.columns:
            self.andamento.insert(3, 'Contrato de Andamento', self.andamento['Código na instituição'])
        
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
        
        andam_file_simples = self.extrair_contratos_simples(andam_referencia_prazos, front_para_processar)
            
        

        # 2. PROCESSAMENTO DE CONTRATOS (Usando apenas o front_para_processar)
        andam_file, front_base = self.processar_contratos_otimizado(andam_file_simples, front_para_processar)
        andam_file = self.extrair_contratos_com_referencia(andam_file, front_para_processar)
        print(f'Andamento depois de extrair_contratos\n{andam_file.columns}')

        # Terceira passada
        andam_file, front_base = self.processar_contratos_otimizado(andam_file, front_para_processar)

        # 3. EXTRAÇÃO DOS PRAZOS
        # colunas_contratos = [col for col in andam_file.columns if 'Contrato' in col or 'Código' in col]
        colunas_contratos = [col for col in andam_file.columns if 'Contrato Editado' in col]
        
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

        # Ordena por prioridade o Tipo Operacao
        # Criar ordem de prioridade
        ordem = {
            'CARTAO BENEFICIO': 1,
            'EMPRESTIMO': 2
        }

        df_front['prioridade'] = df_front['Tipo Operacao'].map(ordem).fillna(3)

        df_front = df_front.sort_values(
            by=['prioridade', 'Esteira'],
            ascending=[True, True]
        )

        df_front = df_front.drop(columns='prioridade')
        # print(f'Ordem dos contratos no cpf 065.999.663-49:\n{df_front["Contrato"][df_front['CPF'] == '065.999.663-49']}')

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

    
    def extrair_contratos_com_referencia(self, df_sujo: pd.DataFrame, df_limpo: pd.DataFrame) -> pd.DataFrame:
        print("Iniciando o processo de extração de contratos...")
        
        def limpar_contrato(texto: str) -> str:
            if not isinstance(texto, str):
                texto = str(texto)
            return re.sub(r'[^0-9a-zA-Z]', '', texto).replace(" ", "")
        
        # --- Passo 1: Preparar Mapas de Referência ---
        df_limpo['Contrato'] = df_limpo['Contrato'].astype(str).str.strip()
        
        
        if df_limpo['Prestacao'].dtype != 'float64':
            df_limpo['Prestacao'] = df_limpo['Prestacao'].astype(str).str.replace(".", "").str.replace(",", ".")
            df_limpo['Prestacao'] = pd.to_numeric(df_limpo['Prestacao'], errors='coerce')
        
        cpf_parcelas = df_limpo.groupby('CPF').apply(
            lambda x: list(zip(x['Prestacao'].round(2), x['Contrato'], x['Esteira']))
        ).to_dict()

        cpf_contratos = df_limpo.groupby('CPF')['Contrato'].apply(list).to_dict()

        # --- Passo 2: Lógica de Extração com Rastreamento de Método ---
        def encontrar_contratos_na_linha(row):
            cpf = row['CPF']
            texto_contratos_sujo = str(row['Contrato de Andamento']).strip()
            valor_parcela_suja = round(float(row.get('Valor da Parcela', 0)), 2)
            
            resultados = [] # Lista de tuplas: (contrato, metodo)

            # MÉTODO 1: Se o código estiver vazio, busca apenas pela parcela
            if not texto_contratos_sujo or texto_contratos_sujo.lower() == 'nan':
                lista_parcelas_validas = cpf_parcelas.get(cpf, [])
                for valor_ref, contrato_ref, _ in lista_parcelas_validas:
                    if valor_parcela_suja == valor_ref:
                        return [(contrato_ref, "Valor da Parcela")]
                return []

            # Lógica de Fuzzy/Texto
            contratos_validos_para_cpf = cpf_contratos.get(cpf, [])
            if not contratos_validos_para_cpf: return []

            partes_sujas = [p for p in re.split(r'[/,;\s]+', texto_contratos_sujo) if p]
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
                    if esteira_match_texto in self.esteiras and valor_match_texto == valor_parcela_suja:
                        metodo_aplicado = "Texto + Valor + Esteira Confirmados"
                    
                    # Caso B: O contrato do texto NÃO serve (ou valor errado ou esteira errada), 
                    # mas temos um reserva que bate valor e esteira
                        
                    
                    #elif possiveis_pelo_valor_e_esteira and self.convenio != 'GOV. PARAÍBA':
                    elif possiveis_pelo_valor_e_esteira:
                        contrato_reserva, esteira_reserva = possiveis_pelo_valor_e_esteira[0]
                        melhor_match = contrato_reserva
                        metodo_aplicado = f"Correção por Valor + Esteira ({esteira_reserva})"

                    # Caso C: O contrato do texto está na esteira certa, mas o valor diverge 
                    # (e não achamos nenhum outro contrato que bata o valor na esteira certa)
                    elif esteira_match_texto in self.esteiras:
                        metodo_aplicado = f"Fuzzy Match (Esteira {esteira_match_texto}) - Valor Divergente"
                        
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
        df_sujo['Contrato de Andamento'] = df_sujo['Contrato de Andamento'].astype(str).replace('nan', '')
        
        # Processa a busca
        res_raw = df_sujo.apply(encontrar_contratos_na_linha, axis=1)
        print(f'O que está em res_raw: {res_raw}')

        # Criar DataFrames separados para Contratos e Métodos
        contratos_data = []
        metodos_data = []

        for lista in res_raw:
            # Separa as tuplas (contrato, metodo) em duas listas
            contratos_data.append([item[0] for item in lista])
            metodos_data.append([item[1] for item in lista])

        df_cont = pd.DataFrame(contratos_data, index=df_sujo.index)
        df_meto = pd.DataFrame(metodos_data, index=df_sujo.index)

        # Renomear colunas dinamicamente
        df_cont.columns = [f'Contrato Editado {i+1}' for i in df_cont.columns]
        df_meto.columns = [f'Metodo {i+1}' for i in df_meto.columns]

        # Concatenar e Reordenar
        df_resultado = pd.concat([df_sujo, df_cont, df_meto], axis=1)
        
        # Organizar colunas para que o Metodo fique logo após o respectivo Contrato
        cols_finais = df_sujo.columns.tolist()
        for i in range(len(df_cont.columns)):
            c_name = f'Contrato Editado {i+1}'
            m_name = f'Metodo {i+1}'
            if c_name in df_resultado.columns:
                # Insere após o código ou após o último par inserido
                idx = cols_finais.index('Contrato de Andamento') + 1 + (i * 2)
                cols_finais.insert(idx, c_name)
                cols_finais.insert(idx + 1, m_name)

        # Remover duplicatas de colunas que possam ter surgido na reordenação
        df_resultado = df_resultado.loc[:, ~df_resultado.columns.duplicated()]
        
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