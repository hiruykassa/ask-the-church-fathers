import { IoSearch } from 'react-icons/io5'
import Button from './Button'

/**
 * Search input row — portable pattern for RN (TextInput + Pressable).
 */
export default function SearchField({
  value,
  onChange,
  onSubmit,
  placeholder = 'Search by topic, father, or keyword…',
  compact = false,
}) {
  return (
    <div className={`ui-search-field${compact ? ' ui-search-field--compact' : ''}`}>
      <IoSearch className="ui-search-field__icon" aria-hidden />
      <input
        className="ui-search-field__input"
        type="search"
        enterKeyHint="search"
        autoComplete="off"
        placeholder={placeholder}
        value={value}
        onChange={e => onChange(e.target.value)}
        onKeyDown={e => e.key === 'Enter' && onSubmit()}
        aria-label="Search the Fathers"
      />
      <Button variant="primary" size="sm" className="ui-search-field__btn" onClick={onSubmit}>
        Search
      </Button>
    </div>
  )
}
