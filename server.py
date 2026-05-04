from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.staticfiles import StaticFiles # <--- Importante
from fastapi.responses import FileResponse, HTMLResponse # <--- Importante
from fastapi.middleware.cors import CORSMiddleware
from flask import Flask, render_template, send_from_directory, jsonify
import shutil
import gc
import os
import pandas as pd
import logging
import io
import traceback
from time import sleep
import re
from typing import List, Optional
import uvicorn

# Importa as classes de validação
from python.Consigfacil import CONSIGFACIL 
from python.Codata import CODATA
from python.INSS import INSS
from python.Serha import SERHA
from python.Consiglog import CONSIGLOG
from python.IgeprevGovTo_Preliminar import IGEPREV_GOVTO
from python.Zetra import ZETRA

app = FastAPI()

# 1. Configura as pastas para o site (CSS, JS, Imagens)
# O servidor precisa saber onde estão esses arquivos para entregar ao navegador
app.mount("/styles", StaticFiles(directory="styles"), name="styles")
app.mount("/scripts", StaticFiles(directory="scripts"), name="scripts")
app.mount("/python", StaticFiles(directory="python"), name="python")
# Se tiver pasta assets, descomente a linha abaixo:
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

# 2. Rota para servir a página principal (Seu Frontend)
@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

# --- Configuração de Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuração de CORS ---
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- LISTAS DE CONVÊNIOS ---
CODATA_CONVENIO = ["GOV. PARAÍBA"]

INSS_CONVENIO = ["INSS"]

SERHA_CONVENIO = ["GOV. MINAS GERAIS - IPSM", "GOV. MINAS GERAIS - CBMMG", "GOV. MINAS GERAIS - PMMG", "GOV. MINAS GERAIS - SEPLAG", "GOV. MINAS GERAIS - IPSEMG"]

CONSIGLOG_CONVENIO = ["GOV. BAHIA", "PREF. ARAGUAÍNA", "PREF. DUQUE DE CAXIAS", "PREF. DUQUE DE CAXIAS - COTAR", 
                      "PREF. DUQUE DE CAXIAS - IMPDC", "PREF. GOIÂNIA", "PREF. SANTOS", "PREF. SÃO GONÇALO", "PREF. TAUBATÉ", "PREVIDÊNCIA SÃO GONÇALO", "PREF. RIBEIRÃO PRETO"]

ZETRA_CONVENIO = [
         "GOV. ESPÍRITO SANTO", "GOV. PARANÁ", "GOV. RIO DE JANEIRO", "IGEPREV", "PREF. BELO HORIZONTE", "PREF. AÇAILÂNDIA", 
         "PREF. CAMPINAS", "PREF. MACAÉ", "PREF. SÃO JOSE DE RIBAMAR", "PREF. SÃO PAULO-HMSP", "PREF. SOBRAL", "PREVIPALMAS"
         ]

TO_IGEPREV_CONVENIO = ["GOV. TOCANTINS e IGEPREV"]

# Todos os outros são Consigfacil
CONSIGFACIL_CONVENIOS = [
    "GOV. MARANHÃO", "GOV. MATO GROSSO", "GOV. PAUÍ", "GOV. PERNAMBUCO","PREF. BAYEUX", "PREF. CAJAMAR",
    "PREF. CAMPINA GRANDE", "PREF. CAMPO GRANDE", "PREF. CUIABÁ", "PREF. PORTO VELHO",
    "PREF. IMPERATRIZ MA", "PREF. ITU", "PREF. JOÃO PESSOA", "PREF. JUAZEIRO DO NORTE",
    "PREF. MARABÁ", "PREF. NITERÓI", "PREF. PAÇO DO LUMIAR", "PREF. PALMAS", "PREF. RECIFE",
    "PREF. SANTA RITA", "PREF. TERESINA", "CÂMARA DE TERESÓPOLIS", "GOV. RIO GRANDE DO NORTE", "PREF. NATAL",
    "PREF. TUTÓIA"
]

