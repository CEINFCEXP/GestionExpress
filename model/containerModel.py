from azure.storage.blob import BlobServiceClient
import os

class ContainerModel:
    def __init__(self):
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)

    def get_containers(self):
        containers = self.blob_service_client.list_containers()
        return [container.name for container in containers]

    def create_container(self, name):
        self.blob_service_client.create_container(name)

    def get_files(self, container_name):
        container_client = self.blob_service_client.get_container_client(container_name)
        blobs = container_client.list_blobs()
        return [blob.name for blob in blobs]

    def download_file(self, container_name, file_name):
        blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=file_name)
        return blob_client.download_blob().readall()

    def delete_file(self, container_name, file_name):
        blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=file_name)
        blob_client.delete_blob()

    async def upload_file(self, container_name, file_name, file_content):
        blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=file_name)
        await blob_client.upload_blob(file_content, overwrite=True)
