/**
 * The browse categories shown on the homepage / browse landing.
 *
 * Most map to the backend author `category` column (see migrate_schema.py) and
 * are counted + listed via /api/categories and /api/authors?category=. The one
 * exception is Biblical Commentaries, which is a work-level collection (the
 * verse commentaries), so it is sourced from /api/library's "Commentary"
 * section instead.
 *
 *   categoryKey  backend authors.category value (null = library-sourced)
 *   countField   which /api/categories field feeds the tile count
 *   sectionKey   /api/library section (only used by the library-sourced tile)
 *   slug         URL segment for /browse/:slug
 */
export const CATEGORIES = [
  {
    slug: 'fathers',
    categoryKey: 'father',
    countField: 'author_count',
    id: 'father',
    title: 'Church Fathers',
    blurb: 'The patristic authors, from the Apostolic Fathers to the great doctors of the early Church.',
    unit: 'authors',
  },
  {
    slug: 'commentaries',
    categoryKey: null,
    sectionKey: 'Commentary',
    id: 'commentary',
    title: 'Biblical Commentaries',
    blurb: 'Browse by verse, then read what each father wrote on it.',
    unit: 'commentaries',
    path: '/scripture',
  },
  {
    slug: 'councils',
    categoryKey: 'council',
    countField: 'author_count',
    id: 'council',
    title: 'Councils',
    blurb: 'Canons and acts of the ecumenical and regional councils.',
    unit: 'councils',
  },
  {
    slug: 'liturgies',
    categoryKey: 'liturgy',
    countField: 'author_count',
    id: 'liturgy',
    title: 'Liturgies',
    blurb: 'Early liturgical texts and rites of Christian worship.',
    unit: 'liturgies',
  },
  {
    slug: 'apocrypha',
    categoryKey: 'apocrypha',
    countField: 'author_count',
    id: 'apocrypha',
    title: 'Apocrypha',
    blurb: 'Non-canonical early Christian writings.',
    unit: 'texts',
  },
  {
    slug: 'misc',
    categoryKey: 'misc',
    countField: 'author_count',
    id: 'misc',
    title: 'Miscellaneous',
    blurb: 'Foundational texts outside the main collections.',
    unit: 'texts',
  },
]

export const CATEGORY_BY_SLUG = Object.fromEntries(
  CATEGORIES.map(c => [c.slug, c]),
)

/**
 * Builds the per-tile count for a category from the loaded data sources.
 * Author-categories read /api/categories; the commentary tile reads the
 * /api/library "Commentary" section. Returns null while still loading.
 */
export function categoryCount(def, catCounts, sections, settled) {
  if (def.categoryKey) {
    const row = catCounts && catCounts[def.categoryKey]
    if (row) return row[def.countField]
    return settled ? 0 : null
  }
  // Library-sourced (Biblical Commentaries)
  const list = sections && sections[def.sectionKey]
  if (list) return list.reduce((n, a) => n + (a.works ? a.works.length : 0), 0)
  return settled ? 0 : null
}
