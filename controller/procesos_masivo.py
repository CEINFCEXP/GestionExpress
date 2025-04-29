import sys
import os
import pandas as pd
from dotenv import load_dotenv

# Agregar ruta base al sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from model.gestion_clausulas import GestionClausulas

# Cargar variables de entorno
load_dotenv()

# Ruta del archivo Excel
archivo_excel = "C:/Users/sergio.hincapie/Desktop/procesos.xlsx"
df = pd.read_excel(archivo_excel)

# Inicializar lógica de cláusulas
gestion = GestionClausulas()

# Iterar sobre las filas y asociar cláusulas con procesos
for index, row in df.iterrows():
    try:
        id_clausula = int(row["id_clausula"])
        id_proceso = int(row["id_proceso"])

        # Construir la lista esperada por el método
        procesos_subprocesos = [{"id_proceso": id_proceso}]

        # Llamar al método correcto
        gestion.registrar_clausula_proceso_subproceso(id_clausula, procesos_subprocesos)

        print(f"✅ Asociación creada: cláusula {id_clausula} → proceso {id_proceso}")

    except Exception as e:
        print(f"❌ Error en la fila {index + 2}: {e}")
