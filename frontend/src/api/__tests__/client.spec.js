import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import apiClient, { onColdStart, resetColdStart } from '../client'

// Replace the transport so no network is touched; the interceptors under test still run.
function useAdapter(responses) {
  const calls = []
  apiClient.defaults.adapter = async (config) => {
    calls.push({ url: config.url, method: config.method, timeout: config.timeout })
    const next = responses.shift()
    if (next instanceof Error) {
      next.config = config
      throw next
    }
    return { data: next.data, status: next.status || 200, statusText: 'OK', headers: {}, config }
  }
  return calls
}
const timeoutErr = () => Object.assign(new Error('timeout of 12000ms exceeded'), { code: 'ECONNABORTED', isAxiosError: true })
const netErr = () => Object.assign(new Error('Network Error'), { code: 'ERR_NETWORK', isAxiosError: true })
const httpErr = (status) => Object.assign(new Error('x'), { isAxiosError: true, response: { status, data: {} } })

describe('apiClient cold start', () => {
  beforeEach(() => {
    resetColdStart()
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.useRealTimers()
    delete apiClient.defaults.adapter
  })

  test('first request gets a long timeout', async () => {
    const calls = useAdapter([{ data: { ok: 1 } }])
    await apiClient.get('/meta')
    expect(calls[0].timeout).toBeGreaterThanOrEqual(45_000)
  })

  test('a timed-out GET is retried once automatically and announces the wake-up', async () => {
    const calls = useAdapter([timeoutErr(), { data: { ok: 1 } }])
    const seen = []
    const off = onColdStart((waking) => seen.push(waking))
    const p = apiClient.get('/meta')
    await vi.runAllTimersAsync()
    const res = await p
    off()
    expect(res.data).toEqual({ ok: 1 })
    expect(calls).toHaveLength(2)
    expect(seen).toEqual([true, false])
  })

  test('network error GET is retried once, then fails', async () => {
    const calls = useAdapter([netErr(), netErr(), { data: 1 }])
    const p = apiClient.get('/meta').catch((e) => e)
    await vi.runAllTimersAsync()
    const e = await p
    expect(e.code).toBe('ERR_NETWORK')
    expect(calls).toHaveLength(2)
  })

  test('429 and other HTTP errors are not retried', async () => {
    const calls = useAdapter([httpErr(429), { data: 1 }])
    await expect(apiClient.get('/meta')).rejects.toMatchObject({ response: { status: 429 } })
    expect(calls).toHaveLength(1)
  })

  test('POST is never retried', async () => {
    const calls = useAdapter([timeoutErr(), { data: 1 }])
    const p = apiClient.post('/posts', {}).catch((e) => e)
    await vi.runAllTimersAsync()
    await p
    expect(calls).toHaveLength(1)
  })

  test('once the server has answered, later requests use the normal timeout', async () => {
    const calls = useAdapter([{ data: 1 }, { data: 2 }])
    await apiClient.get('/a')
    await apiClient.get('/b')
    expect(calls[1].timeout).toBeLessThanOrEqual(15_000)
  })
})
