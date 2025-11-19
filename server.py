from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import pandas as pd
import logging

from typing import List, Type
# Importa a sua classe de validação
from python.Consigfacil import CONSIGFACIL 
from python.Codata import CODATA

# Crie aqui uma importação para sua próxima classe quando ela for feita, ex:
# from python.OutroValidador import OUTRO_VALIDADOR 

app = FastAPI()

# ----------------------------------------------------------------------
# Configuração de CORS (Essencial para o navegador se comunicar com a API)
# ----------------------------------------------------------------------
# server.py (Substituir o bloco de add_middleware)

# Lista de origens permitidas (inclui o Live Server e o local host)
origins = [
    "*", # Permite todas (ideal para desenvolvimento)
    "http://localhost:5500", # Live Server (porta padrão)
    "http://127.0.0.1:5500", # Live Server (IP explícito)
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, # Usa a lista com a porta 5500
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ----------------------------------------------------------------------
# MAPEAMENTO DE CONVÊNIOS PARA CLASSES DE VALIDAÇÃO (DISPATCH)
# ----------------------------------------------------------------------

# Defina quais convênios a classe CONSIGFACIL trata.
# Esta lista deve ser EXATAMENTE igual aos nomes no seu dropdown do HTML.

CONSIGFACIL_CONVENIOS = [
        "GOV. DO MARANHÃO", "GOV. PIAUI", "PREF. BAYEUX", "PREF. CAJAMAR",
        "PREF. CAMPINA GRANDE", "PREF. CAMPO GRANDE", "PREF. CUIABÁ", "PREF. DE PORTO VELHO",
        "PREF. IMPERATRIZ MA", "PREF. ITU", "PREF. JOÃO PESSOA", "PREF. JUAZEIRO DO NORTE",
        "PREF. MARABÁ", "PREF. NITERÓI", "PREF. PAÇO DO LUMIAR", "PREF. PALMAS", "PREF. RECIFE",
        "PREF. SANTA RITA", "PREF. TERESINA"
]

CODATA_CONVENIO = [ 
        "GOV. DA PARAIBA"
]

# Dicionário de despacho: Mapeia o nome do convênio para a CLASSE Python.
CONVENIO_MAP: dict[str, Type] = {
    **{convenio: CONSIGFACIL for convenio in CONSIGFACIL_CONVENIOS},
    **{convenio: CODATA for convenio in CODATA_CONVENIO}
}


# ----------------------------------------------------------------------
# Função Auxiliar para Ler Arquivos e Unificar (FEITA PELO FASTAPI)
# ----------------------------------------------------------------------

# server.py (Função Auxiliar read_and_unify_files)

def read_and_unify_files(file_list: List[UploadFile], is_csv: bool = False):
    """Lê e unifica uma lista de UploadFile, retornando um único DataFrame ou None."""
    if not file_list:
        return None

    lista_df = []
    
    for uploaded_file in file_list:
        try:
            uploaded_file.file.seek(0) 
            
            if is_csv:
                # Lógica de leitura de CSV com tratamento de codificação
                try:
                    df = pd.read_csv(uploaded_file.file, encoding="utf-8-sig", sep=";", on_bad_lines="skip", low_memory=False)
                except UnicodeDecodeError:
                    uploaded_file.file.seek(0)
                    df = pd.read_csv(uploaded_file.file, encoding="ISO-8859-1", sep=";", on_bad_lines="skip", low_memory=False)
                except:
                    uploaded_file.file.seek(0)
                    # Tenta ISO-8859-1 com separador ',' (vírgula)
                    df = pd.read_csv(uploaded_file.file, encoding="ISO-8859-1", sep=",", on_bad_lines="skip", low_memory=False)
            
            else:
                # Lógica de leitura de Excel
                df = pd.read_excel(uploaded_file.file)
            
            lista_df.append(df)
            
        except Exception as e:
            # CORREÇÃO: Removemos o raise HTTPException. 
            # O erro é registrado, e a função retorna None.
            logging.info(f"ERRO CRÍTICO ao processar o arquivo {uploaded_file.filename}. O processamento de arquivos parou: {e}")
            return None # Retorna None para interromper o processamento desta lista.

    return pd.concat(lista_df, ignore_index=True)


# ----------------------------------------------------------------------
# Rota Principal da API
# ----------------------------------------------------------------------
@app.get("/test")
def test_endpoint():
    logging.info("\n--- TESTE BÁSICO BEM-SUCEDIDO: TERMINAL FUNCIONANDO ---")
    return {"message": "Servidor OK! O terminal deve ter exibido uma mensagem."}

@app.post("/validar")
async def validar_planilhas(
    convenio: str = Form(...),
    # Arquivos UploadFile (recebidos do seu app.js)
    AVERBADOS: List[UploadFile] = File(None, alias="AVERBADOS"),
    CONCILIACAO: List[UploadFile] = File(None, alias="CONCILIACAO"),
    LIQUIDADOS: List[UploadFile] = File(None, alias="LIQUIDADOS"),
    LIMINAR: List[UploadFile] = File(None, alias="LIMINAR"),
    HISTORICO_DE_REFINS: List[UploadFile] = File(None, alias="HISTORICO_DE_REFINS"),
    CREDBASE_AKRK_E_DIG: List[UploadFile] = File(None, alias="CREDBASE_AKRK_E_DIG"),
    FUNCAO: List[UploadFile] = File(None, alias="FUNCAO"),
    ANDAMENTO: List[UploadFile] = File(None, alias="ANDAMENTO"),
):
    # NOVO: logging.info inicial para confirmar o recebimento e qual convênio está sendo usado
    logging.info(f"\n--- REQUISIÇÃO RECEBIDA PARA O CONVÊNIO: {convenio} ---")
    # 1. Despacho Dinâmico: Encontra a classe certa
    ValidadorClass = CONVENIO_MAP.get(convenio)

    if not ValidadorClass:
        logging.info(f"ATENÇÃO: Convênio '{convenio}' NÃO ENCONTRADO no mapeamento. Usando CONSIGFACIL.")
        raise HTTPException(status_code=404, detail=f"Nenhuma classe validadora encontrada para o convênio: {convenio}")
        ValidadorClass = CONSIGFACIL

    # 2. Definir caminho de saída
# server.py (Início da função 'validar_planilhas')

    # 2. Definir caminho de saída
    CAMINHO_SAIDA = os.path.join(os.getcwd(), "output_data", convenio.replace(' ', '_').replace('.', ''))
    logging.info(f"Caminho da Pasta de Saída: {CAMINHO_SAIDA}")
    os.makedirs(CAMINHO_SAIDA, exist_ok=True)
    
    # 3. Ler e unificar os arquivos (Delegando ao FastAPI)
    
    # XLSX/XLS (is_csv=False)
    averbados_df = read_and_unify_files(AVERBADOS, is_csv=False)
    conciliacao_df = read_and_unify_files(CONCILIACAO, is_csv=False)
    liquidados_df = read_and_unify_files(LIQUIDADOS, is_csv=False)
    liminar_df = read_and_unify_files(LIMINAR, is_csv=False)
    historico_df = read_and_unify_files(HISTORICO_DE_REFINS, is_csv=False)

    # CSV (is_csv=True)
    credbase_df = read_and_unify_files(CREDBASE_AKRK_E_DIG, is_csv=True)
    funcao_df = read_and_unify_files(FUNCAO, is_csv=True)
    andamento_df = read_and_unify_files(ANDAMENTO, is_csv=True)

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
        # CORREÇÃO: Removemos as chamadas explícitas.
        # A lógica completa (tratamento_funcao -> unificacao_cred_funcao -> etc.) 
        # já é iniciada no construtor (__init__).

        return {"message": f"Validação para {convenio} concluída com sucesso.", "output_path": CAMINHO_SAIDA}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na lógica de validação do {ValidadorClass.__name__}: {e}")
    