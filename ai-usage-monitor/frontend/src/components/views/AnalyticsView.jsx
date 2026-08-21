import { Sparkline } from '../charts/Sparkline.jsx'
import { Bar } from '../charts/Bar.jsx'
import { RadialGauge } from '../charts/RadialGauge.jsx'

export function AnalyticsView({ analytics }) {
  const trendPoints = analytics.usage_over_time.map((day) => ({ label: day.date, value: day.requests }))
  const totalRequests = analytics.usage_over_time.reduce((sum, day) => sum + (day.requests || 0), 0)

  const maxModelRequests = Math.max(...analytics.model_usage.map((m) => m.requests || 0), 1)
  const maxRunDuration = Math.max(...analytics.agent_run_durations.map((r) => r.avg_seconds || 0), 1)

  const failurePercent = Number(analytics.failure_rate.rate) || 0
  const latencyPercent = Math.min(100, ((analytics.latency.avg_latency_ms || 0) / 2000) * 100)

  return (
    <>
      <section className="grid-two analytics-panels">
        <div className="card card-3d">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Trend analysis</p>
              <h2>Usage over time</h2>
            </div>
            <strong className="chart-headline">{totalRequests}</strong>
          </div>
          {trendPoints.length ? (
            <Sparkline points={trendPoints} />
          ) : (
            <p className="muted">Send a few prompts to start a trend line.</p>
          )}
        </div>

        <div className="card card-3d">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Model analytics</p>
              <h2>Model usage</h2>
            </div>
          </div>
          <div className="bar-chart">
            {analytics.model_usage.map((model) => (
              <Bar key={model.model} label={model.model} value={model.requests} max={maxModelRequests} unit=" req" />
            ))}
            {!analytics.model_usage.length && <p className="muted">No model activity yet.</p>}
          </div>
        </div>
      </section>

      <section className="grid-two analytics-panels">
        <div className="card card-3d">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Operational health</p>
              <h2>Failure rate &amp; latency</h2>
            </div>
          </div>
          <div className="gauge-row">
            <RadialGauge
              percent={failurePercent}
              displayValue={`${failurePercent}%`}
              label="failure rate"
              tone={failurePercent > 0 ? 'danger' : 'ok'}
            />
            <RadialGauge
              percent={latencyPercent}
              displayValue={`${Math.round(analytics.latency.avg_latency_ms || 0)}ms`}
              label="avg latency"
              tone="neutral"
            />
          </div>
        </div>

        <div className="card card-3d">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Runner health</p>
              <h2>Agent execution duration</h2>
            </div>
          </div>
          <div className="bar-chart">
            {analytics.agent_run_durations.map((run) => (
              <Bar
                key={run.agent_id}
                label={run.agent_id}
                value={run.avg_seconds}
                accentValue={run.failed}
                accentLabel="failed"
                max={maxRunDuration}
                unit="s"
              />
            ))}
            {!analytics.agent_run_durations.length && <p className="muted">No agent runs recorded yet.</p>}
          </div>
        </div>
      </section>
    </>
  )
}
