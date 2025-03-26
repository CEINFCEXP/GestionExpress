import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()
DATABASE_PATH = os.getenv("DATABASE_PATH")

class GestionChecklist:
    def __init__(self):
        try:
            self.connection = psycopg2.connect(DATABASE_PATH)
        except psycopg2.OperationalError as e:
            print(f"Error al conectar a la base de datos: {e}")
            raise e

    def cerrar_conexion(self):
        """Cierra la conexión a la base de datos si está abierta."""
        if self.connection:
            self.connection.close()

    def obtener_tipos_vehiculos(self):
        """Obtiene la lista de tipos de vehículos."""
        query = "SELECT id_tipo_vehiculo, nombre FROM checklist_tipo_vehiculo ORDER BY nombre ASC;"
        with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query)
            resultados = cursor.fetchall()
        return resultados

    def obtener_vehiculos(self):
        """Obtiene todos los vehículos registrados con el nombre del tipo de vehículo"""
        query = """
        SELECT v.placa, v.id_tipo_vehiculo, t.nombre AS tipo_vehiculo_nombre, v.marca, v.linea, v.modelo, v.estado
        FROM vehiculos v
        JOIN checklist_tipo_vehiculo t ON v.id_tipo_vehiculo = t.id_tipo_vehiculo
        ORDER BY v.placa ASC;
        """
        with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query)
            return cursor.fetchall()
        return resultados

    def crear_vehiculo(self, data):
        """Crea un nuevo vehículo en la base de datos"""
        query = """
        INSERT INTO vehiculos (placa, id_tipo_vehiculo, marca, linea, modelo)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING placa;
        """
        with self.connection.cursor() as cursor:
            try:
                cursor.execute(query, (data["placa"], data["id_tipo_vehiculo"], data["marca"], data["linea"], data["modelo"]))  # 👈 Ajuste aquí
                self.connection.commit()
                return {"message": "Vehículo registrado exitosamente", "placa": cursor.fetchone()[0]}
            except psycopg2.Error as e:
                self.connection.rollback()
                return {"error": f"Error al crear vehículo: {str(e)}"}

    def obtener_vehiculo_por_placa(self, placa):
        """Obtiene un vehículo específico por su placa"""
        query = """
        SELECT v.id AS id_vehiculo, v.placa, v.marca, v.linea, v.modelo, v.id_tipo_vehiculo, t.nombre AS tipo_vehiculo
        FROM vehiculos v
        JOIN checklist_tipo_vehiculo t ON v.id_tipo_vehiculo = t.id_tipo_vehiculo
        WHERE v.placa = %s;
        """
        with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, (placa,))
            vehiculo = cursor.fetchone()
        
        '''
        if vehiculo:
            print("Vehículo encontrado:", vehiculo)
        else:
            print("Vehículo NO encontrado.")
        '''
        
        return vehiculo

    def actualizar_vehiculo(self, placa, data):
        """Actualiza un vehículo por su placa"""
        query_update = """
        UPDATE vehiculos 
        SET id_tipo_vehiculo = %s, marca = %s, linea = %s, modelo = %s
        WHERE placa = %s;
        """
        with self.connection.cursor() as cursor:
            try:
                # Ejecutar la actualización con el ID del tipo de vehículo
                cursor.execute(query_update, (data["id_tipo_vehiculo"], data["marca"], data["linea"], data["modelo"], placa))
                self.connection.commit()
                return {"message": "Vehículo actualizado correctamente"}
            except psycopg2.Error as e:
                self.connection.rollback()
                return {"error": f"Error al actualizar vehículo: {str(e)}"}

    def inactivar_vehiculo(self, placa, nuevo_estado):
        """Cambia el estado de un vehículo en la base de datos."""
        query = "UPDATE vehiculos SET estado = %s WHERE placa = %s;"
        with self.connection.cursor() as cursor:
            try:
                cursor.execute(query, (nuevo_estado, placa))
                self.connection.commit()
                return {"message": f"Vehículo {'activado' if nuevo_estado == 1 else 'inactivado'} correctamente"}
            except psycopg2.Error as e:
                self.connection.rollback()
                return {"error": f"Error al cambiar el estado del vehículo: {str(e)}"}

    def buscar_vehiculos(self, query):
        """Busca vehículos activos que coincidan con la placa ingresada sin importar mayúsculas/minúsculas"""
        query_sql = """
            SELECT placa FROM vehiculos 
            WHERE estado = 1 AND placa ILIKE %s 
            ORDER BY placa ASC;
        """
        with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query_sql, (f"%{query}%",))
            resultados = cursor.fetchall()
        return resultados
     
    def obtener_tipos_documentos(self):
        """Consulta la lista de tipos de documentos en orden alfabético"""
        query = """
        SELECT id_tipo_documento, nombre 
        FROM checklist_tipo_documento
        ORDER BY nombre ASC
        """
        with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query)
            documentos = cursor.fetchall()
            return [{"id": doc["id_tipo_documento"], "nombre": doc["nombre"]} for doc in documentos]

    def obtener_componentes_por_tipo(self, id_tipo_vehiculo):
        """Obtiene los componentes para un tipo de vehículo"""
        query_sql = """
            SELECT id_componente, grupo, posicion, componente 
            FROM checklist_componentes 
            WHERE id_tipo_vehiculo = %s 
            ORDER BY grupo, posicion, componente;
        """
        with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query_sql, (id_tipo_vehiculo,))
            resultados = cursor.fetchall()
        return resultados

    def obtener_ultimo_checklist(self, id_vehiculo):
        """Obtiene el último checklist registrado para un vehículo"""
        query = """
        SELECT * FROM checklist_registro 
        WHERE id_vehiculo = %s 
        ORDER BY fecha_hora_registro DESC 
        LIMIT 1;
        """
        with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, (id_vehiculo,))
            return cursor.fetchone()

    def obtener_documentos_checklist(self, id_checklist):
        """Obtiene los documentos del checklist registrado"""
        query = """
        SELECT id_tipo_documento, estado, observaciones
        FROM checklist_documentos
        WHERE id_checklist_registro = %s;
        """
        with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, (id_checklist,))
            documentos = cursor.fetchall()
        return documentos if documentos else []

    def obtener_detalles_checklist(self, id_checklist):
        """Obtiene los detalles del checklist registrado"""
        query = """
        SELECT id_componente, estado, observaciones
        FROM checklist_detalle
        WHERE id_checklist_registro = %s;
        """
        with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, (id_checklist,))
            detalles = cursor.fetchall()
        return detalles if detalles else []

    def guardar_checklist_registro(self, registro):
        """Inserta un nuevo checklist en checklist_registro y devuelve el ID generado."""
        #print("✅ Guardando checklist_registro...")
        query = """
        INSERT INTO checklist_registro 
        (id_vehiculo, fecha_hora_registro, inicio_turno, fin_turno, km_odometro, 
        observaciones_generales, usuario_registro, fecha_guardado)
        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW() AT TIME ZONE 'America/Bogota')
        RETURNING id_checklist;
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, (
                registro.id_vehiculo, registro.fecha_hora_registro, registro.inicio_turno,
                registro.fin_turno, registro.km_odometro, registro.observaciones_generales,
                registro.usuario_registro
            ))
            id_checklist = cursor.fetchone()
            self.connection.commit()
        
        if id_checklist:
            return id_checklist[0]
        return None

    def guardar_checklist_documento(self, id_checklist, documento):
        """Inserta un documento asociado a un checklist."""
        query = """
        INSERT INTO checklist_documentos (id_checklist_registro, id_tipo_documento, estado, observaciones)
        VALUES (%s, %s, %s::BOOLEAN, %s);
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, (
                id_checklist,  
                documento.id_tipo_documento,
                documento.estado,
                documento.observaciones
            ))
            self.connection.commit()

    def guardar_checklist_detalle(self, id_checklist, detalle):
        """Inserta un detalle asociado a un checklist."""
        query = """
        INSERT INTO checklist_detalle (id_checklist_registro, id_componente, estado, observaciones)
        VALUES (%s, %s, %s::BOOLEAN, %s);
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, (
                id_checklist,  
                detalle.id_componente,
                detalle.estado,
                detalle.observaciones
            ))
            self.connection.commit()

