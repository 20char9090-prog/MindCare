// =============================
// EXPORTACIÓN PDF Y EXCEL
// =============================
function exportToPDF(data, filename) {
    if (!window.jspdf || !window.jspdf.jsPDF) {
        alert('jsPDF no está disponible.');
        return;
    }
    const doc = new window.jspdf.jsPDF();
    doc.setFontSize(14);
    doc.text(filename, 10, 10);
    const headers = ["Fecha", "Riesgo", "Clasificación", "Puntuación", "Valor", "Mensaje"];
    const rows = data.map(a => [
        a.fecha_alerta ? new Date(a.fecha_alerta).toLocaleString() : '',
        a.riesgo,
        a.clasificacion,
        (a.puntuacion || 0).toFixed(3),
        a.valor != null ? a.valor : '',
        a.mensaje || ''
    ]);
    let y = 20;
    doc.setFontSize(10);
    doc.text(headers.join(' | '), 10, y);
    y += 7;
    rows.forEach(row => {
        doc.text(row.join(' | '), 10, y);
        y += 7;
        if (y > 270) { doc.addPage(); y = 20; }
    });
    doc.save(filename + '.pdf');
}

function exportToExcel(data, filename) {
    if (!window.XLSX) {
        alert('SheetJS no está disponible.');
        return;
    }
    const ws = window.XLSX.utils.json_to_sheet(data.map(a => ({
        Fecha: a.fecha_alerta ? new Date(a.fecha_alerta).toLocaleString() : '',
        Riesgo: a.riesgo,
        Clasificación: a.clasificacion,
        Puntuación: (a.puntuacion || 0).toFixed(3),
        Valor: a.valor != null ? a.valor : '',
        Mensaje: a.mensaje || ''
    })));
    const wb = window.XLSX.utils.book_new();
    window.XLSX.utils.book_append_sheet(wb, ws, "Alertas");
    window.XLSX.writeFile(wb, filename + ".xlsx");
}
    // Exportar alertas
    document.getElementById('export-alerts-pdf')?.addEventListener('click', () => {
        exportToPDF(typeof allAlertsRaw !== 'undefined' ? allAlertsRaw : [], 'alertas_mindcare');
    });
    document.getElementById('export-alerts-xlsx')?.addEventListener('click', () => {
        exportToExcel(typeof allAlertsRaw !== 'undefined' ? allAlertsRaw : [], 'alertas_mindcare');
    });
    // Exportar historial
    document.getElementById('export-history-pdf')?.addEventListener('click', () => {
        exportToPDF(typeof allHistoryRaw !== 'undefined' ? allHistoryRaw : [], 'historial_mindcare');
    });
    document.getElementById('export-history-xlsx')?.addEventListener('click', () => {
        exportToExcel(typeof allHistoryRaw !== 'undefined' ? allHistoryRaw : [], 'historial_mindcare');
    });
// =====================================
// CONFIGURACIÓN GLOBAL
// =====================================
// API_BASE_URL: Ruta base del backend donde se envían solicitudes.
// USER_ID: Identificador único del usuario (se almacena en localStorage).
// USER_NAME: Nombre del usuario actualmente autenticado.
const API_BASE_URL = 'http://127.0.0.1:5000/api';
let USER_ID = null;
let USER_NAME = null;


// =====================================
// REFERENCIAS A VISTAS PRINCIPALES
// =====================================
// Cada una corresponde a una sección visible de la interfaz.
// Se muestran u ocultan según la navegación del usuario.
const loginView = document.getElementById('login-view');
const mainAppViews = document.getElementById('main-app-views');
const chatView = document.getElementById('chat-view');
const alertsView = document.getElementById('alerts-view');
const resourcesView = document.getElementById('resources-view');
const historyView = document.getElementById('history-view');
const allAlertsContainer = document.getElementById("all-alerts-container");


// =====================================
// REFERENCIAS DE LOGIN
// =====================================
// Inputs y botón del formulario de inicio de sesión.
const usernameInput = document.getElementById('username-input');
const passwordInput = document.getElementById('password-input');
const startSessionButton = document.getElementById('start-session-button');


