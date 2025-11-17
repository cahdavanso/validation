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
        "CREDBASE AKRK E DIG", "FUNÇÃO", "CONCILIAÇÃO", "LIMINAR", "LIQUIDADOS",
        "ANDAMENTO", "AVERBADOS", "HISTÓRICO DE REFINS"
    ];

    const fileDataMap = {}; 
    
    // Elementos do DOM (Verificação Rigorosa)
    const selectButton = document.getElementById('select-convenio-button');
    const dropdownContent = document.getElementById('convenio-dropdown');
    const convenioSearch = document.getElementById('convenio-search');
    const convenioList = document.getElementById('convenio-list');
    const selectedConvenioText = document.getElementById('selected-convenio-text');
    const uploadForm = document.getElementById('upload-form'); // O container principal
    const uploadFieldsGrid = uploadForm ? uploadForm.querySelector('.upload-fields-grid') : null; // A DIV ONDE OS CAMPOS SÃO INJETADOS
    const submitButton = document.getElementById('submit-validation');
    const themeToggleButton = document.getElementById('theme-toggle');
    const themeIcon = document.getElementById('theme-icon');

    let selectedConvenio = null;

    // Se o grid de campos não for encontrado (uploadFieldsGrid é null), o script irá parar silenciosamente.
    // Adicionamos uma verificação inicial para evitar isso.
    if (!uploadFieldsGrid) {
        console.error("Erro FATAL: O container '.upload-fields-grid' não foi encontrado no DOM. Verifique seu index.html.");
        return; // Interrompe o script se o elemento essencial não for encontrado.
    }

    // ----------------------------------------------------
    // Lógica de Tema (Modo Claro/Escuro) - MANTIDA
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
        if (savedTheme === 'light') {
            enableLightMode();
        } else {
            enableDarkMode();
        }
    };
    
    initializeTheme();
    themeToggleButton.addEventListener('click', () => {
        if (document.body.classList.contains('dark-mode')) {
            enableLightMode();
        } else {
            enableDarkMode();
        }
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
        if (isCurrentlyOpen) {
             convenioSearch.focus();
        }
    });

    document.addEventListener('click', (event) => {
        if (!selectButton.contains(event.target) && !dropdownContent.contains(event.target)) {
            dropdownContent.classList.remove('show');
            selectButton.classList.remove('open');
        }
    });

    convenioSearch.addEventListener('input', (event) => {
        const query = event.target.value.toUpperCase();
        const filtered = CONVENIOS.filter(c => c.toUpperCase().includes(query));
        renderConvenios(filtered);
    });

    /**
     * FUNÇÃO CRÍTICA: Lida com a seleção do convênio e ATIVA a área de upload.
     */
    const handleConvenioSelection = (convenio) => {
        selectedConvenio = convenio;
        selectedConvenioText.textContent = convenio;
        dropdownContent.classList.remove('show');
        selectButton.classList.remove('open');

        // 1. ATUALIZA O TÍTULO
        const uploadTitle = document.getElementById('upload-title');
        if (uploadTitle) {
            uploadTitle.innerHTML = `📤 Upload para: **${convenio}**`;
        }

        // 2. DESOCULTA A ÁREA DE UPLOAD (A classe 'hidden' está no HTML)
        if (uploadForm.classList.contains('hidden')) {
            uploadForm.classList.remove('hidden');
        }
        
        // 3. GARANTE A RENDERIZAÇÃO DOS CAMPOS
        // Chamamos a função de renderização logo após a seleção
        renderUploadFields(); 

        updateSubmitButtonState();
    };

    // ----------------------------------------------------
    // Geração e Lógica dos Campos de Upload
    // ----------------------------------------------------

    /**
     * FUNÇÃO CRÍTICA: Gera dinamicamente o HTML dos campos de upload.
     */
    const renderUploadFields = () => {
        // Limpa o contêiner *antes* de injetar novo HTML
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
                        <input type="file" multiple 
                               accept=".csv, .xlsx, .xls" 
                               data-field-id="${fieldId}" 
                               id="input-${fieldId}" 
                               name="${fieldId}">
                    </div>
                </div>
            `;
            // Insere o HTML no contêiner do grid
            uploadFieldsGrid.insertAdjacentHTML('beforeend', fieldHTML);
            
            // Configura os manipuladores de arquivo (Drag & Drop, Clique) para o novo campo
            setupFileHandlers(fieldId);
        });
    };

    const setupFileHandlers = (fieldId) => {
        const dropArea = document.getElementById(`drop-area-${fieldId}`);
        const fileInput = document.getElementById(`input-${fieldId}`);
        const fileInfoElement = document.getElementById(`file-info-${fieldId}`);

        // Verificação de segurança, caso o elemento não tenha sido renderizado corretamente
        if (!dropArea || !fileInput) return;

        // Evento de Clique para abrir o seletor de arquivo
        dropArea.addEventListener('click', (event) => {
            if (!event.target.closest('input[type="file"]')) {
                fileInput.click();
            }
        });

        fileInput.addEventListener('change', (event) => {
            handleFileProcess(event.target.files, fieldId, fileInfoElement);
        });

        // ... (eventos de Drag & Drop) ...

        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, preventDefaults, false);
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
            
            infoElement.textContent = `Arquivos: ${validFiles.length} (${totalSize} MB). Concatenados: ${names}`;
            infoElement.classList.remove('error');

        } else {
            delete fileDataMap[fieldId];
            infoElement.textContent = `Formatos aceitos: CSV, XLSX, XLS`; 
            infoElement.classList.remove('error');
        }

        updateSubmitButtonState();
    };

    const preventDefaults = (e) => {
        e.preventDefault();
        e.stopPropagation();
    };

    const updateSubmitButtonState = () => {
        const hasFiles = Object.keys(fileDataMap).length > 0;
        submitButton.disabled = !hasFiles || !selectedConvenio;
    };

    // ----------------------------------------------------
    // Submissão do Formulário e Preparação da API - MANTIDA
    // ----------------------------------------------------

    uploadForm.addEventListener('submit', async (event) => {
        event.preventDefault();

        if (Object.keys(fileDataMap).length === 0) {
            alert('Por favor, selecione pelo menos um arquivo para iniciar a validação.');
            return;
        }

        submitButton.disabled = true;
        submitButton.textContent = 'Aguarde... Enviando dados para o Backend';

        try {
            await sendFilesToBackend();
            
            submitButton.textContent = 'Validação Iniciada com Sucesso!';
            submitButton.classList.add('success');
            setTimeout(() => {
                submitButton.textContent = 'Iniciar Validação e Processamento';
                submitButton.classList.remove('success');
                submitButton.disabled = false;
            }, 3000);

        } catch (error) {
            console.error('Erro ao enviar dados para a API:', error);
            alert(`Erro na comunicação com o backend. Verifique o console. Detalhe: ${error.message}`);
            submitButton.textContent = 'Erro ao Enviar. Tente Novamente.';
            submitButton.disabled = false;
        }
    });

    const sendFilesToBackend = async () => {
        // ... (lógica de envio) ...
        const formData = new FormData();
        formData.append('convenio', selectedConvenio);

        for (const [fieldId, files] of Object.entries(fileDataMap)) {
            files.forEach((file) => {
                formData.append(fieldId, file, file.name); 
            });
        }
        
        console.log("--- Conteúdo do FormData para /validar ---");
        for (let [key, value] of formData.entries()) {
            if (value instanceof File) {
                console.log(`Campo: ${key}, Arquivo: ${value.name}, Tamanho: ${(value.size / 1024).toFixed(2)} KB`);
            } else {
                console.log(`Campo: ${key}, Valor: ${value}`);
            }
        }
        console.log("-----------------------------------------");
        
        const API_URL = 'http://localhost:8000/validar'; 

        // --- SIMULAÇÃO DE API ---
        return new Promise(resolve => setTimeout(resolve, 1500)); 
    };
    
    updateSubmitButtonState();
});