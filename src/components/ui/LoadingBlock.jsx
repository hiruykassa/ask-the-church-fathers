export default function LoadingBlock({ label = 'Loading...' }) {
  return (
    <div className="ui-loading" role="status" aria-live="polite">
      <span className="ui-loading__spinner" aria-hidden />
      <span className="ui-loading__label">{label}</span>
    </div>
  )
}
