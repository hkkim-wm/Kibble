import { useEffect, useState } from 'react'

interface ToastItem { id: number; message: string }
let toastId = 0
let toastListener: ((msg: string) => void) | null = null

export function showToast(message: string) { toastListener?.(message) }

export default function ToastContainer() {
  const [toasts, setToasts] = useState<ToastItem[]>([])
  useEffect(() => {
    toastListener = (message) => {
      const id = ++toastId
      setToasts(prev => [...prev, { id, message }])
      setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000)
    }
    return () => { toastListener = null }
  }, [])
  return (
    <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50 flex flex-col gap-2">
      {toasts.map(t => (
        <div key={t.id} className="bg-gray-800 text-white px-4 py-2 rounded-lg shadow-lg text-sm">
          {t.message}
        </div>
      ))}
    </div>
  )
}
