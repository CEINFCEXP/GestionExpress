import pandas as pd
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
import os

# Cargar las variables de entorno desde .env
load_dotenv()
# Configuración de la conexión a PostgreSQL
DATABASE_PATH = os.getenv("DATABASE_PATH")
conexion = psycopg2.connect(DATABASE_PATH)

# Lee el archivo Excel
df = pd.read_excel('C:/Users/sergio.hincapie/Desktop/cargue_clausulas.xlsx', engine='openpyxl')

# Asegúrate de que los nombres de las columnas coincidan con los de la tabla 'clausulas'
df.columns = [
    'control', 'etapa', 'clausula', 'modificacion', 'contrato_concesion', 
    'tema', 'subtema', 'descripcion_clausula', 'tipo_clausula', 
    'norma_relacionada', 'consecuencia', 'frecuencia', 'periodo_control', 'inicio_cumplimiento', 
    'fin_cumplimiento', 'observacion', 'responsable_entrega'
]

# Inserción de registros en la tabla 'clausulas'
insert_query = """
    INSERT INTO clausulas (
        control, etapa, clausula, modificacion, contrato_concesion, 
        tema, subtema, descripcion_clausula, tipo_clausula, 
        norma_relacionada, consecuencia, frecuencia, periodo_control,
        inicio_cumplimiento, fin_cumplimiento, observacion, responsable_entrega
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

# Convierta el DataFrame a una lista de tuplas para insertar
records = [tuple(row) for row in df.values]

# Inserta los registros en la base de datos
with conexion:
    with conexion.cursor() as cursor:
        cursor.executemany(insert_query, records)

# Cierra la conexión
conexion.close()

print("Registros insertados exitosamente.")