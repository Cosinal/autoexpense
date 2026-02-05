const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function fetchAPI(endpoint: string, options?: RequestInit) {
  const url = `${API_URL}${endpoint}`

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })

  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`)
  }

  return response.json()
}

export const api = {
  receipts: {
    list: () => fetchAPI('/receipts'),
    sync: () => fetchAPI('/sync', { method: 'POST' }),
  },
  export: {
    csv: () => fetchAPI('/export/csv'),
  },
}
