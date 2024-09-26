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
from model.gestionar_db import CargueLicenciasBI
from model.gestionar_db import HandleDB
from model.consultas_db import Reporte_Asignaciones
from lib.asignar_controles import fecha_asignacion, puestos_SC, puestos_UQ, concesion, control, rutas, turnos, hora_inicio, hora_fin
from werkzeug.security import generate_password_hash
import psycopg2
import json
from typing import List, Optional
from io import BytesIO 
import os

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="!secret_key")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="./view")
db = HandleDB()
import shutil
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
    # Verifica las credenciales del usuario
    verify, nombres, apellidos = check_user(username, password_user)
    
    if verify:
        # Obtén la información del usuario desde la base de datos, incluyendo el rol
        user_data = db.get_only(username)  # Esto debe retornar la fila completa del usuario

        if user_data:
            estado = user_data[6]  # campo de estado del usuario
            rol = user_data[4]  # es el id_rol del usuario
            
            # Verificamos si el estado del usuario es activo (1)
            if estado == 1:
                # Guardar la sesión del usuario, incluyendo el rol
                req.session['user'] = {
                    "username": username,
                    "nombres": nombres,
                    "apellidos": apellidos,
                    "rol": rol
                }

                # Redirigir al usuario a la página de inicio después del login
                return RedirectResponse(url="/inicio", status_code=302)
            else:
                # Si el usuario está inactivo (estado == 0), muestra un mensaje de error
                error_message = "El usuario está inactivo. No puede iniciar sesión."
                return templates.TemplateResponse("index.html", {"request": req, "error_message": error_message})
    else:
        # Si las credenciales no son válidas, muestra un mensaje de error
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

    roles = db.get_all_roles()  # Obtiene los roles desde la base de datos
    usuarios = db.get_all_users()  # Obtiene los usuarios desde la base de datos

    return templates.TemplateResponse("registrarse.html", {
        "request": req,
        "user_session": user_session,
        "roles": roles,
        "usuarios": usuarios
    })

@app.get("/registrarse/{user_id}/datos" )
async def get_user_data(user_id: int):
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    return JSONResponse(content={
        "id": user["id"],
        "nombres": user["nombres"],
        "apellidos": user["apellidos"],
        "username": user["username"],
        "rol": user["rol"],
        "estado": user["estado"]
    })

@app.post("/registrarse", response_class=HTMLResponse)
def registrarse_post(req: Request, nombres: str = Form(...), apellidos: str = Form(...),
                     username: str = Form(...), rol: int = Form(...),
                     password_user: str = Form(...), user_session: dict = Depends(get_user_session)):
    if not user_session:
        return RedirectResponse(url="/", status_code=302)

    data_user = {
        "nombres": nombres,
        "apellidos": apellidos,
        "username": username,
        "rol": rol,
        "password_user": password_user,
        "estado": 1
    }
    
    user = User(data_user)
    result = user.create_user()

    if result.get("success"):
        # Establecer una cookie con el mensaje de éxito
        response = RedirectResponse(url="/registrarse", status_code=303)
        response.set_cookie(key="success_message", value="Usuario creado correctamente.", max_age=5)
        return response
    else:
        # Establecer una cookie con el mensaje de error
        error_message = result.get("message", "Error desconocido al crear usuario.")
        response = RedirectResponse(url="/registrarse", status_code=303)
        response.set_cookie(key="error_message", value=error_message, max_age=5)
        return response

@app.post("/registrarse/{id}/editar")
async def editar_usuario(id: int, request: Request, user_data: dict = Depends(get_user_session)):
    try:
        form_data = await request.form()
        # Convertimos FormData en un diccionario
        form_data_dict = dict(form_data)

        # Verificamos si se proporcionó una nueva contraseña
        password_user = form_data_dict.get("password_user")
        if not password_user:
            # Si no se proporcionó una nueva contraseña, quitamos ese campo del formulario
            form_data_dict.pop("password_user", None)
        else:
            # Si se proporciona una nueva contraseña, la encriptamos
            form_data_dict["password_user"] = generate_password_hash(password_user)

        # Llama a la función para actualizar el usuario en la base de datos
        db.update_user(id, form_data_dict)
        
        # Crear respuesta de redirección con una cookie que contenga el mensaje de éxito
        response = RedirectResponse(url="/registrarse", status_code=303)
        response.set_cookie(key="success_message", value="Usuario actualizado correctamente.", max_age=5)
        return response

    except Exception as e:
        return templates.TemplateResponse("registrarse.html", {
            "request": request,
            "user_session": user_data,
            "error_message": f"Error al actualizar el usuario: {str(e)}"
        })

