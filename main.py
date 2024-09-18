from fastapi import FastAPI, Request, Form, Depends, File, UploadFile, HTTPException, Response
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from bs4 import BeautifulSoup 
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
from lib.verifcar_clave import check_user
from controller.user import User
from controller.cargues import ProcesarCargueControles
from model.gestionar_db import Cargue_Controles
from model.gestionar_db import Cargue_Asignaciones
from model.consultas_db import Reporte_Asignaciones
from lib.asignar_controles import fecha_asignacion, puestos_SC, puestos_UQ, concesion, control, rutas, turnos, hora_inicio, hora_fin
import psycopg2
import json
from typing import List
from io import BytesIO 
import os

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="!secret_key")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="./view")
DATABASE_PATH = "postgresql://gestionexpress:G3st10n3xpr3ss@serverdbcexp.postgres.database.azure.com:5432/gestionexpress"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Función para verificar si el usuario ha iniciado sesión
def get_user_session(req: Request):
    return req.session.get('user')

# Ruta principal
@app.get("/", response_class=HTMLResponse)
def root(req: Request, user_session: dict = Depends(get_user_session)):
    return templates.TemplateResponse("index.html", {"request": req, "user_session": user_session}, title="Centro de Control")

# Ruta Login
@app.post("/", response_class=HTMLResponse)
def login(req: Request, username: str = Form(...), password_user: str = Form(...)):
    verify, nombres, apellidos = check_user(username, password_user)  # Asegúrate de que check_user devuelva estos valores
    if verify:
        req.session['user'] = {"username": username, "nombres": nombres, "apellidos": apellidos}
        return RedirectResponse(url="/inicio", status_code=302)
    else:
        error_message = "Por favor valide sus credenciales y vuelva a intentar."
        return templates.TemplateResponse("index.html", {"request": req, "error_message": error_message})

@app.get("/inicio", response_class=HTMLResponse)
def registrarse(req: Request, user_session: dict = Depends(get_user_session)):
    if not user_session:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("inicio.html", {"request": req, "user_session": user_session})
  
# Ruta de cierre de sesión
@app.get("/logout", response_class=HTMLResponse)
async def logout(request: Request): # Limpiar cualquier estado de sesión
    request.session.clear()  # Limpia la sesión del usuario
    response = RedirectResponse(url="/", status_code=302) # Crear una respuesta de redirección
    response.delete_cookie("access_token") # Eliminar la cookie de sesión o token de acceso
    return response

@app.get("/registrarse", response_class=HTMLResponse)
def registrarse(req: Request, user_session: dict = Depends(get_user_session)):
    if not user_session:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("registrarse.html", {"request": req, "user_session": user_session})

@app.post("/registrarse", response_class=HTMLResponse)
def registrarse_post(req: Request, nombres: str = Form(...), apellidos: str = Form(...),
                     username: str = Form(...), cargo: str = Form(...),
                     password_user: str = Form(...), user_session: dict = Depends(get_user_session)):
    if not user_session:
        return RedirectResponse(url="/", status_code=302)

    data_user = {
        "nombres": nombres,
        "apellidos": apellidos,
        "username": username,
        "cargo": cargo,
        "password_user": password_user
    }
    
    user = User(data_user)
    result = user.create_user()

    if result.get("success"):
        success_message = "Usuario creado correctamente."
        return templates.TemplateResponse("registrarse.html", {"request": req, "user_session": user_session, "success_message": success_message})
    else:
        error_message = result.get("message", "Error desconocido al crear usuario.")
        return templates.TemplateResponse("registrarse.html", {"request": req, "user_session": user_session, "error_message": error_message})

@app.get("/asignacion", response_class=HTMLResponse)
def asignacion(req: Request, user_session: dict = Depends(get_user_session)):
    if not user_session:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("asignacion.html", {"request": req, "user_session": user_session})

@app.post("/asignacion", response_class=HTMLResponse)
def asignacion_post(req: Request, username: str = Form(...), password_user: str = Form(...)):
    verify = check_user(username, password_user)
    if verify:
        return templates.TemplateResponse("asignacion.html", {"request": req, "data_user": verify})
    else:
        error_message = "Por favor valide sus credenciales y vuelva a intentar."
        return templates.TemplateResponse("index.html", {"request": req, "error_message": error_message})

