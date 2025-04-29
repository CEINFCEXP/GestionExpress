from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from model.gestion_clausulas import GestionClausulas

############################################################################################################
############################### TAREAS PROGRAMADAS GESTIÓN EXPRESS #########################################

class TareasProgramadasJuridico:

    def __init__(self):
        self.gestion = GestionClausulas()

    def calcular_y_actualizar_fechas_dinamicas(self):
        """
        Job para calcular y actualizar fechas dinámicas de todas las cláusulas.
        Este proceso recorre todas las cláusulas y actualiza las fechas dinámicas directamente en la base de datos.
        """
        try:
            print("Iniciando cálculo de fechas dinámicas: ", datetime.now())
            self.gestion.validar_conexion()  # Validar conexión al inicio

            # Obtener todas las cláusulas desde la base de datos
            clausulas = self.gestion.obtener_clausulas_job()

            for clausula in clausulas:
                print(f"Procesando cláusula ID: {clausula['id']}")

                # Calcular fechas dinámicas usando la lógica existente
                fechas_dinamicas = self.gestion.calcular_fechas_dinamicas(
                    clausula['inicio_cumplimiento'],
                    clausula['fin_cumplimiento'],
                    clausula['frecuencia'],
                    clausula['periodo_control']
                )
                print(f"Fechas dinámicas calculadas para cláusula ID {clausula['id']}: {fechas_dinamicas}")

                # **Obtener las fechas existentes en la BD antes de insertar**
                query_select = "SELECT fecha_entrega FROM clausulas_gestion WHERE id_clausula = %s;"
                with self.gestion.connection.cursor() as cursor:
                    cursor.execute(query_select, (clausula['id'],))
                    fechas_existentes = {row[0].strftime("%Y-%m-%d") for row in cursor.fetchall()}  # Convertir a conjunto
                
                # Obtener la fecha actual para calcular el estado
                fecha_actual = datetime.today().date()

                # Formatear las filas para `insertar_filas_gestion_nuevas`
                filas_gestion = []
                for f in fechas_dinamicas:
                    # Calcular el estado dinámicamente
                    fecha_entrega = datetime.strptime(f['entrega'], "%Y-%m-%d").date()
                    
                    # **Evitar insertar si la fecha ya existe en la BD**
                    if fecha_entrega.strftime("%Y-%m-%d") in fechas_existentes:
                        print(f"⚠️ Fecha {fecha_entrega.strftime('%d/%m/%Y')} ya existe. Se omite.")
                        continue
                    
                    # Calcular el estado dinámicamente
                    estado = self.gestion.calcular_estado(
                        fecha_entrega=fecha_entrega,
                        fecha_radicado=None,  # No hay fecha radicado para filas nuevas
                        fecha_actual=fecha_actual
                    )

                    # Agregar la fila formateada
                    filas_gestion.append({
                        "fecha_entrega": fecha_entrega.strftime("%d/%m/%Y"),  # Convertir formato
                        "estado": estado,  # Estado calculado dinámicamente
                        "registrado_por": "Sin Gestionar"  # Registrar autoría del job
                    })
                    
                # Insertar filas dinámicas en la base de datos (solo si hay nuevas)
                if filas_gestion:
                    self.gestion.insertar_filas_gestion_nuevas(clausula['id'], filas_gestion)
                    print(f"✅ {len(filas_gestion)} nuevas fechas insertadas para cláusula ID {clausula['id']}.")

            print("Fechas dinámicas actualizadas correctamente.")

        except Exception as e:
            print(f"Error en el cálculo de fechas dinámicas: {e}")

    def sincronizar_estados_filas_gestion(self):
        """
        Job para sincronizar estados dinámicos de las filas en clausulas_gestion.
        Este proceso verifica los estados actuales y los actualiza según las reglas de negocio.
        """
        try:
            print("Iniciando sincronización de estados: ", datetime.now())
            self.gestion.validar_conexion()  # Validar conexión al inicio

            # Obtener todas las filas de gestión desde la base de datos
            filas_gestion = self.gestion.obtener_todas_filas_gestion()

            for fila in filas_gestion:
                # Recalcular el estado usando la lógica existente
                nuevo_estado = self.gestion.calcular_estado(
                    fila['fecha_entrega'],
                    fila['fecha_radicado'],
                    datetime.today().date()
                )

                # Actualizar el estado en la base de datos si ha cambiado
                if nuevo_estado != fila['estado']:
                    self.gestion.actualizar_estado_fila(fila['id_gestion'], nuevo_estado)

            print("Estados sincronizados correctamente.")

        except Exception as e:
            print(f"Error en la sincronización de estados: {e}")

    def tarea_diaria_recordatorio(self):
        """
        Realiza las tareas diarias :
        1. Envía los correos de recordatorios proximos a vencer.
        """
        try:
            print("Iniciando envío automático de correos de recordatorio...")
            self.gestion.enviar_correos_recordatorio()
            print("Correos de recordatorio enviados exitosamente.")
        except Exception as e:
            print(f"Error en la tarea diaria de recordatorio: {e}")

    def tarea_semanal_incumplimientos(self):
        """
        Realiza la tarea semanal para enviar correos de incumplimiento.
        """
        try:
            print("Iniciando envío de correos de incumplimiento...")
            self.gestion.enviar_correos_incumplimiento() # Correos a los responsables
            self.gestion.enviar_correos_incumplimiento_direccion()  # Correo consolidado para Dirección Jurídica
            print("Correos de incumplimiento enviados exitosamente.")
        except Exception as e:
            print(f"Error en la tarea semanal de incumplimientos: {e}")
