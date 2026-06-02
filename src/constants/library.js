/** Alphabetically sorts an array of objects by their `name` property. */
const alpha = arr => [...arr].sort((a, b) => a.name.localeCompare(b.name))

/**
 * Complete library of Church Fathers with their dates, titles, and major works.
 * Sorted alphabetically by name.
 *
 * Each entry:
 * @typedef {{ name: string, dates: string, titles: string[], works: string[] }} FatherEntry
 */
export const ALL_FATHERS = alpha([
  { name: 'Alexander of Alexandria',   dates: 'd. 328',         titles: ['SAINT'],          works: ['Epistles on the Arian Heresy and the Deposition of Arius'] },
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
  { name: 'Cyril of Alexandria',       dates: '376-444',        titles: ['SAINT','DOCTOR'], works: ['That Christ is One', 'Against Diodore of Tarsus (Fragments)', 'Against Theodore of Mopsuestia (Fragments)', 'Against the Synousiasts (Fragments)', 'Commentary on John', 'Five Tomes Against Nestorius', 'Against Julian', 'Commentary on Luke', 'First Letter to Nestorius', 'Second Letter to Nestorius', 'Third Letter to Nestorius (with the Twelve Anathemas)', 'Letter to John of Antioch (Formula of Reunion)', 'First Letter to Succensus', 'Second Letter to Succensus', 'Scholia on the Incarnation'] },
  { name: 'Cyril of Jerusalem',        dates: 'c. 313-386',     titles: ['SAINT','DOCTOR'], works: ['Catechetical Lectures'] },
  { name: 'Dionysius of Rome',         dates: 'd. 268',         titles: ['SAINT'],          works: ['Against the Sabellians'] },
  { name: 'Dionysius the Great',       dates: 'c. 200-265',     titles: [],                 works: ['Epistles and Epistolary Fragments', 'Exegetical Fragments', 'Miscellaneous Fragments'] },
  { name: 'Epiphanius of Salamis',     dates: '310-403',        titles: ['SAINT'],          works: ['The Panarion (Excerpts)'] },
  { name: 'Ephraim the Syrian',        dates: '306-373',        titles: ['SAINT','DOCTOR'], works: ['Nisibene Hymns', 'Miscellaneous Hymns', 'Homilies'] },
  { name: 'Eusebius of Caesarea',      dates: 'c. 260-340',     titles: [],                 works: ['Church History', 'Life of Constantine', 'Oration in Praise of Constantine', 'On the Theophania', 'The Proof of the Gospel'] },
  { name: 'Firmilian of Caesarea',     dates: 'd. 268',         titles: [],                 works: ['Epistle to Cyprian'] },
  { name: 'Gregory of Nazianzus',      dates: '329-389',        titles: ['SAINT','DOCTOR'], works: ['Orations', 'Letters', 'On the Great Athanasius'] },
  { name: 'Gregory of Nyssa',          dates: 'c. 335-395',     titles: ['SAINT'],          works: ['On the Holy Spirit', 'On Virginity', 'Against Eunomius', 'On the Soul and Resurrection', 'On the Making of Man', 'The Great Catechism', 'On Pilgrimages'] },
  { name: 'Gregory Thaumaturgus',      dates: 'c. 213-270',     titles: ['SAINT'],          works: ['A Declaration of Faith', 'Metaphrase of the Book of Ecclesiastes', 'Oration and Panegyric Addressed to Origen', 'On the Trinity', 'On the Subject of the Soul', 'Canonical Epistle', 'Sectional Confession of Faith', 'Four Homilies'] },
  { name: 'Hermas',                    dates: 'fl. c. 140-155', titles: [],                 works: ['The Shepherd'] },
  { name: 'Hilary of Poitiers',        dates: 'c. 315-367',     titles: ['SAINT','DOCTOR'], works: ['On the Trinity', 'On the Councils', 'Homilies on the Psalms', 'Homily on Matthew'] },
  { name: 'Hippolytus of Rome',        dates: 'c. 170-235',     titles: ['SAINT'],          works: ['The Refutation of All Heresies', 'Treatise on Christ and Antichrist', 'Discourse on the Holy Theophany', 'Fragments', 'On the Apostolic Tradition'] },
  { name: 'Ignatius of Antioch',       dates: 'c. 35-107',      titles: ['SAINT'],          works: ['Epistle to the Ephesians', 'Epistle to the Magnesians', 'Epistle to the Trallians', 'Epistle to the Romans', 'Epistle to the Philadelphians', 'Epistle to the Smyrnaeans', 'Epistle to Polycarp'] },
  { name: 'Irenaeus of Lyons',         dates: 'c. 130-202',     titles: ['SAINT'],          works: ['Against Heresies', 'Proof of the Apostolic Preaching'] },
  { name: 'Jerome',                    dates: '347-420',        titles: ['SAINT','DOCTOR'], works: ['The Perpetual Virginity of Blessed Mary', 'The Life of Paulus the First Hermit', 'The Life of St. Hilarion', 'The Life of Malchus, the Captive Monk', 'Against Helvidius', 'Against Jovinianus', 'Against Vigilantius', 'Against the Pelagians', 'Prefaces to the Books of the Vulgate', 'Commentary on Matthew', 'Letters'] },
  { name: 'John Chrysostom',           dates: '347-407',        titles: ['SAINT','DOCTOR'], works: ['Homilies on the Gospel of Matthew', 'Homilies on the Gospel of John', 'Homilies on the Acts of the Apostles', 'Homilies on the Epistle to the Romans', 'Homilies on First Corinthians', 'Homilies on Second Corinthians', 'Homilies on Galatians', 'Homilies on Ephesians', 'Homilies on Philippians', 'Homilies on Colossians', 'Homilies on First and Second Thessalonians', 'Homilies on First and Second Timothy and Titus', 'Homilies on Philemon', 'Homilies on Hebrews', 'On the Priesthood', 'Instructions to Catechumens', 'Two Exhortations to Theodore After His Fall', 'Letters to Olympias', 'Homilies on the Statues'] },
  { name: 'Julius Africanus',          dates: 'c. 160-240',     titles: [],                 works: ['Extant Writings'] },
  { name: 'Justin Martyr',             dates: 'c. 100-165',     titles: ['SAINT'],          works: ['The First Apology', 'The Second Apology', 'Dialogue with Trypho', 'Discourse to the Greeks', 'Hortatory Address to the Greeks', 'On the Sole Government of God', 'Fragments of the Lost Work of Justin on the Resurrection', 'Other Fragments'] },
  { name: 'Lactantius',                dates: 'c. 250-325',     titles: [],                 works: ['The Divine Institutes', 'The Epitome of the Divine Institutes', 'On the Anger of God', 'On the Workmanship of God', 'On the Deaths of the Persecutors'] },
  { name: 'Macarius of Egypt',           dates: 'c. 300-391',     titles: [],                 works: ['Fifty Spiritual Homilies'] },
  { name: 'Leo the Great',             dates: 'c. 400-461',     titles: ['SAINT','DOCTOR'], works: ['Letters', 'Sermons'] },
  { name: 'Melito of Sardis',            dates: 'd. c. 180',      titles: ['SAINT'],          works: ['On Pascha'] },
  { name: 'Methodius',                 dates: 'd. c. 311',      titles: ['SAINT'],          works: ['The Banquet of the Ten Virgins', 'Concerning Free Will', 'From the Discourse on the Resurrection', 'Concerning Chastity', 'Oration on the Psalms', 'Oration Concerning Simeon and Anna'] },
  { name: 'Minucius Felix',            dates: 'fl. c. 200-240', titles: [],                 works: ['The Octavius'] },
  { name: 'Nicetas of Remesiana',      dates: 'c. 335-414',     titles: [],                 works: ['Writings'] },
  { name: 'Novatian',                  dates: 'c. 200-258',     titles: [],                 works: ['A Treatise of Novatian Concerning the Trinity', 'Treatise on the Jewish Meats', 'On the Advantages of Purity'] },
  { name: 'Origen',                    dates: 'c. 185-254',     titles: [],                 works: ['De Principiis', 'Against Celsus', 'Commentary on the Gospel of John', 'Commentary on the Gospel of Matthew', 'Epistle to Gregory', 'Exhortation to Martyrdom', 'On Prayer'] },
  { name: 'Papias',                    dates: 'c. 60-130',      titles: [],                 works: ['Fragments'] },
  { name: 'Peter of Alexandria',       dates: 'd. 311',         titles: ['SAINT'],          works: ['The Canonical Epistle', 'Fragments'] },
  { name: 'Polycarp of Smyrna',        dates: 'c. 69-155',      titles: ['SAINT'],          works: ['Epistle to the Philippians', 'The Martyrdom of Polycarp'] },
  { name: 'Sulpitius Severus',         dates: 'c. 363-c. 425',  titles: [],                 works: ['The Sacred History of Sulpitius Severus', 'Life of St. Martin', 'The Letters of Sulpitius Severus', 'The Dialogues of Sulpitius Severus'] },
  { name: 'Tatian the Assyrian',       dates: 'c. 120-180',     titles: [],                 works: ['Address to the Greeks'] },
  { name: 'Tertullian',                dates: 'c. 155-220',     titles: [],                 works: ['The Apology', 'The Shows, or De Spectaculis', 'The Chaplet, or De Corona', 'To the Martyrs', 'To Scapula', 'Ad Nationes', 'Against the Jews', 'Against Marcion', 'Against Hermogenes', 'Against the Valentinians', 'Against Praxeas', 'On the Prescription of Heretics', 'A Treatise on the Soul', 'On the Resurrection of the Flesh', 'On Baptism', 'On Repentance', 'On Prayer', 'To His Wife', 'On Exhortation to Chastity', 'On Monogamy', 'On Modesty', 'On Fasting', 'On the Pallium', 'On the Veiling of Virgins', 'On the Apparel of Women', 'On Female Fashion', 'On Idolatry', 'Scorpiace', 'On Patience', 'On Flight in Persecution'] },
  { name: 'Theodoret of Cyrrhus',      dates: 'c. 393-457',     titles: [],                 works: ['Ecclesiastical History', 'Dialogues', 'Against Heresies'] },
  { name: 'Theophilus of Antioch',     dates: 'd. c. 183',      titles: [],                 works: ['Theophilus to Autolycus'] },
  { name: 'Vincent of Lérins',         dates: 'd. c. 445',      titles: [],                 works: ['The Commonitory'] },
])

