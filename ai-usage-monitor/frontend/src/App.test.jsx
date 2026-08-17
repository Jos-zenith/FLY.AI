import { render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App.jsx'

describe('App dashboard', () => {
  beforeEach(() => {
    global.fetch = vi.fn((url) => {
      if (url.includes('/dashboard/summary')) {
        return Promise.resolve({ json: () => Promise.resolve({ total_events: 0, applications: [] }) })
      }
      if (url.includes('/dashboard/usage')) {
        return Promise.resolve({ json: () => Promise.resolve([]) })
      }
      if (url.includes('/dashboard/analytics')) {
        return Promise.resolve({
          json: () => Promise.resolve({
            usage_over_time: [],
            model_usage: [],
            asset_comparison: [],
            token_usage: { input_tokens: 0, output_tokens: 0, total_tokens: 0 },
            latency: { avg_latency_ms: 0, samples: 0 },
            failure_rate: { failed: 0, total: 0, rate: 0 },
            agent_run_durations: [],
          }),
        })
      }
      if (url.includes('/dashboard/prompts/pii-summary')) {
        return Promise.resolve({ json: () => Promise.resolve({}) })
      }
      if (url.includes('/dashboard/runs')) {
        return Promise.resolve({ json: () => Promise.resolve([]) })
      }
      if (url.includes('/dashboard/prompts')) {
        return Promise.resolve({ json: () => Promise.resolve([]) })
      }
      return Promise.resolve({ json: () => Promise.resolve({}) })
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders the dashboard shell and heading', () => {
    render(<App />)
    expect(screen.getByText('AI Usage Monitor')).toBeInTheDocument()
    expect(screen.getByText('AI observability dashboard')).toBeInTheDocument()
  })
})
