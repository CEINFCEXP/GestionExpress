from fastapi import APIRouter, Depends, Request, HTTPException
from starlette.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from model.gestion_checklist import GestionChecklist
from pydantic import BaseModel
from datetime import datetime, time
from typing import List, Optional
import io, json
import pandas as pd


# Crear router
checklist_router = APIRouter()

# Configurar plantillas Jinja2
templates = Jinja2Templates(directory="./view")

# Función localmente para validar usuario
def get_user_session(req: Request):
    return req.session.get('user')

@checklist_router.get("/checklist", response_class=HTMLResponse)
def checklist(req: Request, user_session: dict = Depends(get_user_session)):
    if not user_session:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(
        "checklist.html",
        {
            "request": req,
            "user_session": user_session,
            "componentes": {}
        }
    )

# --- REGISTRO Y PARAMETRIZACIÓN DE VEHÍCULOS ---
@checklist_router.get("/tipos_vehiculos")
def obtener_tipos_vehiculos():
    gestion = GestionChecklist()
    tipos = gestion.obtener_tipos_vehiculos()
    return JSONResponse(content=tipos)

@checklist_router.post("/vehiculos/crear")
def crear_vehiculo(request: Request, data: dict):
    gestion = GestionChecklist()
    resultado = gestion.crear_vehiculo(data)
    return JSONResponse(content=resultado)

@checklist_router.get("/vehiculos")
def obtener_vehiculos():
    gestion = GestionChecklist()
    vehiculos = gestion.obtener_vehiculos()
    return JSONResponse(content=vehiculos)

@checklist_router.get("/vehiculos/{placa}")
def obtener_vehiculo(placa: str):
    gestion = GestionChecklist()
    vehiculo = gestion.obtener_vehiculo_por_placa(placa)
    
    if vehiculo:
        return JSONResponse(content=vehiculo)
    else:
        return JSONResponse(content={"error": "Vehículo no encontrado"}, status_code=404)

@checklist_router.put("/vehiculos/actualizar/{placa}")
def actualizar_vehiculo(placa: str, data: dict):
    gestion = GestionChecklist()
    resultado = gestion.actualizar_vehiculo(placa, data)
    return JSONResponse(content=resultado)

@checklist_router.put("/vehiculos/inactivar/{placa}/{nuevo_estado}")
def inactivar_vehiculo(placa: str, nuevo_estado: int):
    gestion = GestionChecklist()
    resultado = gestion.inactivar_vehiculo(placa, nuevo_estado)
    return JSONResponse(content=resultado)

# --- CONSULTA Y REGISTRO CHECKLIST ESTADO DEL VEHICULO ---
@checklist_router.get("/vehiculos/buscar/{query}")
def buscar_vehiculos(query: str):
    gestion = GestionChecklist()
    vehiculos = gestion.buscar_vehiculos(query)
    return JSONResponse(content=vehiculos)

@checklist_router.get("/documentos")
def obtener_tipos_documentos():
    """Obtiene la lista de tipos de documentos desde la base de datos"""
    gestion = GestionChecklist()
    try:
        documentos = gestion.obtener_tipos_documentos()
        return JSONResponse(content=documentos)
    finally:
        gestion.cerrar_conexion()

