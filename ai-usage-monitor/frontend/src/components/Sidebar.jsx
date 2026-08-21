import { lazy, Suspense } from 'react'
import { LayoutDashboard, BarChart3, MessageSquare, GitBranch, ShieldAlert, MessageSquarePlus, Database } from 'lucide-react'

// three.js is a ~600KB dependency and this orb is purely decorative, so it's
// code-split out of the main bundle and streamed in after first paint
// instead of blocking the dashboard's initial load.
const ParticleOrb = lazy(() => import('./ParticleOrb.jsx').then((m) => ({ default: m.ParticleOrb })))

const NAV_ITEMS = [
  {
    id: 'overview',
    label: 'Overview',
    desc: 'Everything captured so far, at a glance',
    icon: LayoutDashboard,
  },
  {
    id: 'analytics',
    label: 'Analytics',
    desc: 'Usage trends, model load, latency, failures',
    icon: BarChart3,
  },
  {
    id: 'prompts',
    label: 'Prompts',
    desc: 'Every sanitized prompt, searchable',
    icon: MessageSquare,
  },
  {
    id: 'runs',
    label: 'Agent Runs',
    desc: 'Did each AI agent stay within scope?',
    icon: GitBranch,
  },
  {
    id: 'assets',
    label: 'AI Assets',
    desc: 'Declared purpose, data sources, and monitoring per tool',
    icon: Database,
  },
]

export function Sidebar({ activeView, onNavigate, onNewChat, stats }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <Suspense fallback={<div className="orb-glow-fallback" style={{ width: 40, height: 40 }} aria-hidden="true" />}>
          <ParticleOrb size={40} />
        </Suspense>
        <div>
          <span className="sidebar-title">AI Usage Monitor</span>
          <span className="sidebar-subtitle">Catches leaks in AI prompts, in real time</span>
        </div>
      </div>

      <div className="sidebar-new-chat">
        <button
          type="button"
          className="sidebar-new-chat-btn btn-3d"
          onClick={onNewChat}
          title="Go back and send another prompt through the monitor"
        >
          <MessageSquarePlus size={16} strokeWidth={2} aria-hidden="true" />
          New prompt
        </button>
      </div>

      <nav className="sidebar-nav">
        <span className="sidebar-nav-label">Views</span>
        {NAV_ITEMS.map(({ id, label, desc, icon: Icon }) => (
          <button
            key={id}
            type="button"
            className={`sidebar-nav-item btn-3d${activeView === id ? ' active' : ''}`}
            onClick={() => onNavigate(id)}
            aria-current={activeView === id ? 'page' : undefined}
            title={desc}
          >
            <Icon className="sidebar-nav-icon" size={16} strokeWidth={2} aria-hidden="true" />
            <span className="sidebar-nav-text">
              <span className="sidebar-nav-label-text">{label}</span>
              <span className="sidebar-nav-desc">{desc}</span>
            </span>
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="card-3d sidebar-status-card">
          <div className="sidebar-status-icon">
            <ShieldAlert size={18} strokeWidth={2} aria-hidden="true" />
          </div>
          <div className="sidebar-status-body">
            <h4>Agent behavior status</h4>
            <p>
              {stats.governanceAlerts > 0
                ? `${stats.governanceAlerts} agent run${stats.governanceAlerts === 1 ? '' : 's'} did something outside its approved scope`
                : 'Every agent run so far stayed within what it was approved to do'}
            </p>
          </div>
          <div className="sidebar-status-metrics">
            <span>
              <strong>{stats.totalPrompts}</strong> prompts captured
            </span>
            <span>
              <strong>{stats.totalPiiEvents}</strong> pieces of PII caught
            </span>
          </div>
        </div>
      </div>
    </aside>
  )
}
