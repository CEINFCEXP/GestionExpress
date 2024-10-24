class Model {
    constructor() {
        this.apiUrl = 'http://localhost:8000';
    }

    async getContainers() {
        try {
            const response = await fetch(`${this.apiUrl}/containers`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            return data.containers;
        } catch (error) {
            console.error('Error al obtener contenedores:', error);
            throw error;
        }
    }

    async createContainer(name) {
        try {
            const response = await fetch(`${this.apiUrl}/containers?name=${encodeURIComponent(name)}`, {
                method: 'POST'
            });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return true;
        } catch (error) {
            console.error('Error al crear contenedor:', error);
            throw error;
        }
    }

    async getFiles(containerName) {
        try {
            const response = await fetch(`${this.apiUrl}/containers/${encodeURIComponent(containerName)}/files`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            console.log('Datos de archivos recibidos:', data); // Para depuración
            return data.files;
        } catch (error) {
            console.error('Error al obtener archivos:', error);
            throw error;
        }
    }

    async deleteFile(containerName, fileName) {
        try {
            const response = await fetch(`${this.apiUrl}/containers/${encodeURIComponent(containerName)}/files/${encodeURIComponent(fileName)}`, {
                method: 'DELETE'
            });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return true;
        } catch (error) {
            console.error('Error al eliminar archivo:', error);
            throw error;
        }
    }

    downloadFile(containerName, fileName) {
        window.open(`${this.apiUrl}/containers/${encodeURIComponent(containerName)}/files/${encodeURIComponent(fileName)}/download`);
    }

    async uploadFile(containerName, file, onProgress = () => { }) {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            xhr.open('POST', `${this.apiUrl}/containers/${encodeURIComponent(containerName)}/files`);

            xhr.upload.onprogress = (event) => {
                if (event.lengthComputable) {
                    const percentComplete = (event.loaded / event.total) * 100;
                    onProgress(percentComplete);
                }
            };

            xhr.onload = () => {
                let response;
                try {
                    response = JSON.parse(xhr.responseText);
                } catch (e) {
                    response = { message: xhr.responseText };
                }

                if (xhr.status === 200) {
                    resolve(response);
                } else {
                    reject(new Error(response.message || 'Error desconocido al subir el archivo'));
                }
            };

            xhr.onerror = () => reject(new Error('Error de red al subir el archivo'));

            const formData = new FormData();
            formData.append('file', file);

            xhr.send(formData);
        });
    }

    async downloadFile(containerName, fileName, onProgress = () => { }) {
        const response = await fetch(`${this.apiUrl}/containers/${encodeURIComponent(containerName)}/files/${encodeURIComponent(fileName)}/download`);
        const reader = response.body.getReader();
        const contentLength = +response.headers.get('Content-Length');

        let receivedLength = 0;
        let chunks = [];

        while (true) {
            const { done, value } = await reader.read();

            if (done) {
                break;
            }

            chunks.push(value);
            receivedLength += value.length;
            onProgress((receivedLength / contentLength) * 100);
        }

        let blob = new Blob(chunks);
        let url = window.URL.createObjectURL(blob);
        let a = document.createElement('a');
        a.href = url;
        a.download = fileName;
        document.body.appendChild(a);
        a.click();
        a.remove();
    }
}
