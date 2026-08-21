import { AlertTriangle, CheckCircle2 } from 'lucide-react'

function SourceList({ sources, unexpected }) {
  if (!sources.length) return <span className="run-source-empty">None</span>
  return (
    <span className="run-source-list">
      {sources.map((source) => (
        <span key={source} className={`run-source-chip${unexpected.includes(source) ? ' flagged' : ''}`}>
          {unexpected.includes(source) && <AlertTriangle size={11} strokeWidth={2.4} aria-hidden="true" />}
          {source}
        </span>
      ))}
    </span>
  )
}

export function RunsView({ agentRuns }) {
  return (
    <section className="card card-3d">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Agent runs</p>
          <h2>Declared vs observed</h2>
        </div>
      </div>
      <div className="runs-table">
        {agentRuns.map((run) => {
          const declared = run.declared || []
          const observed = run.observed || []
          const unexpected = run.unexpected || []
          return (
            <div key={run.run_id} className={`run-row card-3d ${run.governance_alert ? 'alert' : ''}`}>
              <div className="run-meta">
                <strong>{run.agent_id || 'agent'}</strong>
                <span>{run.status}</span>
              </div>
              <div>
                <div className="run-line">
                  <span>Declared</span>
                  <SourceList sources={declared} unexpected={[]} />
                </div>
                <div className="run-line">
                  <span>Observed</span>
                  <SourceList sources={observed} unexpected={unexpected} />
                </div>
                <div className="run-line">
                  <span>Tools</span>
                  <strong>{(run.tools_invoked || []).join(', ') || 'None'}</strong>
                </div>
              </div>
              <div className="run-badges">
                {run.governance_alert ? (
                  <span className="badge danger" title="This agent touched something it didn't declare">
                    <AlertTriangle size={13} strokeWidth={2.4} aria-hidden="true" />
                    Scope violation
                  </span>
                ) : (
                  <span className="badge ok" title="This agent only touched what it declared">
                    <CheckCircle2 size={13} strokeWidth={2.4} aria-hidden="true" />
                    Within scope
                  </span>
                )}
                {unexpected.map((source) => (
                  <span key={source} className="badge amber" title="Data source this agent accessed without declaring it">
                    Scope violation: {source}
                  </span>
                ))}
              </div>
            </div>
          )
        })}
        {!agentRuns.length && <p className="muted">No agent activity recorded yet.</p>}
      </div>
    </section>
  )
}
