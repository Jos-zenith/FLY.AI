import { useState } from 'react'
import { Database, ShieldCheck, ShieldOff } from 'lucide-react'

export function ToggleSwitch({ checked, onChange, disabled, label }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      className={`toggle-switch ${checked ? 'on' : 'off'}`}
      onClick={() => onChange(!checked)}
      title={checked ? 'Monitoring is on -- prompts through this asset are captured' : 'Monitoring is off -- prompts through this asset are not captured or stored'}
    >
      <span className="toggle-switch-knob" />
    </button>
  )
}

function AssetCard({ asset, onToggleMonitoring }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const handleToggle = async (next) => {
    setBusy(true)
    setError('')
    try {
      await onToggleMonitoring(asset.name, next)
    } catch (err) {
      setError(err.message || 'Could not update monitoring for this asset.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="asset-card card-3d">
      <div className="asset-card-header">
        <div className="asset-card-title">
          <Database size={16} strokeWidth={2} aria-hidden="true" />
          <strong>{asset.name}</strong>
        </div>
        <div className="asset-card-toggle">
          {asset.monitoring_enabled ? (
            <ShieldCheck size={14} strokeWidth={2.2} aria-hidden="true" className="asset-monitor-icon on" />
          ) : (
            <ShieldOff size={14} strokeWidth={2.2} aria-hidden="true" className="asset-monitor-icon off" />
          )}
          <span className="asset-toggle-label">{asset.monitoring_enabled ? 'Monitoring on' : 'Monitoring off'}</span>
          <ToggleSwitch
            checked={asset.monitoring_enabled}
            onChange={handleToggle}
            disabled={busy}
            label={`Toggle monitoring for ${asset.name}`}
          />
        </div>
      </div>

      <p className="asset-card-purpose">
        {asset.declared_purpose || <span className="muted">No declared purpose on file.</span>}
      </p>

      <div className="asset-card-sources">
        <span className="asset-card-sources-label">Declared data sources</span>
        <div className="label-pills">
          {(asset.declared_data_sources || []).length ? (
            asset.declared_data_sources.map((source) => (
              <span key={source} className="pill small">
                {source}
              </span>
            ))
          ) : (
            <span className="pill small clean">None declared</span>
          )}
        </div>
      </div>

      {error && <p className="chat-hero-error">{error}</p>}
    </div>
  )
}

export function AssetsView({ assets, onToggleMonitoring, onRefresh }) {
  return (
    <section className="card card-3d">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Governance registry</p>
          <h2>AI assets</h2>
        </div>
        <button type="button" className="btn-3d" onClick={onRefresh} title="Reload the asset registry">
          Refresh
        </button>
      </div>

      {assets.length ? (
        <div className="asset-grid">
          {assets.map((asset) => (
            <AssetCard key={asset.name} asset={asset} onToggleMonitoring={onToggleMonitoring} />
          ))}
        </div>
      ) : (
        <p className="muted">No AI assets registered yet.</p>
      )}
    </section>
  )
}
