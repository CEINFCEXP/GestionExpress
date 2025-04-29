class Controller {
    constructor(model, view) {
        console.log('Initializing Controller');
        this.model = model;
        this.view = view;
        this.containers = [];

        console.log('Binding view listeners');
        this.view.bindCreateContainer(this.handleCreateContainer.bind(this));
        this.view.bindContainerClick(this.handleContainerClick.bind(this));

        console.log('Binding refreshContainers');
        this.refreshContainers = this.refreshContainers.bind(this);

        console.log('Initial load');
        this.refreshContainers();

        this.view.bindFileUpload(this.handleFileUpload.bind(this));
        this.view.bindFileDownload(this.handleFileDownload.bind(this));
        this.view.bindFileDelete(this.handleFileDelete.bind(this));

        this.view.setupContainerFilter(this.handleContainerFilter.bind(this));
    }

    async refreshContainers() {
        try {
            const containers = await this.model.getContainers();
            this.view.displayContainers(containers);
        } catch (error) {
            console.error('Error al refrescar contenedores:', error);
        }
    }

    async handleCreateContainer(name) {
        try {
            await this.model.createContainer(name);
            await this.refreshContainers();
        } catch (error) {
            console.error('Error al crear contenedor:', error);
        }
    }

    async handleContainerClick(containerName) {
        try {
            this.currentContainer = containerName;  // Asegúrate de que esta línea esté presente
            const files = await this.model.getFiles(containerName);
            console.log('Archivos obtenidos:', files);
            this.view.displayFiles(containerName, files);
        } catch (error) {
            console.error('Error al cargar archivos:', error);
        }
    }

    async handleFileUpload(files) {
        if (this.currentContainer) {
            for (let file of files) {
                try {
                    const result = await this.model.uploadFile(this.currentContainer, file, (progress) => {
                        this.view.updateUploadProgress(progress);
                    });
                    console.log(result.message);
                    this.view.updateUploadProgress(100);
                } catch (error) {
                    console.error(`Error al subir el archivo ${file.name}:`, error);
                    this.view.showError(`Error al subir el archivo ${file.name}: ${error.message}`);
                } finally {
                    setTimeout(() => this.view.resetUploadProgress(), 1000);
                }
            }
            await this.handleContainerClick(this.currentContainer);
        } else {
            console.error('No se ha seleccionado ningún contenedor');
            this.view.showError('Por favor, selecciona un contenedor antes de subir archivos');
        }
    }

    async handleFileDownload(fileName) {
        if (this.currentContainer) {
            try {
                await this.model.downloadFile(this.currentContainer, fileName, (progress) => {
                    this.view.updateDownloadProgress(progress);
                });
                console.log(`Archivo ${fileName} descargado exitosamente`);
            } catch (error) {
                console.error(`Error al descargar el archivo ${fileName}:`, error);
                this.view.showError(`Error al descargar el archivo ${fileName}: ${error.message}`);
            }
        } else {
            console.error('No se ha seleccionado ningún contenedor');
            this.view.showError('No se ha seleccionado ningún contenedor');
        }
    }

    async handleFileDelete(fileName) {
        if (this.currentContainer) {
            try {
                await this.model.deleteFile(this.currentContainer, fileName);
                console.log(`Archivo ${fileName} eliminado exitosamente`);
                await this.handleContainerClick(this.currentContainer);
            } catch (error) {
                console.error(`Error al eliminar el archivo ${fileName}:`, error);
            }
        } else {
            console.error('No se ha seleccionado ningún contenedor');
        }
    }

    async init() {
        try {
            this.containers = await this.model.getContainers();
            this.view.displayContainers(this.containers);
        } catch (error) {
            console.error('Error al cargar contenedores:', error);
        }
    }

    handleContainerFilter(filterText) {
        const filteredContainers = this.containers.filter(container =>
            container.toLowerCase().includes(filterText.toLowerCase())
        );
        this.view.displayContainers(filteredContainers);
    }

    // ... resto de la clase ...
}

document.addEventListener('DOMContentLoaded', () => {
    const model = new Model();
    const view = new View();
    const app = new Controller(model, view);
});
