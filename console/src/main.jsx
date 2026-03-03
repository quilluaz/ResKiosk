import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import { HashRouter } from 'react-router-dom'
import { ModalProvider } from './components/ModalProvider.jsx'

ReactDOM.createRoot(document.getElementById('root')).render(
    <React.StrictMode>
        <HashRouter>
            <ModalProvider>
                <App />
            </ModalProvider>
        </HashRouter>
    </React.StrictMode>,
)
