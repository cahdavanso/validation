import pandas as pd
import re
from thefuzz import fuzz
import os
from python.ESTEIRAS import load_esteiras
from datetime import datetime

'''front_bruto = r"P:\PESSOAL\2026\MAIO\GOV PB\RELATORIOS\relatorio_2026-05-06_11-45-47_parte_1.csv"
andamento_bruto = r"P:\PESSOAL\2026\MAIO\GOV PB\RELATORIOS\Consignacao UNIFICADA GOV PB.xlsx"
caminho = r"P:\PESSOAL\2026\MAIO\GOV PB\TRABALHADOS TESTE ANDAMENTO"
funcao_bruto = r"P:\PESSOAL\2026\MAIO\GOV PB\RELATORIOS\RL167_v4.csv"
kobraki_bruto = r"P:\PESSOAL\2026\MAIO\GOV PB\RELATORIOS\RECEBIVEIS KOBRAKI - ABRIL 2026.xlsx"

front = pd.read_csv(front_bruto, encoding="utf-8-sig", sep=";", on_bad_lines="skip", low_memory=False)
andamento = pd.read_excel(andamento_bruto)
funcao = pd.read_csv(funcao_bruto, encoding="utf-8-sig", sep=";", on_bad_lines="skip", low_memory=False)
kobraki = pd.read_excel(kobraki_bruto, sheet_name='CONSOLIDADO')
convenio = "GOV. PARAÍBA"

andamento = andamento.dropna(axis=0, how='all')
# Se algum CPF estiver sem nada, preenche com 0 e transforma em inteiro para impedir que ele coloque .0 no final
andamento['CPF'] = andamento['CPF'].fillna(0).astype(int)

# --- LÓGICA DA HIERARQUIA ---
# Mapeamento conforme sua solicitação
hierarquia = {
    "Ativa": "1 - Ativa",
    "Pendente": "2 - Pendente",
    "Desc. a Menor": "3 - Desc. a Menor",
    "Não Descontada": "4 - Não Descontada",
    "Fora da Margem": "5 - Fora da Margem",
    "Solicitada Suspensão": "6 - Solicitada Suspensão",
    "Suspensa": "7 - Suspensa",
    "Cancelada": "8 - Cancelada",
    "Cancelamento": "9 - Cancelamento"
}

# Criamos a coluna 'Situacao_Formatada' baseada na coluna 'SITUACAO' do seu Excel
# .str.strip() remove espaços extras que podem causar erro de busca
andamento['Situação'] = andamento['Situação'].str.strip().map(hierarquia)

# Ordenamos o DataFrame pela nova coluna (1 até 9)
andamento = andamento.sort_values(by='Situação')'''


