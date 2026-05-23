import { IoArrowUp } from 'react-icons/io5'

export default function ScrollToTop({ visible, onPress }) {
  return (
    <button
      type="button"
      className={`scroll-top-btn${visible ? ' is-visible' : ''}`}
      onClick={onPress}
      aria-label="Back to top"
    >
      <IoArrowUp />
    </button>
  )
}
