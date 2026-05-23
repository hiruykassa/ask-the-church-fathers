export default function Chip({ children, className = '', ...rest }) {
  return (
    <button type="button" className={`ui-chip ${className}`.trim()} {...rest}>
      {children}
    </button>
  )
}
