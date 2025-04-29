import psycopg2
from psycopg2.extras import RealDictCursor
import os

DATABASE_PATH = os.getenv("DATABASE_PATH")

class ReportBIGestion:
    def __init__(self):
        try:
            self.connection = psycopg2.connect(DATABASE_PATH)
        except psycopg2.OperationalError as e:
            print(f"Error al conectar a la base de datos: {e}")
            raise e

    def obtener_reportes(self):
        """
        Consulta la tabla 'reportbi' para obtener los grupos y reportes disponibles.
        """
        query = """
        SELECT id, workspacename, itemname
        FROM reportbi
        ORDER BY workspacename, itemname;
        """
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query)
                result = cursor.fetchall()

            # Organizar los datos por grupo (workspacename)
            grouped_reports = {}
            for row in result:
                workspace = row["workspacename"]
                if workspace not in grouped_reports:
                    grouped_reports[workspace] = []
                grouped_reports[workspace].append({
                    "report_id": row["id"],  # Solo pasamos el ID, no la URL
                    "ItemName": row["itemname"]
                })

            return grouped_reports
        except Exception as e:
            print(f"Error al consultar la tabla reportbi: {e}")
            return {}

    def obtener_url_bi(self, report_id):
        """
        Obtiene la URL del informe según su ID.
        """
        query = "SELECT weburl FROM reportbi WHERE id = %s"
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, (report_id,))
                result = cursor.fetchone()
                return result["weburl"] if result else None
        except Exception as e:
            print(f"Error al obtener la URL del informe: {e}")
            return None

    def close(self):
        self.connection.close()
