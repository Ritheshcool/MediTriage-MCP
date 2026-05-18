/**
 * MediTriage — Frontend Chat Logic
 * Handles WebSocket connection, message rendering, and UI interactions.
 */

// ── State ──
let ws = null;
let isConnected = false;
let isProcessing = false;

// ── DOM Elements ──
const messagesContainer = document.getElementById('messagesContainer');
const messagesList = document.getElementById('messagesList');
const welcomeScreen = document.getElementById('welcomeScreen');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const serverList = document.getElementById('serverList');
const connectionIndicator = document.getElementById('connectionIndicator');
const headerBadge = document.getElementById('headerBadge');
const newChatBtn = document.getElementById('newChatBtn');
const menuBtn = document.getElementById('menuBtn');
const sidebar = document.getElementById('sidebar');

// ── Server name mapping ──
const SERVER_NAMES = {
    triage: '🔬 Triage Logic',
    tavily: '🔍 Tavily Search',
    notion: '📋 Notion Database',
    google_calendar: '📅 Google Calendar',
    slack: '🔔 Slack Alerts',
    memory: '🧠 Patient Memory'
};

// ══════════════════════════════════════════════════════
//  WebSocket Connection
// ══════════════════════════════════════════════════════

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/ws/chat`);

    ws.onopen = () => {
        isConnected = true;
        connectionIndicator.classList.add('connected');
        connectionIndicator.querySelector('.conn-text').textContent = 'Connected';
        fetchServerStatus();
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleServerMessage(data);
    };

    ws.onclose = () => {
        isConnected = false;
        connectionIndicator.classList.remove('connected');
        connectionIndicator.querySelector('.conn-text').textContent = 'Disconnected';
        // Reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000);
    };

    ws.onerror = (err) => {
        console.error('WebSocket error:', err);
    };
}

// ── Handle incoming messages from server ──
function handleServerMessage(data) {
    switch (data.type) {
        case 'status':
            showThinking(data.message);
            break;

        case 'tool_calls':
            removeThinking();
            showToolCalls(data.calls);
            break;

        case 'response':
            removeThinking();
            addMessage('assistant', data.message);
            isProcessing = false;
            enableInput();
            break;

        case 'slots':
            renderSlotButtons(data.doctor, data.slots);
            break;

        case 'doctors':
            renderDoctorCards(data.specialty, data.doctors);
            break;

        case 'error':
            removeThinking();
            addMessage('assistant', `⚠️ ${data.message}`);
            isProcessing = false;
            enableInput();
            break;
    }
}

// ══════════════════════════════════════════════════════
//  Message Rendering
// ══════════════════════════════════════════════════════

function addMessage(role, content) {
    // Hide welcome screen on first message
    welcomeScreen.classList.add('hidden');

    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = role === 'assistant' ? '🏥' : '👤';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = content;

    msgDiv.appendChild(avatar);
    msgDiv.appendChild(contentDiv);
    messagesList.appendChild(msgDiv);

    scrollToBottom();
}

function showToolCalls(calls) {
    const indicator = document.createElement('div');
    indicator.className = 'tool-calls-indicator';
    indicator.id = 'currentToolCalls';

    const label = document.createElement('span');
    label.style.cssText = 'font-size:11px;color:var(--text-muted);margin-right:4px;';
    label.textContent = '⚡ Called:';
    indicator.appendChild(label);

    calls.forEach((call, index) => {
        setTimeout(() => {
            const chip = document.createElement('span');
            chip.className = 'tool-call-chip';
            chip.setAttribute('data-server', call.server);
            chip.innerHTML = `<span class="chip-dot"></span>${SERVER_NAMES[call.server] || call.server} → ${call.tool}`;
            indicator.appendChild(chip);
        }, index * 150);
    });

    messagesList.appendChild(indicator);
    scrollToBottom();
}

// ── Render clickable slot buttons ──
function renderSlotButtons(doctorName, slots) {
    const container = document.createElement('div');
    container.className = 'slots-container';

    const header = document.createElement('div');
    header.className = 'slots-header';
    header.innerHTML = `📅 <strong>Available slots for ${doctorName}</strong>`;
    container.appendChild(header);

    const grid = document.createElement('div');
    grid.className = 'slots-grid';

    slots.forEach(slot => {
        const btn = document.createElement('button');
        btn.className = 'slot-btn';
        btn.innerHTML = `
            <span class="slot-day">${slot.day}</span>
            <span class="slot-date">${slot.date}</span>
            <span class="slot-time">${slot.time}</span>
        `;
        btn.onclick = () => {
            // Disable all slot buttons
            container.querySelectorAll('.slot-btn').forEach(b => {
                b.classList.remove('selected');
                b.disabled = true;
            });
            btn.classList.add('selected');
            btn.disabled = false;

            // Send as user message
            const msg = `I'd like to book the slot on ${slot.display} with ${doctorName}`;
            addMessage('user', msg);
            ws.send(JSON.stringify({ message: msg }));
            isProcessing = true;
            disableInput();
        };
        grid.appendChild(btn);
    });

    container.appendChild(grid);
    messagesList.appendChild(container);
    scrollToBottom();
}

