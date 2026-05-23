/**
 * Primary UI button — maps to Pressable + StyleSheet on React Native.
 * @param {{ variant?: 'primary'|'secondary'|'ghost', size?: 'sm'|'md', className?: string, children: import('react').ReactNode, [key: string]: unknown }} props
 */
export default function Button({
  variant = 'primary',
  size = 'md',
  className = '',
  children,
  ...rest
}) {
  return (
    <button
      type="button"
      className={`ui-btn ui-btn--${variant} ui-btn--${size} ${className}`.trim()}
      {...rest}
    >
      {children}
    </button>
  )
}
