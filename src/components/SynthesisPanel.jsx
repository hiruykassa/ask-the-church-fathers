import ReactMarkdown from 'react-markdown'

/**
 * Panel that lets the user request an AI synthesis of the current search results.
 * Streams the response token-by-token via `getSynthesis`. Shows a placeholder
 * prompt before any synthesis has been generated.
 *
 * @param {{
 *   topicQuery: string,
 *   authorFilter: string | null,
 *   synthesis: string,
 *   synthesizing: boolean,
 *   getSynthesis: () => void,
 * }} props
 */
export default function SynthesisPanel({
  topicQuery, authorFilter, synthesis, synthesizing, getSynthesis,
}) {
  return (
    <div className="syn-panel">
      <div className="syn-head">
        <span className="syn-label">✦ AI Synthesis</span>
        <button className="syn-btn" onClick={getSynthesis} disabled={synthesizing}>
          {synthesizing ? 'Synthesizing…' : synthesis ? 'Regenerate' : 'Get Synthesis'}
        </button>
      </div>

      {!synthesis && !synthesizing && (
        <p className="syn-placeholder">
          Click <em>Get Synthesis</em> to see what the Fathers collectively taught on{' '}
          <strong>"{topicQuery}"</strong>
          {authorFilter ? ` — filtered to ${authorFilter}` : ' — across all Fathers'}.
        </p>
      )}

      {synthesizing && synthesis === '' && (
        <p className="syn-placeholder">Consulting the Fathers…</p>
      )}

      {synthesis && (
        <div className="syn-text">
          <ReactMarkdown>{synthesis}</ReactMarkdown>
        </div>
      )}
    </div>
  )
}
