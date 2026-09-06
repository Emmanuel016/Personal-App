let currentClientId = null;
let timelineChart = null;
const appId = typeof __app_id !== 'undefined' ? __app_id : 'default-app-id';

// Cache management fingerprints to prevent redundant DOM updates (lowers latency)
let previousMessageHash = "";
window.isTransmitting = false;

// WebSocket/Socket.IO connection
let socket = null;
let notifications = [];
let reconnectAttempts = 0;
let maxReconnectAttempts = 5;
let reconnectDelay = 1000;

// Initialize WebSocket connection
function initializeWebSocket() {
    if (typeof io !== 'undefined') {
        socket = io({
            transports: ['polling'],  // Force polling only for Flask dev server compatibility
            upgrade: false,  // Disable WebSocket upgrade
            reconnection: true,
            reconnectionAttempts: maxReconnectAttempts,
            reconnectionDelay: reconnectDelay,
            reconnectionDelayMax: 10000
        });

        socket.on('connect', () => {
            console.log('Connected to WebSocket server');
            reconnectAttempts = 0;
            reconnectDelay = 1000;
        });

        socket.on('disconnect', (reason) => {
            console.log('Disconnected from WebSocket server:', reason);
            if (reason === 'io server disconnect') {
                // Server disconnected, try to reconnect
                handleReconnect();
            }
        });

        socket.on('connect_error', (error) => {
            console.error('WebSocket connection error:', error);
            reconnectAttempts++;
            if (reconnectAttempts < maxReconnectAttempts) {
                console.log(`Reconnection attempt ${reconnectAttempts}/${maxReconnectAttempts} in ${reconnectDelay}ms`);
                reconnectDelay = Math.min(reconnectDelay * 2, 10000); // Exponential backoff, max 10s
            } else {
                console.error('Max reconnection attempts reached. Falling back to polling.');
                fallbackToPolling();
            }
        });

        socket.on('new_notification', (notification) => {
            addNotificationToDropdown(notification);
            updateNotificationBadge();
            showBrowserNotification(notification);
        });

        socket.on('unread_count', (data) => {
            updateNotificationBadge(data.count);
        });

        socket.on('notifications', (data) => {
            notifications = data.notifications;
            renderNotifications();
        });

        socket.emit('get_notifications', { page: 1, per_page: 20 });
    }
}

function handleReconnect() {
    if (reconnectAttempts < maxReconnectAttempts) {
        setTimeout(() => {
            if (socket && !socket.connected) {
                socket.connect();
            }
        }, reconnectDelay);
    }
}

function fallbackToPolling() {
    console.log('Falling back to HTTP polling for notifications');
    setInterval(() => {
        fetch('/api/notifications/stats')
            .then(response => response.json())
            .then(data => {
                if (data && data.unread !== undefined) {
                    updateNotificationBadge(data.unread);
                }
            })
            .catch(error => console.error('Polling error:', error));
    }, 30000); // Poll every 30 seconds
}

function addNotificationToDropdown(notification) {
    const notificationList = document.getElementById('notificationList');
    if (!notificationList) return;

    const noNotifications = notificationList.querySelector('.no-notifications');
    if (noNotifications) noNotifications.remove();

    // Check if we should group this notification
    const existingGroup = findNotificationGroup(notification);
    
    if (existingGroup) {
        // Add to existing group
        incrementGroupCount(existingGroup);
        return;
    }

    const notificationItem = document.createElement('div');
    notificationItem.className = `notification-item ${notification.read ? '' : 'unread'}`;
    notificationItem.dataset.notificationId = notification.id;
    notificationItem.dataset.notificationType = notification.type;
    notificationItem.onclick = () => markNotificationRead(notification.id);

    notificationItem.innerHTML = `
        <div class="notification-title">${escapeHtml(notification.title)}</div>
        <div class="notification-message">${escapeHtml(notification.message)}</div>
        <div class="notification-time">${getTimeAgo(notification.created_at)}</div>
    `;

    notificationList.insertBefore(notificationItem, notificationList.firstChild);
}

