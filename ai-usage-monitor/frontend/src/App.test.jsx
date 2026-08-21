import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App.jsx'

const emptyAnalytics = {
  usage_over_time: [],
  model_usage: [],
  asset_comparison: [],
  token_usage: { input_tokens: 0, output_tokens: 0, total_tokens: 0 },
  latency: { avg_latency_ms: 0, samples: 0 },
  failure_rate: { failed: 0, total: 0, rate: 0 },
  agent_run_durations: [],
}

const mockAssets = [
  { name: 'chat', declared_purpose: 'General-purpose assistant chat.', declared_data_sources: [], monitoring_enabled: true, updated_at: null },
  { name: 'customer-support', declared_purpose: 'Handle customer support tickets.', declared_data_sources: ['FAQ DB'], monitoring_enabled: true, updated_at: null },
  { name: 'billing-agent', declared_purpose: 'Answer billing questions.', declared_data_sources: ['Billing DB'], monitoring_enabled: true, updated_at: null },
]

function mockFetch({ chatOk = true, summaryOk = true } = {}) {
  return vi.fn((url, options) => {
    if (options?.method === 'PATCH' && url.includes('/dashboard/assets/')) {
      const name = decodeURIComponent(url.split('/dashboard/assets/')[1])
      const body = JSON.parse(options.body)
      const row = mockAssets.find((a) => a.name === name) || { name, declared_purpose: null, declared_data_sources: [], updated_at: null }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ ...row, monitoring_enabled: body.monitoring_enabled }) })
    }
    if (url.includes('/dashboard/assets')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockAssets) })
    }
    if (options?.method === 'POST' && url.includes('/chat')) {
      if (!chatOk) {
        return Promise.resolve({ ok: false, json: () => Promise.resolve({ detail: 'Chat request failed' }) })
      }
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            message: 'Contact me at <EMAIL>',
            pii_detected: [{ type: 'EMAIL', source: 'regex', score: 1 }],
            pii_metadata: { EMAIL: 1 },
            response: 'This is a mock LLM response for usage tracking.',
            model: 'mock-model',
            event_id: 1,
          }),
      })
    }
    if (url.includes('/dashboard/summary')) {
      if (!summaryOk) {
        return Promise.resolve({ ok: false, json: () => Promise.resolve({ detail: 'Backend unavailable' }) })
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ total_events: 1, applications: ['chat'] }) })
    }
    if (url.includes('/dashboard/usage')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve([]) })
    }
    if (url.includes('/dashboard/analytics')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(emptyAnalytics) })
    }
    if (url.includes('/dashboard/prompts/pii-summary')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
    }
    if (url.includes('/dashboard/runs')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve([]) })
    }
    if (url.includes('/dashboard/prompts')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve([]) })
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
  })
}

describe('App', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('opens on the chat hero, not the dashboard', () => {
    global.fetch = mockFetch()
    render(<App />)
    expect(screen.getByRole('heading', { level: 1, name: 'Send a prompt. Watch what this tool catches.' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { level: 1, name: 'AI Usage Monitor' })).not.toBeInTheDocument()
  })

  it('hands off from the chat hero to the dashboard after a successful prompt', async () => {
    global.fetch = mockFetch()
    const user = userEvent.setup()
    render(<App />)

    const textarea = screen.getByPlaceholderText(/Message the monitored assistant/i)
    await user.type(textarea, 'Contact me at alice@example.com')
    const sendBtn = document.querySelector('.chat-send-btn')
    await user.click(sendBtn)

    expect(await screen.findByRole('heading', { level: 1, name: 'AI Usage Monitor' })).toBeInTheDocument()
    expect(screen.getByText(/Just captured/i)).toBeInTheDocument()
    expect(document.querySelector('.just-captured-sanitized').textContent).toBe('Contact me at <EMAIL>')
  })

  it('switches views via the sidebar and renders each view\'s content', async () => {
    global.fetch = mockFetch()
    const user = userEvent.setup()
    render(<App />)

    const textarea = screen.getByPlaceholderText(/Message the monitored assistant/i)
    await user.type(textarea, 'hello')
    await user.click(document.querySelector('.chat-send-btn'))
    await screen.findByRole('heading', { level: 1, name: 'AI Usage Monitor' })

    await user.click(screen.getByRole('button', { name: /Prompts/i }))
    expect(await screen.findByRole('heading', { level: 1, name: 'Prompts' })).toBeInTheDocument()
    expect(screen.getByText(/Sanitized prompts/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Agent Runs/i }))
    expect(await screen.findByRole('heading', { level: 1, name: 'Agent Runs' })).toBeInTheDocument()
    expect(screen.getByText(/Declared vs observed/i)).toBeInTheDocument()
  })

  it('returns to the chat hero via "New prompt"', async () => {
    global.fetch = mockFetch()
    const user = userEvent.setup()
    render(<App />)

    await user.type(screen.getByPlaceholderText(/Message the monitored assistant/i), 'hello')
    await user.click(document.querySelector('.chat-send-btn'))
    await screen.findByRole('heading', { level: 1, name: 'AI Usage Monitor' })

    await user.click(screen.getByRole('button', { name: /New prompt/i }))
    expect(await screen.findByRole('heading', { level: 1, name: 'Send a prompt. Watch what this tool catches.' })).toBeInTheDocument()
  })

  it('keeps the user on the hero and shows an inline error when the chat request fails', async () => {
    global.fetch = mockFetch({ chatOk: false })
    const user = userEvent.setup()
    render(<App />)

    await user.type(screen.getByPlaceholderText(/Message the monitored assistant/i), 'hello')
    await user.click(document.querySelector('.chat-send-btn'))

    expect(await screen.findByText('Chat request failed')).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 1, name: 'Send a prompt. Watch what this tool catches.' })).toBeInTheDocument()
  })

  it('shows a visible error banner in the dashboard when a dashboard fetch fails', async () => {
    global.fetch = mockFetch({ summaryOk: false })
    const user = userEvent.setup()
    render(<App />)

    await user.type(screen.getByPlaceholderText(/Message the monitored assistant/i), 'hello')
    await user.click(document.querySelector('.chat-send-btn'))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Backend unavailable')
    })
  })
})