// =====================================
// REFERENCIAS DE NAVEGACIÓN
// =====================================
// Botones de la barra inferior y otros elementos de cambio de vista.
const navChatButton = document.getElementById('nav-chat-button');
const navAlertsButton = document.getElementById('nav-alerts-button');
const navLogoutButton = document.getElementById('nav-logout-button');
const goToResourcesButton = document.getElementById('go-to-resources');
const backFromResourcesButton = document.getElementById('back-from-resources');
const navStatsButton = document.getElementById('nav-stats-button');
const historyButton = document.getElementById("nav-history-button");


// =====================================
// REFERENCIAS DEL CHAT Y ALERTAS
// =====================================
// Contenedores para mensajes, entradas de texto y avisos visuales.
const chatMessages = document.getElementById('chat-messages');
const userInput = document.getElementById('user-input');
const sendButton = document.getElementById('send-button');
const loadingIndicator = document.getElementById('loading-indicator');
const riskAlertDisplay = document.getElementById('risk-alert-display');
const alertsList = document.getElementById('alerts-list');
const noAlertsMessage = document.getElementById('no-alerts-message');


// =====================================
// FUNCIONES AUXILIARES
// =====================================

/**
 * Oculta todas las vistas principales del sistema.
 * Esta función asegura que solo una vista esté visible a la vez.
 */
function hideAllViews() {
    if(chatView) chatView.classList.add("hidden");
    if(alertsView) alertsView.classList.add("hidden");
    if(resourcesView) resourcesView.classList.add("hidden");
    if(historyView) historyView.classList.add("hidden");

    const statsView = document.getElementById("stats-view");
    if(statsView) statsView.classList.add("hidden");
}

/**
 * Cambia la vista actual dependiendo del parámetro recibido.
 * Controla la lógica de navegación del usuario.
 * 
 * @param {string} view - Nombre de la vista a mostrar.
 */
function navigateTo(view) {
    hideAllViews();

    // Quitamos el estado "active" de todos los botones
    document.querySelectorAll('.bottom-nav .nav-item')
        .forEach(button => button.classList.remove('active'));

    if(view === 'chat' && chatView) {
        chatView.classList.remove('hidden');
        navChatButton?.classList.add('active');
        userInput?.focus();

    } else if(view === 'alerts' && alertsView) {
        alertsView.classList.remove('hidden');
        navAlertsButton?.classList.add('active');
        fetchAlerts();

    } else if(view === 'resources' && resourcesView) {
        resourcesView.classList.remove('hidden');

    } else if(view === 'stats') {
        const statsView = document.getElementById('stats-view');
        if(statsView) statsView.classList.remove('hidden');
        navStatsButton?.classList.add('active');
        fetchStats();

    } else if(view === 'history') {
        if(historyView) historyView.classList.remove('hidden');
    }
}


// =====================================
// FUNCIÓN DE INICIO DE SESIÓN
// =====================================

/**
 * Inicia sesión del usuario: valida el nombre, almacena datos en localStorage
 * y muestra la interfaz principal.
 */
function startSession(username) {
    const trimmedUsername = username.trim();
    if(trimmedUsername.length < 2) {
        console.error("El email/nombre de usuario debe tener al menos 2 caracteres.");
        return;
    }

    // Recuperar o asignar un ID único al usuario
    USER_ID = localStorage.getItem('mindcare_user_id') || crypto.randomUUID();
    localStorage.setItem('mindcare_user_id', USER_ID);
    localStorage.setItem('mindcare_username', trimmedUsername);

    USER_NAME = trimmedUsername;

    loginView?.classList.add('hidden');
    mainAppViews?.classList.remove('hidden');

    // Mensaje inicial del asistente si es la primera vez
    if(chatMessages?.children.length === 0) {
        addMessage('MindCare', `¡Hola, **${USER_NAME}**!?`, null, true);
    }

    navigateTo('chat');
}


// =====================================
// FUNCIÓN DE CERRAR SESIÓN
// =====================================

/**
 * Restablece los datos del usuario y limpia la interfaz.
 */
