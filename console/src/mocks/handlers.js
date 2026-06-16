import { http, HttpResponse, delay } from 'msw';

const now = () => Date.now();
const unixNow = () => Math.floor(Date.now() / 1000);

let emergencyMode = false;
let articles = [
    {
        id: 1,
        question: 'Where can evacuees get drinking water?',
        answer: 'Drinking water is available at the logistics desk beside the registration area. Refill hours are 7:00 AM to 9:00 PM.',
        category: 'Supplies',
        status: 'published',
        enabled: true,
        source: 'manual',
        last_updated: unixNow() - 3600,
    },
    {
        id: 2,
        question: 'How do I report a missing family member?',
        answer: 'Go to the information desk and provide the person name, age, last known location, and contact details.',
        category: 'Assistance',
        status: 'published',
        enabled: true,
        source: 'manual',
        last_updated: unixNow() - 5400,
    },
    {
        id: 3,
        question: 'What medicines are available on site?',
        answer: 'Basic first aid, paracetamol, oral rehydration salts, and maintenance medicine coordination are available through the medical desk.',
        category: 'Medical',
        status: 'published',
        enabled: true,
        source: 'evac_sync',
        last_updated: unixNow() - 9600,
    },
    {
        id: 4,
        question: 'When is the next meal distribution?',
        answer: 'Meal distribution is scheduled at 7:30 AM, 12:00 PM, and 6:00 PM near the covered court.',
        category: 'Food',
        status: 'draft',
        enabled: false,
        source: 'manual',
        last_updated: unixNow() - 12000,
    },
];

let faqTracker = [
    { id: 1, source_question: 'Where is the medical desk?', question_display: 'Where is the medical desk?', count: 18, category: 'Medical', last_seen: unixNow() },
    { id: 2, source_question: 'Can I charge my phone?', question_display: 'Can I charge my phone?', count: 12, category: 'Facilities', last_seen: unixNow() - 900 },
    { id: 3, source_question: 'Is there food for children?', question_display: 'Is there food for children?', count: 9, category: 'Food', last_seen: unixNow() - 1800 },
];

let kiosks = [
    { kiosk_id: 'RK-KIOSK-001', kiosk_name: 'Main Entrance', ip: '192.168.1.21', status: 'online', last_seen: new Date().toISOString() },
    { kiosk_id: 'RK-KIOSK-002', kiosk_name: 'Medical Desk', ip: '192.168.1.22', status: 'online', last_seen: new Date(Date.now() - 180000).toISOString() },
    { kiosk_id: 'RK-KIOSK-003', kiosk_name: 'Dormitory Wing', ip: '192.168.1.23', status: 'offline', last_seen: new Date(Date.now() - 2400000).toISOString() },
];

let alerts = [
    {
        id: 101,
        type: 'EMERGENCY_ALERT',
        kiosk_id: 'RK-KIOSK-002',
        kiosk_name: 'Medical Desk',
        kiosk_location: 'Clinic Area',
        tier: 1,
        status: 'ACTIVE',
        timestamp: now() - 420000,
        language: 'en',
        transcript: 'A senior evacuee is having chest pain near the clinic area.',
    },
    {
        id: 102,
        type: 'EMERGENCY_ALERT',
        kiosk_id: 'RK-KIOSK-001',
        kiosk_name: 'Main Entrance',
        kiosk_location: 'Gate A',
        tier: 2,
        status: 'ACKNOWLEDGED',
        timestamp: now() - 900000,
        language: 'fil',
        transcript: 'May batang nawawala malapit sa entrance.',
    },
];

let historyAlerts = [
    {
        id: 77,
        kiosk_id: 'RK-KIOSK-003',
        kiosk_name: 'Dormitory Wing',
        kiosk_location: 'Room B',
        tier: 2,
        status: 'RESOLVED',
        timestamp: now() - 86400000,
        responding_at: now() - 85800000,
        resolved_at: now() - 84600000,
        resolved_by: 'Incident Team A',
        resolution_notes: 'Escorted resident to the medical desk and logged the case.',
        language: 'en',
        transcript: 'Need help with dizziness in dormitory wing.',
    },
];

