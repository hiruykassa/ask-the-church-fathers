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
import TopicPage from './TopicPage.jsx'
import TopicsIndexPage from './TopicsIndexPage.jsx'
import SeoJsonLd from './components/SeoJsonLd.jsx'
import './index.css'

const stored = localStorage.getItem(COLOR_MODE_KEY)
const initialMode = stored === 'dark' ? 'dark' : 'light'
applyWebTheme(initialMode)

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ThemeProvider>
      <BrowserRouter>
        <SeoJsonLd />
        <Routes>
          <Route path="/" element={<App />} />
          <Route path="/read/:workId" element={<ReadPage />} />
          <Route path="/topics" element={<TopicsIndexPage />} />
          <Route path="/topics/:slug" element={<TopicPage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="/contact" element={<ContactPage />} />
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  </React.StrictMode>,
)
