const API_BASE_URL = 'http://127.0.0.1:5000/api';
let USER_ID = null;
let USER_NAME = null;

// ======================
// Referencias de Vistas
// ======================
const loginView = document.getElementById('login-view');
const mainAppViews = document.getElementById('main-app-views');
const chatView = document.getElementById('chat-view');
const alertsView = document.getElementById('alerts-view');
const resourcesView = document.getElementById('resources-view'); 
const historyView = document.getElementById('history-view');
const allAlertsContainer = document.getElementById("all-alerts-container");

// ======================
// Referencias de Login
// ======================
const usernameInput = document.getElementById('username-input'); 
const passwordInput = document.getElementById('password-input'); 
const startSessionButton = document.getElementById('start-session-button');

// ======================
// Referencias de Navegación
// ======================
const navChatButton = document.getElementById('nav-chat-button'); 
const navAlertsButton = document.getElementById('nav-alerts-button'); 
const navLogoutButton = document.getElementById('nav-logout-button'); 
const goToResourcesButton = document.getElementById('go-to-resources'); 
const backFromResourcesButton = document.getElementById('back-from-resources'); 
const navStatsButton = document.getElementById('nav-stats-button');
const historyButton = document.getElementById("nav-history-button");

// ======================
// Referencias de Chat/Alertas
// ======================
const chatMessages = document.getElementById('chat-messages');
const userInput = document.getElementById('user-input');
const sendButton = document.getElementById('send-button');
const loadingIndicator = document.getElementById('loading-indicator'); 
const riskAlertDisplay = document.getElementById('risk-alert-display'); 
const alertsList = document.getElementById('alerts-list'); 
const noAlertsMessage = document.getElementById('no-alerts-message'); 

// ======================
// Funciones Auxiliares
// ======================

// Ocultar todas las vistas
function hideAllViews() {
    if(chatView) chatView.classList.add("hidden");
    if(alertsView) alertsView.classList.add("hidden");
    if(resourcesView) resourcesView.classList.add("hidden");
    if(historyView) historyView.classList.add("hidden");
    const statsView = document.getElementById("stats-view");
    if(statsView) statsView.classList.add("hidden");
}

// Navegación principal
function navigateTo(view) {
    hideAllViews();

    // Resetear estado active
    document.querySelectorAll('.bottom-nav .nav-item').forEach(button => button.classList.remove('active'));

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

// Iniciar sesión
function startSession(username) {
    const trimmedUsername = username.trim();
    if(trimmedUsername.length < 2) {
        console.error("El email/nombre de usuario debe tener al menos 2 caracteres.");
        return;
    }

    USER_ID = localStorage.getItem('mindcare_user_id') || crypto.randomUUID();
    localStorage.setItem('mindcare_user_id', USER_ID);
    localStorage.setItem('mindcare_username', trimmedUsername);

    USER_NAME = trimmedUsername;

    loginView?.classList.add('hidden');
    mainAppViews?.classList.remove('hidden');

    if(chatMessages?.children.length === 0) {
        addMessage('MindCare', `¡Hola, **${USER_NAME}**! Estoy aquí para escucharte. ¿Cómo te sientes hoy?`, null, true);
    }

    navigateTo('chat');
}

// Cerrar sesión
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

// Scroll al final del chat
function scrollToBottom() {
    if(chatMessages) chatMessages.scrollTop = chatMessages.scrollHeight;
}

// ======================
// Funciones de Chat
// ======================
function addMessage(sender, text, analysis = null, isInitial = false) {
    if(!chatMessages) return;

    const isUser = sender === 'Tú';
    const wrapper = document.createElement('div');
    wrapper.className = `flex w-full ${isUser ? 'justify-end' : 'justify-start'}`;

    const bubble = document.createElement('div');
    bubble.className = `message-bubble ${isUser ? 'user-message-style' : 'mindcare-message-style'}`;

    if(!isUser){
        bubble.innerHTML = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    } else {
        bubble.textContent = text;
    }

    wrapper.appendChild(bubble);
    chatMessages.appendChild(wrapper);

    if(analysis) displayRisk(analysis.riesgo, analysis.clasificacion);
    else if(isUser && riskAlertDisplay) riskAlertDisplay.classList.add('hidden');

    scrollToBottom();
}

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

// Enviar mensaje
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
            addMessage('MindCare', `[ERROR API] El servidor devolvió un error ${res.status}.`);
            console.error("Respuesta fallida del chat:", errorText);
            return;
        }

        const data = await res.json();
        if(data.error){
            addMessage('MindCare', `[ERROR API] ${data.error}`);
        } else {
            addMessage('MindCare', data.respuesta, data.analisis);
        }
    } catch(err){
        addMessage('MindCare', `[ERROR CONEXIÓN] No se pudo conectar con la API: ${err.message}.`);
    } finally {
        sendButton.disabled = false;
        loadingIndicator?.classList.add('hidden');
        scrollToBottom();
    }
}

