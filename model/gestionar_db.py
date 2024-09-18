import psycopg2
from psycopg2 import OperationalError
from threading import Lock
from datetime import datetime, time
import pytz
from fastapi import HTTPException

DATABASE_PATH = "postgresql://gestionexpress:G3st10n3xpr3ss@serverdbcexp.postgres.database.azure.com:5432/gestionexpress" 
# Establecer la zona horaria de Colombia
colombia_tz = pytz.timezone('America/Bogota')

class HandleDB:
    _instance = None
    _lock = Lock()

    def __new__(cls): # Implementación del patrón Singleton para asegurar una única instancia de la clase HandleDB
        with cls._lock:
            if not cls._instance:
                cls._instance = super().__new__(cls)
                cls._instance._con = psycopg2.connect(DATABASE_PATH)
                cls._instance._cur = cls._instance._con.cursor()
            return cls._instance

    def get_all(self): # Método para obtener todos los registros de usuarios
        with self._lock:
            self._cur.execute("SELECT * FROM usuarios")
            return self._cur.fetchall()

    def get_only(self, username): 
        with self._lock:
            cur = self._con.cursor()  # Crear un nuevo cursor
            try:
                cur.execute("SELECT * FROM usuarios WHERE username = %s", (username,))
                result = cur.fetchone()
            finally:
                cur.close()  # Asegurarse de cerrar el cursor después de su uso
            return result
                
    def insert(self, data_user): # Método para insertar un nuevo usuario en la base de datos
        with self._lock:
            self._cur.execute("""
                INSERT INTO usuarios (nombres, apellidos, username, cargo, password_user)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                data_user["nombres"],
                data_user["apellidos"],
                data_user["username"],
                data_user["cargo"],
                data_user["password_user"]
            ))
            self._con.commit()

    def __del__(self): # Método para cerrar la conexión con la base de datos al finalizar el uso
        with self._lock:
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
