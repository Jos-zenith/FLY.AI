import { Fragment, useMemo, useRef, useState } from 'react'
import {
  Paperclip,
  ArrowUp,
  X,
  Loader2,
  MessageSquareText,
  ShieldCheck,
  LineChart,
  ArrowRight,
  ShieldAlert,
  Sparkles,
} from 'lucide-react'
import { previewPiiCounts } from '../lib/piiPreview.js'

const SUGGESTIONS = [
  'Write a reminder email to Ramesh, phone 98401xxxxx.',
  'Summarize the refund policy for ticket TKT-104, customer CUST-104.',
  'Check order status for alice@example.com and draft a reply.',
]

const HOW_IT_WORKS = [
  {
    icon: MessageSquareText,
    title: 'User prompt',
    body: 'Typed the way an employee would into ChatGPT or Copilot.',
  },
  {
    icon: ShieldCheck,
    title: 'Redaction scanner',
    body: 'Emails, phone numbers, card numbers, and IDs are detected instantly.',
  },
  {
    icon: LineChart,
    title: 'Dashboard log & AI model',
    body: 'Sanitized copy is stored here; the raw prompt still reaches the model.',
  },
]

const READABLE_EXTENSIONS = ['.txt', '.md', '.markdown', '.csv', '.json', '.log', '.yml', '.yaml']
const MAX_ATTACHMENT_CHARS = 4000

function isReadableFile(file) {
  const name = file.name.toLowerCase()
  return READABLE_EXTENSIONS.some((ext) => name.endsWith(ext))
}

export function ChatHero({ onSubmit, assetOptions = [], sessionCaught = 0 }) {
  const [message, setMessage] = useState('')
  const [asset, setAsset] = useState(assetOptions[0] || 'customer-support')
  const [attachment, setAttachment] = useState(null)
  const [attachError, setAttachError] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const fileInputRef = useRef(null)

  const canSubmit = (message.trim() || attachment) && !busy

  // Instant client-side preview of what the monitor would catch in this
  // draft -- purely local, never sent anywhere. The real detection record
  // comes back from the backend after submit; this is just live feedback
  // while typing so the value of the tool is visible before you even hit
  // send.
  const draftPreview = useMemo(() => previewPiiCounts(message), [message])
  const draftPreviewTotal = Object.values(draftPreview).reduce((sum, n) => sum + n, 0)

  const handleFileChange = async (event) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return

    setAttachError('')

    if (!isReadableFile(file)) {
      setAttachError('Only text-based files (.txt, .md, .csv, .json, .log, .yml) can be read in this demo.')
      return
    }

    try {
      const text = await file.text()
      const truncated = text.length > MAX_ATTACHMENT_CHARS
      setAttachment({
        name: file.name,
        content: truncated ? text.slice(0, MAX_ATTACHMENT_CHARS) : text,
        truncated,
      })
    } catch {
      setAttachError('Could not read that file in the browser.')
    }
  }

  const handleSubmit = async () => {
    if (!canSubmit) return
    setBusy(true)
    setError('')

    let fullMessage = message.trim()
    if (attachment) {
      fullMessage = `${fullMessage}\n\n[Attached file: ${attachment.name}${attachment.truncated ? ', truncated' : ''}]\n${attachment.content}`.trim()
    }

    try {
      await onSubmit(fullMessage, asset)
    } catch (err) {
      setError(err.message || 'The request failed. Nothing was sent to the dashboard.')
      setBusy(false)
    }
  }

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className="chat-hero">
      <div className="chat-hero-topbar">
        <div className="chat-hero-brand">
          <span className="chat-hero-mark" aria-hidden="true" />
          <div>
            <span className="chat-hero-brand-title">Vict AI</span>
            <span className="chat-hero-brand-tag">Catches sensitive data in AI prompts before it becomes a leak</span>
          </div>
        </div>
        <div className="chat-hero-counter" title="PII items caught across this session">
          <ShieldAlert size={14} strokeWidth={2.2} aria-hidden="true" />
          <strong>{sessionCaught}</strong> caught this session
        </div>
      </div>

      <div className="chat-hero-body">
        <p className="eyebrow">A working demo, not a mockup</p>
        <h1>Send a prompt. Watch what this tool catches.</h1>

        <div className="chat-input-shell card-3d">
          {attachment && (
            <div className="chat-attachment-pill">
              <Paperclip size={13} strokeWidth={2} aria-hidden="true" />
              <span>{attachment.name}</span>
              {attachment.truncated && <span className="chat-attachment-note">truncated</span>}
              <button type="button" aria-label="Remove attachment" onClick={() => setAttachment(null)}>
                <X size={13} strokeWidth={2} />
              </button>
            </div>
          )}

          <textarea
            className="chat-textarea"
            placeholder="Message the monitored assistant…"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={3}
          />

          <div className="chat-input-row">
            <div className="chat-input-row-left">
              <button
                type="button"
                className="chat-icon-btn"
                onClick={() => fileInputRef.current?.click()}
                aria-label="Attach a file"
                title="Attach a text file to include in the prompt"
              >
                <Paperclip size={16} strokeWidth={2} />
              </button>
              <input
                ref={fileInputRef}
                type="file"
                className="chat-file-input"
                onChange={handleFileChange}
                aria-hidden="true"
                tabIndex={-1}
              />
              <select
                className="chat-asset-select"
                value={asset}
                onChange={(e) => setAsset(e.target.value)}
                aria-label="Which AI tool this prompt is simulating"
                title="Which AI tool this prompt is simulating — different tools carry different data-access rules"
              >
                {(assetOptions.length ? assetOptions : ['customer-support', 'chat', 'billing-agent']).map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </select>
            </div>

            <button
              type="button"
              className="chat-send-btn"
              onClick={handleSubmit}
              disabled={!canSubmit}
              title="Send this prompt through the monitor"
            >
              {busy ? <Loader2 size={16} className="chat-spin" /> : <ArrowUp size={16} strokeWidth={2.4} />}
            </button>
          </div>
        </div>

        <div className={`chat-live-preview ${draftPreviewTotal ? 'active' : ''}`}>
          <Sparkles size={13} strokeWidth={2.2} aria-hidden="true" />
          {draftPreviewTotal ? (
            <>
              <span>Live scan:</span>
              {Object.entries(draftPreview).map(([label, count]) => (
                <span key={label} className="pill warn small">
                  {label} {count}
                </span>
              ))}
            </>
          ) : (
            <span>Live scan: nothing sensitive in this draft yet.</span>
          )}
        </div>

        {attachError && <p className="chat-hero-error">{attachError}</p>}
        {error && <p className="chat-hero-error">{error}</p>}

        <div className="chat-suggestions-wrap">
          <p className="chat-suggestions-label">Not sure what to try? These are common leak patterns:</p>
          <div className="chat-suggestions">
            {SUGGESTIONS.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                className="chat-suggestion-chip"
                onClick={() => setMessage(suggestion)}
                title="Click to fill the prompt box with this example"
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>

        <div className="how-it-works">
          {HOW_IT_WORKS.map(({ icon: Icon, title, body }, i) => (
            <Fragment key={title}>
              <div className="how-it-works-step card-3d">
                <div className="how-it-works-icon">
                  <Icon size={18} strokeWidth={2} aria-hidden="true" />
                </div>
                <h3>{title}</h3>
                <p>{body}</p>
              </div>
              {i < HOW_IT_WORKS.length - 1 && (
                <ArrowRight className="how-it-works-arrow" size={18} strokeWidth={2} aria-hidden="true" />
              )}
            </Fragment>
          ))}
        </div>
      </div>
    </div>
  )
}