@checklist_router.get("/componentes/{placa}")
def obtener_componentes_por_placa(placa: str):
    """Obtiene los componentes para un vehículo según su placa"""
    gestion = GestionChecklist()
    
    # Obtener el vehículo por la placa
    vehiculo = gestion.obtener_vehiculo_por_placa(placa)
    
    if not vehiculo:
        print(f"🚨 ERROR: Vehículo con placa {placa} no encontrado en la BD.")
        return JSONResponse(content={"error": "Vehículo no encontrado"}, status_code=404)

    id_tipo_vehiculo = vehiculo.get("id_tipo_vehiculo")
    #print(f" ID Tipo de Vehículo encontrado: {id_tipo_vehiculo}")

    if not id_tipo_vehiculo:
        print(f"🚨 ERROR: Tipo de vehículo no encontrado para {placa}")
        return JSONResponse(content={"error": "Tipo de vehículo no encontrado"}, status_code=400)

    # Obtener los componentes por tipo de vehículo
    componentes = gestion.obtener_componentes_por_tipo(id_tipo_vehiculo)
    # print(f"🔍 Componentes obtenidos para tipo {id_tipo_vehiculo}: {componentes}")

    if not isinstance(componentes, list) or len(componentes) == 0:
        print(f"🚨 ERROR: No hay componentes para el tipo de vehículo {id_tipo_vehiculo}")
        return JSONResponse(content={"error": "No hay componentes para este tipo de vehículo"}, status_code=404)

    # Agrupar los componentes por grupo
    componentes_agrupados = {}
    for componente in componentes:
        if not isinstance(componente, dict):
            print(f"🚨 ERROR: Componente en formato incorrecto: {componente}")
            return JSONResponse(content={"error": "Formato de componente incorrecto"}, status_code=500)

        grupo = componente["grupo"]
        if grupo not in componentes_agrupados:
            componentes_agrupados[grupo] = []

        componentes_agrupados[grupo].append({
            "id_componente": componente["id_componente"],
            "posicion": componente["posicion"],
            "componente": componente["componente"]
        })

    # print(f" Componentes agrupados listos para envío: {componentes_agrupados}")
    return JSONResponse(content=componentes_agrupados)

