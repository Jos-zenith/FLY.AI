import { useEffect, useMemo, useState } from 'react'

const API_URL = 'http://localhost:8000'

function App() {
  const [summary, setSummary] = useState({ total_events: 0, applications: [] })
  const [usageEvents, setUsageEvents] = useState([])
  const [analytics, setAnalytics] = useState({
    usage_over_time: [],
    model_usage: [],
    asset_comparison: [],
    token_usage: { input_tokens: 0, output_tokens: 0, total_tokens: 0 },
    latency: { avg_latency_ms: 0, samples: 0 },
    failure_rate: { failed: 0, total: 0, rate: 0 },
    agent_run_durations: [],
  })
  const [piiSummary, setPiiSummary] = useState({})
  const [promptRows, setPromptRows] = useState([])
  const [agentRuns, setAgentRuns] = useState([])
  const [promptSearch, setPromptSearch] = useState('')
  const [promptAsset, setPromptAsset] = useState('')
  const [promptHasPii, setPromptHasPii] = useState(false)
  const [message, setMessage] = useState('Contact me at alice@example.com or 555-123-4567')
  const [response, setResponse] = useState(null)

  const loadOverview = async () => {
    try {
      const [summaryResp, usageResp, analyticsResp, piiResp, runsResp] = await Promise.all([
        fetch(`${API_URL}/dashboard/summary`).then((res) => res.json()),
        fetch(`${API_URL}/dashboard/usage`).then((res) => res.json()),
        fetch(`${API_URL}/dashboard/analytics`).then((res) => res.json()),
        fetch(`${API_URL}/dashboard/prompts/pii-summary`).then((res) => res.json()),
        fetch(`${API_URL}/dashboard/runs?limit=25`).then((res) => res.json()),
      ])
      setSummary(summaryResp)
      setUsageEvents(usageResp)
      setAnalytics(analyticsResp)
      setPiiSummary(piiResp)
      setAgentRuns(runsResp)
    } catch (error) {
      console.error(error)
    }
  }

  const loadPrompts = async () => {
    try {
      const params = new URLSearchParams()
      if (promptSearch) params.set('search', promptSearch)
      if (promptAsset) params.set('ai_asset', promptAsset)
      if (promptHasPii) params.set('has_pii', 'true')

      const rows = await fetch(`${API_URL}/dashboard/prompts?${params.toString()}`).then((res) => res.json())
      setPromptRows(rows)
    } catch (error) {
      console.error(error)
    }
  }

  useEffect(() => {
    loadOverview()
    loadPrompts()
  }, [])

  useEffect(() => {
    loadPrompts()
  }, [promptSearch, promptAsset, promptHasPii])

  const handleSubmit = async () => {
    const res = await fetch(`${API_URL}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, user_id: 'u-123', session_id: 's-456' }),
    })
    const data = await res.json()
    setResponse(data)
    loadOverview()
    loadPrompts()
  }

  const requestCounts = useMemo(() => {
    const counts = {}
    for (const row of promptRows) {
      counts[row.ai_asset] = (counts[row.ai_asset] || 0) + 1
    }
    return Object.entries(counts)
      .map(([asset, count]) => ({ asset, count }))
      .sort((a, b) => b.count - a.count)
  }, [promptRows])

  const piiCounts = useMemo(() => {
    const counts = {}
    for (const [asset, labels] of Object.entries(piiSummary)) {
      counts[asset] = Object.values(labels || {}).reduce((total, value) => total + Number(value || 0), 0)
    }
    return counts
  }, [piiSummary])

  return (
    <div className="dashboard-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">AI observability dashboard</p>
          <h1>AI Usage Monitor</h1>
          <p>
            Track request trends, model usage, token volume, latency, failures, asset comparisons,
            and declared-vs-observed governance gaps in one place.
          </p>
        </div>
        <button onClick={loadOverview}>Refresh data</button>
      </header>

      <section className="summary-grid">
        <div className="card metric-card">
          <span>Total events</span>
          <strong>{summary.total_events}</strong>
        </div>
        <div className="card metric-card">
          <span>Applications</span>
          <strong>{summary.applications.join(', ') || 'None'}</strong>
        </div>
        <div className="card metric-card">
          <span>Prompt rows</span>
          <strong>{promptRows.length}</strong>
        </div>
        <div className="card metric-card">
          <span>Agent runs</span>
          <strong>{agentRuns.length}</strong>
        </div>
      </section>

      <section className="summary-grid analytics-grid">
        <div className="card metric-card">
          <span>Total tokens</span>
          <strong>{analytics.token_usage.total_tokens}</strong>
        </div>
        <div className="card metric-card">
          <span>Avg latency</span>
          <strong>{Math.round(analytics.latency.avg_latency_ms || 0)} ms</strong>
        </div>
        <div className="card metric-card">
          <span>Failure rate</span>
          <strong>{analytics.failure_rate.rate || 0}%</strong>
        </div>
        <div className="card metric-card">
          <span>Assets tracked</span>
          <strong>{analytics.asset_comparison.length}</strong>
        </div>
      </section>

      <section className="grid-two">
        <div className="card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Usage overview</p>
              <h2>Requests and PII by asset</h2>
            </div>
          </div>
          <div className="chart-list">
            {(analytics.asset_comparison.length ? analytics.asset_comparison : requestCounts).map((row) => {
              const assetName = row.asset || row.name || row.ai_asset || 'unknown'
              const requests = row.requests || row.count || 0
              const piiHits = row.pii_events || piiCounts[assetName] || 0
              return (
                <div key={assetName} className="chart-row">
                  <div className="chart-labels">
                    <span>{assetName}</span>
                    <small>{requests} requests · {piiHits} PII hits</small>
                  </div>
                  <div className="bars">
                    <div className="bar request" style={{ width: `${Math.min(100, requests * 12)}%` }} />
                    <div className="bar pii" style={{ width: `${Math.min(100, piiHits * 12)}%` }} />
                  </div>
                </div>
              )
            })}
            {!analytics.asset_comparison.length && !requestCounts.length && <p className="muted">No prompt traffic yet.</p>}
          </div>
        </div>

        <div className="card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">PII governance</p>
              <h2>PII detection frequency</h2>
            </div>
          </div>
          <div className="governance-list">
            {Object.entries(piiSummary).map(([asset, labels]) => {
              const total = Object.values(labels || {}).reduce((sum, value) => sum + Number(value || 0), 0)
              return (
                <div key={asset} className="governance-row">
                  <div>
                    <strong>{asset}</strong>
                    <small>{total} detections</small>
                  </div>
                  <div className="label-pills">
                    {Object.entries(labels || {}).map(([label, value]) => (
                      <span key={label} className="pill">
                        {label} {value}
                      </span>
                    ))}
                  </div>
                </div>
              )
            })}
            {!Object.keys(piiSummary).length && <p className="muted">No PII detections yet.</p>}
          </div>
        </div>
      </section>

      <section className="grid-two analytics-panels">
        <div className="card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Trend analysis</p>
              <h2>Usage over time</h2>
            </div>
          </div>
          <div className="chart-list">
            {analytics.usage_over_time.map((day) => (
              <div key={day.date} className="chart-row compact-row">
                <div className="chart-labels">
                  <span>{day.date}</span>
                  <small>{day.requests} requests · {day.total_tokens} tokens</small>
                </div>
                <div className="bars">
                  <div className="bar request" style={{ width: `${Math.min(100, (day.requests / Math.max(...analytics.usage_over_time.map((item) => item.requests), 1)) * 100)}%` }} />
                </div>
              </div>
            ))}
            {!analytics.usage_over_time.length && <p className="muted">No trend data yet.</p>}
          </div>
        </div>

        <div className="card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Model analytics</p>
              <h2>Model usage</h2>
            </div>
          </div>
          <div className="governance-list">
            {analytics.model_usage.map((model) => (
              <div key={model.model} className="governance-row">
                <div>
                  <strong>{model.model}</strong>
                  <small>{model.requests} requests</small>
                </div>
                <div className="label-pills">
                  <span className="pill">{model.input_tokens} in</span>
                  <span className="pill">{model.output_tokens} out</span>
                  <span className="pill">{Math.round(model.avg_latency_ms || 0)} ms</span>
                </div>
              </div>
            ))}
            {!analytics.model_usage.length && <p className="muted">No model data yet.</p>}
          </div>
        </div>
      </section>

      <section className="grid-two analytics-panels">
        <div className="card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Operational health</p>
              <h2>Failure rate and latency</h2>
            </div>
          </div>
          <div className="governance-list">
            <div className="governance-row">
              <div>
                <strong>Failure rate</strong>
                <small>{analytics.failure_rate.failed} of {analytics.failure_rate.total} requests</small>
              </div>
              <div className="label-pills">
                <span className="pill">{analytics.failure_rate.rate}%</span>
              </div>
            </div>
            <div className="governance-row">
              <div>
                <strong>Average latency</strong>
                <small>{analytics.latency.samples} samples</small>
              </div>
              <div className="label-pills">
                <span className="pill">{Math.round(analytics.latency.avg_latency_ms || 0)} ms</span>
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Runner health</p>
              <h2>Agent execution duration</h2>
            </div>
          </div>
          <div className="governance-list">
            {analytics.agent_run_durations.map((run) => (
              <div key={run.agent_id} className="governance-row">
                <div>
                  <strong>{run.agent_id}</strong>
                  <small>{run.runs} runs</small>
                </div>
                <div className="label-pills">
                  <span className="pill">{run.avg_seconds}s avg</span>
                  <span className="pill">{run.completed} complete</span>
                  <span className="pill">{run.failed} failed</span>
                </div>
              </div>
            ))}
            {!analytics.agent_run_durations.length && <p className="muted">No agent runs recorded yet.</p>}
          </div>
        </div>
      </section>

      <section className="card">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Prompt browse</p>
            <h2>Sanitized prompts</h2>
          </div>
        </div>
        <div className="filters">
          <input
            value={promptSearch}
            onChange={(e) => setPromptSearch(e.target.value)}
            placeholder="Search sanitized prompts"
          />
          <input
            value={promptAsset}
            onChange={(e) => setPromptAsset(e.target.value)}
            placeholder="Filter by asset"
          />
          <label className="checkbox">
            <input
              type="checkbox"
              checked={promptHasPii}
              onChange={(e) => setPromptHasPii(e.target.checked)}
            />
            Only PII-bearing prompts
          </label>
        </div>
        <div className="prompt-grid">
          {promptRows.map((row) => (
            <article key={row.id} className="prompt-row">
              <div className="prompt-topline">
                <strong>{row.ai_asset}</strong>
                <span>{row.model || 'unknown model'}</span>
              </div>
              <p>{row.sanitized_prompt || 'No prompt text stored'}</p>
              <div className="label-pills">
                {Object.entries(row.pii_detected || {}).map(([label, value]) => (
                  <span key={label} className="pill">
                    {label} {value}
                  </span>
                ))}
              </div>
            </article>
          ))}
          {!promptRows.length && <p className="muted">No matching prompt logs.</p>}
        </div>
      </section>

      <section className="card">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Agent runs</p>
            <h2>Declared vs observed</h2>
          </div>
        </div>
        <div className="runs-table">
          {agentRuns.map((run) => (
            <div key={run.run_id} className={`run-row ${run.governance_alert ? 'alert' : ''}`}>
              <div className="run-meta">
                <strong>{run.agent_id || 'agent'}</strong>
                <span>{run.status}</span>
              </div>
              <div>
                <div className="run-line"><span>Declared</span><strong>{(run.declared || []).join(', ') || 'None'}</strong></div>
                <div className="run-line"><span>Observed</span><strong>{(run.observed || []).join(', ') || 'None'}</strong></div>
                <div className="run-line"><span>Tools</span><strong>{(run.tools_invoked || []).join(', ') || 'None'}</strong></div>
              </div>
              <div className="run-badges">
                {run.governance_alert ? <span className="badge danger">Mismatch</span> : <span className="badge ok">Aligned</span>}
                {!!(run.unexpected || []).length && <span className="badge danger-soft">{run.unexpected.join(', ')}</span>}
              </div>
            </div>
          ))}
          {!agentRuns.length && <p className="muted">No agent runs yet.</p>}
        </div>
      </section>

      <section className="card">
        <h2>PII test input</h2>
        <textarea value={message} onChange={(e) => setMessage(e.target.value)} />
        <button onClick={handleSubmit}>Run monitor</button>
        {response && <pre>{JSON.stringify(response, null, 2)}</pre>}
      </section>

      <section className="card">
        <h2>Recent usage</h2>
        <ul className="usage-list">
          {usageEvents.map((event) => (
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