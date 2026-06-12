import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { applyWebTheme } from './theme/applyWebTheme'
import { COLOR_MODE_KEY } from './theme/tokens'
import { ThemeProvider } from './theme/ThemeProvider'
import App from './App.jsx'
import ReadPage from './ReadPage.jsx'
import BrowsePage from './BrowsePage.jsx'
import AuthorPage from './AuthorPage.jsx'
import ScripturePage from './ScripturePage.jsx'
import AboutPage from './AboutPage.jsx'
import ContactPage from './ContactPage.jsx'
import TopicPage from './TopicPage.jsx'
import TopicsIndexPage from './TopicsIndexPage.jsx'
import SeoJsonLd from './components/SeoJsonLd.jsx'
import './index.css'

const stored = localStorage.getItem(COLOR_MODE_KEY)
const initialMode = stored === 'dark' ? 'dark' : 'light'
applyWebTheme(initialMode)

// We restore scroll ourselves (see useScrollRestoration) because content loads
// async; the browser's native restore lands at the wrong spot on Back.
if ('scrollRestoration' in window.history) {
  window.history.scrollRestoration = 'manual'
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ThemeProvider>
      <BrowserRouter>
        <SeoJsonLd />
        <Routes>
          <Route path="/" element={<App />} />
          <Route path="/read/:workId" element={<ReadPage />} />
          <Route path="/browse" element={<BrowsePage />} />
          <Route path="/browse/:slug" element={<BrowsePage />} />
          <Route path="/author/:id" element={<AuthorPage />} />
          <Route path="/scripture" element={<ScripturePage />} />
          <Route path="/scripture/:book" element={<ScripturePage />} />
          <Route path="/scripture/:book/:chapter" element={<ScripturePage />} />
          <Route path="/scripture/:book/:chapter/:verse" element={<ScripturePage />} />
          <Route path="/topics" element={<TopicsIndexPage />} />
          <Route path="/topics/:slug" element={<TopicPage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="/contact" element={<ContactPage />} />
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  </React.StrictMode>,
)