@checklist_router.get("/vehiculos/checklist/{placa}")
def obtener_checklist_vehiculo(placa: str):
    """Obtiene la información del vehículo y su checklist más reciente"""
    gestion = GestionChecklist()

    # 1. Buscar el vehículo
    vehiculo = gestion.obtener_vehiculo_por_placa(placa)
    if not vehiculo:
        return JSONResponse(content={"error": "Vehículo no encontrado"}, status_code=404)

    #print(f" Vehículo encontrado: {vehiculo}")

    # 2. Obtener el último checklist registrado
    checklist = gestion.obtener_ultimo_checklist(vehiculo["id_vehiculo"])
    
    # 3. Obtener documentos y detalles del checklist
    documentos = gestion.obtener_documentos_checklist(checklist["id_checklist"]) if checklist else []
    detalles = gestion.obtener_detalles_checklist(checklist["id_checklist"]) if checklist else []

    # Validar que documentos y detalles no sean None
    documentos = documentos if documentos is not None else []
    detalles = detalles if detalles is not None else []

    #print(f" Documentos encontrados: {documentos}")
    #print(f" Detalles encontrados: {detalles}")

    # 4. Obtener los componentes del vehículo
    componentes = gestion.obtener_componentes_por_tipo(vehiculo["id_tipo_vehiculo"])

    # print(f"Componentes agrupados listos para envío: {componentes}")

    # 5. Convertir valores `datetime` y `time` a `str`
    def convertir_a_str(obj):
        """Convierte datetime y time a string"""
        if isinstance(obj, datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(obj, time):
            return obj.strftime("%H:%M:%S")
        return obj

    if checklist:
        checklist = {key: convertir_a_str(value) for key, value in checklist.items()}

    return JSONResponse(content={
        "vehiculo": vehiculo,
        "checklist": checklist or {},
        "documentos": documentos,
        "detalles": detalles,
        "componentes": componentes
    })

# --- GUARDAR CHECKLIST DEL VEHICULO ---
class RegistroChecklist(BaseModel):
    id_vehiculo: int
    fecha_hora_registro: str
    inicio_turno: str
    fin_turno: str
    km_odometro: int
    observaciones_generales: Optional[str] = ""
    usuario_registro: str

class DocumentoChecklist(BaseModel):
    id_tipo_documento: int
    estado: bool
    observaciones: Optional[str] = ""

class DetalleChecklist(BaseModel):
    id_componente: int
    estado: bool
    observaciones: Optional[str] = ""

class ChecklistRequest(BaseModel):
    registro: RegistroChecklist
    documentos: List[DocumentoChecklist]
    detalles: List[DetalleChecklist]

@checklist_router.post("/guardar_checklist")
async def guardar_checklist(data: ChecklistRequest):
    #print("Datos recibidos:", data.dict())

    if not data.documentos or not data.detalles:
        raise HTTPException(status_code=400, detail="Debe completar documentos y estado del vehículo.")

    # Validación para evitar valores nulos en documentos y detalles
    if any(doc.id_tipo_documento is None for doc in data.documentos):
        raise HTTPException(status_code=400, detail="Error: Hay documentos sin un ID válido.")

    if any(det.id_componente is None for det in data.detalles):
        raise HTTPException(status_code=400, detail="Error: Hay componentes sin un ID válido.")

    gestion = GestionChecklist()
    id_checklist = gestion.guardar_checklist_registro(data.registro)

    if not id_checklist:
        raise HTTPException(status_code=500, detail="Error al guardar checklist_registro")

    for doc in data.documentos:
        gestion.guardar_checklist_documento(id_checklist, doc)

    for detalle in data.detalles:
        gestion.guardar_checklist_detalle(id_checklist, detalle)

    return {"message": "Checklist guardado correctamente", "id_checklist": id_checklist}

# --- GESTIÓN FALLAS CHECKLIST DEL VEHICULO ---
@checklist_router.get("/fallas_vehiculos")
def obtener_vehiculos_con_fallas():
    """Retorna vehículos con al menos una falla registrada en su checklist"""
    gestion = GestionChecklist()
    vehiculos = gestion.obtener_vehiculos_con_fallas()
    return JSONResponse(content=vehiculos)

@checklist_router.get("/fallas_vehiculo/{placa}")
def obtener_detalles_falla_por_placa(placa: str):
    """Retorna todos los detalles de fallas por vehículo"""
    gestion = GestionChecklist()
    data = gestion.obtener_detalle_falla_vehiculo(placa)
    return JSONResponse(content=data)

# --- GENERACIÓN REPORTES ---
@checklist_router.get("/reportes/filtros")
def obtener_filtros_para_reportes():
    gestion = GestionChecklist()
    try:
        filtros = gestion.obtener_filtros_reportes()
        return JSONResponse(content=filtros)
    finally:
        gestion.cerrar_conexion()
        
@checklist_router.get("/reportes/fallas")
def consultar_reporte_fallas(
    fecha: Optional[str] = None,
    placa: Optional[str] = None,
    tipo_vehiculo: Optional[str] = None,
    marca: Optional[str] = None,
    estado: Optional[str] = None,
    usuario: Optional[str] = None
):
    if not fecha:
        raise HTTPException(status_code=400, detail="La fecha de reporte es obligatoria.")

    gestion = GestionChecklist()
    try:
        resultados = gestion.consultar_datos_reporte(
            fecha=fecha,
            placa=placa,
            tipo_vehiculo=tipo_vehiculo,
            marca=marca,
            estado=estado,
            usuario=usuario
        )
        return JSONResponse(content=resultados)
    finally:
        gestion.cerrar_conexion()

@checklist_router.get("/reportes/fallas/exportar")
def exportar_reporte_fallas(
    fecha: str,
    placa: str = "",
    tipo_vehiculo: str = "",
    marca: str = "",
    estado: str = "",
    usuario: str = "",
    formato: str = "xlsx"
):
    gestion = GestionChecklist()
    resultados = gestion.consultar_datos_reporte(
        fecha=fecha,
        placa=placa,
        tipo_vehiculo=tipo_vehiculo,
        marca=marca,
        estado=estado,
        usuario=usuario
    )

    if not resultados:
        return JSONResponse(content={"error": "No hay datos para exportar"}, status_code=404)

    df = pd.DataFrame(resultados)

    if formato == "json":
        json_bytes = json.dumps(resultados, indent=2).encode("utf-8")
        output = io.BytesIO(json_bytes)
        return StreamingResponse(output, media_type="application/json", headers={
            "Content-Disposition": f"attachment; filename=Reporte_Fallas_{fecha}.json"
        })

    output = io.BytesIO()
    if formato == "csv":
        df.to_csv(output, index=False, sep=";", encoding="utf-8-sig")
        output.seek(0)
        return StreamingResponse(output, media_type="text/csv", headers={
            "Content-Disposition": f"attachment; filename=Reporte_Fallas_{fecha}.csv"
        })

    # Por defecto, Excel
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Fallas')
    output.seek(0)
    return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={
        "Content-Disposition": f"attachment; filename=Reporte_Fallas_{fecha}.xlsx"
    })
