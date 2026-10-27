const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const path = require('node:path');
const { test } = require('node:test');
const { createContext, runInContext } = require('node:vm');
const { setImmediate } = require('node:timers/promises');

const root = path.resolve(__dirname, '..');
const base = readFileSync(path.join(root, 'templates/base.html'), 'utf8');
const page = readFileSync(path.join(root, 'templates/notifications.html'), 'utf8');
const html = base.replace('{% block content %}{% endblock %}', page);
const notification = {
    id: 1,
    type: 'message',
    title: 'New <message>',
    message: 'A client sent a message & attachment.',
    read: false,
    target_role: 'admin',
    created_at: '2026-09-18T12:00:00'
};

function createElement() {
    return {
        innerHTML: '',
        textContent: '',
        className: '',
        dataset: {},
        style: {},
        children: [],
        appendChild(child) { this.children.push(child); }
    };
}

function loadPage() {
    const elements = new Map([...html.matchAll(/\bid="([^"]+)"/g)]
        .map((match) => [match[1], createElement()]));
    elements.get('notificationsList').innerHTML = 'Loading notifications...';
    elements.get('typeFilter').value = 'all';
    elements.get('statusFilter').value = 'all';
    const listeners = new Map();
    const socketHandlers = new Map();
    const requests = [];
    const errors = [];
    let response = { notifications: [notification], pages: 1, current_page: 1 };
    const context = createContext({
        window: {},
        console: { log() {}, error(...args) { errors.push(args); } },
        document: {
            getElementById: (id) => elements.get(id) || null,
            createElement,
            addEventListener: (event, handler) => listeners.set(event, handler)
        },
        io: () => ({
            on: (event, handler) => socketHandlers.set(event, handler),
            emit() {}
        }),
        fetch: async (url) => {
            requests.push(url);
            let data;
            if (url === '/api/loggedin') {
                data = { status: 'loggedin', role: 'admin' };
            } else if (url === '/api/admin/notifications/stats') {
                data = { total: 1, unread: 1, read: 0 };
            } else if (url.startsWith('/api/admin/notifications?')) {
                data = response;
            } else {
                throw new Error(`Unexpected request: ${url}`);
            }
            return { ok: true, json: async () => data };
        }
    });

    for (const [, attributes, source] of html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/g)) {
        const src = attributes.match(/\bsrc="([^"]+)"/)?.[1];
        if (src === '/static/app.js') {
            runInContext(readFileSync(path.join(root, src), 'utf8'), context, { filename: src });
        } else if (!src && !attributes.includes('application/ld+json')) {
            runInContext(source, context, { filename: 'inline-template.js' });
        }
    }

    return {
        context, elements, listeners, socketHandlers, requests, errors,
        respondWith(data) { response = data; }
    };
}

test('HTTP notifications replace the history spinner after all page scripts load', async () => {
    const app = loadPage();
    app.listeners.get('DOMContentLoaded')();
    await setImmediate();

    const history = app.elements.get('notificationsList').innerHTML;
    assert.match(history, /New &lt;message&gt;/);
    assert.match(history, /A client sent a message &amp; attachment\./);
    assert.match(history, /notification-item unread/);
    assert.doesNotMatch(history, /Loading notifications/);
    assert.equal(app.elements.get('unreadNotifications').textContent, 1);
    assert.deepEqual(app.errors, []);
});

for (const socketFirst of [true, false]) {
    test(`history and bell dropdown render independently (${socketFirst ? 'socket' : 'HTTP'} first)`, async () => {
        const app = loadPage();
        app.context.initializeWebSocket();
        const receiveSocket = () => app.socketHandlers.get('notifications')({
            notifications: [{ ...notification, id: 2, title: 'Dropdown only' }]
        });
        if (socketFirst) receiveSocket();
        app.context.loadNotifications();
        await setImmediate();
        if (!socketFirst) receiveSocket();

        assert.match(app.elements.get('notificationsList').innerHTML, /New &lt;message&gt;/);
        assert.doesNotMatch(app.elements.get('notificationsList').innerHTML, /Dropdown only/);
        const dropdown = app.elements.get('notificationList').children;
        assert.equal(dropdown.length, 1);
        assert.match(dropdown[0].innerHTML, /Dropdown only/);
        assert.deepEqual(app.errors, []);
    });
}

test('filters and pagination refresh the history, including empty results', async () => {
    const app = loadPage();
    app.respondWith({ notifications: [notification], pages: 2, current_page: 1 });
    app.context.loadNotifications();
    await setImmediate();
    assert.equal(app.elements.get('pagination').style.display, 'flex');
    assert.equal(app.elements.get('prevBtn').disabled, true);

    app.respondWith({
        notifications: [{ ...notification, id: 3, title: 'Second page', read: true }],
        pages: 2, current_page: 2
    });
    app.context.loadNextPage();
    await setImmediate();
    assert.match(app.requests.at(-1), /page=2&/);
    assert.match(app.elements.get('notificationsList').innerHTML, /Second page/);
    assert.doesNotMatch(app.elements.get('notificationsList').innerHTML, /notification-item unread/);
    assert.equal(app.elements.get('nextBtn').disabled, true);

    app.elements.get('typeFilter').value = 'payment';
    app.elements.get('statusFilter').value = 'unread';
    app.respondWith({ notifications: [], pages: 0, current_page: 1 });
    app.context.filterNotifications();
    await setImmediate();
    assert.match(app.requests.at(-1), /page=1&per_page=10&type=payment&status=unread$/);
    assert.match(app.elements.get('notificationsList').innerHTML, /No new notification logs found/);
    assert.equal(app.elements.get('pagination').style.display, 'none');
    assert.deepEqual(app.errors, []);
});
