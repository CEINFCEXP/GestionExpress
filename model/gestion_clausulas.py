import psycopg2
import json
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import os

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

            # Obtener el id de la cláusula recién creada
            clausula_id = cursor.fetchone()[0]
            
            # Procesar los procesos/subprocesos si se enviaron
            procesos_subprocesos = json.loads(clausula_data.get('procesos_subprocesos', '[]'))

            for ps in procesos_subprocesos:
                proceso = ps.get('proceso')
                subproceso = ps.get('subproceso')

                if proceso and subproceso:
                    # Obtener el id_proceso basado en el proceso y subproceso
                    id_proceso = self.obtener_id_proceso(proceso, subproceso)

                    if id_proceso:
                        # Insertar en la tabla auxiliar clausula_proceso_subproceso
                        query_insert_proceso = """
                        INSERT INTO clausula_proceso_subproceso (id_clausula, id_proceso) 
                        VALUES (%s, %s);
                        """
                        cursor.execute(query_insert_proceso, (clausula_id, id_proceso))
                    else:
                        raise ValueError(f"No se encontró el id_proceso para el proceso: {proceso} y subproceso: {subproceso}")

            # Confirmar la transacción
            self.connection.commit()


    def close(self):
        self.connection.close()