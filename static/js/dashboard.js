/**
 * TireTrack Dashboard Module
 * Обработка интерактивности дашборда
 */
const Dashboard = (function() {
    // Константы
    const API_BASE_URL = '/api';
    
    // DOM элементы
    let elements = {};
    
    // Состояние
    let state = {
        currentFilter: 'all',
        stats: null
    };

    // Инициализация
    function init() {
        collectElements();
        loadStats();
        loadRecentActions();
        setupEventListeners();
        console.log('Dashboard initialized');
    }

    // Сбор DOM элементов
    function collectElements() {
        elements = {
            totalTires: document.getElementById('total-tires'),
            mainWarehouseTires: document.getElementById('main-warehouse-tires'),
            ohWarehouseTires: document.getElementById('oh-warehouse-tires'),
            totalSuppliers: document.getElementById('total-suppliers'),
            recentActionsList: document.getElementById('recent-actions-list'),
            // Modal elements
            importModal: document.getElementById('importModal'),
            exportModal: document.getElementById('exportModal'),
            transferModal: document.getElementById('transferModal'),
            nomenclatureModal: document.getElementById('nomenclatureModal'),
            qrCodesModal: document.getElementById('qrCodesModal'),
            // Form elements
            importFileName: document.getElementById('import-file-name'),
            exportName: document.getElementById('export-name'),
            exportFormat: document.getElementById('export-format'),
            transferQrCodes: document.getElementById('transfer-qr-codes'),
            transferFromWarehouse: document.getElementById('transfer-from-warehouse'),
            transferToWarehouse: document.getElementById('transfer-to-warehouse'),
            nomenclatureName: document.getElementById('nomenclature-name'),
            nomenclatureManufacturer: document.getElementById('nomenclature-manufacturer'),
            nomenclatureSize: document.getElementById('nomenclature-size'),
            nomenclatureWarehouse: document.getElementById('nomenclature-warehouse'),
            nomenclatureQuantity: document.getElementById('nomenclature-quantity'),
            qrModalTitle: document.getElementById('qr-modal-title'),
            qrCount: document.getElementById('qr-count'),
            qrCodesGrid: document.getElementById('qr-codes-grid')
        };
    }

    // Загрузка статистики
    async function loadStats() {
        try {
            const response = await fetch(`${API_BASE_URL}/stats/`);
            if (response.ok) {
                const data = await response.json();
                updateStatsDisplay(data);
            } else {
                // Если API недоступен, используем симуляцию
                simulateStats();
            }
        } catch (error) {
            console.error('Error loading stats:', error);
            simulateStats();
        }
    }

    // Обновление отображения статистики
    function updateStatsDisplay(stats) {
        elements.totalTires.textContent = stats.total.toLocaleString();
        elements.mainWarehouseTires.textContent = stats.main_warehouse.toLocaleString();
        elements.ohWarehouseTires.textContent = stats.oh_warehouse.toLocaleString();
        elements.totalSuppliers.textContent = stats.total_suppliers.toLocaleString();
        state.stats = stats;
    }

    // Симуляция статистики
    function simulateStats() {
        elements.totalTires.textContent = '1,247';
        elements.mainWarehouseTires.textContent = '892';
        elements.ohWarehouseTires.textContent = '234';
        elements.totalSuppliers.textContent = '12';
    }

    // Загрузка последних действий
    async function loadRecentActions() {
        try {
            const response = await fetch(`${API_BASE_URL}/recent-actions/`);
            if (response.ok) {
                const actions = await response.json();
                renderRecentActions(actions);
            } else {
                // Если API недоступен, используем симуляцию
                const actions = getSampleActions();
                renderRecentActions(actions);
            }
        } catch (error) {
            console.error('Error loading recent actions:', error);
            const actions = getSampleActions();
            renderRecentActions(actions);
        }
    }

    // Получение выборки последних действий
    function getSampleActions() {
        return [
            {
                id: 1,
                type: 'receipt',
                title: 'Приемка шин',
                description: 'Поступило 50 шин Michelin 255/70R22.5 на основной склад',
                time: '2 минуты назад',
                icon: 'fa-box',
                color: 'bg-success'
            },
            {
                id: 2,
                type: 'writeoff',
                title: 'Списание шин',
                description: 'Списано 12 шин Bridgestone 315/80R22.5 со склада ОХ',
                time: '15 минут назад',
                icon: 'fa-minus-circle',
                color: 'bg-danger'
            },
            {
                id: 3,
                type: 'receipt',
                title: 'Импорт QR-кодов',
                description: 'Импортировано 45 шин из файла shipment_001.txt',
                time: '1 час назад',
                icon: 'fa-file-import',
                color: 'bg-primary'
            },
            {
                id: 4,
                type: 'transfer',
                title: 'Передача шин',
                description: 'Передано 25 шин между владельцами',
                time: '2 часа назад',
                icon: 'fa-exchange-alt',
                color: 'bg-info'
            },
            {
                id: 5,
                type: 'writeoff',
                title: 'Экспорт для ТСД',
                description: 'Экспортировано 20 шин для сканеров ТСД',
                time: '3 часа назад',
                icon: 'fa-file-export',
                color: 'bg-warning'
            }
        ];
    }

    // Рендер последних действий
    function renderRecentActions(actions) {
        // Фильтрация
        let filtered = actions;
        if (state.currentFilter !== 'all') {
            filtered = actions.filter(action => {
                if (state.currentFilter === 'receipt') return action.type === 'receipt';
                if (state.currentFilter === 'writeoff') return action.type === 'writeoff' || action.type === 'export';
                return true;
            });
        }

        // Генерация HTML
        const html = filtered.map(action => `
            <li class="recent-action-item neomorph-card">
                <div class="action-icon-circle ${action.color}">
                    <i class="fas ${action.icon}"></i>
                </div>
                <div class="action-content">
                    <div class="action-header">
                        <div class="action-title">${action.title}</div>
                        <div class="action-time">${action.time}</div>
                    </div>
                    <div class="action-desc">${action.description}</div>
                </div>
            </li>
        `).join('');

        elements.recentActionsList.innerHTML = html;
    }

    // Фильтрация действий
    window.filterActions = function(filter) {
        state.currentFilter = filter;
        
        // Обновление классов кнопок
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.textContent.toLowerCase().includes(filter === 'all' ? 'все' : 
                filter === 'receipt' ? 'пополнение' : 'списание')) {
                btn.classList.add('active');
            }
        });

        // Перерендер с фильтрацией
        const allActions = getSampleActions();
        renderRecentActions(allActions);
    };

    // Открытие модального окна импорта
    window.openImportModal = function() {
        const modal = new bootstrap.Modal(elements.importModal);
        modal.show();
    };

    // Отправка импорта
    window.submitImport = async function() {
        const fileInput = document.getElementById('import-file-input');
        if (fileInput.files.length === 0) {
            alert('Пожалуйста, выберите файл для импорта');
            return;
        }

        const file = fileInput.files[0];
        elements.importFileName.textContent = file.name;

        // Симуляция импорта
        const btn = elements.importModal.querySelector('.btn-primary');
        const originalText = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Импорт...';
        btn.disabled = true;

        setTimeout(() => {
            btn.innerHTML = originalText;
            btn.disabled = false;
            const modal = bootstrap.Modal.getInstance(elements.importModal);
            modal.hide();
            alert(`Файл "${file.name}" успешно импортирован!`);
        }, 1500);
    };

    // Открытие модального окна экспорта
    window.openExportModal = function() {
        const modal = new bootstrap.Modal(elements.exportModal);
        modal.show();
    };

    // Отправка экспорта
    window.submitExport = async function() {
        const exportName = elements.exportName.value;
        const exportFormat = elements.exportFormat.value;

        if (!exportName) {
            alert('Пожалуйста, укажите название пакета экспорта');
            return;
        }

        // Симуляция экспорта
        const btn = elements.exportModal.querySelector('.btn-success');
        const originalText = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Экспорт...';
        btn.disabled = true;

        setTimeout(() => {
            btn.innerHTML = originalText;
            btn.disabled = false;
            const modal = bootstrap.Modal.getInstance(elements.exportModal);
            modal.hide();
            alert(`Экспорт "${exportName}" успешно создан!`);
        }, 1500);
    };

    // Открытие модального окна передачи
    window.openTransferModal = function() {
        const modal = new bootstrap.Modal(elements.transferModal);
        modal.show();
    };

    // Отправка передачи
    window.submitTransfer = async function() {
        const qrCodes = elements.transferQrCodes.value.trim();
        const fromOwner = elements.transferFromOwner.value;
        const toOwner = elements.transferToOwner.value;

        if (!qrCodes || !fromOwner || !toOwner) {
            alert('Пожалуйста, заполните все обязательные поля');
            return;
        }

        if (fromOwner === toOwner) {
            alert('Владелец отправления и получателя не могут быть одинаковыми');
            return;
        }

        // Симуляция передачи
        const btn = elements.transferModal.querySelector('.btn-info');
        const originalText = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Передача...';
        btn.disabled = true;

        setTimeout(() => {
            btn.innerHTML = originalText;
            btn.disabled = false;
            const modal = bootstrap.Modal.getInstance(elements.transferModal);
            modal.hide();
            alert('Передача шин успешно выполнена!');
        }, 1500);
    };

    // Открытие модального окна номенклатуры
    window.openNomenclatureModal = function() {
        const modal = new bootstrap.Modal(elements.nomenclatureModal);
        modal.show();
    };

    // Отправка номенклатуры
    window.submitNomenclature = async function() {
        const name = elements.nomenclatureName.value;
        const manufacturer = elements.nomenclatureManufacturer.value;
        const size = elements.nomenclatureSize.value;
        const quantity = elements.nomenclatureQuantity.value;

        if (!name || !manufacturer || !size) {
            alert('Пожалуйста, заполните все обязательные поля');
            return;
        }

        // Симуляция сохранения
        const btn = elements.nomenclatureModal.querySelector('.btn-dark');
        const originalText = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Сохранение...';
        btn.disabled = true;

        setTimeout(() => {
            btn.innerHTML = originalText;
            btn.disabled = false;
            const modal = bootstrap.Modal.getInstance(elements.nomenclatureModal);
            modal.hide();
            alert(`Номенклатура "${name}" успешно сохранена!`);
        }, 1500);
    };

    // Показ QR кодов для номенклатуры
    window.showQRCodes = function(nomenclatureName) {
        elements.qrModalTitle.textContent = `QR коды для: ${nomenclatureName}`;
        
        // Генерация QR кодов (симуляция)
        const qrCount = 25;
        elements.qrCount.textContent = qrCount;

        const qrHtml = Array.from({ length: Math.min(qrCount, 8) }).map((_, i) => `
            <div class="neomorph-card p-3 d-flex flex-column align-items-center" style="cursor: pointer;">
                <div class="qr-image" style="width: 100px; height: 100px; background: white; display: flex; align-items: center; justify-content: center; border-radius: 12px; box-shadow: 4px 4px 8px rgba(0,0,0,0.1);">
                    <i class="fas fa-qrcode fa-2x text-primary"></i>
                </div>
                <small class="mt-2 text-muted">QR-${1000 + i}</small>
            </div>
        `).join('');

        elements.qrCodesGrid.innerHTML = qrHtml;

        const modal = new bootstrap.Modal(elements.qrCodesModal);
        modal.show();
    };

    // Экспорт QR кодов
    window.exportQRCodes = function() {
        const modal = bootstrap.Modal.getInstance(elements.qrCodesModal);
        modal.hide();
        alert('QR коды экспортированы!');
    };

    // Синхронизация с Честным Знаком
    window.syncHonestSign = async function() {
        const btn = document.querySelector('.honest-sign-section .neomorph-btn');
        const originalText = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Синхронизация...';
        btn.disabled = true;

        setTimeout(() => {
            btn.innerHTML = originalText;
            btn.disabled = false;
            alert('Синхронизация с "Честным Знаком" выполнена!');
        }, 1500);
    };

    // Настройка слушателей событий
    function setupEventListeners() {
        // Обработчик выбора файла для импорта
        document.getElementById('import-file-input').addEventListener('change', function(e) {
            if (e.target.files.length > 0) {
                const file = e.target.files[0];
                elements.importFileName.textContent = file.name;
                
                // Форматирование размера файла
                const size = formatFileSize(file.size);
                document.getElementById('import-file-size').textContent = size;
            } else {
                elements.importFileName.textContent = 'Файл не выбран';
                document.getElementById('import-file-size').textContent = '';
            }
        });

        // Обработчик drag and drop для импорта
        const dropArea = document.querySelector('.file-drop-area');
        dropArea.addEventListener('dragover', function(e) {
            e.preventDefault();
            this.classList.add('border-primary', 'bg-light');
        });

        dropArea.addEventListener('dragleave', function() {
            this.classList.remove('border-primary', 'bg-light');
        });

        dropArea.addEventListener('drop', function(e) {
            e.preventDefault();
            this.classList.remove('border-primary', 'bg-light');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                const fileInput = document.getElementById('import-file-input');
                fileInput.files = files;
                
                // Триггерим событие change
                const event = new Event('change', { bubbles: true });
                fileInput.dispatchEvent(event);
            }
        });
    }

    // Форматирование размера файла
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Экспорт публичных методов
    return {
        init,
        loadStats,
        renderRecentActions
    };
})();
