import apiClient from './client'

// The weather API key lives in the backend .env; the frontend never calls the provider directly.
export function fetchWeather() {
  return apiClient.get('/weather').then((res) => res.data)
}