function findNotificationGroup(notification) {
    const notificationList = document.getElementById('notificationList');
    if (!notificationList) return null;
    
    // Group messages from same sender within 5 minutes
    if (notification.type === 'message') {
        const items = notificationList.querySelectorAll('.notification-item');
        for (let item of items) {
            if (item.dataset.notificationType === 'message') {
                const time = item.querySelector('.notification-time');
                if (time && time.textContent.includes('minutes ago')) {
                    return item; // Group with recent message
                }
            }
        }
    }
    
    return null;
}

function incrementGroupCount(groupItem) {
    let countBadge = groupItem.querySelector('.group-count');
    if (!countBadge) {
        countBadge = document.createElement('span');
        countBadge.className = 'group-count';
        countBadge.style.cssText = 'background: #00f2fe; color: #0a192f; padding: 2px 6px; border-radius: 10px; font-size: 10px; font-weight: bold; margin-left: 8px;';
        groupItem.querySelector('.notification-title').appendChild(countBadge);
    }
    
    let count = parseInt(countBadge.textContent) || 1;
    countBadge.textContent = count + 1;
}

function renderNotifications() {
    const notificationList = document.getElementById('notificationList');
    if (!notificationList) return;

    notificationList.innerHTML = '';
    if (notifications.length === 0) {
        notificationList.innerHTML = '<div class="no-notifications">No notifications</div>';
        return;
    }

    notifications.forEach(notification => {
        const notificationItem = document.createElement('div');
        notificationItem.className = `notification-item ${notification.read ? '' : 'unread'}`;
        notificationItem.dataset.notificationId = notification.id;
        notificationItem.onclick = () => markNotificationRead(notification.id);

        notificationItem.innerHTML = `
            <div class="notification-title">${escapeHtml(notification.title)}</div>
            <div class="notification-message">${escapeHtml(notification.message)}</div>
            <div class="notification-time">${getTimeAgo(notification.created_at)}</div>
        `;
        notificationList.appendChild(notificationItem);
    });
}

function markNotificationRead(notificationId) {
    if (socket) socket.emit('mark_notification_read', { notification_id: notificationId });
    const notificationItem = document.querySelector(`[data-notification-id="${notificationId}"]`);
    if (notificationItem) notificationItem.classList.remove('unread');
    updateNotificationBadge();
}

function updateNotificationBadge(count) {
    const badge = document.getElementById('notificationBadge');
    if (!badge) return;
    if (count !== undefined) {
        badge.textContent = count;
        badge.style.display = count > 0 ? 'flex' : 'none';
    } else {
        const unreadCount = document.querySelectorAll('.notification-item.unread').length;
        badge.textContent = unreadCount;
        badge.style.display = unreadCount > 0 ? 'flex' : 'none';
    }
}

function showBrowserNotification(notification) {
    if ('Notification' in window && Notification.permission === 'granted') {
        new Notification(notification.title, { body: notification.message });
    } else if ('Notification' in window && Notification.permission !== 'denied') {
        Notification.requestPermission().then(permission => {
            if (permission === 'granted') {
                new Notification(notification.title, { body: notification.message });
            }
        });
    }
}

function requestNotificationPermission() {
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
}

function getTimeAgo(dateString) {
    if (!dateString) return 'Unknown time';
    
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return 'Invalid date';
    
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);

    if (seconds < 0) return 'Just now';
    if (seconds < 60) return 'Just now';
    if (seconds < 3600) return Math.floor(seconds / 60) + ' minute' + (Math.floor(seconds / 60) > 1 ? 's' : '') + ' ago';
    if (seconds < 86400) return Math.floor(seconds / 3600) + ' hour' + (Math.floor(seconds / 3600) > 1 ? 's' : '') + ' ago';
    if (seconds < 604800) return Math.floor(seconds / 86400) + ' day' + (Math.floor(seconds / 86400) > 1 ? 's' : '') + ' ago';
    if (seconds < 2592000) return Math.floor(seconds / 604800) + ' week' + (Math.floor(seconds / 604800) > 1 ? 's' : '') + ' ago';
    if (seconds < 31536000) return Math.floor(seconds / 2592000) + ' month' + (Math.floor(seconds / 2592000) > 1 ? 's' : '') + ' ago';
    if (seconds < 315360000) return Math.floor(seconds / 31536000) + ' year' + (Math.floor(seconds / 31536000) > 1 ? 's' : '') + ' ago';
    
    // For older dates, show formatted date with time
    return date.toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric',
        year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
    });
}

