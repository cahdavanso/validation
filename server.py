from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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

app = FastAPI()

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

# Todos os outros são Consigfacil
CONSIGFACIL_CONVENIOS = [
    "GOV. MA", "GOV. PI", "PREF. BAYEUX", "PREF. CAJAMAR",
    "PREF. CAMPINA GRANDE", "PREF. CAMPO GRANDE", "PREF. CUIABÁ", "PREF. DE PORTO VELHO",
    "PREF. IMPERATRIZ MA", "PREF. ITU", "PREF. JOÃO PESSOA", "PREF. JUAZEIRO DO NORTE",
    "PREF. MARABÁ", "PREF. NITERÓI", "PREF. PAÇO DO LUMIAR", "PREF. PALMAS", "PREF. RECIFE",
    "PREF. SANTA RITA", "PREF. TERESINA", "CÂMARA DE TERESÓPOLIS", "GOV. MG", 
    "GOV. RN", "GOV. SC"
]

# --- Função Auxiliar de Leitura ---
async def read_and_unify_files(file_list: List[UploadFile]):
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
    output_path: Optional[str] = Form(None),
    
    # Todos os campos possíveis do sistema
    AVERBADOS: List[UploadFile] = File(None, alias="AVERBADOS"),
    CONCILIACAO: List[UploadFile] = File(None, alias="CONCILIACAO"),
    LIQUIDADOS: List[UploadFile] = File(None, alias="LIQUIDADOS"),
    LIMINAR: List[UploadFile] = File(None, alias="LIMINAR"),
    HISTORICO_DE_REFINS: List[UploadFile] = File(None, alias="HISTORICO_DE_REFINS"),
    CREDBASE: List[UploadFile] = File(None, alias="CREDBASE"),
    FUNCAO: List[UploadFile] = File(None, alias="FUNCAO"),
    ANDAMENTO: List[UploadFile] = File(None, alias="ANDAMENTO"),
    ORBITAL: List[UploadFile] = File(None, alias="ORBITAL"),
    CASOS_CAPITAL: List[UploadFile] = File(None, alias="CASOS_CAPITAL")
):
    logging.info(f"\n--- INICIANDO VALIDAÇÃO: {convenio} ---")
    
    # 1. Define o caminho de saída
    if output_path and output_path.strip():
        CAMINHO_SAIDA = output_path.strip()
    else:
        CAMINHO_SAIDA = os.path.join(os.getcwd(), "output_data", convenio.replace(' ', '_').replace('.', ''))
    
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
        funcao_df = await read_and_unify_files(FUNCAO)
        andamento_df = await read_and_unify_files(ANDAMENTO)
        orbital_df = await read_and_unify_files(ORBITAL)
        casoscapital_df = await read_and_unify_files(CASOS_CAPITAL)

        # 3. SELEÇÃO DO VALIDADOR (SEM A VARIÁVEL PROBLEMÁTICA)
        
        if convenio in CODATA_CONVENIO:
            logging.info("Usando validador: CODATA")
            validador = CODATA(
                portal_file_list=averbados_df,
                convenio=convenio,
                credbase=credbase_df,
                funcao=funcao_df,
                consignataria=consignataria, 
                conciliacao=conciliacao_df,
                liquidados=liquidados_df,
                andamento_list=andamento_df,
                caminho=CAMINHO_SAIDA,
                tutela=liminar_df,
                orbital=orbital_df
            )

        elif convenio in INSS_CONVENIO:
            logging.info("Usando validador: INSS")
            validador = INSS(
                portal_file_list=averbados_df,
                funcao=funcao_df,
                conciliacao=conciliacao_df,
                liquidados=liquidados_df,
                caminho=CAMINHO_SAIDA,
                tutela=liminar_df,
                orbital=orbital_df,
                casos_capital=casoscapital_df
            )

        else:
            # Padrão para todos os outros (Consigfacil)
            logging.info("Usando validador: CONSIGFACIL")
            validador = CONSIGFACIL(
                portal_file_list=averbados_df, 
                convenio=convenio,
                credbase=credbase_df,
                funcao=funcao_df,
                conciliacao=conciliacao_df,
                andamento_list=andamento_df,
                caminho=CAMINHO_SAIDA,
                liquidados=liquidados_df,
                historico_refin=historico_df,
                tutela=liminar_df 
            )

        return {"message": "Validação concluída com sucesso!", "output_path": CAMINHO_SAIDA}

    except Exception as e:
        error_traceback = traceback.format_exc()
        logging.error("##################################################")
        logging.error(error_traceback)
        logging.error("##################################################")
        
        raise HTTPException(status_code=500, detail=f"Erro Técnico Detalhado:\n{error_traceback}")