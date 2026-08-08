from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.staticfiles import StaticFiles # <--- Importante
from fastapi.responses import FileResponse, HTMLResponse # <--- Importante
from fastapi.middleware.cors import CORSMiddleware
from flask import Flask, render_template, send_from_directory, jsonify
from fastapi import Request
from fastapi.responses import JSONResponse
from gemini_service import explicar_erro
import shutil
import gc
import os
import openpyxl
import xlrd
import pandas as pd
import logging
import io
import traceback
from time import sleep
import re
from typing import List, Optional
import uvicorn
import shutil

# Importa as classes de validação
from python.Consigfacil import CONSIGFACIL 
from python.Codata import CODATA
from python.INSS import INSS
from python.Serha import SERHA
from python.Consiglog import CONSIGLOG
from python.Neoconsig import NEOCONSIG
from python.ConsigiKonexia import CONSIGI_KONEXIA
from python.IgeprevGovTo_Preliminar import IGEPREV_GOVTO
from python.Zetra import ZETRA
from python.Infoconsig import INFOCONSIG
from python.Rf1 import RF1
from python.Sigrh import SIGRH
from python.Cip import CIP
from python.Quantum import QUANTUM
from python.Safeconsig import SAFECONSIG
from python.Lineconsig import LINECONSIG

app = FastAPI()
# Mude para False quando subir para produção
MODO_DESENVOLVIMENTO = True 

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_traceback = traceback.format_exc()
    erro_sanitizado = sanitizar_traceback(error_traceback)
    
    # --- TRAVA DE CRÉDITOS ---
    if MODO_DESENVOLVIMENTO:
        explicacao_amigavel = "MODO DEV ATIVO: O Gemini não foi chamado para economizar créditos. Verifique o console do VS Code."
        logging.info("Gemini bypassado - Modo Desenvolvimento ativo.")
    else:
        # Só chama o Gemini se não estiver em desenvolvimento
        explicacao_amigavel = explicar_erro(erro_sanitizado)
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": erro_sanitizado,
            "mensagem_amigavel": explicacao_amigavel,
            "tipo": type(exc).__name__
        }
    )

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

CONSIGLOG_CONVENIO = ["GOV. BAHIA", "PREF. ARAGUAÍNA", "PREF. DUQUE DE CAXIAS", "PREF. DUQUE DE CAXIAS - COTAR", "PREF. DUQUE DE CAXIAS - IMPDC", "PREF. GOIÂNIA", 
                      "PREVIDÊNCIA SÃO GONÇALO", "PREF. RIBEIRÃO PRETO", "PREF. TABOÃO DA SERRA", "PREVIDÊNCIA SANTOS - IPREV"]

ZETRA_CONVENIO = ["GOV. ESPÍRITO SANTO", "GOV. PARANÁ", "GOV. RIO DE JANEIRO", "IGEPREV", "PREF. BELO HORIZONTE", "PREF. AÇAILÂNDIA", 
                  "PREF. CAMPINAS", "PREF. MACAÉ", "PREF. SÃO JOSE DE RIBAMAR", "PREF. SÃO PAULO-HMSP", "PREF. SOBRAL", "PREVIPALMAS",
                  "PREF. BARBACENA", "GOV. ALAGOAS - TJAL"
                ]

RF1_CONVENIO = ["PREF. ANANINDEUA"]

INFOCONSIG_CONVENIO = ["PREF. ÁGUAS LINDAS DE GOIÁS", "PREF. PIRACICABA", "PREF. FLORIANÓPOLIS",
                        "SEMAE - SERVIÇO MUNICIPAL DE ÁGUA E ESGOTO DE PIRACICABA", "PREV. PIRACICABA IPASP",
                                 ]

TO_IGEPREV_CONVENIO = ["GOV. TOCANTINS e IGEPREV"]

SIGRH_CONVENIO = ["GOV. SANTA CATARINA"]

CONSIGI_KONEXIA_CONVENIO = ["PREF. CONTAGEM", "PREF. PLANALTINA"]

CIP_CONVENIO = ["PREF. SÃO PAULO", "GOV. SÃO PAULO"]

NEOCONSIG_CONVENIO = ["GOV. GOIÁS", "PREF. SÃO GONÇALO", "PREF. SÃO LUÍS", "PREF. SOROCABA"]

QUANTUM_CONVENIO = ["PREF. SÃO JOSÉ DO RIO PRETO", "PREVIDÊNCIA SÃO JOSÉ DO RIO PRETO", "CÂMARA MUNICIPAL DE TERESÓPOLIS", "PREF. JUÍZ DE FORA", "PREF. RIO DE JANEIRO"]

