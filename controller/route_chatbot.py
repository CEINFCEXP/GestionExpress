from fastapi import APIRouter, Request, Query
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from model.agente_IA import AgenteIA
import os, io

chatbot_router = APIRouter()
templates = Jinja2Templates(directory="./view")

# Función para obtener la sesión del usuario
def get_user_session(req: Request):
    return req.session.get('user')

# Pregunta y guarda historial en sesión
@chatbot_router.get("/ask_ia", response_class=JSONResponse)
async def preguntar_a_ia(request: Request, question: str = Query(...)):
    user_session = get_user_session(request) or {}
    nombre = f"{user_session.get('nombres', 'Invitado')} {user_session.get('apellidos', '')}".strip()

    # Inicializa historial si no existe
    if "historial_chat" not in request.session:
        request.session["historial_chat"] = [
            f"=============================\n🗓️ Inicio de sesión: {nombre}\n=============================\n"
        ]

    agente = AgenteIA(nombre_usuario=nombre)
    respuesta = agente.responder(question)

    # Guarda entrada en sesión
    request.session["historial_chat"].append(f"\n👤 {nombre}: {question}\n🤖 Bot-CEXP: {respuesta}\n")
    return {"answer": respuesta}

# Descargar historial desde sesión
@chatbot_router.get("/descargar_historial", response_class=StreamingResponse)
async def descargar_historial(request: Request):
    user_session = get_user_session(request) or {}
    nombre = f"{user_session.get('nombres', 'Invitado')} {user_session.get('apellidos', '')}".strip()

    historial = request.session.get("historial_chat", [])
    if not historial:
        return JSONResponse(content={"error": "Historial vacío"}, status_code=404)

    contenido = "".join(historial)
    buffer = io.BytesIO(contenido.encode("utf-8"))

    return StreamingResponse(buffer, media_type="text/plain", headers={
        "Content-Disposition": f"attachment; filename=chat_bot_cexp_{nombre.replace(' ', '_').lower()}.txt"
    })