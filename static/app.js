let currentClientId = null;
let timelineChart = null;
const appId = typeof __app_id !== 'undefined' ? __app_id : 'default-app-id';

/**
 * GENERIC WARNING SYSTEM
 */

// Create warning styles if not already present
function createWarningStyles() {
    if (document.getElementById('dynamic-warning-styles')) return;
    
    const style = document.createElement('style');
    style.id = 'dynamic-warning-styles';
    style.textContent = `
        .dynamic-warning {
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(255, 152, 0, 0.95);
            border: 1px solid rgba(255, 152, 0, 0.8);
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            z-index: 10000;
            max-width: 400px;
            font-family: Arial, sans-serif;
            animation: slideIn 0.3s ease;
        }
        
        .dynamic-warning i {
            margin-right: 0.5rem;
        }
        
        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
    `;
    document.head.appendChild(style);
}

// Generic warning function
function showWarning(message) {
    createWarningStyles();
    
    // Remove existing warnings
    document.querySelectorAll('.dynamic-warning').forEach(w => w.remove());
    
    const warning = document.createElement('div');
    warning.className = 'dynamic-warning';
    warning.innerHTML = `<i class="fa-solid fa-exclamation-triangle"></i>${message}`;
    document.body.appendChild(warning);
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        warning.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => warning.remove(), 300);
    }, 5000);
}

/**
 * FEEDBACK FUNCTIONALITY
 */

// Star rating system
function initializeStarRating() {
    const stars = document.querySelectorAll('.star');
    const ratingInput = document.getElementById('rating');
    let currentRating = 0;

    stars.forEach(star => {
        star.addEventListener('click', function() {
            currentRating = parseInt(this.dataset.rating);
            ratingInput.value = currentRating;
            updateStars(currentRating);
        });

        star.addEventListener('mouseenter', function() {
            const hoverRating = parseInt(this.dataset.rating);
            updateStars(hoverRating);
        });
    });

    document.getElementById('starRating')?.addEventListener('mouseleave', function() {
        updateStars(currentRating);
    });

    function updateStars(rating) {
        stars.forEach((star, index) => {
            if (index < rating) {
                star.classList.add('active');
            } else {
                star.classList.remove('active');
            }
        });
    }
}

// Service category selection
function initializeServiceCategories() {
    const categoryChips = document.querySelectorAll('.category-chip');
    const serviceInput = document.getElementById('serviceCategory');
    let selectedService = '';

    categoryChips.forEach(chip => {
        chip.addEventListener('click', function() {
            categoryChips.forEach(c => c.classList.remove('selected'));
            this.classList.add('selected');
            selectedService = this.dataset.service;
            serviceInput.value = selectedService;
        });
    });
}

// Feedback form submission is handled in client_feedback.html
// This function is kept for compatibility but does nothing
function initializeFeedbackForm() {
    // Feedback form is now handled locally in each template to avoid duplicate submissions
    return;
}

// Load existing feedback
async function loadFeedback() {
    try {
        const response = await fetch('/api/feedback');
        const feedbacks = await response.json();
        
        const feedbackGrid = document.getElementById('feedbackGrid');
        if (!feedbackGrid) return;

        feedbackGrid.innerHTML = '';

        feedbacks.forEach(feedback => {
            const card = createFeedbackCard(feedback);
            feedbackGrid.appendChild(card);
        });
    } catch (error) {
        console.error('Error loading feedback:', error);
    }
}

function createFeedbackCard(feedback) {
    const card = document.createElement('div');
    card.className = 'feedback-card';
    
    const stars = '&#9733;'.repeat(feedback.rating) + '&#9734;'.repeat(5 - feedback.rating);
    
    card.innerHTML = `
        <div class="feedback-header-info">
            <div class="client-name">${feedback.client_name}</div>
            <div class="feedback-date">${new Date(feedback.created_at).toLocaleDateString()}</div>
        </div>
        <div class="feedback-stars">${stars}</div>
        <div class="feedback-service">${feedback.service_category}</div>
        <div class="feedback-comment">${feedback.comment}</div>
    `;
    
    return card;
}

// Initialize feedback page
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on the feedback page
    if (document.getElementById('feedbackForm')) {
        initializeStarRating();
        initializeServiceCategories();
        initializeFeedbackForm();
        loadFeedback();
    }
});

/**
 * REVISED safeFetch
 * Removed the automatic window.location.href redirect.
 * Now it simply returns null on failure, allowing the UI to stay on the page.
 */
async function safeFetch(path, options = {}) {
    const url = window.location.origin + path;
    try {
        const res = await fetch(url, options);
        
        // Check for unauthorized but DO NOT redirect.
        // This stops the "immediate logout" loop.
        if (res.status === 401 || res.status === 403) {
            console.warn("Access denied or session expired for:", path);
            return null;
        }

        const contentType = res.headers.get("content-type");
        // If server returns HTML instead of JSON (like a login page), just fail gracefully.
        if (!res.ok || (contentType && contentType.includes("text/html"))) {
            return null;
        }
        
        return await res.json();
    } catch (err) {
        // Log error only in development/explicitly
        console.error(`Fetch error [${path}]:`, err);
        return null;
    }
}