// ── Render doctor cards ──
function renderDoctorCards(specialty, doctors) {
    const container = document.createElement('div');
    container.className = 'doctors-container';

    doctors.forEach(doc => {
        const card = document.createElement('div');
        card.className = 'doctor-card';
        card.innerHTML = `
            <div class="doctor-info">
                <div class="doctor-name">👨‍⚕️ ${doc.name}</div>
                <div class="doctor-detail">📋 ${doc.specialty} • ${doc.experience_years} years exp</div>
                <div class="doctor-detail">⭐ ${doc.rating}/5.0 • 📞 ${doc.phone}</div>
                <div class="doctor-days">${doc.available_days.map(d => `<span class="day-chip">${d}</span>`).join('')}</div>
            </div>
            <button class="choose-doctor-btn">View Slots →</button>
        `;
        card.querySelector('.choose-doctor-btn').onclick = () => {
            // Disable all cards
            container.querySelectorAll('.choose-doctor-btn').forEach(b => b.disabled = true);
            card.classList.add('selected');

            const msg = `I'd like to see available slots for ${doc.name}`;
            addMessage('user', msg);
            ws.send(JSON.stringify({ message: msg }));
            isProcessing = true;
            disableInput();
        };
        container.appendChild(card);
    });

    messagesList.appendChild(container);
    scrollToBottom();
}

function showThinking(message) {
    removeThinking();

    const thinking = document.createElement('div');
    thinking.className = 'thinking-indicator';
    thinking.id = 'thinkingIndicator';
    thinking.innerHTML = `
        <div class="thinking-dots">
            <span></span><span></span><span></span>
        </div>
        <span class="thinking-text">${message || 'Thinking...'}</span>
    `;

    messagesList.appendChild(thinking);
    scrollToBottom();
}

function removeThinking() {
    const el = document.getElementById('thinkingIndicator');
    if (el) el.remove();
}

// ══════════════════════════════════════════════════════
//  Server Status
// ══════════════════════════════════════════════════════

async function fetchServerStatus() {
    try {
        const res = await fetch('/api/status');
        const status = await res.json();
        renderServerStatus(status);
    } catch (e) {
        console.error('Failed to fetch server status:', e);
    }
}

function renderServerStatus(status) {
    serverList.innerHTML = '';
    let connectedCount = 0;

    for (const [name, info] of Object.entries(status)) {
        const item = document.createElement('div');
        item.className = `server-item ${info.connected ? 'connected' : 'error'}`;

        const dot = document.createElement('span');
        dot.className = 'server-dot';

        const label = document.createElement('span');
        label.textContent = SERVER_NAMES[name] || name;

        item.appendChild(dot);
        item.appendChild(label);

        if (info.connected && info.tools.length > 0) {
            const count = document.createElement('span');
            count.className = 'server-tool-count';
            count.textContent = `${info.tools.length} tools`;
            item.appendChild(count);
            connectedCount++;
        }

        serverList.appendChild(item);
    }

    headerBadge.textContent = `${connectedCount}/${Object.keys(status).length} Servers Active`;
}

// ══════════════════════════════════════════════════════
//  Input Handling
// ══════════════════════════════════════════════════════

function sendMessage() {
    const text = messageInput.value.trim();
    if (!text || !isConnected || isProcessing) return;

    addMessage('user', text);
    ws.send(JSON.stringify({ message: text }));

    messageInput.value = '';
    messageInput.style.height = 'auto';
    isProcessing = true;
    disableInput();
}

function sendExample(btn) {
    const text = btn.textContent.replace(/^"|"$/g, '');
    messageInput.value = text;
    sendMessage();
}

function enableInput() {
    messageInput.disabled = false;
    messageInput.focus();
    updateSendButton();
}

function disableInput() {
    sendBtn.disabled = true;
}

function updateSendButton() {
    sendBtn.disabled = !messageInput.value.trim() || !isConnected || isProcessing;
}

function scrollToBottom() {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// ── Auto-resize textarea ──
messageInput.addEventListener('input', () => {
    messageInput.style.height = 'auto';
    messageInput.style.height = Math.min(messageInput.scrollHeight, 120) + 'px';
    updateSendButton();
});

messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

sendBtn.addEventListener('click', sendMessage);

// ── New Chat ──
newChatBtn.addEventListener('click', () => {
    messagesList.innerHTML = '';
    welcomeScreen.classList.remove('hidden');
    // Reconnect to get a fresh session
    if (ws) ws.close();
    connectWebSocket();
});

// ── Mobile sidebar toggle ──
menuBtn.addEventListener('click', () => {
    sidebar.classList.toggle('open');
});

// ══════════════════════════════════════════════════════
//  Initialize
// ══════════════════════════════════════════════════════

connectWebSocket();