function logout() {
    USER_ID = null;
    USER_NAME = null;

    localStorage.removeItem('mindcare_user_id');
    localStorage.removeItem('mindcare_username');

    if(chatMessages) chatMessages.innerHTML = '';
    riskAlertDisplay?.classList.add('hidden');

    mainAppViews?.classList.add('hidden');
    loginView?.classList.remove('hidden');

    usernameInput.value = '';
    passwordInput.value = '';
    usernameInput.focus();
}


// =====================================
// CHAT: SCROLL AUTOMÁTICO
// =====================================

/**
 * Desplaza automáticamente el contenedor del chat hacia abajo.
 */
function scrollToBottom() {
    if(chatMessages) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}


// =====================================
// FUNCIÓN PARA MOSTRAR MENSAJES EN EL CHAT
// =====================================

/**
 * Inserta un mensaje en el chat.
 * 
 * @param {string} sender - "Tú" o "MindCare".
 * @param {string} text - Contenido del mensaje.
 * @param {object|null} analysis - Información de análisis emocional (opcional).
 * @param {boolean} isInitial - Si es el mensaje inicial del sistema.
 */
function addMessage(sender, text, analysis = null, isInitial = false) {
    if(!chatMessages) return;

    const isUser = sender === 'Tú';
    const wrapper = document.createElement('div');
    wrapper.className = `flex w-full ${isUser ? 'justify-end' : 'justify-start'}`;

    const bubble = document.createElement('div');
    bubble.className = `message-bubble ${isUser ? 'user-message-style' : 'mindcare-message-style'}`;

    // Permitir negritas en mensajes del sistema
    if(!isUser){
        bubble.innerHTML = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    } else {
        bubble.textContent = text;
    }

    wrapper.appendChild(bubble);
    chatMessages.appendChild(wrapper);

    // Mostrar riesgo (si aplica)
    if(analysis) displayRisk(analysis.riesgo, analysis.clasificacion);
    else if(isUser && riskAlertDisplay) riskAlertDisplay.classList.add('hidden');

    scrollToBottom();
}


// =====================================
// MOSTRAR ALERTA DE RIESGO
// =====================================

/**
 * Muestra una tarjeta de alerta según el nivel de riesgo detectado.
 */
function displayRisk(riskLevel, classification) {
    if(!riskAlertDisplay) return;

    riskAlertDisplay.classList.remove('hidden');

    let bg, text, icon, message;

    if(riskLevel === 'ALTO'){
        bg = 'bg-mind-risk-high'; text='text-white'; icon='🚨';
        message = `${icon} RIESGO ALTO: ${classification}. Por favor, busca ayuda profesional.`;

    } else if(riskLevel === 'MEDIO'){
        bg = 'bg-mind-risk-medium'; text='text-gray-900'; icon='⚠️';
        message = `${icon} RIESGO MEDIO: ${classification}. Te ofrecemos recursos de apoyo.`;

    } else if(riskLevel === 'BAJO'){
        bg = 'bg-mind-risk-low'; text='text-white'; icon='✅';
        message = `${icon} RIESGO BAJO: ${classification}.`;

    } else {
        riskAlertDisplay.classList.add('hidden');
        return;
    }

    riskAlertDisplay.className = `text-sm p-2 rounded-lg mb-2 text-center font-semibold ${bg} ${text}`;
    riskAlertDisplay.textContent = message;
}


// =====================================
// ENVIAR MENSAJE AL BACKEND
// =====================================

/**
 * Envía un mensaje al servidor, recibe respuesta del modelo AI
 * y la muestra en el chat.
 */
async function sendMessage() {
    const message = userInput.value.trim();
    if(!message || !USER_ID) return;

    addMessage('Tú', message);
    userInput.value = '';

    sendButton.disabled = true;
    loadingIndicator?.classList.remove('hidden');

    try {
        const res = await fetch(`${API_BASE_URL}/chat`, { 
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mensaje: message, user_id: USER_ID, username: USER_NAME }) 
        });

        if(!res.ok){
            const errorText = await res.text();
            addMessage('MindCare', `[ERROR API] Error ${res.status}.`);
            console.error("Respuesta fallida:", errorText);
            return;
        }

        const data = await res.json();

        if(data.error){
            addMessage('MindCare', `[ERROR API] ${data.error}`);
        } else {
            addMessage('MindCare', data.respuesta, data.analisis);
        }

    } catch(err){
        addMessage('MindCare', `[ERROR DE CONEXIÓN] ${err.message}`);
    } finally {
        sendButton.disabled = false;
        loadingIndicator?.classList.add('hidden');
        scrollToBottom();
        // Actualizar alertas después de enviar mensaje
        fetchAlerts();
    }
}


