import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import hubClient from '../api/hubClient';
import {
    Send, Trash2, Eye, X, Radio, MessageSquare,
    Wifi, WifiOff, Usb, Bluetooth, RefreshCw, TerminalSquare, ArrowUp, ArrowDown,
    AlertTriangle, AlertOctagon, Info, CheckCircle, RotateCcw,
    Lock, Unlock, Copy, KeyRound
} from 'lucide-react';

const PRIORITY_COLORS = {
    normal: { bg: 'var(--bg-secondary)', color: 'var(--text-muted)', label: 'Normal' },
    urgent: { bg: '#ffa726', color: '#fff', label: 'Urgent' },
    emergency: { bg: 'var(--danger)', color: '#fff', label: 'Emergency' },
};

const STATUS_COLORS = {
    pending: { bg: 'var(--warning)', color: '#fff' },
    delivered: { bg: '#26a69a', color: '#fff' },
    read: { bg: 'var(--primary)', color: '#fff' },
    published: { bg: 'var(--success)', color: '#fff' },
    rejected: { bg: 'var(--danger)', color: '#fff' },
};

const INCOMING_MODAL_THEME = {
    emergency: {
        accent: 'var(--danger)',
        bg: '#2d1214',
        border: 'var(--danger)',
        iconBg: 'rgba(239, 83, 80, 0.15)',
        label: 'EMERGENCY',
        Icon: AlertOctagon,
    },
    urgent: {
        accent: '#ffa726',
        bg: '#2d2214',
        border: '#ffa726',
        iconBg: 'rgba(255, 167, 38, 0.15)',
        label: 'URGENT',
        Icon: AlertTriangle,
    },
    normal: {
        accent: 'var(--primary)',
        bg: 'var(--surface)',
        border: 'var(--primary)',
        iconBg: 'var(--primary-light)',
        label: 'NEW MESSAGE',
        Icon: Info,
    },
};

