import pandas as pd
import os

class TRATA_ORBITAL:
    def __init__(self, orbital, front, convenio, caminho):
        self.orbital = orbital
        self.front = front
        self.convenio = convenio
        self.caminho = caminho

    def orbital_tratado(self):

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

        front_so_orbital = front_para_separar.loc[
            front_para_separar['OBS'] == 'NÃO LANÇAR - ORBITAL',
            ['Contrato', 'Nome', 'CPF', 'Prestacao']].copy()
        
        front_so_orbital.columns = ['Proposta', 'Cliente', 'CPF/CNPJ', 'VALOR DESCONTO']

        # front_so_orbital['Proposta'] = front_so_orbital['Proposta'].astype(str).str.strip()

        # front_so_orbital['VALID DESCONTO FINAL'] = front_so_orbital['VALID DESCONTO FINAL'].astype(str).str.replace('.', '', regex=False)
        front_so_orbital['VALOR DESCONTO'] = front_so_orbital['VALOR DESCONTO'].astype(str).str.replace(',', '.', regex=False)
        front_so_orbital['VALOR DESCONTO'] = pd.to_numeric(front_so_orbital['VALOR DESCONTO'], errors='coerce')

        orbital_final = pd.concat([front_so_orbital, orbital_preparado])

        orbital_final = orbital_final.drop_duplicates(subset=['Proposta'], keep='first')

        print(f"orbital_tratado: Salvando arquivo de orbital tratado teste com front")
        try:
            orbital_final.to_excel(os.path.join(self.caminho, f"ORBITAL TRABALHADO {self.convenio}.xlsx"), index=False)
            print(f"orbital_tratado: ORBITAL TRABALHADO {self.convenio} salvo com sucesso!")
        except Exception as e:
            print(f"orbital_tratado: ERRO AO SALVAR ORBITAL TRABALHADO {self.convenio}: {e}")

        return orbital_final