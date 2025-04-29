# GestiónExpress
Proyecto Aplicación Gestión Administrativa/Operativa con FastAPI, Jinja2 y PostgreSQL
Centro de Información - Consorcio Express S.A.S
https://dashboard.render.com/
https://gestionconsorcioexpress.onrender.com/

## Tecnologías usadas:
- **Python**
- **FastAPI**
- **Jinja2**
- **HTML**

**1:** Ingresar desde la terminal dentro de la carpeta del proyecto:
cd <nombre del directorio>

**2:** Crear un entorno virtual:
python -m venv venv

**3:** Ingresar en el entorno virtual:
venv\Scripts\activate.bat

**4:** Descargar las dependencias del archivo 'requirements.txt' con el comando:
pip install -r requirements.txt   

**5:** Correr el servidor web de uvicorn para visualizar la aplicación:
uvicorn <nombre del archivo principal>:<nombre de la instancia de FastAPI> --reload
```
uvicorn main:app --reload
```
**6:** En el navegador ir al localhost:8000. (http://127.0.0.1:8000/)

###### Construir Archivo Requirements.txt ##### 
Genera la lista de todas las libreris utilizadas con su versión
pip freeze > requirements.txt  

# Explorador de Azure Blob Storage
## Descripción
Este proyecto es una aplicación web que permite administrar contenedores y archivos en Azure Blob Storage. Proporciona una interfaz de usuario intuitiva para realizar operaciones comunes como listar contenedores, crear nuevos contenedores, subir, descargar y eliminar archivos.

## Características
- Listar y crear contenedores de Azure Blob Storage
- Visualizar archivos dentro de los contenedores
- Subir archivos mediante arrastrar y soltar o selección manual
- Descargar archivos de los contenedores
- Eliminar archivos de los contenedores
- Filtrar contenedores y archivos
- Barra de progreso para subidas de archivos

## Tecnologías utilizadas
- Frontend: HTML, CSS, JavaScript (vanilla)
- Backend: Python con FastAPI
- Almacenamiento: Azure Blob Storage

## Requisitos previos
- Python 3.7+
- Cuenta de Azure con un servicio de Blob Storage

## Uso
- Use la interfaz de usuario para navegar por los contenedores y archivos.
- Haga clic en un contenedor para ver sus archivos.
- Use el botón "Crear Contenedor" para crear nuevos contenedores.
- Arrastre y suelte archivos en la zona designada para subirlos, o use el botón "Seleccionar archivos".
- Use los botones de acción junto a cada archivo para descargar o eliminar.

## Contribución
Las contribuciones son bienvenidas. Por favor, abra un issue para discutir cambios importantes antes de crear un pull request.