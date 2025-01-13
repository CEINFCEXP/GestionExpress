import psycopg2
import json
import os
import re
import pandas as pd
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from datetime import datetime, timedelta, date
from azure.storage.blob import BlobServiceClient, ContainerClient
from office365.runtime.auth.authentication_context import AuthenticationContext
from office365.sharepoint.client_context import ClientContext
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Cargar las variables de entorno desde .env
load_dotenv()
DATABASE_PATH = os.getenv("DATABASE_PATH")
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME = "5000-juridica-y-riesgos-juridica-clausulas"
site_url = "https://grupoexpress.sharepoint.com/sites/PlataformaBICEXP"
username = os.getenv("USUARIO_JURIDICO")
password = os.getenv("CLAVE_JURIDICO")
remitente = os.getenv("USUARIO_CORREO_JURIDICO")
contrasena = os.getenv("CLAVE_CORREO_JURIDICO")

# Configuración del servidor SMTP Correos Automaticos
smtp_server = "smtp.office365.com"
smtp_port = 587

class GestionClausulas:
    def __init__(self):
        self.connection = psycopg2.connect(DATABASE_PATH)
    
    def obtener_clausulas(self):
        with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
            query = """
            SELECT id, control, etapa, clausula, contrato_concesion, tema, descripcion_clausula, 
                   tipo_clausula, frecuencia
            FROM clausulas
            ORDER BY id ASC;;
            """
            cursor.execute(query)
            clausulas = cursor.fetchall()
        return clausulas
    
    def obtener_opciones_etapas(self):
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT DISTINCT etapa FROM etapas_juridico;")
            etapas = cursor.fetchall()
        return etapas
    
    def obtener_opciones_clausulas(self):
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT DISTINCT clausula FROM clausulas ORDER BY clausula;")
            clausulas = cursor.fetchall()
        return clausulas

    def obtener_opciones_concesion(self):
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT DISTINCT concesion FROM concesion;")
            concesiones = cursor.fetchall()
        return concesiones
    
    def obtener_opciones_contrato(self):
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT DISTINCT contrato FROM concesion;")
            contratos = cursor.fetchall()
        return contratos
    
    def obtener_contrato_por_concesion(self, concesion):
        query = "SELECT contrato FROM concesion WHERE concesion = %s"
        with self.connection.cursor() as cursor:
            cursor.execute(query, (concesion,))
            contrato = cursor.fetchone()
        return contrato[0] if contrato else None
    
    def obtener_opciones_tipo_clausula(self):
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT DISTINCT tipo_clausula FROM tipo_clausulas ORDER BY tipo_clausula ASC;")
            tipos_clausula = cursor.fetchall()
        return tipos_clausula
    
    def obtener_opciones_procesos(self):
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT DISTINCT proceso FROM procesos ORDER BY proceso;")
            procesos = cursor.fetchall()
        return procesos
    
    def obtener_opciones_subprocesos(self, proceso):
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT subproceso FROM procesos WHERE proceso = %s ORDER BY subproceso;", (proceso,))
            subprocesos = cursor.fetchall()
        return subprocesos

    def obtener_opciones_frecuencias(self):
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT DISTINCT frecuencia FROM frecuencia ORDER BY frecuencia ASC;")
            frecuencias = cursor.fetchall()
        return frecuencias
    
    def obtener_opciones_responsables(self):
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT DISTINCT responsable FROM responsable ORDER BY responsable ASC;")
            responsables = cursor.fetchall()
        return responsables

    def obtener_opciones_responsables_clausulas(self):
        query = """
        SELECT DISTINCT TRIM(responsable_entrega) AS responsable_entrega
        FROM clausulas
        WHERE responsable_entrega IS NOT NULL
        ORDER BY responsable_entrega ASC;
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query)
            responsables = cursor.fetchall()
        
        return [fila[0] for fila in responsables]  # Extraer solo los valores únicos y ordenados

    def obtener_clausulas_filtradas(self, control=None, etapa=None, clausula=None, concesion=None, estado=None, responsable=None):
        query = """
        SELECT c.id, c.control, c.etapa, c.clausula, c.contrato_concesion, c.tema, c.descripcion_clausula, 
            c.tipo_clausula, c.frecuencia, 
            COALESCE(g.estado, 'Sin Estado') AS estado_mas_reciente
        FROM clausulas c
        LEFT JOIN (
            SELECT DISTINCT ON (id_clausula) id_clausula, fecha_entrega, estado
            FROM clausulas_gestion
            ORDER BY id_clausula, fecha_entrega DESC
        ) g ON c.id = g.id_clausula
        WHERE (%s IS NULL OR c.control = %s)
        AND (%s IS NULL OR c.etapa = %s)
        AND (%s IS NULL OR c.clausula = %s)
        AND (%s IS NULL OR c.contrato_concesion = %s)
        AND (%s IS NULL OR g.estado = %s)
        AND (%s IS NULL OR TRIM(c.responsable_entrega) = TRIM(%s)) -- Coincidencia exacta
        ORDER BY c.id ASC;
        """
        with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, (
                control, control,
                etapa, etapa,
                clausula, clausula,
                concesion, concesion,
                estado, estado,
                responsable, responsable  # Responsable
            ))
            clausulas = cursor.fetchall()
        return clausulas

    def obtener_id_proceso(self, proceso, subproceso):
        query = """
        SELECT id_proceso FROM procesos
        WHERE proceso = %s AND subproceso = %s;
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, (proceso, subproceso))
            result = cursor.fetchone()
            if result:
                return result[0]  # Retornar el id_proceso
            else:
                raise ValueError(f"No se encontró el id_proceso para proceso: {proceso} y subproceso: {subproceso}")

    def crear_clausula(self, clausula_data):
        query_clausula = """
        INSERT INTO clausulas (control, etapa, clausula, modificacion, contrato_concesion, tema, subtema, descripcion_clausula, 
                            tipo_clausula, norma_relacionada, consecuencia, frecuencia, inicio_cumplimiento, 
                            fin_cumplimiento, observacion, periodo_control, responsable_entrega, ruta_soporte)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query_clausula, (
                clausula_data['control'],
                clausula_data['etapa'],
                clausula_data['clausula'],
                clausula_data['modificacion'],
                clausula_data['contrato'],
                clausula_data['tema'],
                clausula_data['subtema'],
                clausula_data['descripcion'],
                clausula_data['tipo'],
                clausula_data['norma'],
                clausula_data['consecuencia'],
                clausula_data['frecuencia'],
                clausula_data['inicio_cumplimiento'],
                clausula_data['fin_cumplimiento'],
                clausula_data['observacion'],
                clausula_data['periodo_control'],
                clausula_data['responsable_entrega'],
                clausula_data['ruta_soporte']
            ))
            id_clausula = cursor.fetchone()[0]
            self.connection.commit()
            #print("Cláusula registrada con ID:", id_clausula)
            return id_clausula

    def registrar_ruta_soporte(self, id_clausula, ruta_soporte):
        """
        Actualiza la ruta soporte para una cláusula existente.
        """
        query = """
        UPDATE clausulas
        SET ruta_soporte = %s
        WHERE id = %s;
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, (ruta_soporte, id_clausula))
                self.connection.commit()
                #print(f"Ruta soporte registrada para cláusula {id_clausula}: {ruta_soporte}")
        except Exception as e:
            self.connection.rollback()
            print(f"Error al registrar la ruta soporte: {e}")
            raise

    def registrar_clausula_proceso_subproceso(self, id_clausula, procesos_subprocesos):
        query = """
        INSERT INTO clausula_proceso_subproceso (id_clausula, id_proceso)
        VALUES (%s, %s);
        """
        try:
            with self.connection.cursor() as cursor:
                # Imprimir el id_clausula y procesos_subprocesos para verificar los datos recibidos
                #print("ID de la cláusula:", id_clausula)
                #print("Procesos a insertar:", procesos_subprocesos)

                # Iterar sobre cada proceso y registrar en la tabla
                for proceso in procesos_subprocesos:
                    id_proceso = proceso.get('id_proceso')
                    
                    if id_proceso:
                        # Ejecutar la inserción en la tabla
                        cursor.execute(query, (id_clausula, id_proceso))
                        #print(f"Registro insertado en clausula_proceso_subproceso: id_clausula={id_clausula}, id_proceso={id_proceso}")
                    else:
                        print("Error: id_proceso no encontrado en el objeto", proceso)
                self.connection.commit()  # Confirmar la transacción después de insertar todos los registros

        except Exception as e:
            self.connection.rollback()  # Revertir la transacción en caso de error
            #print(f"Error al insertar en clausula_proceso_subproceso: {e}")
            raise ValueError(f"Error al insertar en clausula_proceso_subproceso: {str(e)}")

    def obtener_clausula_por_id(self, id_clausula):
        query = """
        SELECT id, control, etapa, clausula, contrato_concesion, tema, subtema, descripcion_clausula, 
               tipo_clausula, modificacion, norma_relacionada, consecuencia, frecuencia, inicio_cumplimiento, 
               fin_cumplimiento, observacion, periodo_control, responsable_entrega, ruta_soporte
        FROM clausulas
        WHERE id = %s;
        """
        with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, (id_clausula,))
            clausula = cursor.fetchone()
        return clausula
    
    def obtener_procesos_subprocesos_por_clausula(self, id_clausula):
        query = """
        SELECT cps.id_proceso, p.proceso, p.subproceso
        FROM clausula_proceso_subproceso cps
        JOIN procesos p ON cps.id_proceso = p.id_proceso
        WHERE cps.id_clausula = %s;
        """
        with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, (id_clausula,))
            procesos_subprocesos = cursor.fetchall()
        return procesos_subprocesos
    
    def actualizar_clausula(self, id_clausula, clausula_data):
        query = """
        UPDATE clausulas
        SET control = %s, etapa = %s, clausula = %s, modificacion = %s, contrato_concesion = %s,
            tema = %s, subtema = %s, descripcion_clausula = %s, tipo_clausula = %s, norma_relacionada = %s,
            consecuencia = %s, frecuencia = %s, inicio_cumplimiento = %s, fin_cumplimiento = %s,
            observacion = %s, periodo_control = %s, responsable_entrega = %s, ruta_soporte = %s
        WHERE id = %s;
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, (
                    clausula_data.get('control'),
                    clausula_data.get('etapa'),
                    clausula_data.get('clausula'),
                    clausula_data.get('modificacion'),
                    clausula_data.get('contrato_concesion'),
                    clausula_data.get('tema'),
                    clausula_data.get('subtema'),
                    clausula_data.get('descripcion'),
                    clausula_data.get('tipo_clausula'),
                    clausula_data.get('norma_relacionada'),
                    clausula_data.get('consecuencia'),
                    clausula_data.get('frecuencia'),
                    clausula_data.get('inicio_cumplimiento'),
                    clausula_data.get('fin_cumplimiento'),
                    clausula_data.get('observacion'),
                    clausula_data.get('periodo_control'),
                    clausula_data.get('responsable_entrega'),
                    clausula_data.get('ruta_soporte'),
                    id_clausula
                ))
                self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            print(f"Error al actualizar la cláusula: {e}")
            raise e
            
    def actualizar_procesos_subprocesos(self, id_clausula, procesos_subprocesos):
        # Eliminar duplicados en la lista de procesos usando un conjunto
        procesos_unicos = {proceso['id_proceso'] for proceso in procesos_subprocesos}
        
        query_delete = "DELETE FROM clausula_proceso_subproceso WHERE id_clausula = %s;"
        query_insert = """
        INSERT INTO clausula_proceso_subproceso (id_clausula, id_proceso)
        VALUES (%s, %s);
        """
        with self.connection.cursor() as cursor:
            # Eliminar procesos/subprocesos existentes
            cursor.execute(query_delete, (id_clausula,))
            # Insertar los nuevos procesos/subprocesos únicos
            for id_proceso in procesos_unicos:
                cursor.execute(query_insert, (id_clausula, id_proceso))
            self.connection.commit()

    def calcular_fechas_dinamicas(self, inicio, fin, frecuencia, periodo_control):
        from dateutil.relativedelta import relativedelta
        from datetime import datetime, timedelta
        import calendar

        # Asegurar que los valores sean del tipo `datetime`
        if isinstance(inicio, date):
            inicio = datetime.combine(inicio, datetime.min.time())
        elif isinstance(inicio, str):
            inicio = datetime.strptime(inicio, "%Y-%m-%d")

        if isinstance(fin, date):
            fin = datetime.combine(fin, datetime.min.time())
        elif isinstance(fin, str):
            fin = datetime.strptime(fin, "%Y-%m-%d")

        fechas = []
        fecha_actual = datetime.today()

        # Diccionario de frecuencia
        delta = {
            "Mensual": relativedelta(months=1),
            "Bimestral": relativedelta(months=2),
            "Trimestral": relativedelta(months=3),
            "Semestral": relativedelta(months=6),
            "Anual": relativedelta(years=1),
        }

        # Normaliza la frecuencia
        frecuencia_normalizada = frecuencia.capitalize()

        if frecuencia_normalizada not in delta and frecuencia_normalizada not in ["Personalizado", "No aplica", "Diario", "Quincenal"]:
            raise ValueError(f"Frecuencia no válida: {frecuencia}")

        incremento = delta.get(frecuencia_normalizada, None)

        # Manejo especial para 'No aplica'
        if frecuencia_normalizada == "No aplica":
            return fechas  # Retorna lista vacía

        # Manejo especial para 'PERSONALIZADO'
        if frecuencia_normalizada == "Personalizado":
            if isinstance(periodo_control, str):
                try:
                    fecha_unica = datetime.strptime(periodo_control, "%Y-%m-%d")
                except ValueError:
                    raise ValueError(f"Formato de periodo_control inválido para 'Personalizado': {periodo_control}")
                if inicio <= fecha_unica <= fin:
                    fechas.append({
                        "fecha": fecha_unica.strftime("%Y-%m-%d"),
                        "entrega": fecha_unica.strftime("%Y-%m-%d")
                    })
            return fechas

        # Manejo especial para 'Diario' (excluyendo fines de semana)
        if frecuencia_normalizada == "Diario":
            fecha_entrega = inicio  # Comienza desde la fecha de inicio de cumplimiento
            while fecha_entrega <= min(fecha_actual, fin):  # Hasta la fecha actual o la fecha fin, lo que sea menor
                if fecha_entrega.weekday() < 5:  # Lunes a Viernes
                    fechas.append({
                        "fecha": fecha_entrega.strftime("%Y-%m-%d"),
                        "entrega": fecha_entrega.strftime("%Y-%m-%d")  # La fecha de entrega coincide con el día hábil
                    })
                fecha_entrega += timedelta(days=1)  # Avanza al siguiente día
            return fechas

        # Manejo especial para 'Quincenal'
        if frecuencia_normalizada == "Quincenal":
            # Normalizar el día configurado (quitar espacios y convertir a minúsculas )
            #print(f"Período Control recibido: {periodo_control}")
            dia_configurado = periodo_control.strip().lower()  # Ejemplo: "MIERCOLES" -> "miercoles"

            # Diccionario para convertir nombres de días al formato de calendar
            dias_semana = {
                "lunes": "Monday", "martes": "Tuesday", "miercoles": "Wednesday",
                "jueves": "Thursday", "viernes": "Friday", "sabado": "Saturday", "domingo": "Sunday"
            }
            
            if dia_configurado not in dias_semana:
                raise ValueError(f"El día configurado en periodo_control no es válido: {dia_configurado}")

            dia_configurado_en_ingles = dias_semana[dia_configurado]  # Convertir al formato esperado
            #print(f"Día configurado: {dia_configurado}, en inglés: {dia_configurado_en_ingles}")
            #print(f"Días disponibles: {list(dias_semana.keys())}")

            fecha_entrega = inicio  # Comienza desde la fecha de inicio de cumplimiento
            dias_por_ciclo = 14  # Ciclo de quincena

            # Validar que inicio y fin sean correctos
            if inicio > fin:
                raise ValueError(f"La fecha de inicio ({inicio}) no puede ser mayor que la fecha de fin ({fin}).")
            #print(f"Fecha inicial: {inicio}, Fecha final: {fin}")

            # Avanzar hasta el primer día configurado después de la fecha de inicio
            while calendar.day_name[fecha_entrega.weekday()] != dia_configurado_en_ingles:
                #print(f"Avanzando desde {fecha_entrega.strftime('%Y-%m-%d')} - Día actual: {calendar.day_name[fecha_entrega.weekday()]}")
                fecha_entrega += timedelta(days=1)

            # Generar fechas dinámicas desde la fecha actual hasta la fecha fin
            fechas = []
            while fecha_entrega <= min(fecha_actual, fin):
                fechas.append({
                    "fecha": fecha_entrega.strftime("%Y-%m-%d"),
                    "entrega": fecha_entrega.strftime("%Y-%m-%d")
                })
                #print(f"Fecha programada: {fecha_entrega.strftime('%Y-%m-%d')}")
                fecha_entrega += timedelta(days=dias_por_ciclo)

            #print(f"Fechas calculadas dinámicamente: {fechas}")
            return fechas

        # Para frecuencias basadas en delta (Mensual, Bimestral, Trimestral, Semestral, Anual)
        while inicio <= fin:
            if inicio <= fecha_actual:
                # Ajusta la fecha de entrega exactamente al periodo_control
                if frecuencia_normalizada in ["Mensual", "Bimestral", "Trimestral", "Semestral"]:
                    dia_max = int(periodo_control)
                    fecha_entrega = inicio.replace(day=min(dia_max, calendar.monthrange(inicio.year, inicio.month)[1]))
                elif frecuencia_normalizada == "Anual":
                    dia, mes = map(int, periodo_control.split("-"))
                    fecha_entrega = inicio.replace(day=dia, month=mes)
                else:
                    fecha_entrega = inicio

                fechas.append({
                    "fecha": inicio.strftime("%Y-%m-%d"),
                    "entrega": fecha_entrega.strftime("%Y-%m-%d")
                })

            inicio += incremento

        return fechas

    def insertar_filas_gestion_nuevas(self, id_clausula, filas_gestion):
        """
        Inserta solo las filas de gestión nuevas si la fecha de entrega no existe ya en la base de datos.
        """
        query_check = """
        SELECT 1 FROM clausulas_gestion 
        WHERE id_clausula = %s AND fecha_entrega = %s;
        """
        query_insert = """
        INSERT INTO clausulas_gestion (id_clausula, fecha_entrega, estado, registrado_por, fecha_creacion)
        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
        RETURNING id_gestion;
        """
        with self.connection.cursor() as cursor:
            for fila in filas_gestion:
                # Convertir fecha al formato correcto
                fecha_entrega = datetime.strptime(fila['fecha_entrega'], "%d/%m/%Y").strftime("%Y-%m-%d")

                # Verificar si la fecha ya existe para esta cláusula
                cursor.execute(query_check, (id_clausula, fecha_entrega))
                existe = cursor.fetchone()

                if not existe:  # Solo insertar si no existe
                    cursor.execute(query_insert, (
                        id_clausula,
                        fecha_entrega,
                        fila['estado'],
                        fila['registrado_por'],
                    ))
                    fila['id_gestion'] = cursor.fetchone()[0]
            self.connection.commit()
        return filas_gestion
    
    def actualizar_filas_gestion(self, filas_gestion):
        """
        Actualiza las filas de gestión existentes en la base de datos.
        Solo actualiza el campo `registrado_por` si hay cambios en los valores gestionados.
        """
        query_select = """
        SELECT fecha_radicado, numero_radicado, plan_accion, observacion, estado, adjunto, registrado_por
        FROM clausulas_gestion WHERE id_gestion = %s;
        """
        query_update = """
        UPDATE clausulas_gestion
        SET fecha_radicado = %s, numero_radicado = %s, plan_accion = %s, observacion = %s,
            estado = %s, adjunto = %s, registrado_por = CASE 
                WHEN %s THEN %s ELSE registrado_por END
        WHERE id_gestion = %s;
        """

        with self.connection.cursor() as cursor:
            for fila in filas_gestion:
                # Obtener valores actuales
                cursor.execute(query_select, (fila["id_gestion"],))
                current_values = cursor.fetchone()

                if not current_values:
                    continue  # Saltar si no se encontró el registro

                # Convertir fechas al mismo formato (YYYY-MM-DD)
                current_fecha_radicado = (
                    current_values[0].strftime("%Y-%m-%d") if current_values[0] else None
                )
                nueva_fecha_radicado = (
                    datetime.strptime(fila["fecha_radicado"], "%Y-%m-%d").strftime("%Y-%m-%d")
                    if fila["fecha_radicado"]
                    else None
                )

                # Comparar valores actuales con los enviados
                cambios_detectados = (
                    current_fecha_radicado != nueva_fecha_radicado or
                    current_values[1] != fila["numero_radicado"] or
                    current_values[2] != fila["plan_accion"] or
                    current_values[3] != fila["observacion"] or
                    current_values[4] != fila["estado"] or
                    current_values[5] != fila["adjunto"]
                )

                registrado_por_cambio = fila["registrado_por"] if cambios_detectados else None

                # Ejecutar la actualización
                cursor.execute(query_update, (
                    nueva_fecha_radicado,
                    fila["numero_radicado"],
                    fila["plan_accion"],
                    fila["observacion"],
                    fila["estado"],
                    fila["adjunto"],
                    cambios_detectados,  # True si hay cambios
                    registrado_por_cambio,  # Usuario actual si hay cambios
                    fila["id_gestion"],
                ))
            self.connection.commit()
        
    def obtener_filas_gestion_por_clausula(self, id_clausula):
        """
        Obtiene todas las filas de gestión asociadas a una cláusula específica.
        """
        query = """
        SELECT id_gestion, fecha_entrega, fecha_radicado, numero_radicado, plan_accion, observacion, 
            estado, registrado_por, fecha_creacion
        FROM clausulas_gestion
        WHERE id_clausula = %s
        ORDER BY fecha_entrega ASC;
        """
        with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, (id_clausula,))
            filas = cursor.fetchall()

            # Convertir fechas a formato DD/MM/YYYY
            for fila in filas:
                if fila["fecha_entrega"]:
                    fila["fecha_entrega"] = fila["fecha_entrega"].strftime("%d/%m/%Y")
                if fila["fecha_radicado"]:
                    fila["fecha_radicado"] = fila["fecha_radicado"].strftime("%d/%m/%Y")
                if fila.get("fecha_creacion"):
                    fila["fecha_creacion"] = fila["fecha_creacion"].strftime("%d/%m/%Y")
        return filas

    def obtener_clausula_nombre(self, id_clausula):
        query = "SELECT clausula FROM clausulas WHERE id = %s;"
        with self.connection.cursor() as cursor:
            cursor.execute(query, (id_clausula,))
            result = cursor.fetchone()
            if result:
                return result[0]
            else:
                raise ValueError(f"No se encontró el nombre de la cláusula con ID {id_clausula}")

    def obtener_clausula_contrato(self, id_clausula):
        query = "SELECT contrato_concesion FROM clausulas WHERE id = %s;"
        with self.connection.cursor() as cursor:
            cursor.execute(query, (id_clausula,))
            result = cursor.fetchone()
            if result:
                return result[0]
            else:
                raise ValueError(f"No se encontró el contrato asociado a la cláusula con ID {id_clausula}")

    def obtener_clausulas_con_entrega_estado(self):
        with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
            query = """
            SELECT 
                c.id, 
                subquery.fecha_entrega AS fecha_entrega_mas_reciente,
                subquery.estado AS estado_mas_reciente
            FROM clausulas c
            LEFT JOIN LATERAL (
                SELECT 
                    fecha_entrega, 
                    estado
                FROM clausulas_gestion
                WHERE id_clausula = c.id
                ORDER BY fecha_entrega DESC
                LIMIT 1
            ) subquery ON TRUE
            ORDER BY c.id ASC;
            """
            cursor.execute(query)
            clausulas = cursor.fetchall()

            # Convertir fechas a formato DD/MM/YYYY
            for clausula in clausulas:
                if clausula["fecha_entrega_mas_reciente"]:
                    fecha_original = clausula["fecha_entrega_mas_reciente"]
                    clausula["fecha_entrega_mas_reciente"] = fecha_original.strftime("%d/%m/%Y")

            #print("Resultados procesados:", clausulas)  # Verificar en consola
        return clausulas

    def obtener_opciones_estado(self):
        with self.connection.cursor() as cursor:
            query = """
            SELECT DISTINCT estado
            FROM clausulas_gestion
            WHERE estado IS NOT NULL
            ORDER BY estado;
            """
            cursor.execute(query)
            resultados = cursor.fetchall()
        return [fila[0] for fila in resultados]

    def crear_estructura_blob_storage(self, id_clausula, nombre_clausula, contrato, fechas_entrega):
        """
        Crea la estructura de carpetas en Blob Storage para una cláusula específica.
        """
        try:
            blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
            container_client = blob_service_client.get_container_client(CONTAINER_NAME)

            # Normalizar nombres para cumplir con los requisitos de Azure Storage
            def normalizar_nombre(nombre):
                # Reemplazar espacios por guiones, eliminar caracteres no permitidos
                return re.sub(r"[^a-zA-Z0-9\-]", "", nombre.replace(" ", "-"))

            carpeta_principal = f"{normalizar_nombre(str(id_clausula))}-{normalizar_nombre(nombre_clausula)}-{normalizar_nombre(contrato)}"
            
            for fecha_entrega in fechas_entrega:
                # Convertir fecha de entrega a objetos datetime
                fecha_obj = datetime.strptime(fecha_entrega, "%Y-%m-%d")
                anio = fecha_obj.year
                mes = f"{fecha_obj.month:02}"  # Mes en formato MM

                # Crear la ruta simulada para la carpeta
                ruta_carpeta = f"{carpeta_principal}/{anio}/{mes}/"

                # Subir un archivo vacío para simular el funcionamiento de la carpeta
                blob_client = container_client.get_blob_client(f"{ruta_carpeta}estructura.txt")
                blob_client.upload_blob(b"", overwrite=True)  # Archivo vacío para crear la estructura
        except Exception as e:
            print(f"Error creando la estructura en Blob Storage: {e}")
            raise

# REPORTES Y NOTIFICACIONES
# Recordatorio de Notificaciones
    def validar_conexion(self):
        """
        Verifica si la conexión a la base de datos sigue activa y la reestablece si está cerrada.
        """
        try:
            if self.connection.closed != 0:  # Si la conexión está cerrada (0 indica abierta)
                print("La conexión a la base de datos estaba cerrada. Reestableciendo conexión...")
                self.connection = psycopg2.connect(DATABASE_PATH)  # Reestablecer conexión
        except Exception as e:
            print(f"Error al validar o reestablecer la conexión: {e}")
            raise

    def generar_datos_recordatorio(self):
        """
        Obtiene los datos necesarios para generar el reporte Excel de las notificaciones por recordatorio.
        """
        self.validar_conexion()  # Asegurar que la conexión esté activa
        query_clausulas = """
        SELECT 
            c.id, c.clausula, c.contrato_concesion, c.frecuencia, c.responsable_entrega, r.correo
        FROM clausulas c
        LEFT JOIN responsable r ON c.responsable_entrega = r.responsable;
        """
        
        query_gestion = """
        SELECT id_clausula, fecha_entrega, estado
        FROM clausulas_gestion
        WHERE id_clausula = %s
        ORDER BY fecha_entrega DESC
        LIMIT 1; -- Traer solo la última fecha de entrega
        """
        
        query_procesos = """
        SELECT p.proceso, p.subproceso
        FROM clausula_proceso_subproceso cps
        JOIN procesos p ON cps.id_proceso = p.id_proceso
        WHERE cps.id_clausula = %s;
        """
        try:
            # Inicializar datos vacíos
            data = []

            fecha_hoy = datetime.today().date()  # Obtener la fecha de hoy

            with self.connection.cursor() as cursor:
                # Obtener los datos base
                cursor.execute(query_clausulas)
                clausulas = cursor.fetchall()

                # Iterar sobre las cláusulas
                for row in clausulas:
                    id_clausula = row[0]
                    
                    # Obtener la última fecha de entrega y su estado
                    cursor.execute(query_gestion, (id_clausula,))
                    gestion = cursor.fetchone()  # Solo una fila

                    if not gestion:
                        continue  # Si no hay datos en clausulas_gestion, pasa a la siguiente cláusula
                    
                    fecha_entrega = gestion[1]
                    estado = gestion[2]

                    # Obtener los procesos y subprocesos asociados
                    cursor.execute(query_procesos, (id_clausula,))
                    procesos = cursor.fetchall()

                    # Concatenar procesos y subprocesos en una cadena
                    procesos_texto = ", ".join(
                        [f"{proceso[0]} - {proceso[1]}" for proceso in procesos]
                    )

                    # Calcular la fecha de notificación
                    frecuencia = row[3]
                    dias_resta = 5 if frecuencia.lower() in ["mensual", "quincenal"] else 15
                    fecha_notificacion = fecha_entrega - timedelta(days=dias_resta)

                    # Filtrar solo las fechas de notificación que coinciden con hoy
                    if fecha_notificacion == fecha_hoy:
                        # Agregar los datos al resultado
                        data.append({
                            "ID": row[0],
                            "Clausula": row[1],
                            "Contrato Concesion": row[2],
                            "Frecuencia": frecuencia,
                            "Responsable Entrega": row[4],
                            "Correo": row[5],
                            "Proceso/Subproceso": procesos_texto,
                            "Fecha Entrega": fecha_entrega,
                            "Estado": estado,
                            "Fecha Notificacion": fecha_notificacion
                        })

            # Si no hay registros, inicializar con solo encabezados
            if not data:
                data.append({
                    "ID": None,
                    "Clausula": None,
                    "Contrato Concesion": None,
                    "Frecuencia": None,
                    "Responsable Entrega": None,
                    "Correo": None,
                    "Proceso/Subproceso": None,
                    "Fecha Entrega": None,
                    "Estado": None,
                    "Fecha Notificacion": None
                })

            return data
        except Exception as e:
            print(f"Error al generar los datos del reporte: {e}")
            raise
        
    def generar_reporte_recordatorio(self, output_path="temp"):
        """
        Genera el reporte de recordatorios y lo guarda en SharePoint.
        """
        self.validar_conexion()  # Asegurar que la conexión esté activa
        try:
            # Generar los datos
            data = self.generar_datos_recordatorio()

            # Crear el DataFrame
            df = pd.DataFrame(data)

            # Ruta temporal local
            os.makedirs(output_path, exist_ok=True)
            file_name = f"Notifica_Recordatorios_{datetime.now().strftime('%Y%m%d')}.xlsx"
            local_file_path = os.path.join(output_path, file_name)

            # Guardar el archivo Excel localmente
            df.to_excel(local_file_path, index=False)

            # Guardar en SharePoint
            sharepoint_folder = "5- Archivos Base/9- Jurídica y Seguros/Notifica_Recordatorios"
            self.guardar_en_sharepoint(local_file_path, sharepoint_folder, file_name)

            # Eliminar el archivo local después de subirlo
            os.remove(local_file_path)

        except Exception as e:
            print(f"Error al generar el reporte de recordatorios: {e}")
            raise

    def guardar_en_sharepoint(self, local_file_path, sharepoint_folder, file_name):
        """
        Sube un archivo a SharePoint usando autenticación de usuario y lo sobrescribe si ya existe.
        """        
        if not username or not password:
            raise Exception("Las credenciales de SharePoint no están configuradas correctamente.")

        try:
            # Autenticación con usuario y contraseña
            auth_context = AuthenticationContext(site_url)
            if not auth_context.acquire_token_for_user(username, password):
                raise Exception("Autenticación fallida: " + auth_context.get_last_error())

            # Conectar al sitio de SharePoint
            ctx = ClientContext(site_url, auth_context)

            # Ruta completa en SharePoint
            folder_url = f"Documentos compartidos/{sharepoint_folder}"
            target_file_url = f"{folder_url}/{file_name}"

            # Subir el archivo y sobrescribir si ya existe
            with open(local_file_path, "rb") as file_content:
                target_folder = ctx.web.get_folder_by_server_relative_url(folder_url)
                target_folder.upload_file(file_name, file_content).execute_query()

            #print(f"Archivo guardado en SharePoint: {target_file_url}")
        except Exception as e:
            print(f"Error al guardar el archivo en SharePoint: {e}")
            raise

    def enviar_correos_recordatorio(self):
        """
        Envía correos utilizando la información generada por la función `generar_datos_recordatorio`.
        """
        # Credenciales del correo remitente
        remitente = os.getenv("USUARIO_CORREO_JURIDICO")
        contrasena = os.getenv("CLAVE_CORREO_JURIDICO")

        # Configuración del servidor SMTP
        smtp_server = "smtp.office365.com"
        smtp_port = 587

        try:
            # Obtener los datos de recordatorio del día
            datos_recordatorio = self.generar_datos_recordatorio()

            if not datos_recordatorio or all(d["ID"] is None for d in datos_recordatorio):
                print("No hay recordatorios para enviar hoy.")
                return

            # Conectar al servidor SMTP
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()  # Iniciar conexión segura
            server.login(remitente, contrasena)

            # Enviar correos
            for recordatorio in datos_recordatorio:
                if recordatorio["ID"] is None:
                    continue  # Saltar encabezados o filas vacías
                
                # Formatear la fecha de entrega
                try:
                    fecha_entrega = recordatorio["Fecha Entrega"]
                    if isinstance(fecha_entrega, str):
                        fecha_entrega = datetime.strptime(fecha_entrega, "%Y-%m-%d")
                    fecha_entrega_formateada = fecha_entrega.strftime("%d/%m/%Y")
                except Exception as e:
                    print(f"Error al formatear la fecha de entrega: {e}")
                    fecha_entrega_formateada = recordatorio["Fecha Entrega"]

                destinatario = recordatorio["Correo"]
                asunto = f"Recordatorio: {recordatorio['ID']} - {recordatorio['Clausula']} (Contrato: {recordatorio['Contrato Concesion']}) - Entrega el {fecha_entrega_formateada}"
                
                cuerpo = (
                    f"<div style='background-color: #004080; color: white; padding: 10px; text-align: center; border-radius: 8px;'>"
                    f"<h2 style='margin: 0; font-size: 20px;'>Recordatorio del Cumplimiento de Obligaciones Jurídicas</h2>"
                    f"<p style='margin: 5px 0; font-size: 16px; font-style: italic; font-weight: bold;'>Consorcio Express S.A.S</p>"
                    f"</div>"
                    f"<div style='font-size: 14px; background-color: #f9f9f9; padding: 15px; border: 1px solid #ddd; border-radius: 8px; margin-top: 10px;'>"
                    f"<p>Estimado(a):<br><strong>{recordatorio['Responsable Entrega']}</strong>,</p>"
                    f"<p>Este es un recordatorio para la acreditación y cumplimiento de la cláusula:</p>"
                    f"<p style='font-weight: bold;'>"
                    f"{recordatorio['ID']} - {recordatorio['Clausula']} (Contrato: {recordatorio['Contrato Concesion']})</p>"
                    f"<p>Cuyo proceso y subproceso responsable son:</p>"
                    f"<p><strong>{recordatorio['Proceso/Subproceso']}</strong></p>"
                    f"<p>Frecuencia de cumplimiento: <strong>{recordatorio['Frecuencia']}</strong></p>"
                    f"<p>Fecha de entrega programada: <strong>{fecha_entrega_formateada}</strong></p>"
                    f"<p>Estado actual: <strong>{recordatorio['Estado']}</strong></p>"
                    f"<p style='margin-top: 20px;'>Por favor, recuerde actualizar el estado del cumplimiento con fecha, radicado y los soportes pertinentes a la plataforma de GestiónExpress.</p>"
                    f"<div style='text-align: center; margin-top: 20px;'>"
                    f"<a href='https://gestionconsorcioexpress.onrender.com/' style='"
                    f"display: inline-block; background-color: #004080; color: white; padding: 10px 20px; text-decoration: none; "
                    f"border-radius: 5px; font-size: 16px;'>Ir a GestiónExpress</a>"
                    f"</div>"
                    f"</div>"
                    f"<div style='margin-top: 20px; font-size: 12px; color: #666; text-align: center;'>"
                    f"<p>Dirección Jurídica - Consorcio Express S.A.S</p>"
                    f"<p>Dirección: Av. El Dorado #69-63, Bogotá, Colombia | Tel: +57 123 456789</p>"
                    f"<p>Este correo es informativo y no requiere respuesta.</p>"
                    f"</div>"
                )

                # Crear el correo
                mensaje = MIMEMultipart()
                mensaje["From"] = remitente
                mensaje["To"] = destinatario
                mensaje["Subject"] = asunto
                mensaje.attach(MIMEText(cuerpo, "html"))

                # Enviar el correo
                server.sendmail(remitente, destinatario, mensaje.as_string())
                print(f"Correo enviado a: {destinatario}")

            # Cerrar conexión con el servidor SMTP
            server.quit()
        except Exception as e:
            print(f"Error al enviar correos: {e}")
            raise

# Incumplimientos de Notificaciones
    def generar_datos_incumplimiento(self):
        """
        Obtiene los datos necesarios para generar el reporte de incumplimiento.
        """
        self.validar_conexion()  # Asegurar que la conexión esté activa
        query_clausulas = """
        SELECT 
            c.id, c.clausula, c.contrato_concesion, c.consecuencia, c.frecuencia, 
            c.responsable_entrega, r.correo
        FROM clausulas c
        LEFT JOIN responsable r ON c.responsable_entrega = r.responsable;
        """
        
        query_gestion = """
        SELECT id_clausula, fecha_entrega
        FROM clausulas_gestion
        WHERE id_clausula = %s AND estado = 'Incumplida' AND fecha_entrega < %s
        ORDER BY fecha_entrega ASC;
        """
        
        query_procesos = """
        SELECT p.proceso, p.subproceso
        FROM clausula_proceso_subproceso cps
        JOIN procesos p ON cps.id_proceso = p.id_proceso
        WHERE cps.id_clausula = %s;
        """
        
        try:
            data = []
            fecha_actual = datetime.today().date()

            with self.connection.cursor() as cursor:
                # Obtener los datos base de las cláusulas
                cursor.execute(query_clausulas)
                clausulas = cursor.fetchall()

                for row in clausulas:
                    id_clausula = row[0]

                    # Obtener las fechas incumplidas
                    cursor.execute(query_gestion, (id_clausula, fecha_actual))
                    fechas_incumplidas = cursor.fetchall()

                    if not fechas_incumplidas:
                        continue  # Si no hay fechas incumplidas, pasa a la siguiente cláusula

                    # Obtener los procesos y subprocesos asociados
                    cursor.execute(query_procesos, (id_clausula,))
                    procesos = cursor.fetchall()

                    procesos_texto = ", ".join(
                        [f"{proceso[0]} - {proceso[1]}" for proceso in procesos]
                    )

                    # Formatear las fechas incumplidas
                    fechas_formateadas = [
                        fecha[1].strftime("%d/%m/%Y") for fecha in fechas_incumplidas
                    ]

                    data.append({
                        "ID": row[0],
                        "Clausula": row[1],
                        "Contrato Concesion": row[2],
                        "Consecuencia": row[3],
                        "Frecuencia": row[4],
                        "Responsable Entrega": row[5],
                        "Correo": row[6],
                        "Proceso/Subproceso": procesos_texto,
                        "Fechas Incumplidas": fechas_formateadas
                    })

            return data
        except Exception as e:
            print(f"Error al generar los datos de incumplimiento: {e}")
            raise

    def enviar_correos_incumplimiento(self):
        """
        Envía correos con las fechas de entrega incumplidas por responsable.
        """
        remitente = os.getenv("USUARIO_CORREO_JURIDICO")
        contrasena = os.getenv("CLAVE_CORREO_JURIDICO")
        smtp_server = "smtp.office365.com"
        smtp_port = 587

        try:
            datos_incumplimiento = self.generar_datos_incumplimiento()

            if not datos_incumplimiento:
                print("No hay fechas de incumplimiento para enviar.")
                return

            # Agrupar datos por responsable
            responsables = {}
            for registro in datos_incumplimiento:
                responsable = registro["Responsable Entrega"]
                if responsable not in responsables:
                    responsables[responsable] = {
                        "Correo": registro["Correo"],
                        "Clausulas": []
                    }
                responsables[responsable]["Clausulas"].append(registro)

            # Conectar al servidor SMTP
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(remitente, contrasena)

            # Enviar correos
            for responsable, datos in responsables.items():
                destinatario = datos["Correo"]
                cuerpo = (
                    f"<div style='background-color: #004080; color: white; padding: 10px; text-align: center; border-radius: 8px;'>"
                    f"<h2 style='margin: 0; font-size: 20px;'>Reporte de Incumplimientos de Cláusulas Jurídicas</h2>"
                    f"<p style='margin: 5px 0 0; font-size: 16px; font-style: italic; font-weight: bold;'>Consorcio Express S.A.S</p>"
                    f"</div>"
                    f"<div style='font-size: 14px; background-color: #f9f9f9; padding: 15px; border: 1px solid #ddd; border-radius: 8px;'>"
                    f"<p>Estimado(a):<br><strong>{responsable}</strong></p>"
                    f"<p>A continuación, se informa las cláusulas jurídicas en estado de 'INCUMPLIMIENTO'. "
                    f"Es importante dar gestión y subsanar esta obligación de forma inmediata:</p>"
                )

                cuerpo += (
                    f"<table style='width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 12px;'>"
                    f"<thead style='background-color: #f2f2f2;'>"
                    f"<tr>"
                    f"<th style='border: 1px solid #ddd; padding: 8px; font-size: 14px;'>Cláusula</th>"
                    f"<th style='border: 1px solid #ddd; padding: 8px; font-size: 14px;'>Frecuencia</th>"
                    f"<th style='border: 1px solid #ddd; padding: 8px; font-size: 14px;'>Consecuencia</th>"
                    f"<th style='border: 1px solid #ddd; padding: 8px; font-size: 14px;'>Fechas Incumplidas</th>"
                    f"</tr>"
                    f"</thead>"
                    f"<tbody>"
                )

                for clausula in datos["Clausulas"]:
                    fechas_incumplidas = " - ".join([f"[{fecha}]" for fecha in clausula["Fechas Incumplidas"]])
                    cuerpo += (
                        f"<tr>"
                        f"<td style='border: 1px solid #ddd; padding: 8px; font-size: 12px;'><b>{clausula['ID']} - {clausula['Clausula']}</b></td>"
                        f"<td style='border: 1px solid #ddd; padding: 8px; font-size: 12px;'>{clausula['Frecuencia']}</td>"
                        f"<td style='border: 1px solid #ddd; padding: 8px; font-size: 12px;'>{clausula['Consecuencia']}</td>"
                        f"<td style='border: 1px solid #ddd; padding: 8px; font-size: 12px;'>{fechas_incumplidas}</td>"
                        f"</tr>"
                    )

                cuerpo += (
                    f"</tbody>"
                    f"</table>"
                    f"<p>Por favor, recuerde actualizar el estado del cumplimiento con fecha, radicado y los soportes pertinentes "
                    f"a la plataforma de GestiónExpress.</p>"
                    f"<div style='text-align: center; margin-top: 20px;'>"
                    f"<a href='https://gestionconsorcioexpress.onrender.com/' style='"
                    f"display: inline-block; background-color: #004080; color: white; padding: 10px 20px; text-decoration: none; "
                    f"border-radius: 5px; font-size: 16px;'>Ir a GestiónExpress</a>"
                    f"</div>"
                    f"</div>"
                    f"<div style='margin-top: 20px; font-size: 12px; color: #666; text-align: center;'>"
                    f"<p>Consorcio Express S.A.S</p>"
                    f"<p>Dirección: Av. El Dorado #69-63, Bogotá, Colombia | Tel: +57 123 456789</p>"
                    f"<p>Este correo es informativo y no requiere respuesta.</p>"
                    f"</div>"
                )

                mensaje = MIMEMultipart()
                mensaje["From"] = remitente
                mensaje["To"] = destinatario
                mensaje["Subject"] = "¡Importante! Reporte de Incumplimientos de Cláusulas Jurídicas"
                mensaje.attach(MIMEText(cuerpo, "html"))

                server.sendmail(remitente, destinatario, mensaje.as_string())
                print(f"Correo enviado a: {destinatario}")

            server.quit()

        except Exception as e:
            print(f"Error al enviar correos de incumplimiento: {e}")
            raise

    def close(self):
        self.connection.close()