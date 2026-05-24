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
  const paragraphs = synthesis
    ? synthesis.split(/\n+/).filter(p => p.trim())
    : []

  return (
    <div className="syn-panel">
      <div className="syn-head">
        <span className="syn-label">✦ AI Synthesis</span>
        <button className="syn-btn" onClick={getSynthesis} disabled={synthesizing}>
          {synthesizing ? 'Synthesizing…' : synthesis ? 'Regenerate' : 'Ask the Fathers'}
        </button>
      </div>

      {!synthesis && !synthesizing && (
        <p className="syn-placeholder">
          Click <em>Ask the Fathers</em> for a historian-style summary of what the passages say on{' '}
          <strong>"{topicQuery}"</strong>
          {authorFilter ? ` (filtered to ${authorFilter})` : ''}.
        </p>
      )}

      {synthesizing && synthesis === '' && (
        <p className="syn-placeholder">Consulting the Fathers…</p>
      )}

      {synthesis && (
        <div className="syn-text">
          {synthesizing && paragraphs.length === 0
            ? <p>{synthesis}</p>
            : paragraphs.map((para, i) => <p key={i}>{para}</p>)
          }
        </div>
      )}
    </div>
  )
}