let messages = [
    {
        id: 501,
        subject: 'Supply request',
        content: 'Need additional blankets and bottled water at Site B.',
        status: 'new',
        priority: 'high',
        category: 'supplies',
        source_hub_id: 'HUB-NORTH',
        source_hub_name: 'North Shelter',
        from_device_id: 'RK-HUB-NORTH',
        created_at: new Date(Date.now() - 300000).toISOString(),
    },
    {
        id: 502,
        subject: 'Medical transfer complete',
        content: 'Patient transferred to partner clinic. Monitoring continues.',
        status: 'read',
        priority: 'normal',
        category: 'medical',
        source_hub_id: 'HUB-EAST',
        source_hub_name: 'East Shelter',
        from_device_id: 'RK-HUB-EAST',
        created_at: new Date(Date.now() - 3600000).toISOString(),
    },
];

const kbSnapshot = () => ({
    kb_version: 12,
    generated_at: new Date().toISOString(),
    articles,
});

const ok = (body = {}) => HttpResponse.json(body);

export const handlers = [
    http.post('/auth/login', async () => {
        await delay(250);
        return ok({
            token: 'mock-portfolio-token',
            id: 1,
            username: 'admin',
            fname: 'Portfolio',
            lname: 'Reviewer',
            role: 'admin',
            is_first_login: false,
        });
    }),
    http.post('/auth/logout', () => new HttpResponse(null, { status: 204 })),
    http.post('/auth/setup', async ({ request }) => {
        const body = await request.json();
        return ok({ id: 1, username: body.username || 'admin', fname: body.fname, lname: body.lname, role: 'admin', is_first_login: false });
    }),
    http.get('/auth/me', () => ok({ id: 1, username: 'admin', fname: 'Portfolio', lname: 'Reviewer', role: 'admin', is_first_login: false })),

    http.get('/admin/ping', () => ok({ ok: true })),
    http.get('/health', () => ok({ status: 'ok' })),
    http.get('/kb/version', () => ok({ kb_version: 12 })),
    http.get('/kb/snapshot', () => ok(kbSnapshot())),
    http.post('/admin/article', async ({ request }) => {
        const body = await request.json();
        const article = { ...body, id: Date.now(), enabled: body.enabled ?? true, status: body.status || 'published', last_updated: unixNow() };
        articles = [article, ...articles];
        return HttpResponse.json(article, { status: 201 });
    }),
    http.put('/admin/article/:id', async ({ params, request }) => {
        const body = await request.json();
        articles = articles.map((article) => article.id === Number(params.id) ? { ...article, ...body, last_updated: unixNow() } : article);
        return ok(articles.find((article) => article.id === Number(params.id)) || body);
    }),
    http.delete('/admin/article/:id', ({ params }) => {
        articles = articles.filter((article) => article.id !== Number(params.id));
        return new HttpResponse(null, { status: 204 });
    }),
    http.post('/admin/import', async ({ request }) => {
        const body = await request.json();
        const incoming = (body.articles || []).map((article, index) => ({
            ...article,
            id: Date.now() + index,
            enabled: article.enabled ?? true,
            status: article.status || 'published',
            last_updated: unixNow(),
        }));
        articles = [...incoming, ...articles];
        return ok({ imported: incoming.length, articles: incoming });
    }),
    http.post('/admin/publish', () => ok({ published: true, kb_version: 13 })),

    http.get('/admin/emergency_mode', () => ok({ active: emergencyMode })),
    http.post('/admin/emergency_mode', async ({ request }) => {
        const body = await request.json();
        emergencyMode = !!body.active;
        return ok({ active: emergencyMode });
    }),

    http.get('/admin/faq-tracker', () => ok(faqTracker)),
    http.delete('/admin/faq-tracker/:id', ({ params }) => {
        faqTracker = faqTracker.filter((item) => item.id !== Number(params.id));
        return new HttpResponse(null, { status: 204 });
    }),
    http.delete('/admin/faq-tracker', () => {
        faqTracker = [];
        return new HttpResponse(null, { status: 204 });
    }),

    http.get('/admin/evac', () => ok({
        shelter_name: 'ResKiosk Demo Evacuation Center',
        location: 'Barangay Hall Covered Court',
        capacity: 350,
        current_occupancy: 214,
        contact_person: 'Demo Coordinator',
        contact_number: '+63 900 000 0000',
        notes: 'Portfolio demo data served by MSW.',
    })),
    http.put('/admin/evac', async ({ request }) => ok({ ...(await request.json()), updated: true })),
    http.get('/admin/evac/freshness', () => ok({ stale: false, last_confirmed_at: new Date().toISOString(), days_since_confirmed: 0 })),
    http.post('/admin/evac/freshness/confirm', () => ok({ stale: false, last_confirmed_at: new Date().toISOString(), days_since_confirmed: 0 })),

    http.get('/network/info', () => ok({
        device_id: 'RK-HUB-DEMO-001',
        ip: '192.168.1.10',
        online: true,
        kiosks_list: kiosks,
    })),
    http.post('/network/kiosk/name', async ({ request }) => {
        const body = await request.json();
        kiosks = kiosks.map((kiosk) => kiosk.kiosk_id === body.kiosk_id ? { ...kiosk, kiosk_name: body.kiosk_name } : kiosk);
        return ok({ ok: true });
    }),

    http.get('/emergency/active', () => ok({ alerts })),
    http.get('/emergency/history', () => ok({ alerts: historyAlerts })),
    http.patch('/emergency/:id/acknowledge', ({ params }) => {
        alerts = alerts.map((alert) => alert.id === Number(params.id) ? { ...alert, status: 'ACKNOWLEDGED', acknowledged_at: now() } : alert);
        return ok({ ok: true });
    }),
    http.patch('/emergency/:id/responding', ({ params }) => {
        alerts = alerts.map((alert) => alert.id === Number(params.id) ? { ...alert, status: 'RESPONDING', responding_at: now() } : alert);
        return ok({ ok: true });
    }),
    http.post('/emergency/:id/resolve', async ({ params, request }) => {
        const body = await request.json();
        const alert = alerts.find((item) => item.id === Number(params.id));
        if (alert) {
            const resolved = { ...alert, ...body, status: 'RESOLVED', resolved_at: now() };
            historyAlerts = [resolved, ...historyAlerts];
            alerts = alerts.filter((item) => item.id !== Number(params.id));
        }
        return ok({ ok: true });
    }),

    http.get('/lora/status', () => ok({ connected: true, port: 'COM4', auto_connect: true })),
    http.get('/lora/ports', () => ok({
        ports: [
            { port: 'COM4', description: 'USB Serial Relay' },
            { port: 'COM7', description: 'Bluetooth Relay Bridge' },
        ],
    })),
    http.post('/lora/connect', () => ok({ connected: true, port: 'COM4' })),
    http.post('/lora/disconnect', () => ok({ connected: false })),
    http.post('/lora/auto-connect', async ({ request }) => ok(await request.json())),
    http.get('/lora/encryption', () => ok({ enabled: true, has_key: true })),
    http.post('/lora/encryption', () => ok({ enabled: true, has_key: true })),
    http.delete('/lora/encryption', () => ok({ enabled: false, has_key: false })),
    http.post('/lora/send', async ({ request }) => {
        const body = await request.json();
        const message = { ...body, id: Date.now(), status: 'sent', created_at: new Date().toISOString() };
        messages = [message, ...messages];
        return ok({ ok: true, message });
    }),
    http.post('/lora/send_ack', () => ok({ ok: true })),

    http.get('/messages', () => ok({ messages, this_hub_id: 'HUB-DEMO' })),
    http.get('/messages/categories', () => ok({
        categories: [
            { id: 1, name: 'supplies' },
            { id: 2, name: 'medical' },
            { id: 3, name: 'operations' },
            { id: 4, name: 'security' },
        ],
    })),
    http.get('/messages/hubs', () => ok({
        hubs: [
            { hub_id: 'HUB-DEMO', hub_name: 'Demo Hub', device_id: 'RK-HUB-DEMO-001' },
            { hub_id: 'HUB-NORTH', hub_name: 'North Shelter', device_id: 'RK-HUB-NORTH' },
            { hub_id: 'HUB-EAST', hub_name: 'East Shelter', device_id: 'RK-HUB-EAST' },
        ],
    })),
    http.put('/messages/:id', async ({ params, request }) => {
        const body = await request.json();
        messages = messages.map((message) => message.id === Number(params.id) ? { ...message, ...body } : message);
        return ok(messages.find((message) => message.id === Number(params.id)));
    }),
    http.delete('/messages/:id', ({ params }) => {
        messages = messages.filter((message) => message.id !== Number(params.id));
        return new HttpResponse(null, { status: 204 });
    }),

    http.post('/admin/shutdown', () => ok({ ok: true })),
    http.post('/admin/restart', () => ok({ ok: true })),
];