// =====================================
// RENDERIZAR ALERTAS
// =====================================

/**
 * Muestra todas las alertas del usuario en la vista dedicada.
 */
function renderAlerts(alerts) {
    if(!alertsList) return;
    alertsList.innerHTML = ''; 

    if(alerts.length === 0){
        noAlertsMessage?.classList.remove('hidden');
        return;
    } else {
        noAlertsMessage?.classList.add('hidden');
    }

    alerts.forEach((alert, idx) => {
        let accentClass, borderClass, icon, riskLabel, bgClass, timelineColor;
        if(alert.riesgo === 'ALTO') {
            accentClass = 'ring-2 ring-mind-risk-high';
            borderClass = 'border-mind-risk-high';
            icon = '🚨';
            riskLabel = 'Alto';
            bgClass = 'bg-[#2a1a1a]/80';
            timelineColor = 'bg-mind-risk-high';
        } else if(alert.riesgo === 'MEDIO') {
            accentClass = 'ring-2 ring-mind-risk-medium';
            borderClass = 'border-mind-risk-medium';
            icon = '⚠️';
            riskLabel = 'Medio';
            bgClass = 'bg-[#2a2a1a]/80';
            timelineColor = 'bg-mind-risk-medium';
        } else {
            accentClass = 'ring-2 ring-mind-risk-low';
            borderClass = 'border-mind-risk-low';
            icon = '✅';
            riskLabel = 'Bajo';
            bgClass = 'bg-[#1a2a1a]/80';
            timelineColor = 'bg-mind-risk-low';
        }
        const dateOptions = { year: 'numeric', month: 'short', day: 'numeric', hour:'2-digit', minute:'2-digit'};
        const date = new Date(alert.fecha_alerta || Date.now()).toLocaleDateString('es-ES', dateOptions);
        // Timeline vertical
        const timeline = `<div class="absolute left-0 top-0 bottom-0 flex flex-col items-center z-0" style="width:18px;">
            <div class="w-3 h-3 rounded-full ${timelineColor} shadow-lg mt-2"></div>
            ${idx < alerts.length-1 ? '<div class="flex-1 w-1 mx-auto bg-gradient-to-b from-mind-blue/40 to-transparent"></div>' : ''}
        </div>`;
        const alertItem = document.createElement('div');
        alertItem.className = `relative p-5 pl-8 rounded-2xl shadow-lg border ${borderClass} ${accentClass} ${bgClass} transition hover:scale-[1.01] duration-150 overflow-hidden`;
        alertItem.innerHTML = `
            ${timeline}
            <div class="flex items-center justify-between mb-2 z-10 relative">
                <span class="inline-flex items-center gap-2 font-bold text-lg">
                    <span class="text-2xl">${icon}</span>
                    <span class="uppercase tracking-wide">Riesgo <span class="px-2 py-0.5 rounded-full text-xs font-bold ${alert.riesgo === 'ALTO' ? 'bg-mind-risk-high text-white' : alert.riesgo === 'MEDIO' ? 'bg-mind-risk-medium text-gray-900' : 'bg-mind-risk-low text-white'}">${riskLabel}</span></span>
                </span>
                <span class="text-xs opacity-80 text-text-muted">${date}</span>
            </div>
            <div class="mb-2 z-10 relative">
                <span class="block text-sm text-text-muted">Mensaje:</span>
                <p class="italic text-base text-text-light font-medium">"${alert.mensaje || 'Mensaje no disponible.'}"</p>
            </div>
            <div class="flex flex-wrap gap-4 text-sm pt-2 border-t border-opacity-30 border-gray-600 z-10 relative">
                <span>Clasificación: <strong>${alert.clasificacion || 'N/A'}</strong></span>
                <span>Puntuación: <strong>${(alert.puntuacion || 0).toFixed(3)}</strong></span>
                <span>Valor: <strong>${alert.valor != null ? alert.valor : '-'}</strong></span>
            </div>
        `;
        alertsList.appendChild(alertItem);
    });
}


