import {
  CheckCircle2,
  AlertTriangle,
  Activity,
  Boxes,
  MessagesSquare,
  GitBranch,
  Cpu,
  Gauge,
  Layers,
  ArrowRight as ArrowRightIcon,
} from 'lucide-react'
import { useCountUp } from '../../hooks/useCountUp.js'
import { Bar } from '../charts/Bar.jsx'
import { Donut } from '../charts/Donut.jsx'
import { splitSanitizedText } from '../../lib/piiPreview.js'

function Metric({ icon: Icon, label, value }) {
  const display = useCountUp(value)
  return (
    <div className="card metric-card card-3d">
      <div className="metric-card-icon">
        <Icon size={16} strokeWidth={2} aria-hidden="true" />
      </div>
      <span>{label}</span>
      <strong>{display}</strong>
    </div>
  )
}

function SanitizedText({ text }) {
  const parts = splitSanitizedText(text)
  return (
    <>
      {parts.map((part, i) =>
        part.type === 'token' ? (
          <span key={i} className="pii-token" title={`${part.value} was detected and redacted here`}>
            {`<${part.value}>`}
          </span>
        ) : (
          <span key={i}>{part.value}</span>
        ),
      )}
    </>
  )
}

export function OverviewView({
  summary,
  analytics,
  promptRows,
  agentRuns,
  requestCounts,
  piiSummary,
  piiCounts,
  usageEvents,
  lastResult,
  usageAssetFilter,
  setUsageAssetFilter,
  onNavigate,
}) {
  const piiHits = Object.keys(lastResult?.pii_metadata || {}).length

  const assetRows = (analytics.asset_comparison.length ? analytics.asset_comparison : requestCounts).map((row) => {
    const assetName = row.asset || row.name || row.ai_asset || 'unknown'
    return {
      assetName,
      requests: row.requests || row.count || 0,
      pii: row.pii_events || piiCounts[assetName] || 0,
    }
  })
  const maxRequests = Math.max(...assetRows.map((r) => r.requests), 1)

  const piiTotals = {}
  Object.values(piiSummary).forEach((labels) => {
    Object.entries(labels || {}).forEach(([label, value]) => {
      piiTotals[label] = (piiTotals[label] || 0) + Number(value || 0)
    })
  })
  const donutSegments = Object.entries(piiTotals)
    .sort((a, b) => b[1] - a[1])
    .map(([label, value]) => ({ label, value }))

  const usageAssets = [...new Set(usageEvents.map((e) => e.application))].sort()
  const filteredUsage = usageAssetFilter
    ? usageEvents.filter((e) => e.application === usageAssetFilter)
    : usageEvents

  return (
    <>
      {lastResult && (
        <section className="card card-3d just-captured">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Just captured</p>
              <h2>What the monitor saw</h2>
            </div>
            <span className={`just-captured-status ${piiHits ? 'warn' : 'clean'}`}>
              {piiHits ? <AlertTriangle size={14} strokeWidth={2} /> : <CheckCircle2 size={14} strokeWidth={2} />}
              {piiHits ? `${piiHits} PII type${piiHits === 1 ? '' : 's'} caught` : 'Clean'}
            </span>
          </div>
          <p className="just-captured-sanitized">
            <SanitizedText text={lastResult.message || 'No prompt text stored'} />
          </p>
          <div className="label-pills">
            {Object.entries(lastResult.pii_metadata || {}).map(([label, value]) => (
              <span key={label} className="pill warn">
                {label} {value}
              </span>
            ))}
            {!piiHits && <span className="pill clean">No PII detected</span>}
          </div>
          {onNavigate && (
            <button type="button" className="just-captured-next" onClick={() => onNavigate('runs')}>
              Next: see if an agent stayed in scope for this kind of request
              <ArrowRightIcon size={14} strokeWidth={2.2} aria-hidden="true" />
            </button>
          )}
        </section>
      )}

      <section className="summary-grid">
        <Metric icon={Activity} label="Total events" value={summary.total_events} />
        <div className="card metric-card card-3d">
          <div className="metric-card-icon">
            <Boxes size={16} strokeWidth={2} aria-hidden="true" />
          </div>
          <span>Applications</span>
          <strong className="metric-card-text">{summary.applications.join(', ') || 'None yet'}</strong>
        </div>
        <Metric icon={MessagesSquare} label="Prompt rows" value={promptRows.length} />
        <Metric icon={GitBranch} label="Agent runs" value={agentRuns.length} />
      </section>

      <section className="summary-grid analytics-grid">
        <Metric icon={Cpu} label="Total tokens" value={analytics.token_usage.total_tokens} />
        <Metric icon={Gauge} label="Avg latency (ms)" value={Math.round(analytics.latency.avg_latency_ms || 0)} />
        <Metric icon={AlertTriangle} label="Failure rate (%)" value={analytics.failure_rate.rate || 0} />
        <Metric icon={Layers} label="Assets tracked" value={analytics.asset_comparison.length} />
      </section>

      <section className="grid-two">
        <div className="card card-3d">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Usage overview</p>
              <h2>Requests by asset</h2>
            </div>
          </div>
          <div className="bar-chart">
            {assetRows.map((row) => (
              <Bar
                key={row.assetName}
                label={row.assetName}
                value={row.requests}
                accentValue={row.pii}
                accentLabel="PII"
                max={maxRequests}
              />
            ))}
            {!assetRows.length && <p className="muted">Send a prompt to see this chart fill in.</p>}
          </div>
        </div>

        <div className="card card-3d">
          <div className="section-heading">
            <div>
              <p className="eyebrow">PII governance</p>
              <h2>What's been caught</h2>
            </div>
          </div>
          {donutSegments.length ? (
            <Donut segments={donutSegments} centerLabel="detections" />
          ) : (
            <p className="muted">Nothing caught yet — try a prompt with an email or phone number.</p>
          )}
          <p className="detection-disclaimer">
            Best-effort pattern detection, not an identity classifier — full limits documented in the README.
          </p>
        </div>
      </section>

      <section className="card card-3d">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Activity</p>
            <h2>Recent usage</h2>
          </div>
          {usageAssets.length > 1 && (
            <select
              className="input-3d usage-filter-select"
              value={usageAssetFilter}
              onChange={(e) => setUsageAssetFilter(e.target.value)}
              aria-label="Filter activity by AI tool"
            >
              <option value="">All tools</option>
              {usageAssets.map((asset) => (
                <option key={asset} value={asset}>
                  {asset}
                </option>
              ))}
            </select>
          )}
        </div>
        {filteredUsage.length ? (
          <div className="usage-table-wrap">
            <table className="usage-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Asset</th>
                  <th>Event type</th>
                </tr>
              </thead>
              <tbody>
                {filteredUsage.map((event) => (
                  <tr key={event.id}>
                    <td className="usage-table-time">{event.created_at}</td>
                    <td>{event.application}</td>
                    <td>{event.event_type}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="muted">Nothing yet — activity appears here in real time.</p>
        )}
      </section>
    </>
  )
}
