import { describe, expect, test, vi, beforeEach } from 'vitest'
import apiClient from '../../api/client'
import { fetchWeather } from '../../api/weather'

describe('Weather API In-Flight Deduplication F6', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  test('concurrent fetchWeather calls share a single in-flight request', async () => {
    let resolveGet
    const pendingPromise = new Promise((resolve) => {
      resolveGet = resolve
    })
    const getSpy = vi.spyOn(apiClient, 'get').mockReturnValue(pendingPromise)

    const p1 = fetchWeather()
    const p2 = fetchWeather()

    // Even though fetchWeather was invoked twice concurrently, apiClient.get was called once
    expect(getSpy).toHaveBeenCalledTimes(1)

    // Complete the in-flight request
    resolveGet({ data: { temperature: 21, condition: '구름많음' } })
    const [res1, res2] = await Promise.all([p1, p2])

    expect(res1).toEqual({ temperature: 21, condition: '구름많음' })
    expect(res2).toEqual({ temperature: 21, condition: '구름많음' })

    // Next request after settlement should initiate a new call
    getSpy.mockResolvedValueOnce({ data: { temperature: 22, condition: '맑음' } })
    const res3 = await fetchWeather()
    expect(getSpy).toHaveBeenCalledTimes(2)
    expect(res3).toEqual({ temperature: 22, condition: '맑음' })
  })
})
