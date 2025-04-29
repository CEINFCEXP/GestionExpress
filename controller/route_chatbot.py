from fastapi import APIRouter, Request, Query
from starlette.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from model.agente_IA import AgenteIA

chatbot_router = APIRouter()
templates = Jinja2Templates(directory="./view")

# Función para obtener la sesión del usuario
def get_user_session(req: Request):
    return req.session.get('user')

# Endpoint para obtener respuesta del modelo IA
@chatbot_router.get("/ask_ia", response_class=JSONResponse)
async def preguntar_a_ia(request: Request, question: str = Query(...)):
    user_session = get_user_session(request) or {}
    nombre = f"{user_session.get('nombres', 'Invitado')} {user_session.get('apellidos', '')}".strip()
    
    if not question:
        return JSONResponse(content={"answer": "❌ Pregunta vacía. Por favor escribe algo."}, status_code=400)

    agente = AgenteIA(nombre_usuario=nombre)
    respuesta = agente.responder(question)
    return {"answer": respuesta}