/**
 * Accordion sections for the right column of the library catalog.
 * Each section has clickable entries that trigger a search query.
 */
export const RIGHT_SECTIONS = [
  {
    id: 'liturgies',
    title: 'Liturgies',
    entries: [
      { title: 'Liturgy of St. James',           query: 'Liturgy of St. James' },
      { title: 'Liturgy of St. Mark',            query: 'Liturgy of St. Mark' },
      { title: 'Liturgy of St. Basil',           query: 'Liturgy of St. Basil' },
      { title: 'Liturgy of St. John Chrysostom', query: 'Liturgy of St. John Chrysostom' },
      { title: 'Apostolic Constitutions',        query: 'Apostolic Constitutions' },
      { title: 'Didache — Eucharistic Prayers',  query: 'Didache eucharist' },
    ],
  },
  {
    id: 'councils',
    title: 'Councils',
    entries: [
      { title: 'Council of Nicaea (325)',          query: 'Nicaea Trinity homoousios' },
      { title: 'Council of Constantinople (381)',  query: 'Constantinople Holy Spirit creed' },
      { title: 'Council of Ephesus (431)',         query: 'Ephesus Theotokos Mary' },
      { title: 'Council of Chalcedon (451)',       query: 'Chalcedon two natures Christ' },
    ],
  },
  {
    id: 'apocrypha',
    title: 'Apocrypha',
    entries: [
      { title: 'Protoevangelium of James',      query: 'Protoevangelium of James' },
      { title: 'Shepherd of Hermas',            query: 'Shepherd of Hermas' },
      { title: 'Epistle of Barnabas',           query: 'Epistle of Barnabas' },
      { title: '1 Clement',                     query: '1 Clement' },
    ],
  },
  {
    id: 'misc',
    title: 'Miscellaneous',
    entries: [
      { title: 'Didache',                          query: 'Didache' },
      { title: 'Apostolic Tradition (Hippolytus)', query: 'Apostolic Tradition' },
      { title: 'Letter to Diognetus',             query: 'Diognetus' },
      { title: "Apostles' Creed",                  query: 'Apostles Creed' },
      { title: 'Nicene Creed',                     query: 'Nicene Creed' },
      { title: 'Athanasian Creed',                 query: 'Athanasian Creed' },
      { title: 'Martyrdom of Polycarp',            query: 'Martyrdom of Polycarp' },
    ],
  },
]
