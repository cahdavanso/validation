import pandas as pd
import os

class TRATA_ORBITAL:
    def __init__(self, orbital, front, convenio, caminho, averbado_final=None, rubrica=None):
        self.orbital = orbital
        self.front = front
        self.convenio = convenio
        self.caminho = caminho
        self.averbado_final = averbado_final if averbado_final is not None else None
        self.rubrica = rubrica if rubrica is not None else None

    def salvar_com_layout_original(self, df, caminho_arquivo):
        # 1. Criar o ExcelWriter
        writer = pd.ExcelWriter(caminho_arquivo, engine='xlsxwriter')
        
        # 2. Converter o DF para Excel, mas começando da linha 4 (índice 3)
        # index=False remove os números das linhas
        df.to_excel(writer, sheet_name='Sheet1', startrow=3, index=False)
        
        # 3. Acessar o objeto da planilha para escrever no topo
        workbook  = writer.book
        worksheet = writer.sheets['Sheet1']
        
        # 4. Escrever as linhas de metadados manualmente
        worksheet.write(0, 0, "CAPITAL CONSIG - SCD") # Linha 1, Coluna A
        worksheet.write(1, 0, "AVERBAÇÃO - CONTAS")  # Linha 2, Coluna A
        # A linha 3 (índice 2) fica em branco automaticamente
        
        # 5. Salvar
        writer.close()
        print(f"Arquivo salvo com sucesso em: {caminho_arquivo}")

    def orbital_tratado(self):

        # Nesse caso, estaremos usando o arquivo ORBITAL_RESTANTE, que não requer tratamento algum
        if self.rubrica == 'BENEFÍCIO' and "GOV. MINAS GERAIS" in self.convenio:
            return self.orbital

        empregador_dict = {'PREF. PIRACICABA': 'PREF PIRACICABA', 
                           'SEMAE - SERVIÇO MUNICIPAL DE ÁGUA E ESGOTO DE PIRACICABA': 'PM PIRA SEMAE',
                           'PREV. PIRACICABA IPASP': 'PREF PIRA IPASP',
                           'INSS': 'INSS RMC',
                           'GOV. PARAÍBA': 'GOV PB INSPFEM',
                           'GOV. ALAGOAS': 'GOV AL CC',
                           'GOV. ALAGOAS': 'GOV AL CB',
                           'INSS': 'INSS BENEFICIO',
                           'PREF. CAJAMAR': 'PREF CAJAMAR CC',
                           'INSS': 'INSS BENEF CPL',
                           'INSS': 'INSS RMC CPL',
                           'INSS': 'INSS BENEF SEG',
                           'INSS': 'INSS RMC SEG',
                           'GOV. GOIÁS': 'GOV GO CPL',
                           'PREF. PICOS': 'PREF PICOS',
                           'PREF. GUARULHOS': 'PREF GRU CB',
                           'GOV. PIAUÍ': 'GOV PIAUÍ CC',
                           'GOV. MATO GROSSO': 'GOV MT CB',
                           'GOV. RIO DE JANEIRO': 'GOV RJ DG',
                           'GOV. RIO DE JANEIRO': 'GOV RJ',
                           'GOV. MINAS GERAIS - PMMG': 'GOV MG - PMMG',
                           'GOV. SANTA CATARINA': 'GOV S. CATARINA',
                           'PREF. NATAL': 'PM NATAL CB DG',
                           'GOV. MINAS GERAIS - SEPLAG': 'MG SEPLAG',
                           'GOV. GOIÁS': 'GOV GOIAS',
                           'GOV. PIAUÍ': 'GOV PIAUÍ CB',
                           'GOV. CEARÁ': 'GOV CEARA DG',
                           'GOV. MINAS GERAIS - PMMG': 'MG PMMG CB DG',
                           'INSS': 'INSS BEN S FL',
                           'GOV. MINAS GERAIS - CBMMG': 'MG CBMMG',
                           'PREF. GOIÂNIA': 'PM GOIANIA SEG',
                           'GOV. MINAS GERAIS - PMMG': 'MG - PMMG CC DG',
                           'GOV. PERNAMBUCO': 'GOV PE CC',
                           'GOV. CEARÁ': 'GOV CEARÁ',
                           'GOV. MINAS GERAIS - SEPLAG': 'MG SEPLAG CC DG',
                           'GOV. PERNAMBUCO': 'GOV PE CB',
                           'PREF. GOIÂNIA': 'PREF GOIÂNIA',
                           'GOV. MINAS GERAIS - SEPLAG': 'MG SEPLAG CB DG',
                           'GOV. SÃO PAULO': 'GOV SÃO PAULO',
                           'INSS': 'INSS RMC S FL',
                           'GOV. PERNAMBUCO': 'GOV PE CC DG',
                           'GOV. MINAS GERAIS - CBMMG': 'MG CBMMG CB DG',
                           'GOV. PARAÍBA': 'INSPFEM S FL',
                           'PREF. PICOS': 'PREF PICOS DG',
                           'GOV. MG - IPSEMG': 'GOV MG - IPSEMG',
                           'GOV. PARANÁ': 'GOV PARANA',
                           'GOV. RIO DE JANEIRO': 'GOV RJ SEG',
                           'GOV. MATO GROSSO': 'GOV MT PL CAPIT',
                           'GOV. SANTA CATARINA': 'GOV SC SEG',
                           'GOV. ESPÍRITO SANTO': 'GOV ES CB',
                           'GOV. PIAUÍ': 'GOV PIAUÍ CB DG',
                           'GOV. ESPÍRITO SANTO': 'GOV ES CB DG',
                           'GOV. MATO GROSSO': 'GOVMT CARTOS CB',
                           'GOV. MINAS GERAIS - SEPLAG': 'SEPL CC DG SEG',
                           'GOV. SÃO PAULO - SPPREV': 'GOV SPPREV',

                            }
        orbital = self.orbital

        convenio = self.convenio

        empregador = empregador_dict.get(convenio)

        front_para_separar = self.front

        if empregador:
            # Filtro dinâmico
            orbital_preparado = orbital.loc[
                orbital['DESCRIÇÃO DO EMPREG'].str.contains(empregador, case=False, na=False),
                ['CONTRATO', 'nome_mutuario', 'num_cpf_mutuario', 'VALID DESCONTO FINAL']
            ].copy()
        else:
            # Opcional: log de erro ou retorno vazio se o convênio não existir no dict
            print(f"Aviso: Convênio '{convenio}' não mapeado.")
            orbital_preparado = pd.DataFrame(columns=['CONTRATO', 'nome_mutuario', 'num_cpf_mutuario', 'VALID DESCONTO FINAL'])


        orbital_preparado.columns = ['Proposta', 'Cliente', 'CPF/CNPJ', 'VALOR DESCONTO']

        if self.convenio == "INSS":
            front_so_orbital = front_para_separar.loc[
            front_para_separar['Análise'].isin(['NÃO LANÇAR - ORBITAL', 'NÃO LANÇAR - TELESAQUE']),
            ['Contrato', 'Nome', 'CPF', 'Prestacao']].copy()
        else:
            front_so_orbital = front_para_separar.loc[
                front_para_separar['OBS'] == 'NÃO LANÇAR - ORBITAL',
                ['Contrato', 'Nome', 'CPF', 'Prestacao']].copy()
        
        front_so_orbital.columns = ['Proposta', 'Cliente', 'CPF/CNPJ', 'VALOR DESCONTO']

        # front_so_orbital['Proposta'] = front_so_orbital['Proposta'].astype(str).str.strip()

        # front_so_orbital['VALID DESCONTO FINAL'] = front_so_orbital['VALID DESCONTO FINAL'].astype(str).str.replace('.', '', regex=False)
        front_so_orbital['VALOR DESCONTO'] = front_so_orbital['VALOR DESCONTO'].astype(str).str.replace(',', '.', regex=False)
        front_so_orbital['VALOR DESCONTO'] = pd.to_numeric(front_so_orbital['VALOR DESCONTO'], errors='coerce')

        orbital_preparado['Proposta'] = orbital_preparado['Proposta'].astype('int64')

        orbital_final = pd.concat([front_so_orbital, orbital_preparado])

        orbital_final = orbital_final.drop_duplicates(subset=['Proposta'], keep='first')
        orbital_final['PRAZO'] = orbital_final['Proposta'].map(front_para_separar.set_index('Contrato')['Prazo'])

        print(f"orbital_tratado: Salvando arquivo de orbital tratado teste com front")
        try:
            orbital_final.to_excel(os.path.join(self.caminho, f"ORBITAL TRABALHADO {self.convenio}.xlsx"), index=False)
            print(f"orbital_tratado: ORBITAL TRABALHADO {self.convenio} salvo com sucesso!")
        except Exception as e:
            print(f"orbital_tratado: ERRO AO SALVAR ORBITAL TRABALHADO {self.convenio}: {e}")

        # Vamos tentar deixar somente os CPF que exclusivamente estão na rubrica de benefício
        if self.rubrica == 'CARTÃO' and "GOV. MINAS GERAIS" in self.convenio:
            averbado = self.averbado_final
            # Vamos separar os CPFs de front cartao e averbado beneficio
            cpf_averbado = averbado['CPF Ponto e Traço'].unique()

            orbital_restante = orbital_final[~orbital_final['CPF/CNPJ'].isin(cpf_averbado)]

            print(f'Teste de orbital que restou para a rubrica de beneficio\n{orbital_restante}')
            
            print(f"orbital_tratado: Salvando arquivo de orbital restante para beneficio")
            caminho_salvar = fr'{self.caminho}\ORBITAL RESTANTE PARA BENEFICIO.xlsx'
            self.salvar_com_layout_original(orbital_restante, caminho_salvar)

        return orbital_final