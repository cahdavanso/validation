document.addEventListener('DOMContentLoaded', () => {
    // ----------------------------------------------------
    // Dados e Variáveis
    // ----------------------------------------------------
    const CONVENIOS = [
        "CÂMARA DE TERESÓPOLIS", "GOV. DA PARAIBA", "GOV. DO MARANHÃO", "GOV. MINAS GERAIS",
        "GOV. PIAUI", "GOV. RIO GRANDE DO NORTE", "GOV. SANTA CATARINA", "INSS",
        "PREF. BAYEUX", "PREF. CAJAMAR", "PREF. CAMPINA GRANDE", "PREF. CAMPO GRANDE",
        "PREF. CUIABÁ", "PREF. DE PORTO VELHO", "PREF. IMPERATRIZ MA", "PREF. ITU",
        "PREF. JOÃO PESSOA", "PREF. JUAZEIRO DO NORTE", "PREF. MARABÁ", "PREF. NITERÓI",
        "PREF. PAÇO DO LUMIAR", "PREF. PALMAS", "PREF. RECIFE", "PREF. SANTA RITA",
        "PREF. TERESINA"
    ];

    const UPLOAD_FIELDS = [
        "CREDBASE", "FUNCAO", "CONCILIACAO", "LIMINAR", "LIQUIDADOS",
        "ANDAMENTO", "AVERBADOS", "HISTÓRICO DE REFINS", "ORBITAL", "CASOS CAPITAL"
    ];

    const fileDataMap = {}; 
    
    // Elementos do DOM
    const selectButton = document.getElementById('select-convenio-button');
    const dropdownContent = document.getElementById('convenio-dropdown');
    const convenioSearch = document.getElementById('convenio-search');
    const convenioList = document.getElementById('convenio-list');
    const selectedConvenioText = document.getElementById('selected-convenio-text');
    
    // --- NOVOS ELEMENTOS DE CONSIGNATÁRIA ---
    const consignatariaArea = document.getElementById('consignataria-selection-area');
    const selectConsigButton = document.getElementById('select-consignataria-button');
    const dropdownConsigContent = document.getElementById('consignataria-dropdown');
    const selectedConsigText = document.getElementById('selected-consignataria-text');
    const consignatariaOptions = document.querySelectorAll('#consignataria-list li');

    const uploadForm = document.getElementById('upload-form');
    const uploadFieldsGrid = uploadForm ? uploadForm.querySelector('.upload-fields-grid') : null;
    const submitButton = document.getElementById('submit-validation');
    const themeToggleButton = document.getElementById('theme-toggle');
    const themeIcon = document.getElementById('theme-icon');

    let selectedConvenio = null;
    let selectedConsignataria = null;

    if (!uploadFieldsGrid) {
        console.error("Erro FATAL: Container de upload não encontrado.");
        return;
    }

    // ----------------------------------------------------
    // Lógica de Tema
    // ----------------------------------------------------
    const enableLightMode = () => {
        document.body.classList.remove('dark-mode');
        document.body.classList.add('light-mode');
        themeIcon.setAttribute('data-icon', 'lucide:moon');
        localStorage.setItem('theme', 'light');
    };
    const enableDarkMode = () => {
        document.body.classList.remove('light-mode');
        document.body.classList.add('dark-mode');
        themeIcon.setAttribute('data-icon', 'lucide:sun');
        localStorage.setItem('theme', 'dark');
    };
    const initializeTheme = () => {
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'light') enableLightMode();
        else enableDarkMode();
    };
    initializeTheme();
    themeToggleButton.addEventListener('click', () => {
        if (document.body.classList.contains('dark-mode')) enableLightMode();
        else enableDarkMode();
    });

    // ----------------------------------------------------
    // Dropdown Pesquisável (Convênios)
    // ----------------------------------------------------
    const renderConvenios = (list) => {
        convenioList.innerHTML = '';
        if (list.length === 0) {
            convenioList.innerHTML = `<li style="padding: 10px 15px; color: var(--color-text-muted);">Nenhum convênio encontrado.</li>`;
            return;
        }
        list.forEach(convenio => {
            const listItem = document.createElement('li');
            listItem.textContent = convenio;
            listItem.setAttribute('data-value', convenio);
            listItem.addEventListener('click', () => handleConvenioSelection(convenio));
            convenioList.appendChild(listItem);
        });
    };
    renderConvenios(CONVENIOS);

    selectButton.addEventListener('click', (event) => {
        event.stopPropagation();
        const isCurrentlyOpen = dropdownContent.classList.toggle('show');
        selectButton.classList.toggle('open');
        if (isCurrentlyOpen) convenioSearch.focus();
    });

    convenioSearch.addEventListener('input', (event) => {
        const query = event.target.value.toUpperCase();
        const filtered = CONVENIOS.filter(c => c.toUpperCase().includes(query));
        renderConvenios(filtered);
    });

    // ----------------------------------------------------
    // Lógica de Consignatária (Dropdown Novo)
    // ----------------------------------------------------
    if (selectConsigButton) {
        selectConsigButton.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdownConsigContent.classList.toggle('show');
            selectConsigButton.classList.toggle('open');
        });

        consignatariaOptions.forEach(option => {
            option.addEventListener('click', () => {
                selectedConsignataria = option.getAttribute('data-value');
                selectedConsigText.textContent = option.textContent;
                
                dropdownConsigContent.classList.remove('show');
                selectConsigButton.classList.remove('open');
                
                updateSubmitButtonState();
            });
        });
    }

    // Fecha dropdowns ao clicar fora
    document.addEventListener('click', (event) => {
        if (!selectButton.contains(event.target) && !dropdownContent.contains(event.target)) {
            dropdownContent.classList.remove('show');
            selectButton.classList.remove('open');
        }
        if (selectConsigButton && !selectConsigButton.contains(event.target) && !dropdownConsigContent.contains(event.target)) {
            dropdownConsigContent.classList.remove('show');
            selectConsigButton.classList.remove('open');
        }
    });

    /**
     * FUNÇÃO PRINCIPAL: Seleção de Convênio com Lógica Condicional
     */
    const handleConvenioSelection = (convenio) => {
        selectedConvenio = convenio;
        selectedConvenioText.textContent = convenio;
        dropdownContent.classList.remove('show');
        selectButton.classList.remove('open');

        // --- LÓGICA CONDICIONAL PARA GOV. DA PARAIBA ---
        if (convenio === "GOV. DA PARAIBA") {
            consignatariaArea.classList.remove('hidden');
            // Reseta a seleção para forçar o usuário a escolher
            selectedConsignataria = null;
            selectedConsigText.textContent = "Clique para Selecionar";
        } else {
            consignatariaArea.classList.add('hidden');
            selectedConsignataria = null;
        }

        // Mostra a área de upload
        if (uploadForm.classList.contains('hidden')) {
            uploadForm.classList.remove('hidden');
        }
        
        renderUploadFields(); 
        updateSubmitButtonState();
    };

    // ----------------------------------------------------
    // Campos de Upload
    // ----------------------------------------------------
    const renderUploadFields = () => {
        uploadFieldsGrid.innerHTML = '';
        UPLOAD_FIELDS.forEach(field => {
            const fieldId = field.replace(/[^a-zA-Z0-9]/g, '_').toUpperCase();
            const fieldHTML = `
                <div class="upload-group">
                    <label class="form-label">${field}</label>
                    <div class="upload-box" id="drop-area-${fieldId}">
                        <span class="iconify upload-icon" data-icon="lucide:file-text"></span>
                        <p class="upload-text-main">Arraste seu arquivo aqui</p>
                        <p class="upload-text-subtle">ou clique para selecionar</p>
                        <p class="file-info" id="file-info-${fieldId}">Formatos aceitos: CSV, XLSX, XLS</p>
                        <input type="file" multiple accept=".csv, .xlsx, .xls" data-field-id="${fieldId}" id="input-${fieldId}" name="${fieldId}">
                    </div>
                </div>
            `;
            uploadFieldsGrid.insertAdjacentHTML('beforeend', fieldHTML);
            setupFileHandlers(fieldId);
        });
    };

    const setupFileHandlers = (fieldId) => {
        const dropArea = document.getElementById(`drop-area-${fieldId}`);
        const fileInput = document.getElementById(`input-${fieldId}`);
        const fileInfoElement = document.getElementById(`file-info-${fieldId}`);

        if (!dropArea || !fileInput) return;

        dropArea.addEventListener('click', (event) => {
            if (!event.target.closest('input[type="file"]')) {
                fileInput.click();
            }
        });

        fileInput.addEventListener('change', (event) => {
            handleFileProcess(event.target.files, fieldId, fileInfoElement);
        });

        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, e => { e.preventDefault(); e.stopPropagation(); }, false);
        });

        ['dragenter', 'dragover'].forEach(eventName => {
            dropArea.addEventListener(eventName, () => dropArea.classList.add('dragover'), false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, () => dropArea.classList.remove('dragover'), false);
        });

        dropArea.addEventListener('drop', (event) => {
            const dt = event.dataTransfer;
            handleFileProcess(dt.files, fieldId, fileInfoElement);
        }, false);
    };

    const handleFileProcess = (files, fieldId, infoElement) => {
        const validFiles = Array.from(files);
        if (validFiles.length > 0) {
            fileDataMap[fieldId] = validFiles;
            const names = validFiles.map(f => f.name).join(', ');
            const totalSize = (validFiles.reduce((sum, f) => sum + f.size, 0) / (1024 * 1024)).toFixed(2);
            infoElement.textContent = `Arquivos: ${validFiles.length} (${totalSize} MB). ${names}`;
            infoElement.classList.remove('error');
        } else {
            delete fileDataMap[fieldId];
            infoElement.textContent = `Formatos aceitos: CSV, XLSX, XLS`; 
            infoElement.classList.remove('error');
        }
        updateSubmitButtonState();
    };

    const updateSubmitButtonState = () => {
        const hasFiles = Object.keys(fileDataMap).length > 0;
        let isConfigValid = !!selectedConvenio;

        // Validação extra para Paraíba: Exige Consignatária
        if (selectedConvenio === "GOV. DA PARAIBA") {
            if (!selectedConsignataria) {
                isConfigValid = false;
            }
        }

        submitButton.disabled = !hasFiles || !isConfigValid;
    };

    // ----------------------------------------------------
    // Submissão
    // ----------------------------------------------------
    uploadForm.addEventListener('submit', async (event) => {
        event.preventDefault();

        if (Object.keys(fileDataMap).length === 0) {
            alert('Por favor, selecione pelo menos um arquivo.');
            return;
        }

        submitButton.disabled = true;
        submitButton.textContent = 'Enviando...';

        try {
            await sendFilesToBackend();
            
            submitButton.textContent = 'Sucesso!';
            submitButton.classList.add('success');
            setTimeout(() => {
                submitButton.textContent = 'Iniciar Validação e Processamento';
                submitButton.classList.remove('success');
                submitButton.disabled = false;
            }, 3000);

        } catch (error) {
            console.error('Erro:', error);
            alert(`Erro: ${error.message}`);
            submitButton.textContent = 'Tente Novamente';
            submitButton.disabled = false;
        }
    });

    const sendFilesToBackend = async () => {
        const formData = new FormData();
        formData.append('convenio', selectedConvenio);

        // Envia consignatária apenas se foi selecionada (importante para o backend)
        if (selectedConsignataria) {
            formData.append('consignataria', selectedConsignataria);
        }

        for (const [fieldId, files] of Object.entries(fileDataMap)) {
            files.forEach((file) => {
                formData.append(fieldId, file, file.name); 
            });
        }
        
        const API_URL = 'http://localhost:8000/validar'; 
        const response = await fetch(API_URL, { method: 'POST', body: formData });
        
        if (!response.ok) {
            let errorDetail = `Erro HTTP: ${response.status}`;
            try {
                const errorData = await response.json();
                errorDetail = errorData.detail || errorDetail;
            } catch (e) {}
            throw new Error(errorDetail);
        }
        
        return response.json();
    };
    
    updateSubmitButtonState();
});