@app.post("/registrarse/{id}/inactivar")
async def inactivate_user(id: int, request: Request, user_data: dict = Depends(get_user_session)):
    try:
        db.inactivate_user(id)
       
        # Crear respuesta de redirección con una cookie que contenga el mensaje de éxito
        response = RedirectResponse(url="/registrarse", status_code=303)
        response.set_cookie(key="success_message", value="Usuario inactivado correctamente.", max_age=5)
        return response
        
    except Exception as e:
        return templates.TemplateResponse("registrarse.html", {
            "request": request,
            "user_session": user_data,
            "error_message": f"Error al inactivar el usuario: {str(e)}"
        })

@app.get("/roles", response_class=HTMLResponse)
async def get_roles(request: Request, user_session: dict = Depends(get_user_session)):
    if not user_session:
        return RedirectResponse(url="/", status_code=302)  # Redirigir si no hay sesión iniciada.

    pantallas_disponibles = db.get_pantallas_from_layout('view/components/layout.html')
    roles = db.get_all_roles()

    # Verifica si existe el parámetro de éxito en la URL
    success_message = None
    success_param = request.query_params.get('success', None)

    if success_param == '1':
        success_message = "Rol creado correctamente."
    elif success_param == '2':
        success_message = "Rol actualizado correctamente."
    elif success_param == '3':
        success_message = "Rol eliminado correctamente."

    return templates.TemplateResponse("roles.html", {
        "request": request,
        "roles": roles,
        "pantallas": pantallas_disponibles,
        "success_message": success_message,
        "user_session": user_session  # Pasa `user_session` al contexto de la plantilla.
    })

@app.get("/roles/{id_rol}/datos")
async def obtener_datos_rol(id_rol: int):
    # Obtener los datos del rol desde la base de datos
    rol = db.get_role_by_id(id_rol)

    if not rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")

    id_rol, nombre_rol, pantallas_asignadas = rol

    return JSONResponse(content={
        "id_rol": id_rol,
        "nombre_rol": nombre_rol,
        "pantallas_asignadas": pantallas_asignadas.split(',')  # Convertimos las pantallas a lista
    })

@app.post("/roles", response_class=HTMLResponse)
async def add_role(request: Request, role_name: str = Form(...), permissions: List[str] = Form(...), role_id: Optional[int] = Form(None)):
    if role_id:
        # Si hay un role_id, entonces es una actualización
        return await update_role(request, role_id, role_name, permissions)

    # Validaciones
    if not role_name.strip():
        return templates.TemplateResponse("roles.html", {
            "request": request,
            "roles": db.get_all_roles(),
            "pantallas": db.get_pantallas_from_layout('view/components/layout.html'),
            "error_message": "Debe ingresar un nombre para el rol."
        })

    if not permissions or len(permissions) == 0:
        return templates.TemplateResponse("roles.html", {
            "request": request,
            "roles": db.get_all_roles(),
            "pantallas": db.get_pantallas_from_layout('view/components/layout.html'),
            "error_message": "Debe seleccionar al menos una pantalla para asignar al rol."
        })

    # Inserta el nuevo rol en la base de datos
    permisos_string = ','.join(permissions)
    db.insert_role({
        "nombre_rol": role_name,
        "pantallas_asignadas": permisos_string
    })

    return RedirectResponse(url="/roles?success=1", status_code=303)

