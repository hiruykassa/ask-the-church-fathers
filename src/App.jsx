import './App.css'
import { useState } from 'react'

function App() {
  const [query, setQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])

  const results = [
    {
      father: "Saint Augustine",
      source: "Confessions, Book I",
      quote: "Our heart is restless, until it repose in Thee."
    },
    {
      father: "Saint John Chrysostom",
      source: "Homilies on Matthew",
      quote: "Prayer is the place of refuge for every worry."
    },
    {
      father: "Saint Athanasius",
      source: "On the Incarnation",
      quote: "God became man so that man might become God."
    }
  ]

  function handleSearch() {
    const filtered = results.filter((result) => {
      return result.quote.toLowerCase().includes(query.toLowerCase())
    })
    setSearchResults(filtered)
  }

  return (
    <div className='container'>
      <h1>Ask the Church Fathers</h1>
      <p className='cross'>☦</p>
      <p className='subtitle'>Wisdom from the Early Church Fathers</p>
      <input
        type="text"
        placeholder="Ask a question for the Church Fathers..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <button onClick={handleSearch}>Submit</button>

      {searchResults.map((result) => (
        <div key={result.father} className='card'>
          <h2>{result.father}</h2>
          <p>{result.source}</p>
          <p>{result.quote}</p>
        </div>
      ))}
    </div>
  ) 
}

export default App