class ANDAMENTO:
    def __init__(self, front, convenio, caminho, consignataria, andamento=None, funcao=None):
        self.front = front
        self.andamento = andamento
        self.convenio = convenio
        self.caminho = caminho
        self.esteiras = load_esteiras()
        self.funcao = funcao
        self.consignataria = consignataria

    def unifica_front_funcao(self):
        front = self.front
        funcao = self.funcao

        if funcao is None:
            print('\nFunção está vazio\n')
            return front

        print(f"colunas de funcao: {funcao.columns}")

        contrato_front = front['Contrato']
        ccb_tratado = front['CCB'].astype(str).str.slice(0, 9)
        ccb_tratado = ccb_tratado.astype('int64')

        # Verifica se o que é andamento no front está no função, se tiver transforma em integrado
        contrato_funcao = funcao['NR_PROP']
        front.loc[front['Contrato'].isin(contrato_funcao) & (front['Esteira'].str.contains('ANDAMENTO')), 'Esteira'] = 'INTEGRADO'

        # Tira os contratos do Front que já existem no Função
        funcao = funcao[~funcao['NR_PROP'].isin(contrato_front)].copy()

        # Tira os contratos CCB do Front que também existem no Função
        funcao_tratado = funcao[~funcao['NR_PROP'].isin(ccb_tratado)].copy()


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
        funcao_ajustado = funcao_tratado[list(mapeamento.keys())].rename(columns=mapeamento)

        # 3. Use o concat para unir os dois DataFrames
        # O ignore_index=True serve para gerar um novo índice sequencial no DF final
        front_unif = pd.concat([front, funcao_ajustado], ignore_index=True)

        # Coloca Preenche o resto das colunas necessárias com valores genéricos, para não ficarem vazias
        front_unif['Esteira'] = front_unif['Esteira'].fillna("INTEGRADO")
        # Coloca SIM onde é orbital no função
        front_unif.loc[front_unif['Tipo Operacao'].str.contains('CARTÃO PLÁSTICO|CARTÃO PLÁSTICO - RE|CARTAO SEGURO - A VISTA| CARTAO - SEG PARC'), 'Orbital'] = 'SIM'

        # Altera para cartão
        front_unif['Tipo Operacao'] = front_unif['Tipo Operacao'].fillna('') # -> Só para ter certeza que ele vai preencher corretamente nos vazios
        front_unif.loc[~front_unif['Tipo Operacao'].str.contains('EMPR|BENS', na=False) & (front_unif['Operação'] == ''), 'Tipo Operacao'] = 'CARTAO DE CREDITO'

        front_unif['Orbital'] = front_unif['Orbital'].fillna("NAO")
        front_unif['Status'] = front_unif['Status'].fillna("INTEGRADO")
        front_unif['Acao Judicial'] = front_unif['Acao Judicial'].fillna("NAO")
        front_unif['Obito'] = front_unif['Obito'].fillna("NAO")
        front_unif['Consignataria'] = front_unif['Consignataria'].fillna(self.consignataria)
        


        print(f'FRONT UNIFICADO FINALZIN: {front_unif.tail()}')

        front_unif.to_excel(rf"{self.caminho}\Teste_front {self.convenio} {self.consignataria} {datetime.now().strftime("%m-%Y")}.xlsx", index=False)

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
        # lista_prazos = [f"0/{i}" for i in range(10)]
        print(f'cabeçalhos de andamento de paraíba: {self.andamento.columns}')
        self.andamento = self.andamento[
            ~(
                self.andamento['Situação'].isin(['Quitada', 'Baixada'])
                |
                self.andamento['Prazo'].str.match(r'^0/\d+$')
                |
                (self.andamento['Prazo'] == '1/1')
            )
        ].copy()
        
        
        if 'Contrato de Andamento' not in self.andamento.columns:
            self.andamento.insert(8, 'Contrato de Andamento', self.andamento['Contrato'])
        
        # Padronização de valores numéricos para os filtros funcionarem
        if self.andamento['Valor da Parcela'].dtype != 'float64':
            self.andamento['Valor da Parcela'] = self.andamento['Valor da Parcela'].astype(str)\
                .str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
            self.andamento['Valor da Parcela'] = pd.to_numeric(self.andamento['Valor da Parcela'], errors='coerce')

        andam_referencia_prazos = self.andamento.drop_duplicates(subset=['Contrato']).copy()
        cpf_tratado = andam_referencia_prazos['CPF'].astype(str).str.zfill(11).str.replace(r'(\d{3})(\d{3})(\d{3})(\d{2})',  r'\1.\2.\3-\4', regex=True)
        andam_referencia_prazos['CPF'] = cpf_tratado

        # Renomear a coluna Prazo para Prazo Total
        try:
            andam_referencia_prazos.rename(columns={'Prazo': 'Prazo Total'}, inplace=True)
        except Exception as e:
            print('Erro ao renomear a coluna de Prazo', e)
        
        

        # 2. PROCESSAMENTO DE CONTRATOS (Usando apenas o front_para_processar)
        andam_file= self.processar_contrato_simples(andam_referencia_prazos, front_para_processar)
        andam_file = self.extrair_contratos_com_referencia(andam_file, front_para_processar)
        andam_file= self.processar_contrato_simples(andam_file, front_para_processar)
        # Terceira passada
        # andam_file, front_base = self.processar_contratos_otimizado(andam_file, front_para_processar)
        print(f'Andamento depois de extrair_contratos\n{andam_file.columns}')

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
            andam_file.to_excel(os.path.join(self.caminho, f"ANDAMENTO GERAL {self.convenio} TESTE.xlsx"), index=False)
        except Exception as e:
            print(f"DEBUG: ERRO AO SALVAR ANDAMENTO GERAL: {e}")

        front_final.to_excel(rf"{self.caminho}\Teste_front.xlsx", index=False)

        return front_final
    
    def processar_contrato_simples(self, df_andamento, df_front):
        # 1. Limpeza e Padronização
        df_andamento = df_andamento.drop_duplicates(subset=['Contrato']).copy()
        
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
            df_andamento.insert(2, 'Contrato de Andamento', df_andamento['Contrato'])

        col_destino = 'Contrato Editado 1' if 'Contrato Editado 1' in df_andamento.columns else 'Contrato de Andamento'
        
        # 3. Filtrar Front disponível
        ocupados = df_andamento['Contrato'].dropna().unique()
        df_front_dispo = df_front[~df_front['Contrato'].astype(str).isin(map(str, ocupados))].copy()

        # 4. Criar dicionário indexado por CPF
        # O valor será uma lista de tuplas: [(contrato, valor_prestacao), ...]
        dict_front = {}
        for _, row in df_front_dispo.iterrows():
            cpf = row['CPF']
            if cpf not in dict_front:
                dict_front[cpf] = []
            dict_front[cpf].append((row['Contrato'], row['Prestacao']))

        # 5. Busca com Tolerância (0.10)
        vazios = df_andamento[df_andamento[col_destino].isna() | (df_andamento[col_destino] == "")].copy()
        tolerancia = 0.10

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
        ocupados = df_andamento['Contrato'].dropna().unique()

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
                    '''if esteira_match_texto in self.esteiras and valor_match_texto == valor_parcela_suja and self.convenio != 'GOV. PARAÍBA':
                    if valor_match_texto == valor_parcela_suja:
                        metodo_aplicado = "Texto + Valor + Esteira Confirmados"'''

                    
                    # Caso B: O contrato do texto NÃO serve (ou valor errado ou esteira errada), 
                    # mas temos um reserva que bate valor e esteira
                        
                    '''elif possiveis_pelo_valor_e_esteira and self.convenio != 'GOV. PARAÍBA':
                    # elif possiveis_pelo_valor_e_esteira:
                        contrato_reserva, esteira_reserva = possiveis_pelo_valor_e_esteira[0]
                        melhor_match = contrato_reserva
                        metodo_aplicado = f"Correção por Valor + Esteira ({esteira_reserva})"'''

                    # Caso C: O contrato do texto está na esteira certa, mas o valor diverge 
                    # (e não achamos nenhum outro contrato que bata o valor na esteira certa)
                    '''elif esteira_match_texto in self.esteiras and self.convenio != 'GOV. PARAÍBA':
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
    
'''andamento_obj = ANDAMENTO(front=front, convenio=convenio, caminho=caminho, andamento=andamento, funcao=funcao)

resultado = andamento_obj.andamento_func_front()'''
