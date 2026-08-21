import { useEffect, useMemo, useState } from 'react'
import { ChatHero } from './components/ChatHero.jsx'
import { Sidebar } from './components/Sidebar.jsx'
import { OverviewView } from './components/views/OverviewView.jsx'
import { AnalyticsView } from './components/views/AnalyticsView.jsx'
import { PromptsView } from './components/views/PromptsView.jsx'
import { RunsView } from './components/views/RunsView.jsx'

const API_URL = 'http://localhost:8000'

const VIEW_META = {
  overview: {
    title: 'AI Usage Monitor',
    description: 'Live snapshot of every prompt, leak, and agent action this monitor has caught.',
  },
  analytics: {
    title: 'Analytics',
    description: 'Trends, model load, and response health over time.',
  },
  prompts: {
    title: 'Prompts',
    description: 'Every captured prompt, sanitized and searchable.',
  },
  runs: {
    title: 'Agent Runs',
    description: 'Declared scope vs. what each agent actually touched.',
  },
}

function App() {
  const [stage, setStage] = useState('hero') // 'hero' | 'dashboard'
  const [activeView, setActiveView] = useState('overview')
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
  const [promptLimit, setPromptLimit] = useState(20)
  const [lastResult, setLastResult] = useState(null)
  const [apiError, setApiError] = useState('')
  const [sessionCaught, setSessionCaught] = useState(0)
  const [usageAssetFilter, setUsageAssetFilter] = useState('')

  const readJsonResponse = async (res) => {
    const body = await res.json().catch(() => ({}))
    if (!res.ok) {
      const detail = body?.detail || body?.error || 'Request failed'
      throw new Error(detail)
    }
    return body
  }

  const loadOverview = async () => {
    try {
      setApiError('')
      const [summaryResp, usageResp, analyticsResp, piiResp, runsResp] = await Promise.all([
        fetch(`${API_URL}/dashboard/summary`).then(readJsonResponse),
        fetch(`${API_URL}/dashboard/usage`).then(readJsonResponse),
        fetch(`${API_URL}/dashboard/analytics`).then(readJsonResponse),
        fetch(`${API_URL}/dashboard/prompts/pii-summary`).then(readJsonResponse),
        fetch(`${API_URL}/dashboard/runs?limit=25`).then(readJsonResponse),
      ])
      setSummary(summaryResp)
      setUsageEvents(usageResp)
      setAnalytics(analyticsResp)
      setPiiSummary(piiResp)
      setAgentRuns(runsResp)
    } catch (error) {
      console.error(error)
      setApiError(error.message || 'The dashboard could not load data from the API.')
    }
  }

  const loadPrompts = async () => {
    try {
      // Deliberately does NOT clear apiError on entry: this runs alongside
      // loadOverview (sequentially in handleChatSubmit, in parallel from the
      // stage-change effect), and a successful prompts fetch here shouldn't
      // silently wipe out an error loadOverview just surfaced.
      const params = new URLSearchParams()
      if (promptSearch) params.set('search', promptSearch)
      if (promptAsset) params.set('ai_asset', promptAsset)
      if (promptHasPii) params.set('has_pii', 'true')
      params.set('limit', String(promptLimit))

      const rows = await fetch(`${API_URL}/dashboard/prompts?${params.toString()}`).then(readJsonResponse)
      setPromptRows(rows)
    } catch (error) {
      console.error(error)
      setApiError(error.message || 'The prompt feed could not be loaded.')
    }
  }

  useEffect(() => {
    if (stage === 'dashboard') {
      loadOverview()
      loadPrompts()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stage])

  useEffect(() => {
    if (stage === 'dashboard') loadPrompts()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [promptSearch, promptAsset, promptHasPii, promptLimit])

  const handleChatSubmit = async (message, asset) => {
    const res = await fetch(`${API_URL}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, ai_asset: asset, user_id: 'u-123', session_id: 's-456' }),
    })
    const data = await readJsonResponse(res)
    setLastResult(data)
    const caughtNow = Object.values(data.pii_metadata || {}).reduce((sum, n) => sum + Number(n || 0), 0)
    if (caughtNow) setSessionCaught((prev) => prev + caughtNow)
    setStage('dashboard')
    setActiveView('overview')
    await loadOverview()
    await loadPrompts()
  }

  const startNewChat = () => {
    setLastResult(null)
    setStage('hero')
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

  const sidebarStats = useMemo(
    () => ({
      totalPrompts: promptRows.length,
      totalPiiEvents: Object.values(piiCounts).reduce((sum, value) => sum + value, 0),
      governanceAlerts: agentRuns.filter((run) => run.governance_alert).length,
    }),
    [promptRows, piiCounts, agentRuns],
  )

  if (stage === 'hero') {
    return (
      <ChatHero
        onSubmit={handleChatSubmit}
        assetOptions={['customer-support', 'chat', 'billing-agent']}
        sessionCaught={sessionCaught}
      />
    )
  }

  const viewMeta = VIEW_META[activeView] || VIEW_META.overview

  return (
    <div className="app-shell">
      <Sidebar activeView={activeView} onNavigate={setActiveView} onNewChat={startNewChat} stats={sidebarStats} />

      <main className="app-main">
        <div className="app-main-inner">
          <header className="hero">
            <div>
              <h1>{viewMeta.title}</h1>
              <p>{viewMeta.description}</p>
            </div>
            <button
              className="btn-3d hero-refresh"
              onClick={loadOverview}
              title="Reload the latest captured data from the monitor"
            >
              Refresh
            </button>
          </header>

          {apiError ? <div role="alert" className="error-banner">{apiError}</div> : null}

          {activeView === 'overview' && (
            <OverviewView
              summary={summary}
              analytics={analytics}
              promptRows={promptRows}
              agentRuns={agentRuns}
              requestCounts={requestCounts}
              piiSummary={piiSummary}
              piiCounts={piiCounts}
              usageEvents={usageEvents}
              lastResult={lastResult}
              usageAssetFilter={usageAssetFilter}
              setUsageAssetFilter={setUsageAssetFilter}
              onNavigate={setActiveView}
            />
          )}

          {activeView === 'analytics' && <AnalyticsView analytics={analytics} />}

          {activeView === 'prompts' && (
            <PromptsView
              promptRows={promptRows}
              promptSearch={promptSearch}
              setPromptSearch={setPromptSearch}
              promptAsset={promptAsset}
              setPromptAsset={setPromptAsset}
              promptHasPii={promptHasPii}
              setPromptHasPii={setPromptHasPii}
              promptLimit={promptLimit}
              onLoadMore={() => setPromptLimit((n) => n + 20)}
            />
          )}

          {activeView === 'runs' && <RunsView agentRuns={agentRuns} />}
        </div>
      </main>
    </div>
  )
}

export default App