// =====================================
// OBTENER ALERTAS DEL SERVIDOR
// =====================================

/**
 * Descarga las alertas del backend y las muestra.
 */
async function fetchAlerts() {
    if(!USER_ID || !alertsList) return;

    alertsList.innerHTML = `<p class="text-gray-500 text-center">Cargando alertas...</p>`;

    try {
        const res = await fetch(`${API_BASE_URL}/alerts?user_id=${USER_ID}`);
        if(!res.ok) throw new Error(`Error ${res.status}`);
        const data = await res.json();

        renderAlerts(data.alerts || []);

    } catch(err){
        alertsList.innerHTML =
            `<p class="text-red-500 text-center">Error de conexión: ${err.message}</p>`;
    }
}


// =====================================
// ESTADÍSTICAS DEL USUARIO
// =====================================

/**
 * Descarga las estadísticas del usuario y las muestra en pantalla.
 */
async function fetchStats() {
    if(!USER_ID) return;
    const statsView = document.getElementById('stats-view');
    if(!statsView) return;
    // Loading state
    statsView.querySelector('#stats-total-interacciones').textContent = '-';
    statsView.querySelector('#stats-ultimo-estado').textContent = '-';
    statsView.querySelector('#stats-emoji').textContent = '😊';
    if(window.renderEmocionesChart) window.renderEmocionesChart([], []);
    try{
        const res = await fetch(`${API_BASE_URL}/stats?user_id=${USER_ID}`);
        if(!res.ok) throw new Error(`Error ${res.status}`);
        const data = await res.json();
        // Actualizar tarjetas
        statsView.querySelector('#stats-total-interacciones').textContent = data.total_interacciones || 0;
        statsView.querySelector('#stats-ultimo-estado').textContent = data.ultimo_estado || '-';
        // Emoji según último riesgo (preferible) o por clasificación como fallback
        let emoji = '😊';
        if(data.ultimo_riesgo){
            if(data.ultimo_riesgo === 'ALTO') emoji = '😢';
            else if(data.ultimo_riesgo === 'MEDIO') emoji = '😐';
            else if(data.ultimo_riesgo === 'BAJO') emoji = '😃';
        } else {
            // Backward-compatible: revisar clasificación textual
            if(data.ultimo_estado?.toLowerCase().includes('triste')) emoji = '😢';
            if(data.ultimo_estado?.toLowerCase().includes('ansioso')) emoji = '😰';
            if(data.ultimo_estado?.toLowerCase().includes('feliz')) emoji = '😃';
        }
        statsView.querySelector('#stats-emoji').textContent = emoji;
        // Gráfica de emociones
        if(window.renderEmocionesChart && data.tendencia_emocional){
            const labels = data.tendencia_emocional.map(e => e.fecha);
            const values = data.tendencia_emocional.map(e => e.valor);
            window.renderEmocionesChart(labels, values);
        }
    } catch(err){
        // Error visual
        statsView.querySelector('#stats-total-interacciones').textContent = '-';
        statsView.querySelector('#stats-ultimo-estado').textContent = 'Error';
        if(window.renderEmocionesChart) window.renderEmocionesChart([], []);
    }
}


// =====================================
// EVENTOS PRINCIPALES DEL SISTEMA
// =====================================

/**
 * Registra todos los eventos necesarios cuando carga la página:
 * - Login
 * - Envío de mensajes
 * - Navegación
 * - Carga de historial
 */
