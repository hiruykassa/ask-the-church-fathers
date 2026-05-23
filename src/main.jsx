import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { applyWebTheme } from './theme/applyWebTheme'
import { COLOR_MODE_KEY } from './theme/tokens'
import { ThemeProvider } from './theme/ThemeProvider'
import App from './App.jsx'
import ReadPage from './ReadPage.jsx'
import AboutPage from './AboutPage.jsx'
import ContactPage from './ContactPage.jsx'
import './index.css'

const stored = localStorage.getItem(COLOR_MODE_KEY)
const initialMode = stored === 'dark' ? 'dark' : 'light'
applyWebTheme(initialMode)

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ThemeProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<App />} />
          <Route path="/read/:workId" element={<ReadPage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="/contact" element={<ContactPage />} />
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  </React.StrictMode>,
)
