'use client'

import { useState, useEffect } from 'react'
import { createClient } from '@/lib/supabase'
import { useRouter } from 'next/navigation'

interface MonthlySummary {
  [month: string]: {
    count: number
    total: {
      [currency: string]: number
    }
  }
}

interface Summary {
  total_receipts: number
  date_range: {
    start: string | null
    end: string | null
  }
  by_month: MonthlySummary
  grand_total: {
    [currency: string]: number
  }
}

export default function ExportPage() {
  const [userId, setUserId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [summary, setSummary] = useState<Summary | null>(null)
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [currency, setCurrency] = useState('')
  const [error, setError] = useState('')

  const router = useRouter()
  const supabase = createClient()

  useEffect(() => {
    checkAuth()
  }, [])

  const checkAuth = async () => {
    const { data: { user } } = await supabase.auth.getUser()

    if (!user) {
      router.push('/login')
      return
    }

    setUserId(user.id)
    loadSummary(user.id)
  }

  const loadSummary = async (uid: string, filters?: any) => {
    setLoading(true)
    setError('')

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const params = new URLSearchParams({
        user_id: uid,
        ...(filters?.start_date && { start_date: filters.start_date }),
        ...(filters?.end_date && { end_date: filters.end_date }),
      })

      const response = await fetch(`${API_URL}/export/summary?${params}`)

      if (!response.ok) throw new Error('Failed to fetch summary')

      const data = await response.json()
      setSummary(data)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleExportCSV = async () => {
    if (!userId) return

    setError('')

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const params = new URLSearchParams({
        user_id: userId,
        ...(startDate && { start_date: startDate }),
        ...(endDate && { end_date: endDate }),
        ...(currency && { currency }),
      })

      const response = await fetch(`${API_URL}/export/csv?${params}`)

      if (!response.ok) throw new Error('Export failed')

      // Download the CSV file
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `receipts_${new Date().toISOString().split('T')[0]}.csv`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (err: any) {
      setError(err.message)
    }
  }

  const handleUpdateSummary = () => {
    if (!userId) return

    loadSummary(userId, {
      start_date: startDate,
      end_date: endDate,
    })
  }

  const formatCurrency = (amount: number, curr: string) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: curr || 'USD',
    }).format(amount)
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Export</h1>
              <p className="text-sm text-gray-500">Download and analyze your receipts</p>
            </div>
            <button
              onClick={() => router.push('/receipts')}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Back to Receipts
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Export options */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Export Options</h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Start Date
              </label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                End Date
              </label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Currency (optional)
              </label>
              <input
                type="text"
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                placeholder="USD, EUR, etc."
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleExportCSV}
              className="px-6 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
            >
              Download CSV
            </button>
            <button
              onClick={handleUpdateSummary}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Update Summary
            </button>
          </div>
        </div>

        {/* Error message */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        {/* Summary */}
        {loading ? (
          <div className="bg-white rounded-lg shadow p-6">
            <p className="text-center text-gray-500">Loading summary...</p>
          </div>
        ) : summary ? (
          <div className="space-y-6">
            {/* Overview */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-medium text-gray-900 mb-4">Overview</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                  <p className="text-sm text-gray-500">Total Receipts</p>
                  <p className="text-2xl font-semibold text-gray-900">
                    {summary.total_receipts}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Start Date</p>
                  <p className="text-lg font-medium text-gray-900">
                    {summary.date_range.start || 'All time'}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">End Date</p>
                  <p className="text-lg font-medium text-gray-900">
                    {summary.date_range.end || 'Present'}
                  </p>
                </div>
              </div>
            </div>

            {/* Grand Total */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-medium text-gray-900 mb-4">Grand Total</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {Object.entries(summary.grand_total).map(([curr, amount]) => (
                  <div key={curr} className="bg-gray-50 rounded-lg p-4">
                    <p className="text-sm text-gray-500">{curr}</p>
                    <p className="text-xl font-semibold text-gray-900">
                      {formatCurrency(amount, curr)}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* Monthly Breakdown */}
            {Object.keys(summary.by_month).length > 0 && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-medium text-gray-900 mb-4">
                  Monthly Breakdown
                </h2>
                <div className="space-y-4">
                  {Object.entries(summary.by_month)
                    .sort(([a], [b]) => b.localeCompare(a))
                    .map(([month, data]) => (
                      <div key={month} className="border-b border-gray-200 pb-4 last:border-0">
                        <div className="flex justify-between items-center mb-2">
                          <h3 className="text-md font-medium text-gray-900">{month}</h3>
                          <span className="text-sm text-gray-500">
                            {data.count} receipt{data.count !== 1 ? 's' : ''}
                          </span>
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                          {Object.entries(data.total).map(([curr, amount]) => (
                            <div key={curr} className="bg-gray-50 rounded px-3 py-2">
                              <p className="text-xs text-gray-500">{curr}</p>
                              <p className="text-sm font-medium text-gray-900">
                                {formatCurrency(amount, curr)}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                </div>
              </div>
            )}
          </div>
        ) : null}
      </div>
    </div>
  )
}
