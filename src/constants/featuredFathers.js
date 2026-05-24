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
 * Featured Fathers card grid.
 * imgPos / imgScale tune each icon so faces sit at the same headshot height.
 * Vertical position: higher % = head moves up in the card; lower % = head moves down.
 *
 * @type {Array<{ name: string, dates: string, region: string, img: string, imgPos?: string, imgScale?: number }>}
 */
export const FEATURED_FATHERS = [
  { name: 'Augustine',     dates: '354–430',    region: 'North Africa', img: imgAugustine,  imgPos: 'center 11%', imgScale: 1.44 },
  { name: 'Chrysostom',    dates: '347–407',    region: 'Antioch',      img: imgChrysostom, imgPos: 'center 13%', imgScale: 1.46 },
  { name: 'Athanasius',    dates: '298–373',    region: 'Alexandria',   img: imgAthanasius, imgPos: 'center 11%', imgScale: 1.82 },
  { name: 'Ignatius',      dates: 'c. 35–107',  region: 'Antioch',      img: imgIgnatius,   imgPos: 'center 20%', imgScale: 2.35 },
  { name: 'Justin Martyr', dates: 'c. 100–165', region: 'Rome',         img: imgJustin,     imgPos: 'center 22%', imgScale: 1.14 },
  { name: 'Cyril',         dates: '376–444',    region: 'Alexandria',   img: imgCyril,      imgPos: 'center 11%', imgScale: 1.42 },
  { name: 'Tertullian',    dates: 'c. 155–220', region: 'Carthage',     img: imgTertullian, imgPos: 'center 12%', imgScale: 1.52 },
  { name: 'Origen',        dates: 'c. 185–254', region: 'Alexandria',   img: imgOrigen,     imgPos: '52% 11%',    imgScale: 1.52 },
  { name: 'Irenaeus',      dates: 'c. 130–202', region: 'Gaul',         img: imgIrenaeus,   imgPos: 'center 12%', imgScale: 1.42 },
  { name: 'Basil',         dates: '329–379',    region: 'Cappadocia',   img: imgBasil,      imgPos: 'center 11%', imgScale: 1.40 },
]
