/**
 * ChristianIcons.jsx
 * Displays your Byzantine iconography images.
 */

import augustine      from './assets/icons/st-augustine.jpeg'
import chrysostom     from './assets/icons/st-john-chrysostom.jpeg'
import mosesBlack     from './assets/icons/st-moses-the-black.jpeg'
import ambrose        from './assets/icons/st-ambrose.jpeg'
import leoGreat       from './assets/icons/st-leo-the-great.jpeg'
import cyrilAlex      from './assets/icons/st-cyril-of-alexandria.jpeg'
import threeHierarchs from './assets/icons/three-holy-hierarchs.jpeg'
import apostles       from './assets/icons/twelve-apostles.jpeg'
import maryEgypt      from './assets/icons/st-mary-of-egypt.jpeg'
import icon3          from './assets/icons/icon-3.jpeg'
import icon4          from './assets/icons/icon-4.jpeg'
import icon5          from './assets/icons/icon-5.jpeg'
import icon6          from './assets/icons/icon-6.jpeg'
import icon7          from './assets/icons/icon-7.jpeg'
import icon8          from './assets/icons/icon-8.jpeg'

/** Icons shown in the header strip (6 circular frames) */
const STRIP_ICONS = [
  { src: augustine,  label: 'St. Augustine of Hippo' },
  { src: chrysostom, label: 'St. John Chrysostom' },
  { src: mosesBlack, label: 'St. Moses the Black' },
  { src: ambrose,    label: 'St. Ambrose' },
  { src: leoGreat,   label: 'St. Leo the Great' },
  { src: cyrilAlex,  label: 'St. Cyril of Alexandria' },
]

/** All icons shown in the landing gallery */
export const ALL_ICONS = [
  { src: augustine,       label: 'St. Augustine of Hippo' },
  { src: chrysostom,      label: 'St. John Chrysostom' },
  { src: mosesBlack,      label: 'St. Moses the Black' },
  { src: ambrose,         label: 'St. Ambrose' },
  { src: leoGreat,        label: 'St. Leo the Great' },
  { src: cyrilAlex,       label: 'St. Cyril of Alexandria' },
  { src: threeHierarchs,  label: 'The Three Holy Hierarchs' },
  { src: apostles,        label: 'The Twelve Apostles' },
  { src: maryEgypt,       label: 'St. Mary of Egypt' },
  { src: icon3,           label: 'Byzantine Icon' },
  { src: icon4,           label: 'Byzantine Icon' },
  { src: icon5,           label: 'Byzantine Icon' },
  { src: icon6,           label: 'Byzantine Icon' },
  { src: icon7,           label: 'Byzantine Icon' },
  { src: icon8,           label: 'Byzantine Icon' },
]

export function IconStrip() {
  return (
    <div className="icon-strip" aria-label="Church Fathers icons">
      {STRIP_ICONS.map(({ src, label }) => (
        <span key={label} className="icon-strip-item" title={label} aria-label={label}>
          <img src={src} alt={label} className="icon-img" />
        </span>
      ))}
    </div>
  )
}

export function IconSidebar() {
  return (
    <aside className="icon-sidebar" aria-label="Christian iconography">
      {ALL_ICONS.map(({ src, label }) => (
        <div key={label} className="sidebar-icon" title={label}>
          <img src={src} alt={label} className="sidebar-icon-img" />
        </div>
      ))}
    </aside>
  )
}
