from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
import logging

load_dotenv()

client = genai.Client(
    api_key = os.getenv("GEMINI_API_KEY")
)

# No seu arquivo do Gemini
def explicar_erro(traceback_limpo):
    try:
        prompt = f"""
        Explique este erro técnico para um usuário comum que está validando planilhas de consignado.
        Regras:
        - Seja breve e direto.
        - Não use termos técnicos complexos.
        - Se o erro for de 'coluna não encontrada', diga qual coluna falta.
        - Sugira uma solução simples.

        Erro:
        {traceback_limpo}
        """
        response = client.models.generate_content(
            model="gemini-2.5-flash", # Ajuste para a versão que você possui acesso
            contents=prompt
        )
        return response.text
    except Exception as e:
        print(f'Erro gemini: {e}')
        return "Ocorreu um erro inesperado no processamento. Por favor, tente novamente ou contate o suporte."

