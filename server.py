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
from python.INSS import INSS # Importando INSS

app = FastAPI()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- LISTAS DE CONVÊNIOS ---
CONSIGFACIL_CONVENIOS = [
        "GOV. DO MARANHÃO", "GOV. PIAUI", "PREF. BAYEUX", "PREF. CAJAMAR",
        "PREF. CAMPINA GRANDE", "PREF. CAMPO GRANDE", "PREF. CUIABÁ", "PREF. DE PORTO VELHO",
        "PREF. IMPERATRIZ MA", "PREF. ITU", "PREF. JOÃO PESSOA", "PREF. JUAZEIRO DO NORTE",
        "PREF. MARABÁ", "PREF. NITERÓI", "PREF. PAÇO DO LUMIAR", "PREF. PALMAS", "PREF. RECIFE",
        "PREF. SANTA RITA", "PREF. TERESINA", "CÂMARA DE TERESÓPOLIS", "GOV. MINAS GERAIS", 
        "GOV. RIO GRANDE DO NORTE", "GOV. SANTA CATARINA"
]

CODATA_CONVENIO = ["GOV. DA PARAIBA"]

INSS_CONVENIO = ["INSS"]

# Mapeamento para classe (Usado apenas para referência inicial)
CONVENIO_MAP: dict[str, Type] = {
    **{convenio: CONSIGFACIL for convenio in CONSIGFACIL_CONVENIOS},
    **{convenio: CODATA for convenio in CODATA_CONVENIO},
    **{convenio: INSS for convenio in INSS_CONVENIO}
}

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
            logging.error(f"Erro ao ler {uploaded_file.filename}: {e}")
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
    output_path: Optional[str] = Form(None), # NOVO CAMPO RECEBIDO
    
    # Todos os campos possíveis do sistema
    AVERBADOS: List[UploadFile] = File(None, alias="AVERBADOS"),
    CONCILIACAO: List[UploadFile] = File(None, alias="CONCILIACAO"),
    LIQUIDADOS: List[UploadFile] = File(None, alias="LIQUIDADOS"),
    LIMINAR: List[UploadFile] = File(None, alias="LIMINAR"),
    HISTORICO_DE_REFINS: List[UploadFile] = File(None, alias="HISTORICO_DE_REFINS"),
    CREDBASE_AKRK_E_DIG: List[UploadFile] = File(None, alias="CREDBASE_AKRK_E_DIG"),
    FUNCAO: List[UploadFile] = File(None, alias="FUNCAO"),
    ANDAMENTO: List[UploadFile] = File(None, alias="ANDAMENTO"),
    ORBITAL: List[UploadFile] = File(None, alias="ORBITAL"), # Novo
    CASOS_CAPITAL: List[UploadFile] = File(None, alias="CASOS_CAPITAL") # Novo
):
    logging.info(f"\n--- INICIANDO VALIDAÇÃO: {convenio} ---")
    

    # --- LÓGICA DE DEFINIÇÃO DO CAMINHO ---
    if output_path and output_path.strip():
        # Se o usuário mandou um caminho, usa ele
        CAMINHO_SAIDA = output_path.strip()
    else:
        # Se não, usa o padrão 'output_data/NOME_CONVENIO'
        CAMINHO_SAIDA = os.path.join(os.getcwd(), "output_data", convenio.replace(' ', '_').replace('.', ''))
        # Cria a pasta se ela não existir
    try:
        os.makedirs(CAMINHO_SAIDA, exist_ok=True)
        logging.info(f"Arquivos serão salvos em: {CAMINHO_SAIDA}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Caminho de saída inválido ou sem permissão: {str(e)}")


    # Leitura de todos os arquivos possíveis
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

    conciliacao_df.to_excel(fr'{CAMINHO_SAIDA}\conciliacao_teste.xlsx', index=False)

    # funcao_df.to_excel(fr'{CAMINHO_SAIDA}\FUNCAO TESTE.xlsx')

    try:
        # --- LÓGICA DE INSTANCIAÇÃO PERSONALIZADA ---
        
        if convenio in CODATA_CONVENIO:
            # INSTANCIAÇÃO CODATA (Gov. Paraíba)
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
                orbital=orbital_df # CODATA usa orbital
            )

        elif convenio in INSS_CONVENIO:
            # INSTANCIAÇÃO INSS
            logging.info("Usando validador: INSS")
            validador = INSS(
                portal_file_list=averbados_df,
                funcao=funcao_df,
                conciliacao=conciliacao_df,
                liquidados=liquidados_df,
                caminho=CAMINHO_SAIDA,
                tutela=liminar_df,
                orbital=orbital_df, # INSS usa orbital
                casos_capital=casoscapital_df # INSS usa casos_capital
            )

        else:
            # INSTANCIAÇÃO CONSIGFACIL (Padrão para o restante)
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

        return {"message": "Sucesso", "output_path": CAMINHO_SAIDA}

    except Exception as e:
        logging.error(f"FALHA NO PROCESSAMENTO: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")