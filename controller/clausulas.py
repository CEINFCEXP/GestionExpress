import sys
import os
import datetime
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pandas as pd
from dotenv import load_dotenv
from model.gestion_clausulas import GestionClausulas

# Cargar variables de entorno
load_dotenv()

# Ruta del archivo Excel
archivo_excel = "C:/Users/sergio.hincapie/Desktop/cargue_clausulas.xlsx"
df = pd.read_excel(archivo_excel)

# Inicializar clase de lógica jurídica
gestion = GestionClausulas()

# Iterar sobre las filas del archivo
for index, row in df.iterrows():
    try:
        # --------------------------
        # Procesar periodo_control
        # --------------------------
        frecuencia = str(row["frecuencia"]).strip().lower()
        valor_periodo = row["periodo_control"]

        if frecuencia == "personalizado":
            if pd.notnull(valor_periodo) and hasattr(valor_periodo, "strftime"):
                periodo_control = valor_periodo.strftime("%Y-%m-%d")
            else:
                periodo_control = str(valor_periodo).strip()
        else:
            periodo_control = str(valor_periodo).strip()

        # --------------------------
        # Construir el diccionario con los datos de la cláusula
        # --------------------------
        clausula_data = {
            "control": row["control"],
            "etapa": row["etapa"],
            "clausula": row["clausula"],
            "modificacion": row.get("modificacion", ""),
            "contrato": row["contrato_concesion"],
            "tema": row["tema"],
            "subtema": row["subtema"],
            "descripcion": row["descripcion_clausula"],
            "tipo": row["tipo_clausula"],
            "norma": row.get("norma_relacionada", ""),
            "consecuencia": row.get("consecuencia", ""),
            "frecuencia": row["frecuencia"],
            "periodo_control": periodo_control,
            "inicio_cumplimiento": str(row["inicio_cumplimiento"].date()) if pd.notnull(row["inicio_cumplimiento"]) else None,
            "fin_cumplimiento": str(row["fin_cumplimiento"].date()) if pd.notnull(row["fin_cumplimiento"]) else None,
            "observacion": row.get("observacion", ""),
            "responsable_entrega": row["responsable_entrega"],
            "ruta_soporte": None  # Se completa luego
        }

        # 1. Crear la cláusula
        clausula_id = gestion.crear_clausula(clausula_data)

        # 2. Generar y registrar la ruta de soporte
        clausula_str = str(row["clausula"]).replace(" ", "-")
        contrato_str = str(row["contrato_concesion"]).replace(" ", "-")
        ruta_soporte = f"5000-juridica-y-riesgos-juridica-clausulas/{clausula_id}-{clausula_str}-{contrato_str}"
        gestion.registrar_ruta_soporte(clausula_id, ruta_soporte)

        # 3. Calcular fechas de entrega
        fechas = gestion.calcular_fechas_dinamicas(
            clausula_data["inicio_cumplimiento"],
            clausula_data["fin_cumplimiento"],
            clausula_data["frecuencia"],
            clausula_data["periodo_control"]
        )

        # 4. Crear la estructura de carpetas en Azure Blob Storage
        gestion.crear_estructura_blob_storage(
            clausula_id,
            row["clausula"],
            row["contrato_concesion"],
            [f["entrega"] for f in fechas]
        )

        print(f"✅ Cláusula ID {clausula_id} registrada exitosamente.")

    except Exception as e:
        print(f"❌ Error en la fila {index + 2}: {e}")

