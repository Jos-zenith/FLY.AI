import { useState } from 'react'
import { ChevronDown, Download } from 'lucide-react'

function toCsv(rows) {
  const header = ['id', 'ai_asset', 'model', 'sanitized_prompt', 'pii_detected', 'input_tokens', 'output_tokens', 'latency_ms']
  const lines = [header.join(',')]
  for (const row of rows) {
    const values = [
      row.id,
      row.ai_asset,
      row.model || '',
      `"${(row.sanitized_prompt || '').replace(/"/g, '""')}"`,
      `"${JSON.stringify(row.pii_detected || {}).replace(/"/g, '""')}"`,
      row.tokens?.input ?? '',
      row.tokens?.output ?? '',
      row.latency_ms ?? '',
    ]
    lines.push(values.join(','))
  }
  return lines.join('\n')
}

function downloadFile(content, filename, mimeType) {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

function PromptRow({ row }) {
  const [open, setOpen] = useState(false)
  const entities = Object.entries(row.pii_detected || {})

  return (
    <>
      <tr className="prompt-table-row" onClick={() => setOpen((v) => !v)}>
        <td>
          <span className="prompt-asset-chip">{row.ai_asset}</span>
        </td>
        <td className="prompt-model-cell">{row.model || 'unknown'}</td>
        <td className="prompt-text-cell">{row.sanitized_prompt || 'No prompt text stored'}</td>
        <td>
          <div className="label-pills">
            {entities.map(([label, value]) => (
              <span key={label} className="pill warn small">
                {label} {value}
              </span>
            ))}
            {!entities.length && <span className="pill clean small">Clean</span>}
          </div>
        </td>
        <td className="prompt-expand-cell">
          <ChevronDown size={16} strokeWidth={2} className={`prompt-expand-icon ${open ? 'open' : ''}`} aria-hidden="true" />
        </td>
      </tr>
      {open && (
        <tr className="prompt-detail-row">
          <td colSpan={5}>
            <div className="prompt-detail">
              <div>
                <span>Input tokens</span>
                <strong>{row.tokens?.input ?? '—'}</strong>
              </div>
              <div>
                <span>Output tokens</span>
                <strong>{row.tokens?.output ?? '—'}</strong>
              </div>
              <div>
                <span>Latency</span>
                <strong>{row.latency_ms != null ? `${Math.round(row.latency_ms)} ms` : '—'}</strong>
              </div>
              <div>
                <span>Row id</span>
                <strong>#{row.id}</strong>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  )
}

export function PromptsView({
  promptRows,
  promptSearch,
  setPromptSearch,
  promptAsset,
  setPromptAsset,
  promptHasPii,
  setPromptHasPii,
  promptLimit,
  onLoadMore,
}) {
  return (
    <section className="card card-3d">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Prompt browse</p>
          <h2>Sanitized prompts</h2>
        </div>
        <button
          type="button"
          className="btn-3d prompts-export-btn"
          onClick={() => downloadFile(JSON.stringify(promptRows, null, 2), 'prompts.json', 'application/json')}
          title="Download the currently loaded rows as JSON"
        >
          <Download size={14} strokeWidth={2.2} aria-hidden="true" />
          Export JSON
        </button>
        <button
          type="button"
          className="btn-3d prompts-export-btn"
          onClick={() => downloadFile(toCsv(promptRows), 'prompts.csv', 'text/csv')}
          title="Download the currently loaded rows as CSV"
        >
          <Download size={14} strokeWidth={2.2} aria-hidden="true" />
          Export CSV
        </button>
      </div>
      <div className="filters">
        <input
          className="input-3d"
          value={promptSearch}
          onChange={(e) => setPromptSearch(e.target.value)}
          placeholder="Search sanitized prompt text"
        />
        <input
          className="input-3d"
          value={promptAsset}
          onChange={(e) => setPromptAsset(e.target.value)}
          placeholder="Filter by AI tool (e.g. chat, billing-agent)"
        />
        <label className="checkbox">
          <input
            type="checkbox"
            checked={promptHasPii}
            onChange={(e) => setPromptHasPii(e.target.checked)}
          />
          Only show prompts that contained PII
        </label>
      </div>

      {promptRows.length ? (
        <div className="prompt-table-wrap">
          <table className="prompt-table">
            <thead>
              <tr>
                <th>Asset / tool</th>
                <th>Model</th>
                <th>Sanitized prompt</th>
                <th>Detected entities</th>
                <th aria-hidden="true" />
              </tr>
            </thead>
            <tbody>
              {promptRows.map((row) => (
                <PromptRow key={row.id} row={row} />
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="muted">No prompts match these filters.</p>
      )}

      {promptRows.length >= promptLimit && (
        <button type="button" className="btn-3d prompts-load-more" onClick={onLoadMore}>
          Load more
        </button>
      )}
    </section>
  )
}
