import { useEffect, useState } from 'react'

const API_URL = 'http://localhost:8000'

function App() {
  const [items, setItems] = useState([])
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [error, setError] = useState('')

  const loadItems = async () => {
    try {
      const response = await fetch(`${API_URL}/items`)
      if (!response.ok) throw new Error('Failed to fetch items')
      const data = await response.json()
      setItems(data)
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => {
    loadItems()
  }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      const response = await fetch(`${API_URL}/items`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, description }),
      })

      if (!response.ok) throw new Error('Failed to create item')
      setName('')
      setDescription('')
      await loadItems()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="app-shell">
      <h1>Betty</h1>
      <p className="subtitle">FastAPI + React + PostgreSQL starter</p>

      <form onSubmit={handleSubmit} className="item-form">
        <input
          type="text"
          placeholder="Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <textarea
          placeholder="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <button type="submit">Add item</button>
      </form>

      {error && <p className="error">{error}</p>}

      <ul className="items-list">
        {items.map((item) => (
          <li key={item.id}>
            <strong>{item.name}</strong>
            {item.description && <span>{item.description}</span>}
          </li>
        ))}
      </ul>
    </div>
  )
}

export default App
