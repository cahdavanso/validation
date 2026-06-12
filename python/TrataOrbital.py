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

        empregador_dict = {
                            'PREF. PIRACICABA': ['PREF PIRACICABA'], 
                            'SEMAE - SERVIÇO MUNICIPAL DE ÁGUA E ESGOTO DE PIRACICABA': ['PM PIRA SEMAE'],
                            'PREV. PIRACICABA IPASP': ['PREF PIRA IPASP'],
                            'GOV. PARAÍBA': ['GOV PB INSPFEM', 'INSPFEM S FL'],
                            'GOV. ALAGOAS': ['GOV AL CC', 'GOV AL CB'],
                            'PREF. CAJAMAR': ['PREF CAJAMAR CC'],
                            'GOV. GOIÁS': ['GOV GO CPL', 'GOV GOIAS'],
                            'PREF. PICOS': ['PREF PICOS', 'PREF PICOS DG'],
                            'PREF. GUARULHOS': ['PREF GRU CB'],
                            'GOV. PIAUÍ': ['GOV PIAUÍ CC', 'GOV PIAUÍ CB', 'GOV PIAUÍ CB DG'],
                            'GOV. MATO GROSSO': ['GOV MT CB', 'GOV MT PL CAPIT', 'GOVMT CARTOS CB'],
                            'GOV. RIO DE JANEIRO': ['GOV RJ DG', 'GOV RJ', 'GOV RJ SEG'],
                            'GOV. MINAS GERAIS - PMMG': ['GOV MG - PMMG', 'MG PMMG CB DG', 'MG - PMMG CC DG'],
                            'GOV. SANTA CATARINA': ['GOV S. CATARINA', 'GOV SC SEG'],
                            'PREF. NATAL': ['PM NATAL CB DG'],
                            'GOV. MINAS GERAIS - SEPLAG': ['MG SEPLAG', 'MG SEPLAG CC DG', 'MG SEPLAG CB DG', 'SEPL CC DG SEG'],
                            'GOV. CEARÁ': ['GOV CEARA DG', 'GOV CEARÁ'],
                            'GOV. MINAS GERAIS - CBMMG': ['MG CBMMG', 'MG CBMMG CB DG'],
                            'PREF. GOIÂNIA': ['PM GOIANIA SEG', 'PREF GOIÂNIA'],
                            'GOV. PERNAMBUCO': ['GOV PE CC', 'GOV PE CB', 'GOV PE CC DG'],
                            'GOV. SÃO PAULO': ['GOV SÃO PAULO'],
                            'INSS': [
                                'INSS BENEFICIO', 'INSS BEN S FL', 'INSS BENEF CPL', 
                                'INSS BENEF SEG', 'INSS RMC', 'INSS RMC S FL', 
                                'INSS RMC CPL', 'INSS RMC SEG'
                            ],
                            'GOV. MG - IPSEMG': ['GOV MG - IPSEMG'],
                            'GOV. PARANÁ': ['GOV PARANA'],
                            'GOV. ESPÍRITO SANTO': ['GOV ES CB', 'GOV ES CB DG'],
                            'GOV. SÃO PAULO - SPPREV': ['GOV SPPREV']
                        }
        orbital = self.orbital

        convenio = self.convenio

        # Agora isso retorna uma lista de empregadores
        lista_empregadores = empregador_dict.get(convenio)

        front_para_separar = self.front

        if lista_empregadores:
            # Junta a lista em um único texto separado por "|" (Pipe)
            # Resultado: 'INSS BENEFICIO|INSS BEN S FL|INSS BENEF CPL...'
            padrao_busca = '|'.join(lista_empregadores)

            # Filtro dinâmico
            orbital_preparado = orbital.loc[
                # Passamos o padrao_busca e garantimos que regex=True
                orbital['DESCRIÇÃO DO EMPREG'].str.contains(padrao_busca, case=False, na=False, regex=True),
                ['CONTRATO', 'nome_mutuario', 'num_cpf_mutuario', 'VALID DESCONTO FINAL']
            ].copy()
        else:
            # Opcional: log de erro ou retorno vazio se o convênio não existir no dict
            print(f"Aviso: Convênio '{convenio}' não mapeado.")
            orbital_preparado = pd.DataFrame(columns=['CONTRATO', 'nome_mutuario', 'num_cpf_mutuario', 'VALID DESCONTO FINAL'])


        orbital_preparado.columns = ['Proposta', 'Cliente', 'CPF/CNPJ', 'VALOR DESCONTO']


        if self.convenio == "INSS":
            front_so_orbital = front_para_separar.loc[
            (front_para_separar['Análise'].isin(['NÃO LANÇAR - ORBITAL', 'NÃO LANÇAR - TELESAQUE', 'NÃO LANÇAR - COMPLEMENTAR'])) & (~front_para_separar['Status'].isin(["EM ANDAMENTO"])),
            ['NR_OPER_EDITADO', 'CLIENTE', 'CPF', 'VLR_PARC']].copy()
        else:
            front_so_orbital = front_para_separar.loc[
                (front_para_separar['OBS'] == 'NÃO LANÇAR - ORBITAL') & (~front_para_separar['Status'].isin(["EM ANDAMENTO"])),
                ['Contrato', 'Nome', 'CPF', 'Prestacao']].copy()
        
        front_so_orbital.columns = ['Proposta', 'Cliente', 'CPF/CNPJ', 'VALOR DESCONTO']

        # front_so_orbital['Proposta'] = front_so_orbital['Proposta'].astype(str).str.strip()

        # front_so_orbital['VALID DESCONTO FINAL'] = front_so_orbital['VALID DESCONTO FINAL'].astype(str).str.replace('.', '', regex=False)
        front_so_orbital['VALOR DESCONTO'] = front_so_orbital['VALOR DESCONTO'].astype(str).str.replace(',', '.', regex=False)
        front_so_orbital['VALOR DESCONTO'] = pd.to_numeric(front_so_orbital['VALOR DESCONTO'], errors='coerce')

        orbital_preparado.to_excel(os.path.join(self.caminho, f"ORBITAL PURO {self.convenio}.xlsx"), index=False)


        # Criar uma coluna temporária para remover os contratos liquidados, cancelados, ou com saldo positivo
        if self.convenio == 'INSS':
            orbital_preparado['OBS'] = orbital_preparado['Proposta'].map(front_para_separar.set_index('NR_OPER_EDITADO')['Análise'])
        else:
            orbital_preparado['OBS'] = orbital_preparado['Proposta'].map(front_para_separar.set_index('Contrato')['OBS'])
        orbital_preparado = orbital_preparado[~orbital_preparado['OBS'].isin(['NÃO LANÇAR - SALDO POSITIVO', 'NÃO LANÇAR - AÇÃO JUDICIAL', 'NÃO LANÇAR - LIQUIDADO', 'NÃO LANÇAR - CASOS PATRICK'])].copy()
        
        orbital_preparado['Proposta'] = orbital_preparado['Proposta'].astype('int64')
        orbital_final = pd.concat([front_so_orbital, orbital_preparado])

        orbital_final = orbital_final.drop_duplicates(subset=['Proposta'], keep='first')
        if self.convenio == "INSS":
            orbital_final['PRAZO'] = orbital_final['Proposta'].map(front_para_separar.set_index('NR_OPER_EDITADO')['Prazo'])
        else:
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