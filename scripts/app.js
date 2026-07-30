document.addEventListener('DOMContentLoaded', () => {
    // ----------------------------------------------------
    // CONFIGURAÇÃO DE DADOS
    // ----------------------------------------------------
    
    // Grupos de Convênios
    const CONVENIOS_CODATA = ["GOV. PARAÍBA"];
    const CONVENIOS_INSS = ["INSS"];
    const CONVENIOS_CONSIGFACIL = ["GOV. MARANHÃO", "GOV. MATO GROSSO","GOV. PERNAMBUCO","GOV. PIAUÍ", "PREF. BAYEUX", "PREF. CAJAMAR",
                                   "PREF. CAMPINA GRANDE", "PREF. CAMPO GRANDE", "PREF. CUIABÁ", "PREF. PORTO VELHO",
                                   "PREF. IMPERATRIZ MA", "PREF. ITU", "PREF. JOÃO PESSOA", "PREF. JUAZEIRO DO NORTE",
                                   "PREF. MARABÁ", "PREF. NITERÓI", "PREF. PAÇO DO LUMIAR", "PREF. PALMAS", "PREF. RECIFE",
                                   "PREF. SANTA RITA", "PREF. TERESINA", "CÂMARA DE TERESÓPOLIS", "GOV. RIO GRANDE DO NORTE", "PREF. NATAL",
                                   "PREF. TUTÓIA"
                                  ];
    const CONVENIOS_SERHA = ["GOV. MINAS GERAIS - IPSM", "GOV. MINAS GERAIS - CBMMG", "GOV. MINAS GERAIS - PMMG", 
                             "GOV. MINAS GERAIS - SEPLAG", "GOV. MINAS GERAIS - IPSEMG"];

    const CONVENIOS_CONSIGLOG = ["GOV. BAHIA", "PREF. ARAGUAÍNA", "PREF. DUQUE DE CAXIAS", "PREF. DUQUE DE CAXIAS - IMPDC", 
                                 "PREF. GOIÂNIA", "PREVIDÊNCIA SÃO GONÇALO", "PREF. RIBEIRÃO PRETO"];

    const CONVENIOS_ZETRA = ["GOV. ESPÍRITO SANTO", "GOV. PARANÁ", "GOV. RIO DE JANEIRO", "PREF. BELO HORIZONTE", "PREF. AÇAILÂNDIA", "PREF. BARBACENA",
                             "PREF. CAMPINAS", "PREF. MACAÉ", "PREF. SÃO JOSE DE RIBAMAR", "PREF. SÃO PAULO-HMSP", "PREF. SOBRAL", "PREVIPALMAS",
                             "GOV. ALAGOAS - TJAL"];

    const TO_IGEPREV = ["GOV. TOCANTINS e IGEPREV"];

    const CONVENIOS_RF1 = ["PREF. ANANINDEUA"];

    const CONVENIOS_INFOCONSIG = ["PREF. ÁGUAS LINDAS DE GOIÁS", "PREF. PIRACICABA", "PREF. FLORIANÓPOLIS", 
                                  "SEMAE - SERVIÇO MUNICIPAL DE ÁGUA E ESGOTO DE PIRACICABA", "PREV. PIRACICABA IPASP",
                                 ];

    const CONVENIOS_CIP = ["PREF. SÃO PAULO", "GOV. SÃO PAULO"];

    const CONVENIOS_SIGRH = ["GOV. SANTA CATARINA"];

    const CONVENIOS_CONSIGI_KONEXIA = ["PREF. CONTAGEM", "PREF. PLANALTINA"];

    const CONVENIOS_NEOCONSIG = ["GOV. GOIÁS", "PREF. SÃO GONÇALO", "PREF. SÃO LUÍS", "PREF. SOROCABA"];

    const CONVENIOS_QUANTUM = ["PREF. SÃO JOSÉ DO RIO PRETO", "PREVIDÊNCIA SÃO JOSÉ DO RIO PRETO", "CÂMARA MUNICIPAL DE TERESÓPOLIS", "PREF. JUÍZ DE FORA"];

    const CONVENIOS_SAFECONSIG = ["PREF. TAUBATÉ", "PREF. SANTOS", "GOV. CEARÁ", "GOV. ALAGOAS"];

    const CONVENIOS_LINECONSIG = ["PREF. PICOS", "PREV. PICOS"];

    const ALL_CONVENIOS = [...CONVENIOS_CODATA, ...CONVENIOS_INSS, ...CONVENIOS_CONSIGFACIL, ...CONVENIOS_SERHA, ...TO_IGEPREV, ...CONVENIOS_ZETRA, ...CONVENIOS_RF1, 
        ...CONVENIOS_INFOCONSIG, ...CONVENIOS_CONSIGLOG, ...CONVENIOS_SIGRH, ...CONVENIOS_CONSIGI_KONEXIA, ...CONVENIOS_CIP, ...CONVENIOS_NEOCONSIG, ...CONVENIOS_QUANTUM, ...CONVENIOS_SAFECONSIG,
        ...CONVENIOS_LINECONSIG].sort();

    const FIELDS_CONSIGFACIL = ["FRONT", "FUNCAO", "XAO", "CONCILIACAO", "KOBRAKI", "TACS", "EXTRA-JUDICIAL", "ANDAMENTO", "AVERBADOS", "ORBITAL"];
    const FIELDS_SAFECONSIG = ["FRONT", "FUNCAO", "XAO", "CONCILIACAO", "KOBRAKI", "TACS", "EXTRA-JUDICIAL", "AVERBADOS", "ORBITAL"];
    const FIELDS_CODATA = ["FRONT", "FUNCAO", "XAO", "CONCILIACAO", "KOBRAKI", "TACS", "EXTRA-JUDICIAL", "ANDAMENTO", "AVERBADOS", "ORBITAL"];
    const FIELDS_INSS = ["FRONT", "FUNCAO", "CONCILIACAO", "KOBRAKI", "TACS", "EXTRA-JUDICIAL", "AVERBADOS", "CASOS_CAPITAL", "ORBITAL", "D8"];
    const FIELDS_SERHA = ["FRONT", "FUNCAO", "XAO", "CONCILIACAO", "KOBRAKI", "TACS", "EXTRA-JUDICIAL", "AVERBADOS", "TRABALHADO_ANTERIOR", "COMPLEMENTAR", "ORBITAL"];
    const FIELDS_ZETRA = ["FRONT", "FUNCAO", "XAO", "CONCILIACAO", "KOBRAKI", "TACS", "EXTRA-JUDICIAL", "AVERBADOS", "HISTORICO", "ORBITAL"];
    const FIELDS_CONSIGLOG = ["FRONT", "FUNCAO", "XAO", "CONCILIACAO", "KOBRAKI", "TACS", "EXTRA-JUDICIAL", "AVERBADOS", "ORBITAL"];
    const FIELDS_INFOCONSIG = ["FRONT", "FUNCAO", "XAO", "CONCILIACAO", "KOBRAKI", "TACS", "EXTRA-JUDICIAL", "AVERBADOS", "ORBITAL"];
    const FIELDS_TO_IGEPREV = ["FRONT", "FUNCAO", "AVERBADOS_TO", "AVERBADOS_IGEPREV", "D8_TO", "D8_IGEPREV", "XAO", "CONCILIACAO", "KOBRAKI", "TACS", "EXTRA-JUDICIAL"];
    const FIELDS_RF1 = ["FRONT", "FUNCAO", "AVERBADOS", "XAO", "CONCILIACAO", "KOBRAKI", "TACS", "EXTRA-JUDICIAL"];
    const FIELDS_CIP = ["FRONT", "FUNCAO", "AVERBADOS", "XAO", "CONCILIACAO", "KOBRAKI", "TACS", "EXTRA-JUDICIAL", "ORBITAL"];
    const FIELDS_SIGRH = ["FRONT", "FUNCAO", "AVERBADOS_SC_CAPITAL", "AVERBADOS_SC_CLICK", "ANDAMENTO_SC_CAPITAL", "ANDAMENTO_SC_CLICK", "XAO", "CONCILIACAO", "KOBRAKI", "TACS", "EXTRA-JUDICIAL", "ORBITAL"];
    const FIELDS_CONSIG_KONEXIA = ["FRONT", "FUNCAO", "XAO", "CONCILIACAO", "KOBRAKI", "TACS", "EXTRA-JUDICIAL", "AVERBADOS", "ORBITAL"];
    const FIELDS_NEOCONSIG = ["FRONT", "FUNCAO", "XAO", "CONCILIACAO", "KOBRAKI", "TACS", "EXTRA-JUDICIAL", "AVERBADOS", "ORBITAL"];
    const FIELDS_QUANTUM = ["FRONT", "FUNCAO", "XAO", "CONCILIACAO", "KOBRAKI", "TACS", "EXTRA-JUDICIAL", "AVERBADOS", "ORBITAL"];
    const FIELDS_LINECONSIG = ["FRONT", "FUNCAO", "XAO", "CONCILIACAO", "KOBRAKI", "TACS", "EXTRA-JUDICIAL", "AVERBADOS", "ORBITAL"];

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

    const rubricaArea = document.getElementById('rubrica-selection-area');
    const selectRubricaButton = document.getElementById('select-rubrica-button');
    const dropdownRubricaContent = document.getElementById('rubrica-dropdown');
    const selectedRubricaText = document.getElementById('selected-rubrica-text');
    const rubricaOptions = document.querySelectorAll('#rubrica-list li');

    const uploadForm = document.getElementById('upload-form');
    const uploadFieldsGrid = uploadForm ? uploadForm.querySelector('.upload-fields-grid') : null;
    const submitButton = document.getElementById('submit-validation');
    
    // Console Elements
    const consoleContainer = document.getElementById('system-console');

    const themeToggleButton = document.getElementById('theme-toggle');
    const themeIcon = document.getElementById('theme-icon');

    let selectedConvenio = null;
    let selectedConsignataria = null;
    let selectedRubrica = null;

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

    const exibirAlertaUsuario = (mensagem) => {
        // Usamos o tipo 'error' para a mensagem do Gemini se destacar em vermelho
        logToConsole(`FALHA NO PROCESSAMENTO: ${mensagem}`, 'error');
    };

    const exibirSucesso = (mensagem) => {
        // Usamos o tipo 'success' para a mensagem de conclusão
        logToConsole(mensagem, 'success');
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
    convenioSearch.addEventListener('click', (e) => {
    // Isso impede que o clique chegue ao 'document' e dispare o fechamento
    e.stopPropagation(); 
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

    if (selectRubricaButton) {
        selectRubricaButton.addEventListener('click', (e) => { e.stopPropagation(); dropdownRubricaContent.classList.toggle('show'); });
        rubricaOptions.forEach(opt => {
            opt.addEventListener('click', () => {
                selectedRubrica = opt.getAttribute('data-value');
                selectedRubricaText.textContent = opt.textContent;
                dropdownRubricaContent.classList.remove('show');
                updateSubmitButtonState();
            });
        });
    }

    document.addEventListener('click', () => {
        dropdownContent.classList.remove('show');
        if (dropdownConsigContent) dropdownConsigContent.classList.remove('show');
    });

    document.addEventListener('click', () => {
        dropdownContent.classList.remove('show');
        if (dropdownRubricaContent) dropdownRubricaContent.classList.remove('show');
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
        rubricaArea.classList.add('hidden');
        selectedRubrica = null;
        selectedRubricaText.textContent = "Clique para Selecionar a rubrica";
        for (const key in fileDataMap) delete fileDataMap[key];
        clearConsole(); // Limpa console anterior

        let currentFields = [];
        if (CONVENIOS_CODATA.includes(convenio)) {
            consignatariaArea.classList.remove('hidden');
            currentFields = FIELDS_CODATA;
        }else if (CONVENIOS_CONSIGLOG.includes(convenio)) {
            consignatariaArea.classList.remove('hidden');
            currentFields = FIELDS_CONSIGLOG;
        } else if (CONVENIOS_INSS.includes(convenio)) {
            currentFields = FIELDS_INSS;
        } else if (CONVENIOS_SERHA.includes(convenio)) {
            rubricaArea.classList.remove('hidden');
            currentFields = FIELDS_SERHA;
        } else if (CONVENIOS_INFOCONSIG.includes(convenio)) {
            rubricaArea.classList.remove('hidden')
            consignatariaArea.classList.remove('hidden');
            currentFields = FIELDS_INFOCONSIG;
        }else if (CONVENIOS_ZETRA.includes(convenio)){
            consignatariaArea.classList.remove('hidden');
            currentFields = FIELDS_ZETRA;
        } else if (TO_IGEPREV.includes(convenio)){
            currentFields = FIELDS_TO_IGEPREV;
        } else if (CONVENIOS_CONSIGFACIL.includes(convenio)){
            currentFields = FIELDS_CONSIGFACIL;
        } else if (CONVENIOS_RF1.includes(convenio)){
            consignatariaArea.classList.remove('hidden');
            currentFields = FIELDS_RF1;
        } else if (CONVENIOS_CIP.includes(convenio)) {
            currentFields = FIELDS_CIP;
        } else if (CONVENIOS_SIGRH.includes(convenio)){
            consignatariaArea.classList.remove('hidden');
            currentFields = FIELDS_SIGRH;
        } else if (CONVENIOS_CONSIGI_KONEXIA.includes(convenio)) {
            consignatariaArea.classList.remove('hidden');
            currentFields = FIELDS_CONSIG_KONEXIA;
        } else if (CONVENIOS_NEOCONSIG.includes(convenio)) {
            consignatariaArea.classList.remove('hidden');
            currentFields = FIELDS_NEOCONSIG;
        } else if (CONVENIOS_QUANTUM.includes(convenio)) {
            consignatariaArea.classList.remove('hidden');
            currentFields = FIELDS_QUANTUM;
        } else if (CONVENIOS_SAFECONSIG.includes(convenio)) {
            currentFields = FIELDS_SAFECONSIG;
        } else if (CONVENIOS_LINECONSIG.includes(convenio)) {
            consignatariaArea.classList.remove('hidden');
            currentFields = FIELDS_LINECONSIG;
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
            
            // --- IDENTIFICAÇÃO EXATA DO CAMPO ---
            const isZipField = field.toUpperCase() === "ZIPS";
            
            // Atributos: Se for ZIPS, aceita pastas e .zip. Se não, apenas planilhas.
            // Adicionamos text/html e as strings vazias para o navegador não bloquear o HTML disfarçado
            const attrs = isZipField 
                ? 'webkitdirectory directory accept=".zip"' 
                : 'accept=".csv,.xlsx,.xls,text/html,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"';
                
            const icon = isZipField ? 'lucide:folder-archive' : 'lucide:file-text';
            const helpText = isZipField ? '.ZIP ou Selecionar Pasta' : '.CSV,.XLSX,.XLS';

            const html = `
                <div class="upload-group">
                    <label class="form-label">${field}</label>
                    <div class="upload-box" id="drop-area-${fieldId}">
                        <span class="iconify upload-icon" data-icon="${icon}"></span>
                        <p class="upload-text-main">Arraste aqui</p>
                        <p class="file-info" id="file-info-${fieldId}">${helpText}</p>
                        <input type="file" multiple ${attrs} data-field-id="${fieldId}" id="input-${fieldId}" name="${fieldId}">
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
            info.textContent = '.CSV,.XLSX,.XLS';
        }
        updateSubmitButtonState();
    };

    const updateSubmitButtonState = () => {
        const hasFiles = Object.keys(fileDataMap).length > 0;
        let valid = !!selectedConvenio;
        if (selectedConvenio && CONVENIOS_CODATA.includes(selectedConvenio)) {
            if (!selectedConsignataria) valid = false;
        }
        else if (selectedConvenio && CONVENIOS_CONSIGLOG.includes(selectedConvenio))  {
            if (!selectedConsignataria) valid = false;
        }
        
        else if (selectedConvenio && CONVENIOS_ZETRA.includes(selectedConvenio)) {
            if (!selectedConsignataria) valid = false;
        }

        else if (selectedConvenio && CONVENIOS_SERHA.includes(selectedConvenio)) {
            if (!selectedRubrica) valid = false;
        }
        else if (selectedConvenio && CONVENIOS_INFOCONSIG.includes(selectedConvenio)) {
            if (!selectedConsignataria) valid = false;
            if (!selectedRubrica) valid = false;
        }
        else if (selectedConvenio && CONVENIOS_SIGRH.includes(selectedConvenio)){
            if (!selectedConsignataria) valid = false;
        }
        else if (selectedConvenio && CONVENIOS_CONSIGI_KONEXIA.includes(selectedConvenio)){
            if (!selectedConsignataria) valid = false;
        }
        else if (selectedConvenio && CONVENIOS_NEOCONSIG.includes(selectedConvenio)){
            if (!selectedConsignataria) valid = false;
        }
        else if (selectedConvenio && CONVENIOS_QUANTUM.includes(selectedConvenio)){
            if (!selectedConsignataria) valid = false;
        }
        else if (selectedConvenio && CONVENIOS_LINECONSIG.includes(selectedConvenio)){
            if (!selectedConsignataria) valid = false;
        }
        submitButton.disabled = !(hasFiles && valid);
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
        if (selectedRubrica) logToConsole(`Rubrica selecionada: ${selectedRubrica}`, 'info');
        
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
        // --- PASSO 1: DEBUG DE CONFERÊNCIA ---
        console.log("Estado atual do fileDataMap:", fileDataMap);

        const formData = new FormData();
        formData.append('convenio', selectedConvenio);
        if (selectedConsignataria) formData.append('consignataria', selectedConsignataria);
        if (selectedRubrica) formData.append('rubrica', selectedRubrica);

        // Anexando arquivos
        for (const [fieldId, files] of Object.entries(fileDataMap)) {
            files.forEach(file => {
                // Normaliza o nome do arquivo para garantir que a extensão esteja em minúsculo (.xls)
                const fileNameLower = file.name.toLowerCase();
                
                // --- PASSO 2: CORREÇÃO TÉCNICA PARA O .XLS (FORÇAR TIPO CORRETO) ---
                let fileToSend = file;
                if (fileNameLower.endsWith('.xls') && file.type !== 'application/vnd.ms-excel') {
                    logToConsole(`Corrigindo MIME Type legado para: ${file.name}`, 'warning');
                    // Recriamos o Blob forçando o cabeçalho correto que o FastAPI/Python espera
                    fileToSend = new File([file], file.name, { type: 'application/vnd.ms-excel' });
                }

                // Enviamos o arquivo tratado (ou original se for csv/xlsx)
                formData.append(fieldId, fileToSend, fileToSend.name);
                logToConsole(`Anexando: ${fileToSend.name} (${(fileToSend.size/1024).toFixed(1)}KB) -> [${fieldId}]`, 'info');
            });
        }

        logToConsole("Aguardando processamento do Python...", 'warning');

        try {
            const response = await fetch('/validar', { 
                method: 'POST', 
                body: formData 
            });

            const result = await response.json();

            if (response.ok) {
                logToConsole("------------------------------------------------", 'system');
                logToConsole("PROCESSAMENTO CONCLUÍDO PELO SERVIDOR!", 'success');
                logToConsole(`Mensagem: ${result.message}`, 'success');

                exibirSucesso(result.message || "Validação concluída com sucesso!");
                
                if (result.filename) {
                    logToConsole(`Baixando arquivo processado...`, 'success');
                    window.open(`/download/${result.filename}`, '_blank'); 
                }
                return result;

            } else {
                const mensagemIA = result.mensagem_amigavel;
                const erroTecnico = result.detail;
                exibirAlertaUsuario(mensagemIA || "Ocorreu um erro inesperado.");
                console.error("DEBUG TÉCNICO:", erroTecnico);
            }

        } catch (error) {
            console.error("Erro de conexão:", error);
            exibirAlertaUsuario("Não foi possível conectar ao servidor.");
            logToConsole("Erro crítico de conexão com o servidor.", 'error');
            return null;
        }
    };
});