function IncomingLoraModal({ message, onClose, onViewDetails, thisHubDeviceId }) {
    const [ackStatus, setAckStatus] = useState(null);
    const [resending, setResending] = useState(false);
    const [resendDone, setResendDone] = useState(false);
    const [lastMessageId, setLastMessageId] = useState(null);

    // Reset states when a new message arrives
    useEffect(() => {
        if (message && message.id !== lastMessageId) {
            setAckStatus(null);
            setResending(false);
            setResendDone(false);
            setLastMessageId(message.id);
        }
    }, [message, lastMessageId]);

    if (!message) return null;

    const theme = INCOMING_MODAL_THEME[message.priority] || INCOMING_MODAL_THEME.normal;
    const { Icon } = theme;

    const senderLabel = message.source_hub_name || message.from_device_id || 'Unknown';

    const handleAcknowledge = async () => {
        setAckStatus('sending');
        try {
            const res = await hubClient.post('/lora/send_ack', {
                message_id: message.id,
            });
            if (res.data.ok) {
                setAckStatus('sent');
                window.__hubMessagesReload?.();
            } else {
                setAckStatus('error');
            }
        } catch {
            setAckStatus('error');
        }
    };

    const handleResend = async () => {
        setResending(true);
        setResendDone(false);
        try {
            // Resend = broadcast the received message to all devices (not back to sender)
            const payload = {
                target_hub_id: null, // Broadcast to all
                subject: message.subject || '(no subject)',
                content: message.content || '',
                priority: message.priority || 'normal',
            };
            const res = await hubClient.post('/lora/send', payload);
            if (res.data.ok) {
                setResendDone(true);
            } else {
                alert('Resend failed: ' + (res.data.error || 'Unknown error'));
            }
        } catch {
            alert('Resend failed.');
        } finally {
            setResending(false);
        }
    };

    return (
        <div className="modal-overlay" style={{ zIndex: 9999 }} onClick={onClose}>
            <div
                className="modal-content"
                onClick={e => e.stopPropagation()}
                style={{
                    maxWidth: '32rem',
                    border: `2px solid ${theme.accent}`,
                    animation: 'fadeIn 0.2s ease, loraModalPulse 0.6s ease',
                    overflow: 'hidden',
                }}
            >
                {/* Colored header strip */}
                <div style={{
                    background: theme.accent,
                    padding: '0.75rem 1.25rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.625rem',
                }}>
                    <div style={{
                        width: 32, height: 32, borderRadius: '50%',
                        background: 'rgba(255,255,255,0.2)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}>
                        <Icon size={18} color="#fff" />
                    </div>
                    <div style={{ flex: 1 }}>
                        <div style={{
                            fontSize: '0.65rem', fontWeight: 700, letterSpacing: '0.1em',
                            textTransform: 'uppercase', color: 'rgba(255,255,255,0.85)',
                        }}>
                            {theme.label}
                        </div>
                        <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#fff' }}>
                            LoRa Message Received
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        style={{
                            background: 'rgba(255,255,255,0.15)', border: 'none',
                            borderRadius: '50%', width: 28, height: 28,
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            cursor: 'pointer', color: '#fff',
                        }}
                    >
                        <X size={14} />
                    </button>
                </div>

                {/* Body */}
                <div style={{ padding: '1.25rem' }}>
                    {/* Auto-update confirmation banner */}
                    <div style={{
                        background: 'rgba(102, 187, 106, 0.1)',
                        border: '1px solid rgba(102, 187, 106, 0.3)',
                        borderRadius: 'var(--radius)',
                        padding: '0.625rem 0.875rem',
                        marginBottom: '1rem',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        fontSize: '0.8125rem',
                        color: '#66BB6A',
                    }}>
                        <CheckCircle size={16} style={{ flexShrink: 0 }} />
                        <span>
                            Message received — will automatically update <strong>{senderLabel}</strong>
                        </span>
                    </div>

                    <h3 style={{ margin: '0 0 0.75rem', fontSize: '1.05rem', fontWeight: 600 }}>
                        {message.subject || '(no subject)'}
                    </h3>

                    {message.content && (
                        <div style={{
                            background: 'var(--bg-secondary)',
                            borderRadius: 'var(--radius)',
                            padding: '0.75rem 1rem',
                            fontSize: '0.875rem',
                            lineHeight: 1.6,
                            whiteSpace: 'pre-wrap',
                            maxHeight: '10rem',
                            overflowY: 'auto',
                            marginBottom: '1rem',
                            borderLeft: `3px solid ${theme.accent}`,
                        }}>
                            {message.content}
                        </div>
                    )}

                    <div style={{
                        display: 'flex', flexWrap: 'wrap', gap: '0.5rem',
                        marginBottom: '1rem', fontSize: '0.8125rem',
                    }}>
                        <span className="badge" style={{
                            background: 'var(--bg-secondary)', color: 'var(--text-muted)',
                            fontSize: '0.75rem', display: 'inline-flex', alignItems: 'center', gap: '0.3rem',
                        }}>
                            <Radio size={12} /> LoRa
                        </span>
                        {(message.from_device_id || message.source_hub_name) && (
                            <span className="badge" style={{
                                background: 'var(--bg-secondary)', color: 'var(--text)',
                                fontSize: '0.75rem', display: 'inline-flex', alignItems: 'center', gap: '0.3rem',
                                fontFamily: "'Menlo','Consolas',monospace",
                            }}>
                                From: {senderLabel}
                            </span>
                        )}
                    </div>

                    {/* Response actions */}
                    <div style={{
                        background: 'var(--bg-secondary)',
                        borderRadius: 'var(--radius)',
                        padding: '0.75rem',
                        marginBottom: '1rem',
                    }}>
                        <div style={{
                            fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)',
                            textTransform: 'uppercase', letterSpacing: '0.05em',
                            marginBottom: '0.5rem',
                        }}>
                            Response Actions
                        </div>
                        <div className="flex gap-2 flex-wrap">
                            {ackStatus === 'sent' ? (
                                <div style={{
                                    display: 'inline-flex', alignItems: 'center', gap: '0.375rem',
                                    fontSize: '0.8125rem', color: '#66BB6A', fontWeight: 500,
                                    padding: '0.375rem 0.75rem',
                                    background: 'rgba(102, 187, 106, 0.1)',
                                    borderRadius: '6px',
                                }}>
                                    <CheckCircle size={14} /> Acknowledgment sent to {senderLabel}
                                </div>
                            ) : (
                                <button
                                    className="btn btn-sm"
                                    disabled={ackStatus === 'sending'}
                                    onClick={handleAcknowledge}
                                    style={{
                                        background: 'var(--success)',
                                        color: '#fff',
                                        border: 'none',
                                        opacity: ackStatus === 'sending' ? 0.7 : 1,
                                    }}
                                >
                                    <CheckCircle size={14} />
                                    {ackStatus === 'sending' ? 'Sending...' : ackStatus === 'error' ? 'Retry Acknowledgment' : 'Send Acknowledgment'}
                                </button>
                            )}

                            {resendDone ? (
                                <div style={{
                                    display: 'inline-flex', alignItems: 'center', gap: '0.375rem',
                                    fontSize: '0.8125rem', color: 'var(--primary)', fontWeight: 500,
                                    padding: '0.375rem 0.75rem',
                                    background: 'var(--primary-light)',
                                    borderRadius: '6px',
                                }}>
                                    <CheckCircle size={14} /> Message broadcast sent
                                </div>
                            ) : (
                                <button
                                    className="btn btn-sm"
                                    disabled={resending}
                                    onClick={handleResend}
                                    style={{
                                        background: 'transparent',
                                        color: 'var(--primary)',
                                        border: '1px solid var(--primary)',
                                        opacity: resending ? 0.7 : 1,
                                    }}
                                >
                                    <RotateCcw size={14} className={resending ? 'spin' : ''} />
                                    {resending ? 'Broadcasting...' : 'Broadcast Message'}
                                </button>
                            )}
                        </div>

                        {ackStatus === 'error' && (
                            <div style={{
                                fontSize: '0.75rem', color: 'var(--danger)', marginTop: '0.375rem',
                            }}>
                                Failed to send acknowledgment. Check LoRa connection and try again.
                            </div>
                        )}
                    </div>

                    <div className="flex justify-end gap-2" style={{ borderTop: '1px solid var(--border)', paddingTop: '0.75rem' }}>
                        <button className="btn" onClick={onClose}>Dismiss</button>
                        <button
                            className="btn"
                            style={{ background: theme.accent, color: '#fff', border: 'none' }}
                            onClick={() => { onViewDetails(message); onClose(); }}
                        >
                            <Eye size={15} /> View Details
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}


// ─── Messages Tab (original) ──────────────────────────────────────────────

function MessagesTab({ messages, categories, hubs, loading, loraConnected, thisHubId }) {
    const [direction, setDirection] = useState('all');
    const [filterStatus, setFilterStatus] = useState('all');
    const [showCompose, setShowCompose] = useState(false);
    const [viewMsg, setViewMsg] = useState(null);
    const [form, setForm] = useState({
        subject: '', content: '', target_hub_id: '', category_id: '', priority: 'normal'
    });
    const [sending, setSending] = useState(false);
    const [ackSending, setAckSending] = useState(false);

    const loadAll = useCallback(() => {
        window.__hubMessagesReload?.();
    }, []);

    useEffect(() => {
        window.__hubMessagesViewMsg = (msg) => setViewMsg(msg);
        return () => { delete window.__hubMessagesViewMsg; };
    }, []);

    const handleSend = async (e) => {
        e.preventDefault();
        if (!loraConnected) {
            alert('No LoRa device connected.');
            return;
        }
        setSending(true);
        try {
            const payload = {
                subject: form.subject,
                content: form.content,
                priority: form.priority,
                category_id: form.category_id ? parseInt(form.category_id) : null,
                target_hub_id: form.target_hub_id ? parseInt(form.target_hub_id) : null,
            };
            const res = await hubClient.post('/lora/send', payload);
            if (!res.data.ok) {
                alert('LoRa send failed: ' + (res.data.error || 'Unknown error'));
                setSending(false);
                return;
            }
            setShowCompose(false);
            setForm({ subject: '', content: '', target_hub_id: '', category_id: '', priority: 'normal' });
            loadAll();
        } catch (e) {
            alert('Failed to send message.');
        } finally {
            setSending(false);
        }
    };

    const handleDelete = async (id) => {
        if (!confirm('Delete this message?')) return;
        try {
            await hubClient.delete(`/messages/${id}`);
            if (viewMsg && viewMsg.id === id) setViewMsg(null);
            loadAll();
        } catch (e) {
            alert('Delete failed.');
        }
    };

    const handleStatusChange = async (id, status) => {
        try {
            const res = await hubClient.put(`/messages/${id}`, { status });
            if (viewMsg && viewMsg.id === id) setViewMsg(res.data);
            loadAll();
        } catch (e) {
            alert('Status update failed.');
        }
    };

    const handleSendAck = async (msg) => {
        setAckSending(true);
        try {
            const res = await hubClient.post('/lora/send_ack', { message_id: msg.id });
            if (res.data.ok) {
                handleStatusChange(msg.id, 'read');
            } else {
                alert('Acknowledgement failed: ' + (res.data.error || 'Unknown error'));
            }
        } catch {
            alert('Failed to send acknowledgement.');
        } finally {
            setAckSending(false);
        }
    };

    const isSent = (m) => m.source_hub_id === thisHubId;

    const filtered = messages.filter(m => {
        if (direction === 'sent' && !isSent(m)) return false;
        if (direction === 'received' && isSent(m)) return false;
        if (filterStatus !== 'all' && m.status !== filterStatus) return false;
        return true;
    });

    const sentCount = messages.filter(m => isSent(m)).length;
    const receivedCount = messages.filter(m => !isSent(m)).length;

    const fmtTime = (ts) => {
        if (!ts) return '—';
        return new Date(ts * 1000).toLocaleString();
    };

    const dirBtnStyle = (val) => {
        const active = direction === val;
        return {
            padding: '0.375rem 0.875rem',
            borderRadius: '6px',
            border: `1px solid ${active ? 'var(--primary)' : 'var(--border)'}`,
            background: active ? 'var(--primary)' : 'transparent',
            color: active ? '#fff' : 'var(--text-muted)',
            fontWeight: active ? 600 : 400,
            fontSize: '0.8125rem',
            cursor: 'pointer',
            fontFamily: 'inherit',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.375rem',
        };
    };

    if (loading) {
        return <p className="text-muted">Loading...</p>;
    }

    return (
        <>
            {/* Direction toggle + filters */}
            <div className="flex justify-between items-center" style={{ flexWrap: 'wrap', gap: '0.75rem' }}>
                <div className="flex gap-2 items-center">
                    <div className="flex" style={{ gap: '0.25rem', background: 'var(--bg-secondary)', borderRadius: '8px', padding: '3px' }}>
                        <button style={dirBtnStyle('all')} onClick={() => setDirection('all')}>
                            All
                            <span style={{ fontSize: '0.7rem', opacity: 0.75 }}>({messages.length})</span>
                        </button>
                        <button style={dirBtnStyle('received')} onClick={() => setDirection('received')}>
                            <ArrowDown size={14} />
                            Received
                            <span style={{ fontSize: '0.7rem', opacity: 0.75 }}>({receivedCount})</span>
                        </button>
                        <button style={dirBtnStyle('sent')} onClick={() => setDirection('sent')}>
                            <ArrowUp size={14} />
                            Sent
                            <span style={{ fontSize: '0.7rem', opacity: 0.75 }}>({sentCount})</span>
                        </button>
                    </div>
                    <select
                        value={filterStatus}
                        onChange={e => setFilterStatus(e.target.value)}
                        className="input"
                        style={{ maxWidth: '10rem' }}
                    >
                        <option value="all">All Status</option>
                        <option value="pending">Pending</option>
                        <option value="delivered">Delivered</option>
                        <option value="read">Read</option>
                        <option value="published">Published</option>
                        <option value="rejected">Rejected</option>
                    </select>
                    <span className="text-sm text-muted">{filtered.length} message(s)</span>
                </div>
                <button className="btn btn-primary" onClick={() => setShowCompose(true)}>
                    <Send size={16} /> Compose
                </button>
            </div>

            <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
                <table>
                    <thead>
                        <tr>
                            <th style={{ width: '3.5rem' }}></th>
                            <th>Subject</th>
                            <th>{direction === 'sent' ? 'To' : direction === 'received' ? 'From' : 'From / To'}</th>
                            <th>Priority</th>
                            <th>Status</th>
                            <th>Time</th>
                            <th style={{ width: '6rem' }}>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filtered.map(m => {
                            const pri = PRIORITY_COLORS[m.priority] || PRIORITY_COLORS.normal;
                            const st = STATUS_COLORS[m.status] || STATUS_COLORS.pending;
                            const sent = isSent(m);
                            return (
                                <tr key={m.id} style={{ cursor: 'pointer' }} onClick={() => setViewMsg(m)}>
                                    <td style={{ textAlign: 'center' }}>
                                        {sent ? (
                                            <ArrowUp size={15} style={{ color: 'var(--primary)' }} title="Sent" />
                                        ) : (
                                            <ArrowDown size={15} style={{ color: 'var(--success)' }} title="Received" />
                                        )}
                                    </td>
                                    <td style={{ fontWeight: 500 }}>{m.subject || '(no subject)'}</td>
                                    <td className="text-muted" style={{ fontFamily: "'Menlo','Consolas',monospace", fontSize: '0.75rem' }}>
                                        {sent
                                            ? (m.target_device_id || m.target_hub_name || 'Broadcast')
                                            : (m.source_device_id || m.source_hub_name || 'Unknown')
                                        }
                                    </td>
                                    <td>
                                        <span className="badge" style={{ background: pri.bg, color: pri.color, fontSize: '0.7rem' }}>
                                            {pri.label}
                                        </span>
                                    </td>
                                    <td>
                                        <span className="badge" style={{ background: st.bg, color: st.color, fontSize: '0.7rem', textTransform: 'uppercase' }}>
                                            {m.status}
                                        </span>
                                    </td>
                                    <td className="text-muted text-sm">{fmtTime(sent ? m.sent_at : (m.received_at || m.sent_at))}</td>
                                    <td>
                                        <div className="flex gap-1" onClick={e => e.stopPropagation()}>
                                            <button onClick={() => setViewMsg(m)} className="btn btn-icon" title="View">
                                                <Eye size={15} style={{ color: 'var(--primary)' }} />
                                            </button>
                                            <button onClick={() => handleDelete(m.id)} className="btn btn-icon" title="Delete">
                                                <Trash2 size={15} style={{ color: 'var(--danger)' }} />
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            );
                        })}
                        {filtered.length === 0 && (
                            <tr>
                                <td colSpan="7" className="empty-state">No messages found.</td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>

            {/* Compose Modal */}
            {showCompose && (
                <div className="modal-overlay" onClick={() => setShowCompose(false)}>
                    <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '34rem' }}>
                        <div className="modal-header">
                            <div className="flex items-center gap-2">
                                <Send size={20} style={{ color: 'var(--primary)' }} />
                                <h2 className="modal-title">Compose Message</h2>
                            </div>
                            <button className="btn-icon" onClick={() => setShowCompose(false)}>
                                <X size={18} />
                            </button>
                        </div>
                        <div className="modal-body">
                            <form onSubmit={handleSend}>
                                <div className="form-group">
                                    <label>Send Via</label>
                                    <div
                                        className="input"
                                        style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '0.5rem',
                                            background: 'var(--primary-light)',
                                            color: 'var(--primary)',
                                            fontWeight: 600,
                                        }}
                                    >
                                        <Radio size={14} />
                                        LoRa Radio
                                        <span
                                            style={{
                                                width: 6,
                                                height: 6,
                                                borderRadius: '50%',
                                                background: loraConnected ? 'var(--success)' : 'var(--danger)',
                                                display: 'inline-block',
                                                marginLeft: 4,
                                            }}
                                        />
                                    </div>
                                    <p className="form-hint" style={{ color: 'var(--primary)', marginTop: '0.375rem' }}>
                                        Message will be transmitted over LoRa radio to the target device.
                                    </p>
                                </div>

                                <div className="form-group">
                                    <label>Subject</label>
                                    <input
                                        required
                                        className="input"
                                        placeholder="Message subject..."
                                        value={form.subject}
                                        onChange={e => setForm({ ...form, subject: e.target.value })}
                                    />
                                </div>
                                <div className="grid-2" style={{ marginBottom: '1rem' }}>
                                    <div>
                                        <label>Category</label>
                                        <select
                                            className="input"
                                            value={form.category_id}
                                            onChange={e => setForm({ ...form, category_id: e.target.value })}
                                        >
                                            <option value="">— None —</option>
                                            {categories.map(c => (
                                                <option key={c.category_id} value={c.category_id}>{c.category_name}</option>
                                            ))}
                                        </select>
                                    </div>
                                    <div>
                                        <label>Target Device</label>
                                        <select
                                            className="input"
                                            value={form.target_hub_id}
                                            onChange={e => setForm({ ...form, target_hub_id: e.target.value })}
                                        >
                                            <option value="">Broadcast (all devices)</option>
                                            {hubs.map(h => (
                                                <option key={h.hub_id} value={h.hub_id}>
                                                    {h.device_id || h.hub_name}
                                                </option>
                                            ))}
                                        </select>
                                    </div>
                                </div>
                                <div className="form-group">
                                    <label>Priority</label>
                                    <div className="flex gap-3">
                                        {['normal', 'urgent', 'emergency'].map(p => {
                                            const pri = PRIORITY_COLORS[p];
                                            const selected = form.priority === p;
                                            return (
                                                <button
                                                    type="button"
                                                    key={p}
                                                    className="btn btn-sm"
                                                    style={{
                                                        background: selected ? pri.bg : 'transparent',
                                                        color: selected ? pri.color : 'var(--text-muted)',
                                                        border: `1px solid ${selected ? pri.bg : 'var(--border)'}`,
                                                        fontWeight: selected ? 600 : 400,
                                                    }}
                                                    onClick={() => setForm({ ...form, priority: p })}
                                                >
                                                    {pri.label}
                                                </button>
                                            );
                                        })}
                                    </div>
                                </div>
                                <div className="form-group">
                                    <label>Content</label>
                                    <textarea
                                        required
                                        className="textarea"
                                        placeholder="Write your message..."
                                        rows={5}
                                        value={form.content}
                                        onChange={e => setForm({ ...form, content: e.target.value })}
                                    />
                                </div>
                                <div className="flex justify-end gap-3" style={{ borderTop: '1px solid var(--border)', paddingTop: '1rem' }}>
                                    <button type="button" onClick={() => setShowCompose(false)} className="btn">Cancel</button>
                                    <button type="submit" className="btn btn-primary" disabled={sending || !loraConnected}>
                                        <Radio size={16} />
                                        {sending ? 'Sending via LoRa...' : 'Send via LoRa'}
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            )}

            {/* View Message Modal */}
            {viewMsg && (() => {
                const viewSent = isSent(viewMsg);
                return (
                    <div className="modal-overlay" onClick={() => setViewMsg(null)}>
                        <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '36rem' }}>
                            <div className="modal-header">
                                <div className="flex items-center gap-2">
                                    {viewSent
                                        ? <ArrowUp size={20} style={{ color: 'var(--primary)' }} />
                                        : <ArrowDown size={20} style={{ color: 'var(--success)' }} />
                                    }
                                    <h2 className="modal-title">{viewSent ? 'Sent Message' : 'Received Message'}</h2>
                                </div>
                                <button className="btn-icon" onClick={() => setViewMsg(null)}>
                                    <X size={18} />
                                </button>
                            </div>
                            <div className="modal-body">
                                <div style={{ marginBottom: '1.25rem' }}>
                                    <h3 style={{ margin: 0, fontSize: '1.1rem' }}>{viewMsg.subject || '(no subject)'}</h3>
                                    <div className="flex gap-2 items-center" style={{ marginTop: '0.5rem' }}>
                                        {(() => {
                                            const pri = PRIORITY_COLORS[viewMsg.priority] || PRIORITY_COLORS.normal;
                                            const st = STATUS_COLORS[viewMsg.status] || STATUS_COLORS.pending;
                                            return (
                                                <>
                                                    <span className="badge" style={{
                                                        background: viewSent ? 'var(--primary)' : 'var(--success)',
                                                        color: '#fff', fontSize: '0.7rem',
                                                        display: 'inline-flex', alignItems: 'center', gap: '0.25rem',
                                                    }}>
                                                        {viewSent ? <><ArrowUp size={10} /> Sent</> : <><ArrowDown size={10} /> Received</>}
                                                    </span>
                                                    <span className="badge" style={{ background: pri.bg, color: pri.color, fontSize: '0.7rem' }}>{pri.label}</span>
                                                    <span className="badge" style={{ background: st.bg, color: st.color, fontSize: '0.7rem', textTransform: 'uppercase' }}>{viewMsg.status}</span>
                                                </>
                                            );
                                        })()}
                                    </div>
                                </div>
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '1.25rem', fontSize: '0.85rem' }}>
                                    <div>
                                        <strong>From:</strong>{' '}
                                        <span style={{ fontFamily: "'Menlo','Consolas',monospace", fontSize: '0.8rem' }}>
                                            {viewMsg.source_device_id || viewMsg.source_hub_name || '—'}
                                        </span>
                                    </div>
                                    <div>
                                        <strong>To:</strong>{' '}
                                        <span style={{ fontFamily: "'Menlo','Consolas',monospace", fontSize: '0.8rem' }}>
                                            {viewMsg.target_device_id || viewMsg.target_hub_name || 'Broadcast'}
                                        </span>
                                    </div>
                                    <div><strong>Category:</strong> {viewMsg.category_name || '—'}</div>
                                    <div><strong>Via:</strong> {viewMsg.received_via || '—'}</div>
                                    <div><strong>Sent:</strong> {fmtTime(viewMsg.sent_at)}</div>
                                    <div><strong>Received:</strong> {fmtTime(viewMsg.received_at)}</div>
                                </div>
                                <div style={{ background: 'var(--bg-secondary)', borderRadius: '0.5rem', padding: '1rem', marginBottom: '1.25rem', whiteSpace: 'pre-wrap', fontSize: '0.9rem', lineHeight: 1.6 }}>
                                    {viewMsg.content || '(no content)'}
                                </div>
                                <div style={{ borderTop: '1px solid var(--border)', paddingTop: '1rem' }}>
                                    <label style={{ fontSize: '0.8rem', marginBottom: '0.5rem', display: 'block', color: 'var(--text-muted)' }}>
                                        Change Status
                                    </label>
                                    <div className="flex gap-2 flex-wrap">
                                        {['pending', 'delivered', 'read', 'published', 'rejected'].map(s => {
                                            const st = STATUS_COLORS[s];
                                            const isCurrent = viewMsg.status === s;
                                            return (
                                                <button
                                                    key={s}
                                                    className="btn btn-sm"
                                                    disabled={isCurrent}
                                                    style={{
                                                        background: isCurrent ? st.bg : 'transparent',
                                                        color: isCurrent ? st.color : 'var(--text)',
                                                        border: `1px solid ${isCurrent ? st.bg : 'var(--border)'}`,
                                                        opacity: isCurrent ? 1 : 0.8,
                                                        textTransform: 'capitalize',
                                                    }}
                                                    onClick={() => handleStatusChange(viewMsg.id, s)}
                                                >
                                                    {s}
                                                </button>
                                            );
                                        })}
                                    </div>
                                </div>
                                <div className="flex justify-end gap-3" style={{ marginTop: '1rem' }}>
                                    <button className="btn" style={{ color: 'var(--danger)' }} onClick={() => { handleDelete(viewMsg.id); setViewMsg(null); }}>
                                        <Trash2 size={15} /> Delete
                                    </button>
                                    {viewSent && (
                                        <button className="btn" style={{ color: 'var(--primary)' }} onClick={() => {
                                            setForm({
                                                subject: viewMsg.subject || '',
                                                content: viewMsg.content || '',
                                                priority: viewMsg.priority || 'normal',
                                                category_id: viewMsg.category_id ? String(viewMsg.category_id) : '',
                                                target_hub_id: viewMsg.target_hub_id ? String(viewMsg.target_hub_id) : '',
                                            });
                                            setViewMsg(null);
                                            setShowCompose(true);
                                        }}>
                                            <RotateCcw size={15} /> Resend
                                        </button>
                                    )}
                                    {!viewSent && viewMsg.status === 'pending' && (
                                        <button
                                            className="btn"
                                            style={{ color: 'var(--success)' }}
                                            disabled={ackSending}
                                            onClick={() => handleSendAck(viewMsg)}
                                        >
                                            <CheckCircle size={15} />
                                            {ackSending ? 'Sending...' : 'Send Acknowledgement'}
                                        </button>
                                    )}
                                    <button className="btn" onClick={() => setViewMsg(null)}>Close</button>
                                </div>
                            </div>
                        </div>
                    </div>
                );
            })()}
        </>
    );
}