# Clase para manejar el request de confirmación de cargue
class ConfirmarCargueRequest(BaseModel):
    session_id: str

#########################################################################################
# FUNCIONALIDADES PARA CARGUES MASIVOS DE PLANTA Y CONTROLES "gestionar_db.py.py"
# Cargues Archivos de Planta y Parametrización de Controles
# Caché en memoria como diccionario
cache = {}

@app.post("/cargar_archivo/")
async def cargar_archivo(file: UploadFile = File(...)):
    procesador = ProcesarCargueControles(file)
    preliminar = procesador.leer_archivo()

    # Generar una clave única para el usuario/sesión (simulación de UUID)
    session_id = str(len(cache) + 1)
    cache[session_id] = preliminar

    print(f"Archivo cargado correctamente. Session ID: {session_id}")
    return {"session_id": session_id, "preliminar": preliminar}

@app.post("/confirmar_cargue/")
async def confirmar_cargue(data: dict):
    session_id = data.get("session_id")
    if session_id not in cache:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    # Obtener datos preliminares desde la caché
    preliminar = cache[session_id]

    # Filtrar datos según lo seleccionado por el usuario
    hojas_a_cargar = {}

    if data.get("tcz"):
        hojas_a_cargar['planta'] = preliminar.get('planta')

    if data.get("supervisores"):
        hojas_a_cargar['supervisores'] = preliminar.get('supervisores')

    if data.get("turnos"):
        hojas_a_cargar['turnos'] = preliminar.get('turnos')

    if data.get("controles"):
        hojas_a_cargar['controles'] = preliminar.get('controles')

    if not hojas_a_cargar:
        raise HTTPException(status_code=400, detail="Debe seleccionar al menos una hoja para cargar.")

    # Enviar las hojas seleccionadas a la base de datos
    try:
        cargador = Cargue_Controles()
        cargador.cargar_datos(hojas_a_cargar)
        return {"message": "Datos cargados exitosamente."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al cargar los datos: {str(e)}")
    
# Plantilla de cargue de planta activa y controles
@app.get("/plantilla_cargue")
async def descargar_plantilla():
    file_path = "./cargues/asignaciones_tecnicos.xlsx"
    return FileResponse(path=file_path, filename="asignaciones_tecnicos.xlsx", media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

#########################################################################################
# FUNCIONALIDADES PARA GESTIONAR LAS ASIGNACIONES "asignar_controles.py"
def get_planta_data():
    conn = psycopg2.connect("postgresql://gestionexpress:G3st10n3xpr3ss@serverdbcexp.postgres.database.azure.com:5432/gestionexpress")
    cursor = conn.cursor()
    cursor.execute("SELECT cedula, nombre FROM planta")
    rows = cursor.fetchall()
    conn.close()
    return [{"cedula": row[0], "nombre": row[1]} for row in rows]

def get_supervisores_data():
    conn = psycopg2.connect("postgresql://gestionexpress:G3st10n3xpr3ss@serverdbcexp.postgres.database.azure.com:5432/gestionexpress")
    cursor = conn.cursor()
    cursor.execute("SELECT cedula, nombre FROM supervisores")
    rows = cursor.fetchall()
    conn.close()
    return [{"cedula": row[0], "nombre": row[1]} for row in rows]

@app.get("/api/planta", response_class=JSONResponse)
def api_planta():
    data = get_planta_data()
    return data

@app.get("/api/supervisores", response_class=JSONResponse)
def api_supervisores():
    data = get_supervisores_data()
    return data

@app.get("/api/fecha_asignacion")
async def api_fecha_asignacion(fecha: str):
    return fecha_asignacion(fecha)

@app.get("/api/puestos_SC")
async def api_puestos_SC():
    return puestos_SC()

@app.get("/api/puestos_UQ")
async def api_puestos_UQ():
    return puestos_UQ()

@app.get("/api/concesion")
async def api_concesion():
    return concesion()

@app.get("/api/control")
async def get_control(concesion: str, puestos: str):
    controles = control(concesion, puestos)
    return JSONResponse(content=controles)

@app.get("/api/rutas")
async def get_rutas(concesion: str, puestos: str, control: str):
    rutas_asociadas = rutas(concesion, puestos, control)
    return {"rutas": rutas_asociadas}

@app.get("/api/turnos")
async def get_turnos():
    return turnos()

def get_turnos_data():
    conn = psycopg2.connect("postgresql://gestionexpress:G3st10n3xpr3ss@serverdbcexp.postgres.database.azure.com:5432/gestionexpress") 
    cursor = conn.cursor()
    cursor.execute("SELECT turno, hora_inicio, hora_fin, detalles FROM turnos")
    rows = cursor.fetchall()
    conn.close()
    return [{"turno": row[0], "hora_inicio": row[1], "hora_fin": row[2], "detalles": row[3]} for row in rows]

@app.get("/api/turnos", response_class=JSONResponse)
def api_turnos():
    data = get_turnos_data()
    return data

@app.get("/api/turno_descripcion")
def turno_descripcion(turno: str):
    return {"descripcion": turno_descripcion(turno)}

@app.get("/api/hora_inicio")
async def get_hora_inicio(turno: str):
    return {"inicio": hora_inicio(turno)}

@app.get("/api/hora_fin")
async def get_hora_fin(turno: str):
    return {"fin": hora_fin(turno)}

#######################################################################
# FUNCIONALIDADES PARA GUARDAR LO REGISTRADO EN LA GRILLA DE ASIGNACIÓN"
cargue_asignaciones = Cargue_Asignaciones()

class AsignacionRequest(BaseModel):
    fecha: str
    cedula: str
    nombre: str
    turno: str
    hora_inicio: str
    hora_fin: str
    concesion: str
    control: str
    rutas_asociadas: str
    observaciones: str

# Función para obtener datos del cuerpo de la solicitud y guardar las asignaciones
@app.post("/api/guardar_asignaciones")
async def guardar_asignaciones(request: Request, user_session: dict = Depends(get_user_session)):
    try:
        data = await request.json() # Obtener datos del cuerpo de la solicitud
        processed_data = cargue_asignaciones.procesar_asignaciones(data, user_session) # Procesar, cargar asignaciones y Pasar user_session
        cargue_asignaciones.cargar_asignaciones(processed_data)
        return {"message": "Asignaciones guardadas exitosamente."} # Retornar mensaje de éxito
    except Exception as e:
        error_message = f"Error al guardar asignaciones: {str(e)}" # Manejar errores y retornar mensaje de error
        raise HTTPException(status_code=500, detail=str(e))

#################################################################
# FUNCIONALIDADES DE CONSULTA Y REPORTES PARA CENTRO DE CONTROL"
# Instancia de la clase para manejar reportes
reporte_asignaciones = Reporte_Asignaciones()

# Ruta para el dashboard principal
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(req: Request, user_session: dict = Depends(get_user_session)):
    if not user_session:
        return RedirectResponse(url="/", status_code=302)
    filtros = reporte_asignaciones.obtener_filtros_unicos()
    return templates.TemplateResponse("dashboard.html", {
        "request": req,
        "user_session": user_session,
        **filtros
    })

@app.get("/filtrar_asignaciones", response_class=HTMLResponse)
async def filtrar_asignaciones(request: Request, fechaInicio: str, fechaFin: str, cedulaTecnico: str = None, nombreTecnico: str = None, turno: str = None, concesion: str = None, control: str = None, ruta: str = None, linea: str = None, cop: str = None, usuarioRegistra: str = None, nombreSupervisorEnlace: str = None):
    filtros = {
        "fecha_inicio": fechaInicio,
        "fecha_fin": fechaFin,
        "cedula": cedulaTecnico,
        "nombre": nombreTecnico,
        "turno": turno,
        "concesion": concesion,
        "control": control,
        "ruta": ruta,
        "linea": linea,
        "cop": cop,
        "registrado_por": usuarioRegistra,
        "nombre_supervisor_enlace": nombreSupervisorEnlace
    }
    
    asignaciones = reporte_asignaciones.obtener_asignaciones(**filtros)
    return templates.TemplateResponse("dashboard.html", {"request": request, "asignaciones": asignaciones, **filtros})

@app.post("/buscar_asignaciones")
async def buscar_asignaciones(request: Request):
    # Recibir los datos de los filtros desde el frontend
    filtros = await request.json()
    
    # Crear una instancia de Reporte_Asignaciones
    reporte = Reporte_Asignaciones()

    # Obtener las asignaciones utilizando los filtros
    asignaciones = reporte.obtener_asignaciones(
        fecha_inicio=filtros.get('fechaInicio'),
        fecha_fin=filtros.get('fechaFin'),
        cedula=filtros.get('cedulaTecnico'),
        nombre=filtros.get('nombreTecnico'),
        turno=filtros.get('turno'),
        concesion=filtros.get('concesion'),
        control=filtros.get('control'),
        ruta=filtros.get('ruta'),
        linea=filtros.get('linea'),
        cop=filtros.get('cop'),
        registrado_por=filtros.get('usuarioRegistra'),
        nombre_supervisor_enlace=filtros.get('nombreSupervisorEnlace')
    )
    # Depuración para verificar la salida
    print(asignaciones)
    # Devolver las asignaciones como JSON para que el frontend las maneje
    return JSONResponse(content=asignaciones)

@app.post("/descargar_xlsx")
async def descargar_xlsx(request: Request):
    filtros = await request.json()
    
    reporte = Reporte_Asignaciones()
    xlsx_file = reporte.generar_xlsx(filtros)
    
    # Usar StreamingResponse para devolver el archivo
    headers = {
        'Content-Disposition': 'attachment; filename="asignaciones.xlsx"'
    }
    return StreamingResponse(xlsx_file, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)

@app.post("/descargar_csv")
async def descargar_csv(request: Request):
    filtros = await request.json()
    
    reporte = Reporte_Asignaciones()
    csv_file = reporte.generar_csv(filtros)
    
    headers = {
        'Content-Disposition': 'attachment; filename="asignaciones.csv"'
    }
    return StreamingResponse(csv_file, media_type="text/csv", headers=headers)

@app.post("/descargar_json")
async def descargar_json(request: Request):
    filtros = await request.json()
    
    reporte = Reporte_Asignaciones()
    json_data = reporte.generar_json(filtros)
    
    headers = {
        'Content-Disposition': 'attachment; filename="asignaciones.json"'
    }
    return JSONResponse(content=json_data, headers=headers)

##################################################################
# FUNCIONALIDADES DE CONSULTA DE ASIGNACIONES Y TRAERLO EN GRILLA"
# Instancia de la clase para manejar consultas en la base de datos

@app.post("/api/obtener_asignaciones_ayuda")
async def obtener_asignaciones_ayuda(request: Request):
    data = await request.json()
    fecha = data['fecha']
    concesion = data['concesion']
    fecha_hora_registro = data.get('fecha_hora_registro')

    reporte = Reporte_Asignaciones()
    asignaciones = reporte.obtener_asignacion_por_fecha(fecha, concesion, fecha_hora_registro)

    if not asignaciones:
        return JSONResponse(content={"message": "No se encontraron asignaciones para la fecha, concesión y fecha/hora seleccionadas."}, status_code=404)
    
    return JSONResponse(content={"asignaciones": asignaciones}, status_code=200)

@app.post("/api/obtener_concesiones_por_fecha")
async def obtener_concesiones_por_fecha(request: Request):
    data = await request.json()
    fecha = data['fecha']

    reporte = Reporte_Asignaciones()
    concesiones = reporte.obtener_concesiones_unicas_por_fecha(fecha)

    if not concesiones:
        return JSONResponse(content={"message": "No se encontraron concesiones para la fecha seleccionada."}, status_code=404)

    return JSONResponse(content=concesiones)

@app.post("/api/obtener_fechas_horas_registro")
async def obtener_fechas_horas_registro(request: Request):
    data = await request.json()
    fecha = data['fecha']
    concesion = data['concesion']

    reporte = Reporte_Asignaciones()
    fechas_horas = reporte.obtener_fechas_horas_registro(fecha, concesion)

    if not fechas_horas:
        return JSONResponse(content={"message": "No se encontraron registros para la fecha y concesión seleccionada."}, status_code=404)
    
    return JSONResponse(content={"fechas_horas": fechas_horas}, status_code=200)

# Define el modelo para las asignaciones individuales para el PDF
class Asignacion(BaseModel):
    fecha: str
    cedula: str
    nombre: str
    turno: str
    h_inicio: str
    h_fin: str
    concesion: str
    control: str
    ruta: str
    linea: str
    cop: str
    observaciones: str
    puestosSC: int
    puestosUQ: int
    fecha_hora_registro: str

# Define el modelo para la solicitud de PDF
class PDFRequest(BaseModel):
    asignaciones: List[Asignacion]
    fecha_asignacion: str
    fecha_hora_registro: str

@app.post("/generar_pdf/")
def generar_pdf_asignaciones(request: PDFRequest):
    try:
        # Crear un buffer de memoria
        pdf_buffer = BytesIO()

        # Instanciar la clase Reporte_Asignaciones
        reporte_asignaciones = Reporte_Asignaciones()

        # Generar el PDF usando el buffer
        reporte_asignaciones.generar_pdf(
            request.asignaciones,  # Lista de asignaciones
            request.fecha_asignacion,  # Fecha de asignación
            request.fecha_hora_registro,  # Fecha de última modificación
            pdf_buffer  # Buffer de memoria para escribir el PDF
        )

        # Asegurarse de que el buffer esté al inicio antes de enviarlo
        pdf_buffer.seek(0)

        # Devolver el PDF generado directamente al cliente sin guardarlo en disco
        return StreamingResponse(pdf_buffer, media_type='application/pdf', headers={
            "Content-Disposition": "attachment; filename=asignaciones_tecnicos.pdf"
        })

    except Exception as e:
        return {"error": str(e)}

############ SECCIÓN PARAMETRIZACIÓN DE ROLES ################
# Simula la base de datos de roles
roles_db = {
    "admin": ["Centro de Control", "Configuración"],
    "user": ["Centro de Control"]
}

def get_pantallas_from_layout():
    # Asegúrate de que el archivo 'layout.html' está en 'view/components'
    layout_path = os.path.join(os.path.dirname(__file__), 'view', 'components', 'layout.html')
    print(f"Intentando abrir el archivo en: {layout_path}")  # Imprime la ruta para verificar
    with open(layout_path, 'r', encoding='utf-8') as f:
        layout_html = f.read()

    # Usa BeautifulSoup para extraer los enlaces
    soup = BeautifulSoup(layout_html, 'html.parser')
    
    # Extrae los textos de los enlaces dentro del sidebar
    pantallas = []
    for link in soup.select(".sidebar .nav-link"):
        pantallas.append(link.text.strip())  # Extrae el texto visible del enlace

    return pantallas

@app.get("/roles", response_class=HTMLResponse)
def get_roles(req: Request, user_session: dict = Depends(get_user_session)):
    if not user_session:
        return RedirectResponse(url="/", status_code=302)

    pantallas_disponibles = get_pantallas_from_layout()  # Extrae las pantallas del layout
    roles = roles_db  # Simulando datos de la base de datos
    
    return templates.TemplateResponse("roles.html", {
        "request": req, 
        "roles": roles, 
        "pantallas": pantallas_disponibles, 
        "user_session": user_session  # Asegurarse de pasar user_session
    })

@app.post("/roles/add", response_class=HTMLResponse)
async def add_role(request: Request, role_name: str = Form(...), permissions: list[str] = Form(...)):
    # Simula agregar un nuevo rol a la base de datos
    roles_db[role_name] = permissions
    pantallas_disponibles = get_pantallas_from_layout()  # Extrae las pantallas del layout
    return templates.TemplateResponse("roles.html", {"request": request, "roles": roles_db, "pantallas": pantallas_disponibles})

################## SECCIÓN JURIDICO ####################
@app.get("/juridico", response_class=HTMLResponse)
def registrarse(req: Request, user_session: dict = Depends(get_user_session)):
    if not user_session:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("juridico.html", {"request": req, "user_session": user_session})
