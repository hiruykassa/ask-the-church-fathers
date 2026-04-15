import { useState, useCallback } from 'react'
import { MdFavoriteBorder, MdFavorite } from 'react-icons/md'
import { IoSearch, IoChevronDown, IoChevronUp, IoClose } from 'react-icons/io5'
import { searchFathers, fathers } from './data/fathers'
import './App.css'

/* ── Detect a Father's name in the raw query string ── */
function detectAuthor(q) {
  if (!q) return null
  const lower = q.toLowerCase()
  for (const f of fathers) {
    // match on first word of surname or full name
    const nameLower = f.name.toLowerCase()
    const parts = nameLower.split(/\s+/)
    if (parts.some(p => p.length > 4 && lower.includes(p))) {
      return f.name
    }
  }
  return null
}

/* ── Strip the author name from the query so we search by topic only ── */
function stripAuthor(q, authorName) {
  if (!authorName) return q
  // remove each word of the author name and common prefixes from the query
  let result = q
  const wordsToRemove = [
    ...authorName.toLowerCase().split(/\s+/),
    'saint', 'st.', 'st', 'blessed', 'pope', 'bishop', 'of', 'the',
    'on', 'about', 'regarding', 'according', 'to', 'what', 'did', 'say'
  ]
  for (const w of wordsToRemove) {
    result = result.replace(new RegExp('\\b' + w + '\\b', 'gi'), '')
  }
  return result.replace(/\s+/g, ' ').trim()
}

/* ── Apostolic suggestions ── */
const SUGGESTIONS = [
  'Eucharist', 'baptism', 'prayer', 'fasting', 'martyrdom',
  'repentance', 'scripture', 'resurrection', 'Holy Spirit', 'church'
]

/* ── Sort helper ── */
const alpha = arr => [...arr].sort((a, b) => a.name.localeCompare(b.name))

