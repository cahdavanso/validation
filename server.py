from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import pandas as pd
import logging
import io
from typing import List, Type

# Importa as classes de validação
from python.Consigfacil import CONSIGFACIL 
from python.Codata import CODATA

app = FastAPI()

# Configuração de CORS
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mapeamento de Convênios
CONSIGFACIL_CONVENIOS = [
        "GOV. DO MARANHÃO", "GOV. PIAUI", "PREF. BAYEUX", "PREF. CAJAMAR",
        "PREF. CAMPINA GRANDE", "PREF. CAMPO GRANDE", "PREF. CUIABÁ", "PREF. DE PORTO VELHO",
        "PREF. IMPERATRIZ MA", "PREF. ITU", "PREF. JOÃO PESSOA", "PREF. JUAZEIRO DO NORTE",
        "PREF. MARABÁ", "PREF. NITERÓI", "PREF. PAÇO DO LUMIAR", "PREF. PALMAS", "PREF. RECIFE",
        "PREF. SANTA RITA", "PREF. TERESINA"
]

CODATA_CONVENIO = ["GOV. DA PARAIBA"]

CONVENIO_MAP: dict[str, Type] = {
    **{convenio: CONSIGFACIL for convenio in CONSIGFACIL_CONVENIOS},
    **{convenio: CODATA for convenio in CODATA_CONVENIO}
}

# --- FUNÇÃO DE LEITURA INTELIGENTE (CORRIGIDA) ---
def read_and_unify_files(file_list: List[UploadFile]):
    """
    Lê arquivos Excel ou CSV baseando-se na extensão e unifica em um DataFrame.
    """
    if not file_list:
        return None

    lista_df = []
    
    for uploaded_file in file_list:
        try:
            filename = uploaded_file.filename.lower()
            content = uploaded_file.file.read() # Lê o conteúdo para memória
            file_obj = io.BytesIO(content) # Cria objeto em memória

            logging.info(f"Lendo arquivo: {uploaded_file.filename}")

            # 1. Se for Excel (.xlsx, .xls)
            if filename.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_obj)
            
            # 2. Se for CSV ou Texto (.csv, .txt)
            else:
                # Tenta UTF-8 com ponto e vírgula (padrão brasileiro)
                try:
                    file_obj.seek(0)
                    df = pd.read_csv(file_obj, encoding="utf-8-sig", sep=";", on_bad_lines="skip", low_memory=False)
                except:
                    # Tenta ISO-8859-1 com ponto e vírgula
                    try:
                        file_obj.seek(0)
                        df = pd.read_csv(file_obj, encoding="latin1", sep=";", on_bad_lines="skip", low_memory=False)
                    except:
                        # Tenta separador vírgula (padrão internacional)
                        file_obj.seek(0)
                        df = pd.read_csv(file_obj, encoding="latin1", sep=",", on_bad_lines="skip", low_memory=False)

            lista_df.append(df)
            
        except Exception as e:
            logging.error(f"ERRO ao ler arquivo {uploaded_file.filename}: {e}")
            # Não retorna None imediatamente, tenta processar os outros arquivos
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
    # Recebendo arquivos (removido is_csv pois a função agora é automática)
    AVERBADOS: List[UploadFile] = File(None, alias="AVERBADOS"),
    CONCILIACAO: List[UploadFile] = File(None, alias="CONCILIACAO"),
    LIQUIDADOS: List[UploadFile] = File(None, alias="LIQUIDADOS"),
    LIMINAR: List[UploadFile] = File(None, alias="LIMINAR"),
    HISTORICO_DE_REFINS: List[UploadFile] = File(None, alias="HISTORICO_DE_REFINS"),
    CREDBASE_AKRK_E_DIG: List[UploadFile] = File(None, alias="CREDBASE_AKRK_E_DIG"),
    FUNCAO: List[UploadFile] = File(None, alias="FUNCAO"),
    ANDAMENTO: List[UploadFile] = File(None, alias="ANDAMENTO"),
):
    logging.info(f"\n--- PROCESSANDO CONVÊNIO: {convenio} ---")
    
    ValidadorClass = CONVENIO_MAP.get(convenio, CONSIGFACIL)
    CAMINHO_SAIDA = os.path.join(os.getcwd(), "output_data", convenio.replace(' ', '_').replace('.', ''))
    os.makedirs(CAMINHO_SAIDA, exist_ok=True)
    
    # Leitura Unificada (Sem precisar especificar se é CSV ou Excel)
    averbados_df = read_and_unify_files(AVERBADOS)
    conciliacao_df = read_and_unify_files(CONCILIACAO)
    liquidados_df = read_and_unify_files(LIQUIDADOS)
    liminar_df = read_and_unify_files(LIMINAR)
    historico_df = read_and_unify_files(HISTORICO_DE_REFINS)
    credbase_df = read_and_unify_files(CREDBASE_AKRK_E_DIG)
    funcao_df = read_and_unify_files(FUNCAO) # Agora aceita .xlsx ou .csv automaticamente
    andamento_df = read_and_unify_files(ANDAMENTO)

    try:
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
        logging.error(f"Erro no processamento: {e}")
        raise HTTPException(status_code=500, detail=str(e))