/**
 * DASHBOARD & ANALYTICS
 */
async function loadDashboard() {
    const data = await safeFetch("/api/dashboard");
    if (!data) return;

    const revEl = document.getElementById("dashRevenue");
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
                borderWidth: 0,
                hoverOffset: 4
            }]
        },
        options: {
            plugins: {
                legend: { labels: { color: "#e2e8f0", font: { family: "'Rajdhani', sans-serif" } } }
            }
        }
    });
}

/**
 * PROJECTS & TIMELINE
 */
async function loadProjects() {
    const list = document.getElementById("projectList");
    if (!list) return;

    const data = await safeFetch("/api/projects");
    if (!data || !Array.isArray(data)) return;

    const countEl = document.getElementById("projectCount");
    if (countEl) countEl.textContent = `Active Nodes: ${data.length}`;

    list.innerHTML = "";
    const chartLabels = [];
    const chartData = [];
    const chartColors = [];

    data.forEach(p => {
        const li = document.createElement("li");
        li.className = "project-item";
        
        const paid = p.amount_paid || 0;
        const statusColor = p.status === 'Completed' ? '#00e676' : (p.status === 'Pending' ? '#ff9100' : '#00f2fe');
        
        let deadlineHtml = "";
        if (p.deadline) {
            const today = new Date();
            const due = new Date(p.deadline);
            const diffDays = Math.ceil((due - today) / (1000 * 60 * 60 * 24));
            const alertColor = diffDays < 3 ? "#ff003c" : (diffDays < 7 ? "#ff9100" : "#00f2fe");
            
            deadlineHtml = `
                <div style="color: ${alertColor}; font-size: 11px; margin-top: 5px; font-family: 'Rajdhani'; font-weight: bold; text-transform: uppercase;">
                    <i class="fa-solid fa-clock-rotate-left"></i> ${diffDays} Days Remaining
                </div>
            `;

            if (p.status !== 'Completed') {
                chartLabels.push(p.title);
                chartData.push(diffDays);
                chartColors.push(alertColor);
            }
        }

        li.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px;">
                <div>
                    <h4 style="margin: 0; color: white;">${p.title}</h4>
                    ${deadlineHtml}
                </div>
                <span style="padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: bold; background: ${statusColor}22; color: ${statusColor}; border: 1px solid ${statusColor}55;">${p.status}</span>
            </div>
            <div style="color: #8892b0; font-size: 13px; margin-bottom: 10px;">${p.description || "System parameters initialized."}</div>
            <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(0,0,0,0.2); padding: 10px; border-radius: 8px;">
                <div style="font-size: 12px;">Value: £${p.price} | Paid: £${paid}</div>
                <div style="display: flex; gap: 5px;">
                    <input data-id="${p.id}" class="payInput" placeholder="£" style="padding: 5px; width: 60px; margin:0; height:30px; background:#0a192f; border:1px solid #233554; color:white;">
                    <button onclick="addPayment(${p.id})" style="padding: 0 10px; width: auto; margin:0; font-size:11px; height:30px; background:#00f2fe; color:#0a192f; border:none; border-radius:4px; cursor:pointer;">Process</button>
                </div>
            </div>
        `;
        list.appendChild(li);
    });
    renderTimelineChart(chartLabels, chartData, chartColors);
}

function renderTimelineChart(labels, data, colors) {
    const ctx = document.getElementById('timelineChart');
    if (!ctx) return;

    if (timelineChart) timelineChart.destroy();
    timelineChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors,
                borderWidth: 0,
                borderRadius: 8
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#8892b0' } },
                y: { grid: { display: false }, ticks: { color: '#fff', font: { family: 'Rajdhani' } } }
            }
        }
    });
}

async function loadClients() {
    const data = await safeFetch("/api/clients");
    const list = document.getElementById("clientList");
    if (!list || !data || !Array.isArray(data)) return;

    list.innerHTML = "";
    data.forEach(c => {
        const li = document.createElement("li");
        const subtitle = c.company || c.email || "Active Client";
        const name = c.username || c.name || "Unknown";
        
        li.style.cssText = "padding: 15px; margin-bottom: 10px; border-radius: 12px; background: rgba(255,255,255,0.03); border-left: 3px solid #00f2fe; cursor: pointer; transition: 0.3s;";
        li.innerHTML = `<strong style="color: #fff; font-size: 16px;">${name}</strong><br><small style="color: #4facfe;">${subtitle}</small>`;
        
        li.onclick = () => openMessages(c);
        list.appendChild(li);
    });
}

async function openMessages(client) {
    currentClientId = client.id;
    const panel = document.getElementById("messagePanel");
    const nameLabel = document.getElementById("msgClientName");
    
    if (panel) panel.style.display = "block";
    if (nameLabel) nameLabel.textContent = (client.username || client.name || "Client").toUpperCase();

    await refreshMessageThread();
    panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

async function refreshMessageThread() {
    if (!currentClientId || document.visibilityState === 'hidden') return;
    
    const data = await safeFetch(`/api/messages/${currentClientId}`);
    const box = document.getElementById("messageList");
    if (!box || !data || !Array.isArray(data)) return;

    const threshold = 100;
    const isAtBottom = box.scrollHeight - box.scrollTop <= box.clientHeight + threshold;
    
    box.innerHTML = data.map(m => {
        const isAdmin = m.sender === 'admin' || m.from === 'admin';
        const timeStr = m.timestamp ? new Date(m.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : '--:--';

        return `
            <div class="message-wrapper" style="display: flex; flex-direction: column; width: 100%; margin-bottom: 12px; align-items: ${isAdmin ? 'flex-end' : 'flex-start'};">
                <div class="msg-bubble" 
                     style="padding: 10px 16px; border-radius: 18px; max-width: 75%; font-size: 14px; line-height: 1.4;
                     ${isAdmin ? 
                        'background: linear-gradient(135deg, #0072ff, #00c6ff); color: white; border-bottom-right-radius: 4px;' : 
                        'background: rgba(255,255,255,0.08); color: #e2e8f0; border: 1px solid rgba(255,255,255,0.1); border-bottom-left-radius: 4px;'}">
                    ${m.content}
                </div>
                <span style="font-size: 9px; color: #8892b0; margin-top: 4px; padding: 0 4px;">
                    ${timeStr}
                </span>
            </div>
        `;
    }).join('');

    if (isAtBottom) {
        box.scrollTop = box.scrollHeight;
    }
}

async function sendMessage() {
    const input = document.getElementById("msgContent");
    if (!input || !input.value.trim() || !currentClientId) return;

    const content = input.value.trim();
    input.value = ""; 
    input.disabled = true;

    const response = await safeFetch(`/api/messages/${currentClientId}`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ 
            content: content,
            sender: 'admin',
            timestamp: new Date().toISOString()
        })
    });

    input.disabled = false;
    input.focus();

    if (response && response.status === "success") {
        await refreshMessageThread();
    }
}

async function addClient() {
    const nameInput = document.getElementById("c_name");
    const emailInput = document.getElementById("c_email");
    if (!nameInput || !nameInput.value.trim()) return;

    const payload = {
        username: nameInput.value.trim(),
        email: emailInput.value.trim() || "N/A",
        role: "Client"
    };

    const response = await safeFetch("/api/clients/add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });

    if (response && response.status === "success") {
        nameInput.value = "";
        if (emailInput) emailInput.value = "";
        await loadClients();
    }
}

async function addPayment(projectId) {
    const input = document.querySelector(`input.payInput[data-id="${projectId}"]`);
    if (!input || !input.value) return;

    const result = await safeFetch(`/api/projects/${projectId}/payment`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ amount: parseFloat(input.value) })
    });
    
    if (result) {
        input.value = "";
        await loadProjects();
        await loadDashboard();
    }
}

function initBackground() {
    const canvas = document.getElementById("bgCanvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    
    const resize = () => {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    };
    window.addEventListener("resize", resize);
    resize();

    let particles = Array.from({length: 40}, () => ({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 0.8,
        vy: (Math.random() - 0.5) * 0.8
    }));

    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        particles.forEach(p => {
            p.x += p.vx; p.y += p.vy;
            if (p.x < 0 || p.x > canvas.width) p.vx *= -1;
            if (p.y < 0 || p.y > canvas.height) p.vy *= -1;
            ctx.fillStyle = "rgba(0, 242, 254, 0.3)";
            ctx.beginPath(); ctx.arc(p.x, p.y, 1.5, 0, Math.PI*2); ctx.fill();
        });

        particles.forEach((p1, i) => {
            particles.slice(i+1).forEach(p2 => {
                let d = Math.hypot(p1.x - p2.x, p1.y - p2.y);
                if (d < 150) {
                    ctx.strokeStyle = `rgba(0, 242, 254, ${0.15 * (1 - d/150)})`;
                    ctx.beginPath(); ctx.moveTo(p1.x, p1.y); ctx.lineTo(p2.x, p2.y); ctx.stroke();
                }
            });
        });
        requestAnimationFrame(animate);
    }
    animate();
}

window.onload = () => {
    loadDashboard();
    loadClients();
    loadProjects();
    initBackground();

    setInterval(() => {
        if (document.visibilityState === 'visible') {
            const panel = document.getElementById("messagePanel");
            if (panel && panel.style.display !== "none") {
                refreshMessageThread();
            }
        }
    }, 5000);
};

// Global assignments for HTML onclick handlers
window.addPayment = addPayment;
window.sendMessage = sendMessage;
window.openMessages = openMessages;
window.addClient = addClient;