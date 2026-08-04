// Adds jest-dom matchers (toBeInTheDocument, toHaveAttribute, …) to expect().
import '@testing-library/jest-dom/vitest'

// Testing Library auto-registers cleanup only when Vitest runs with
// `globals: true`. This project keeps globals off — tests import describe/it/
// expect explicitly — so cleanup has to be wired by hand. Without it every
// render stays in document.body and queries start matching elements left over
// from earlier tests ("Found multiple elements with the role link").
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

afterEach(cleanup)
