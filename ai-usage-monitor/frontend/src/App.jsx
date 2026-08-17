import { useEffect, useState } from 'react'

const API_URL = 'http://localhost:8000'

function App() {
  const [metrics, setMetrics] = useState({ total_events: 0, applications: [] })
  const [events, setEvents] = useState([])
  const [message, setMessage] = useState('Contact me at alice@example.com or 555-123-4567')
  const [response, setResponse] = useState(null)

  const loadData = async () => {
    try {
      const summary = await fetch(`${API_URL}/dashboard/summary`).then((res) => res.json())
      const usage = await fetch(`${API_URL}/dashboard/usage`).then((res) => res.json())
      setMetrics(summary)
      setEvents(usage)
    } catch (err) {
      console.error(err)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleSubmit = async () => {
    const res = await fetch(`${API_URL}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, user_id: 'u-123', session_id: 's-456' }),
    })
    const data = await res.json()
    setResponse(data)
    loadData()
  }

  return (
    <div className="dashboard-shell">
      <header>
        <h1>AI Usage Monitor</h1>
        <p>Track AI usage, detect PII, and review declared vs observed tools.</p>
      </header>

      <section className="summary-grid">
        <div className="card">
          <span>Total events</span>
          <strong>{metrics.total_events}</strong>
        </div>
        <div className="card">
          <span>Applications</span>
          <strong>{metrics.applications.join(', ') || 'None'}</strong>
        </div>
      </section>

      <section className="card">
        <h2>PII test input</h2>
        <textarea value={message} onChange={(e) => setMessage(e.target.value)} />
        <button onClick={handleSubmit}>Run monitor</button>
        {response && (
          <pre>{JSON.stringify(response, null, 2)}</pre>
        )}
      </section>

      <section className="card">
        <h2>Recent usage</h2>
        <ul>
          {events.map((event) => (
            <li key={event.id}>
              <span>{event.application}</span>
              <span>{event.event_type}</span>
              <small>{event.created_at}</small>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}

export default App
