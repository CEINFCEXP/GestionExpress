import psycopg2
import json
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta, date

# Cargar las variables de entorno desde .env
load_dotenv()
DATABASE_PATH = os.getenv("DATABASE_PATH")

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
            cursor.execute("SELECT DISTINCT tipo_clausula FROM tipo_clausulas;")
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
            cursor.execute("SELECT DISTINCT frecuencia FROM frecuencia;")
            frecuencias = cursor.fetchall()
        return frecuencias
    
    def obtener_opciones_responsables(self):
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT DISTINCT responsable FROM responsable;")
            responsables = cursor.fetchall()
        return responsables    

    def obtener_clausulas_filtradas(self, control=None, etapa=None, clausula=None, concesion=None, buscar=None):
        query = """
        SELECT id, control, etapa, clausula, contrato_concesion, tema, descripcion_clausula, 
            tipo_clausula, frecuencia
        FROM clausulas
        WHERE (%s IS NULL OR control = %s)
        AND (%s IS NULL OR etapa = %s)
        AND (%s IS NULL OR clausula = %s)
        AND (%s IS NULL OR contrato_concesion = %s)
        AND (%s IS NULL OR tema ILIKE %s OR descripcion_clausula ILIKE %s)
        ORDER BY id ASC;
        """
        with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, (control, control, etapa, etapa, clausula, clausula, concesion, concesion, buscar, f"%{buscar}%", f"%{buscar}%"))
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

        if frecuencia_normalizada not in delta and frecuencia_normalizada not in ["Única vez", "No aplica", "Diario", "Quincenal"]:
            raise ValueError(f"Frecuencia no válida: {frecuencia}")

        incremento = delta.get(frecuencia_normalizada, None)

        # Manejo especial para 'No aplica'
        if frecuencia_normalizada == "No aplica":
            return fechas  # Retorna lista vacía

        # Manejo especial para 'Única vez'
        if frecuencia_normalizada == "Única vez":
            if isinstance(periodo_control, str):
                try:
                    fecha_unica = datetime.strptime(periodo_control, "%Y-%m-%d")
                except ValueError:
                    raise ValueError(f"Formato de periodo_control inválido para 'Única vez': {periodo_control}")
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
            # Normalizar el día configurado (quitar espacios y convertir a minúsculas para mayor robustez)
            dia_configurado = periodo_control.strip().lower()  # Ejemplo: "MIERCOLES" -> "miercoles"

            # Diccionario para convertir nombres de días al formato de calendar
            dias_semana = {
                "lunes": "Monday", "martes": "Tuesday", "miercoles": "Wednesday",
                "jueves": "Thursday", "viernes": "Friday", "sabado": "Saturday", "domingo": "Sunday"
            }
            
            if dia_configurado not in dias_semana:
                raise ValueError(f"El día configurado en periodo_control no es válido: {dia_configurado}")

            dia_configurado_en_ingles = dias_semana[dia_configurado]  # Convertir al formato esperado

            fecha_entrega = inicio  # Comienza desde la fecha de inicio de cumplimiento
            dias_incremento = timedelta(days=1)
            dias_por_ciclo = 14  # Ciclo de quincena (cada 2 semanas)

            # Avanzar hasta el primer día configurado después de la fecha de inicio
            while calendar.day_name[fecha_entrega.weekday()] != dia_configurado_en_ingles:
                fecha_entrega += dias_incremento

            # Generar fechas hasta la fecha fin o la fecha actual (lo que sea menor)
            while fecha_entrega <= min(fecha_actual, fin):
                fechas.append({
                    "fecha": fecha_entrega.strftime("%Y-%m-%d"),
                    "entrega": fecha_entrega.strftime("%Y-%m-%d")
                })
                # Incrementar por 14 días para llegar al siguiente ciclo quincenal
                fecha_entrega += timedelta(days=dias_por_ciclo)

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


    def close(self):
        self.connection.close()