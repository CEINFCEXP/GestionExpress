import psycopg2
import pandas as pd
import os

# Ruta al archivo Excel
excel_path = os.path.abspath("C:/Users/sergio.hincapie/Desktop/Turnos CC.xlsx")

# Leer el archivo Excel
df = pd.read_excel(excel_path)

# Ruta absoluta al archivo de la base de datos
db_path = os.path.abspath("C:/Users/sergio.hincapie/OneDrive - Grupo Express/Gestión de la Operación/0 - Script Python/Asignación_Controles/centro_control.db")

# Conectar a la base de datos
conn = psycopg2.connect(db_path)
cursor = conn.cursor()

# Crear la tabla turnos si no existe
create_table_query = """
CREATE TABLE IF NOT EXISTS turnos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    turno TEXT NOT NULL,
    hora_inicio TEXT NOT NULL,
    hora_fin TEXT NOT NULL,
    detalles TEXT
);
"""
cursor.execute(create_table_query)

# Insertar los datos del DataFrame en la tabla turnos
for index, row in df.iterrows():
    cursor.execute(
        "INSERT INTO turnos (turno, hora_inicio, hora_fin, detalles) VALUES (%s, %s, %s, %s)",
        (str(row['turno']), str(row['hora_inicio']), str(row['hora_fin']), str(row['detalle']))
    )

# Confirmar los cambios
conn.commit()

# Consultar y mostrar los datos de la tabla turnos
cursor.execute("SELECT * FROM turnos")
rows = cursor.fetchall()

# Cerrar la conexión
conn.close()

# Mostrar los datos insertados
for row in rows:
    print(row)
