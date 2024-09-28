import psycopg2
from psycopg2 import OperationalError
from threading import Lock
from datetime import datetime, time
from bs4 import BeautifulSoup
import pandas as pd
import pytz
from fastapi import HTTPException

# Base de Datos POSTGRESQL en Azure (Cuenta: sergio.hincapie@ucentral.edu.co)
DATABASE_PATH = "postgresql://gestionexpress:G3st10n3xpr3ss@serverdbcexp.postgres.database.azure.com:5432/gestionexpress" 
# Establecer la zona horaria de Colombia
colombia_tz = pytz.timezone('America/Bogota')

class HandleDB:
    _instance = None
    _lock = Lock()

    def __new__(cls):  # Implementación del patrón Singleton para asegurar una única instancia de la clase HandleDB
        with cls._lock:
            if not cls._instance:
                cls._instance = super().__new__(cls)
                cls._instance._con = cls._create_connection()  # Usar el método estático para crear la conexión
                cls._instance._cur = cls._instance._con.cursor()
            return cls._instance
        
    @staticmethod
    def _create_connection():
        return psycopg2.connect(DATABASE_PATH)  # Reemplaza con la cadena de conexión a tu base de datos PostgreSQL

    def _check_connection(self):
        if self._con.closed:  # Verifica si la conexión está cerrada
            self._con = self._create_connection()  # Reabre la conexión
            self._cur = self._con.cursor()  # Reasigna el cursor

    def get_all(self):  # Método para obtener todos los registros de usuarios
        with self._lock:
            self._check_connection()  # Verifica la conexión antes de usarla
            self._cur.execute("SELECT * FROM usuarios")
            return self._cur.fetchall()

    def get_only(self, username):
        with self._lock:
            self._check_connection()  # Verifica la conexión antes de usarla
            cur = self._con.cursor()  # Crear un nuevo cursor
            try:
                cur.execute("SELECT * FROM usuarios WHERE username = %s", (username,))
                result = cur.fetchone()
            except Exception as e:
                self._con.rollback()  # Si ocurre un error, hacemos rollback de la transacción
                raise e  # Opcionalmente, lanzar el error para depuración
            finally:
                cur.close()  # Asegúrate de cerrar el cursor después de su uso
            return result

    def insert(self, data_user):  # Método para insertar un nuevo usuario en la base de datos
        with self._lock:
            self._check_connection()  # Verifica la conexión antes de usarla
            self._cur.execute("""
                INSERT INTO usuarios (nombres, apellidos, username, rol, rol_storage, password_user, estado)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                data_user["nombres"],
                data_user["apellidos"],
                data_user["username"],
                data_user["rol"],
                data_user["rol_storage"],
                data_user["password_user"],
                1 # Siempre se insertará como 'activo' con estado 1
            ))
            self._con.commit()

    def insert_role(self, role_data):  # Método para insertar un nuevo rol en la tabla 'roles'
        with self._lock:
            self._check_connection()  # Verifica la conexión antes de usarla
            self._cur.execute("""
                INSERT INTO roles (nombre_rol, pantallas_asignadas)
                VALUES (%s, %s)
            """, (
                role_data["nombre_rol"],
                role_data["pantallas_asignadas"]
            ))
            self._con.commit()

    def get_all_roles(self):
        try:
            with self._lock:
                self._check_connection()
                self._cur.execute("SELECT id_rol, nombre_rol, pantallas_asignadas FROM roles ORDER BY id_rol ASC")
                return self._cur.fetchall()
        except psycopg2.OperationalError as e:
            self._con.rollback()  # Si ocurre un error, realiza un rollback
            print(f"Error de conexión: {str(e)}")
            raise e  # Opcionalmente, relanzar el error o intentar reconectar

    def get_pantallas_from_layout(self, layout_path):
        with open(layout_path, 'r', encoding='utf-8') as f:
            layout_html = f.read()
        soup = BeautifulSoup(layout_html, 'html.parser')
        pantallas = [link.text.strip() for link in soup.select(".sidebar .nav-link")]
        return pantallas
        
    def get_role_by_id(self, role_id):
        with self._lock:
            self._check_connection()
            self._cur.execute("SELECT id_rol, nombre_rol, pantallas_asignadas FROM roles WHERE id_rol = %s", (role_id,))
            rol_data = self._cur.fetchone()
            if rol_data and rol_data[2]:  # Validar que `pantallas_asignadas` no esté vacío
                return rol_data
            else:
                return None

    def update_role(self, role_id, role_name, permissions):
        with self._lock:
            self._check_connection()
            self._cur.execute("""
                UPDATE roles SET nombre_rol = %s, pantallas_asignadas = %s WHERE id_rol = %s
            """, (role_name, permissions, role_id))
            self._con.commit()

    def delete_role(self, role_id):
        with self._lock:
            self._check_connection()
            try:
                self._cur.execute("DELETE FROM roles WHERE id_rol = %s", (role_id,))
                self._con.commit()  # Realiza commit para confirmar la transacción
            except Exception as e:
                self._con.rollback()  # Realiza rollback en caso de error
                raise e

    def get_pantallas_by_role(self, role_id):
        """Consulta las pantallas asignadas a un rol en la base de datos."""
        with self._lock:
            self._check_connection()
            self._cur.execute("SELECT pantallas_asignadas FROM roles WHERE id_rol = %s", (role_id,))
            result = self._cur.fetchone()
            if result:
                return result[0].split(',')  # Convertimos la cadena a lista
            return []
        
    def get_all_users(self):
        with self._lock:
            self._check_connection()
            # Asegurémonos de obtener todos los campos
            self._cur.execute("SELECT id, nombres, apellidos, username, rol, estado, rol_storage FROM usuarios ORDER BY id ASC")
            usuarios = self._cur.fetchall()
            # print("Usuarios obtenidos de la base de datos:", usuarios)  # Debugging
            return usuarios
      
    def get_user_by_id(self, user_id):
        with self._lock:
            self._check_connection()
            self._cur.execute("SELECT id, nombres, apellidos, username, rol, estado, rol_storage FROM usuarios WHERE id = %s", (user_id,))
            usuario = self._cur.fetchone()
            if usuario:
                return {
                    "id": usuario[0],
                    "nombres": usuario[1],
                    "apellidos": usuario[2],
                    "username": usuario[3],
                    "rol": usuario[4],
                    "estado": usuario[5],
                    "rol_storage": usuario[6]
                }
            return None
           
    def update_user(self, user_id, data):
        with self._lock:
            self._check_connection()

            # Comienza a construir la consulta SQL
            query = """
                UPDATE usuarios SET nombres = %s, apellidos = %s, username = %s, rol = %s, estado = %s, rol_storage = %s
            """
            params = [data['nombres'], data['apellidos'], data['username'], data['rol'], data['estado'], data['rol_storage']]

            # Solo agrega la contraseña si está presente en los datos
            if "password_user" in data and data["password_user"]:
                query += ", password_user = %s"
                params.append(data["password_user"])
            
            # Finaliza la consulta SQL
            query += " WHERE id = %s"
            params.append(user_id)

            self._cur.execute(query, params)
            self._con.commit()
                
    def inactivate_user(self, user_id):
        with self._lock:
            self._check_connection()
            self._cur.execute("""
                UPDATE usuarios SET estado = 0 WHERE id = %s
            """, (user_id,))
            self._con.commit()
    
    # Conexión Licencias Power BI
    def fetch_one(self, query, values=None):
        with self._lock:
            self._check_connection()  # Verificar la conexión
            try:
                self._cur.execute(query, values)  # Ejecutar la consulta con parámetros
                return self._cur.fetchone()  # Obtener un solo resultado
            except Exception as e:
                self._con.rollback()  # Hacer rollback si hay un error
                raise e  # Lanzar el error

    # Conexiones Licencias Power BI
    def fetch_all(self, query, params=None):
        with self._lock:
            self._check_connection()
            try:
                if params:
                    self._cur.execute(query, params)
                else:
                    self._cur.execute(query)
                return self._cur.fetchall()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error fetching data: {str(e)}")

    def __del__(self):  # Método para cerrar la conexión con la base de datos al finalizar el uso
        with self._lock:
            if not self._con.closed:
                self._con.close()

class Cargue_Controles:
    def __init__(self):
        self.database_path = "postgresql://gestionexpress:G3st10n3xpr3ss@serverdbcexp.postgres.database.azure.com:5432/gestionexpress"
        self.conn = psycopg2.connect(self.database_path)
        self.cursor = self.conn.cursor()
        
    def borrar_tablas(self, tablas_a_borrar):
        try:
            if 'planta' in tablas_a_borrar:
                self.cursor.execute('DELETE FROM planta')
            if 'supervisores' in tablas_a_borrar:
                self.cursor.execute('DELETE FROM supervisores')
            if 'turnos' in tablas_a_borrar:
                self.cursor.execute('DELETE FROM turnos')
            if 'controles' in tablas_a_borrar:
                self.cursor.execute('DELETE FROM controles')
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            print(f"Error al borrar las tablas: {str(e)}")
            raise

    def cargar_datos(self, data):
        # Crear una lista de las tablas a borrar según las hojas seleccionadas
        tablas_a_borrar = []
        if 'planta' in data:
            tablas_a_borrar.append('planta')
        if 'supervisores' in data:
            tablas_a_borrar.append('supervisores')
        if 'turnos' in data:
            tablas_a_borrar.append('turnos')
        if 'controles' in data:
            tablas_a_borrar.append('controles')

        # Borrar solo las tablas seleccionadas
        self.borrar_tablas(tablas_a_borrar)

        print("Iniciando la carga de datos...")

        if 'planta' in data:
            self._cargar_planta(data['planta'])
        if 'supervisores' in data:
            self._cargar_supervisores(data['supervisores'])
        if 'turnos' in data:
            self._cargar_turnos(data['turnos'])
        if 'controles' in data:
            self._cargar_controles(data['controles'])

        print("Datos cargados exitosamente.")
        self.conn.close()

    def _cargar_planta(self, planta_data):
        try:
            for row in planta_data:
                print(f"Insertando o actualizando en planta: {row}")
                self.cursor.execute('''
                    INSERT INTO planta (cedula, nombre) VALUES (%s, %s)
                    ON CONFLICT(cedula) DO UPDATE SET nombre=excluded.nombre
                ''', (row['cedula'], row['nombre']))
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            print(f"Error al cargar los datos de planta: {str(e)}")
            raise
        
    def _cargar_supervisores(self, supervisores_data):
        try:
            for row in supervisores_data:
                print(f"Insertando o actualizando en supervisores: {row}")
                self.cursor.execute('''
                    INSERT INTO supervisores (cedula, nombre) VALUES (%s, %s)
                    ON CONFLICT(cedula) DO UPDATE SET nombre=excluded.nombre
                ''', (row['cedula'], row['nombre']))
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            print(f"Error al cargar los datos de supervisores: {str(e)}")
            raise
        
    def _cargar_turnos(self, turnos_data):
        try:
            for row in turnos_data:
                print(f"Insertando o actualizando en turnos: {row}")
                self.cursor.execute('''
                    INSERT INTO turnos (turno, hora_inicio, hora_fin, detalles)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT(turno) DO UPDATE SET hora_inicio = excluded.hora_inicio, hora_fin = excluded.hora_fin, detalles = excluded.detalles
                ''', (str(row['turno']), str(row['hora_inicio']), str(row['hora_fin']), str(row['detalles'])))
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            print(f"Error al cargar los datos de turnos: {str(e)}")
            raise

    def _cargar_controles(self, controles_data):
        batch_size = 450  # Tamaño del lote
        retries = 10  # Número de reintentos
        delay = 1  # Retraso entre reintentos en segundos

        for i in range(0, len(controles_data), batch_size):
            batch = controles_data[i:i + batch_size]
            for _ in range(retries):
                try:
                    conn = psycopg2.connect(self.database_path)
                    cursor = conn.cursor()

                    for row in batch:
                        print(f"Insertando o actualizando en controles: {row}")
                        cursor.execute('''
                            INSERT INTO controles (concesion, puestos, control, ruta, linea, admin, cop, tablas) 
                            VALUES (%s, %s, %s, %s, %s, %s,%s, %s)
                            ON CONFLICT(id) DO UPDATE SET concesion = excluded.concesion, puestos = excluded.puestos, ruta = excluded.ruta, linea = excluded.linea, admin = excluded.admin, cop = excluded.cop, tablas = excluded.tablas
                        ''', (row['concesion'], row['puestos'], row['control'], row['ruta'], row['linea'], row['admin'], row['cop'], row['tablas']))
                    
                    conn.commit()  # Hacer commit si todo va bien
                    break  # Salir del ciclo de reintentos si todo es exitoso

                except psycopg2.OperationalError as e:
                    # Manejo de errores específicos
                    print(f"Error de conexión: {str(e)}, reintentando...")
                    time.sleep(delay)  # Esperar antes de reintentar

                except Exception as e:
                    # Manejo de errores generales
                    conn.rollback()  # Hacer rollback en caso de error
                    print(f"Error al cargar los datos de controles: {str(e)}")
                    raise

                finally:
                    if conn:
                        conn.close()  # Asegurar que la conexión siempre se cierra

            else:
                raise psycopg2.OperationalError("No se pudo desbloquear la base de datos después de varios intentos")                 
               
class Cargue_Asignaciones:
    def __init__(self):
        self.database_path = DATABASE_PATH

    def procesar_asignaciones(self, assignments, user_session):
        processed_data = []
        try:
            conn = psycopg2.connect(self.database_path, connect_timeout=30)
            cursor = conn.cursor()

            # Recupera todos los controles en una sola consulta y los guarda en un diccionario
            cursor.execute("SELECT ruta, linea, cop FROM controles")
            controles = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}

            for asignacion in assignments:
                rutas = asignacion['rutas_asociadas'].split(',')
                for ruta in rutas:
                    if asignacion['turno'] in ["AUSENCIA", "DESCANSO", "VACACIONES", "OTRAS TAREAS"]:
                        concesion = control = linea = cop = "NO APLICA"
                        ruta = "NO APLICA"
                    else:
                        # Obtén la información del control de la ruta en el diccionario
                        linea, cop = controles.get(ruta.strip(), ("", ""))
                        concesion = asignacion['concesion']
                        control = asignacion['control']
                        
                    processed_data.append({
                        'fecha': asignacion['fecha'],
                        'cedula': asignacion['cedula'],
                        'nombre': asignacion['nombre'],
                        'turno': asignacion['turno'],
                        'h_inicio': asignacion['hora_inicio'],
                        'h_fin': asignacion['hora_fin'],
                        'concesion': concesion,
                        'control': control,
                        'ruta': ruta.strip() if asignacion['turno'] not in ["AUSENCIA", "DESCANSO", "VACACIONES", "OTRAS TAREAS"] else "NO APLICA",
                        'linea': linea,
                        'cop': cop,
                        'observaciones': asignacion['observaciones'],
                        'usuario_registra': user_session['username'],
                        'registrado_por': f"{user_session['nombres']} {user_session['apellidos']}",
                        'fecha_hora_registro': datetime.now(colombia_tz).strftime("%d-%m-%Y %H:%M:%S"),
                        'puestosSC': int(asignacion.get('puestosSC', 0)),
                        'puestosUQ': int(asignacion.get('puestosUQ', 0)),
                        'cedula_enlace': asignacion['cedula_enlace'],
                        'nombre_supervisor_enlace': asignacion['nombre_supervisor_enlace']
                    })

            conn.close()
        except psycopg2.Error as e:
            print(f"Error al procesar asignaciones: {e}")
        return processed_data

    def cargar_asignaciones(self, processed_data):
        try:
            conn = psycopg2.connect(self.database_path, connect_timeout=30)
            cursor = conn.cursor()

            # Fase de eliminación en lote (en lugar de hacerlo uno por uno)
            delete_conditions = [(data['fecha'], data['cedula'], data['turno'], data['h_inicio'], data['h_fin'], data['control'])
                                 for data in processed_data]
            cursor.executemany('''
                DELETE FROM asignaciones
                WHERE fecha = %s AND cedula = %s AND turno = %s AND h_inicio = %s AND h_fin = %s AND control = %s
            ''', delete_conditions)

            print(f"Registros eliminados para las asignaciones.")

            # Fase de inserción en lote
            insert_values = [
                (data['fecha'], data['cedula'], data['nombre'], data['turno'], data['h_inicio'], data['h_fin'],
                 data['concesion'], data['control'], ruta.strip(), data['linea'], data['cop'], data['observaciones'],
                 data['usuario_registra'], data['registrado_por'], data['fecha_hora_registro'], data['puestosSC'], 
                 data['puestosUQ'], data['cedula_enlace'], data['nombre_supervisor_enlace'])
                for data in processed_data for ruta in data['ruta'].split(',')
            ]

            cursor.executemany('''
                INSERT INTO asignaciones (fecha, cedula, nombre, turno, h_inicio, h_fin, concesion, control, ruta, linea, cop, observaciones, usuario_registra, registrado_por, fecha_hora_registro, puestosSC, puestosUQ, cedula_enlace, nombre_supervisor_enlace)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', insert_values)

            # Confirmar la transacción
            conn.commit()
            return {"status": "success", "message": "Asignaciones guardadas exitosamente."}

        except psycopg2.Error as e:
            conn.rollback()
            print(f"Error al guardar asignaciones: {e}")
            raise HTTPException(status_code=500, detail=f"Error al guardar asignaciones: {e}")

        finally:
            conn.close()  # Cerrar la conexión
            
class CargueLicenciasBI:
    def __init__(self, db_conn):
        self.conn = db_conn
        self.cursor = self.conn.cursor()

    def cargar_licencias_excel(self, file_path):
        try:
            # Leer el archivo Excel
            df = pd.read_excel(file_path)

            # Validar si las columnas necesarias están presentes
            if not set(['cedula', 'nombre', 'correo_corporativo', 'grupo', 'licencia_bi', 'contraseña_licencia']).issubset(df.columns):
                raise ValueError("El archivo Excel debe contener las columnas: 'cedula', 'nombre', 'correo_corporativo', 'grupo', 'licencia_bi' y 'contraseña_licencia'.")

            # Insertar o actualizar los datos en la tabla licencias_bi
            for _, row in df.iterrows():
                self.cursor.execute('''
                    INSERT INTO licencias_bi (cedula, nombre, correo_corporativo, grupo, licencia_bi, contraseña_licencia)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (cedula) DO UPDATE
                    SET nombre = EXCLUDED.nombre, correo_corporativo = EXCLUDED.correo_corporativo,
                        grupo = EXCLUDED.grupo, licencia_bi = EXCLUDED.licencia_bi, contraseña_licencia = EXCLUDED.contraseña_licencia
                ''', (
                    row['cedula'], row['nombre'], row['correo_corporativo'], row['grupo'],
                    row['licencia_bi'], row['contraseña_licencia']
                ))

            # Hacer commit a la base de datos
            self.conn.commit()
            return {"message": "Licencias cargadas exitosamente."}

        except Exception as e:
            self.conn.rollback()
            raise HTTPException(status_code=400, detail=f"Error al cargar el archivo Excel: {str(e)}")

class Cargue_Roles_Blob_Storage:
    _instance = None
    _lock = Lock()  # Para manejar la concurrencia en la base de datos

    def __new__(cls):
        with cls._lock:
            if not cls._instance:
                cls._instance = super().__new__(cls)
                cls._instance._con = cls._create_connection()  # Crear la conexión a la base de datos
                cls._instance._cur = cls._instance._con.cursor()
            return cls._instance

    @staticmethod # Método para crear la conexión a la base de datos
    def _create_connection():
        return psycopg2.connect(DATABASE_PATH)

    def _check_connection(self): # Verifica si la conexión está activa
        if not hasattr(self, '_con') or self._con.closed:  # Asegura que la conexión existe y está abierta
            self._con = self._create_connection()
            self._cur = self._con.cursor()

    def insert_roles_storage(self, role_data):
        with self._lock:
            self._check_connection()
            try:
                self._cur.execute("""
                    INSERT INTO roles_storage (nombre_rol_storage, contenedores_asignados)
                    VALUES (%s, %s)
                """, (
                    role_data["nombre_rol_storage"],
                    ','.join(role_data["contenedores_asignados"])  # Convertimos la lista a una cadena
                ))
                self._con.commit()
            except Exception as e:
                self._con.rollback()  # Si hay un error, hacemos rollback
                raise e

    def get_all_roles_storage(self): # Método para obtener todos los roles de storage en la tabla roles_storage
        with self._lock:
            self._check_connection()
            self._cur.execute("SELECT id_rol_storage, nombre_rol_storage, contenedores_asignados FROM roles_storage ORDER BY id_rol_storage ASC")
            return self._cur.fetchall()

    def get_role_storage_by_id(self, role_storage_id): # Método para obtener un rol específico por ID
        with self._lock:
            self._check_connection()
            self._cur.execute("SELECT id_rol_storage, nombre_rol_storage, contenedores_asignados FROM roles_storage WHERE id_rol_storage = %s", (role_storage_id,))
            role_data = self._cur.fetchone()
            if role_data:
                return {
                    "id_rol_storage": role_data[0],
                    "nombre_rol_storage": role_data[1],
                    "contenedores_asignados": role_data[2].split(',')  # Convertimos la cadena a lista
                }
            return None

    def update_role_storage(self, role_storage_id, role_name, contenedores_asignados): # Método para actualizar un rol en la tabla roles_storage
        with self._lock:
            self._check_connection()
            try:
                self._cur.execute("""
                    UPDATE roles_storage
                    SET nombre_rol_storage = %s, contenedores_asignados = %s
                    WHERE id_rol_storage = %s
                """, (role_name, ','.join(contenedores_asignados), role_storage_id))
                self._con.commit()
            except Exception as e:
                self._con.rollback()  # Si hay un error, hacemos rollback
                raise e

    def delete_role_storage(self, role_storage_id): # Método para eliminar un rol de storage por ID
        with self._lock:
            self._check_connection()
            try:
                self._cur.execute("DELETE FROM roles_storage WHERE id_rol_storage = %s", (role_storage_id,))
                self._con.commit()
            except Exception as e:
                self._con.rollback()
                raise e