function formatDateTime(dateString, includeTime = true) {
    if (!dateString) return 'Unknown time';
    
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return 'Invalid date';
    
    const options = {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
    };
    
    if (includeTime) {
        options.hour = '2-digit';
        options.minute = '2-digit';
    }
    
    return date.toLocaleDateString('en-US', options);
}

function escapeHtml(text) {
    if (text === null || text === undefined || typeof text !== 'string') return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function createWarningStyles() {
    if (document.getElementById('dynamic-warning-styles')) return;
    const style = document.createElement('style');
    style.id = 'dynamic-warning-styles';
    style.textContent = `
        .dynamic-warning {
            position: fixed; top: 20px; right: 20px; background: rgba(255, 152, 0, 0.95); border: 1px solid rgba(255, 152, 0, 0.8);
            color: white; padding: 1rem 1.5rem; border-radius: 8px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            z-index: 10000; max-width: 400px; font-family: Arial, sans-serif; animation: slideIn 0.3s ease;
        }
        .dynamic-warning i { margin-right: 0.5rem; }
        @keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
    `;
    document.head.appendChild(style);
}

function showWarning(message) {
    if (/session|authentication required|unauthorized|forbidden|too many requests|429|log in again/i.test(String(message || ''))) return;
    createWarningStyles();
    document.querySelectorAll('.dynamic-warning').forEach(w => w.remove());
    
    const warning = document.createElement('div');
    warning.className = 'dynamic-warning';
    warning.textContent = message;
    const icon = document.createElement('i');
    icon.className = 'fa-solid fa-exclamation-triangle';
    icon.style.marginRight = '0.5rem';
    warning.prepend(icon);
    document.body.appendChild(warning);
    
    setTimeout(() => {
        warning.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => warning.remove(), 300);
    }, 5000);
}

async function safeFetch(path, options = {}) {
    const url = window.location.origin + path;
    const timeout = options.timeout || 15000; 
    
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);
        const res = await fetch(url, { ...options, signal: controller.signal });
        clearTimeout(timeoutId);
        
        if (res.status === 401 || res.status === 403) return null;
        const contentType = res.headers.get("content-type");
        if (!res.ok || (contentType && contentType.includes("text/html"))) return null;
        
        return await res.json();
    } catch (err) {
        return null;
    }
}

/**
 * DASHBOARD & ANALYTICS
 */
async function loadDashboard() {
    const revEl = document.getElementById("dashRevenue");
    if (!revEl) return; // Skip if not on dashboard
    
    const data = await safeFetch("/api/dashboard");
    if (!data) return;

    const paidEl = document.getElementById("dashPaid");
    if (revEl) revEl.textContent = `£${(data.total_revenue || 0).toFixed(2)}`;
    if (paidEl) paidEl.textContent = `£${(data.total_paid || 0).toFixed(2)}`;

    const ctx = document.getElementById("statusChart");
    if (!ctx) return;

    const existingChart = Chart.getChart(ctx);
    if (existingChart) existingChart.destroy();

    new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: Object.keys(data.status_counts || {}),
            datasets: [{
                data: Object.values(data.status_counts || {}),
                backgroundColor: ["#00f2fe", "#ff007f", "#4caf50", "#ff9800"],
                borderWidth: 0, hoverOffset: 4
            }]
        },
        options: { plugins: { legend: { labels: { color: "#e2e8f0", font: { family: "'Rajdhani', sans-serif" } } } } }
    });
}

