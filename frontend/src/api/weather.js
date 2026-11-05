import apiClient from './client'

let inFlightWeather = null

// The weather API key lives in the backend .env; the frontend never calls the provider directly.
export function fetchWeather() {
  if (inFlightWeather) return inFlightWeather
  inFlightWeather = apiClient
    .get('/weather')
    .then((res) => res.data)
    .finally(() => {
      inFlightWeather = null
    })
  return inFlightWeather
}