/* ══════════════════════════════════════════════════
   FULL FATHERS LIST  (left column)
══════════════════════════════════════════════════ */
const ALL_FATHERS = alpha([
  { name: 'Alexander of Alexandria',   dates: 'd. 328',         titles: ['SAINT'],          works: ['Epistles on the Arian Heresy and the Deposition of Arius'] },
  { name: 'Alexander of Lycopolis',    dates: 'fl. c. 300',     titles: [],                 works: ['Of the Manicheans'] },
  { name: 'Ambrose of Milan',          dates: '340-397',        titles: ['SAINT','DOCTOR'], works: ['On the Christian Faith (De fide)', 'On the Holy Spirit', 'On the Mysteries', 'On Repentance', 'On the Duties of the Clergy', 'Concerning Virgins', 'Concerning Widows', 'On the Death of Satyrus', 'Memorial of Symmachus', 'Sermon against Auxentius', 'Letters'] },
  { name: 'Aphrahat / Aphraates',      dates: 'c. 280-367',     titles: [],                 works: ['Demonstrations'] },
  { name: 'Archelaus',                 dates: 'fl. c. 278',     titles: [],                 works: ['Acts of the Disputation with the Heresiarch Manes'] },
  { name: 'Aristides the Philosopher', dates: 'fl. c. 125',     titles: [],                 works: ['The Apology'] },
  { name: 'Arnobius',                  dates: 'fl. c. 295-330', titles: [],                 works: ['Against the Heathen'] },
  { name: 'Athanasius of Alexandria',  dates: '298-373',        titles: ['SAINT','DOCTOR'], works: ['Against the Heathen', 'On the Incarnation of the Word', 'Deposition of Arius', 'Statement of Faith', 'On Luke 10:22 (Matthew 11:27)', 'Circular Letter', 'Apologia Contra Arianos', 'De Decretis', 'De Sententia Dionysii', 'Vita S. Antoni (Life of St. Anthony)', 'Ad Episcopus Aegypti et Libyae', 'Apologia ad Constantium', 'Apologia de Fuga', 'Historia Arianorum', 'Four Discourses Against the Arians', 'De Synodis', 'Tomus ad Antiochenos', 'Ad Afros Epistola Synodica', 'Historia Acephala', 'Letters'] },
  { name: 'Athenagoras',               dates: 'fl. c. 177',     titles: [],                 works: ['A Plea for the Christians', 'The Resurrection of the Dead'] },
  { name: 'Augustine of Hippo',        dates: '354-430',        titles: ['SAINT','DOCTOR'], works: ['Confessions', 'Letters', 'City of God', 'Christian Doctrine', 'On the Holy Trinity', 'The Enchiridion', 'On the Catechising of the Uninstructed', 'On Faith and the Creed', 'Concerning Faith of Things Not Seen', 'On the Profit of Believing', 'On the Creed: A Sermon to Catechumens', 'On Continence', 'On the Good of Marriage', 'On Holy Virginity', 'On the Good of Widowhood', 'On Lying', 'To Consentius: Against Lying', 'On the Work of Monks', 'On Patience', 'On Care to be Had For the Dead', 'On the Morals of the Catholic Church', 'On the Morals of the Manichaeans', 'On Two Souls, Against the Manichaeans', 'Acts or Disputation Against Fortunatus the Manichaean', 'Against the Epistle of Manichaeus Called Fundamental', 'Reply to Faustus the Manichaean', 'Concerning the Nature of Good, Against the Manichaeans', 'On Baptism, Against the Donatists', 'Answer to Letters of Petilian, Bishop of Cirta', 'Merits and Remission of Sin, and Infant Baptism', 'On the Spirit and the Letter', 'On Nature and Grace', 'On Mans Perfection in Righteousness', 'On the Proceedings of Pelagius', 'On the Grace of Christ, and on Original Sin', 'On Marriage and Concupiscence', 'On the Soul and its Origin', 'Against Two Letters of the Pelagians', 'On Grace and Free Will', 'On Rebuke and Grace', 'The Predestination of the Saints / Gift of Perseverance', 'Our Lords Sermon on the Mount', 'The Harmony of the Gospels', 'Sermons on Selected Lessons of the New Testament', 'Tractates on the Gospel of John', 'Homilies on the First Epistle of John', 'Soliloquies', 'The Enarrations, or Expositions, on the Psalms'] },
  { name: 'Bardesanes',                dates: '154-222',        titles: [],                 works: ['The Book of the Laws of Various Countries'] },
  { name: 'Barnabas',                  dates: 'fl. c. 70-130',  titles: ['SAINT'],          works: ['Epistle of Barnabas'] },
  { name: 'Basil the Great',           dates: '329-379',        titles: ['SAINT','DOCTOR'], works: ['De Spiritu Sancto', 'Nine Homilies of Hexaemeron', 'Letters'] },
  { name: 'Caius',                     dates: 'fl. c. 199',     titles: [],                 works: ['Fragments'] },
  { name: 'Clement of Alexandria',     dates: 'c. 150-c. 215',  titles: ['SAINT'],          works: ['Who is the Rich Man That Shall Be Saved?', 'Exhortation to the Heathen', 'The Instructor', 'The Stromata, or Miscellanies', 'Fragments'] },
  { name: 'Clement of Rome',           dates: 'fl. c. 96',      titles: ['SAINT'],          works: ['First Epistle', 'Second Epistle [SPURIOUS]', 'Two Epistles Concerning Virginity [SPURIOUS]', 'Recognitions [SPURIOUS]', 'Clementine Homilies [SPURIOUS]'] },
  { name: 'Commodianus',               dates: 'fl. c. 240',     titles: [],                 works: ['Writings'] },
  { name: 'Cyprian of Carthage',       dates: 'c. 200-258',     titles: ['SAINT'],          works: ['The Life and Passion of Cyprian By Pontius the Deacon', 'The Epistles of Cyprian', 'The Treatises of Cyprian', 'The Seventh Council of Carthage'] },
  { name: 'Cyril of Jerusalem',        dates: 'c. 313-386',     titles: ['SAINT','DOCTOR'], works: ['Catechetical Lectures'] },
  { name: 'Dionysius of Rome',         dates: 'd. 268',         titles: ['SAINT'],          works: ['Against the Sabellians'] },
  { name: 'Dionysius the Great',       dates: 'c. 200-265',     titles: [],                 works: ['Epistles and Epistolary Fragments', 'Exegetical Fragments', 'Miscellaneous Fragments'] },
  { name: 'Ephraim the Syrian',        dates: '306-373',        titles: ['SAINT','DOCTOR'], works: ['Nisibene Hymns', 'Miscellaneous Hymns', 'Homilies'] },
  { name: 'Eusebius of Caesarea',      dates: 'c. 265-c. 340',  titles: [],                 works: ['Church History', 'Life of Constantine', 'Oration of Constantine to the Assembly of the Saints', 'Oration in Praise of Constantine', 'Letter on the Council of Nicaea'] },
  { name: 'Gennadius of Marseilles',   dates: 'fl. c. 480',     titles: [],                 works: ['Illustrious Men (Supplement to Jerome)'] },
  { name: 'Gregory the Great',         dates: 'c. 540-604',     titles: ['SAINT','DOCTOR'], works: ['Pastoral Rule', 'Register of Letters'] },
  { name: 'Gregory Nazianzen',         dates: '329-390',        titles: ['SAINT','DOCTOR'], works: ['Orations', 'Letters'] },
  { name: 'Gregory of Nyssa',          dates: 'c. 335-c. 395',  titles: ['SAINT'],          works: ['Against Eunomius', 'Answer to Eunomius Second Book', 'On the Holy Spirit (Against the Followers of Macedonius)', 'On the Holy Trinity, and of the Godhead of the Holy Spirit (To Eustathius)', 'On Not Three Gods (To Ablabius)', 'On the Faith (To Simplicius)', 'On Virginity', 'On Infants Early Deaths', 'On Pilgrimages', 'On the Making of Man', 'On the Soul and the Resurrection', 'The Great Catechism', 'Funeral Oration on Meletius', 'On the Baptism of Christ (Sermon for the Day of Lights)', 'Letters'] },
  { name: 'Gregory Thaumaturgus',      dates: 'c. 213-c. 270',  titles: ['SAINT'],          works: ['A Declaration of Faith', 'A Metaphrase of the Book of Ecclesiastes', 'Canonical Epistle', 'The Oration and Panegyric Addressed to Origen', 'A Sectional Confession of Faith', 'On the Trinity', 'Twelve Topics on the Faith', 'On the Subject of the Soul', 'Four Homilies', 'On All the Saints', 'On Matthew 6:22-23'] },
  { name: 'Hermas',                    dates: 'fl. c. 140-155', titles: [],                 works: ['The Pastor (or The Shepherd)'] },
  { name: 'Hilary of Poitiers',        dates: 'c. 310-367',     titles: ['SAINT','DOCTOR'], works: ['On the Councils, or the Faith of the Easterns', 'On the Trinity', 'Homilies on the Psalms'] },
  { name: 'Hippolytus of Rome',        dates: 'c. 170-235',     titles: ['SAINT'],          works: ['The Refutation of All Heresies', 'Some Exegetical Fragments of Hippolytus', 'Expository Treatise Against the Jews', 'Against Plato, On the Cause of the Universe', 'Against the Heresy of Noetus', 'Discourse on the Holy Theophany', 'The Antichrist', 'The End of the World (Pseudonymous)', 'The Apostles and the Disciples (Pseudonymous)'] },
  { name: 'Ignatius of Antioch',       dates: 'c. 35-c. 108',   titles: ['SAINT'],          works: ['Epistle to the Ephesians', 'Epistle to the Magnesians', 'Epistle to the Trallians', 'Epistle to the Romans', 'Epistle to the Philadelphians', 'Epistle to the Smyrnaeans', 'Epistle to Polycarp', 'The Martyrdom of Ignatius', 'The Spurious Epistles'] },
  { name: 'Irenaeus of Lyons',         dates: 'c. 130-c. 202',  titles: ['SAINT'],          works: ['Adversus haereses', 'Fragments from the Lost Writings of Irenaeus'] },
  { name: 'Jerome',                    dates: 'c. 347-420',     titles: ['SAINT','DOCTOR'], works: ['Letters', 'The Perpetual Virginity of Blessed Mary', 'To Pammachius Against John of Jerusalem', 'The Dialogue Against the Luciferians', 'The Life of Malchus, the Captive Monk', 'The Life of S. Hilarion', 'The Life of Paulus the First Hermit', 'Against Jovinianus', 'Against Vigilantius', 'Against the Pelagians', 'Prefaces', 'De Viris Illustribus (Illustrious Men)', 'Apology for himself against the Books of Rufinus'] },
  { name: 'John Cassian',              dates: 'c. 360-c. 435',  titles: [],                 works: ['Institutes', 'Conferences', 'On the Incarnation of the Lord (Against Nestorius)'] },
  { name: 'John Chrysostom',           dates: 'c. 349-407',     titles: ['SAINT','DOCTOR'], works: ['Homilies on the Gospel of St. Matthew', 'Homilies on Acts', 'Homilies on Romans', 'Homilies on First Corinthians', 'Homilies on Second Corinthians', 'Homilies on Ephesians', 'Homilies on Philippians', 'Homilies on Colossians', 'Homilies on First Thessalonians', 'Homilies on Second Thessalonians', 'Homilies on First Timothy', 'Homilies on Second Timothy', 'Homilies on Titus', 'Homilies on Philemon', 'Commentary on Galatians', 'Homilies on the Gospel of John', 'Homilies on the Epistle to the Hebrews', 'Homilies on the Statues', 'No One Can Harm the Man Who Does Not Injure Himself', 'Two Letters to Theodore After His Fall', 'Letter to a Young Widow', 'Homily on St. Ignatius', 'Homily on St. Babylas', 'Homily Concerning Lowliness of Mind', 'Instructions to Catechumens', 'Three Homilies on the Power of Satan', 'Homily on the Passage Father if it be possible', 'Homily on the Paralytic Lowered Through the Roof', 'Homily on the Passage If your enemy hunger feed him', 'Homily Against Publishing the Errors of the Brethren', 'First Homily on Eutropius', 'Second Homily on Eutropius (After His Captivity)', 'Four Letters to Olympias', 'Letter to Some Priests of Antioch', 'Correspondence with Pope Innocent I', 'On the Priesthood'] },
  { name: 'John of Damascus',          dates: 'c. 675-749',     titles: ['SAINT','DOCTOR'], works: ['Exposition of the Faith'] },
  { name: 'Julius Africanus',          dates: 'c. 160-c. 240',  titles: [],                 works: ['Extant Writings'] },
  { name: 'Justin Martyr',             dates: 'c. 100-165',     titles: ['SAINT'],          works: ['First Apology', 'Second Apology', 'Dialogue with Trypho', 'Hortatory Address to the Greeks', 'On the Sole Government of God', 'Fragments of the Lost Work on the Resurrection', 'Miscellaneous Fragments from Lost Writings', 'Martyrdom of Justin, Chariton, and other Roman Martyrs', 'Discourse to the Greeks'] },
  { name: 'Lactantius',                dates: 'c. 250-c. 325',  titles: [],                 works: ['The Divine Institutes', 'The Epitome of the Divine Institutes', 'On the Anger of God', 'On the Workmanship of God', 'Of the Manner In Which the Persecutors Died', 'Fragments of Lactantius', 'The Phoenix', 'A Poem on the Passion of the Lord'] },
  { name: 'Leo the Great',             dates: 'c. 395-461',     titles: ['SAINT','DOCTOR'], works: ['Sermons', 'Letters'] },
  { name: 'Malchion',                  dates: 'fl. c. 270',     titles: [],                 works: ['Epistle'] },
  { name: 'Mar Jacob',                 dates: '452-521',        titles: [],                 works: ['Canticle on Edessa', 'Homily on Habib the Martyr', 'Homily on Guria and Shamuna'] },
  { name: 'Mathetes',                  dates: 'fl. c. 130',     titles: [],                 works: ['Epistle to Diognetus'] },
  { name: 'Methodius',                 dates: 'd. c. 311',      titles: [],                 works: ['The Banquet of the Ten Virgins', 'Concerning Free Will', 'From the Discourse on the Resurrection', 'Fragments', 'Oration Concerning Simeon and Anna', 'Oration on the Psalms', 'Three Fragments from the Homily on the Cross and Passion of Christ'] },
  { name: 'Minucius Felix',            dates: 'fl. c. 200-240', titles: [],                 works: ['Octavius'] },
  { name: 'Moses of Chorene',          dates: 'c. 400-c. 490',  titles: [],                 works: ['History of Armenia'] },
  { name: 'Novatian',                  dates: 'c. 200-258',     titles: [],                 works: ['Treatise Concerning the Trinity', 'On the Jewish Meats'] },
  { name: 'Origen',                    dates: 'c. 184-c. 253',  titles: [],                 works: ['De Principiis', 'Africanus to Origen', 'Origen to Africanus', 'Origen to Gregory', 'Against Celsus', 'Letter of Origen to Gregory', 'Commentary on the Gospel of John', 'Commentary on the Gospel of Matthew'] },
  { name: 'Pamphilus',                 dates: 'c. 240-309',     titles: ['SAINT'],          works: ['Exposition on the Acts of the Apostles'] },
  { name: 'Papias',                    dates: 'c. 60-c. 130',   titles: ['SAINT'],          works: ['Fragments'] },
  { name: 'Peter of Alexandria',       dates: 'd. 311',         titles: ['SAINT'],          works: ['The Genuine Acts', 'The Canonical Epistle', 'Fragments'] },
  { name: 'Polycarp',                  dates: 'c. 69-155',      titles: ['SAINT'],          works: ['Epistle to the Philippians', 'The Martyrdom of Polycarp'] },
  { name: 'Rufinus',                   dates: '344-411',        titles: [],                 works: ['Apology', 'Commentary on the Apostles Creed', 'Prefaces and Other Works'] },
  { name: 'Socrates Scholasticus',     dates: 'c. 379-c. 450',  titles: [],                 works: ['Ecclesiastical History'] },
  { name: 'Sozomen',                   dates: 'c. 375-c. 447',  titles: [],                 works: ['Ecclesiastical History'] },
  { name: 'Sulpitius Severus',         dates: 'c. 363-c. 420',  titles: [],                 works: ['On the Life of St. Martin', 'Letters - Genuine and Dubious', 'Dialogues', 'Sacred History'] },
  { name: 'Tatian',                    dates: 'c. 120-c. 180',  titles: [],                 works: ['Address to the Greeks', 'Fragments', 'The Diatessaron'] },
  { name: 'Tertullian',                dates: 'c. 155-c. 220',  titles: [],                 works: ['The Apology', 'On Idolatry', 'De Spectaculis (The Shows)', 'De Corona (The Chaplet)', 'To Scapula', 'Ad Nationes', 'An Answer to the Jews', 'The Souls Testimony', 'A Treatise on the Soul', 'The Prescription Against Heretics', 'Against Marcion', 'Against Hermogenes', 'Against the Valentinians', 'On the Flesh of Christ', 'On the Resurrection of the Flesh', 'Against Praxeas', 'Scorpiace', 'Appendix (Against All Heresies)', 'On Repentance', 'On Baptism', 'On Prayer', 'Ad Martyras', 'The Martyrdom of Perpetua and Felicity', 'Of Patience', 'On the Pallium', 'On the Apparel of Women', 'On the Veiling of Virgins', 'To His Wife', 'On Exhortation to Chastity', 'On Monogamy', 'On Modesty', 'On Fasting', 'De Fuga in Persecutione'] },
  { name: 'Theodoret',                 dates: 'c. 393-c. 457',  titles: [],                 works: ['Counter-Statements to Cyrils 12 Anathemas against Nestorius', 'Ecclesiastical History', 'Dialogues (Eranistes or Polymorphus)', 'Demonstrations by Syllogism', 'Letters'] },
  { name: 'Theodotus',                 dates: 'fl. c. 160',     titles: [],                 works: ['Excerpts'] },
  { name: 'Theophilus of Antioch',     dates: 'd. c. 183',      titles: [],                 works: ['Theophilus to Autolycus'] },
  { name: 'Venantius',                 dates: 'c. 530-c. 600',  titles: [],                 works: ['Poem on Easter'] },
  { name: 'Victorinus',                dates: 'd. c. 304',      titles: ['SAINT'],          works: ['On the Creation of the World', 'Commentary on the Apocalypse of the Blessed John'] },
  { name: 'Vincent of Lerins',         dates: 'd. c. 450',      titles: ['SAINT'],          works: ['Commonitory for the Antiquity and Universality of the Catholic Faith'] },
])