LINECONSIG_CONVENIO = ["PREF. PICOS", "PREV. PICOS"]

SAFECONSIG_CONVENIO = ["PREF. TAUBATÉ", "PREF. SANTOS", "GOV. CEARÁ", "GOV. ALAGOAS"]

# Todos os outros são Consigfacil
CONSIGFACIL_CONVENIOS = [
    "GOV. MARANHÃO", "GOV. MATO GROSSO", "GOV. PIAUÍ", "GOV. PERNAMBUCO","PREF. BAYEUX", "PREF. CAJAMAR",
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
    aba_recusas = None

    for nome in todas_as_abas:
        # Lógica para a aba de Linhas
        # Aqui verificamos se tem 'Linhas' no nome e se NÃO tem outros termos indesejados
        if "Linhas" in nome and "Suspensas" not in nome:
            aba_linhas = nome
        
        # Lógica para a aba de Descontos Parciais
        if "Desc. Parciais" in nome:
            aba_parciais = nome

        if "Recusas" in nome:
            aba_recusas = nome

        if  aba_linhas is not None and aba_parciais is not None and aba_recusas is not None:
            return aba_linhas, aba_parciais, aba_recusas
        else:
            continue


# --- Função Auxiliar de Leitura ---
async def read_and_unify_files(file_list: List[UploadFile], convenio=None):
    conv = convenio

    if not file_list:
        return None, []
    print(file_list)
    lista_df = []
    erros = []
    for uploaded_file in file_list:
        try:
            filename = uploaded_file.filename.lower()
            print(f'nome do arquivo: {filename}')
            print(f'Convenio: {conv}')
            
            # 1. Pegar o cabeçalho Content-Disposition
            content_disposition = uploaded_file.headers.get("content-disposition", "")
            match = re.search('name="([^"]+)"', content_disposition)
            # Se encontrar o 'name', armazena, senão usa o filename como reserva
            name = match.group(1).lower() if match else "desconhecido"
            print(f'Nome informal: {name}')
            content = await uploaded_file.read()
            file_obj = io.BytesIO(content)
            logging.info(f"Lendo: {uploaded_file.filename}")
            
            
            if "kobraki" in filename and filename.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_obj, sheet_name='CONSOLIDADO')
            elif "extrajudicial" in filename and filename.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_obj, sheet_name='CONSOLIDADO')
            elif "d8_to" in name:
                d8_gov_to_amostra = pd.ExcelFile(file_obj)
                planilha_linhas, planilha_parciais, planilha_recusas = abas(d8_gov_to_amostra)
                df_d8_linhas = pd.read_excel(file_obj, header=7, sheet_name=planilha_linhas)

                print(f'HEAD de d8_to: {df_d8_linhas.head()}')

                # DataFrame criado para a ideia de remover as parcelas de d8 que não estão sendo descontadas da aba recusados, e
                # usar os valores que sobraram dos descontos que foram descontados parcialmente 
                df_d8_recusas = pd.read_excel(file_obj, header=7, sheet_name=planilha_recusas)

                df_d8_parciais = pd.read_excel(file_obj, header=7, sheet_name=planilha_parciais)
                df_d8_parciais.rename(columns={'R$ PARCELA DESCONTADA': 'R$ PARCELA'}, inplace=True)
                mapeamento_d8 = ["ORDEM", "REFERENCIA", "CPF", "MATRICULA", "NOME", "RUBRICA", "PARCELA", "ADF", "R$ PARCELA"]
                df_d8_parciais_completo = df_d8_parciais[mapeamento_d8]


                # df = pd.concat([df_d8_linhas, df_d8_parciais_completo], ignore_index=True)
                print(f'Colunas de df_d8_recusas: {df_d8_recusas.columns}')
                df = df_d8_recusas
            elif "d8" in name and convenio == 'INSS':
                df = pd.read_excel(file_obj, "Refinado")

            elif "averbados" in name and convenio in ['PREF. SÃO PAULO', 'GOV. SÃO PAULO']:
                df = pd.read_excel(file_obj, header=3)
            elif "averbados" in name and convenio in ['GOV. CEARÁ', 'GOV. ALAGOAS', 'PREF. TAUBATÉ', 'PREF. SANTOS']:
                df = pd.read_excel(file_obj, header=1)
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
            elif conv in ZETRA_CONVENIO and 'averbados' in name:
                df_temp = pd.read_csv(file_obj, sep=';', encoding='latin1')
                if len(df_temp) > 3:
                    df = df_temp.iloc[:-3]

            elif conv in INFOCONSIG_CONVENIO and 'averbados' in name:
                df = pd.read_csv(
                        file_obj, 
                        sep=';', 
                        encoding='latin1', 
                        header=None, # Lemos sem cabeçalho para ele não se confundir
                        names=range(25), # Forçamos a leitura de várias colunas (ajuste o número se precisar)
                        on_bad_lines='skip' 
                    )
            elif "andamento" in name and conv == 'GOV. PARAÍBA':
                df_andamento = pd.read_excel(file_obj)
                df = df_andamento[:-3]
            elif "orbital" in name:
                df = pd.read_excel(file_obj, header=3)
                # print(f'Cabeçalho de orbital:\n{df.head(3)}')
            elif filename.endswith(('.xlsx', '.xls')):
                try:
                    # 1. Tentativa padrão como Excel verdadeiro
                    df = pd.read_excel(file_obj) 
                except Exception as e:
                    if "Excel file format cannot be determined" in str(e):
                        print(f"Caiu no tratamento de HTML disfarçado para: {filename}")
                        try:
                            # CORREÇÃO 1: Reseta o ponteiro antes de tentar ler como HTML
                            file_obj.seek(0)
                            lista_tabelas_html = pd.read_html(file_obj)
                            
                            # CORREÇÃO 2: Pega o primeiro DataFrame da lista retornada
                            if lista_tabelas_html:
                                df = lista_tabelas_html[0]
                            else:
                                raise ValueError("Nenhuma tabela encontrada dentro do arquivo HTML.")
                                
                            print(f"Sucesso ao ler HTML de: {filename}")
                           
                        except Exception as erro_html:
                            print(f'Falhou no read_html também. Erro original: {erro_html}')
                            print(f'Indo para o fluxo de segurança (CSV): {filename}')
                            
                            if hasattr(file_obj, 'seek'): file_obj.seek(0)
                            try:
                                df = pd.read_csv(file_obj, encoding="utf-8-sig", sep=";", on_bad_lines="skip", low_memory=False)
                            except Exception:
                                file_obj.seek(0) # Garante o reset antes do fallback final do CSV
                                df = pd.read_csv(file_obj, encoding="latin1", sep=";", on_bad_lines="skip", low_memory=False)
            else:
                print(f'Caiu no else')
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

            logging.exception(
                f"Erro ao ler {uploaded_file.filename}"
            )

            erros.append({
                "arquivo": uploaded_file.filename,
                "tipo": type(e).__name__,
                "mensagem": str(e)
            })
            continue
    
    if not lista_df:
        return None, []
    # return pd.concat(lista_df, ignore_index=True)
    return pd.concat(lista_df, ignore_index=True), erros

