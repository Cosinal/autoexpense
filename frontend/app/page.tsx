export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="text-center">
        <h1 className="text-4xl font-bold mb-4">AutoExpense</h1>
        <p className="text-xl text-gray-600 mb-8">
          Privacy-first expense receipt vault
        </p>
        <div className="space-y-2 text-sm text-gray-500">
          <p>✓ Forward receipts via email</p>
          <p>✓ Automatic OCR & parsing</p>
          <p>✓ Secure storage</p>
          <p>✓ CSV export</p>
        </div>
      </div>
    </main>
  );
}
