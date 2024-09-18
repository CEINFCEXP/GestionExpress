# GestiónExpress
Proyecto Aplicación Gestión Administrativa/Operativa con FastAPI, Jinja2 y SQLite3
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