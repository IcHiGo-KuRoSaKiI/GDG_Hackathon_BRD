'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { FileText, Zap, Target, CheckCircle, ArrowRight, Moon, Sun } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { useAuthStore } from '@/lib/store/authStore'
import { useThemeStore } from '@/lib/store/themeStore'

const ease = [0.25, 0.1, 0.25, 1] as const

const fadeUp = {
  hidden: { opacity: 0, y: 12 },
  visible: (delay: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.35, delay, ease },
  }),
}

const staggerContainer = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.08 } },
}

const staggerItem = {
  hidden: { opacity: 0, y: 14 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.3, ease } },
}

export default function HomePage() {
  const router = useRouter()
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const { theme, toggleTheme } = useThemeStore()

  // Redirect to dashboard if already logged in
  useEffect(() => {
    if (isAuthenticated) {
      router.push('/dashboard')
    }
  }, [isAuthenticated, router])

  const features = [
    {
      icon: Zap,
      title: 'Lightning Fast',
      description: 'Generate comprehensive BRDs in seconds, not hours',
    },
    {
      icon: Target,
      title: 'AI-Powered',
      description: 'Advanced AI extracts requirements from any document',
    },
    {
      icon: CheckCircle,
      title: 'Cited Sources',
      description: 'Every requirement linked to original source documents',
    },
  ]

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-background">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <FileText className="h-6 w-6 text-primary" />
            <span className="text-sm font-mono uppercase tracking-wider font-bold text-foreground">BRD Generator</span>
          </div>
          <div className="flex items-center space-x-4">
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleTheme}
            >
              {theme === 'dark' ? (
                <Sun className="h-5 w-5" />
              ) : (
                <Moon className="h-5 w-5" />
              )}
            </Button>
            <Link href="/login">
              <Button variant="ghost">Login</Button>
            </Link>
            <Link href="/register">
              <Button>Get Started</Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main className="container mx-auto px-4 py-20">
        <motion.div
          variants={fadeUp}
          initial="hidden"
          animate="visible"
          custom={0}
          className="text-center max-w-4xl mx-auto"
        >
          <h1 className="text-4xl md:text-6xl font-bold mb-6 font-mono uppercase tracking-wider">
            Generate BRDs{' '}
            <span className="text-primary">from Chaos</span>
          </h1>
          <p className="text-lg text-muted-foreground mb-8 max-w-2xl mx-auto">
            Upload documents. AI extracts requirements. Get a comprehensive
            Business Requirements Document with cited sources.
          </p>
          <div className="flex items-center justify-center space-x-4">
            <Link href="/register">
              <Button size="lg" className="group">
                Get Started
                <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />
              </Button>
            </Link>
          </div>

          {/* Process Flow */}
          <motion.div
            variants={fadeUp}
            initial="hidden"
            animate="visible"
            custom={0.15}
            className="mt-16 flex items-center justify-center space-x-4 text-muted-foreground"
          >
            <div className="flex flex-col items-center">
              <div className="w-12 h-12 bg-primary/10 border border-primary/30 flex items-center justify-center mb-2">
                <FileText className="h-6 w-6 text-primary" />
              </div>
              <span className="text-sm">Upload</span>
            </div>
            <ArrowRight className="h-5 w-5" />
            <div className="flex flex-col items-center">
              <div className="w-12 h-12 bg-primary/10 border border-primary/30 flex items-center justify-center mb-2">
                <Zap className="h-6 w-6 text-primary" />
              </div>
              <span className="text-sm">AI Analyzes</span>
            </div>
            <ArrowRight className="h-5 w-5" />
            <div className="flex flex-col items-center">
              <div className="w-12 h-12 bg-primary/10 border border-primary/30 flex items-center justify-center mb-2">
                <CheckCircle className="h-6 w-6 text-primary" />
              </div>
              <span className="text-sm">BRD Ready</span>
            </div>
          </motion.div>
        </motion.div>

        {/* Features */}
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate="visible"
          className="mt-24 grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto"
        >
          {features.map((feature, index) => (
            <motion.div key={index} variants={staggerItem}>
              <Card className="h-full">
                <CardContent className="p-6">
                  <feature.icon className="h-12 w-12 text-primary mb-4" />
                  <h3 className="text-lg font-semibold mb-2">{feature.title}</h3>
                  <p className="text-muted-foreground">{feature.description}</p>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      </main>

      {/* Footer */}
      <footer className="border-t border-border mt-20">
        <div className="container mx-auto px-4 py-8 text-center text-muted-foreground">
          <p>© 2026 BRD Generator. Built with AI for the future.</p>
        </div>
      </footer>
    </div>
  )
}
