import pandas as pd
import numpy as np
import re
from thefuzz import fuzz
from python.ESTEIRAS import load_esteiras
import os


class UNIFICA_FRONT_FUNC_ESTEIRAS:
    def __init__(self, front, convenio, consignataria=None, funcao=None, andamento_funcao=None, caminho=None):
        self.front = front
        self.convenio = convenio
        self.consignataria = consignataria if consignataria is not None else None
        self.funcao = funcao
        self.andamento_funcao = andamento_funcao
        self.condicoes_1 = load_esteiras()
        self.caminho = caminho

        if self.andamento_funcao is not None:
            print('Tipo da coluna Valor da Parcela antes da conversão:\n', self.andamento_funcao['Valor da Parcela'].dtype)
            if self.andamento_funcao['Valor da Parcela'].dtype == 'float64':
                self.andamento_funcao['Valor da Parcela'] = self.andamento_funcao['Valor da Parcela'].astype(str).str.replace(".", ",")


        self.mapeamento_convenio = {
                                    'GOV. ALAGOAS': ['GOV AL CC', 'GOV AL EMP', 'GOV AL CB'],
                                    'GOV. ALAGOAS - TJAL': ['TJ AL CC'],
                                    'GOV. CEARÁ': ['GOV CEARA DG', 'GOV CEARÁ'],
                                    'GOV. ESPÍRITO SANTO': ['GOV ES CB', 'GOV ES CB DG'],
                                    'GOV. GOIÁS': ['GOV GOIAS', 'GOV GO CPL', 'GOV GOIAS SEG'],
                                    'GOV. MARANHÃO': ['GOV MARANHÃO CC', 'GOV MARANHÃO CB', 'GOV MARANHÃO', 'GOV MA CB', 'GOV MA CC', 'GOV MA'],
                                    'GOV. MATO GROSSO': ['GOV MT PL CAPIT', 'GOV MT CT'],
                                    'GOV. MINAS GERAIS - CBMMG': ['MG CBMMG', 'MG-CBMMG CC DG', 'MG CBMMG CB DG', 'MG-CBMMG CC'],
                                    'GOV. MINAS GERAIS - IPSEMG': ['GOV MG - IPSEMG', 'MG IPSEMG CC DG', 'MG IPSEMG CB DG'],
                                    'GOV. MINAS GERAIS - IPSM': ['GOV MG - IPSM', 'MG IPSM CC DG', 'MG IPSM CB DG', 'GOV MG IPSM'],
                                    'GOV. MINAS GERAIS - PMMG': ['GOV MG - PMMG', 'MG - PMMG CC DG', 'MG PMMG CB DG', 'MG PMMG SEG', 'PMMG CB DG SEG', 'PMMG CC DG SEG', 'PMMG CC DG CPL', 'PMMG CB DG CPL', 'GOV MG PMMG'],
                                    'GOV. MINAS GERAIS - SEPLAG': ['MG SEPLAG', 'MG SEPLAG CC', 'MG SEPLAG CC DG', 'MG SEPLAG CB DG', 'SEPL CC DG SEG', 'SEPL CB DG SEG', 'SEPL CC DG CPL', 'SEPL CB DG CPL'],
                                    'GOV. PARANÁ': ['GOV PARANA', 'GOV PR CPL', 'GOV PR DG', 'GOV PARANA SEG', 'GOV PR DG SEG', 'GOV PR DG CPL'],
                                    'GOV. PARAÍBA': ['GOV PB INSPFEM', 'GOV PARAIBA BD', 'GOV PARAIBA', 'UNIV. EST PB', 'GOV PBPREV', 'PBPREV', 'UEPB BD', 'INSPFEM S FL'],
                                    'GOV. PERNAMBUCO': ['GOV PE CC', 'GOV PE CB', 'GOV PE CC DG', 'GOV PE CB DG', 'GOV PE EMP'],
                                    'GOV. PIAUÍ': ['GOV PIAUÍ CC', 'GOV PI CPL', 'GOV PIAUÍ CB', 'GOV PI CB SEG', 'GOV PIAUÍ EMP', 'GOV PI CB CPL', 'GOV PIAUÍ CB DG', 'PIAUÍ CB DG SEG', 'PIAUÍ CB DG COM'],
                                    'GOV. RIO DE JANEIRO': ['GOV RJ', 'GOV RJ DG', 'GOV RJ SEG', 'GOV RJ CPL', 'GOV RJ M NEG'],
                                    'GOV. RIO GRANDE DO NORTE': ['GOV RN', 'GOV RN CC '],
                                    'GOV. SANTA CATARINA': ['GOV S. CATARINA', 'GOV SC SEG', 'GOV SC CPL', 'GOV SC S FL', 'GOV SC CAP', 'GOV SC DG', 'GOV SC DG SEG'],
                                    'GOV. SÃO PAULO': ['GOV SPPREV', 'GOV SÃO PAULO'],
                                    'GOV. TOCANTINS': ['GOV TOCANTINS'],
                                    'GOV. TOCANTINS e IGEPREV': ['IGEPREV'],
                                    'INSS': ['INSS BENEFICIO', 'INSS RMC', 'INSS RMC SEG', 'INSS BENEF SEG', 'INSS RMC S FL', 'INSS BEN S FL', 'INSS BENEF CPL', 'INSS RMC CPL'],
                                    'PREF. ALAGOINHAS': ['PM ALAGOINHAS'],
                                    'PREF. ANAJATUBA': ['PM ANAJ EMP', 'PM ANAJATUBA CC', 'PM ANAJATUBA CB'],
                                    'PREF. ANANINDEUA': ['PM ANANIN CC', 'PM ANANINDEUA', 'PM ANANIN CB', 'PM ANANIN CB DG'],
                                    'PREF. ARACAJU': ['PM ARACAJU', 'PM ARACAJU CB', 'PM ARACAJU CC'],
                                    'PREF. ARAGUAÍNA': ['PM ARAGUAINA'],
                                    'PREF. ARAPONGAS': ['PM ARAPONGAS CC'],
                                    'PREF. ARAUCÁRIA': ['PM ARAUC EMP'],
                                    'PREF. AÇAILÂNDIA': ['PM ACAILANDIA'],
                                    'PREF. BARBACENA': ['PM BARB CC', 'PM BARB EMP'],
                                    'PREF. BAURU': ['PM DE BAURU'],
                                    'PREF. BELO HORIZONTE': ['PM BH CB', 'PM BH CC'],
                                    'PREF. CAJAMAR': ['PM CAJAMAR CC', 'PM CAJAMAR', 'PM CAJAMAR SEG', 'PM CAJAMAR CPL', 'PM CAJAMAR DG'],
                                    'PREF. CAMPINA GRANDE': ['CAMPINA G-IPSEM', 'C.G IPSEM DG'],
                                    'PREF. CAMPINAS': ['PM CAMPINAS', 'PM CAMPINAS DG'],
                                    'PREF. CAMPO GRANDE': ['PM CAMPO GRANDE', 'IMPCG '],
                                    'PREF. CONTAGEM': ['PM CONTAGEM', 'PREVICON', 'TRANSCON'],
                                    'PREF. DUQUE DE CAXIAS': ['PM DUQUE CAXIAS'],
                                    'PREF. DUQUE DE CAXIAS - IMPDC': ['PM DC - IPMDC'],
                                    'PREF. ESTÂNCIA VELHA': ['PM EST. VLH EMP'],
                                    'PREF. FLORIANÓPOLIS': ['PM FLORIPA CB', 'PM FLORIPA CC', 'PM FLORIPA', 'PM FLORIAN EMP'],
                                    'PREF. GOIÂNIA': ['PM GOIANIA SEG', 'PM GOIÂNIA'],
                                    'PREF. GRAVATAÍ': ['PM GRAVATAÍ'],
                                    'PREF. GUARULHOS': ['PM GRU CB', 'PM GRU CC', 'PM GRU EMP'],
                                    'PREF. IMPERATRIZ': ['PM IMPTRZ', 'PM IMPTRZ CB', 'PM IMPTRZ CC'],
                                    'PREF. ITU': ['PM DE ITU', 'PM DE ITU CC', 'PM DE ITU CB'],
                                    'PREF. JOÃO PESSOA': ['PM JOAO PESSOA'],
                                    'PREF. JUAZEIRO DO NORTE': ['PM JUAZEIRO N'],
                                    'PREF. JUÍZ DE FORA': ['PM JUÍZ DE FORA', 'PM JUIZ DE F CC', 'PM JFPREV CC'],
                                    'PREF. MACAÉ': ['PM MACAE'],
                                    'PREF. MAZAGÃO': ['PM MAZAGAO'],
                                    'PREF. NATAL': ['PM NATAL CB', 'PM NATAL CC', 'PM NATAL CB DG'],
                                    'PREF. NITERÓI': ['PM DE NITEROI'],
                                    'PREF. PALMAS': ['PM PALMAS ADTO', 'PM PALMAS EMP', 'PM PALMAS CC'],
                                    'PREF. PAÇO DO LUMIAR': ['PM P LUMIAR'],
                                    'PREF. PICOS': ['PM PICOS', 'PM PICOS S FL', 'PM PICOS DG'],
                                    'PREF. PIRACICABA': ['PM PIRACICABA', 'PM PIRA SEG'],
                                    'PREF. PIRACICABA IPASP': ['PM PIRA IPASP'],
                                    'PREF. PLANALTINA': ['PM PLANALTINA', 'PREVPLAN'],
                                    'PREF. PORTO VELHO': ['PM PORTO VELHO', 'PM PORTO V IPAM'],
                                    'PREF. QUIJINGUE': ['PM DE QUIJINGUE'],
                                    'PREF. RECIFE': ['PM RECIFE'],
                                    'PREF. RIBEIRÃO PRETO': ['PM RIB. PRETO', 'PM RIB PRETO'],
                                    'PREF. RIO DE JANEIRO': ['PM RJ'],
                                    'PREF. SANTA LUZIA': ['PM SANTA LUZIA'],
                                    'PREF. SANTA RITA': ['PM ST RITA CB', 'PM ST RITA ADTO', 'PM ST RITA CC', 'PM SANTA MARIA', 'IPREV S RT ADTO', 'IPREV S RTA CC', 'PM STA RITA EMP', 'IPREV S RTA EMP'],
                                    'PREF. SANTOS': ['PM SANTOS'],
                                    'PREF. SAPUCAIA': ['PM SAPUCAIA'],
                                    'PREF. SOBRAL': ['PM SOBRAL'],
                                    'PREF. SOROCABA': ['PM SOROCABA CB', 'PM SOROCABA SEG'],
                                    'PREF. SUZANO': ['PM SUZANO'],
                                    'PREF. SÃO GONÇALO': ['PM SÃO GONÇALO'],
                                    'PREF. SÃO JOSÉ DE RIBAMAR': ['PM S JOSE RIB'],
                                    'PREF. SÃO JOSÉ DO RIO PRETO': ['PM SJ RIO PRETO'],
                                    'PREF. SÃO LUÍS': ['PM SÃO LUÍS'],
                                    'PREF. SÃO PAULO': ['PM SP IPREM', 'PM SAO PAULO'],
                                    'PREF. TAUBATÉ': ['PM TAUBATÉ', 'PM TAUBATÉ CB', 'TAUBATÉ CB DG', 'PM TAUBATE', 'PM TAUBATE CB'],
                                    'PREF. TERESINA': ['PM TERESINA'],
                                    'PREF. TUTÓIA': ['PM TUTÓIA CC', 'PM TUTÓIA EMP', 'PM TUTÓIA CB'],
                                    'PREF. UBERABA': ['PM UBERABA CB', 'PM UBERABA EMP', 'PM UBERABA CC'],
                                    'PREF. VENÂNCIO AIRES': ['PM VE AIRES EMP'],
                                    'PREF. VÁRZEA GRANDE': ['PM VARZEA G'],
                                    'PREF. ÁGUAS LINDAS DE GOIÁS': ['PM ÁGUAS LINDAS'],
                                    'PREV. PIRACICABA IPASP': ['IPASP', 'IPASP DG'],
                                    'PREVIPALMAS': ['PM PALMAS PREV'],
                                    'SEMAE - SERVIÇO MUNICIPAL DE ÁGUA E ESGOTO DE PIRACICABA': ['PM PIRA SEMAE'],
                                }
        
        #  Separar no andamento do função somente o convenio que vamos juntar
        if self.andamento_funcao is not None:
            colunas = ['Proposta', 'Operação', 'CPF/CNPJ', 'MatrÍcula', 'Cliente', 'Quantidade de Parcelas', 'Data Base', 'Valor da Parcela', 'Descrição do Produto',
                                   'Descrição da Atividade', 'Descrição EMPREGADOR']
            
            # Vai receber só essas colunas
            andamento_funcao_excel = andamento_funcao[colunas]
            andamento_funcao_excel.to_excel(os.path.join(self.caminho, f'ESTEIRAS DO FUNÇÃO COM MENOS COLUNAS.xlsx'), index=False)
            print(f'Andamento do função filtrado para o convenio antes da seleção de empregador {self.convenio}:\n{self.andamento_funcao.head()}')
            self.andamento_funcao = self.andamento_funcao[self.andamento_funcao['Descrição EMPREGADOR'].isin(self.mapeamento_convenio.get(self.convenio, []))]
            print(f'Andamento do função filtrado para o convenio {self.convenio}:\n{self.andamento_funcao.head()}')

    def unifica_front_funcao(self):
        mapeamento = {
            'NR_PROP': 'Contrato',
            'NR_OPER': 'CCB',
            'CPF': 'CPF',
            'MATRICULA': 'Matricula',
            'CLIENTE': 'Nome',
            'PARC': 'Prazo',
            'DT_BASE': 'Data Averbacao',
            'VLR_PARC': 'Prestacao',
            'PRODUTO': 'Tipo Operacao',
            'ORIGEM_4': 'Convenio'
        }
        return self._processar_unificacao_front(
            base_adicional=self.funcao, 
            coluna_contrato='NR_PROP', 
            mapeamento=mapeamento, 
            verificar_ccb=True,
            atualizar_esteira_integrado=True  # <-- LIGA A REGRA AQUI
        )
    
    def unifica_front_funcao_esteiras_andamento(self):
        mapeamento = {
            'Proposta': 'Contrato',
            'Operação': 'CCB',
            'CPF/CNPJ': 'CPF',
            'MatrÍcula': 'Matricula',
            'Cliente': 'Nome',
            'Quantidade de Parcelas': 'Prazo',
            'Data Base': 'Data Averbacao',
            'Valor da Parcela': 'Prestacao',
            'Descrição do Produto': 'Tipo Operacao',
            'Descrição da Atividade': 'Esteira',
            'Descrição EMPREGADOR': 'Convenio'
        }
        return self._processar_unificacao_front(
            base_adicional=self.andamento_funcao, 
            coluna_contrato='Proposta', 
            mapeamento=mapeamento, 
            verificar_ccb=False,
            atualizar_esteira_integrado=False  # <-- DESLIGA A REGRA AQUI
        )

    # =====================================================================
    # FUNÇÃO MESTRE QUE PROCESSA A LÓGICA (EVITANDO REPETIÇÃO)
    # =====================================================================
    def _processar_unificacao_front(self, base_adicional, coluna_contrato, mapeamento, verificar_ccb=False, atualizar_esteira_integrado=False):
        front = self.front

        if base_adicional is None or base_adicional.empty:
            print('\nDEBUG -> Base adicional é nula ou vazia. Retornando "front" sem tratamento.\n')
            return front

        contrato_front = front['Contrato'].astype('int64')
        contratos_base = base_adicional[coluna_contrato].astype('int64')

        # 1. Transforma em INTEGRADO apenas se o parâmetro permitir (chamada pela self.funcao)
        if atualizar_esteira_integrado:
            # Isolamos a condição na variável mask_integrado antes de aplicar
            mask_integrado = front['Contrato'].isin(contratos_base) & (front['Esteira'].str.contains('ANDAMENTO|PENDENTE', na=False))

            # Aplica a alteração
            front.loc[mask_integrado, 'Esteira'] = 'INTEGRADO'

        if 'Descrição da Atividade' in base_adicional.columns:
            # 1. Padroniza as chaves de busca para texto puro (evitando divergência entre int/str)
            chaves_base = base_adicional['Proposta'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            chaves_front = front['Contrato'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

            # 2. Cria o "dicionário" de busca vinculando as chaves padronizadas à Descrição
            mapa_andamento_pendente = base_adicional.set_index(chaves_base)['Descrição da Atividade']
            
            # 3. Puxa as descrições da base adicional para os contratos do front (agora ambos são strings)
            novos_status = chaves_front.map(mapa_andamento_pendente)
            
            # 4. Cria a máscara (filtro) com as suas regras
            mask_atualizar = novos_status.notna() & front['Esteira'].str.contains('ANDAMENTO|PENDENTE', na=False)
            
            # 5. Substitui a Esteira atual pelo Novo Status apenas nas linhas filtradas pela máscara
            front.loc[mask_atualizar, 'Esteira'] = novos_status[mask_atualizar]

        # 2. Remove da base adicional os contratos que já existem no Front
        base_tratada = base_adicional[~base_adicional[coluna_contrato].isin(contrato_front)].copy()

        # 3. Filtro extra de CCB (usado apenas pela unifica_front_funcao)
        if verificar_ccb:
            ccb_tratado = front['CCB'].astype(str).str.slice(0, 9).fillna(0).astype('float64').astype('int64')
            base_tratada = base_tratada[~base_tratada[coluna_contrato].isin(ccb_tratado)].copy()

        # 4. Filtra e renomeia as colunas usando o mapeamento fornecido
        base_ajustada = base_tratada[list(mapeamento.keys())].rename(columns=mapeamento)


        # 5. Junta o Front com a Base Tratada
        front_unif = pd.concat([front, base_ajustada], ignore_index=True)

        # 6. Preenche valores genéricos onde ficou nulo
        front_unif['Esteira'] = front_unif['Esteira'].fillna("INTEGRADO")
        # 1. Preenche os vazios
        front_unif['Orbital'] = front_unif['Orbital'].fillna("")

        # 2. Cria a lista limpando possíveis espaços invisíveis nas pontas
        produtos_orbital = [
            'CARTÃO PLÁSTICO', 'CARTÃO PLÁSTICO - RE', 'CARTAO - SEG PARC', 
            'CARTAO SEGURO - A VISTA', 'CARTÃO MT PL', 'CARTAO DIGITAL'
        ]

        # 3. Faz a marcação garantindo que a coluna de busca está sem espaços extras nas pontas (.str.strip())
        mask_orbital = (front_unif['Tipo Operacao'].str.strip().isin(produtos_orbital)) & (front_unif['Orbital'] == '')
        front_unif.loc[mask_orbital, 'Orbital'] = "SIM"
        front_unif.loc[front_unif['Orbital'] == '', 'Orbital'] = "NAO"

        front_unif['Consignataria'] = front_unif['Consignataria'].fillna("CAPITAL CONSIG") if self.consignataria is None else front_unif['Consignataria'].fillna(self.consignataria)
        front_unif['Status'] = front_unif['Status'].fillna("INTEGRADO")
        front_unif['Acao Judicial'] = front_unif['Acao Judicial'].fillna("NAO")
        front_unif['Obito'] = front_unif['Obito'].fillna("NAO")

        print('front unif finalzin:\n', front_unif.tail())

        return front_unif
    
class TRATA_CONTRATOS:
    def __init__(self, front_semi_trabalhado, averbados, convenio=None, conciliacao_tratada=None, nome_coluna_cpf='CPF',
                 nome_coluna_contrato='Contrato', nome_coluna_parcela='Valor da reserva'):
        self.front = front_semi_trabalhado
        self.averbados = averbados
        self.convenio = convenio
        self.conciliacao_tratada = conciliacao_tratada
        self.nome_coluna_cpf = nome_coluna_cpf
        self.nome_coluna_contrato = nome_coluna_contrato
        self.nome_coluna_parcela = nome_coluna_parcela
        self.condicoes_1 = load_esteiras()

    def extrair_contratos_com_referencia(self, df_sujo: pd.DataFrame, df_limpo: pd.DataFrame) -> pd.DataFrame:
            print("Iniciando o processo de extração de contratos...")

            # Função de limpeza (pode ser definida aqui ou fora)
            def limpar_contrato(texto: str) -> str:
                if not isinstance(texto, str):
                    texto = str(texto)
                    texto = texto.replace(" ", "")
                return re.sub(r'[^0-9a-zA-Z]', '', texto)  # Mantém letras e números

            # --- Passo 1: Criar o mapa de referência (sem alterações) ---
            df_limpo['Contrato'] = df_limpo['Contrato'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            df_limpo['CCB'] = df_limpo['CCB'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            print("Criando mapa de referência CPF -> Contratos...")
            
            cpf_contratos = df_limpo.groupby('CPF')['Contrato'].apply(list).to_dict()
            cpf_operacao = df_limpo.groupby('CPF')['CCB'].apply(list).to_dict()
            # print(f'Mapa contratos:\n{cpf_contratos}')

            # --- Passo 2: Definir a função que será aplicada em cada linha (LÓGICA ALTERADA) ---
            def encontrar_contratos_na_linha(row):
                cpf = row['CPF_temp']
                texto_contratos_sujo = str(row[self.nome_coluna_contrato]).strip()
            
                cpf = row['CPF_temp']
                texto_contratos_sujo = str(row[self.nome_coluna_contrato])

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

                    # ==========================================
                    # DEBUG: INÍCIO DA AVALIAÇÃO DA PARTE
                    # ==========================================
                    # is_debug_cpf = str(cpf).startswith('420.365')
                    is_debug_cpf = False
                    if is_debug_cpf:
                        print(f"\n--- AVALIANDO A PARTE: '{parte_limpa}' ---")

                    melhor_match_para_parte = None
                    maior_score_ponderado = 0

                    for i, contrato_valido in enumerate(contratos_disponiveis):
                        operacao_valida = operacoes_disponiveis[i] if i < len(operacoes_disponiveis) else ""

                        alvos = [
                            (contrato_valido, 'CONTRATO'),
                            (operacao_valida, 'OPERACAO')
                        ]

                        for alvo_texto, tipo_alvo in alvos:
                            if not alvo_texto: continue

                            alvo_limpo = limpar_contrato(alvo_texto)
                            score_base = 0
                            metodo = ""

                            if alvo_limpo.endswith(parte_limpa):
                                score_base = 200
                                metodo = "Endswith"
                            else:
                                score_partial = fuzz.partial_ratio(parte_limpa, alvo_limpo)
                                if score_partial >= LIMIAR_SEGURO:
                                    score_base = score_partial
                                    metodo = "Partial Ratio"
                                else:
                                    score_ratio = fuzz.ratio(parte_limpa, alvo_limpo)
                                    if score_ratio >= LIMIAR_SEGURO:
                                        score_base = score_ratio
                                        metodo = "Ratio (Completo)"

                            if score_base >= LIMIAR_SEGURO:
                                score_final = score_base
                                if tipo_alvo == 'CONTRATO':
                                    score_final += 1

                                # ==========================================
                                # DEBUG: MOSTRAR NOTAS DA COMPARAÇÃO
                                # ==========================================
                                if is_debug_cpf:
                                    print(f"Alvo: {alvo_limpo:15} | Tipo: {tipo_alvo:8} | Score: {score_final} | Método: {metodo}")

                                if score_final > maior_score_ponderado:
                                    maior_score_ponderado = score_final
                                    melhor_match_para_parte = contrato_valido

                    if melhor_match_para_parte:
                        if is_debug_cpf:
                            print(f"=> VENCEDOR PARA '{parte_limpa}': {melhor_match_para_parte} (Score Final: {maior_score_ponderado})")
                            
                        encontrados_nesta_linha.append(melhor_match_para_parte)
                        if melhor_match_para_parte in contratos_disponiveis:
                            index_remocao = contratos_disponiveis.index(melhor_match_para_parte)
                            del contratos_disponiveis[index_remocao]

                            # <-- CORREÇÃO 2: Remove a operação no mesmo índice para manter a sincronia
                            if index_remocao < len(operacoes_disponiveis):
                                del operacoes_disponiveis[index_remocao]
                    else:
                        if is_debug_cpf:
                            print(f"=> NENHUM VENCEDOR PARA '{parte_limpa}' (Maior score não atingiu limite)")

                return encontrados_nesta_linha

            # --- Passo 3: Aplicar a função e criar as novas colunas (sem alterações) ---
            print("Analisando a Planilha A e extraindo os contratos...")
            df_sujo[self.nome_coluna_contrato] = df_sujo[self.nome_coluna_contrato].astype(str).str.replace('nan', '')


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
    
    def adiciona_contratos_faltando(self, averbado_contratos_faltantes, front_semi):
        # 0. TRAVA DE SEGURANÇA: Remove colunas duplicadas
        averbado_contratos_faltantes = averbado_contratos_faltantes.loc[:, ~averbado_contratos_faltantes.columns.duplicated()]

        # =====================================================================
        # 1. A MÁGICA E BLINDAGEM: Isolar as colunas do Front
        # =====================================================================
        front_semi_base = front_semi[['CPF', 'Prestacao', 'Contrato']].copy()
        
        # Renomeamos as colunas do Front para garantir que NUNCA haja colisão no merge!
        front_semi_base.rename(columns={
            'CPF': 'CPF_front', 
            'Prestacao': 'Prestacao_front', 
            'Contrato': 'Contrato_Encontrado'
        }, inplace=True)

        # --- A CORREÇÃO ENTRA AQUI ---
        # Garante que a Prestação do Front seja float64 para o merge não quebrar
        if front_semi_base['Prestacao_front'].dtype != 'float64':
            front_semi_base['Prestacao_front'] = front_semi_base['Prestacao_front'].astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
            front_semi_base['Prestacao_front'] = pd.to_numeric(front_semi_base['Prestacao_front'], errors='coerce').fillna(0)
        # -----------------------------
        
        # Cria um ID sequencial para CPFs com valores de prestação repetidos no Front
        front_semi_base['chave_duplicata'] = front_semi_base.groupby(['CPF_front', 'Prestacao_front']).cumcount()

        # =====================================================================
        # 2. Prepara os dados de entrada
        # =====================================================================
        if averbado_contratos_faltantes[self.nome_coluna_parcela].dtype != 'float64':
            averbado_contratos_faltantes[self.nome_coluna_parcela] = averbado_contratos_faltantes[self.nome_coluna_parcela].astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
            averbado_contratos_faltantes[self.nome_coluna_parcela] = pd.to_numeric(averbado_contratos_faltantes[self.nome_coluna_parcela], errors='coerce')

        # =====================================================================
        # 3. Execução dos Merges no DataFrame A
        # =====================================================================
        
        # --- PRIMEIRA TENTATIVA: Match Exato ---
        averbado_contratos_faltantes['chave_duplicata'] = averbado_contratos_faltantes.groupby(['CPF_temp', self.nome_coluna_parcela]).cumcount()

        averbado_contratos_faltantes = averbado_contratos_faltantes.merge(
            front_semi_base, 
            left_on=['CPF_temp', self.nome_coluna_parcela, 'chave_duplicata'],   
            right_on=['CPF_front', 'Prestacao_front', 'chave_duplicata'], 
            how='left'
        )

        # Preenche com o nome blindado que veio do front
        averbado_contratos_faltantes[self.nome_coluna_contrato] = averbado_contratos_faltantes[self.nome_coluna_contrato].fillna(averbado_contratos_faltantes['Contrato_Encontrado'])
        
        # Apaga as colunas provisórias que vieram do front para o DataFrame continuar limpo
        averbado_contratos_faltantes.drop(columns=['CPF_front', 'Prestacao_front', 'Contrato_Encontrado'], inplace=True)

        # --- SEGUNDA TENTATIVA: Caso de +20 reais ---
        front_semi_plus20 = front_semi_base.copy()
        front_semi_plus20['Prestacao_Ajustada'] = front_semi_plus20['Prestacao_front'] + 20
        
        averbado_contratos_faltantes['chave_duplicata'] = averbado_contratos_faltantes.groupby(['CPF_temp', self.nome_coluna_parcela]).cumcount()

        averbado_contratos_faltantes = averbado_contratos_faltantes.merge(
            front_semi_plus20, 
            left_on=['CPF_temp', self.nome_coluna_parcela, 'chave_duplicata'],   
            right_on=['CPF_front', 'Prestacao_Ajustada', 'chave_duplicata'], 
            how='left'
        )

        averbado_contratos_faltantes[self.nome_coluna_contrato] = averbado_contratos_faltantes[self.nome_coluna_contrato].fillna(averbado_contratos_faltantes['Contrato_Encontrado'])
        averbado_contratos_faltantes.drop(columns=['CPF_front', 'Prestacao_front', 'Contrato_Encontrado', 'Prestacao_Ajustada'], inplace=True)

        # --- TERCEIRA TENTATIVA: Caso de +40 reais ---
        front_semi_plus40 = front_semi_base.copy()
        front_semi_plus40['Prestacao_Ajustada'] = front_semi_plus40['Prestacao_front'] + 40
        
        averbado_contratos_faltantes['chave_duplicata'] = averbado_contratos_faltantes.groupby(['CPF_temp', self.nome_coluna_parcela]).cumcount()

        averbado_contratos_faltantes = averbado_contratos_faltantes.merge(
            front_semi_plus40, 
            left_on=['CPF_temp', self.nome_coluna_parcela, 'chave_duplicata'],   
            right_on=['CPF_front', 'Prestacao_Ajustada', 'chave_duplicata'], 
            how='left'
        )

        averbado_contratos_faltantes[self.nome_coluna_contrato] = averbado_contratos_faltantes[self.nome_coluna_contrato].fillna(averbado_contratos_faltantes['Contrato_Encontrado'])
        averbado_contratos_faltantes.drop(columns=['CPF_front', 'Prestacao_front', 'Contrato_Encontrado', 'Prestacao_Ajustada', 'chave_duplicata'], inplace=True)

        return averbado_contratos_faltantes
    

    def trata_averbacao(self):
        # PUXA OS ARQUIVOS À SEREM TRATADOS
        data_averbados_bruto = self.averbados
        data_averbados_bruto['CPF_temp'] = data_averbados_bruto[self.nome_coluna_cpf].astype(str).str.replace(r'[.-]', '', regex=True).str.strip().str.zfill(11)
        front = self.front
        front['CPF'] = front['CPF'].astype(str).str.replace(r'[.-]', '', regex=True).str.strip().str.zfill(11)
        
        # Como era: front['Contrato'] = front['Contrato'].astype(str).str.strip()
        
        # Como deve ficar:
        front['Contrato'] = front['Contrato'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

        # teste_conciliacao = TRATA_CONCILIACAO(self.conciliacao, self.kobraki, self.tacs)
        teste_conciliacao = self.conciliacao_tratada
        # conciliacao_tratado = teste_conciliacao.trata_conciliacao()

        if front is False:
            print("trata_averbacao_1: O tratamento preliminar do front falhou. Verifique os erros anteriores.")
            return False

        print(f'Contrato 301268942 no front em trata_averbacao: {front.loc[front["Contrato"] == "301268942", "Prestacao"]}\n')

        semi_front = self.front
        if semi_front is False:
            print("trata_averbacao_2: O tratamento preliminar do front falhou. Verifique os erros anteriores.")
            return False
        
        data_averbados_bruto = self.adiciona_contratos_faltando(data_averbados_bruto, semi_front)

        semi_front['Contrato'] = semi_front['Contrato'].astype(str).str.strip()


        data_averbados = self.extrair_contratos_com_referencia(data_averbados_bruto, semi_front)

        '''teste_conciliacao = TRATA_CONCILIACAO(self.conciliacao, self.kobraki, self.extra_judicial)
        conciliacao_tratado = teste_conciliacao.trata_conciliacao()'''

        # Operações liquidadas. Tratando NRº OPER EDITADO
        # OP LIQUIDADO
        try:
            oper_liq = self.front[self.front['Status'].str.contains('Liquidado|CANCELADO', na=False)][['Contrato']].copy()
            contratos_tratados_liq = oper_liq['Contrato'].str.slice(0, 9)
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

            data_averbados[f'OBS {i}'] = data_averbados[nome_coluna_contrato].map(
                front.set_index('Contrato')['OBS'].to_dict()
            )

            # Cria a coluna de Esteira correspondente
            data_averbados[f'Esteira_{i}'] = data_averbados[nome_coluna_contrato].map(
                front.set_index('Contrato')['Esteira'].to_dict()
            )

            # Cria a coluna de Valor da Parcela correspondente
            data_averbados[f'Valor_Unif_{i}'] = data_averbados[nome_coluna_contrato].map(
                semi_front.set_index('Contrato')['Prestacao'].to_dict()
            )

            # Puxa os valores de saldo da conciliação
            """data_averbados[f'Saldo {i}'] = data_averbados[nome_coluna_contrato].map(
                semi_front.set_index('Contrato')['Saldo'].to_dict()
            )

            # Puxando os contratos liquidados (FORMA CORRIGIDA)
            # Cria a nova coluna 'OP LIQ {i}' com o resultado do map
            data_averbados[f'OP LIQ {i}'] = data_averbados[nome_coluna_contrato].map(
                oper_liq.set_index('Nº OPERAÇÃO EDITADO')['Contrato'].to_dict()
            )

            # --- 2.5 Puxa as liminares ---
            data_averbados[f"LIMINAR {i}"] = data_averbados[nome_coluna_contrato].map(
                semi_front.set_index('Contrato')['Acao Judicial'].to_dict()
            )
            data_averbados.loc[data_averbados[f"LIMINAR {i}"] != 1, f'LIMINAR {i}'] = ''

            # --- 3 Puxa os extrajudiciais ---
            data_averbados[f"EXTRA JUDICIAL {i}"] = data_averbados[nome_coluna_contrato].map(
                semi_front.set_index('Contrato')['OBS'].to_dict()
            )
            data_averbados.loc[data_averbados[f"EXTRA JUDICIAL {i}"] != 'EXTRA JUDICIAL', f'EXTRA JUDICIAL {i}'] = ''"""

            # print(f'Verificar qual é o saldo do contrato "302298345": {data_averbados.loc[data_averbados[f"Contrato Editado {i}"] == "302298345", f"Saldo {i}"]}')

            # --- PASSO 2: PREPARAÇÃO E LIMPEZA DE DADOS ---
            # Agora que todas as colunas foram criadas, garantimos que sejam numéricas para os cálculos.
            if data_averbados[f'Valor_Unif_{i}'].dtype != 'float64':
                data_averbados[f'Valor_Unif_{i}'] = data_averbados[f'Valor_Unif_{i}'].astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
                data_averbados[f'Valor_Unif_{i}'] = pd.to_numeric(data_averbados[f'Valor_Unif_{i}'], errors='coerce').fillna(0)
            '''if data_averbados[f'Saldo {i}'].dtype != 'float64':
                data_averbados[f'Saldo {i}'] = data_averbados[f'Saldo {i}'].astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
                data_averbados[f'Saldo {i}'] = pd.to_numeric(data_averbados[f'Saldo {i}'], errors='coerce').fillna(-np.inf)'''

            # --- PASSO 3: CONSTRUIR AS CONDIÇÕES E APLICAR A LÓGICA ---

            # Condição 1: Encontra todas as linhas onde o Saldo (já limpo) é >= 0
            """condicao_saldo_positivo = data_averbados[f'Saldo {i}'] >= -1

            # Condição 2: Encontra onde um contrato liquidado foi efetivamente encontrado (FORMA CORRIGIDA E ROBUSTA)
            # .notna() garante que só pegamos as linhas onde o map retornou um valor, e não NaN.
            data_averbados[f'OP LIQ {i}'] = data_averbados[f'OP LIQ {i}'].fillna('')
            condicao_op_liq = data_averbados[f'OP LIQ {i}'] != ''
            condicao_esteira = ~data_averbados[f'Esteira_{i}'].isin(self.condicoes_1)

            # --- 2.5 Puxa as liminares ---
            data_averbados[f"LIMINAR {i}"] = data_averbados[f"LIMINAR {i}"].fillna('')
            condicao_liminar = data_averbados[f'LIMINAR {i}'] == 1

            # --- 3 Extra judicial ---
            data_averbados[f"EXTRA JUDICIAL {i}"] = data_averbados[f"EXTRA JUDICIAL {i}"].fillna('')
            condicao_extra_judicial = data_averbados[f'EXTRA JUDICIAL {i}'] == 'EXTRA JUDICIAL'"""

            # --- 4 OBS ---
            data_averbados[f'OBS {i}'] = data_averbados[f'OBS {i}'].fillna('')
            condicao_obs = (data_averbados[f'OBS {i}'] != '') & (~data_averbados[f'OBS {i}'].isin(['NÃO LANÇAR - NÃO CARTÃO', 'NÃO LANÇAR - CONSIGNATÁRIA ERRADA']))

            # Ação: Nessas linhas, define o 'Valor_Unif' correspondente como 0
            # O operador | significa OU (se uma condição OU a outra for verdadeira)
            # data_averbados.loc[(condicao_saldo_positivo | condicao_op_liq | condicao_esteira | condicao_liminar | condicao_extra_judicial), f'Valor_Unif_{i}'] = 0
            data_averbados.loc[condicao_obs, f'Valor_Unif_{i}'] = 0
            # --- FIM DA NOVA LÓGICA ---

            # Condição de Operações Liquidadas, se a linha estiver preenchida vai lançar 0

        

        # Vamos remover a coluna CPF_temp
        data_averbados.drop(columns=['CPF_temp'], inplace=True)

        # Feito a verificação dos contratos, esteiras e valores do front, o restante será tratado em cada módulo
        return data_averbados
    

class FRONT_TRABALHADO:
    def __init__ (self, front, convenio, caminho):
        self.tratamento_front_preliminar = front
        self.convenio = convenio
        self.caminho = caminho
        self.condicoes_1 = load_esteiras()

    def tratamento_front(self):
        front_consig = self.tratamento_front_preliminar
        print(f'Comprimento de front_consig: {len(front_consig)}')


        if front_consig is False:
            print("DEBUG: O tratamento preliminar do front falhou. Verifique os erros anteriores.")
            return False
        
        # Adiciona só as esteiras que podem ser lançadas
        front_consig = front_consig[front_consig['Esteira'].isin(self.condicoes_1)].copy()

        # Separar o que não é cartão de crédito da conciliação
        # front_consig_nao_cartao = front_consig[~front_consig['Tipo Conciliação'].str.contains('Cartão de Crédito', na=False)].copy()

        # Pegar o que é CARTAO DE CREDITO do front
        # condicao_cartao = ['CARTAO DE CREDITO']
        # front_consig_cartao_front = front_consig_nao_cartao[front_consig_nao_cartao['Tipo Operacao'].isin(condicao_cartao)].copy()
        # Faz concat dos dois dataframes
        front_consig_trabalhado = front_consig.copy()

        # ------------------------------- TIRA O QUE É ADIANTAMENTO SALARIAL ------------------------------- #
        if self.convenio not in ['PREF. PALMAS']:
            front_consig_trabalhado = front_consig_trabalhado[~front_consig_trabalhado['Tipo Operacao'].str.contains('ADIANTAMENTO SALARIAL', na=False)].copy()
        print(f'Comprimento de front_consig_trabalhado: {len(front_consig_trabalhado)}')

        # ---------------------------------- TIRAR AÇÃO JUDICIAL DO FRONT ---------------------------------- #
        front_consig_trabalhado = front_consig_trabalhado.loc[front_consig_trabalhado['Acao Judicial'] != 'SIM'].copy()
        print(f'Comprimento de front_consig_trabalhado pós ação judicial: {len(front_consig_trabalhado)}')

        # ---------------------------------- TIRAR ÓBITO DO FRONT ---------------------------------- #
        # front_consig_trabalhado = front_consig_trabalhado.loc[front_consig_trabalhado['Obito'] != 1].copy()

        # --------------------------------------- TIRA BANCO OUTROS ----------------------------------------- #
        front_consig_trabalhado = front_consig_trabalhado[~front_consig_trabalhado['Consignataria'].str.contains('OUTROS|FUTURO', na=False)].copy()
        print(f'Comprimento de front_consig_trabalhado pós outros bancos: {len(front_consig_trabalhado)}')

        # ----------------------------------------- TIRA LIQUIDADOS ----------------------------------------- #
        front_consig_trabalhado = front_consig_trabalhado[~front_consig_trabalhado['Status'].str.contains('Liquidado|CANCELADO', na=False)].copy()
        print(f'Comprimento de front_consig_trabalhado pós liquidados: {len(front_consig_trabalhado)}\n')

        print(f'Contratos em 505.029.723-00:\n{front_consig_trabalhado.loc[front_consig_trabalhado['CPF'] == '505.029.723-00', 'Contrato']}\n')

        print('DEBUG: Esteiras finais do front trabalhado')
        try:
            front_consig_trabalhado.to_excel(
                os.path.join(self.caminho, f"FRONT PARA ANDAMENTO {self.convenio}.xlsx"),
                index=False, 
            )
        except Exception as e:
            print(f"DEBUG: ERRO AO SALVAR FRONT TRABALHADO: {e}")

        return front_consig_trabalhado