async function loadProjectChart() {
    const ctx = document.getElementById("projectChart");
    if (!ctx) return; // Skip if not on projects page

    try {
        const response = await fetch('/api/projects');
        const data = await response.json();
        
        let projectsList = [];
        if (Array.isArray(data)) {
            projectsList = data;
        } else if (data && Array.isArray(data.data)) {
            projectsList = data.data;
        } else {
            return;
        }
        
        const statusCounts = {
            'Pending': 0,
            'Active': 0,
            'Completed': 0
        };
        
        projectsList.forEach(project => {
            if (statusCounts.hasOwnProperty(project.status)) {
                statusCounts[project.status]++;
            }
        });
        
        const existingChart = Chart.getChart(ctx);
        if (existingChart) existingChart.destroy();
        
        const allStatuses = Object.keys(statusCounts).filter(status => statusCounts[status] > 0);
        const statusColors = {
            'Pending': '#ff9100',
            'Active': '#00f2fe', 
            'Completed': '#00e676',
            'Pending Approval': '#ff9100',
            'In Progress': '#00f2fe',
            'On Hold': '#ff003c',
            'Cancelled': '#ff003c'
        };
        
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: allStatuses,
                datasets: [{
                    data: allStatuses.map(status => statusCounts[status]),
                    backgroundColor: allStatuses.map(status => statusColors[status] || '#8892b0'),
                    borderWidth: 2,
                    borderColor: '#0a192f',
                    borderRadius: 8,
                    hoverOffset: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: '#ffffff',
                            padding: 20,
                            font: {
                                size: 12,
                                weight: '600'
                            },
                            usePointStyle: true,
                            pointStyle: 'circle'
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(10, 25, 47, 0.9)',
                        titleColor: '#00f2fe',
                        bodyColor: '#ffffff',
                        borderColor: '#00f2fe',
                        borderWidth: 2,
                        padding: 12,
                        displayColors: true,
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.parsed || 0;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((value / total) * 100).toFixed(1);
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                },
                animation: {
                    animateScale: true,
                    animateRotate: true
                }
            }
        });
    } catch (error) {
        console.error('Error loading project chart:', error);
    }
}

function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

/**
 * Asynchronously loads project data from Flask API and renders cards.
 */
