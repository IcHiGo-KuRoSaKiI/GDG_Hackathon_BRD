'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Sidebar } from '@/components/layout/Sidebar'
import { useAuthStore } from '@/lib/store/authStore'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const router = useRouter()
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [hasMounted, setHasMounted] = useState(false)

  useEffect(() => {
    setHasMounted(true)
  }, [])

  useEffect(() => {
    if (hasMounted && !isAuthenticated) {
      router.push('/login')
    }
  }, [hasMounted, isAuthenticated, router])

  if (!hasMounted || !isAuthenticated) {
    return null
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      <Sidebar mobileOpen={sidebarOpen} onMobileOpenChange={setSidebarOpen} />

      <main className="flex-1 overflow-y-auto bg-background">
        {children}
      </main>
    </div>
  )
}
