import psycopg2
from datetime import datetime
from fastapi import HTTPException

DATABASE_PATH = "postgresql://gestionexpress:G3st10n3xpr3ss@serverdbcexp.postgres.database.azure.com:5432/gestionexpress"

def fecha_asignacion(fecha_str):
    try:
        fecha = datetime.strptime(fecha_str, "%d/%m/%Y")
        if fecha < datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
            raise HTTPException(status_code=400, detail="La fecha debe ser el día actual o una fecha futura.")
        return fecha_str
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use DD/MM/YYYY.")

def puestos_SC():
    conn = psycopg2.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT puestos FROM controles WHERE concesion = 'SAN CRISTÓBAL'")
    puestos = [row[0] for row in cursor.fetchall()]
    conn.close()
    return puestos

def puestos_UQ():
    conn = psycopg2.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT puestos FROM controles WHERE concesion = 'USAQUÉN'")
    puestos = [row[0] for row in cursor.fetchall()]
    conn.close()
    return puestos

def concesion():
    conn = psycopg2.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT concesion FROM controles")
    concesiones = [row[0] for row in cursor.fetchall()]
    conn.close()
    return concesiones

def control(concesion_seleccionada, puestos_seleccionado):
    conn = psycopg2.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    query = """
    SELECT DISTINCT control FROM controles 
    WHERE concesion = %s AND puestos = %s
    """
    cursor.execute(query, (concesion_seleccionada, puestos_seleccionado))
    controles = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    return controles

def rutas(concesion, puestos, control):
    conn = psycopg2.connect(DATABASE_PATH)
    cursor = conn.cursor()
    print(f"Filtrando rutas para concesion: {concesion}, puestos: {puestos}, control: {control}")  # Validación

    #Consulta basada en concesion, puestos, and control
    query = """
    SELECT ruta FROM controles 
    WHERE concesion = %s AND puestos = %s AND control = %s
    """
    cursor.execute(query, (concesion, puestos, control))
    rutas = [row[0] for row in cursor.fetchall()]
    print(f"Rutas obtenidas: {rutas}") 
    conn.close()
    
    # Ordenar las rutas y unirlas en una cadena separada por comas
    if rutas:
        rutas_unidas = ", ".join(sorted(rutas))
    else:
        rutas_unidas = ""
    
    return rutas_unidas

def turnos():
    conn = psycopg2.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT turno FROM turnos")
    turnos = [row[0] for row in cursor.fetchall()]
    conn.close()
    return turnos

def turno_descripcion(turno):
    conn = psycopg2.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT descripcion FROM turnos WHERE turno = %s", (turno,))
    descripcion = cursor.fetchone()
    conn.close()
    return descripcion[0] if descripcion else None

def hora_inicio(turno):
    conn = psycopg2.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT hora_inicio FROM turnos WHERE turno = %s", (turno,))
    hora_inicio = cursor.fetchone()[0]
    conn.close()
    return hora_inicio

def hora_fin(turno):
    conn = psycopg2.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT hora_fin FROM turnos WHERE turno = %s", (turno,))
    hora_fin = cursor.fetchone()[0]
    conn.close()
    return hora_fin


    


