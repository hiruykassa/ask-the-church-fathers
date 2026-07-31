import React from 'react'

/**
 * Catches render errors anywhere below it so a single bad component cannot
 * blank the whole page.
 *
 * Without this, any uncaught error during render unmounts the entire React
 * tree and leaves the user staring at an empty white document with no
 * explanation and no way forward — indistinguishable from the site being
 * down. This turns that into a readable message with a way out.
 *
 * Deliberately a class component: error boundaries have no hook equivalent.
 * `getDerivedStateFromError` is still the only way to render a fallback.
 *
 * Scope note — this catches errors thrown while *rendering*. It does not catch
 * errors inside event handlers, async callbacks, or promise rejections; those
 * paths handle their own failures (see `src/api/client.js`).
 */
export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    // Surfaced in the browser console and picked up by any error reporter
    // that hooks console/window errors. Kept deliberately simple — there is
    // no frontend error-reporting service wired up today.
    console.error('Unhandled render error:', error, info?.componentStack)
  }

  handleReload = () => {
    window.location.reload()
  }

  render() {
    if (!this.state.error) return this.props.children

    return (
      <div className="error-boundary" role="alert">
        <div className="error-boundary-inner">
          <span className="error-boundary-mark" aria-hidden>&#9633;</span>
          <h1 className="error-boundary-title">Something went wrong</h1>
          <p className="error-boundary-text">
            This page hit an unexpected error. The library itself is fine — try
            reloading, or head back to the search page.
          </p>
          <div className="error-boundary-actions">
            <button
              type="button"
              className="error-boundary-btn"
              onClick={this.handleReload}
            >
              Reload the page
            </button>
            <a className="error-boundary-link" href="/">
              Back to search
            </a>
          </div>
        </div>
      </div>
    )
  }
}
