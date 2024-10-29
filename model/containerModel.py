from azure.storage.blob import BlobServiceClient
from model.gestionar_db import HandleDB
from model.gestionar_db import Cargue_Roles_Blob_Storage
import os

class ContainerModel:
    def __init__(self):
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        self.db = HandleDB()

    def get_containers(self):
        containers = self.blob_service_client.list_containers()
        container_names = [container.name for container in containers]
        #print(f"Contenedores disponibles en Azure Blob Storage: {container_names}")  # Verificación
        return container_names

    def create_container(self, name):
        self.blob_service_client.create_container(name)

    def get_files(self, container_name):
        container_client = self.blob_service_client.get_container_client(container_name)
        blobs = container_client.list_blobs()

        tree = {}
        for blob in blobs:
            parts = blob.name.split('/')
            current_level = tree
            for part in parts[:-1]:
                if part not in current_level or current_level[part] is None:
                    current_level[part] = {}  # Crear un subdirectorio si no existe
                current_level = current_level[part]
            current_level[parts[-1]] = None  # Marcar el archivo en el nivel actual
        return tree

    def download_file(self, container_name, file_name):
        blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=file_name)
        return blob_client.download_blob().readall()

    def delete_file(self, container_name, file_name):
        blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=file_name)
        blob_client.delete_blob()

    async def upload_file(self, container_name, file_name, file_content):
        blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=file_name)
        await blob_client.upload_blob(file_content, overwrite=True)

    def get_allowed_containers(self, user_rol_storage):
        roles_blob_storage = Cargue_Roles_Blob_Storage() # Instanciar la clase Cargue_Roles_Blob_Storage

        contenedores_asignados = roles_blob_storage.get_contenedores_por_rol(user_rol_storage) # Obtener los contenedores asignados al rol_storage      
        all_containers = self.get_containers() # Listar todos los contenedores disponibles en Blob Storage

        # Filtrar solo los contenedores permitidos
        allowed_containers = [container for container in all_containers if container in contenedores_asignados]
        return allowed_containers