// Основной JavaScript файл для TireTrack

// Глобальные переменные
const API_BASE_URL = '/api';

// Получение cookie по имени
function getCookie(name) {
    const cookieValue = document.cookie.match('(^|;) ?' + name + '=([^;]*)(;|$)');
    return cookieValue ? cookieValue[2] : null;
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    console.log('TireTrack app initialized');
    
    // Инициализация тултипов
    initializeTooltips();
    
    // Инициализация обработчиков событий
    initializeEventHandlers();
    
    // Настройка HTMX CSRF
    setupHtmxCsrf();
    
    // Инициализация обработчиков кнопок удаления
    initializeDeleteHandlers();
});

// Настройка HTMX CSRF token
function setupHtmxCsrf() {
    // Проверяем, загружен ли HTMX (ожидаем до 5 секунд)
    const checkHtmxLoaded = setInterval(function() {
        if (typeof htmx !== 'undefined') {
            clearInterval(checkHtmxLoaded);
            htmx.on('htmx:configRequest', function(evt) {
                // Добавляем CSRF token в заголовки
                evt.detail.headers['X-CSRFToken'] = getCookie('csrftoken');
            });
            console.log('HTMX CSRF настройка завершена');
        }
    }, 100);
    
    // Таймаут на случай проблем с загрузкой HTMX
    setTimeout(function() {
        clearInterval(checkHtmxLoaded);
    }, 5000);
}

// Инициализация тултипов Bootstrap
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Инициализация обработчиков событий
function initializeEventHandlers() {
    // Обработчик для файлов импорта
    const fileInputs = document.querySelectorAll('.file-input');
    fileInputs.forEach(input => {
        input.addEventListener('change', handleFileSelect);
    });
    
    // Обработчик для drag and drop зон
    const dropAreas = document.querySelectorAll('.file-drop-area');
    dropAreas.forEach(area => {
        initializeDropArea(area);
    });
    
    // Обработчик для кнопок сканирования QR
    const scanButtons = document.querySelectorAll('[data-action="scan-qr"]');
    scanButtons.forEach(button => {
        button.addEventListener('click', openQRScanner);
    });
    
    // Обработчики кнопок удаления
    initializeDeleteHandlers();
}

// Обработчик выбора файла
function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        const fileName = file.name;
        const fileSize = formatFileSize(file.size);
        
        // Обновляем отображение файла
        const dropArea = event.target.closest('.file-drop-area');
        if (dropArea) {
            dropArea.querySelector('.file-name').textContent = fileName;
            dropArea.querySelector('.file-size').textContent = fileSize;
            dropArea.classList.add('active');
        }
        
        console.log(`Selected file: ${fileName} (${fileSize})`);
    }
}

