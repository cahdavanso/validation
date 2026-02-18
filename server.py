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
from typing import List, Optional

# Importa as classes de validação
from python.Consigfacil import CONSIGFACIL 
from python.Codata import CODATA
from python.INSS import INSS
from python.Serha import SERHA
from python.Consiglog import CONSIGLOG

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
CODATA_CONVENIO = ["GOV. PB"]

INSS_CONVENIO = ["INSS"]

SERHA_CONVENIO = ["GOV. MG - IPSM", "GOV. MG - CBMMG", "GOV. MG - PMMG", "GOV. MG - SEPLAG", "GOV. MG - IPSEMG"]

CONSIGLOG_CONVENIO = ["GOV. BAHIA", "PREF. ARAGUAÍNA", "PREF. DE CAJAMAR", "PREF. DUQUE DE CAXIAS", "PREF. DUQUE DE CAXIAS - COTAR", "PREF. DUQUE DE CAXIAS - IMPDC", "PREF. GOIÂNIA", "PREF. SANTOS", "PREF. SÃO GONÇALO", "PREF. TAUBATÉ", "PREVIDÊNCIA SÃO GONÇALO"]


# Todos os outros são Consigfacil
CONSIGFACIL_CONVENIOS = [
    "GOV. MA", "GOV. PI", "PREF. BAYEUX", "PREF. CAJAMAR",
    "PREF. CAMPINA GRANDE", "PREF. CAMPO GRANDE", "PREF. CUIABÁ", "PREF. DE PORTO VELHO",
    "PREF. IMPERATRIZ MA", "PREF. ITU", "PREF. JOÃO PESSOA", "PREF. JUAZEIRO DO NORTE",
    "PREF. MARABÁ", "PREF. NITERÓI", "PREF. PAÇO DO LUMIAR", "PREF. PALMAS", "PREF. RECIFE",
    "PREF. SANTA RITA", "PREF. TERESINA", "CÂMARA DE TERESÓPOLIS", "GOV. RN", "GOV. SC"
]

# --- Função Auxiliar de Leitura ---
async def read_and_unify_files(file_list: List[UploadFile]):
    conv: str = Form(...)

    if not file_list:
        return None
    lista_df = []
    for uploaded_file in file_list:
        try:
            filename = uploaded_file.filename.lower()
            content = await uploaded_file.read()
            file_obj = io.BytesIO(content)
            logging.info(f"Lendo: {uploaded_file.filename}")

            if filename.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_obj)
            elif filename == 'liminar' and filename.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_obj, sheet_name='DEMAIS CONVÊNIOS')
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
    AVERBADOS: List[UploadFile] = File(None, alias="AVERBADOS"),
    CONCILIACAO: List[UploadFile] = File(None, alias="CONCILIACAO"),
    LIQUIDADOS: List[UploadFile] = File(None, alias="LIQUIDADOS"),
    LIMINAR: List[UploadFile] = File(None, alias="LIMINAR"),
    HISTORICO_DE_REFINS: List[UploadFile] = File(None, alias="HISTORICO_DE_REFINS"),
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
        conciliacao_df = await read_and_unify_files(CONCILIACAO)
        liquidados_df = await read_and_unify_files(LIQUIDADOS)
        liminar_df = await read_and_unify_files(LIMINAR)
        historico_df = await read_and_unify_files(HISTORICO_DE_REFINS)
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
                consignataria=consignataria, 
                conciliacao=conciliacao_df,
                andamento_list=andamento_df,
                caminho=CAMINHO_SAIDA
            )

        elif convenio in INSS_CONVENIO:
            logging.info("Usando validador: INSS")
            validador = INSS(
                portal_file_list=averbados_df,
                front=front_df,
                conciliacao=conciliacao_df,
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
                trabalhado_anterior=trabalhado_anterior_df,
                rubrica=rubrica,
                caminho=CAMINHO_SAIDA,
                complementar=complementar_df
            )
        elif convenio in CONSIGLOG_CONVENIO:
            logging.info("Usando validador: CONSIGLOG")
            validador = CONSIGLOG(
                portal_file_list=averbados_df, 
                convenio=convenio,
                front=front_df,
                consignataria=consignataria,
                conciliacao=conciliacao_df,
                caminho=CAMINHO_SAIDA,
                orbital=orbital_df
            )

        else:
            # Padrão para todos os outros (Consigfacil)
            logging.info("Usando validador: CONSIGFACIL")
            validador = CONSIGFACIL(
                portal_file_list=averbados_df, 
                convenio=convenio,
                front=front_df,
                conciliacao=conciliacao_df,
                andamento_list=andamento_df,
                caminho=CAMINHO_SAIDA,
            )

        # 1. Defina o nome do arquivo ZIP
        nome_zip = f"resultado_{convenio.replace(' ', '_')}"
        caminho_zip_completo = os.path.join(PASTA_BASE, nome_zip) # O shutil adiciona o .zip sozinho

        # 2. Compacta a pasta CAMINHO_SAIDA inteira
        # Isso pega os 5 arquivos que estão lá dentro e vira um só
        # shutil.make_archive(caminho_zip_completo, 'zip', CAMINHO_SAIDA)

        # 1. Lista os arquivos que o validador criou
        arquivos_na_pasta = os.listdir(CAMINHO_SAIDA)
        
        # 2. Filtra para pegar apenas um arquivo Excel (ou o primeiro da lista)
        # Vamos ignorar o ZIP por enquanto
        planilhas = [f for f in arquivos_na_pasta if f.endswith(('.xlsx', '.xls', '.csv'))]

        if not planilhas:
            raise HTTPException(status_code=500, detail="Nenhum arquivo foi gerado pelo validador.")

        nome_do_arquivo_teste = planilhas[0]
        
        # 3. Monta o caminho relativo (Pasta/Arquivo)
        pasta_formatada = convenio.replace(' ', '_').replace('.', '')
        caminho_para_frontend = f"{pasta_formatada}/{nome_do_arquivo_teste}"

        logging.info(f"Teste 3: Retornando apenas o arquivo {caminho_para_frontend}")

        return {
            "message": "Teste de arquivo único",
            "filename": caminho_para_frontend 
        }
    
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
    file_path = os.path.join(os.getcwd(), "output_data", filename)
    
    if os.path.exists(file_path):
        return FileResponse(
            path=file_path, 
            filename=os.path.basename(filename),
        )
    return {"error": "Arquivo não encontrado"}

