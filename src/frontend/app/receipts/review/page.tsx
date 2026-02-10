'use client'

import { useState, useEffect } from 'react'
import { createClient } from '@/lib/supabase'
import { useRouter } from 'next/navigation'

interface CandidateOption {
  value: string
  score: number
  pattern: string
}

interface FieldReviewData {
  current_value: string | null
  confidence: number
  options: CandidateOption[]
}

interface ReviewCandidates {
  vendor?: FieldReviewData
  amount?: FieldReviewData
  date?: FieldReviewData
  currency?: FieldReviewData
}

interface Receipt {
  id: string
  vendor: string | null
  amount: string | null
  currency: string | null
  date: string | null
  tax: string | null
  file_url: string
  file_path: string | null
  created_at: string
  needs_review: boolean
  review_reason: string | null
  ingestion_debug: {
    review_candidates?: ReviewCandidates
    confidence_per_field?: Record<string, number>
  }
}

interface FieldCorrection {
  original: string | null
  corrected_to: string
  candidates: string[]
  confidence: number
}

export default function ReviewQueuePage() {
  const [receipts, setReceipts] = useState<Receipt[]>([])
  const [loading, setLoading] = useState(true)
  const [userId, setUserId] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [currentReceiptIndex, setCurrentReceiptIndex] = useState(0)
  const [corrections, setCorrections] = useState<Record<string, FieldCorrection>>({})
  const [submitting, setSubmitting] = useState(false)
  const [customInputs, setCustomInputs] = useState<Record<string, string>>({})
  const [selectedOptions, setSelectedOptions] = useState<Record<string, string>>({})

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
    loadPendingReviews(user.id)
  }

  const loadPendingReviews = async (uid: string) => {
    setLoading(true)
    setError('')

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${API_URL}/review/pending?user_id=${uid}&limit=50`)

      if (!response.ok) throw new Error('Failed to fetch pending reviews')

      const data = await response.json()
      setReceipts(data.receipts)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleFieldSelection = (fieldName: string, value: string, isCustom: boolean) => {
    setSelectedOptions(prev => ({
      ...prev,
      [fieldName]: isCustom ? 'custom' : value
    }))

    if (!isCustom) {
      // Clear custom input if selecting a predefined option
      setCustomInputs(prev => {
        const newInputs = { ...prev }
        delete newInputs[fieldName]
        return newInputs
      })
    }
  }

  const handleCustomInput = (fieldName: string, value: string) => {
    setCustomInputs(prev => ({
      ...prev,
      [fieldName]: value
    }))
  }

  const handleSubmitReview = async () => {
    if (!userId || !receipts[currentReceiptIndex]) return

    const receipt = receipts[currentReceiptIndex]
    const reviewCandidates = receipt.ingestion_debug?.review_candidates || {}
    const confidencePerField = receipt.ingestion_debug?.confidence_per_field || {}

    // Build corrections object from ALL fields
    const corrections: Record<string, FieldCorrection> = {}

    allFields.forEach(field => {
      const selectedValue = selectedOptions[field.name]
      const customValue = customInputs[field.name]
      const fieldData = reviewCandidates[field.name as keyof ReviewCandidates]
      const currentValue = field.currentValue

      // Determine the corrected value
      let correctedValue: string | null = null

      if (customValue) {
        // User entered a custom value for this field
        correctedValue = customValue
      } else if (selectedValue && selectedValue !== currentValue) {
        // User selected a different option (not the current value)
        correctedValue = selectedValue
      }

      // Only add to corrections if user actually changed the value
      if (correctedValue && correctedValue !== currentValue) {
        corrections[field.name] = {
          original: currentValue,
          corrected_to: correctedValue,
          candidates: fieldData?.options?.map(opt => opt.value) || [],
          confidence: confidencePerField[field.name] || 0.0
        }
      }
    })

    if (Object.keys(corrections).length === 0) {
      alert('No changes made. Please edit at least one field or click Skip.')
      return
    }

    setSubmitting(true)
    setError('')

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${API_URL}/review/submit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          receipt_id: receipt.id,
          corrections,
          user_id: userId
        })
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Failed to submit review')
      }

      // Success! Remove this receipt from the queue and move to next
      const updatedReceipts = receipts.filter((_, idx) => idx !== currentReceiptIndex)
      setReceipts(updatedReceipts)

      // Reset state
      setCorrections({})
      setCustomInputs({})
      setSelectedOptions({})

      // If we removed the last receipt, go back one
      if (currentReceiptIndex >= updatedReceipts.length && currentReceiptIndex > 0) {
        setCurrentReceiptIndex(currentReceiptIndex - 1)
      }

      if (updatedReceipts.length === 0) {
        alert('All receipts reviewed! Great work.')
      }
    } catch (err: any) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleSkip = () => {
    if (currentReceiptIndex < receipts.length - 1) {
      setCurrentReceiptIndex(currentReceiptIndex + 1)
      setCorrections({})
      setCustomInputs({})
      setSelectedOptions({})
    }
  }

  const handlePrevious = () => {
    if (currentReceiptIndex > 0) {
      setCurrentReceiptIndex(currentReceiptIndex - 1)
      setCorrections({})
      setCustomInputs({})
      setSelectedOptions({})
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-500">Loading review queue...</p>
      </div>
    )
  }

  if (receipts.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="bg-white shadow">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <div className="flex justify-between items-center">
              <h1 className="text-2xl font-bold text-gray-900">Review Queue</h1>
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
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <svg
              className="mx-auto h-12 w-12 text-green-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <h2 className="mt-4 text-xl font-semibold text-gray-900">
              All caught up!
            </h2>
            <p className="mt-2 text-gray-500">
              No receipts need review at the moment.
            </p>
          </div>
        </div>
      </div>
    )
  }

  const currentReceipt = receipts[currentReceiptIndex]
  const reviewCandidates = currentReceipt.ingestion_debug?.review_candidates || {}

  // Define all fields that can be edited
  const allFields = [
    { name: 'vendor', label: 'Vendor', currentValue: currentReceipt.vendor },
    { name: 'amount', label: 'Amount', currentValue: currentReceipt.amount },
    { name: 'date', label: 'Date', currentValue: currentReceipt.date },
    { name: 'currency', label: 'Currency', currentValue: currentReceipt.currency },
    { name: 'tax', label: 'Tax', currentValue: currentReceipt.tax },
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Review Queue</h1>
              <p className="text-sm text-gray-500">
                {currentReceiptIndex + 1} of {receipts.length} receipts
              </p>
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
        {/* Error message */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left: Receipt Preview */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Receipt Preview</h2>

            {/* Receipt file */}
            <div className="mb-6">
              {currentReceipt.file_url ? (
                currentReceipt.file_path?.endsWith('.pdf') ? (
                  <>
                    <iframe
                      src={currentReceipt.file_url}
                      className="w-full h-96 border border-gray-300 rounded-lg"
                      title="Receipt preview"
                    />
                    <a
                      href={currentReceipt.file_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-2 inline-block text-sm text-blue-600 hover:text-blue-800"
                    >
                      Open PDF in new tab
                    </a>
                  </>
                ) : (
                  <div className="border border-gray-300 rounded-lg p-4 bg-gray-50">
                    <p className="text-sm text-gray-600 mb-2">
                      This receipt was processed from email text. No PDF available.
                    </p>
                    <a
                      href={currentReceipt.file_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-blue-600 hover:text-blue-800"
                    >
                      View original email text
                    </a>
                  </div>
                )
              ) : (
                <div className="border border-gray-300 rounded-lg p-4 bg-gray-50">
                  <p className="text-sm text-gray-500">No file preview available</p>
                </div>
              )}
            </div>

            {/* Current extraction */}
            <div className="space-y-2">
              <h3 className="text-sm font-medium text-gray-700">Current Extraction</h3>
              <div className="bg-gray-50 rounded-lg p-4 space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Vendor:</span>
                  <span className="text-sm font-medium text-gray-900">
                    {currentReceipt.vendor || 'N/A'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Amount:</span>
                  <span className="text-sm font-medium text-gray-900">
                    {currentReceipt.amount || 'N/A'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Date:</span>
                  <span className="text-sm font-medium text-gray-900">
                    {currentReceipt.date || 'N/A'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Currency:</span>
                  <span className="text-sm font-medium text-gray-900">
                    {currentReceipt.currency || 'N/A'}
                  </span>
                </div>
              </div>

              {currentReceipt.review_reason && (
                <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <p className="text-sm text-yellow-800">
                    <strong>Review Reason:</strong> {currentReceipt.review_reason}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Right: Review Form */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-2">
              Review & Edit Fields
            </h2>
            <p className="text-sm text-gray-500 mb-4">
              Edit any field below. Fields with low confidence show suggested options.
            </p>

            <div className="space-y-6">
              {allFields.map((field) => {
                const fieldData = reviewCandidates[field.name as keyof ReviewCandidates]
                const hasOptions = fieldData && fieldData.options && fieldData.options.length > 0

                return (
                  <div key={field.name} className="border-b border-gray-200 pb-6 last:border-0">
                    <div className="mb-3">
                      <h3 className="text-sm font-medium text-gray-900">
                        {field.label}
                      </h3>
                      <p className="text-xs text-gray-500">
                        Current: {field.currentValue || 'N/A'}
                        {fieldData && ` (confidence: ${Math.round(fieldData.confidence * 100)}%)`}
                      </p>
                    </div>

                    {hasOptions ? (
                      // Show radio button options for low-confidence fields
                      <div className="space-y-2">
                        {/* Keep current value option */}
                        <label
                          className={`flex items-start p-3 border rounded-lg cursor-pointer transition-colors ${
                            selectedOptions[field.name] === field.currentValue
                              ? 'border-blue-500 bg-blue-50'
                              : 'border-gray-300 hover:bg-gray-50'
                          }`}
                        >
                          <input
                            type="radio"
                            name={field.name}
                            value={field.currentValue || ''}
                            checked={selectedOptions[field.name] === field.currentValue}
                            onChange={() => handleFieldSelection(field.name, field.currentValue || '', false)}
                            className="mt-1 mr-3"
                          />
                          <div className="flex-1">
                            <div className="text-sm font-medium text-gray-900">
                              Keep: {field.currentValue || 'N/A'}
                            </div>
                            <div className="text-xs text-gray-500">
                              (Current extraction)
                            </div>
                          </div>
                        </label>

                        {/* Other option buttons */}
                        {fieldData.options.filter(opt => opt.value !== field.currentValue).map((option, idx) => (
                          <label
                            key={idx}
                            className={`flex items-start p-3 border rounded-lg cursor-pointer transition-colors ${
                              selectedOptions[field.name] === option.value
                                ? 'border-blue-500 bg-blue-50'
                                : 'border-gray-300 hover:bg-gray-50'
                            }`}
                          >
                            <input
                              type="radio"
                              name={field.name}
                              value={option.value}
                              checked={selectedOptions[field.name] === option.value}
                              onChange={() => handleFieldSelection(field.name, option.value, false)}
                              className="mt-1 mr-3"
                            />
                            <div className="flex-1">
                              <div className="text-sm font-medium text-gray-900">
                                {option.value}
                              </div>
                              <div className="text-xs text-gray-500">
                                Confidence: {Math.round(option.score * 100)}% • Pattern: {option.pattern}
                              </div>
                            </div>
                          </label>
                        ))}

                        {/* Custom input option */}
                        <label
                          className={`flex items-start p-3 border rounded-lg cursor-pointer transition-colors ${
                            selectedOptions[field.name] === 'custom'
                              ? 'border-blue-500 bg-blue-50'
                              : 'border-gray-300 hover:bg-gray-50'
                          }`}
                        >
                          <input
                            type="radio"
                            name={field.name}
                            value="custom"
                            checked={selectedOptions[field.name] === 'custom'}
                            onChange={() => handleFieldSelection(field.name, '', true)}
                            className="mt-1 mr-3"
                          />
                          <div className="flex-1">
                            <div className="text-sm font-medium text-gray-900 mb-2">
                              Other (enter custom value)
                            </div>
                            <input
                              type="text"
                              value={customInputs[field.name] || ''}
                              onChange={(e) => handleCustomInput(field.name, e.target.value)}
                              onFocus={() => handleFieldSelection(field.name, '', true)}
                              placeholder={`Enter ${field.label.toLowerCase()}...`}
                              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                            />
                          </div>
                        </label>
                      </div>
                    ) : (
                      // Show simple text input for high-confidence fields
                      <div className="space-y-2">
                        <label
                          className={`flex items-start p-3 border rounded-lg cursor-pointer transition-colors ${
                            !customInputs[field.name]
                              ? 'border-blue-500 bg-blue-50'
                              : 'border-gray-300 hover:bg-gray-50'
                          }`}
                        >
                          <input
                            type="radio"
                            name={field.name}
                            checked={!customInputs[field.name]}
                            onChange={() => {
                              const newInputs = { ...customInputs }
                              delete newInputs[field.name]
                              setCustomInputs(newInputs)
                            }}
                            className="mt-1 mr-3"
                          />
                          <div className="flex-1">
                            <div className="text-sm font-medium text-gray-900">
                              Keep: {field.currentValue || 'N/A'}
                            </div>
                            <div className="text-xs text-gray-500">
                              (No changes)
                            </div>
                          </div>
                        </label>

                        <label
                          className={`flex items-start p-3 border rounded-lg cursor-pointer transition-colors ${
                            customInputs[field.name]
                              ? 'border-blue-500 bg-blue-50'
                              : 'border-gray-300 hover:bg-gray-50'
                          }`}
                        >
                          <input
                            type="radio"
                            name={field.name}
                            checked={!!customInputs[field.name]}
                            onChange={() => {
                              // Focus the input when radio is selected
                              setCustomInputs(prev => ({ ...prev, [field.name]: '' }))
                            }}
                            className="mt-1 mr-3"
                          />
                          <div className="flex-1">
                            <div className="text-sm font-medium text-gray-900 mb-2">
                              Edit value
                            </div>
                            <input
                              type="text"
                              value={customInputs[field.name] || ''}
                              onChange={(e) => handleCustomInput(field.name, e.target.value)}
                              onFocus={() => {
                                if (!customInputs[field.name]) {
                                  setCustomInputs(prev => ({ ...prev, [field.name]: field.currentValue || '' }))
                                }
                              }}
                              placeholder={`Enter ${field.label.toLowerCase()}...`}
                              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                            />
                          </div>
                        </label>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>

            {/* Action buttons */}
            <div className="mt-6 flex gap-3">
              <button
                onClick={handleSubmitReview}
                disabled={submitting}
                className="flex-1 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {submitting ? 'Submitting...' : 'Submit Changes'}
              </button>
              <button
                onClick={handleSkip}
                disabled={currentReceiptIndex >= receipts.length - 1}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
              >
                Skip
              </button>
              <button
                onClick={handlePrevious}
                disabled={currentReceiptIndex === 0}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
              >
                Previous
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