def abas(excel_file):
    # 2. Pegamos a lista de todas as abas disponíveis
    todas_as_abas = excel_file.sheet_names

    # print(f'todas as abas: {todas_as_abas}')

    # 3. Identificamos as abas dinamicamente
    # Buscamos por 'Linhas' mas garantimos que não seja a que você quer descartar (se houver uma regra)
    # E buscamos por 'desc. Parciais'
    aba_linhas = None
    aba_parciais = None

    for nome in todas_as_abas:
        # Lógica para a aba de Linhas
        # Aqui verificamos se tem 'Linhas' no nome e se NÃO tem outros termos indesejados
        if "Linhas" in nome and "Suspensas" not in nome:
            aba_linhas = nome
        
        # Lógica para a aba de Descontos Parciais
        if "Desc. Parciais" in nome:
            aba_parciais = nome

        if  aba_linhas is not None and aba_parciais is not None:
            return aba_linhas, aba_parciais
        else:
            continue

# --- Função Auxiliar de Leitura ---
async def read_and_unify_files(file_list: List[UploadFile]):
    conv: str = Form(...)

    if not file_list:
        return None
    lista_df = []
    for uploaded_file in file_list:
        try:
            filename = uploaded_file.filename.lower()
            # print(f'nome do arquivo: {filename}')
            # 1. Pegar o cabeçalho Content-Disposition
            content_disposition = uploaded_file.headers.get("content-disposition", "")
            match = re.search('name="([^"]+)"', content_disposition)
            # Se encontrar o 'name', armazena, senão usa o filename como reserva
            name = match.group(1).lower() if match else "desconhecido"
            content = await uploaded_file.read()
            file_obj = io.BytesIO(content)
            logging.info(f"Lendo: {uploaded_file.filename}")

            print(f'File list: {file_list}')

            
            
            if "kobraki" in filename and filename.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_obj, sheet_name='CONSOLIDADO')
            elif "d8_to" in name:
                d8_gov_to_amostra = pd.ExcelFile(file_obj)
                planilha_linhas, planilha_parciais = abas(d8_gov_to_amostra)
                df_d8_linhas = pd.read_excel(file_obj, header=7, sheet_name=planilha_linhas)

                print(f'HEAD de d8_to: {df_d8_linhas.head()}')

                df_d8_parciais = pd.read_excel(file_obj, header=7, sheet_name=planilha_parciais)
                df_d8_parciais.rename(columns={'R$ PARCELA DESCONTADA': 'R$ PARCELA'}, inplace=True)
                mapeamento_d8 = ["ORDEM", "REFERENCIA", "CPF", "MATRICULA", "NOME", "RUBRICA", "PARCELA", "ADF", "R$ PARCELA"]
                df_d8_parciais_completo = df_d8_parciais[mapeamento_d8]


                df = pd.concat([df_d8_linhas, df_d8_parciais_completo], ignore_index=True)
            elif "averbados_to" in name:
                df_preliminar = pd.read_excel(file_obj)
                linha_identificacao = str(df_preliminar.iloc[5].values)
                if "CAPITAL" in linha_identificacao:
                    consig = "CAPITAL"
                elif "CIASPREV" in linha_identificacao:
                    consig = "CIASPREV"
                elif "HOJE" in linha_identificacao:
                    consig = "HP"
                else:
                    consig = "CLICKBANK"

                df = pd.read_excel(file_obj, header=17)
                df['Consignataria'] = consig
            elif "averbados_igeprev" in name:
                df_preliminar = pd.read_excel(file_obj)
                linha_identificacao = str(df_preliminar.iloc[1].values)
                consig = "CAPITAL" if "CAPITAL" in linha_identificacao else "CIASPREV"
                df = pd.read_excel(file_obj, header=4)
                df = df[:-6]
                df['Consignataria'] = consig
                df = df.dropna(axis=1, how='all')
            elif "orbital" in name:
                df = pd.read_excel(file_obj, header=3)
                # print(f'Cabeçalho de orbital:\n{df.head(3)}')
            elif filename.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_obj) 
            else:
                try:
                    file_obj.seek(0)
                    df = pd.read_csv(file_obj, encoding="utf-8-sig", sep=";", on_bad_lines="skip", low_memory=False)
                except:
                    try:
                        file_obj.seek(0)
                        df = pd.read_csv(file_obj, encoding="latin1", sep=";", on_bad_lines="skip", low_memory=False)
                    except:
                        file_obj.seek(0)
                        df = pd.read_csv(file_obj, encoding="latin1", sep=",", on_bad_lines="skip", low_memory=False)
            lista_df.append(df)
        except Exception as e:
            error_msg = traceback.format_exc()
            logging.error(f"Erro ao ler {uploaded_file.filename}:\n{error_msg}")
            continue
    
    if not lista_df:
        return None
    return pd.concat(lista_df, ignore_index=True)

