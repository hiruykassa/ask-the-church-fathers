export default function EmptyState({ title, hint, children }) {
  return (
    <div className="ui-empty" role="status">
      <p className="ui-empty__title">{title}</p>
      {hint && <p className="ui-empty__hint">{hint}</p>}
      {children}
    </div>
  )
}