document.addEventListener('DOMContentLoaded', () => {

    // --- Inicio de Sesión ---
    startSessionButton?.addEventListener('click', () =>
        startSession(usernameInput.value)
    );

    usernameInput?.addEventListener('keypress', e => {
        if(e.key === 'Enter') startSessionButton.click();
    });

    passwordInput?.addEventListener('keypress', e => {
        if(e.key === 'Enter') startSessionButton.click();
    });


    // --- Enviar mensaje ---
    sendButton?.addEventListener('click', sendMessage);
    userInput?.addEventListener('keypress', e => {
        if(e.key === 'Enter') sendMessage();
    });


    // --- Navegación inferior ---
    navChatButton?.addEventListener('click', () => navigateTo('chat'));
    navStatsButton?.addEventListener('click', () => navigateTo('stats'));
    navAlertsButton?.addEventListener('click', () => navigateTo('alerts'));
    navLogoutButton?.addEventListener('click', logout);


    // --- Recursos ---
    goToResourcesButton?.addEventListener('click', () => navigateTo('resources'));
    backFromResourcesButton?.addEventListener('click', () => navigateTo('alerts'));


    // --- Historial de Alertas ---
    historyButton?.addEventListener('click', () => {
        hideAllViews();
        historyView?.classList.remove('hidden');
        fetch(`${API_BASE_URL}/alerts?user_id=${USER_ID}`)
        .then(res => res.json())
        .then(data => {
            allAlertsContainer.innerHTML = "";
            if(data.alerts?.length > 0){
                data.alerts.forEach((alert, idx) => {
                    let icon = '✅', timelineColor = 'bg-mind-risk-low';
                    if(alert.riesgo === 'ALTO') { icon = '🚨'; timelineColor = 'bg-mind-risk-high'; }
                    else if(alert.riesgo === 'MEDIO') { icon = '⚠️'; timelineColor = 'bg-mind-risk-medium'; }
                    const timeline = `<div class='absolute left-0 top-0 bottom-0 flex flex-col items-center z-0' style='width:18px;'>
                        <div class='w-3 h-3 rounded-full ${timelineColor} shadow-lg mt-2'></div>
                        ${idx < data.alerts.length-1 ? '<div class="flex-1 w-1 mx-auto bg-gradient-to-b from-mind-blue/40 to-transparent"></div>' : ''}
                    </div>`;
                    const item = document.createElement("div");
                    item.className = "relative p-4 pl-8 rounded-xl bg-dark-card shadow-md text-text-light mb-2 overflow-hidden";
                    item.innerHTML = `
                        ${timeline}
                        <div class='flex items-center gap-2 mb-1 z-10 relative'>
                            <span class='text-xl'>${icon}</span>
                            <span class='font-bold'>${alert.riesgo}</span>
                            <span class='text-xs text-text-muted ml-auto'>${new Date(alert.fecha_alerta).toLocaleString()}</span>
                        </div>
                        <div class='z-10 relative'>
                            <span class='block text-xs text-text-muted'>Mensaje:</span>
                            <span class='italic text-base text-text-light font-medium'>"${alert.mensaje || 'Mensaje no disponible.'}"</span>
                        </div>
                        <div class='flex flex-wrap gap-4 text-xs pt-2 border-t border-opacity-30 border-gray-600 z-10 relative'>
                            <span>Clasificación: <strong>${alert.clasificacion || 'N/A'}</strong></span>
                            <span>Puntuación: <strong>${(alert.puntuacion || 0).toFixed(3)}</strong></span>
                            <span>Valor: <strong>${alert.valor != null ? alert.valor : '-'}</strong></span>
                        </div>
                    `;
                    allAlertsContainer.appendChild(item);
                });
            } else {
                allAlertsContainer.innerHTML = "<p class='text-text-muted text-center'>No hay alertas registradas.</p>";
            }
        })
        .catch(err => {
            allAlertsContainer.innerHTML = `<p class='text-red-500 text-center'>Error al cargar historial: ${err.message}</p>`;
        });
    });


    // --- Restaurar sesión guardada ---
    const savedUserId = localStorage.getItem('mindcare_user_id');
    const savedUsername = localStorage.getItem('mindcare_username');

    if(savedUserId && savedUsername){
        startSession(savedUsername);
    } else {
        loginView?.classList.remove('hidden');
        mainAppViews?.classList.add('hidden');
        usernameInput?.focus();
    }
});
