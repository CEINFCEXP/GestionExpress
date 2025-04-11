from langchain_huggingface import HuggingFaceEndpoint
from langchain.prompts import PromptTemplate
from datetime import datetime
from dotenv import load_dotenv
import os
import re

load_dotenv()  # Carga variables desde .env

api_token_ia = os.getenv("HUGGINGFACEHUB_API_TOKEN")
# Verifica si el token de Hugging Face está presente
if not api_token_ia:
    raise ValueError("❌ ERROR: No se encontró la variable HUGGINGFACEHUB_API_TOKEN en el archivo .env")
os.environ["HUGGINGFACEHUB_API_TOKEN"] = api_token_ia

class AgenteIA:
    def __init__(self, nombre_usuario: str):
        self.nombre_usuario = nombre_usuario.strip().title()

        self.llm = HuggingFaceEndpoint(
            repo_id="meta-llama/Meta-Llama-3-8B-Instruct",
            task="text-generation",
            temperature=0.7,
            max_new_tokens=512
        )

        self.prompt = PromptTemplate(
            input_variables=["input", "nombre"],
            template="""<|system|>
Eres Bot-CEXP, un asistente especializado en temas de transporte de pasajeros en Colombia.
Responde de forma clara, estructurada y profesional. Siempre trata al usuario por su nombre ({nombre}).
Puedes ayudar con:
- Normativa del transporte público o empresarial 🚌
- Rutas, horarios y operación de transporte masivo 🕒
- Legislación vigente del Ministerio de Transporte 📜
- Seguridad vial y atención al cliente 🦺
- Documentación técnica, manuales y formatos 🗂️
<|end|>
<|user|>{input}<|end|>
<|assistant|>
"""
        )
        

        self.chain = self.prompt | self.llm
        self.historial_archivo = f"historial_chat_{self.nombre_usuario.lower().replace(' ', '_')}.txt"

        with open(self.historial_archivo, "a", encoding="utf-8") as f:
            f.write(f"\n=============================\n🗓️ Inicio de sesión: {datetime.now()}\n👤 Usuario: {self.nombre_usuario}\n=============================\n")

    def responder(self, pregunta: str) -> str:
        try:
            respuesta = self.chain.invoke({
                "input": pregunta,
                "nombre": self.nombre_usuario
            })
            respuesta_limpia = re.split(r"\n(Pregunta del usuario|Escribe tu respuesta|Puedes utilizar emojis|Respuesta del asistente):", respuesta)[0].strip()

            with open(self.historial_archivo, "a", encoding="utf-8") as f:
                f.write(f"\n👤 {self.nombre_usuario}: {pregunta}\n🤖 Bot-CEXP: {respuesta_limpia}\n")

            return respuesta_limpia
        except Exception as e:
            return f"⚠️ Error al generar respuesta: {str(e)}"
