'use client'

import { useState, useEffect, useCallback } from 'react'
import { createClient } from '@/lib/supabase'
import { useRouter } from 'next/navigation'

interface UploadedFile {
  file: File
  status: 'pending' | 'uploading' | 'processing' | 'success' | 'error'
  message?: string
  receiptId?: string
}

export default function UploadPage() {
  const [userId, setUserId] = useState<string | null>(null)
  const [files, setFiles] = useState<UploadedFile[]>([])
  const [isDragging, setIsDragging] = useState(false)
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
  }

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)

    const droppedFiles = Array.from(e.dataTransfer.files)
    addFiles(droppedFiles)
  }, [])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files)
      addFiles(selectedFiles)
    }
  }

  const addFiles = (newFiles: File[]) => {
    // Validate file types
    const validTypes = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png']
    const validFiles = newFiles.filter(file => {
      const isValid = validTypes.includes(file.type)
      if (!isValid) {
        alert(`${file.name} is not a supported file type. Please upload PDF, JPG, or PNG files.`)
      }
      return isValid
    })

    // Add to files list
    const uploadedFiles: UploadedFile[] = validFiles.map(file => ({
      file,
      status: 'pending'
    }))

    setFiles(prev => [...prev, ...uploadedFiles])
  }

  const uploadFile = async (uploadedFile: UploadedFile, index: number) => {
    if (!userId) return

    // Update status to uploading
    setFiles(prev => prev.map((f, i) =>
      i === index ? { ...f, status: 'uploading' } : f
    ))

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

      // Create form data
      const formData = new FormData()
      formData.append('file', uploadedFile.file)
      formData.append('user_id', userId)

      // Upload to backend
      const response = await fetch(`${API_URL}/upload`, {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Upload failed' }))
        throw new Error(error.detail || 'Upload failed')
      }

      const result = await response.json()

      // Update status to success
      setFiles(prev => prev.map((f, i) =>
        i === index ? {
          ...f,
          status: 'success',
          message: `Processed: ${result.vendor || 'Unknown vendor'} - ${result.amount || 'N/A'}`,
          receiptId: result.id
        } : f
      ))

    } catch (err: any) {
      // Update status to error
      setFiles(prev => prev.map((f, i) =>
        i === index ? {
          ...f,
          status: 'error',
          message: err.message
        } : f
      ))
    }
  }

  const uploadAll = async () => {
    // Upload all pending files
    const pendingIndexes = files
      .map((f, i) => ({ file: f, index: i }))
      .filter(({ file }) => file.status === 'pending')

    for (const { file, index } of pendingIndexes) {
      await uploadFile(file, index)
    }
  }

  const clearCompleted = () => {
    setFiles(prev => prev.filter(f => f.status === 'pending' || f.status === 'uploading'))
  }

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
  }

  const getStatusColor = (status: UploadedFile['status']) => {
    switch (status) {
      case 'pending': return 'text-gray-500'
      case 'uploading': return 'text-blue-600'
      case 'processing': return 'text-blue-600'
      case 'success': return 'text-green-600'
      case 'error': return 'text-red-600'
      default: return 'text-gray-500'
    }
  }

  const getStatusText = (status: UploadedFile['status']) => {
    switch (status) {
      case 'pending': return 'Ready to upload'
      case 'uploading': return 'Uploading...'
      case 'processing': return 'Processing...'
      case 'success': return 'Success!'
      case 'error': return 'Failed'
      default: return 'Unknown'
    }
  }

  const pendingCount = files.filter(f => f.status === 'pending').length
  const successCount = files.filter(f => f.status === 'success').length
  const errorCount = files.filter(f => f.status === 'error').length

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Upload Receipts</h1>
              <p className="text-sm text-gray-500">Drag and drop your downloaded receipts</p>
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
        {/* Drop zone */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors ${
            isDragging
              ? 'border-blue-500 bg-blue-50'
              : 'border-gray-300 bg-white hover:border-gray-400'
          }`}
        >
          <svg
            className="mx-auto h-12 w-12 text-gray-400"
            stroke="currentColor"
            fill="none"
            viewBox="0 0 48 48"
          >
            <path
              d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <p className="mt-4 text-lg text-gray-600">
            Drag and drop your receipts here
          </p>
          <p className="mt-2 text-sm text-gray-500">
            or click to browse files
          </p>
          <p className="mt-1 text-xs text-gray-400">
            Supports PDF, JPG, PNG (max 10MB per file)
          </p>
          <input
            type="file"
            multiple
            accept=".pdf,.jpg,.jpeg,.png"
            onChange={handleFileSelect}
            className="hidden"
            id="file-upload"
          />
          <label
            htmlFor="file-upload"
            className="mt-6 inline-block px-6 py-3 text-white bg-blue-600 rounded-md hover:bg-blue-700 cursor-pointer font-medium"
          >
            Select Files
          </label>
        </div>

        {/* File list */}
        {files.length > 0 && (
          <div className="mt-8 bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
              <div>
                <h2 className="text-lg font-medium text-gray-900">Files</h2>
                <p className="text-sm text-gray-500">
                  {pendingCount} pending, {successCount} uploaded, {errorCount} failed
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={clearCompleted}
                  disabled={successCount === 0}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
                >
                  Clear Completed
                </button>
                <button
                  onClick={uploadAll}
                  disabled={pendingCount === 0}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
                >
                  Upload All ({pendingCount})
                </button>
              </div>
            </div>

            <div className="divide-y divide-gray-200">
              {files.map((uploadedFile, index) => (
                <div key={index} className="px-6 py-4 flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {uploadedFile.file.name}
                    </p>
                    <div className="flex items-center mt-1">
                      <p className={`text-sm ${getStatusColor(uploadedFile.status)}`}>
                        {getStatusText(uploadedFile.status)}
                      </p>
                      {uploadedFile.message && (
                        <p className="ml-2 text-sm text-gray-500">
                          - {uploadedFile.message}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="ml-4 flex items-center gap-2">
                    <span className="text-xs text-gray-400">
                      {(uploadedFile.file.size / 1024 / 1024).toFixed(2)} MB
                    </span>
                    {uploadedFile.status === 'pending' && (
                      <button
                        onClick={() => removeFile(index)}
                        className="text-red-600 hover:text-red-800 text-sm"
                      >
                        Remove
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Success message */}
        {successCount > 0 && (
          <div className="mt-6 bg-green-50 border border-green-200 rounded-lg p-4">
            <p className="text-sm text-green-800">
              {successCount} receipt{successCount !== 1 ? 's' : ''} uploaded successfully!{' '}
              <button
                onClick={() => router.push('/receipts')}
                className="underline font-medium"
              >
                View receipts
              </button>
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
