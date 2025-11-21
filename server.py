from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import pandas as pd
import logging
import io
from typing import List, Type, Optional

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

# --- Mapeamento de Convênios ---
CONSIGFACIL_CONVENIOS = [
        "GOV. DO MARANHÃO", "GOV. PIAUI", "PREF. BAYEUX", "PREF. CAJAMAR",
        "PREF. CAMPINA GRANDE", "PREF. CAMPO GRANDE", "PREF. CUIABÁ", "PREF. DE PORTO VELHO",
        "PREF. IMPERATRIZ MA", "PREF. ITU", "PREF. JOÃO PESSOA", "PREF. JUAZEIRO DO NORTE",
        "PREF. MARABÁ", "PREF. NITERÓI", "PREF. PAÇO DO LUMIAR", "PREF. PALMAS", "PREF. RECIFE",
        "PREF. SANTA RITA", "PREF. TERESINA"
]

CODATA_CONVENIO = ["GOV. DA PARAIBA"]

INSS_CONVENIO = ["INSS"]

CONVENIO_MAP: dict[str, Type] = {
    **{convenio: CONSIGFACIL for convenio in CONSIGFACIL_CONVENIOS},
    **{convenio: CODATA for convenio in CODATA_CONVENIO},
    **{convenio: INSS for convenio in INSS_CONVENIO}
}

# --- Função Auxiliar de Leitura ---
async def read_and_unify_files(file_list: List[UploadFile]):
    """
    Lê arquivos Excel (.xlsx, .xls) ou CSV/Texto (.csv, .txt) e unifica.
    """
    if not file_list:
        return None

    lista_df = []
    
    for uploaded_file in file_list:
        try:
            filename = uploaded_file.filename.lower()
            content = await uploaded_file.read()
            file_obj = io.BytesIO(content)

            logging.info(f"Lendo arquivo: {uploaded_file.filename}")

            if filename.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_obj)
            else:
                # Tenta diferentes codificações e separadores para CSV
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
            logging.error(f"ERRO CRÍTICO ao ler {uploaded_file.filename}: {e}")
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
    consignataria: Optional[str] = Form(None), # Novo campo opcional recebido do front
    
    # Campos de Arquivo (Aliases corrigidos para bater com app.js)
    AVERBADOS: List[UploadFile] = File(None, alias="AVERBADOS"),
    CONCILIACAO: List[UploadFile] = File(None, alias="CONCILIACAO"),
    LIQUIDADOS: List[UploadFile] = File(None, alias="LIQUIDADOS"),
    LIMINAR: List[UploadFile] = File(None, alias="LIMINAR"),
    HISTORICO_DE_REFINS: List[UploadFile] = File(None, alias="HISTORICO_DE_REFINS"),
    CREDBASE_AKRK_E_DIG: List[UploadFile] = File(None, alias="CREDBASE"),
    FUNCAO: List[UploadFile] = File(None, alias="FUNCAO"),
    ANDAMENTO: List[UploadFile] = File(None, alias="ANDAMENTO"),
    ORBITAL: List[UploadFile] = File(None, alias="ORBITAL"),
    CASOS_CAPITAL: List[UploadFile] = File(None, alias="CASOS_CAPITAL")
):
    logging.info(f"\n--- INICIANDO VALIDAÇÃO: {convenio} ---")
    if consignataria:
        logging.info(f"Consignatária: {consignataria}")
    
    ValidadorClass = CONVENIO_MAP.get(convenio, CONSIGFACIL)
    
    CAMINHO_SAIDA = os.path.join(os.getcwd(), "output_data", convenio.replace(' ', '_').replace('.', ''))
    os.makedirs(CAMINHO_SAIDA, exist_ok=True)

    # Leitura dos arquivos
    try:
        averbados_df = await read_and_unify_files(AVERBADOS)
        conciliacao_df = await read_and_unify_files(CONCILIACAO)
        liquidados_df = await read_and_unify_files(LIQUIDADOS)
        liminar_df = await read_and_unify_files(LIMINAR)
        historico_df = await read_and_unify_files(HISTORICO_DE_REFINS)
        credbase_df = await read_and_unify_files(CREDBASE_AKRK_E_DIG)
        funcao_df = await read_and_unify_files(FUNCAO)
        andamento_df = await read_and_unify_files(ANDAMENTO)
        orbital_df = await read_and_unify_files(ORBITAL)
        casoscapital_df = await read_and_unify_files(CASOS_CAPITAL)

        # Instanciação Condicional
        if ValidadorClass == CODATA:
            # CODATA exige consignatária
            validador = ValidadorClass(
                portal_file_list=averbados_df,
                convenio=convenio,
                credbase=credbase_df,
                funcao=funcao_df,
                consignataria=consignataria, # Passa o valor aqui
                conciliacao=conciliacao_df,
                liquidados=liquidados_df,
                andamento_list=andamento_df,
                caminho=CAMINHO_SAIDA,
                tutela=liminar_df,
                orbital=orbital_df
            )

        elif ValidadorClass == INSS:
            # CODATA exige consignatária
            validador = ValidadorClass(
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
            # CONSIGFACIL (Padrão)
            validador = ValidadorClass(
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

        return {"message": "Sucesso", "output_path": CAMINHO_SAIDA}

    except Exception as e:
        logging.error(f"FALHA NO PROCESSAMENTO: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")