async function loadProjects() {
    const list = document.getElementById("projectsList");
    if (!list) return; // Exit if container isn't present

    try {
        const res = await safeFetch("/api/projects");
        const data = Array.isArray(res) ? res : (res && Array.isArray(res.data) ? res.data : null);

        if (!data) {
            list.innerHTML = `<li style="color: #94a3b8; text-align: center; padding: 20px;">No projects found.</li>`;
            return;
        }

        const countEl = document.getElementById("projectCount");
        if (countEl) countEl.textContent = data.length;

        const activeCountEl = document.getElementById("activeCount");
        if (activeCountEl) {
            const activeCount = data.filter(p => ['Active', 'In Progress'].includes(p.status)).length;
            activeCountEl.textContent = activeCount;
        }
        const completedCountEl = document.getElementById('completedCount')
        if (completedCountEl) {
            const completedCount = data.filter(p => ['Completed'].includes(p.status)).length;
            completedCountEl.textContent = completedCount;
        }
        const pendingCountEl = document.getElementById('pendingCount')
        if (pendingCountEl) {
            const pendingCount = data.filter(p => ['Pending', 'Not Completed'].includes(p.status)).length;
            pendingCountEl.textContent = pendingCount;
        }

        list.innerHTML = "";

        data.forEach(p => {
            const li = document.createElement("li");
            li.className = "project-item";
            li.style.cssText = "background: #112240; border: 1px solid #233554; border-radius: 8px; padding: 16px; margin-bottom: 12px; list-style: none;";
            const paid = p.amount_paid || 0;
            const price = p.price || 0;
            const statusColor = p.status === 'Completed' ? '#00e676' : (p.status === 'Pending' ? '#ff9100' : '#00f2fe');

            // 1. Deadline Badge (Using backend server-calculated fields)
            let deadlineHtml = "";
            if (p.deadline) {
                const days = p.days_until_deadline;
                const status = p.deadline_status; // 'overdue', 'urgent', or 'normal'
                const alertColor = status === 'overdue' ? "#ff003c" : (status === 'urgent' ? "#ff9100" : "#00f2fe");
                const text = days < 0 ? `OVERDUE (${Math.abs(days)} Days)` : `${0-days} Days Remaining`;

                deadlineHtml = `
                    <div style="color: ${alertColor}; font-size: 11px; margin-top: 4px; font-weight: bold; text-transform: uppercase;">
                        <i class="fa-solid fa-clock"></i> ${text}
                    </div>
                `;
            }

            // 2. Attachments List (Mapping backend attached_files array)
            let filesHtml = '<div style="font-size: 12px; color: #64748b;">No attachments</div>';
            if (Array.isArray(p.attached_files) && p.attached_files.length > 0) {
                filesHtml = p.attached_files.map(file => {
                    const name = escapeHtml(file.original_filename || 'Attachment');
                    const size = file.file_size ? (file.file_size / 1024).toFixed(1) + ' KB' : 'N/A';
                    const downloadUrl = file.download_url ? escapeHtml(file.download_url) : '#';

                    return `
                        <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(0,0,0,0.2); padding: 6px 10px; border-radius: 4px; margin-top: 4px; font-size: 12px;">
                            <span><i class="fa-solid fa-paperclip" style="color: #00f2fe; margin-right: 6px;"></i>${name} (${size})</span>
                            <a href="${downloadUrl}" download style="color: #00f2fe; text-decoration: none; font-weight: bold;">Download</a>
                        </div>
                    `;
                }).join('');
            }

            // 3. Owner / Client Name
            const clientName = escapeHtml(p.client_name || (p.client_details ? p.client_details.username : 'Unassigned'));

            // Render complete list item HTML
            li.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px;">
                    <div>
                        <h4 style="margin: 0; color: white; font-size: 15px;">${escapeHtml(p.title)}</h4>
                        ${deadlineHtml}            
                    </div>
                    <div style="text-align: right;">
                        <h5 style="margin: 0; color: white; font-size: 13px;"><i class="fa-solid fa-user"></i> Owner: ${clientName}</h5>
                    </div>
                    <span style="padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: bold; background: ${statusColor}22; color: ${statusColor}; border: 1px solid ${statusColor}55;">
                        ${escapeHtml(p.status || 'Active')}
                    </span>
                </div>

                <div style="color: #8892b0; font-size: 13px; margin-bottom: 10px;">
                    ${escapeHtml(p.desc || "System parameters initialized.")}
                </div>
                
                <div style="margin-bottom: 10px;">
                    ${filesHtml}
                </div>
                
                <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(0,0,0,0.2); padding: 10px; border-radius: 8px;">
                    <div style="font-size: 12px; color: #e2e8f0;">Value: £${price.toFixed(2)} | Paid: £${paid.toFixed(2)}</div>
                    <div style="display: flex; gap: 5px;">
                        <input data-id="${p.id}" class="payInput" placeholder="£" type="number" step="0.01" style="padding: 5px; width: 65px; height: 30px; background: #0a192f; border: 1px solid #233554; color: white; border-radius: 4px;">
                        <button onclick="addPayment(${p.id})" style="padding: 0 10px; font-size: 11px; height: 30px; background: #00f2fe; color: #0a192f; border: none; border-radius: 4px; font-weight: bold; cursor: pointer;">Process</button>
                    </div>
                </div>
            `;

            list.appendChild(li);
        });

    } catch (err) {
        console.error("Failed to load projects:", err);
        list.innerHTML = `<li style="color: #ff003c; text-align: center; padding: 20px;">Unable to load project data.</li>`;
    }
}


async function loadClients() {
    const list = document.getElementById("clientList");
    if (!list) return; // Only process if list container exists (e.g., on clients.html)
    
    const data = await safeFetch("/api/clients");
    if (!data || !Array.isArray(data)) return;

    list.innerHTML = "";
    data.forEach(c => {
        const li = document.createElement("li");
        const subtitle = c.company || c.email || "Active Client";
        const name = c.username || c.name || "Unknown";
        
        li.style.cssText = "padding: 15px; margin-bottom: 10px; border-radius: 12px; background: rgba(255,255,255,0.03); border-left: 3px solid #00f2fe; cursor: pointer; transition: 0.3s;";
        li.innerHTML = `
            <div class="client-info">
                <strong style="color: #fff; font-size: 16px;">${escapeHtml(name)}</strong>
                <span style="display: block; font-size: 0.8em; color: #94a3b8; margin-top: 2px;">${escapeHtml(subtitle)}</span>
            </div>
            <small style="color: #00f2fe; font-weight: bold; font-family: 'Rajdhani', sans-serif; letter-spacing: 1px; text-transform: uppercase;">View</small>
        `;
        li.onclick = () => openMessages(c);
        list.appendChild(li);
    });
}

async function openMessages(client) {
    currentClientId = client.id;
    previousMessageHash = ""; // Reset message comparison hash
    const panel = document.getElementById("messagePanel");
    const nameLabel = document.getElementById("msgClientName");
    
    if (panel && panel.style.display === "none") {
        panel.style.display = "block";
    }
    if (nameLabel) nameLabel.textContent = (client.username || client.name || "Client").toUpperCase();

    // Trigger visual loading cue if switching
    const box = document.getElementById("messageList");
    if(box) box.innerHTML = `<div class="text-center opacity-50 py-10 text-xs"><i class="fa-solid fa-spinner fa-spin text-cyan-400 text-2xl mb-2"></i><br>SYNCING SECURE CHANNEL...</div>`;

    await refreshMessageThread();
    if (panel) panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

async function refreshMessageThread() {
    if (!currentClientId || document.visibilityState === 'hidden' || window.isTransmitting) return;
    
    const box = document.getElementById("messageList");
    if (!box) return;

    const data = await safeFetch(`/api/messages/${currentClientId}`);
    if (!data || !Array.isArray(data)) return;

    // PERFORMANCE: Skip parsing and repainting the DOM if message payload remains identical
    const currentMessageHash = JSON.stringify({ count: data.length, last_id: data.length > 0 ? data[data.length - 1].id : 0 });
    if (currentMessageHash === previousMessageHash) return;
    previousMessageHash = currentMessageHash;

    const isAtBottom = box.scrollHeight - box.scrollTop <= box.clientHeight + 100;
    
    if (data.length === 0) {
        box.innerHTML = `<div class="text-center opacity-30 py-10 text-xs"><i class="fa-solid fa-satellite-dish text-2xl mb-2"></i><br>NO SECURE TRANSMISSIONS LOGGED</div>`;
        return;
    }

    box.innerHTML = data.map(m => {
        const isAdmin = m.sender === 'admin' || m.from === 'admin' || m.from_role === 'admin';
        const timeStr = m.timestamp ? new Date(m.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : '--:--';
        
        let filesHtml = '';
        if (m.attachments && m.attachments.length > 0) {
            filesHtml = '<div style="margin-top: 10px; display: flex; flex-wrap: wrap; gap: 8px;">';
            m.attachments.forEach(f => {
                const fileSizeKb = (f.file_size / 1024).toFixed(1);
                filesHtml += `
                    <a href="/api/files/${f.id}/download" 
                       style="padding: 6px 10px; background: rgba(0,242,254,0.15); border: 1px solid rgba(0,242,254,0.3); border-radius: 6px; color: #00f2fe; text-decoration: none; font-size: 12px; display: flex; align-items: center; gap: 6px; transition: background 0.2s;"
                       onmouseover="this.style.background='rgba(0,242,254,0.3)'"
                       onmouseout="this.style.background='rgba(0,242,254,0.15)'">
                        <i class="fa-solid fa-paperclip"></i>
                        <span>${escapeHtml(f.original_filename)} (${fileSizeKb}KB)</span>
                    </a>
                `;
            });
            filesHtml += '</div>';
        }

        return `
            <div class="message-wrapper" style="display: flex; flex-direction: column; width: 100%; margin-bottom: 12px; align-items: ${isAdmin ? 'flex-end' : 'flex-start'};">
                <div class="msg-bubble shadow-md" 
                     style="padding: 10px 16px; border-radius: 18px; max-width: 75%; font-size: 13px; line-height: 1.4;
                     ${isAdmin ? 
                        'background: linear-gradient(135deg, #0072ff, #00c6ff); color: white; border-bottom-right-radius: 4px;' : 
                        'background: rgba(255,255,255,0.08); color: #cbd5e1; border: 1px solid rgba(255,255,255,0.1); border-bottom-left-radius: 4px;'}">
                    ${escapeHtml(m.content)}
                    ${filesHtml}
                </div>
                <span style="font-size: 9px; color: #64748b; margin-top: 4px; padding: 0 4px; text-transform: uppercase;">
                    ${isAdmin ? 'Studio' : 'Client'} • ${timeStr}
                </span>
            </div>
        `;
    }).join('');

    if (isAtBottom || previousMessageHash === "") {
        requestAnimationFrame(() => {
            setTimeout(() => {
                box.scrollTop = box.scrollHeight;
            }, 30);
        });
    }
}

/**
 * UNIFIED FILE UPLOAD & MANAGEMENT (Admin Integration)
 */
let adminPendingFile = null;

function initializeFileUpload() {
    const fileInput = document.getElementById('fileInput');
    if (fileInput) {
        fileInput.addEventListener('change', handleAdminFileSelection);
    }
}

function handleAdminFileSelection(e) {
    const fileInput = e.target;
    if (fileInput.files && fileInput.files.length > 0) {
        adminPendingFile = fileInput.files[0];
        
        if (adminPendingFile.size > 100 * 1024 * 1024) {
            showWarning('File too large (max 100MB)');
            removeAdminSelectedFile();
            return;
        }
        
        const preview = document.getElementById('adminFilePreviewContainer');
        const filenameSpan = document.getElementById('adminPreviewFilename');
        if (preview && filenameSpan) {
            filenameSpan.textContent = adminPendingFile.name;
            preview.style.display = 'flex';
        }
    }
}

function removeAdminSelectedFile() {
    adminPendingFile = null;
    const fileInput = document.getElementById('fileInput');
    if (fileInput) fileInput.value = '';
    const preview = document.getElementById('adminFilePreviewContainer');
    if (preview) preview.style.display = 'none';
}

async function sendMessage() {
    const input = document.getElementById("msgContent");
    let content = input ? input.value.trim() : "";
    
    if (!content && !adminPendingFile) return;
    if (!currentClientId) {
        showWarning("Please select a client to communicate with.");
        return;
    }

    if (!content && adminPendingFile) {
        content = `📎 Attached File: ${adminPendingFile.name}`;
    }

    if (input) input.value = ""; 
    
    // Block polling cycles while we transmit the API request
    window.isTransmitting = true;
    const box = document.getElementById("messageList");

    // Local echo for instant response
    const localTimeStr = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    const tempWrapper = document.createElement("div");
    tempWrapper.className = "message-wrapper";
    tempWrapper.style.cssText = "display: flex; flex-direction: column; width: 100%; margin-bottom: 12px; align-items: flex-end; opacity: 0.7;";
    
    const attachmentHtml = adminPendingFile ? `<div style="margin-top: 5px; font-size: 11px; color: rgba(255,255,255,0.7);"><i class="fa-solid fa-paperclip"></i> ${escapeHtml(adminPendingFile.name)}</div>` : '';

    tempWrapper.innerHTML = `
        <div class="msg-bubble shadow-md" style="padding: 10px 16px; border-radius: 18px; max-width: 75%; font-size: 13px; line-height: 1.4; background: linear-gradient(135deg, #0072ff, #00c6ff); color: white; border-bottom-right-radius: 4px;">
            ${escapeHtml(content)}
            ${attachmentHtml}
        </div>
        <span class="msg-indicator" style="font-size: 9px; color: #64748b; margin-top: 4px; padding: 0 4px; text-transform: uppercase;">
            Studio • ${localTimeStr} (Sending...)
        </span>
    `;
    box.appendChild(tempWrapper);
    
    requestAnimationFrame(() => {
        box.scrollTop = box.scrollHeight;
    });
    const now = new Date();
    try {
        // Step 1: Send Parent Message
        const response = await safeFetch(`/api/messages/${currentClientId}`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ 
                content: content,
                sender: 'admin',
                timestamp: now.toISOString()
            })
        });

        if (!response || response.status !== "success") {
            throw new Error("Failed transmission");
        }

        const indicator = tempWrapper.querySelector(".msg-indicator");
        
        // Step 2: Push Attachments if required
        if (adminPendingFile) {
            if (indicator) indicator.textContent = `Studio • ${localTimeStr} (Uploading file...)`;
            const messageId = response.message.id;
            const formData = new FormData();
            formData.append('file', adminPendingFile);

            const uploadRes = await fetch(`/api/messages/${messageId}/upload`, {
                method: 'POST',
                body: formData
            });

            if (!uploadRes.ok) {
                showWarning('Message sent, but network error interrupted file upload.');
            }
        }

        // Cleanup
        removeAdminSelectedFile();
        previousMessageHash = ""; 
        await refreshMessageThread();

    } catch(err) {
        tempWrapper.style.opacity = "0.5";
        const indicator = tempWrapper.querySelector(".msg-indicator");
        if (indicator) {
            indicator.textContent = "Failed to Transmit";
            indicator.style.color = "#ef4444";
        }
        showWarning("Failed to transmit message. Please check connection.");
    } finally {
        window.isTransmitting = false;
        if(input) input.focus();
    }
}

async function addClient() {
    const nameInput = document.getElementById("c_name");
    const emailInput = document.getElementById("c_email");
    const companyInput = document.getElementById("c_company");
    const phoneInput = document.getElementById("c_phone");
    const notesInput = document.getElementById("c_notes");
    
    if (!nameInput || !nameInput.value.trim()) {
        showWarning("Please enter a client name");
        return;
    }

    const payload = {
        username: nameInput.value.trim(),
        email: (emailInput && emailInput.value.trim()) || "N/A",
        company: (companyInput && companyInput.value.trim()) || "N/A",
        phone: (phoneInput && phoneInput.value.trim()) || "N/A",
        notes: (notesInput && notesInput.value.trim()) || "",
        role: "Client"
    };

    const response = await safeFetch("/api/clients/add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });

    if (response && response.status === "success") {
        [nameInput, emailInput, companyInput, phoneInput, notesInput].forEach(i => { if(i) i.value = ""; });
        showWarning(`✓ Client "${payload.username}" added successfully!`);
        await loadClients();
    } else {
        showWarning("Failed to add client. Please try again.");
    }
}

async function addPayment(projectId) {
    const input = document.querySelector(`input.payInput[data-id="${projectId}"]`);
    if (!input || !input.value.trim()) return;

    const amount = parseFloat(input.value);
    if (isNaN(amount) || amount <= 0 || amount > 999999.99) {
        showWarning("Please enter a valid amount between 0.01 and 999,999.99");
        return;
    }

    input.disabled = true;
    const result = await safeFetch(`/api/projects/${projectId}/payment`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ amount: amount })
    });
    input.disabled = false;
    
    if (result && result.status === "success") {
        input.value = "";
        showWarning(`✓ Payment of £${amount.toFixed(2)} processed successfully!`);
        await loadProjects();
        await loadDashboard();
        await loadProjectChart();
    } else {
        showWarning("Failed to process payment. Please try again.");
    }
}

async function addProject() {
    const form = document.getElementById('addProjectForm');
    if (!form) return;
    const projectData = {
        client_user_id: document.getElementById('clientId').value,
        title: document.getElementById('projectTitle').value,
        desc: document.getElementById('projectDescription').value,
        price: parseFloat(document.getElementById('projectPrice').value) || 0,
        status: document.getElementById('projectStatus').value,
        deadline: document.getElementById('projectDeadline').value,
        amount_paid: 0
    };
    
    if (!projectData.client_user_id || !projectData.title || !projectData.desc) {
        showWarning('Please fill in all required fields');
        return;
    }
    
    try {
        const response = await fetch('/api/projects', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(projectData)
        });
        
        if (response.ok) {
            form.reset();
            showWarning('✓ Project created successfully!');
            await loadProjects();
            await loadDashboard();
            await loadProjectChart();
        } else {
            const error = await response.json();
            showWarning(error.error || 'Failed to create project');
        }
    } catch (error) {
        console.error('Error creating project:', error);
        showWarning('Failed to create project');
    }
}

// Global Poll Initializer
window.onload = () => {
    loadDashboard();
    loadClients();
    loadProjects();
    loadProjectChart();
    initializeFileUpload();
    initializeWebSocket();
    requestNotificationPermission();

    // Add project form handler
    const addProjectForm = document.getElementById('addProjectForm');
    if (addProjectForm) {
        addProjectForm.addEventListener('submit', (e) => {
            e.preventDefault();
            addProject();
        });
    }

    // Centralized Smart Polling Loop
    setInterval(() => {
        if (document.visibilityState === 'visible' && currentClientId) {
            if (document.getElementById("messageList")) {
                refreshMessageThread();
            }
        }
    }, 2000); 
};

// Expose handlers globally for inline HTML execution
window.addPayment = addPayment;
window.addProject = addProject;
window.sendMessage = sendMessage;
window.openMessages = openMessages;
window.addClient = addClient;
window.removeAdminSelectedFile = removeAdminSelectedFile;