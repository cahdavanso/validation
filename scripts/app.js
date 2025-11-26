document.addEventListener('DOMContentLoaded', () => {
    // ----------------------------------------------------
    // CONFIGURAÇÃO DE DADOS
    // ----------------------------------------------------
    
    // Grupos de Convênios
    const CONVENIOS_CODATA = ["GOV. PB"];
    const CONVENIOS_INSS = ["INSS"];
    const CONVENIOS_CONSIGFACIL = [
        "GOV. MA", "GOV. PI", "PREF. BAYEUX", "PREF. CAJAMAR",
        "PREF. CAMPINA GRANDE", "PREF. CAMPO GRANDE", "PREF. CUIABÁ", "PREF. DE PORTO VELHO",
        "PREF. IMPERATRIZ MA", "PREF. ITU", "PREF. JOÃO PESSOA", "PREF. JUAZEIRO DO NORTE",
        "PREF. MARABÁ", "PREF. NITERÓI", "PREF. PAÇO DO LUMIAR", "PREF. PALMAS", "PREF. RECIFE",
        "PREF. SANTA RITA", "PREF. TERESINA", "CÂMARA DE TERESÓPOLIS", "GOV. MG", 
        "GOV. RN", "GOV. SC"
    ];

    const ALL_CONVENIOS = [...CONVENIOS_CODATA, ...CONVENIOS_INSS, ...CONVENIOS_CONSIGFACIL].sort();

    const FIELDS_CONSIGFACIL = ["CREDBASE", "FUNCAO", "CONCILIACAO", "LIMINAR", "LIQUIDADOS", "ANDAMENTO", "AVERBADOS", "HISTORICO_DE_REFINS"];
    const FIELDS_CODATA = ["CREDBASE", "FUNCAO", "CONCILIACAO", "LIMINAR", "LIQUIDADOS", "ANDAMENTO", "AVERBADOS", "ORBITAL"];
    const FIELDS_INSS = ["FUNCAO", "CONCILIACAO", "LIMINAR", "LIQUIDADOS", "AVERBADOS", "ORBITAL", "CASOS_CAPITAL"];

    const fileDataMap = {}; 
    
    // Elementos do DOM
    const selectButton = document.getElementById('select-convenio-button');
    const dropdownContent = document.getElementById('convenio-dropdown');
    const convenioSearch = document.getElementById('convenio-search');
    const convenioList = document.getElementById('convenio-list');
    const selectedConvenioText = document.getElementById('selected-convenio-text');
    
    const consignatariaArea = document.getElementById('consignataria-selection-area');
    const selectConsigButton = document.getElementById('select-consignataria-button');
    const dropdownConsigContent = document.getElementById('consignataria-dropdown');
    const selectedConsigText = document.getElementById('selected-consignataria-text');
    const consignatariaOptions = document.querySelectorAll('#consignataria-list li');

    const uploadForm = document.getElementById('upload-form');
    const uploadFieldsGrid = uploadForm ? uploadForm.querySelector('.upload-fields-grid') : null;
    const submitButton = document.getElementById('submit-validation');
    
    // Console Elements
    const consoleContainer = document.getElementById('system-console');

    const themeToggleButton = document.getElementById('theme-toggle');
    const themeIcon = document.getElementById('theme-icon');

    let selectedConvenio = null;
    let selectedConsignataria = null;

    if (!uploadFieldsGrid) return;

    // --- Tema ---
    const initializeTheme = () => {
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'light') {
            document.body.classList.add('light-mode');
            document.body.classList.remove('dark-mode');
            themeIcon.setAttribute('data-icon', 'lucide:moon');
        } else {
            document.body.classList.add('dark-mode');
            document.body.classList.remove('light-mode');
            themeIcon.setAttribute('data-icon', 'lucide:sun');
        }
    };
    initializeTheme();
    themeToggleButton.addEventListener('click', () => {
        document.body.classList.toggle('dark-mode');
        document.body.classList.toggle('light-mode');
        const isDark = document.body.classList.contains('dark-mode');
        themeIcon.setAttribute('data-icon', isDark ? 'lucide:sun' : 'lucide:moon');
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
    });

    // --- FUNCAO DE LOG DO CONSOLE (NOVO) ---
    const logToConsole = (message, type = 'info') => {
        // Garante que o console esteja visível
        consoleContainer.style.display = 'block';

        const now = new Date();
        const timeString = now.toLocaleTimeString('pt-BR', { hour12: false });
        
        const line = document.createElement('div');
        line.classList.add('log-line');
        
        let typeClass = 'log-info';
        if (type === 'success') typeClass = 'log-success';
        if (type === 'error') typeClass = 'log-error';
        if (type === 'warning') typeClass = 'log-warning';
        if (type === 'system') typeClass = 'log-system';

        line.innerHTML = `
            <span class="log-timestamp">[${timeString}]</span>
            <span class="log-content ${typeClass}">${message}</span>
        `;
        
        consoleContainer.appendChild(line);
        consoleContainer.scrollTop = consoleContainer.scrollHeight; // Auto-scroll para o final
    };

    const clearConsole = () => {
        consoleContainer.innerHTML = '';
        consoleContainer.style.display = 'none';
    };

    // --- Dropdowns ---
    const renderConvenios = (list) => {
        convenioList.innerHTML = '';
        list.forEach(convenio => {
            const li = document.createElement('li');
            li.textContent = convenio;
            li.setAttribute('data-value', convenio);
            li.addEventListener('click', () => handleConvenioSelection(convenio));
            convenioList.appendChild(li);
        });
    };
    renderConvenios(ALL_CONVENIOS);

    selectButton.addEventListener('click', (e) => { e.stopPropagation(); dropdownContent.classList.toggle('show'); });
    convenioSearch.addEventListener('input', (e) => {
        const query = e.target.value.toUpperCase();
        renderConvenios(ALL_CONVENIOS.filter(c => c.toUpperCase().includes(query)));
    });

    if (selectConsigButton) {
        selectConsigButton.addEventListener('click', (e) => { e.stopPropagation(); dropdownConsigContent.classList.toggle('show'); });
        consignatariaOptions.forEach(opt => {
            opt.addEventListener('click', () => {
                selectedConsignataria = opt.getAttribute('data-value');
                selectedConsigText.textContent = opt.textContent;
                dropdownConsigContent.classList.remove('show');
                updateSubmitButtonState();
            });
        });
    }

    document.addEventListener('click', () => {
        dropdownContent.classList.remove('show');
        if (dropdownConsigContent) dropdownConsigContent.classList.remove('show');
    });

    // --- Lógica de Seleção ---
    const handleConvenioSelection = (convenio) => {
        selectedConvenio = convenio;
        selectedConvenioText.textContent = convenio;
        dropdownContent.classList.remove('show');
        
        // Reset
        consignatariaArea.classList.add('hidden');
        selectedConsignataria = null;
        selectedConsigText.textContent = "Clique para Selecionar";
        for (const key in fileDataMap) delete fileDataMap[key];
        clearConsole(); // Limpa console anterior

        let currentFields = [];
        if (CONVENIOS_CODATA.includes(convenio)) {
            consignatariaArea.classList.remove('hidden');
            currentFields = FIELDS_CODATA;
        } else if (CONVENIOS_INSS.includes(convenio)) {
            currentFields = FIELDS_INSS;
        } else {
            currentFields = FIELDS_CONSIGFACIL;
        }

        uploadForm.classList.remove('hidden');
        renderUploadFields(currentFields); 
        updateSubmitButtonState();
    };

    // --- Upload Fields ---
    const renderUploadFields = (fieldsList) => {
        uploadFieldsGrid.innerHTML = '';
        fieldsList.forEach(field => {
            const fieldId = field.replace(/[^a-zA-Z0-9]/g, '_').toUpperCase();
            const html = `
                <div class="upload-group">
                    <label class="form-label">${field}</label>
                    <div class="upload-box" id="drop-area-${fieldId}">
                        <span class="iconify upload-icon" data-icon="lucide:file-text"></span>
                        <p class="upload-text-main">Arraste aqui</p>
                        <p class="file-info" id="file-info-${fieldId}">.CSV, .XLSX</p>
                        <input type="file" multiple accept=".csv, .xlsx, .xls" data-field-id="${fieldId}" id="input-${fieldId}" name="${fieldId}">
                    </div>
                </div>`;
            uploadFieldsGrid.insertAdjacentHTML('beforeend', html);
            setupFileHandlers(fieldId);
        });
    };

    const setupFileHandlers = (fieldId) => {
        const dropArea = document.getElementById(`drop-area-${fieldId}`);
        const input = document.getElementById(`input-${fieldId}`);
        const info = document.getElementById(`file-info-${fieldId}`);
        if (!dropArea) return;

        dropArea.addEventListener('click', (e) => { if(e.target !== input) input.click(); });
        input.addEventListener('change', (e) => handleFileProcess(e.target.files, fieldId, info));
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(ev => {
            dropArea.addEventListener(ev, (e) => { e.preventDefault(); e.stopPropagation(); });
        });
        dropArea.addEventListener('dragover', () => dropArea.classList.add('dragover'));
        dropArea.addEventListener('dragleave', () => dropArea.classList.remove('dragover'));
        dropArea.addEventListener('drop', (e) => handleFileProcess(e.dataTransfer.files, fieldId, info));
    };

    const handleFileProcess = (files, fieldId, info) => {
        if (files.length > 0) {
            fileDataMap[fieldId] = Array.from(files);
            const size = (Array.from(files).reduce((a, b) => a + b.size, 0) / 1024 / 1024).toFixed(2);
            info.textContent = `${files.length} arq. (${size} MB)`;
            info.classList.remove('error');
        } else {
            delete fileDataMap[fieldId];
            info.textContent = '.CSV, .XLSX';
        }
        updateSubmitButtonState();
    };

    const updateSubmitButtonState = () => {
        const hasFiles = Object.keys(fileDataMap).length > 0;
        let valid = !!selectedConvenio;
        if (selectedConvenio && CONVENIOS_CODATA.includes(selectedConvenio) && !selectedConsignataria) valid = false;
        submitButton.disabled = !hasFiles || !valid;
    };

    // ----------------------------------------------------
    // SUBMISSÃO COM CONSOLE VISUAL
    // ----------------------------------------------------
    uploadForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        
        // 1. Prepara Interface
        submitButton.disabled = true;
        submitButton.innerHTML = '<span class="iconify icon-spin" data-icon="lucide:loader-2"></span> Processando...';
        clearConsole();
        
        // 2. Logs Iniciais
        logToConsole(`Iniciando validação para: ${selectedConvenio}`, 'system');
        if (selectedConsignataria) logToConsole(`Consignatária selecionada: ${selectedConsignataria}`, 'info');
        
        const totalFiles = Object.values(fileDataMap).reduce((acc, val) => acc + val.length, 0);
        logToConsole(`Preparando ${totalFiles} arquivos para upload...`, 'info');

        try {
            // 3. Envio
            await sendFilesToBackend();
            
            // 4. Sucesso
            submitButton.innerHTML = '<span class="iconify" data-icon="lucide:check"></span> Sucesso!';
            submitButton.classList.add('success');
            
            setTimeout(() => {
                submitButton.innerHTML = '<span class="iconify" data-icon="lucide:upload-cloud"></span> Iniciar Validação';
                submitButton.classList.remove('success');
                submitButton.disabled = false;
            }, 4000);

        } catch (error) {
            // 5. Erro
            console.error(error);
            logToConsole(`FALHA NO PROCESSO: ${error.message}`, 'error');
            submitButton.innerHTML = '<span class="iconify" data-icon="lucide:alert-triangle"></span> Erro';
            submitButton.disabled = false;
        }
    });

    const sendFilesToBackend = async () => {
        const formData = new FormData();
        formData.append('convenio', selectedConvenio);
        if (selectedConsignataria) formData.append('consignataria', selectedConsignataria);

        // NOVO: PEGA O CAMINHO DE SAÍDA
        const outputPathInput = document.getElementById('output-path-input');
        if (outputPathInput && outputPathInput.value.trim() !== "") {
            formData.append('output_path', outputPathInput.value.trim());
            logToConsole(`Caminho de saída definido: ${outputPathInput.value.trim()}`, 'info');
        } else {
            logToConsole(`Usando pasta de saída padrão do sistema`, 'info');
        }

        // Log detalhado dos arquivos
        for (const [fieldId, files] of Object.entries(fileDataMap)) {
            files.forEach(file => {
                formData.append(fieldId, file, file.name);
                logToConsole(`Anexando: ${file.name} (${(file.size/1024).toFixed(1)}KB) -> [${fieldId}]`, 'info');
            });
        }

        logToConsole("Enviando dados para o servidor...", 'warning');
        logToConsole("Enviando dados para o servidor local (localhost:8000)...", 'warning');
        logToConsole("Aguardando processamento do Python... Isso pode levar alguns minutos.", 'warning');

        const response = await fetch('http://localhost:8000/validar', { method: 'POST', body: formData });

        if (!response.ok) {
            const err = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(err.detail || `Erro HTTP ${response.status}`);
        }

        const result = await response.json();
        
        // Logs de Sucesso vindos do servidor
        logToConsole("------------------------------------------------", 'system');
        logToConsole("PROCESSAMENTO CONCLUÍDO PELO SERVIDOR!", 'success');
        logToConsole(`Mensagem: ${result.message}`, 'success');
        
        if (result.output_path) {
            logToConsole(`Arquivos gerados salvos em:`, 'success');
            logToConsole(`${result.output_path}`, 'info');
        }
        
        return result;
    };
});