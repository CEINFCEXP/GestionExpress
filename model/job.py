from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from model.gestion_clausulas import GestionClausulas

############################################################################################################
############################### TAREAS PROGRAMADAS MODULO JURIDICO #########################################

class TareasProgramadasJuridico:

    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone="America/Bogota")
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

                # Obtener la fecha actual para calcular el estado
                fecha_actual = datetime.today().date()

                # Formatear las filas para `insertar_filas_gestion_nuevas`
                filas_gestion = []
                for f in fechas_dinamicas:
                    # Calcular el estado dinámicamente
                    fecha_entrega = datetime.strptime(f['entrega'], "%Y-%m-%d").date()
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

                # Insertar filas dinámicas en la base de datos
                self.gestion.insertar_filas_gestion_nuevas(clausula['id'], filas_gestion)

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
            self.gestion.enviar_correos_incumplimiento()
            print("Correos de incumplimiento enviados exitosamente.")
        except Exception as e:
            print(f"Error en la tarea semanal de incumplimientos: {e}")

    def iniciar_scheduler(self):
        """
        Configura y arranca los jobs programados para el proceso Jurídico.
        """
        self.scheduler.add_job(self.calcular_y_actualizar_fechas_dinamicas, 'cron', hour=2, minute=0, id='job_calculo_fechas')
        self.scheduler.add_job(self.sincronizar_estados_filas_gestion, 'cron', hour=3, minute=0, id='job_sincronizacion_estados')
        self.scheduler.add_job(self.tarea_diaria_recordatorio, 'cron', hour=7, minute=30, id='job_tarea_diaria_recordatorio')
        self.scheduler.add_job(self.tarea_semanal_incumplimientos, 'cron', day_of_week='tue', hour=8, minute=0, id='job_tarea_semanal_incumplimientos')
        self.scheduler.start()
        print("Scheduler iniciado con los jobs configurados.")

# Instancia de la clase para tareas programadas
tareas_juridico = TareasProgramadasJuridico()
tareas_juridico.iniciar_scheduler()