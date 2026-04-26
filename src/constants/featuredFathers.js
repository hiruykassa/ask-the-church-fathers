import imgAugustine   from '../img/augustine.jpeg'
import imgAthanasius  from '../img/athanasius.jpeg'
import imgIgnatius    from '../img/ignatius.jpeg'
import imgIrenaeus    from '../img/irenaeus.jpeg'
import imgChrysostom  from '../img/chrysostom.jpeg'
import imgJustin      from '../img/justin-martyr.jpeg'
import imgTertullian  from '../img/tertullian.jpeg'
import imgBasil       from '../img/basil.jpeg'
import imgCyril       from '../img/cyril.jpeg'
import imgOrigen      from '../img/origen.jpeg'

/**
 * The 10 featured Church Fathers shown in the homepage card grid.
 * `cropFrame: true` shifts the image focal point upward to better
 * frame portrait-style icon artwork.
 *
 * @type {Array<{ name: string, dates: string, region: string, img: string, cropFrame?: boolean }>}
 */
export const FEATURED_FATHERS = [
  { name: 'Augustine of Hippo',       dates: '354–430',    region: 'North Africa', img: imgAugustine  },
  { name: 'John Chrysostom',          dates: '347–407',    region: 'Antioch',      img: imgChrysostom, cropFrame: true },
  { name: 'Athanasius of Alexandria', dates: '298–373',    region: 'Alexandria',   img: imgAthanasius },
  { name: 'Ignatius of Antioch',      dates: 'c. 35–107',  region: 'Antioch',      img: imgIgnatius   },
  { name: 'Justin Martyr',            dates: 'c. 100–165', region: 'Rome',         img: imgJustin,     cropFrame: true },
  { name: 'Cyril of Alexandria',      dates: '376–444',    region: 'Alexandria',   img: imgCyril,      cropFrame: true },
  { name: 'Tertullian',               dates: 'c. 155–220', region: 'Carthage',     img: imgTertullian },
  { name: 'Origen',                   dates: 'c. 185–254', region: 'Alexandria',   img: imgOrigen     },
  { name: 'Irenaeus of Lyons',        dates: 'c. 130–202', region: 'Gaul',         img: imgIrenaeus   },
  { name: 'Basil the Great',          dates: '329–379',    region: 'Cappadocia',   img: imgBasil      },
]
