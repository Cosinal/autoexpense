'use client'

import { useEffect } from 'react'
import { createClient } from '@/lib/supabase'
import { useRouter } from 'next/navigation'
import Link from 'next/link'

export default function Home() {
  const router = useRouter()
  const supabase = createClient()

  useEffect(() => {
    checkAuth()
  }, [])

  const checkAuth = async () => {
    const { data: { user } } = await supabase.auth.getUser()

    if (user) {
      router.push('/receipts')
    }
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="text-center">
        <h1 className="text-4xl font-bold mb-4">AutoExpense</h1>
        <p className="text-xl text-gray-600 mb-8">
          Privacy-first expense receipt vault
        </p>
        <div className="space-y-2 text-sm text-gray-500 mb-8">
          <p>✓ Forward receipts via email</p>
          <p>✓ Automatic OCR & parsing</p>
          <p>✓ Secure storage</p>
          <p>✓ CSV export</p>
        </div>
        <Link
          href="/login"
          className="inline-block px-6 py-3 text-white bg-blue-600 rounded-md hover:bg-blue-700 font-medium"
        >
          Get Started
        </Link>
      </div>
    </main>
  );
}
