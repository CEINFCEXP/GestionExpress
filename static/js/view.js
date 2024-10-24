class View {
    constructor() {
        this.containerList = document.getElementById('containerList');
        this.fileList = document.getElementById('fileList');
        this.createContainerBtn = document.getElementById('createContainerBtn');
        this.newContainerNameInput = document.getElementById('newContainerName');
        this.currentContainerSpan = document.querySelector('#currentContainer span');
        this.dropZone = document.getElementById('dropZone');
        this.fileUpload = document.getElementById('fileUpload');
        this.uploadFilesBtn = document.getElementById('uploadFilesBtn');
        this.uploadProgressBar = document.getElementById('uploadProgress');
        this.uploadProgressBarFill = this.uploadProgressBar.querySelector('.progress-bar-fill');
        this.downloadProgressBar = document.getElementById('downloadProgress');
        this.downloadProgressBarFill = this.downloadProgressBar.querySelector('.progress-bar-fill');
        this.containerFilter = document.getElementById('containerFilter');
    }

    displayContainers(containers) {
        this.containerList.innerHTML = containers.map(container =>
            `<li data-container="${container}">${container}</li>`
        ).join('');
    }

    displayFiles(containerName, files) {
        this.currentContainerSpan.textContent = containerName;
        this.fileList.innerHTML = '';
        if (files && files.length > 0) {
            files.forEach(file => {
                const li = document.createElement('li');
                const fileName = typeof file === 'string' ? file : file.name;
                li.innerHTML = `
                    <span>${fileName}</span>
                    <div class="file-actions">
                        <button class="download-btn" data-file="${fileName}"><i class="fas fa-download"></i></button>
                        <button class="delete-btn" data-file="${fileName}"><i class="fas fa-trash"></i></button>
                    </div>
                `;
                this.fileList.appendChild(li);
            });
        } else {
            const li = document.createElement('li');
            li.textContent = 'No hay archivos en este contenedor';
            this.fileList.appendChild(li);
        }
    }

    bindCreateContainer(handler) {
        this.createContainerBtn.addEventListener('click', () => {
            const name = this.newContainerNameInput.value.trim();
            if (name) {
                handler(name);
                this.newContainerNameInput.value = ''; // Limpiar el input después de crear
            }
        });
    }

    bindContainerClick(handler) {
        this.containerList.addEventListener('click', event => {
            if (event.target.tagName === 'LI') {
                const containerName = event.target.textContent;
                handler(containerName);
            }
        });
    }

    bindFileUpload(handler) {
        const dropZone = document.getElementById('dropZone');
        const fileInput = document.getElementById('fileUpload');
        const selectFilesBtn = document.getElementById('selectFilesBtn');

        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        });

        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('dragover');
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            const files = e.dataTransfer.files;
            handler(files);
        });

        fileInput.addEventListener('change', (e) => {
            const files = e.target.files;
            handler(files);
        });

        selectFilesBtn.addEventListener('click', () => {
            fileInput.click();
        });
    }

    bindFileDownload(handler) {
        this.fileList.addEventListener('click', (e) => {
            if (e.target.closest('.download-btn')) {
                const fileName = e.target.closest('.download-btn').getAttribute('data-file');
                handler(fileName);
            }
        });
    }

    bindFileDelete(handler) {
        this.fileList.addEventListener('click', (e) => {
            if (e.target.closest('.delete-btn')) {
                const fileName = e.target.closest('.delete-btn').getAttribute('data-file');
                handler(fileName);
            }
        });
    }

    updateUploadProgress(progress) {
        this.uploadProgressBar.style.display = 'block';
        this.uploadProgressBarFill.style.width = `${progress}%`;
    }

    resetUploadProgress() {
        this.uploadProgressBar.style.display = 'none';
        this.uploadProgressBarFill.style.width = '0%';
    }

    updateDownloadProgress(progress) {
        this.downloadProgressBar.style.display = 'block';
        this.downloadProgressBarFill.style.width = `${progress}%`;
        if (progress >= 100) {
            setTimeout(() => {
                this.downloadProgressBar.style.display = 'none';
                this.downloadProgressBarFill.style.width = '0%';
            }, 1000);
        }
    }

    showError(message) {
        alert(message);  // Puedes reemplazar esto con una implementación más elegante
    }

    setupContainerFilter(filterCallback) {
        this.containerFilter.addEventListener('input', (event) => {
            filterCallback(event.target.value);
        });
    }

    updateFilteredContainers(filteredContainers) {
        console.log('Actualizando contenedores filtrados:', filteredContainers); // Para depuración
        this.displayContainers(filteredContainers);
    }
}