const SECTIONS_LEFT = [
  { id: 'fathers', title: 'The Fathers of the Church', entries: ALL_FATHERS }
]

/* ══════════════════════════════════════════════════
   OTHER WORKS  (right column)
══════════════════════════════════════════════════ */
const SECTIONS_RIGHT = [
  {
    id: 'liturgies',
    title: 'Liturgies',
    entries: alpha([
      { name: 'The Liturgy of James',                works: [] },
      { name: 'The Liturgy of Mark',                 works: [] },
      { name: 'The Liturgy of the Blessed Apostles', works: [] },
    ])
  },
  {
    id: 'councils',
    title: 'Councils',
    entries: [
      ...alpha([
        { name: 'Nicaea I (325)',                              works: [], badge: 'ECUMENICAL' },
        { name: 'Constantinople I (381)',                      works: [], badge: 'ECUMENICAL' },
        { name: 'Ephesus (431)',                               works: [], badge: 'ECUMENICAL' },
        { name: 'Chalcedon (451)',                             works: [], badge: 'ECUMENICAL' },
        { name: 'Constantinople II (553)',                     works: [], badge: 'ECUMENICAL' },
        { name: 'Constantinople III (680)',                    works: [], badge: 'ECUMENICAL' },
        { name: 'Nicaea II (787)',                             works: [], badge: 'ECUMENICAL' },
      ]),
      ...alpha([
        { name: 'Carthage under Cyprian (257)',                works: [], badge: 'LOCAL' },
        { name: 'Ancyra (314)',                                works: [], badge: 'LOCAL' },
        { name: 'Neocaesarea (315)',                           works: [], badge: 'LOCAL' },
        { name: 'Antioch in Encaeniis (341)',                  works: [], badge: 'LOCAL' },
        { name: 'Gangra (343)',                                works: [], badge: 'LOCAL' },
        { name: 'Sardica (344)',                               works: [], badge: 'LOCAL' },
        { name: 'Constantinople (382)',                        works: [], badge: 'LOCAL' },
        { name: 'Laodicea (390)',                              works: [], badge: 'LOCAL' },
        { name: 'Constantinople under Nectarius (394)',        works: [], badge: 'LOCAL' },
        { name: 'Carthage (419)',                              works: [], badge: 'LOCAL' },
        { name: 'Constantinople / Trullo / Quinisext (692)',   works: [], badge: 'LOCAL' },
      ]),
    ]
  },
  {
    id: 'apocrypha',
    title: 'Apocrypha',
    entries: [
      { name: 'Apocalypse of Peter (c. 130)',                         works: [] },
      { name: 'Protoevangelium of James (c. 150)',                    works: [] },
      { name: 'Gospel of Nicodemus / Acta Pilati (c. 150-400)',      works: [] },
      { name: 'Acts of Paul and Thecla (c. 180)',                    works: [] },
      { name: 'Gospel of Peter (c. 190) [DOCETIC]',                  works: [] },
      { name: 'Testaments of the Twelve Patriarchs (c. 192) [EBIONITIC]', works: [] },
      { name: 'Acts of Peter and Paul (c. 200)',                     works: [] },
      { name: 'Gospel of Thomas (c. 200) [GNOSTIC]',                 works: [] },
      { name: 'Acts of Thomas (c. 240) [GNOSTIC]',                   works: [] },
      { name: 'Acts of Thaddaeus (c. 250)',                          works: [] },
      { name: 'Acts of Andrew (c. 260) [GNOSTIC]',                   works: [] },
      { name: 'Acts of Xanthippe and Polyxena (c. 270)',             works: [] },
      { name: 'Acts of John [DOCETIC]',                              works: [] },
      { name: 'Acts of Philip (c. 350)',                             works: [] },
      { name: 'Apocalypse of Paul (c. 380)',                         works: [] },
      { name: 'The Doctrine of Addai (c. 400)',                      works: [] },
      { name: 'Assumption of Mary (c. 400)',                         works: [] },
      { name: 'History of Joseph the Carpenter (c. 400)',            works: [] },
      { name: 'Gospel of Pseudo-Matthew (c. 400)',                   works: [] },
      { name: 'Acts of Barnabas (c. 500)',                           works: [] },
      { name: 'Acts of Bartholomew (c. 500) [NESTORIAN]',            works: [] },
      { name: 'Acts and Martyrdom of St. Matthew the Apostle (c. 550) [ABYSSINIAN]', works: [] },
      { name: 'Arabic Gospel of the Infancy of the Saviour (c. 600)', works: [] },
      { name: 'Avenging of the Saviour (c. 700)',                    works: [] },
      { name: 'Apocalypse of John (unknown date; late)',              works: [] },
      { name: 'Apocalypse of Moses (unknown date) [JUDAISTIC]',       works: [] },
      { name: 'Apocalypse of Esdras (unknown date) [JUDAISTIC]',      works: [] },
      { name: 'Testament of Abraham (unknown date) [JUDAISTIC]',      works: [] },
      { name: 'Narrative of Zosimus (unknown date)',                  works: [] },
      { name: 'Gospel of the Nativity of Mary (unknown date; late)',  works: [] },
      { name: 'Narrative of Joseph of Arimathea (unknown date; late)', works: [] },
      { name: 'Report of Pontius Pilate (unknown date; late)',        works: [] },
      { name: 'Letter of Pontius Pilate (unknown date; late)',        works: [] },
      { name: 'Giving Up of Pontius Pilate (unknown date; late)',     works: [] },
      { name: 'Death of Pilate (unknown date; late)',                 works: [] },
      { name: 'Apocalypse of the Virgin (unknown date; very late)',   works: [] },
      { name: 'Apocalypse of Sedrach (unknown date; very late)',      works: [] },
      { name: 'Acts of Andrew and Matthias',                         works: [] },
      { name: 'Acts of Peter and Andrew',                            works: [] },
      { name: 'Consummation of Thomas the Apostle',                  works: [] },
    ]
  },
  {
    id: 'misc',
    title: 'Miscellaneous',
    entries: [
      { name: 'The Didache (c. 100)',                                         works: [] },
      { name: 'The Passion of the Scillitan Martyrs (c. 180)',               works: [] },
      { name: 'A Treatise Against the Heretic Novatian (c. 255)',            works: [] },
      { name: 'A Treatise on Re-Baptism (c. 255)',                           works: [] },
      { name: 'Remains of the Second and Third Centuries (various)',         works: [] },
      { name: 'Apostolic Constitutions (c. 400)',                            works: [] },
      { name: 'Apostolic Canons (c. 400)',                                   works: [] },
      { name: 'The Legend of Barlaam and Josaphat',                         works: [] },
      { name: 'The False Decretals (c. 850)',                                works: [] },
      { name: 'Acts of Sharbil [SYRIAC]',                                    works: [] },
      { name: 'The Martyrdom of Barsamya [SYRIAC]',                          works: [] },
      { name: 'Extracts Concerning Abgar the King and Addaeus the Apostle [SYRIAC]', works: [] },
      { name: 'The Teaching of the Apostles [SYRIAC]',                       works: [] },
      { name: 'The Teaching of Simon Cephas in the City of Rome [SYRIAC]',  works: [] },
      { name: 'Martyrdom of Habib the Deacon [SYRIAC]',                      works: [] },
      { name: 'Martyrdom of the Holy Confessors Shamuna, Guria, and Habib [SYRIAC]', works: [] },
      { name: 'A Letter of Mara, Son of Serapion [SYRIAC]',                 works: [] },
      { name: 'Ambrose [SYRIAC]',                                            works: [] },
    ]
  },
]