// Инициализация drag and drop зоны
function initializeDropArea(dropArea) {
    dropArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        dropArea.classList.add('active');
    });
    
    dropArea.addEventListener('dragleave', function() {
        dropArea.classList.remove('active');
    });
    
    dropArea.addEventListener('drop', function(e) {
        e.preventDefault();
        dropArea.classList.remove('active');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            // Создаем событие change для input файла
            const fileInput = dropArea.querySelector('input[type="file"]');
            if (fileInput) {
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(files[0]);
                fileInput.files = dataTransfer.files;
                
                // Триггерим событие change
                const event = new Event('change', { bubbles: true });
                fileInput.dispatchEvent(event);
            }
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

// Открытие сканера QR-кодов
function openQRScanner() {
    console.log('Opening QR scanner...');
    
    // Проверяем поддержку getUserMedia
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        alert('Ваш браузер не поддерживает доступ к камере. Пожалуйста, используйте современный браузер.');
        return;
    }
    
    // Создаем модальное окно для сканера
    createQRScannerModal();
}

// Создание модального окна сканера QR
function createQRScannerModal() {
    // Проверяем, существует ли уже модальное окно
    let modal = document.getElementById('qr-scanner-modal');
    if (modal) {
        bootstrap.Modal.getInstance(modal).show();
        return;
    }
    
    // Создаем HTML модального окна
    const modalHTML = `
        <div class="modal fade" id="qr-scanner-modal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-camera"></i> Сканер QR-кодов
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div class="qr-scanner-container">
                            <video id="qr-video" class="scanner-video" autoplay playsinline></video>
                            <div class="qr-overlay"></div>
                        </div>
                        <div class="scanner-controls mt-3">
                            <button id="start-camera" class="btn btn-primary">
                                <i class="fas fa-video"></i> Включить камеру
                            </button>
                            <button id="stop-camera" class="btn btn-secondary" disabled>
                                <i class="fas fa-video-slash"></i> Выключить камеру
                            </button>
                        </div>
                        <div class="scanner-result mt-3">
                            <h6>Результат сканирования:</h6>
                            <div id="scan-result" class="alert alert-info">
                                Наведите камеру на QR-код
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                            Закрыть
                        </button>
                        <button id="use-scan-result" class="btn btn-primary" disabled>
                            Использовать результат
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Добавляем модальное окно в DOM
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    // Инициализируем модальное окно
    modal = document.getElementById('qr-scanner-modal');
    const modalInstance = new bootstrap.Modal(modal);
    
    // Добавляем обработчики событий
    document.getElementById('start-camera').addEventListener('click', startCamera);
    document.getElementById('stop-camera').addEventListener('click', stopCamera);
    document.getElementById('use-scan-result').addEventListener('click', useScanResult);
    
    // Показываем модальное окно
    modalInstance.show();
    
    // Очищаем ресурсы при закрытии модального окна
    modal.addEventListener('hidden.bs.modal', function() {
        stopCamera();
        modal.remove();
    });
}

// Запуск камеры для сканирования QR
let stream = null;
let video = null;

function startCamera() {
    video = document.getElementById('qr-video');
    
    navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } })
        .then(function(mediaStream) {
            stream = mediaStream;
            video.srcObject = stream;
            
            // Включаем кнопки
            document.getElementById('start-camera').disabled = true;
            document.getElementById('stop-camera').disabled = false;
            
            // Начинаем сканирование
            startQRScanning();
        })
        .catch(function(err) {
            console.error("Ошибка доступа к камере: ", err);
            alert('Не удалось получить доступ к камере. Пожалуйста, проверьте разрешения.');
        });
}

// Остановка камеры
function stopCamera() {
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
        stream = null;
    }
    
    if (video) {
        video.srcObject = null;
    }
    
    // Отключаем кнопки
    document.getElementById('start-camera').disabled = false;
    document.getElementById('stop-camera').disabled = true;
    document.getElementById('use-scan-result').disabled = true;
}

// Начало сканирования QR-кодов
function startQRScanning() {
    // В реальном приложении здесь будет библиотека для сканирования QR
    // Например, jsQR или ZXing
    
    // Пока используем симуляцию
    simulateQRScanning();
}

// Симуляция сканирования QR-кода
function simulateQRScanning() {
    // Симуляция нахождения QR-кода через 3 секунды
    setTimeout(function() {
        if (stream) { // Проверяем, что камера все еще активна
            const result = "QR1234567890"; // Симулированный результат
            document.getElementById('scan-result').innerHTML = `
                <strong>Найден QR-код:</strong> ${result}
                <br><small class="text-muted">Сканировано автоматически</small>
            `;
            document.getElementById('scan-result').className = 'alert alert-success';
            document.getElementById('use-scan-result').disabled = false;
        }
    }, 3000);
}

// Использование результата сканирования
function useScanResult() {
    const result = document.getElementById('scan-result').textContent;
    console.log('Using scan result:', result);
    
    // Закрываем модальное окно
    const modal = bootstrap.Modal.getInstance(document.getElementById('qr-scanner-modal'));
    modal.hide();
    
    // Здесь можно добавить логику использования результата
    // Например, заполнение поля формы или отправка данных на сервер
}

// Функции для работы с API
const API = {
    // Получение статистики
    getStats: async function() {
        try {
            const response = await fetch(`${API_BASE_URL}/stats/`);
            if (response.ok) {
                return await response.json();
            }
            throw new Error('Failed to fetch stats');
        } catch (error) {
            console.error('Error fetching stats:', error);
            return null;
        }
    },
    
    // Импорт QR-кодов
    importQRs: async function(formData) {
        try {
            const response = await fetch(`${API_BASE_URL}/qr/import/`, {
                method: 'POST',
                body: formData
            });
            return await response.json();
        } catch (error) {
            console.error('Error importing QRs:', error);
            return { error: 'Failed to import QR codes' };
        }
    },
    
    // Экспорт QR-кодов
    exportQRs: async function(exportData) {
        try {
            const response = await fetch(`${API_BASE_URL}/qr/export/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(exportData)
            });
            return await response.json();
        } catch (error) {
            console.error('Error exporting QRs:', error);
            return { error: 'Failed to export QR codes' };
        }
    }
};