// ======================
// Funciones de Alertas
// ======================
function renderAlerts(alerts) {
    if(!alertsList) return;
    alertsList.innerHTML = ''; 

    if(alerts.length === 0){
        noAlertsMessage?.classList.remove('hidden');
        return;
    } else {
        noAlertsMessage?.classList.add('hidden');
    }

    alerts.forEach(alert => {
        let accentClass;
        if(alert.riesgo === 'ALTO') accentClass='accent-red';
        else if(alert.riesgo === 'MEDIO') accentClass='accent-yellow';
        else accentClass='accent-blue';

        const alertItem = document.createElement('div');
        alertItem.className = `p-4 rounded-xl shadow-md emotion-card ${accentClass}`; 

        const dateOptions = { year: 'numeric', month: 'short', day: 'numeric', hour:'2-digit', minute:'2-digit'};
        const date = new Date(alert.fecha_alerta || Date.now()).toLocaleDateString('es-ES', dateOptions);

        alertItem.innerHTML = `
            <div class="flex items-center justify-between mb-2">
                <span class="font-bold text-lg">${alert.riesgo === 'ALTO' ? '🚨' : alert.riesgo === 'MEDIO' ? '⚠️' : '✅'} Riesgo ${alert.riesgo}</span>
                <span class="text-xs opacity-80 text-text-muted">${date}</span>
            </div>
            <p class="mb-1 italic opacity-90 text-text-light">"${alert.mensaje || 'Mensaje de alerta no disponible.'}"</p>
            <div class="text-sm pt-2 border-t border-opacity-30 border-gray-600">
                <span>Clasificación: <strong>${alert.clasificacion || 'N/A'}</strong></span>
                <span class="ml-4">Puntuación: <strong>${(alert.puntuacion || 0).toFixed(3)}</strong></span>
            </div>
        `;
        alertsList.appendChild(alertItem);
    });
}

async function fetchAlerts() {
    if(!USER_ID || !alertsList) return;
    alertsList.innerHTML = `<p class="text-gray-500 text-center">Cargando alertas...</p>`;

    try {
        const res = await fetch(`${API_BASE_URL}/alerts?user_id=${USER_ID}`);
        if(!res.ok) throw new Error(`Error ${res.status} al cargar alertas.`);
        const data = await res.json();
        renderAlerts(data.alerts || []);
    } catch(err){
        alertsList.innerHTML = `<p class="text-red-500 text-center">Error de conexión al cargar alertas: ${err.message}</p>`;
    }
}

// ======================
// Funciones de Estadísticas
// ======================
async function fetchStats() {
    if(!USER_ID) return;
    const statsView = document.getElementById('stats-view');
    if(!statsView) return;

    statsView.innerHTML = `<p class="text-gray-500 text-center">Cargando estadísticas...</p>`;

    try{
        const res = await fetch(`${API_BASE_URL}/stats?user_id=${USER_ID}`);
        if(!res.ok) throw new Error(`Error ${res.status} al cargar estadísticas.`);
        const data = await res.json();

        statsView.innerHTML = `
            <h2 class="text-xl font-bold mb-4">Estadísticas de tu interacción</h2>
            <p><strong>Total de interacciones:</strong> ${data.total_interacciones}</p>
            <p><strong>Último estado emocional:</strong> ${data.ultimo_estado}</p>
            <div class="mt-4">
                <h3 class="font-semibold mb-2">Conteo de alertas por nivel de riesgo:</h3>
                <ul class="list-disc ml-5">
                    <li>Riesgo BAJO: ${data.conteo_riesgo.BAJO}</li>
                    <li>Riesgo MEDIO: ${data.conteo_riesgo.MEDIO}</li>
                    <li>Riesgo ALTO: ${data.conteo_riesgo.ALTO}</li>
                </ul>
            </div>
        `;
    } catch(err){
        statsView.innerHTML = `<p class="text-red-500 text-center">Error al cargar estadísticas: ${err.message}</p>`;
    }
}

// ======================
// EVENTOS
// ======================
document.addEventListener('DOMContentLoaded', () => {

    // Login
    startSessionButton?.addEventListener('click', () => startSession(usernameInput.value));
    usernameInput?.addEventListener('keypress', e => { if(e.key==='Enter') startSessionButton.click(); });
    passwordInput?.addEventListener('keypress', e => { if(e.key==='Enter') startSessionButton.click(); });

    // Enviar mensaje
    sendButton?.addEventListener('click', sendMessage);
    userInput?.addEventListener('keypress', e => { if(e.key==='Enter') sendMessage(); });

    // Navegación barra inferior
    navChatButton?.addEventListener('click', () => navigateTo('chat'));
    navStatsButton?.addEventListener('click', () => navigateTo('stats'));
    navAlertsButton?.addEventListener('click', () => navigateTo('alerts'));
    navLogoutButton?.addEventListener('click', logout);

    // Recursos
    goToResourcesButton?.addEventListener('click', () => navigateTo('resources'));
    backFromResourcesButton?.addEventListener('click', () => navigateTo('alerts'));

    // Historial
    historyButton?.addEventListener('click', () => {
        hideAllViews();
        historyView?.classList.remove('hidden');

        fetch(`${API_BASE_URL}/alerts?user_id=${USER_ID}`)
        .then(res => res.json())
        .then(data => {
            allAlertsContainer.innerHTML = "";
            if(data.alerts && data.alerts.length > 0){
                data.alerts.forEach(alert => {
                    const item = document.createElement("div");
                    item.className = "p-4 rounded-xl bg-dark-card shadow-md text-text-light mb-2";
                    item.innerHTML = `
                        <p><strong>Mensaje:</strong> ${alert.mensaje}</p>
                        <p><strong>Clasificación:</strong> ${alert.clasificacion}</p>
                        <p><strong>Riesgo:</strong> ${alert.riesgo}</p>
                        <p><strong>Fecha:</strong> ${new Date(alert.fecha_alerta).toLocaleString()}</p>
                    `;
                    allAlertsContainer.appendChild(item);
                });
            } else {
                allAlertsContainer.innerHTML = "<p class='text-text-muted text-center'>No hay alertas registradas.</p>";
            }
        })
        .catch(err => {
            allAlertsContainer.innerHTML = `<p class="text-red-500 text-center">Error al cargar historial: ${err.message}</p>`;
        });
    });

    // Cargar sesión guardada
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
