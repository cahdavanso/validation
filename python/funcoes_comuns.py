import pandas as pd


class UNIFICA_FRONT_FUNC_ESTEIRAS:
    def __init__(self, front, convenio, funcao=None, andamento_funcao=None):
        self.front = front
        self.convenio = convenio
        self.funcao = funcao
        self.andamento_funcao = andamento_funcao

        if self.andamento_funcao is not None:
            print('Tipo da coluna Valor da Parcela antes da conversão:\n', self.andamento_funcao['Valor da Parcela'].dtype)
            if self.andamento_funcao['Valor da Parcela'].dtype == 'float64':
                self.andamento_funcao['Valor da Parcela'] = self.andamento_funcao['Valor da Parcela'].astype(str).str.replace(".", ",")

        self.mapeamento_convenio = {
                                    'GOV. ALAGOAS': ['GOV AL CC', 'GOV AL EMP', 'GOV AL CB'],
                                    'GOV. ALAGOAS - TJAL': 'TJ AL CC',
                                    'GOV. CEARÁ': ['GOV CEARA DG', 'GOV CEARÁ'],
                                    'GOV. ESPÍRITO SANTO': ['GOV ES CB', 'GOV ES CB DG'],
                                    'GOV. GOIÁS': ['GOV GOIAS', 'GOV GO CPL', 'GOV GOIAS SEG'],
                                    'GOV. MARANHÃO': ['GOV MARANHÃO CC', 'GOV MARANHÃO CB', 'GOV MARANHÃO', 'GOV MA CB', 'GOV MA CC', 'GOV MA'],
                                    'GOV. MATO GROSSO': ['GOV MT PL CAPIT', 'GOV MT CT'],
                                    'GOV. MINAS GERAIS - CBMMG': ['MG CBMMG', 'MG-CBMMG CC DG', 'MG CBMMG CB DG', 'MG-CBMMG CC'],
                                    'GOV. MINAS GERAIS - IPSEMG': ['GOV MG - IPSEMG', 'MG IPSEMG CC DG', 'MG IPSEMG CB DG'],
                                    'GOV. MINAS GERAIS - IPSM': ['GOV MG - IPSM', 'MG IPSM CC DG', 'MG IPSM CB DG'],
                                    'GOV. MINAS GERAIS - PMMG': ['GOV MG - PMMG', 'MG - PMMG CC DG', 'MG PMMG CB DG', 'MG PMMG SEG', 'PMMG CB DG SEG', 'PMMG CC DG SEG', 'PMMG CC DG CPL', 'PMMG CB DG CPL'],
                                    'GOV. MINAS GERAIS - SEPLAG': ['MG SEPLAG', 'MG SEPLAG CC', 'MG SEPLAG CC DG', 'MG SEPLAG CB DG', 'SEPL CC DG SEG', 'SEPL CB DG SEG', 'SEPL CC DG CPL', 'SEPL CB DG CPL'],
                                    'GOV. PARANÁ': ['GOV PARANA', 'GOV PR CPL', 'GOV PR DG', 'GOV PARANA SEG', 'GOV PR DG SEG', 'GOV PR DG CPL'],
                                    'GOV. PARAÍBA': ['GOV PB INSPFEM', 'GOV PARAIBA BD', 'GOV PARAIBA', 'UNIV. EST PB', 'GOV PBPREV', 'PBPREV', 'UEPB BD', 'INSPFEM S FL'],
                                    'GOV. PERNAMBUCO': ['GOV PE CC', 'GOV PE CB', 'GOV PE CC DG', 'GOV PE CB DG', 'GOV PE EMP'],
                                    'GOV. PIAUÍ': ['GOV PIAUÍ CC', 'GOV PI CPL', 'GOV PIAUÍ CB', 'GOV PI CB SEG', 'GOV PIAUÍ EMP', 'GOV PI CB CPL', 'GOV PIAUÍ CB DG', 'PIAUÍ CB DG SEG', 'PIAUÍ CB DG COM'],
                                    'GOV. RIO DE JANEIRO': ['GOV RJ', 'GOV RJ DG', 'GOV RJ SEG', 'GOV RJ CPL', 'GOV RJ M NEG'],
                                    'GOV. RIO GRANDE DO NORTE': ['GOV RN', 'GOV RN CC '],
                                    'GOV. SANTA CATARINA': ['GOV S. CATARINA', 'GOV SC SEG', 'GOV SC CPL', 'GOV SC S FL', 'GOV SC CAP', 'GOV SC DG', 'GOV SC DG SEG'],
                                    'GOV. SÃO PAULO': ['GOV SPPREV', 'GOV SÃO PAULO'],
                                    'GOV. TOCANTINS': 'GOV TOCANTINS',
                                    'GOV. TOCANTINS e IGEPREV': 'IGEPREV',
                                    'INSS': ['INSS BENEFICIO', 'INSS RMC', 'INSS RMC SEG', 'INSS BENEF SEG', 'INSS RMC S FL', 'INSS BEN S FL', 'INSS BENEF CPL', 'INSS RMC CPL'],
                                    'PREF. ALAGOINHAS': 'PM ALAGOINHAS',
                                    'PREF. ANAJATUBA': ['PM ANAJ EMP', 'PM ANAJATUBA CC', 'PM ANAJATUBA CB'],
                                    'PREF. ANANINDEUA': ['PM ANANIN CC', 'PM ANANINDEUA', 'PM ANANIN CB', 'PM ANANIN CB DG'],
                                    'PREF. ARACAJU': ['PM ARACAJU', 'PM ARACAJU CB', 'PM ARACAJU CC'],
                                    'PREF. ARAGUAÍNA': 'PM ARAGUAINA',
                                    'PREF. ARAPONGAS': 'PM ARAPONGAS CC',
                                    'PREF. ARAUCÁRIA': 'PM ARAUC EMP',
                                    'PREF. AÇAILÂNDIA': 'PM ACAILANDIA',
                                    'PREF. BARBACENA': ['PM BARB CC', 'PM BARB EMP'],
                                    'PREF. BAURU': 'PM DE BAURU',
                                    'PREF. BELO HORIZONTE': ['PM BH CB', 'PM BH CC'],
                                    'PREF. CAJAMAR': ['PM CAJAMAR CC', 'PM CAJAMAR', 'PM CAJAMAR SEG', 'PM CAJAMAR CPL', 'PM CAJAMAR DG'],
                                    'PREF. CAMPINA GRANDE': ['CAMPINA G-IPSEM', 'C.G IPSEM DG'],
                                    'PREF. CAMPINAS': ['PM CAMPINAS', 'PM CAMPINAS DG'],
                                    'PREF. CAMPO GRANDE': ['PM CAMPO GRANDE', 'IMPCG '],
                                    'PREF. CONTAGEM': ['PM CONTAGEM', 'PREVICON', 'TRANSCON'],
                                    'PREF. DUQUE DE CAXIAS': 'PM DUQUE CAXIAS',
                                    'PREF. DUQUE DE CAXIAS - IMPDC': 'PM DC - IPMDC',
                                    'PREF. ESTÂNCIA VELHA': 'PM EST. VLH EMP',
                                    'PREF. FLORIANÓPOLIS': ['PM FLORIPA CB', 'PM FLORIPA CC', 'PM FLORIPA', 'PM FLORIAN EMP'],
                                    'PREF. GOIÂNIA': ['PM GOIANIA SEG', 'PM GOIÂNIA'],
                                    'PREF. GRAVATAÍ': 'PM GRAVATAÍ',
                                    'PREF. GUARULHOS': ['PM GRU CB', 'PM GRU CC', 'PM GRU EMP'],
                                    'PREF. IMPERATRIZ': ['PM IMPTRZ', 'PM IMPTRZ CB', 'PM IMPTRZ CC'],
                                    'PREF. ITU': ['PM DE ITU', 'PM DE ITU CC', 'PM DE ITU CB'],
                                    'PREF. JOÃO PESSOA': 'PM JOAO PESSOA',
                                    'PREF. JUAZEIRO DO NORTE': 'PM JUAZEIRO N',
                                    'PREF. JUÍZ DE FORA': ['PM JUÍZ DE FORA', 'PM JUIZ DE F CC', 'PM JFPREV CC'],
                                    'PREF. MACAÉ': 'PM MACAE',
                                    'PREF. MAZAGÃO': 'PM MAZAGAO',
                                    'PREF. NATAL': ['PM NATAL CB', 'PM NATAL CC', 'PM NATAL CB DG'],
                                    'PREF. NITERÓI': 'PM DE NITEROI',
                                    'PREF. PALMAS': ['PM PALMAS ADTO', 'PM PALMAS EMP', 'PM PALMAS CC'],
                                    'PREF. PAÇO DO LUMIAR': 'PM P LUMIAR',
                                    'PREF. PICOS': ['PM PICOS', 'PM PICOS S FL', 'PM PICOS DG'],
                                    'PREF. PIRACICABA': ['PM PIRACICABA', 'PM PIRA SEG'],
                                    'PREF. PIRACICABA IPASP': 'PM PIRA IPASP',
                                    'PREF. PLANALTINA': ['PM PLANALTINA', 'PREVPLAN'],
                                    'PREF. PORTO VELHO': ['PM PORTO VELHO', 'PM PORTO V IPAM'],
                                    'PREF. QUIJINGUE': 'PM DE QUIJINGUE',
                                    'PREF. RECIFE': 'PM RECIFE',
                                    'PREF. RIBEIRÃO PRETO': ['PM RIB. PRETO', 'PM RIB PRETO'],
                                    'PREF. RIO DE JANEIRO': 'PM RJ',
                                    'PREF. SANTA LUZIA': 'PM SANTA LUZIA',
                                    'PREF. SANTA RITA': ['PM ST RITA CB', 'PM ST RITA ADTO', 'PM ST RITA CC', 'PM SANTA MARIA', 'IPREV S RT ADTO', 'IPREV S RTA CC', 'PM STA RITA EMP', 'IPREV S RTA EMP'],
                                    'PREF. SANTOS': 'PM SANTOS',
                                    'PREF. SAPUCAIA': 'PM SAPUCAIA',
                                    'PREF. SOBRAL': 'PM SOBRAL',
                                    'PREF. SOROCABA': ['PM SOROCABA CB', 'PM SOROCABA SEG'],
                                    'PREF. SUZANO': 'PM SUZANO',
                                    'PREF. SÃO GONÇALO': 'PM SÃO GONÇALO',
                                    'PREF. SÃO JOSÉ DE RIBAMAR': 'PM S JOSE RIB',
                                    'PREF. SÃO JOSÉ DO RIO PRETO': 'PM SJ RIO PRETO',
                                    'PREF. SÃO LUÍS': 'PM SÃO LUÍS',
                                    'PREF. SÃO PAULO': ['PM SP IPREM', 'PM SAO PAULO'],
                                    'PREF. TAUBATÉ': ['PM TAUBATÉ', 'PM TAUBATÉ CB', 'TAUBATÉ CB DG', 'PM TAUBATE', 'PM TAUBATE CB'],
                                    'PREF. TERESINA': 'PM TERESINA',
                                    'PREF. TUTÓIA': ['PM TUTÓIA CC', 'PM TUTÓIA EMP', 'PM TUTÓIA CB'],
                                    'PREF. UBERABA': ['PM UBERABA CB', 'PM UBERABA EMP', 'PM UBERABA CC'],
                                    'PREF. VENÂNCIO AIRES': 'PM VE AIRES EMP',
                                    'PREF. VÁRZEA GRANDE': 'PM VARZEA G',
                                    'PREF. ÁGUAS LINDAS DE GOIÁS': 'PM ÁGUAS LINDAS',
                                    'PREV. PIRACICABA IPASP': ['IPASP', 'IPASP DG'],
                                    'PREVIPALMAS': 'PM PALMAS PREV',
                                    'SEMAE - SERVIÇO MUNICIPAL DE ÁGUA E ESGOTO DE PIRACICABA': 'PM PIRA SEMAE',
                                }
        
        #  Separar no andamento do função somente o convenio que vamos juntar
        if self.andamento_funcao is not None:
            print(f'Andamento do função filtrado para o convenio antes da seleção de empregador {self.convenio}:\n{self.andamento_funcao.head()}')
            self.andamento_funcao = self.andamento_funcao[self.andamento_funcao['Descrição EMPREGADOR'].isin(self.mapeamento_convenio.get(self.convenio, []))]
            print(f'Andamento do função filtrado para o convenio {self.convenio}:\n{self.andamento_funcao.head()}')

    def unifica_front_funcao(self):
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
            return self._processar_unificacao_front(
                base_adicional=self.funcao, 
                coluna_contrato='NR_PROP', 
                mapeamento=mapeamento, 
                verificar_ccb=True
        )
    
    def unifica_front_funcao_esteiras_andamento(self):
        mapeamento = {
            'Proposta': 'Contrato',
            'CPF/CNPJ': 'CPF',
            'MatrÍcula': 'Matricula',
            'Cliente': 'Nome',
            'Quantidade de Parcelas': 'Prazo',
            'Valor da Parcela': 'Prestacao',
            'Descrição do Produto': 'Tipo Operacao',
            'Descrição da Atividade': 'Esteira',
            'Descrição EMPREGADOR': 'Convenio'
        }
        return self._processar_unificacao_front(
            base_adicional=self.andamento_funcao, 
            coluna_contrato='Proposta', 
            mapeamento=mapeamento, 
            verificar_ccb=False
        )

    # =====================================================================
    # FUNÇÃO MESTRE QUE PROCESSA A LÓGICA (EVITANDO REPETIÇÃO)
    # =====================================================================
    def _processar_unificacao_front(self, base_adicional, coluna_contrato, mapeamento, verificar_ccb=False):
        front = self.front

        if base_adicional is None or base_adicional.empty:
            print('\nDEBUG -> Base adicional é nula ou vazia. Retornando "front" sem tratamento.\n')
            return front

        contrato_front = front['Contrato'].astype('int64')
        contratos_base = base_adicional[coluna_contrato].astype('int64')

        # 1. Transforma em INTEGRADO o que for andamento/pendente no front e constar na base
        front.loc[front['Contrato'].isin(contratos_base) & (front['Esteira'].str.contains('ANDAMENTO|PENDENTE')), 'Esteira'] = 'INTEGRADO'

        # 2. Remove da base adicional os contratos que já existem no Front
        base_tratada = base_adicional[~base_adicional[coluna_contrato].isin(contrato_front)].copy()

        # 3. Filtro extra de CCB (usado apenas pela unifica_front_funcao)
        if verificar_ccb:
            ccb_tratado = front['CCB'].astype(str).str.slice(0, 9).fillna(0).astype('float64').astype('int64')
            base_tratada = base_tratada[~base_tratada[coluna_contrato].isin(ccb_tratado)].copy()

        # 4. Filtra e renomeia as colunas usando o mapeamento fornecido
        base_ajustada = base_tratada[list(mapeamento.keys())].rename(columns=mapeamento)

        # DEBUG: Verifica o contrato 301120431 na base já ajustada (buscando pela coluna certa: 'Contrato')
        print(f'Contrato 301120431 está na base ainda?\n{base_ajustada.loc[base_ajustada["Contrato"] == 301120431, "Contrato"]}')

        # 5. Junta o Front com a Base Tratada
        front_unif = pd.concat([front, base_ajustada], ignore_index=True)

        # 6. Preenche valores genéricos onde ficou nulo
        front_unif['Esteira'] = front_unif['Esteira'].fillna("INTEGRADO")
        front_unif['Orbital'] = front_unif['Orbital'].fillna("NAO")
        front_unif['Consignataria'] = front_unif['Consignataria'].fillna("CAPITAL CONSIG")
        front_unif['Status'] = front_unif['Status'].fillna("INTEGRADO")
        front_unif['Acao Judicial'] = front_unif['Acao Judicial'].fillna("NAO")
        front_unif['Obito'] = front_unif['Obito'].fillna("NAO")

        print('front unif finalzin:\n', front_unif.tail())

        return front_unif