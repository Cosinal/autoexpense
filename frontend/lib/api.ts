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

interface ReceiptFilters {
  user_id: string
  vendor?: string
  min_amount?: number
  max_amount?: number
  start_date?: string
  end_date?: string
  currency?: string
  page?: number
  page_size?: number
}

export const api = {
  receipts: {
    list: (filters: ReceiptFilters) => {
      const params = new URLSearchParams()
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params.append(key, String(value))
        }
      })
      return fetchAPI(`/receipts?${params.toString()}`)
    },
    get: (id: string, user_id: string) =>
      fetchAPI(`/receipts/${id}?user_id=${user_id}`),
    delete: (id: string, user_id: string) =>
      fetchAPI(`/receipts/${id}?user_id=${user_id}`, { method: 'DELETE' }),
    stats: (user_id: string, start_date?: string, end_date?: string) => {
      const params = new URLSearchParams({ user_id })
      if (start_date) params.append('start_date', start_date)
      if (end_date) params.append('end_date', end_date)
      return fetchAPI(`/receipts/stats/summary?${params.toString()}`)
    },
  },
  sync: {
    trigger: (user_id: string, days_back: number = 7) =>
      fetchAPI('/sync', {
        method: 'POST',
        body: JSON.stringify({ user_id, days_back }),
      }),
    status: () => fetchAPI('/sync/status'),
  },
  export: {
    csv: (user_id: string, start_date?: string, end_date?: string, currency?: string) => {
      const params = new URLSearchParams({ user_id })
      if (start_date) params.append('start_date', start_date)
      if (end_date) params.append('end_date', end_date)
      if (currency) params.append('currency', currency)
      return fetch(`${API_URL}/export/csv?${params.toString()}`)
    },
    summary: (user_id: string, start_date?: string, end_date?: string) => {
      const params = new URLSearchParams({ user_id })
      if (start_date) params.append('start_date', start_date)
      if (end_date) params.append('end_date', end_date)
      return fetchAPI(`/export/summary?${params.toString()}`)
    },
  },
}
