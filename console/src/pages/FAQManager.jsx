import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import hubClient from '../api/hubClient';
import { Save, ArrowLeft, Upload, FileJson, X, CheckCircle, AlertCircle, Loader } from 'lucide-react';
import { useModal } from '../components/ModalProvider';

function FAQManager({ isNew }) {
    const modal = useModal();
    const navigate = useNavigate();
    const { id } = useParams();
    const [formData, setFormData] = useState({
        question: '', answer: '', category: 'General', tags: [], enabled: true, status: 'draft'
    });
    const [loading, setLoading] = useState(false);
    const [isEvacSync, setIsEvacSync] = useState(false);

    // Upload modal state
    const [showUploadModal, setShowUploadModal] = useState(false);
    const [uploadState, setUploadState] = useState('idle');  // idle | parsing | uploading | success | error
    const [dragOver, setDragOver] = useState(false);
    const [parsedArticles, setParsedArticles] = useState(null);
    const [uploadResult, setUploadResult] = useState(null);
    const [uploadError, setUploadError] = useState('');
    const fileInputRef = useRef(null);

    useEffect(() => {
        if (!isNew && id) {
            loadArticle();
        }
    }, [id, isNew]);

    const loadArticle = async () => {
        try {
            const res = await hubClient.get('/kb/snapshot');
            const found = res.data.articles.find(a => a.id === parseInt(id));
            if (found) {
                setFormData({
                    question: found.question,
                    answer: found.answer,
                    category: found.category,
                    tags: found.tags || [],
                    enabled: found.enabled,
                    status: found.status || 'draft'
                });
                setIsEvacSync(found.source === 'evac_sync');
            }
        } catch (e) {
            console.error(e);
            await modal.alert("Could not load article");
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            if (isNew) {
                await hubClient.post('/admin/article', formData);
            } else {
                await hubClient.put(`/admin/article/${id}`, formData);
            }
            navigate('/kb');
        } catch (e) {
            await modal.alert("Save failed");
        } finally {
            setLoading(false);
        }
    };

    // ─── Upload Modal Logic ─────────────────────────────────────────────

    const resetModal = () => {
        setUploadState('idle');
        setParsedArticles(null);
        setUploadResult(null);
        setUploadError('');
        setDragOver(false);
        if (fileInputRef.current) fileInputRef.current.value = '';
    };

    const openModal = () => {
        resetModal();
        setShowUploadModal(true);
    };

    const closeModal = () => {
        setShowUploadModal(false);
        resetModal();
    };

    const processFile = (file) => {
        if (!file) return;

        if (!file.name.toLowerCase().endsWith('.json')) {
            setUploadError('Only .json files are accepted.');
            setUploadState('error');
            return;
        }

        if (file.size > 10 * 1024 * 1024) {
            setUploadError('File too large (max 10 MB).');
            setUploadState('error');
            return;
        }

        setUploadState('parsing');
        setUploadError('');

        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const parsed = JSON.parse(e.target.result);

                // Accept a raw array or { articles: [...] }
                let articles;
                if (Array.isArray(parsed)) {
                    articles = parsed;
                } else if (parsed.articles && Array.isArray(parsed.articles)) {
                    articles = parsed.articles;
                } else {
                    setUploadError('JSON must be an array of articles or an object with an "articles" key.');
                    setUploadState('error');
                    return;
                }

                if (articles.length === 0) {
                    setUploadError('The JSON file contains no articles.');
                    setUploadState('error');
                    return;
                }

                // Validate each has question & answer
                const invalid = articles.filter(a => !a.question || !a.answer);
                if (invalid.length > 0) {
                    setUploadError(`${invalid.length} article(s) are missing a question or answer.`);
                    setUploadState('error');
                    return;
                }

                setParsedArticles(articles);
                setUploadState('idle');
            } catch (err) {
                setUploadError(`Invalid JSON: ${err.message}`);
                setUploadState('error');
            }
        };
        reader.onerror = () => {
            setUploadError('Failed to read file.');
            setUploadState('error');
        };
        reader.readAsText(file);
    };

    const handleFilePick = (e) => {
        const file = e.target.files?.[0];
        if (file) processFile(file);
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragOver(false);
        const file = e.dataTransfer.files?.[0];
        if (file) processFile(file);
    };

    const handleDragOver = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragOver(true);
    };

    const handleDragLeave = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragOver(false);
    };

    const handleImport = async () => {
        if (!parsedArticles || parsedArticles.length === 0) return;
        setUploadState('uploading');
        setUploadError('');

        try {
            const res = await hubClient.post('/admin/import', { articles: parsedArticles }, { timeout: 60000 });
            setUploadResult(res.data);
            setUploadState('success');
        } catch (err) {
            const detail = err.response?.data?.detail || err.message || 'Upload failed.';
            setUploadError(typeof detail === 'string' ? detail : JSON.stringify(detail));
            setUploadState('error');
        }
    };

    // ─── Render ─────────────────────────────────────────────────────────

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-3">
                <button onClick={() => navigate('/kb')} className="btn btn-sm">
                    <ArrowLeft size={16} />
                </button>
                <h1 className="page-title">{isNew ? 'New Article' : (isEvacSync ? 'View Article (Read Only)' : 'Edit Article')}</h1>

                {isNew && (
                    <button
                        onClick={openModal}
                        className="btn"
                        style={{ marginLeft: 'auto' }}
                    >
                        <Upload size={16} />
                        Upload JSON
                    </button>
                )}
            </div>

            <div className="card" style={{ maxWidth: '42rem' }}>
                {isEvacSync && (
                    <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: '0.5rem', padding: '0.75rem 1rem', marginBottom: '1rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                        This article is auto-generated from <strong>Shelter Config</strong>. To edit it, go to the Shelter Config page.
                    </div>
                )}
                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label>Question / Title</label>
                        <input
                            required
                            className="input"
                            placeholder="e.g. Where can I get food?"
                            value={formData.question}
                            onChange={e => setFormData({ ...formData, question: e.target.value })}
                            disabled={isEvacSync}
                        />
                    </div>

                    <div className="form-group">
                        <label>Answer / Body</label>
                        <textarea
                            required
                            className="textarea"
                            placeholder="Provide a clear, helpful answer..."
                            value={formData.answer}
                            onChange={e => setFormData({ ...formData, answer: e.target.value })}
                            disabled={isEvacSync}
                        />
                    </div>

                    <div className="grid-2" style={{ marginBottom: '1rem' }}>
                        <div>
                            <label>Category</label>
                            <input
                                className="input"
                                placeholder="e.g. Food, Medical, Safety"
                                value={formData.category}
                                onChange={e => setFormData({ ...formData, category: e.target.value })}
                                disabled={isEvacSync}
                            />
                        </div>
                        <div>
                            <label>Tags (comma sep)</label>
                            <input
                                className="input"
                                placeholder="e.g. meals, schedule"
                                value={formData.tags.join(', ')}
                                onChange={e => setFormData({ ...formData, tags: e.target.value.split(',').map(s => s.trim()) })}
                                disabled={isEvacSync}
                            />
                        </div>
                    </div>

                    <div className="grid-2" style={{ marginBottom: '1.5rem' }}>
                        <div>
                            <label>Status</label>
                            <select
                                className="input"
                                value={formData.status}
                                onChange={e => setFormData({ ...formData, status: e.target.value })}
                                disabled={isEvacSync}
                            >
                                <option value="draft">Draft</option>
                                <option value="published">Published</option>
                            </select>
                        </div>
                        <div className="checkbox-row" style={{ marginBottom: 0, alignItems: 'center' }}>
                            <input
                                type="checkbox"
                                checked={formData.enabled}
                                onChange={e => setFormData({ ...formData, enabled: e.target.checked })}
                                id="enabled"
                                disabled={isEvacSync}
                            />
                            <label htmlFor="enabled">Enabled</label>
                        </div>
                    </div>

                    <div className="flex justify-end gap-3" style={{ borderTop: '1px solid var(--border)', paddingTop: '1rem' }}>
                        <button type="button" onClick={() => navigate('/kb')} className="btn">{isEvacSync ? 'Back' : 'Cancel'}</button>
                        {!isEvacSync && (
                            <button type="submit" className="btn btn-primary" disabled={loading}>
                                <Save size={16} />
                                {loading ? 'Saving...' : 'Save & Publish'}
                            </button>
                        )}
                    </div>
                </form>
            </div>

            {/* ─── Upload JSON Modal ─── */}
            {showUploadModal && (
                <div className="modal-overlay" onClick={closeModal}>
                    <div className="modal-content" onClick={e => e.stopPropagation()}>
                        {/* Header */}
                        <div className="modal-header">
                            <div className="flex items-center gap-2">
                                <FileJson size={20} style={{ color: 'var(--primary)' }} />
                                <h2 className="modal-title">Import Articles from JSON</h2>
                            </div>
                            <button className="btn-icon" onClick={closeModal}>
                                <X size={18} />
                            </button>
                        </div>

                        {/* Body */}
                        <div className="modal-body">

                            {/* Success State */}
                            {uploadState === 'success' && uploadResult && (
                                <div className="upload-result-container">
                                    <div className="upload-result-icon success">
                                        <CheckCircle size={48} />
                                    </div>
                                    <h3>Import Complete</h3>
                                    <p className="text-muted text-sm">
                                        {uploadResult.imported} of {uploadResult.total_in_payload} articles imported successfully.
                                        {uploadResult.skipped > 0 && ` ${uploadResult.skipped} skipped.`}
                                    </p>
                                    {uploadResult.errors && uploadResult.errors.length > 0 && (
                                        <div className="upload-errors">
                                            {uploadResult.errors.map((err, i) => (
                                                <div key={i} className="upload-error-line">
                                                    <AlertCircle size={14} />
                                                    <span>{err}</span>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                    <div className="flex gap-3 mt-4" style={{ justifyContent: 'center' }}>
                                        <button onClick={() => { closeModal(); navigate('/kb'); }} className="btn btn-primary">
                                            View Knowledge Base
                                        </button>
                                        <button onClick={resetModal} className="btn">
                                            Import More
                                        </button>
                                    </div>
                                </div>
                            )}

                            {/* Error State */}
                            {uploadState === 'error' && (
                                <div className="upload-result-container">
                                    <div className="upload-result-icon error">
                                        <AlertCircle size={48} />
                                    </div>
                                    <h3>Something went wrong</h3>
                                    <p className="text-muted text-sm">{uploadError}</p>
                                    <button onClick={resetModal} className="btn mt-4">
                                        Try Again
                                    </button>
                                </div>
                            )}

                            {/* Uploading State */}
                            {uploadState === 'uploading' && (
                                <div className="upload-result-container">
                                    <div className="upload-result-icon uploading">
                                        <Loader size={48} className="spin" />
                                    </div>
                                    <h3>Importing {parsedArticles?.length} articles...</h3>
                                    <p className="text-muted text-sm">Embedding and saving to the knowledge base. This may take a moment.</p>
                                </div>
                            )}

                            {/* Parsing State */}
                            {uploadState === 'parsing' && (
                                <div className="upload-result-container">
                                    <div className="upload-result-icon uploading">
                                        <Loader size={48} className="spin" />
                                    </div>
                                    <h3>Reading file...</h3>
                                </div>
                            )}

                            {/* Idle / File Selection State */}
                            {uploadState === 'idle' && !parsedArticles && (
                                <>
                                    <div
                                        className={`drop-zone ${dragOver ? 'drag-over' : ''}`}
                                        onDrop={handleDrop}
                                        onDragOver={handleDragOver}
                                        onDragLeave={handleDragLeave}
                                        onClick={() => fileInputRef.current?.click()}
                                    >
                                        <Upload size={32} style={{ color: dragOver ? 'var(--primary)' : 'var(--text-muted)' }} />
                                        <p className="drop-zone-title">
                                            {dragOver ? 'Drop your file here' : 'Drag & drop a JSON file here'}
                                        </p>
                                        <p className="drop-zone-hint">or click to browse</p>
                                        <input
                                            ref={fileInputRef}
                                            type="file"
                                            accept=".json,application/json"
                                            onChange={handleFilePick}
                                            style={{ display: 'none' }}
                                        />
                                    </div>

                                    <div className="upload-format-hint">
                                        <p className="font-semibold text-sm" style={{ marginBottom: '0.25rem' }}>Expected format:</p>
                                        <pre className="format-preview">{`[
  {
    "question": "Where do I get food?",
    "answer": "Meals are served at...",
    "category": "Food",
    "tags": ["meals", "food"],
    "status": "published",
    "enabled": true
  },
  ...
]`}</pre>
                                    </div>
                                </>
                            )}

                            {/* Preview State — file parsed, ready to import */}
                            {uploadState === 'idle' && parsedArticles && (
                                <div className="upload-preview">
                                    <div className="upload-preview-header">
                                        <div className="flex items-center gap-2">
                                            <CheckCircle size={18} style={{ color: 'var(--success)' }} />
                                            <span className="font-semibold">{parsedArticles.length} articles ready to import</span>
                                        </div>
                                        <button onClick={resetModal} className="btn btn-sm">
                                            Change File
                                        </button>
                                    </div>

                                    <div className="upload-preview-list">
                                        {parsedArticles.slice(0, 8).map((art, i) => (
                                            <div key={i} className="upload-preview-item">
                                                <span className="upload-preview-num">{i + 1}</span>
                                                <div>
                                                    <div className="font-medium text-sm">{art.question}</div>
                                                    <div className="text-xs text-muted">{art.category || 'General'} · {(art.tags || []).length} tags</div>
                                                </div>
                                            </div>
                                        ))}
                                        {parsedArticles.length > 8 && (
                                            <div className="text-muted text-xs text-center" style={{ padding: '0.5rem' }}>
                                                ... and {parsedArticles.length - 8} more
                                            </div>
                                        )}
                                    </div>

                                    <div className="flex gap-3 mt-4" style={{ justifyContent: 'flex-end' }}>
                                        <button onClick={closeModal} className="btn">Cancel</button>
                                        <button onClick={handleImport} className="btn btn-primary">
                                            <Upload size={16} />
                                            Import {parsedArticles.length} Articles
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default FAQManager;