// ─── LoRa Monitor Tab ─────────────────────────────────────────────────────

function LoraMonitorTab({ hubs }) {
    const [status, setStatus] = useState(null);
    const [ports, setPorts] = useState([]);
    const [logs, setLogs] = useState([]);
    const [showConnect, setShowConnect] = useState(false);
    const [autoScroll, setAutoScroll] = useState(true);
    const [connecting, setConnecting] = useState(false);
    const [scanning, setScanning] = useState(false);
    const [autoConnect, setAutoConnect] = useState(false);
    const [togglingAutoConnect, setTogglingAutoConnect] = useState(false);

    // Connect form
    const [connForm, setConnForm] = useState({
        port: '', baud: '115200', connection_type: 'serial'
    });

    // Compose LoRa message
    const [showLoraCompose, setShowLoraCompose] = useState(false);
    const [loraForm, setLoraForm] = useState({
        subject: '', content: '', target_hub_id: '', priority: 'normal'
    });
    const [sendingLora, setSendingLora] = useState(false);

    // Encryption state
    const [encStatus, setEncStatus] = useState(null);
    const [encKeyInput, setEncKeyInput] = useState('');
    const [encBusy, setEncBusy] = useState(false);
    const [encRevealedKey, setEncRevealedKey] = useState(null);
    const [encCopied, setEncCopied] = useState(false);

    const terminalRef = useRef(null);
    const bottomRef = useRef(null);
    const wsRef = useRef(null);

    const fetchEncryption = useCallback(async () => {
        try {
            const res = await hubClient.get('/lora/encryption');
            setEncStatus(res.data);
        } catch (e) {
            console.error('Encryption status error', e);
        }
    }, []);

    const fetchStatus = useCallback(async () => {
        try {
            const res = await hubClient.get('/lora/status');
            setStatus(res.data);
            setAutoConnect(!!res.data.auto_connect);
        } catch (e) {
            console.error('LoRa status error', e);
        }
    }, []);

    const fetchPorts = useCallback(async (autoSelect = false) => {
        setScanning(true);
        try {
            const res = await hubClient.get('/lora/ports');
            const found = res.data.ports || [];
            setPorts(found);
            if (autoSelect && found.length > 0) {
                setConnForm(f => ({ ...f, port: f.port || found[0].port }));
            }
        } catch (e) {
            console.error('LoRa ports error', e);
        } finally {
            setScanning(false);
        }
    }, []);

    useEffect(() => {
        fetchStatus();
        fetchEncryption();
        const interval = setInterval(fetchStatus, 5000);
        return () => clearInterval(interval);
    }, [fetchStatus, fetchEncryption]);

    const handleGenerateKey = async () => {
        setEncBusy(true);
        setEncRevealedKey(null);
        try {
            const res = await hubClient.post('/lora/encryption', {});
            if (res.data.ok) {
                setEncRevealedKey(res.data.key);
                setEncCopied(false);
                fetchEncryption();
            } else {
                alert('Failed: ' + (res.data.error || 'Unknown error'));
            }
        } catch {
            alert('Failed to generate encryption key.');
        } finally {
            setEncBusy(false);
        }
    };

    const handleSetKey = async () => {
        if (!encKeyInput.trim()) return;
        setEncBusy(true);
        try {
            const res = await hubClient.post('/lora/encryption', { key: encKeyInput.trim() });
            if (res.data.ok) {
                setEncKeyInput('');
                setEncRevealedKey(null);
                fetchEncryption();
            } else {
                alert('Failed: ' + (res.data.error || 'Unknown error'));
            }
        } catch {
            alert('Failed to set encryption key.');
        } finally {
            setEncBusy(false);
        }
    };

    const handleDisableEncryption = async () => {
        if (!confirm('Disable LoRa encryption? Messages will be sent in plaintext.')) return;
        setEncBusy(true);
        try {
            await hubClient.delete('/lora/encryption');
            setEncRevealedKey(null);
            fetchEncryption();
        } catch {
            alert('Failed to disable encryption.');
        } finally {
            setEncBusy(false);
        }
    };

    const handleCopyKey = () => {
        if (encRevealedKey) {
            navigator.clipboard.writeText(encRevealedKey);
            setEncCopied(true);
            setTimeout(() => setEncCopied(false), 2000);
        }
    };

    // WebSocket for real-time serial monitor
    useEffect(() => {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        let hostUrl = window.location.host;
        if (window.location.port === '5173') {
            hostUrl = window.location.hostname + ':8000';
        }
        const wsUrl = `${protocol}//${hostUrl}/lora/ws/lora`;
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            wsRef.current = ws;
        };

        ws.onmessage = (event) => {
            if (!event.data) return;
            setLogs(prev => {
                const next = [...prev, event.data];
                return next.length > 500 ? next.slice(next.length - 500) : next;
            });
        };

        ws.onclose = () => {
            wsRef.current = null;
        };

        return () => {
            ws.close();
        };
    }, []);

    // Auto-scroll terminal
    useEffect(() => {
        if (autoScroll && bottomRef.current) {
            bottomRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [logs, autoScroll]);

    const handleConnect = async (e) => {
        e.preventDefault();
        setConnecting(true);
        try {
            const res = await hubClient.post('/lora/connect', {
                port: connForm.port,
                baud: parseInt(connForm.baud) || 115200,
                connection_type: connForm.connection_type,
            });
            if (res.data.ok) {
                setShowConnect(false);
                fetchStatus();
            } else {
                alert('Connection failed: ' + (res.data.error || 'Unknown error'));
            }
        } catch (e) {
            alert('Connection failed.');
        } finally {
            setConnecting(false);
        }
    };

    const handleDisconnect = async () => {
        try {
            await hubClient.post('/lora/disconnect');
            fetchStatus();
        } catch (e) {
            alert('Disconnect failed.');
        }
    };

    const handleLoraSend = async (e) => {
        e.preventDefault();
        if (!loraForm.subject.trim() || !loraForm.content.trim()) return;
        setSendingLora(true);
        try {
            const payload = {
                target_hub_id: (loraForm.target_hub_id && loraForm.target_hub_id !== 'broadcast') ? parseInt(loraForm.target_hub_id) : null,
                subject: loraForm.subject,
                content: loraForm.content,
                priority: loraForm.priority,
            };
            const res = await hubClient.post('/lora/send', payload);
            if (res.data.ok) {
                setShowLoraCompose(false);
                setLoraForm({ subject: '', content: '', target_hub_id: '', priority: 'normal' });
                fetchStatus();
            } else {
                alert('Send failed: ' + (res.data.error || 'Unknown error'));
            }
        } catch (e) {
            alert('Send failed.');
        } finally {
            setSendingLora(false);
        }
    };

    const openConnectModal = () => {
        setShowConnect(true);
        fetchPorts(true);
    };

    const handleToggleAutoConnect = async () => {
        setTogglingAutoConnect(true);
        try {
            const newVal = !autoConnect;
            await hubClient.post('/lora/auto-connect', { enabled: newVal });
            setAutoConnect(newVal);
            fetchStatus();
        } catch (e) {
            console.error('Auto-connect toggle error', e);
        } finally {
            setTogglingAutoConnect(false);
        }
    };

    const isConnected = status?.connected;

    const getLineColor = (line) => {
        if (line.includes('[TX]')) return '#42A5F5';
        if (line.includes('[RX]')) return '#66BB6A';
        if (line.includes('[ERR]')) return '#EF5350';
        if (line.includes('[SYS]')) return '#78909C';
        return '#cccccc';
    };

    const txSecurityState = useMemo(() => {
        for (let i = logs.length - 1; i >= 0; i -= 1) {
            const line = logs[i] || '';
            if (!line.includes('[TX]')) continue;
            if (line.includes('"type":"enc"')) return 'encrypted';
            if (line.includes('"type":"msg"')) return 'plaintext';
        }
        return 'unknown';
    }, [logs]);

    return (
        <div className="space-y-4" style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 14rem)' }}>
            {/* Connection Bar */}
            <div className="card" style={{ padding: '0.75rem 1.25rem', flexShrink: 0 }}>
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <span
                            className="status-dot"
                            style={{ background: isConnected ? 'var(--success)' : 'var(--danger)' }}
                        />
                        <span className="font-semibold text-sm">
                            {isConnected ? 'Connected' : 'Disconnected'}
                        </span>

                        {isConnected && status.connection_type && (
                            <span className="badge" style={{
                                background: status.connection_type === 'bluetooth' ? '#1565C0' : 'var(--primary)',
                                color: '#fff',
                                fontSize: '0.7rem',
                                gap: '0.25rem',
                                display: 'inline-flex',
                                alignItems: 'center',
                            }}>
                                {status.connection_type === 'bluetooth'
                                    ? <><Bluetooth size={11} /> Bluetooth</>
                                    : <><Usb size={11} /> Serial USB</>
                                }
                            </span>
                        )}

                        {isConnected && status.port && (
                            <span className="font-mono text-sm text-muted">{status.port} @ {status.baud_rate}</span>
                        )}

                        {isConnected && (
                            <div className="flex items-center gap-3 text-xs text-muted" style={{ marginLeft: '0.5rem' }}>
                                <span className="flex items-center gap-1"><ArrowUp size={12} /> {status.messages_sent || 0}</span>
                                <span className="flex items-center gap-1"><ArrowDown size={12} /> {status.messages_received || 0}</span>
                            </div>
                        )}
                    </div>

                    <div className="flex items-center gap-2">
                        {!status?.serial_available && (
                            <span className="text-xs" style={{ color: 'var(--warning)' }}>pyserial not installed</span>
                        )}

                        {/* Auto-connect toggle */}
                        <button
                            onClick={handleToggleAutoConnect}
                            disabled={togglingAutoConnect}
                            title={autoConnect ? 'Auto-connect enabled — click to disable' : 'Enable auto-connect to automatically reconnect'}
                            style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '0.375rem',
                                padding: '0.25rem 0.625rem',
                                borderRadius: '999px',
                                border: `1px solid ${autoConnect ? 'var(--success)' : 'var(--border)'}`,
                                background: autoConnect ? 'rgba(76,175,80,0.12)' : 'transparent',
                                color: autoConnect ? 'var(--success)' : 'var(--text-muted)',
                                fontSize: '0.7rem',
                                fontWeight: 600,
                                cursor: togglingAutoConnect ? 'wait' : 'pointer',
                                transition: 'all 0.2s ease',
                                opacity: togglingAutoConnect ? 0.6 : 1,
                            }}
                        >
                            <span style={{
                                width: 24,
                                height: 14,
                                borderRadius: 7,
                                background: autoConnect ? 'var(--success)' : '#555',
                                position: 'relative',
                                display: 'inline-block',
                                transition: 'background 0.2s ease',
                            }}>
                                <span style={{
                                    position: 'absolute',
                                    top: 2,
                                    left: autoConnect ? 12 : 2,
                                    width: 10,
                                    height: 10,
                                    borderRadius: '50%',
                                    background: '#fff',
                                    transition: 'left 0.2s ease',
                                }} />
                            </span>
                            Auto-connect
                        </button>

                        {isConnected ? (
                            <button className="btn btn-sm" style={{ color: 'var(--danger)' }} onClick={handleDisconnect}>
                                <WifiOff size={14} /> Disconnect
                            </button>
                        ) : (
                            <button className="btn btn-sm btn-primary" onClick={openConnectModal}>
                                <Wifi size={14} /> Connect Device
                            </button>
                        )}
                    </div>
                </div>

                {/* Device info strip */}
                {isConnected && (status.device_info || status.last_activity) && (
                    <div className="flex gap-4 text-xs text-muted" style={{ marginTop: '0.5rem', paddingTop: '0.5rem', borderTop: '1px solid var(--border)' }}>
                        {status.device_info && <span>Firmware: {status.device_info}</span>}
                        {status.last_activity && (
                            <span>Last activity: {new Date(status.last_activity * 1000).toLocaleTimeString()}</span>
                        )}
                    </div>
                )}
            </div>

            {/* Encryption Card */}
            {encStatus && (
                <div className="card" style={{ padding: '0.75rem 1.25rem', flexShrink: 0 }}>
                    <div className="flex items-center justify-between" style={{ marginBottom: encRevealedKey ? '0.75rem' : 0 }}>
                        <div className="flex items-center gap-3">
                            {encStatus.enabled ? (
                                <Lock size={15} style={{ color: 'var(--success)' }} />
                            ) : (
                                <Unlock size={15} style={{ color: 'var(--text-muted)' }} />
                            )}
                            <span className="font-semibold text-sm">
                                Encryption {encStatus.enabled ? 'Enabled' : 'Disabled'}
                            </span>
                            {encStatus.enabled && (
                                <span className="badge" style={{
                                    background: 'rgba(76,175,80,0.12)',
                                    color: 'var(--success)',
                                    fontSize: '0.7rem',
                                    gap: '0.25rem',
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                }}>
                                    <KeyRound size={11} />
                                    AES-256-GCM
                                </span>
                            )}
                            {encStatus.enabled && encStatus.key_preview && (
                                <span className="font-mono text-xs text-muted">{encStatus.key_preview}</span>
                            )}
                        </div>
                        <div className="flex items-center gap-2">
                            {encStatus.enabled ? (
                                <button
                                    className="btn btn-sm"
                                    style={{ color: 'var(--danger)', fontSize: '0.75rem' }}
                                    disabled={encBusy}
                                    onClick={handleDisableEncryption}
                                >
                                    <Unlock size={13} /> Disable
                                </button>
                            ) : null}
                            <button
                                className="btn btn-sm"
                                style={{
                                    background: 'var(--primary)',
                                    color: '#fff',
                                    border: 'none',
                                    fontSize: '0.75rem',
                                }}
                                disabled={encBusy}
                                onClick={handleGenerateKey}
                            >
                                <KeyRound size={13} />
                                {encStatus.enabled ? 'Regenerate Key' : 'Generate Key'}
                            </button>
                        </div>
                    </div>

                    {txSecurityState !== 'unknown' && (
                        <div style={{
                            marginTop: '0.625rem',
                            marginBottom: '0.375rem',
                            padding: '0.5rem 0.75rem',
                            borderRadius: 'var(--radius)',
                            border: txSecurityState === 'encrypted'
                                ? '1px solid rgba(76,175,80,0.35)'
                                : '1px solid rgba(239,83,80,0.45)',
                            background: txSecurityState === 'encrypted'
                                ? 'rgba(76,175,80,0.08)'
                                : 'rgba(239,83,80,0.08)',
                            color: txSecurityState === 'encrypted' ? 'var(--success)' : 'var(--danger)',
                            fontSize: '0.8rem',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                        }}>
                            {txSecurityState === 'encrypted' ? <Lock size={14} /> : <Unlock size={14} />}
                            Last outbound TX detected as <strong>{txSecurityState === 'encrypted' ? 'ENCRYPTED' : 'PLAINTEXT'}</strong>.
                            {txSecurityState === 'plaintext' && encStatus.enabled && (
                                <span style={{ opacity: 0.9 }}>
                                    Encryption is enabled in UI but runtime is still sending plaintext. Restart hub and verify crypto install.
                                </span>
                            )}
                        </div>
                    )}

                    {/* Revealed key after generation */}
                    {encRevealedKey && (
                        <div style={{
                            background: 'rgba(76,175,80,0.08)',
                            border: '1px solid rgba(76,175,80,0.3)',
                            borderRadius: 'var(--radius)',
                            padding: '0.625rem 0.875rem',
                            marginBottom: '0.5rem',
                        }}>
                            <div style={{
                                fontSize: '0.7rem', fontWeight: 600, color: 'var(--success)',
                                textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.375rem',
                            }}>
                                Copy this key to all other hubs
                            </div>
                            <div className="flex items-center gap-2">
                                <code style={{
                                    flex: 1,
                                    fontSize: '0.75rem',
                                    fontFamily: "'Menlo','Consolas',monospace",
                                    background: 'var(--bg-secondary)',
                                    padding: '0.375rem 0.625rem',
                                    borderRadius: '4px',
                                    wordBreak: 'break-all',
                                    userSelect: 'all',
                                }}>
                                    {encRevealedKey}
                                </code>
                                <button
                                    className="btn btn-sm"
                                    onClick={handleCopyKey}
                                    style={{
                                        flexShrink: 0,
                                        background: encCopied ? 'var(--success)' : 'var(--bg-secondary)',
                                        color: encCopied ? '#fff' : 'var(--text)',
                                        border: 'none',
                                    }}
                                >
                                    {encCopied ? <><CheckCircle size={13} /> Copied</> : <><Copy size={13} /> Copy</>}
                                </button>
                            </div>
                        </div>
                    )}

                    {/* Paste key from another hub */}
                    {!encStatus.enabled && !encRevealedKey && (
                        <div className="flex items-center gap-2" style={{ marginTop: '0.625rem' }}>
                            <input
                                className="input"
                                placeholder="Paste encryption key from another hub..."
                                value={encKeyInput}
                                onChange={e => setEncKeyInput(e.target.value)}
                                style={{ flex: 1, fontSize: '0.8rem', fontFamily: "'Menlo','Consolas',monospace" }}
                            />
                            <button
                                className="btn btn-sm btn-primary"
                                disabled={encBusy || !encKeyInput.trim()}
                                onClick={handleSetKey}
                                style={{ flexShrink: 0 }}
                            >
                                <Lock size={13} /> Set Key
                            </button>
                        </div>
                    )}
                </div>
            )}

            {/* Serial Monitor Terminal */}
            <div style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                background: '#0c0c0c',
                borderRadius: '8px',
                overflow: 'hidden',
                border: '1px solid var(--border)',
                minHeight: 0,
            }}>
                {/* Terminal header */}
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '0.5rem 0.75rem',
                    background: '#181818',
                    borderBottom: '1px solid #333',
                    flexShrink: 0,
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <TerminalSquare size={14} color="#78909C" />
                        <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#78909C', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                            Serial Monitor
                        </span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <button
                            onClick={() => setAutoScroll(a => !a)}
                            style={{
                                fontSize: '0.7rem',
                                padding: '2px 8px',
                                borderRadius: 4,
                                border: '1px solid #444',
                                background: autoScroll ? '#1B5E20' : 'transparent',
                                color: autoScroll ? '#A5D6A7' : '#666',
                                cursor: 'pointer',
                                fontFamily: 'inherit',
                            }}
                        >
                            Auto-scroll {autoScroll ? 'ON' : 'OFF'}
                        </button>
                        <button
                            onClick={() => setLogs([])}
                            style={{
                                fontSize: '0.7rem',
                                padding: '2px 8px',
                                borderRadius: 4,
                                border: '1px solid #444',
                                background: 'transparent',
                                color: '#666',
                                cursor: 'pointer',
                                fontFamily: 'inherit',
                            }}
                        >
                            Clear
                        </button>
                    </div>
                </div>

                {/* Terminal output */}
                <div ref={terminalRef} style={{
                    flex: 1,
                    overflowY: 'auto',
                    padding: '0.75rem',
                    fontFamily: "'Menlo', 'Consolas', monospace",
                    fontSize: '0.8125rem',
                    lineHeight: 1.6,
                    color: '#cccccc',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-all',
                }}>
                    {logs.length === 0 && (
                        <div style={{ color: '#555', textAlign: 'center', padding: '2rem' }}>
                            {isConnected
                                ? 'Waiting for data from Relay module...'
                                : 'Connect an Relay device to start monitoring.'
                            }
                        </div>
                    )}
                    {logs.map((line, i) => (
                        <div key={i} style={{ color: getLineColor(line), marginBottom: 1 }}>
                            {line}
                        </div>
                    ))}
                    <div ref={bottomRef} />
                </div>
            </div>

            {/* Send Bar */}
            <div className="card" style={{ padding: '0.625rem 1rem', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div className="flex items-center gap-2 text-sm text-muted">
                    <Radio size={16} style={{ color: isConnected ? 'var(--primary)' : 'var(--text-muted)' }} />
                    {isConnected
                        ? 'Device ready — compose a message to send via LoRa radio'
                        : 'Connect an Relay device to send messages'
                    }
                </div>
                <button
                    className="btn btn-primary btn-sm"
                    disabled={!isConnected}
                    onClick={() => setShowLoraCompose(true)}
                >
                    <Send size={14} /> Compose LoRa Message
                </button>
            </div>

            {/* Compose LoRa Message Modal */}
            {showLoraCompose && (
                <div className="modal-overlay" onClick={() => setShowLoraCompose(false)}>
                    <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '34rem' }}>
                        <div className="modal-header">
                            <div className="flex items-center gap-2">
                                <Radio size={20} style={{ color: 'var(--primary)' }} />
                                <h2 className="modal-title">Compose LoRa Message</h2>
                            </div>
                            <button className="btn-icon" onClick={() => setShowLoraCompose(false)}>
                                <X size={18} />
                            </button>
                        </div>
                        <div className="modal-body">
                            <div style={{
                                background: 'var(--primary-light)',
                                borderRadius: 'var(--radius)',
                                padding: '0.5rem 0.75rem',
                                marginBottom: '1rem',
                                fontSize: '0.8rem',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.5rem',
                                color: 'var(--primary)',
                            }}>
                                <Usb size={14} />
                                Sending via {status?.port || 'Relay'} @ {status?.baud_rate || 115200} baud
                            </div>
                            <form onSubmit={handleLoraSend}>
                                <div className="form-group">
                                    <label>Subject <span style={{ color: 'var(--danger)' }}>*</span></label>
                                    <input
                                        required
                                        className="input"
                                        placeholder="Message subject..."
                                        value={loraForm.subject}
                                        onChange={e => setLoraForm({ ...loraForm, subject: e.target.value })}
                                    />
                                </div>

                                <div className="grid-2" style={{ marginBottom: '1rem' }}>
                                    <div>
                                        <label>Target Device <span style={{ color: 'var(--danger)' }}>*</span></label>
                                        <select
                                            className="input"
                                            value={loraForm.target_hub_id}
                                            onChange={e => setLoraForm({ ...loraForm, target_hub_id: e.target.value })}
                                            required
                                        >
                                            <option value="">— Select target device —</option>
                                            <option value="broadcast">Broadcast (all devices)</option>
                                            {hubs.map(h => (
                                                <option key={h.hub_id} value={h.hub_id}>
                                                    {h.device_id || h.hub_name}
                                                </option>
                                            ))}
                                        </select>
                                    </div>
                                    <div>
                                        <label>Priority <span style={{ color: 'var(--danger)' }}>*</span></label>
                                        <div className="flex gap-3" style={{ marginTop: '0.25rem' }}>
                                            {['normal', 'urgent', 'emergency'].map(p => {
                                                const pri = PRIORITY_COLORS[p];
                                                const selected = loraForm.priority === p;
                                                return (
                                                    <button
                                                        type="button"
                                                        key={p}
                                                        className="btn btn-sm"
                                                        style={{
                                                            background: selected ? pri.bg : 'transparent',
                                                            color: selected ? pri.color : 'var(--text-muted)',
                                                            border: `1px solid ${selected ? pri.bg : 'var(--border)'}`,
                                                            fontWeight: selected ? 600 : 400,
                                                        }}
                                                        onClick={() => setLoraForm({ ...loraForm, priority: p })}
                                                    >
                                                        {pri.label}
                                                    </button>
                                                );
                                            })}
                                        </div>
                                    </div>
                                </div>

                                <div className="form-group">
                                    <label>Content <span style={{ color: 'var(--danger)' }}>*</span></label>
                                    <textarea
                                        required
                                        className="textarea"
                                        placeholder="Write your message..."
                                        rows={5}
                                        value={loraForm.content}
                                        onChange={e => setLoraForm({ ...loraForm, content: e.target.value })}
                                    />
                                </div>

                                <div className="flex justify-end gap-3" style={{ borderTop: '1px solid var(--border)', paddingTop: '1rem' }}>
                                    <button type="button" onClick={() => setShowLoraCompose(false)} className="btn">Cancel</button>
                                    <button
                                        type="submit"
                                        className="btn btn-primary"
                                        disabled={sendingLora || !loraForm.subject.trim() || !loraForm.content.trim()}
                                    >
                                        <Radio size={16} />
                                        {sendingLora ? 'Sending via LoRa...' : 'Send via LoRa'}
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            )}

            {/* Connect Modal */}
            {showConnect && (
                <div className="modal-overlay" onClick={() => setShowConnect(false)}>
                    <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '28rem' }}>
                        <div className="modal-header">
                            <div className="flex items-center gap-2">
                                <Wifi size={20} style={{ color: 'var(--primary)' }} />
                                <h2 className="modal-title">Connect Relay Device</h2>
                            </div>
                            <button className="btn-icon" onClick={() => setShowConnect(false)}>
                                <X size={18} />
                            </button>
                        </div>
                        <div className="modal-body">
                            <form onSubmit={handleConnect}>
                                <div className="form-group">
                                    <label>Connection Type</label>
                                    <div className="flex gap-3">
                                        {[
                                            { val: 'serial', label: 'Serial USB', icon: Usb },
                                            { val: 'bluetooth', label: 'Bluetooth', icon: Bluetooth },
                                        ].map(({ val, label, icon: Icon }) => {
                                            const sel = connForm.connection_type === val;
                                            return (
                                                <button
                                                    key={val}
                                                    type="button"
                                                    className="btn btn-sm"
                                                    style={{
                                                        background: sel ? 'var(--primary)' : 'transparent',
                                                        color: sel ? '#fff' : 'var(--text-muted)',
                                                        border: `1px solid ${sel ? 'var(--primary)' : 'var(--border)'}`,
                                                        fontWeight: sel ? 600 : 400,
                                                    }}
                                                    onClick={() => {
                                                        setConnForm({ ...connForm, connection_type: val, port: '' });
                                                        fetchPorts(true);
                                                    }}
                                                >
                                                    <Icon size={14} /> {label}
                                                </button>
                                            );
                                        })}
                                    </div>
                                </div>

                                <div className="form-group">
                                    <div className="flex items-center justify-between">
                                        <label>
                                            {connForm.connection_type === 'bluetooth' ? 'Bluetooth Address / Port' : 'Serial Port'}
                                        </label>
                                        <button
                                            type="button"
                                            className="btn btn-sm"
                                            style={{ padding: '2px 8px', fontSize: '0.75rem' }}
                                            onClick={() => fetchPorts(true)}
                                            disabled={scanning}
                                        >
                                            <RefreshCw size={12} className={scanning ? 'spin' : ''} />
                                            {scanning ? 'Scanning...' : 'Scan'}
                                        </button>
                                    </div>

                                    {scanning && ports.length === 0 ? (
                                        <div className="input" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-muted)' }}>
                                            <RefreshCw size={14} className="spin" />
                                            Detecting devices...
                                        </div>
                                    ) : ports.length > 0 ? (
                                        <>
                                            <select
                                                className="input"
                                                value={connForm.port}
                                                onChange={e => setConnForm({ ...connForm, port: e.target.value })}
                                                required
                                            >
                                                <option value="">— Select port —</option>
                                                {ports.map(p => (
                                                    <option key={p.port} value={p.port}>
                                                        {p.port} — {p.description}
                                                    </option>
                                                ))}
                                            </select>
                                            <p className="form-hint" style={{ color: 'var(--success)' }}>
                                                {ports.length} device(s) found
                                            </p>
                                        </>
                                    ) : (
                                        <>
                                            <input
                                                className="input"
                                                placeholder={connForm.connection_type === 'bluetooth' ? 'e.g. 00:11:22:33:44:55' : 'e.g. COM3 or /dev/ttyUSB0'}
                                                value={connForm.port}
                                                onChange={e => setConnForm({ ...connForm, port: e.target.value })}
                                                required
                                            />
                                            <p className="form-hint">No ports detected. Plug in your Relay device and click Scan, or enter manually.</p>
                                        </>
                                    )}
                                </div>

                                <div className="form-group">
                                    <label>Baud Rate</label>
                                    <select
                                        className="input"
                                        value={connForm.baud}
                                        onChange={e => setConnForm({ ...connForm, baud: e.target.value })}
                                    >
                                        {['9600', '19200', '38400', '57600', '115200', '230400', '460800', '921600'].map(b => (
                                            <option key={b} value={b}>{b}</option>
                                        ))}
                                    </select>
                                </div>

                                <div className="flex justify-end gap-3" style={{ borderTop: '1px solid var(--border)', paddingTop: '1rem' }}>
                                    <button type="button" onClick={() => setShowConnect(false)} className="btn">Cancel</button>
                                    <button type="submit" className="btn btn-primary" disabled={connecting || !connForm.port}>
                                        <Wifi size={16} />
                                        {connecting ? 'Connecting...' : 'Connect'}
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}