/* ══════════════════════════════════════════════════
   ENTRY ROW  — name row + optional works sub-accordion
══════════════════════════════════════════════════ */
function EntryRow({ entry, isFather, onSearch, onFatherClick, onWorkClick }) {
  const [open, setOpen] = useState(false)
  const hasWorks = entry.works && entry.works.length > 0

  return (
    <li className="na-entry">
      <div className="na-entry-head">
        {hasWorks ? (
          <button
            className="na-expand-btn"
            onClick={() => setOpen(o => !o)}
            aria-label="expand works"
          >
            {open ? <IoChevronUp className="na-expand-icon" /> : <IoChevronDown className="na-expand-icon" />}
          </button>
        ) : (
          <span className="na-expand-placeholder" />
        )}

        <div className="na-entry-meta">
          <button
            className="na-name clickable"
            onClick={() => isFather && onFatherClick ? onFatherClick(entry.name) : onSearch(entry.name)}
          >
            {entry.name}{entry.dates ? ' (' + entry.dates + ')' : ''}
          </button>

          {entry.titles && entry.titles.length > 0 && (
            <span className="na-badges">
              {entry.titles.map(t => (
                <span key={t} className="na-badge">[{t}]</span>
              ))}
            </span>
          )}
          {entry.badge && (
            <span className={'na-badge na-badge--' + entry.badge.toLowerCase()}>
              [{entry.badge}]
            </span>
          )}
        </div>
      </div>

      {open && hasWorks && (
        <ul className="na-works">
          {entry.works.map((w, j) => (
            <li key={j} className="na-work">
              <button
                className="na-work-btn"
                onClick={() => onWorkClick ? onWorkClick(w) : onSearch(w)}
              >
                {w}
              </button>
            </li>
          ))}
        </ul>
      )}
    </li>
  )
}