@app.post("/roles/{role_id}/editar", response_class=HTMLResponse)
async def update_role(request: Request, role_id: int, role_name: str = Form(...), permissions: List[str] = Form(...)):
    # Validaciones
    if not role_name.strip():
        return templates.TemplateResponse("roles.html", {
            "request": request,
            "roles": db.get_all_roles(),
            "pantallas": db.get_pantallas_from_layout('view/components/layout.html'),
            "error_message": "Debe ingresar un nombre para el rol."
        })

    if not permissions or len(permissions) == 0:
        return templates.TemplateResponse("roles.html", {
            "request": request,
            "roles": db.get_all_roles(),
            "pantallas": db.get_pantallas_from_layout('view/components/layout.html'),
            "error_message": "Debe seleccionar al menos una pantalla para asignar al rol."
        })

    # Actualizar el rol
    permisos_string = ','.join(permissions)
    db.update_role(role_id, role_name, permisos_string)

    return RedirectResponse(url="/roles?success=2", status_code=303)

@app.post("/roles/{role_id}/eliminar")
async def eliminar_rol(role_id: int):
    try:
        db.delete_role(role_id)
        return RedirectResponse(url="/roles?success=3", status_code=303)
    except Exception as e:
        return templates.TemplateResponse("roles.html", {
            "roles": db.get_all_roles(),
            "pantallas": db.get_pantallas_from_layout('view/components/layout.html'),
            "error_message": f"Ocurrió un error al intentar eliminar el rol: {e}"
        })

@app.get("/pantallas_permitidas", response_class=JSONResponse)
def obtener_pantallas_permitidas(req: Request, user_session: dict = Depends(get_user_session)):
    if not user_session:
        return JSONResponse({"error": "Usuario no autenticado"}, status_code=401)

    role_id = user_session.get("rol")
    if not role_id:
        return JSONResponse({"error": "Rol no encontrado para el usuario"}, status_code=404)

    # Consultar las pantallas asignadas al rol del usuario
    pantallas_permitidas = db.get_pantallas_by_role(role_id)
    if not pantallas_permitidas:
        return JSONResponse({"error": "No hay pantallas asignadas para el rol"}, status_code=404)

    return JSONResponse({"pantallas": pantallas_permitidas}, status_code=200)

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

############### SECCIÓN POWER_BI EMBEBIDO #################
@app.get("/powerbi", response_class=HTMLResponse)
def get_powerbi(req: Request, user_session: dict = Depends(get_user_session)):
    if not user_session:
        return RedirectResponse(url="/", status_code=302)

    # Obtener la cédula del usuario logueado desde la sesión
    cedula = user_session.get('username')  # La cédula está en 'username'
    
    # Consulta a la tabla licencias_bi
    licencias_bi_query = """SELECT licencia_bi, contraseña_licencia 
                            FROM licencias_bi 
                            WHERE cedula = %s"""
    result = db.fetch_one(query=licencias_bi_query, values=(cedula,))

    if result:
        # Imprimir en la terminal para verificar las credenciales
        #print(f"Licencia: {result[0]}")
        #print(f"Contraseña: {result[1]}")
        
        # Si se encuentra una licencia, pasar los datos a la plantilla
        return templates.TemplateResponse("powerbi.html", {
            "request": req,
            "user_session": user_session,
            "licencia_bi": result[0],
            "contraseña_licencia": result[1],
            "error_message": None  # No hay error
        })
    else:
        # Si no se encuentra la licencia, mostrar el mensaje de error en la plantilla
        return templates.TemplateResponse("powerbi.html", {
            "request": req,
            "user_session": user_session,
            "licencia_bi": None,
            "contraseña_licencia": None,
            "error_message": "No se encontraron licencias para el usuario."  # Pasar el mensaje de error
        })

@app.post("/cargar_licencias")
async def cargar_licencias(file: UploadFile = File(...)):
    try:
        # Guardar el archivo temporalmente
        file_path = f"temp_{file.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Instanciar el cargador de licencias y cargar el archivo
        db_conn = psycopg2.connect(DATABASE_PATH)
        cargador = CargueLicenciasBI(db_conn)
        result = cargador.cargar_licencias_excel(file_path)

        # Eliminar el archivo temporal
        os.remove(file_path)

        # Retornar el resultado en formato JSON
        return result
    except Exception as e:
        return {"error": str(e)}

################## SECCIÓN JURIDICO ####################
@app.get("/juridico", response_class=HTMLResponse)
def registrarse(req: Request, user_session: dict = Depends(get_user_session)):
    if not user_session:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("juridico.html", {"request": req, "user_session": user_session})