@app.get("/test")
def test_endpoint():
    return {"message": "Servidor Online"}

def sanitizar_traceback(tb):

    # Remove caminhos do Windows
    tb = re.sub(r"[A-Z]:\\\\[^\\n]+", "[CAMINHO_REMOVIDO]", tb)

    # Remove CPF
    tb = re.sub(r"\\b\\d{3}\\.\\d{3}\\.\\d{3}-\\d{2}\\b", "[CPF]", tb)

    # Remove tokens
    tb = re.sub(r"token\\s*=\\s*['\\\"].+?['\\\"]", "token=[REMOVIDO]", tb)

    # Remove emails
    tb = re.sub(r"[\\w\\.-]+@[\\w\\.-]+", "[EMAIL]", tb)

    return tb
    

@app.post("/validar")
async def validar_planilhas(
    convenio: str = Form(...),
    consignataria: Optional[str] = Form(None),
    rubrica: Optional[str] = Form(None),
    output_path: Optional[str] = Form(None),
    
    # Todos os campos possíveis do sistema
    # NÃO PODE TER ESPAÇO NOS NOMES EM ALIAS, PRECISA COLOCAR ALGUM SEPARADOR COMO _ OU - OU TUDO JUNTO
    AVERBADOS: List[UploadFile] = File(None, alias="AVERBADOS"),
    AVERBADOS_SC_CAPITAL: List[UploadFile] = File(None, alias="AVERBADOS_SC_CAPITAL"),
    AVERBADOS_SC_CLICK: List[UploadFile] = File(None, alias="AVERBADOS_SC_CLICK"),
    AVERBADOS_TO: List[UploadFile] = File(None, alias="AVERBADOS_TO"),
    AVERBADOS_IGEPREV: List[UploadFile] = File(None, alias="AVERBADOS_IGEPREV"),
    ZIPS: List[UploadFile] = File(None, alias="ZIPS"),
    CONCILIACAO: List[UploadFile] = File(None, alias="CONCILIACAO"),
    KOBRAKI: List[UploadFile] = File(None, alias="KOBRAKI"),
    EXTRA_JUDICIAL: List[UploadFile] = File(None, alias="EXTRA_JUDICIAL"),
    TACS: List[UploadFile] = File(None, alias="TACS"),
    D8_TO: List[UploadFile] = File(None, alias="D8_TO"),
    D8_IGEPREV: List[UploadFile] = File(None, alias="D8_IGEPREV"),
    LIQUIDADOS: List[UploadFile] = File(None, alias="LIQUIDADOS"),
    LIMINAR: List[UploadFile] = File(None, alias="LIMINAR"),
    HISTORICO: List[UploadFile] = File(None, alias="HISTORICO"),
    CREDBASE: List[UploadFile] = File(None, alias="CREDBASE"),
    FRONT: List[UploadFile] = File(None, alias="FRONT"),
    FUNCAO: List[UploadFile] = File(None, alias="FUNCAO"),
    XAO: List[UploadFile] = File(None, alias="XAO"),
    ANDAMENTO: List[UploadFile] = File(None, alias="ANDAMENTO"),
    ANDAMENTO_SC_CAPITAL: List[UploadFile] = File(None, alias="ANDAMENTO_SC_CAPITAL"),
    ANDAMENTO_SC_CLICK: List[UploadFile] = File(None, alias="ANDAMENTO_SC_CLICK"),
    TRABALHADO_ANTERIOR: List[UploadFile] = File(None, alias="TRABALHADO_ANTERIOR"),
    ORBITAL: List[UploadFile] = File(None, alias="ORBITAL"),
    COMPLEMENTAR: List[UploadFile] = File(None, alias="COMPLEMENTAR"),
    CASOS_CAPITAL: List[UploadFile] = File(None, alias="CASOS_CAPITAL"),
    D8: List[UploadFile] = File(None, alias="D8"),
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
        raise HTTPException(status_code=500, detail=f"Erro ao criar pasta de saída:\n{e}")
    
    # 2. Leitura dos arquivos
    averbados_df, erros = await read_and_unify_files(AVERBADOS, convenio=convenio)
    averbados_sc_capital_df, errors = await read_and_unify_files(AVERBADOS_SC_CAPITAL, convenio=convenio)
    averbados_sc_click_df, errors = await read_and_unify_files(AVERBADOS_SC_CLICK, convenio=convenio)
    averbados_to_df, erros = await read_and_unify_files(AVERBADOS_TO, convenio=convenio)
    averbados_igeprev_df, erros = await read_and_unify_files(AVERBADOS_IGEPREV, convenio=convenio)
    conciliacao_df, erros = await read_and_unify_files(CONCILIACAO, convenio=convenio)
    kobraki_df, erros = await read_and_unify_files(KOBRAKI, convenio=convenio)
    extra_judicial_df, errors = await read_and_unify_files(EXTRA_JUDICIAL, convenio=convenio)
    tacs_df, erros = await read_and_unify_files(TACS, convenio=convenio)
    d8_df_to, erros = await read_and_unify_files(D8_TO, convenio=convenio)
    d8_df_igeprev, erros = await read_and_unify_files(D8_IGEPREV, convenio=convenio)
    liquidados_df, erros = await read_and_unify_files(LIQUIDADOS, convenio=convenio)
    liminar_df, erros = await read_and_unify_files(LIMINAR, convenio=convenio)
    historico_df, erros = await read_and_unify_files(HISTORICO, convenio=convenio)
    credbase_df, erros = await read_and_unify_files(CREDBASE, convenio=convenio)
    front_df, erros = await read_and_unify_files(FRONT, convenio=convenio)
    funcao_df, erros = await read_and_unify_files(FUNCAO, convenio=convenio)
    xao_df, errors = await read_and_unify_files(XAO, convenio=convenio)
    andamento_df, erros = await read_and_unify_files(ANDAMENTO, convenio=convenio)
    and_sc_capital_df, erros = await read_and_unify_files(ANDAMENTO_SC_CAPITAL, convenio=convenio)
    and_sc_click_df, erros = await read_and_unify_files(ANDAMENTO_SC_CLICK, convenio=convenio)
    trabalhado_anterior_df, erros = await read_and_unify_files(TRABALHADO_ANTERIOR, convenio=convenio)
    orbital_df, erros = await read_and_unify_files(ORBITAL, convenio=convenio)
    complementar_df, erros = await read_and_unify_files(COMPLEMENTAR, convenio=convenio)
    casoscapital_df, erros = await read_and_unify_files(CASOS_CAPITAL, convenio=convenio)
    d8_df, erros = await read_and_unify_files(D8, convenio=convenio)

    # 3. SELEÇÃO DO VALIDADOR (SEM A VARIÁVEL PROBLEMÁTICA)
    
    if convenio in CODATA_CONVENIO:
        logging.info("Usando validador: CODATA")
        validador = CODATA(
            portal_file_list=averbados_df,
            convenio=convenio,
            front = front_df,
            andamento_funcao=xao_df,
            funcao=funcao_df,
            consignataria=consignataria, 
            conciliacao=conciliacao_df,
            kobraki=kobraki_df,
            extra_judicial=extra_judicial_df,
            tacs=tacs_df,
            andamento_list=andamento_df,
            orbital=orbital_df,
            caminho=CAMINHO_SAIDA
        )

    elif convenio in INSS_CONVENIO:
        logging.info("Usando validador: INSS")
        validador = INSS(
            portal_file_list=averbados_df,
            front=front_df,
            funcao=funcao_df,
            conciliacao=conciliacao_df,
            kobraki=kobraki_df,
            extra_judicial=extra_judicial_df,
            tacs=tacs_df,
            caminho=CAMINHO_SAIDA,
            casos_capital=casoscapital_df,
            orbital=orbital_df,
            d8=d8_df
        )
    elif convenio in SERHA_CONVENIO:
        logging.info("Usando validador: SERHA")
        validador = SERHA(
            portal_file_list=averbados_df,
            convenio=convenio,
            front=front_df,
            conciliacao=conciliacao_df,
            kobraki=kobraki_df,
            extra_judicial=extra_judicial_df,
            tacs=tacs_df,
            funcao=funcao_df,
            andamento_funcao = xao_df,
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
            extra_judicial=extra_judicial_df,
            andamento_funcao=xao_df,
            funcao=funcao_df,
            tacs=tacs_df,
            caminho=CAMINHO_SAIDA,
            orbital=orbital_df
        )
    elif convenio in CONSIGI_KONEXIA_CONVENIO:
        logging.info("Usando validador: CONSIGI_KONEXIA")
        validador = CONSIGI_KONEXIA(
            portal_file_list=averbados_df, 
            convenio=convenio,
            front=front_df,
            consignataria=consignataria,
            conciliacao=conciliacao_df,
            kobraki=kobraki_df,
            extra_judicial=extra_judicial_df,
            tacs=tacs_df,
            caminho=CAMINHO_SAIDA,
            andamento_funcao=xao_df,
            funcao=funcao_df,
            orbital=orbital_df
        )
    elif convenio in INFOCONSIG_CONVENIO:
        logging.info("Usando validador: INFOCONSIG")
        validador = INFOCONSIG(
            portal_file_list=averbados_df, 
            convenio=convenio,
            front=front_df,
            consignataria=consignataria,
            conciliacao=conciliacao_df,
            kobraki=kobraki_df,
            extra_judicial=extra_judicial_df,
            tacs=tacs_df,
            caminho=CAMINHO_SAIDA,
            rubrica=rubrica,
            andamento_funcao=xao_df,
            funcao=funcao_df,
            orbital=orbital_df
        )
    elif convenio in ZETRA_CONVENIO:
        logging.info("Usando o validador: ZETRA")
        validador = ZETRA(
            portal_file_path=averbados_df,
            convenio=convenio,
            front=front_df,
            funcao=funcao_df,
            andamento_funcao=xao_df,
            conciliacao=conciliacao_df,
            kobraki=kobraki_df,
            extra_judicial=extra_judicial_df,
            tacs=tacs_df,
            consignataria=consignataria,
            caminho=CAMINHO_SAIDA,
            historico=historico_df,
            orbital=orbital_df
        )
    elif convenio in RF1_CONVENIO:
        logging.info("Usando o validador: RF1")
        validador = RF1(
            front=front_df,
            portal_file_list=averbados_df,
            convenio=convenio,
            caminho=CAMINHO_SAIDA,
            andamento_funcao=xao_df,
            funcao=funcao_df,
            conciliacao=conciliacao_df,
            tacs=tacs_df,
            extra_judicial=extra_judicial_df,
            kobraki=kobraki_df
        )
    elif convenio in CIP_CONVENIO:
        logging.info("Usando o validador: CIP")
        validador = CIP(
            front=front_df,
            portal_file_list=averbados_df,
            convenio=convenio,
            caminho=CAMINHO_SAIDA,
            funcao=funcao_df,
            conciliacao=conciliacao_df,
            tacs=tacs_df,
            kobraki=kobraki_df,
            extra_judicial=extra_judicial_df,
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
            extra_judicial=extra_judicial_df,
            tacs=tacs_df,
            caminho=CAMINHO_SAIDA
        )
    elif convenio in SIGRH_CONVENIO:
        logging.info("Usando o validador: SIGRH")
        validador = SIGRH(front=front_df,
                          averbado_capital=averbados_sc_capital_df,
                          averbado_click=averbados_sc_click_df,
                          andamento_capital=and_sc_capital_df,
                          andamento_click=and_sc_click_df,
                          convenio=convenio,
                          consignataria=consignataria,
                          caminho=CAMINHO_SAIDA,
                          funcao=funcao_df,
                          orbital=orbital_df,
                          conciliacao=conciliacao_df,
                          kobraki=kobraki_df,
                          extra_judicial=extra_judicial_df,
                          tacs=tacs_df)
        
    elif convenio in NEOCONSIG_CONVENIO:
        logging.info("Usando validador: NEOCONSIG")
        validador = NEOCONSIG(
            portal_file_list=averbados_df, 
            convenio=convenio,
            front=front_df,
            consignataria=consignataria,
            conciliacao=conciliacao_df,
            kobraki=kobraki_df,
            extra_judicial=extra_judicial_df,
            andamento_funcao=xao_df,
            funcao=funcao_df,
            tacs=tacs_df,
            caminho=CAMINHO_SAIDA,
            orbital=orbital_df
        )
    elif convenio in QUANTUM_CONVENIO:
        logging.info("Usando validador: QUANTUM")
        validador = QUANTUM(
            portal_file_list=averbados_df, 
            convenio=convenio,
            front=front_df,
            consignataria=consignataria,
            conciliacao=conciliacao_df,
            kobraki=kobraki_df,
            extra_judicial=extra_judicial_df,
            tacs=tacs_df,
            caminho=CAMINHO_SAIDA,
            andamento_funcao=xao_df,
            funcao=funcao_df,
            orbital=orbital_df
        )

    elif convenio in SAFECONSIG_CONVENIO:
        # Padrão para todos os outros (Consigfacil)
        logging.info("Usando validador: SAFECONSIG")
        validador = SAFECONSIG(
            portal_file_list=averbados_df, 
            convenio=convenio,
            front=front_df,
            andamento_funcao=xao_df,
            funcao=funcao_df,
            conciliacao=conciliacao_df,
            orbital=orbital_df,
            tacs=tacs_df,
            kobraki=kobraki_df,
            extra_judicial=extra_judicial_df,
            caminho=CAMINHO_SAIDA,
        )
    elif convenio in LINECONSIG_CONVENIO:
            logging.info("Usando validador: LINECONSIGIT")
            validador = LINECONSIG(
                portal_file_list=averbados_df, 
                convenio=convenio,
                front=front_df,
                consignataria=consignataria,
                conciliacao=conciliacao_df,
                kobraki=kobraki_df,
                extra_judicial=extra_judicial_df,
                tacs=tacs_df,
                caminho=CAMINHO_SAIDA,
                andamento_funcao=xao_df,
                funcao=funcao_df,
                orbital=orbital_df
            )

    elif convenio in CONSIGFACIL_CONVENIOS:
        # Padrão para todos os outros (Consigfacil)
        logging.info("Usando validador: CONSIGFACIL")
        validador = CONSIGFACIL(
            portal_file_list=averbados_df, 
            convenio=convenio,
            front=front_df,
            andamento_funcao=xao_df,
            funcao=funcao_df,
            conciliacao=conciliacao_df,
            orbital=orbital_df,
            tacs=tacs_df,
            kobraki=kobraki_df,
            extra_judicial=extra_judicial_df,
            andamento_list=andamento_df,
            caminho=CAMINHO_SAIDA,
        )
    else:
        raise Exception ('O convênio selecionado está fora dos parâmetros.')
    

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
    # Pega a porta do Render ou usa 8000 se estiver local
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)