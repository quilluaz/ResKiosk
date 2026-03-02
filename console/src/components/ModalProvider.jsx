import React, { createContext, useContext, useState, useRef, useEffect } from 'react';
import { X, Check, AlertTriangle, AlertCircle, HelpCircle, Info } from 'lucide-react';

const ModalContext = createContext(null);

export const useModal = () => {
    const context = useContext(ModalContext);
    if (!context) {
        throw new Error('useModal must be used within a ModalProvider');
    }
    return context;
};

export const ModalProvider = ({ children }) => {
    const [modalState, setModalState] = useState({
        isOpen: false,
        type: 'alert', // 'alert', 'confirm', 'prompt'
        title: '',
        message: '',
        defaultValue: '',
        placeholder: '',
    });

    const [inputValue, setInputValue] = useState('');
    const inputRef = useRef(null);

    // Promise resolvers
    const resolveRef = useRef(null);

    const openModal = (type, message, title, options = {}) => {
        return new Promise((resolve) => {
            resolveRef.current = resolve;
            setInputValue(options.defaultValue || '');
            setModalState({
                isOpen: true,
                type,
                message,
                title: title || (type === 'alert' ? 'Alert' : type === 'confirm' ? 'Confirm' : 'Input Required'),
                defaultValue: options.defaultValue || '',
                placeholder: options.placeholder || '',
            });
        });
    };

    const alert = (message, title = 'Alert') => openModal('alert', message, title);
    const confirm = (message, title = 'Confirm') => openModal('confirm', message, title);
    const prompt = (message, defaultValue = '', title = 'Prompt', placeholder = '') => 
        openModal('prompt', message, title, { defaultValue, placeholder });

    const handleConfirm = () => {
        setModalState((prev) => ({ ...prev, isOpen: false }));
        if (resolveRef.current) {
            if (modalState.type === 'prompt') {
                resolveRef.current(inputValue);
            } else {
                resolveRef.current(true);
            }
            resolveRef.current = null;
        }
    };

    const handleCancel = () => {
        setModalState((prev) => ({ ...prev, isOpen: false }));
        if (resolveRef.current) {
            if (modalState.type === 'prompt') {
                resolveRef.current(null);
            } else {
                resolveRef.current(false);
            }
            resolveRef.current = null;
        }
    };

    // Handle Enter key for submit and Escape for cancel
    useEffect(() => {
        const handleKeyDown = (e) => {
            if (!modalState.isOpen) return;
            if (e.key === 'Enter') {
                e.preventDefault();
                handleConfirm();
            } else if (e.key === 'Escape') {
                e.preventDefault();
                handleCancel();
            }
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [modalState.isOpen, inputValue]); // Including inputValue so handleConfirm sees the latest state

    useEffect(() => {
        if (modalState.isOpen && modalState.type === 'prompt' && inputRef.current) {
            // Slight delay to allow render animation to finish before focusing
            setTimeout(() => inputRef.current?.focus(), 50);
        }
    }, [modalState.isOpen, modalState.type]);

    const getIcon = () => {
        switch (modalState.type) {
            case 'alert': return <AlertCircle size={20} style={{ color: 'var(--danger, #ef5350)' }} />;
            case 'confirm': return <HelpCircle size={20} style={{ color: 'var(--warning, #ffa726)' }} />;
            case 'prompt': return <Info size={20} style={{ color: 'var(--primary, #42a5f5)' }} />;
            default: return <Info size={20} />;
        }
    };

    const getThemeColor = () => {
        switch (modalState.type) {
            case 'alert': return 'var(--danger, #ef5350)';
            case 'confirm': return 'var(--warning, #ffa726)';
            case 'prompt': return 'var(--primary, #42a5f5)';
            default: return 'var(--primary, #42a5f5)';
        }
    };

    return (
        <ModalContext.Provider value={{ alert, confirm, prompt }}>
            {children}
            {modalState.isOpen && (
                <div style={{
                    position: 'fixed',
                    inset: 0,
                    zIndex: 99999,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: 'var(--modal-overlay)',
                    backdropFilter: 'blur(4px)',
                    animation: 'fadeIn 0.2s ease-out',
                }}>
                    <div style={{
                        background: 'var(--modal-bg)',
                        backdropFilter: 'blur(32px)',
                        WebkitBackdropFilter: 'blur(32px)',
                        borderRadius: '16px',
                        border: `1px solid ${getThemeColor()}50`,
                        boxShadow: `0 20px 60px rgba(0,0,0,0.5), 0 0 40px ${getThemeColor()}20`,
                        maxWidth: '28rem',
                        width: '90%',
                        overflow: 'hidden',
                        animation: 'slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
                    }}>
                        {/* Header */}
                        <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            padding: '1rem 1.25rem',
                            borderBottom: '1px solid var(--border, #333)',
                            background: `${getThemeColor()}15`,
                        }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
                                <div style={{
                                    width: 34, height: 34, borderRadius: '50%',
                                    background: `${getThemeColor()}20`,
                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                }}>
                                    {getIcon()}
                                </div>
                                <h2 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 600, color: getThemeColor() }}>
                                    {modalState.title}
                                </h2>
                            </div>
                            {modalState.type !== 'alert' && (
                                <button
                                    onClick={handleCancel}
                                    style={{
                                        background: 'transparent', border: 'none', cursor: 'pointer',
                                        padding: '0.25rem', borderRadius: '6px', color: 'var(--text-muted, #999)',
                                    }}
                                >
                                    <X size={18} />
                                </button>
                            )}
                        </div>

                        {/* Body */}
                        <div style={{ padding: '1.5rem 1.25rem' }}>
                            <div style={{
                                fontSize: '0.95rem',
                                lineHeight: 1.5,
                                color: 'var(--text, #e0e0e0)',
                                marginBottom: modalState.type === 'prompt' ? '1rem' : '1.5rem',
                                wordBreak: 'break-word',
                            }}>
                                {modalState.message}
                            </div>

                            {modalState.type === 'prompt' && (
                                <div style={{ marginBottom: '1.5rem' }}>
                                    <input
                                        ref={inputRef}
                                        type="text"
                                        value={inputValue}
                                        onChange={(e) => setInputValue(e.target.value)}
                                        placeholder={modalState.placeholder}
                                        style={{
                                            width: '100%',
                                            padding: '0.75rem 1rem',
                                            borderRadius: '8px',
                                            border: '1px solid var(--border, #444)',
                                            background: 'var(--surface)',
                                            color: 'var(--text-main)',
                                            fontSize: '0.95rem',
                                            outline: 'none',
                                            transition: 'border-color 0.2s, box-shadow 0.2s',
                                        }}
                                        onFocus={(e) => {
                                            e.target.style.borderColor = getThemeColor();
                                            e.target.style.boxShadow = `0 0 0 2px ${getThemeColor()}30`;
                                        }}
                                        onBlur={(e) => {
                                            e.target.style.borderColor = 'var(--border, #444)';
                                            e.target.style.boxShadow = 'none';
                                        }}
                                    />
                                </div>
                            )}

                            {/* Actions */}
                            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
                                {modalState.type !== 'alert' && (
                                    <button
                                        onClick={handleCancel}
                                        style={{
                                            padding: '0.5rem 1rem', borderRadius: '8px',
                                            border: '1px solid var(--border, #444)',
                                            background: 'transparent', color: 'var(--text, #e0e0e0)',
                                            cursor: 'pointer', fontSize: '0.9rem', fontWeight: 500,
                                            transition: 'background 0.2s',
                                        }}
                                        onMouseEnter={e => e.target.style.background = 'rgba(255,255,255,0.05)'}
                                        onMouseLeave={e => e.target.style.background = 'transparent'}
                                    >
                                        Cancel
                                    </button>
                                )}
                                <button
                                    onClick={handleConfirm}
                                    style={{
                                        padding: '0.5rem 1.25rem', borderRadius: '8px',
                                        border: 'none',
                                        background: getThemeColor(), color: '#fff',
                                        cursor: 'pointer', fontSize: '0.9rem', fontWeight: 600,
                                        display: 'flex', alignItems: 'center', gap: '0.375rem',
                                        transition: 'filter 0.2s',
                                    }}
                                    onMouseEnter={e => e.target.style.filter = 'brightness(1.1)'}
                                    onMouseLeave={e => e.target.style.filter = 'brightness(1)'}
                                >
                                    {modalState.type === 'alert' ? 'OK' : 'Confirm'}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </ModalContext.Provider>
    );
};