@app.get("/test")
def test_endpoint():
    return {"message": "Servidor Online"}
    

@app.post("/validar")
async def validar_planilhas(
    convenio: str = Form(...),
    consignataria: Optional[str] = Form(None),
    rubrica: Optional[str] = Form(None),
    output_path: Optional[str] = Form(None),
    
    # Todos os campos possíveis do sistema
    # NÃO PODE TER ESPAÇO NOS NOMES EM ALIAS, PRECISA COLOCAR ALGUM SEPARADOR COMO _ OU - OU TUDO JUNTO
    AVERBADOS: List[UploadFile] = File(None, alias="AVERBADOS"),
    AVERBADOS_TO: List[UploadFile] = File(None, alias="AVERBADOS_TO"),
    AVERBADOS_IGEPREV: List[UploadFile] = File(None, alias="AVERBADOS_IGEPREV"),
    ZIPS: List[UploadFile] = File(None, alias="ZIPS"),
    CONCILIACAO: List[UploadFile] = File(None, alias="CONCILIACAO"),
    KOBRAKI: List[UploadFile] = File(None, alias="KOBRAKI"),
    D8_TO: List[UploadFile] = File(None, alias="D8_TO"),
    D8_IGEPREV: List[UploadFile] = File(None, alias="D8_IGEPREV"),
    LIQUIDADOS: List[UploadFile] = File(None, alias="LIQUIDADOS"),
    LIMINAR: List[UploadFile] = File(None, alias="LIMINAR"),
    HISTORICO: List[UploadFile] = File(None, alias="HISTORICO"),
    CREDBASE: List[UploadFile] = File(None, alias="CREDBASE"),
    FRONT: List[UploadFile] = File(None, alias="FRONT"),
    FUNCAO: List[UploadFile] = File(None, alias="FUNCAO"),
    ANDAMENTO: List[UploadFile] = File(None, alias="ANDAMENTO"),
    TRABALHADO_ANTERIOR: List[UploadFile] = File(None, alias="TRABALHADO_ANTERIOR"),
    ORBITAL: List[UploadFile] = File(None, alias="ORBITAL"),
    COMPLEMENTAR: List[UploadFile] = File(None, alias="COMPLEMENTAR"),
    CASOS_CAPITAL: List[UploadFile] = File(None, alias="CASOS_CAPITAL"),
):
    logging.info(f"\n--- INICIANDO VALIDAÇÃO: {convenio} ---")
    
    # Define um caminho fixo no servidor (seguro para nuvem)
    # Removemos o "if output_path" porque o servidor não acessa o PC do usuário
    PASTA_BASE = os.path.join(os.getcwd(), "output_data")
    
    # --- NOVA LÓGICA DE LIMPEZA ---
    if os.path.exists(PASTA_BASE):
        # Deleta a pasta inteira e tudo dentro dela
        shutil.rmtree(PASTA_BASE)
    
    # Recria a pasta do zero (vazia e limpa)
    os.makedirs(PASTA_BASE, exist_ok=True)
    # ------------------------------
    
    # Cria uma subpasta com o nome do convênio (opcional, ajuda na organização)
    CAMINHO_SAIDA = os.path.join(PASTA_BASE, convenio.replace(' ', '_').replace('.', ''))
    
    try:
        os.makedirs(CAMINHO_SAIDA, exist_ok=True)
    except Exception as e:
        error_trace = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"Erro ao criar pasta de saída:\n{error_trace}")
    
    try:
        # 2. Leitura dos arquivos
        averbados_df = await read_and_unify_files(AVERBADOS)
        averbados_to_df = await read_and_unify_files(AVERBADOS_TO)
        averbados_igeprev_df = await read_and_unify_files(AVERBADOS_IGEPREV)
        conciliacao_df = await read_and_unify_files(CONCILIACAO)
        kobraki_df = await read_and_unify_files(KOBRAKI)
        d8_df_to = await read_and_unify_files(D8_TO)
        d8_df_igeprev = await read_and_unify_files(D8_IGEPREV)
        liquidados_df = await read_and_unify_files(LIQUIDADOS)
        liminar_df = await read_and_unify_files(LIMINAR)
        historico_df = await read_and_unify_files(HISTORICO)
        credbase_df = await read_and_unify_files(CREDBASE)
        front_df = await read_and_unify_files(FRONT)
        funcao_df = await read_and_unify_files(FUNCAO)
        andamento_df = await read_and_unify_files(ANDAMENTO)
        trabalhado_anterior_df = await read_and_unify_files(TRABALHADO_ANTERIOR)
        orbital_df = await read_and_unify_files(ORBITAL)
        complementar_df = await read_and_unify_files(COMPLEMENTAR)
        casoscapital_df = await read_and_unify_files(CASOS_CAPITAL)

        # 3. SELEÇÃO DO VALIDADOR (SEM A VARIÁVEL PROBLEMÁTICA)
        
        if convenio in CODATA_CONVENIO:
            logging.info("Usando validador: CODATA")
            validador = CODATA(
                portal_file_list=averbados_df,
                convenio=convenio,
                front = front_df,
                funcao=funcao_df,
                consignataria=consignataria, 
                conciliacao=conciliacao_df,
                kobraki=kobraki_df,
                andamento_list=andamento_df,
                orbital=orbital_df,
                caminho=CAMINHO_SAIDA
            )

        elif convenio in INSS_CONVENIO:
            logging.info("Usando validador: INSS")
            validador = INSS(
                portal_file_list=averbados_df,
                front=front_df,
                conciliacao=conciliacao_df,
                kobraki=kobraki_df,
                caminho=CAMINHO_SAIDA,
                casos_capital=casoscapital_df
            )
        elif convenio in SERHA_CONVENIO:
            logging.info("Usando validador: SERHA")
            validador = SERHA(
                portal_file_list=averbados_df,
                convenio=convenio,
                front=front_df,
                conciliacao=conciliacao_df,
                kobraki=kobraki_df,
                trabalhado_anterior=trabalhado_anterior_df,
                rubrica=rubrica,
                caminho=CAMINHO_SAIDA,
                complementar=complementar_df,
                orbital=orbital_df
            )
        elif convenio in CONSIGLOG_CONVENIO:
            logging.info("Usando validador: CONSIGLOG")
            validador = CONSIGLOG(
                portal_file_list=averbados_df, 
                convenio=convenio,
                front=front_df,
                consignataria=consignataria,
                conciliacao=conciliacao_df,
                kobraki=kobraki_df,
                caminho=CAMINHO_SAIDA,
                orbital=orbital_df
            )
        
        elif convenio in ZETRA_CONVENIO:
            logging.info("Usando o validador: ZETRA")
            validador = ZETRA(
                portal_file_path=ZIPS,
                convenio=convenio,
                front=front_df,
                conciliacao=conciliacao_df,
                kobraki=kobraki_df,
                consignataria=consignataria,
                caminho=CAMINHO_SAIDA,
                historico=historico_df,
                orbital=orbital_df
            )
        elif convenio in TO_IGEPREV_CONVENIO:
            logging.info("Usando o validador: GOV TO e IGEPREV")
            validador = IGEPREV_GOVTO(
                portal_file_path_to=averbados_to_df,
                portal_file_path_igeprev=averbados_igeprev_df,
                d8_file_path_to=d8_df_to,
                d8_file_path_igeprev=d8_df_igeprev,
                front=front_df,
                funcao=funcao_df,
                conciliacao=conciliacao_df,
                kobraki=kobraki_df,
                caminho=CAMINHO_SAIDA
            )
        else:
            # Padrão para todos os outros (Consigfacil)
            logging.info("Usando validador: CONSIGFACIL")
            validador = CONSIGFACIL(
                portal_file_list=averbados_df, 
                convenio=convenio,
                front=front_df,
                funcao=funcao_df,
                conciliacao=conciliacao_df,
                kobraki=kobraki_df,
                andamento_list=andamento_df,
                caminho=CAMINHO_SAIDA,
            )

        # 1. Pequena pausa para garantir que o sistema de arquivos liberou os .xlsx
        sleep(1) 

        # 2. Verifica se realmente há arquivos para zipar
        arquivos_gerados = os.listdir(CAMINHO_SAIDA)
        if not arquivos_gerados:
            raise HTTPException(status_code=500, detail="Validador não gerou arquivos para o ZIP.")

        # 3. Define os nomes
        nome_zip = f"resultado_{convenio.replace(' ', '_').replace('.', '')}"
        # Onde o arquivo ZIP vai ficar (na raiz da PASTA_BASE)
        caminho_zip_destino = os.path.join(PASTA_BASE, nome_zip) 

        try:
            # 4. Cria o ZIP
            # 'zip', CAMINHO_SAIDA -> Pega tudo dentro da pasta do convênio e gera o .zip
            shutil.make_archive(caminho_zip_destino, 'zip', CAMINHO_SAIDA)
            logging.info(f"ZIP criado com sucesso: {nome_zip}.zip")
            
            # 5. Limpeza de memória estratégica
            # (Pegue a lista de variáveis que definimos antes)
            for var in ['averbados_df', 'conciliacao_df', 'liquidados_df', 'front_df']:
                if var in locals():
                    del locals()[var]
            gc.collect()

            # 6. Retorna o nome do arquivo ZIP para o download
            return {
                "message": "Validação concluída com sucesso!",
                "filename": f"{nome_zip}.zip" 
            }

        except Exception as e:
            logging.error(f"Erro ao criar ZIP: {e}")
            raise HTTPException(status_code=500, detail="Erro na compactação dos arquivos.")
    
    except Exception as e:
        error_traceback = traceback.format_exc()
        logging.error("##################################################")
        logging.error(error_traceback)
        logging.error("##################################################")
        
        raise HTTPException(status_code=500, detail=f"Erro Técnico Detalhado:\n{error_traceback}")
    
# 3. NOVA ROTA: Download do Arquivo
# Note o ":path" depois de filename. Isso permite baixar arquivos dentro de subpastas
@app.get("/download/{filename:path}")
async def download_file(filename: str):
    # Procura o arquivo na PASTA_BASE (output_data)
    file_path = os.path.join(os.getcwd(), "output_data", filename)
    
    if os.path.exists(file_path):
        return FileResponse(
            path=file_path,
            filename=os.path.basename(filename),
            media_type='application/zip' if filename.endswith('.zip') else None
        )
    
    logging.error(f"Arquivo não encontrado: {file_path}")
    return {"error": "Arquivo não encontrado"}


# É melhor comentar do que apagar na próxima vez que precisar testar no render
if __name__ == "__main__":
    # Pega a porta do Render ou usa 5000 se estiver local
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)