/* ══════════════════════════════════════════════════
   TOP-LEVEL SECTION  (collapsible)
══════════════════════════════════════════════════ */
function Section({ section, onSearch, onFatherClick, onWorkClick }) {
  const [open, setOpen] = useState(false)
  const isFathers = section.id === 'fathers'

  return (
    <div className="na-section">
      <button className="na-section-btn" onClick={() => setOpen(o => !o)}>
        <span className="na-section-label">{section.title}</span>
        <span className="na-arrow">{open ? <IoChevronUp /> : <IoChevronDown />}</span>
      </button>

      {open && (
        <ul className="na-list">
          {section.entries.map((entry, i) => (
            <EntryRow
              key={i}
              entry={entry}
              isFather={isFathers}
              onSearch={onSearch}
              onFatherClick={onFatherClick}
              onWorkClick={onWorkClick}
            />
          ))}
        </ul>
      )}
    </div>
  )
}

/* ══════════════════════════════════════════════════
   APP
══════════════════════════════════════════════════ */
function App() {
  const [query, setQuery]             = useState('')
  const [results, setResults]         = useState([])
  const [searched, setSearched]       = useState(false)
  const [favorites, setFavorites]     = useState([])
  const [authorFilter, setAuthorFilter] = useState(null) // e.g. "Cyril of Jerusalem"
  const [topicQuery, setTopicQuery]   = useState('')     // query with author stripped out

  function doSearch(q, forceAuthor = undefined) {
    if (!q.trim()) return

    // detect author from query (unless sidebar click already set forceAuthor)
    const detected = forceAuthor !== undefined ? forceAuthor : detectAuthor(q)
    const topic    = detected ? stripAuthor(q, detected) : q

    setAuthorFilter(detected)
    setTopicQuery(topic || q)
    setQuery(q)

    let raw = searchFathers(topic || q)
    if (detected) {
      // filter results to only the matched author
      raw = raw.filter(r => r.father.name === detected)
    }
    setResults(raw)
    setSearched(true)
  }

  // called when user removes the author chip — re-run search without filter
  function clearAuthorFilter() {
    const newResults = searchFathers(topicQuery)
    setAuthorFilter(null)
    setResults(newResults)
  }

  // sidebar click: clicking a Father's name searches for them by author
  function onSidebarFatherClick(name) {
    setQuery(name)
    doSearch(name, name)
  }

  // sidebar click: clicking a work searches for that work title (no author filter)
  function onSidebarWorkClick(work) {
    setQuery(work)
    doSearch(work, null)
  }

  function goBack() {
    setSearched(false)
    setQuery('')
    setAuthorFilter(null)
    setTopicQuery('')
  }

  function toggleFavorite(key) {
    setFavorites(prev =>
      prev.includes(key) ? prev.filter(f => f !== key) : [...prev, key]
    )
  }

  const totalPassages = results.reduce((a, r) => a + r.works.length, 0)

  return (
    <div className="page">

      <header className="site-header">
        <h1 className="site-title">Ask the Church Fathers</h1>
        <p className="site-sub">Search the writings of the Early Church</p>
      </header>

      <section className="search-section">
        <div className="search-cross">♱</div>
        <div className="search-bar">
          <IoSearch className="search-icon" />
          <input
            className="search-input"
            type="text"
            placeholder="Search by topic, father, or keyword..."
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && doSearch(query)}
            autoFocus
          />
          <button className="search-btn" onClick={() => doSearch(query)}>Search</button>
        </div>
        <div className="suggestions">
          {SUGGESTIONS.map(s => (
            <button key={s} className="chip" onClick={() => doSearch(s)}>{s}</button>
          ))}
        </div>
      </section>

      <main className="main">

        {!searched && (
          <div className="landing">
            <div className="col-left">
              {SECTIONS_LEFT.map(s => (
                <Section
                  key={s.id}
                  section={s}
                  onSearch={doSearch}
                  onFatherClick={onSidebarFatherClick}
                  onWorkClick={onSidebarWorkClick}
                />
              ))}
            </div>
            <div className="col-right">
              {SECTIONS_RIGHT.map(s => (
                <Section
                  key={s.id}
                  section={s}
                  onSearch={doSearch}
                  onFatherClick={onSidebarFatherClick}
                  onWorkClick={onSidebarWorkClick}
                />
              ))}
            </div>
          </div>
        )}

        {searched && results.length === 0 && (
          <div className="empty">
            <p className="empty-title">No results for "<em>{query}</em>"</p>
            <p className="empty-hint">Try: Eucharist · baptism · prayer · fasting · martyrdom</p>
            <button className="back-btn" onClick={goBack}>Back</button>
          </div>
        )}

        {searched && results.length > 0 && (
          <>
            {/* ── Meta bar: count + active filter chip + back ── */}
            <div className="results-meta">
              <div className="results-meta-left">
                <span className="results-count">
                  {results.length} Father{results.length !== 1 ? 's' : ''} · {totalPassages} passage{totalPassages !== 1 ? 's' : ''}
                </span>
                {authorFilter && (
                  <span className="author-chip">
                    {authorFilter}
                    <button
                      className="author-chip-remove"
                      onClick={clearAuthorFilter}
                      title="Show all Fathers on this topic"
                    >
                      <IoClose />
                    </button>
                  </span>
                )}
              </div>
              <button className="back-btn" onClick={goBack}>Back</button>
            </div>

            {/* ── AI Synthesis panel (placeholder until Flask + Claude are live) ── */}
            <div className="synthesis-panel">
              <div className="synthesis-header">
                <span className="synthesis-label">✦ AI Synthesis</span>
                <span className="synthesis-badge">Coming soon</span>
              </div>
              <p className="synthesis-placeholder">
                When the backend is live, this panel will show what the Church Fathers
                collectively taught on <em>"{topicQuery || query}"</em>
                {authorFilter ? ` — filtered to ${authorFilter}` : ' — across all Fathers'}.
                Disagreements between Fathers will be shown explicitly, not resolved.
              </p>
            </div>

            {/* ── Passage results ── */}
            <div className="results-list">
              {results.map(({ father, works }) => (
                <div key={father.id} className="father-card">
                  <div className="card-header">
                    <div className="card-meta">
                      <div className="card-badges">
                        {father.titles.map(t => (
                          <span key={t} className="badge">[{t}]</span>
                        ))}
                      </div>
                      <h2 className="father-name">{father.name}</h2>
                      <p className="father-dates">{father.dates}</p>
                    </div>
                  </div>
                  <div className="passages">
                    {works.map((work, i) => {
                      const key = father.id + '-' + i
                      const fav = favorites.includes(key)
                      return (
                        <div key={key} className="passage">
                          <div className="passage-top">
                            <span className="work-title">{work.title}</span>
                            <button className="fav-btn" onClick={() => toggleFavorite(key)}>
                              {fav
                                ? <MdFavorite className="fav-filled" />
                                : <MdFavoriteBorder className="fav-empty" />}
                            </button>
                          </div>
                          <blockquote className="passage-quote">"{work.excerpt}"</blockquote>
                          <div className="passage-footer">
                            {work.newAdventUrl ? (
                              <a
                                className="read-more-btn"
                                href={work.newAdventUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                title={`Read full text of ${work.title} on New Advent`}
                              >
                                Read full text on New Advent ↗
                              </a>
                            ) : (
                              <button
                                className="read-more-btn"
                                onClick={() => onSidebarFatherClick(father.name)}
                              >
                                More from {father.name} →
                              </button>
                            )}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

      </main>

      <footer className="site-footer">
        <p className="footer-text">&#169; 2026 Ask the Church Fathers</p>
      </footer>

    </div>
  )
}

export default App