// ─── Main HubMessages (tabbed container) ──────────────────────────────────

function HubMessages() {
    const [tab, setTab] = useState('messages');
    const [messages, setMessages] = useState([]);
    const [categories, setCategories] = useState([]);
    const [hubs, setHubs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [loraConnected, setLoraConnected] = useState(false);
    const [newMsgFlash, setNewMsgFlash] = useState(false);
    const [incomingMsg, setIncomingMsg] = useState(null);
    const [thisHubId, setThisHubId] = useState(null);
    const [noUsbAlert, setNoUsbAlert] = useState(null);

    const loadAll = useCallback(async () => {
        try {
            const [msgRes, catRes, hubRes] = await Promise.all([
                hubClient.get('/messages'),
                hubClient.get('/messages/categories'),
                hubClient.get('/messages/hubs'),
            ]);
            setMessages(msgRes.data.messages || []);
            setCategories(catRes.data.categories || []);
            setHubs(hubRes.data.hubs || []);
            if (msgRes.data.this_hub_id != null) {
                setThisHubId(msgRes.data.this_hub_id);
            }
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadAll();
        window.__hubMessagesReload = loadAll;
        return () => { delete window.__hubMessagesReload; };
    }, [loadAll]);

    // Real-time: subscribe to LoRa WS for instant new-message push
    useEffect(() => {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        let hostUrl = window.location.host;
        if (window.location.port === '5173') {
            hostUrl = window.location.hostname + ':8000';
        }
        const wsUrl = `${protocol}//${hostUrl}/lora/ws/lora`;

        let ws;
        let reconnectTimer;

        function connect() {
            ws = new WebSocket(wsUrl);

            ws.onmessage = (event) => {
                if (!event.data) return;
                try {
                    const data = JSON.parse(event.data);
                    if (data.event === 'new_message') {
                        loadAll();
                        setNewMsgFlash(true);
                        setTimeout(() => setNewMsgFlash(false), 2000);

                        setIncomingMsg({
                            id: data.id,
                            subject: data.subject,
                            content: data.content,
                            priority: data.priority || 'normal',
                            source_hub_id: data.source_hub_id,
                            source_hub_name: data.source_hub_name,
                            from_device_id: data.from_device_id,
                        });
                    } else if (data.event === 'message_delivered') {
                        // ACK received — refresh message list to show updated status
                        loadAll();
                    } else if (data.event === 'no_usb_device') {
                        setNoUsbAlert(data.message || 'No USB serial device detected. Please plug in your Relay module.');
                    }
                } catch (_) {
                    // plain log line, ignore in this listener
                }
            };

            ws.onclose = () => {
                reconnectTimer = setTimeout(connect, 5000);
            };
        }

        connect();

        return () => {
            clearTimeout(reconnectTimer);
            if (ws) ws.close();
        };
    }, [loadAll]);

    useEffect(() => {
        const check = async () => {
            try {
                const res = await hubClient.get('/lora/status');
                setLoraConnected(res.data.connected);
                if (res.data.connected) setNoUsbAlert(null);
            } catch (_) { }
        };
        check();
        const interval = setInterval(check, 8000);
        return () => clearInterval(interval);
    }, []);

    const tabStyle = (t) => ({
        padding: '0.5rem 1.25rem',
        borderRadius: '6px 6px 0 0',
        border: '1px solid var(--border)',
        borderBottom: tab === t ? '2px solid var(--primary)' : '1px solid var(--border)',
        background: tab === t ? 'var(--surface)' : 'transparent',
        color: tab === t ? 'var(--primary)' : 'var(--text-muted)',
        fontWeight: tab === t ? 600 : 400,
        fontSize: '0.875rem',
        cursor: 'pointer',
        fontFamily: 'inherit',
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.5rem',
        marginBottom: '-1px',
        position: 'relative',
    });

    const handleViewIncomingDetail = useCallback((msg) => {
        setTab('messages');
        setNewMsgFlash(false);
        const fullMsg = messages.find(m => m.id === msg.id);
        if (fullMsg) {
            window.__hubMessagesViewMsg?.(fullMsg);
        }
    }, [messages]);

    const thisHub = hubs.find(h => h.hub_id === thisHubId);
    const thisHubDeviceId = thisHub?.device_id || thisHub?.hub_name;

    return (
        <div className="space-y-4">
            <h1 className="page-title">Hub Messages</h1>

            {/* No USB device alert */}
            {noUsbAlert && !loraConnected && (
                <div style={{
                    background: 'rgba(239, 83, 80, 0.08)',
                    border: '1px solid rgba(239, 83, 80, 0.35)',
                    borderRadius: 'var(--radius)',
                    padding: '0.625rem 1rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.625rem',
                    fontSize: '0.8125rem',
                    color: 'var(--danger)',
                    animation: 'fadeIn 0.15s ease',
                }}>
                    <AlertTriangle size={16} style={{ flexShrink: 0 }} />
                    <span style={{ flex: 1 }}>{noUsbAlert}</span>
                    <button
                        className="btn btn-sm"
                        style={{ color: 'var(--danger)', border: '1px solid var(--danger)', background: 'transparent', flexShrink: 0 }}
                        onClick={() => setNoUsbAlert(null)}
                    >
                        <X size={14} /> Dismiss
                    </button>
                </div>
            )}

            {/* Incoming LoRa message modal */}
            <IncomingLoraModal
                message={incomingMsg}
                onClose={() => setIncomingMsg(null)}
                onViewDetails={handleViewIncomingDetail}
                thisHubDeviceId={thisHubDeviceId}
            />

            {/* Tabs */}
            <div style={{ borderBottom: '1px solid var(--border)', display: 'flex', gap: '0.25rem' }}>
                <button style={tabStyle('messages')} onClick={() => { setTab('messages'); setNewMsgFlash(false); }}>
                    <MessageSquare size={16} /> Messages
                    {newMsgFlash && tab !== 'messages' && (
                        <span style={{
                            width: 8, height: 8, borderRadius: '50%',
                            background: 'var(--danger)',
                            display: 'inline-block',
                            marginLeft: 4,
                            animation: 'pulse 1s ease-in-out infinite',
                        }} />
                    )}
                </button>
                <button style={tabStyle('lora')} onClick={() => setTab('lora')}>
                    <Radio size={16} />
                    LoRa Monitor
                    <span
                        className="status-dot"
                        style={{
                            width: 7,
                            height: 7,
                            borderRadius: '50%',
                            background: loraConnected ? 'var(--success)' : 'var(--text-muted)',
                            display: 'inline-block',
                            marginLeft: 2,
                        }}
                    />
                </button>
            </div>

            {/* New LoRa message toast */}
            {newMsgFlash && tab === 'messages' && (
                <div style={{
                    background: 'var(--success-light)',
                    border: '1px solid var(--success)',
                    borderRadius: 'var(--radius)',
                    padding: '0.5rem 1rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    fontSize: '0.8125rem',
                    fontWeight: 500,
                    color: 'var(--success)',
                    animation: 'fadeIn 0.15s ease',
                }}>
                    <Radio size={14} />
                    New LoRa message received
                </div>
            )}

            {/* Tab content */}
            {tab === 'messages' && (
                <MessagesTab
                    messages={messages}
                    categories={categories}
                    hubs={hubs}
                    loading={loading}
                    loraConnected={loraConnected}
                    thisHubId={thisHubId}
                />
            )}
            {tab === 'lora' && (
                <LoraMonitorTab hubs={hubs} />
            )}
        </div>
    );
}

export default HubMessages;