// Экспорт функций для использования в других модулях
window.TireTrack = {
    API,
    utils: {
        formatFileSize
    }
};

// Добавление товара в документ
function addItemToDocument(button) {
    const productName = button.getAttribute('data-product-name');
    const documentId = button.getAttribute('data-document-id');
    
    if (!productName) {
        console.error('productName не указан');
        return;
    }
    
    if (!documentId) {
        console.error('documentId не указан');
        return;
    }
    
    // Получаем CSRF token из meta тега или cookies
    const csrfToken = document.querySelector('meta[name=csrf-token]')?.getAttribute('content') ||
                     getCookie('csrftoken');
    
    if (!csrfToken) {
        console.error('CSRF token не найден');
        return;
    }
    
    // Отправляем POST запрос
    fetch(`/warehouse/documents/${documentId}/add-item/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': csrfToken
        },
        body: new URLSearchParams({
            'product_name': productName
        })
    })
    .then(response => {
        if (response.ok) {
            return response.text();
        }
        throw new Error('Ошибка добавления товара');
    })
    .then(html => {
        // Обновляем таблицу товаров
        const table = document.getElementById('documentItemsTable');
        if (table) {
            table.innerHTML = html;
        }
        
        // Закрываем модальное окно
        const modalElement = document.getElementById('addItemModal');
        if (modalElement) {
            const modal = bootstrap.Modal.getInstance(modalElement);
            if (modal) {
                modal.hide();
            }
        }
        
        console.log('Товар добавлен успешно');
    })
    .catch(error => {
        console.error('Ошибка:', error);
        alert('Ошибка при добавлении товара: ' + error.message);
    });
}

// Получение cookie по имени
function getCookie(name) {
    const cookieValue = document.cookie.match('(^|;) ?' + name + '=([^;]*)(;|$)');
    return cookieValue ? cookieValue[2] : null;
}

// Инициализация обработчиков кнопок удаления
function initializeDeleteHandlers() {
    // Удаление документа
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('delete-document-btn')) {
            e.preventDefault();
            
            const documentId = e.target.dataset.documentId;
            const documentNumber = e.target.dataset.documentNumber;
            const csrfToken = e.target.dataset.csrfToken;
            
            showDeleteDocumentModal(documentId, documentNumber, csrfToken);
        }
    });
    
    // Удаление позиции из документа
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('delete-document-item-btn')) {
            e.preventDefault();
            
            const documentId = e.target.dataset.documentId;
            const itemId = e.target.dataset.itemId;
            const productName = e.target.dataset.productName;
            const csrfToken = e.target.dataset.csrfToken;
            
            showDeleteItemModal(documentId, itemId, productName, csrfToken);
        }
    });
}

// Показать модальное окно подтверждения удаления документа
function showDeleteDocumentModal(documentId, documentNumber, csrfToken) {
    // Проверяем, существует ли уже модальное окно
    let modal = document.getElementById('deleteDocumentModal');
    if (modal) {
        modal.remove();
    }
    
    // Создаем HTML модального окна
    const modalHTML = `
        <div class="modal fade" id="deleteDocumentModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-trash text-danger"></i> Удаление документа
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <p>Вы уверены, что хотите удалить документ <strong>"${documentNumber}"</strong>?</p>
                        <p class="text-muted">Это действие нельзя отменить.</p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
                        <button type="button" class="btn btn-danger" id="confirmDeleteDocument">Удалить</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Добавляем модальное окно в DOM
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    // Инициализируем модальное окно
    modal = document.getElementById('deleteDocumentModal');
    const modalInstance = new bootstrap.Modal(modal);
    
    // Добавляем обработчик подтверждения
    document.getElementById('confirmDeleteDocument').addEventListener('click', function() {
        deleteDocument(documentId, csrfToken);
        modalInstance.hide();
    });
    
    // Показываем модальное окно
    modalInstance.show();
}

// Удаление документа
function deleteDocument(documentId, csrfToken) {
    fetch(`/warehouse/documents/${documentId}/delete/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': csrfToken,
            'HX-Request': 'true'
        },
        body: new URLSearchParams({})
    })
    .then(response => {
        if (response.ok) {
            // Обновляем список документов
            const documentRow = document.getElementById(`document-${documentId}`);
            if (documentRow) {
                documentRow.remove();
            }
            
            // Показываем сообщение об успехе
            const alertHTML = `
                <div class="alert alert-success alert-dismissible fade show" role="alert">
                    <i class="fas fa-check-circle"></i> Документ успешно удалён
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>
            `;
            document.querySelector('.container.mt-4')?.insertAdjacentHTML('afterbegin', alertHTML);
        } else {
            throw new Error('Ошибка удаления документа');
        }
    })
    .catch(error => {
        console.error('Ошибка:', error);
        alert('Ошибка при добавлении товара: ' + error.message);
    });
}

// Показать модальное окно подтверждения удаления позиции
function showDeleteItemModal(documentId, itemId, productName, csrfToken) {
    // Проверяем, существует ли уже модальное окно
    let modal = document.getElementById('deleteItemModal');
    if (modal) {
        modal.remove();
    }
    
    // Создаем HTML модального окна
    const modalHTML = `
        <div class="modal fade" id="deleteItemModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-trash text-danger"></i> Удаление позиции
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <p>Вы уверены, что хотите удалить позицию <strong>"${productName}"</strong>?</p>
                        <p class="text-muted">Это действие нельзя отменить.</p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
                        <button type="button" class="btn btn-danger" id="confirmDeleteItem">Удалить</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Добавляем модальное окно в DOM
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    // Инициализируем модальное окно
    modal = document.getElementById('deleteItemModal');
    const modalInstance = new bootstrap.Modal(modal);
    
    // Добавляем обработчик подтверждения
    document.getElementById('confirmDeleteItem').addEventListener('click', function() {
        deleteDocumentItem(documentId, itemId, csrfToken);
        modalInstance.hide();
    });
    
    // Показываем модальное окно
    modalInstance.show();
}

// Удаление позиции из документа
function deleteDocumentItem(documentId, itemId, csrfToken) {
    fetch(`/warehouse/documents/${documentId}/delete-item/${itemId}/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': csrfToken,
            'HX-Request': 'true'
        },
        body: new URLSearchParams({})
    })
    .then(response => {
        if (response.ok) {
            // Обновляем таблицу товаров
            const tableBody = document.querySelector('#documentItemsTable tbody');
            if (tableBody) {
                // Ищем строку с этой позицией
                const rows = tableBody.querySelectorAll('tr');
                rows.forEach(row => {
                    const cell = row.querySelector('td:last-child button.delete-document-item-btn');
                    if (cell && cell.dataset.itemId == itemId) {
                        row.remove();
                    }
                });
            }
            
            // Показываем сообщение об успехе
            const alertHTML = `
                <div class="alert alert-success alert-dismissible fade show" role="alert">
                    <i class="fas fa-check-circle"></i> Позиция успешно удалена
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>
            `;
            document.querySelector('.container.mt-4')?.insertAdjacentHTML('afterbegin', alertHTML);
        } else {
            throw new Error('Ошибка удаления позиции');
        }
    })
    .catch(error => {
        console.error('Ошибка:', error);
        alert('Ошибка при добавлении товара: ' + error.message);
    });
}