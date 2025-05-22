import google.generativeai as genai
from langchain.prompts import PromptTemplate
from datetime import datetime
from dotenv import load_dotenv
import os, re

load_dotenv()  # Carga variables desde .env

# Carga el token de IA LLM Generativa desde la variable de entorno
api_token_ia = os.getenv("IA_API_KEY")
# Si no se encuentra en el entorno, intenta cargarlo desde el archivo .env
if not api_token_ia:
    raise ValueError("❌ ERROR: No se encontró la variable IA_API_KEY en el entorno ni en .env")

# Establece el token de IA LLM en la variable de entorno
os.environ["IA_API_KEY"] = api_token_ia
genai.configure(api_key=api_token_ia)

class AgenteIA:
    def __init__(self, nombre_usuario: str):
        self.nombre_usuario = nombre_usuario.strip().title()

        # Inicializa modelo IA Generativa
        self.model = genai.GenerativeModel(model_name="gemini-1.5-flash")
        self.chat = self.model.start_chat()  # Sesión de conversación

        # Solo se guarda el prompt como plantilla (no en pipeline con chat)
        self.prompt = PromptTemplate(
            input_variables=["input", "nombre"],
            template="""Eres Bot-CEXP, asistente experto en transporte de pasajeros en Colombia. 
                        Responde profesionalmente al usuario llamado {nombre}.
                        <|user|>{input}<|end|><|assistant|>"""
        )

    def responder(self, pregunta: str) -> str:
        try:
            # Generar prompt fusionado
            prompt_text = self.prompt.format(input=pregunta, nombre=self.nombre_usuario)

            # Enviar mensaje al modelo
            response = self.chat.send_message(prompt_text, generation_config={"max_output_tokens": 256, "temperature": 0.7, "top_p": 0.9})

            respuesta_limpia = re.split(
                r"\n(Pregunta del usuario|Escribe tu respuesta|Puedes utilizar emojis|Respuesta del asistente):",
                response.text)[0].strip()
            
            return respuesta_limpia
        
        except Exception as e:
            mensaje_error = str(e)
            if "429" in mensaje_error or "quota" in mensaje_error.lower() or "rate" in mensaje_error.lower():
                return f"😓 {self.nombre_usuario}, en estos momentos me encuentro fuera de servicio por límite de uso. Por favor intenta más tarde. 🤐"
            return f"⚠️ Error al generar respuesta: {mensaje_error}"