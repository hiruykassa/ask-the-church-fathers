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
import ErrorBoundary from './components/ErrorBoundary.jsx'
import NotFound from './components/NotFound.jsx'
import './index.css'

// Guarded because this runs at module scope, *before* createRoot().render().
// Accessing localStorage throws SecurityError when site data is blocked (e.g.
// Chrome's "block all cookies", some embedded webviews). Unguarded, that
// exception escapes before React ever mounts, so the user gets a completely
// blank document — and ErrorBoundary, which lives inside the tree that never
// rendered, cannot catch it. public/theme-init.js already wraps the identical
// call in try/catch; this keeps the two consistent.
let stored = null
try {
  stored = localStorage.getItem(COLOR_MODE_KEY)
} catch {
  /* storage unavailable — fall through to the light default */
}
const initialMode = stored === 'dark' ? 'dark' : 'light'
applyWebTheme(initialMode)

// We restore scroll ourselves (see useScrollRestoration) because content loads
// async; the browser's native restore lands at the wrong spot on Back.
if ('scrollRestoration' in window.history) {
  window.history.scrollRestoration = 'manual'
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
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
            {/* Catch-all. Without it, <Routes> renders null for an unmatched
                URL and — because nothing wraps <Routes> — the document comes
                back completely empty under an HTTP 200 (CloudFront rewrites
                404 to /index.html with status 200). Must stay last. */}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </BrowserRouter>
      </ThemeProvider>
    </ErrorBoundary>
  </React.StrictMode>,
)
