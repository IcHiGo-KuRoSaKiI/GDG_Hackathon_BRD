'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { FileText, Zap, Target, CheckCircle, ArrowRight, Moon, Sun, Brain, FileSearch, BarChart3 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { TextReveal, WordReveal } from '@/components/ui/text-reveal'
import { TiltCard } from '@/components/ui/tilt-card'
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
      icon: Brain,
      title: 'Agentic AI',
      description: 'Autonomous AI agent reads, analyzes, and synthesizes your documents into structured requirements',
    },
    {
      icon: FileSearch,
      title: 'Deep Analysis',
      description: 'Extracts functional specs, stakeholder needs, and edge cases from any document format',
    },
    {
      icon: BarChart3,
      title: 'Cited Sources',
      description: 'Every requirement traced back to original source documents with conflict detection',
    },
  ]

  return (
    <div className="min-h-screen bg-background dot-grid">
      {/* Header */}
      <header className="border-b border-border/50 bg-background/60 backdrop-blur-xl sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <FileText className="h-6 w-6 text-primary" />
            <span className="text-sm font-mono uppercase tracking-wider font-bold text-foreground">Sybil</span>
          </div>
          <div className="flex items-center space-x-2 md:space-x-4">
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
      <main className="container mx-auto px-4 py-12 md:py-20">
        <div className="text-center max-w-4xl mx-auto">
          <TextReveal
            text="Documents In."
            as="h1"
            className="text-3xl sm:text-4xl md:text-6xl font-bold mb-2 font-mono uppercase tracking-wider justify-center"
          />
          <TextReveal
            text="Requirements Out."
            as="h1"
            className="text-3xl sm:text-4xl md:text-6xl font-bold mb-6 font-mono uppercase tracking-wider justify-center text-primary"
            delay={0.6}
          />
          <WordReveal
            text="Sybil is an AI agent that reads your project documents and generates comprehensive Business Requirements Documents — with cited sources, conflict detection, and structured analysis."
            className="text-base md:text-lg text-muted-foreground mb-8 max-w-2xl mx-auto justify-center"
            delay={1.2}
          />
          <motion.div
            variants={fadeUp}
            initial="hidden"
            animate="visible"
            custom={1.8}
            className="flex items-center justify-center space-x-4"
          >
            <Link href="/register">
              <Button size="lg" className="group glow-hover">
                Start Building
                <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />
              </Button>
            </Link>
          </motion.div>

          {/* Process Flow */}
          <motion.div
            variants={fadeUp}
            initial="hidden"
            animate="visible"
            custom={2.2}
            className="mt-12 md:mt-16 flex items-center justify-center space-x-3 md:space-x-4 text-muted-foreground"
          >
            <div className="flex flex-col items-center">
              <div className="w-10 h-10 md:w-12 md:h-12 bg-primary/10 border border-primary/30 flex items-center justify-center mb-2 glow-hover">
                <FileText className="h-5 w-5 md:h-6 md:w-6 text-primary" />
              </div>
              <span className="text-xs md:text-sm">Upload</span>
            </div>
            <ArrowRight className="h-4 w-4 md:h-5 md:w-5" />
            <div className="flex flex-col items-center">
              <div className="w-10 h-10 md:w-12 md:h-12 bg-primary/10 border border-primary/30 flex items-center justify-center mb-2 glow-hover">
                <Brain className="h-5 w-5 md:h-6 md:w-6 text-primary" />
              </div>
              <span className="text-xs md:text-sm">AI Analyzes</span>
            </div>
            <ArrowRight className="h-4 w-4 md:h-5 md:w-5" />
            <div className="flex flex-col items-center">
              <div className="w-10 h-10 md:w-12 md:h-12 bg-primary/10 border border-primary/30 flex items-center justify-center mb-2 glow-hover">
                <CheckCircle className="h-5 w-5 md:h-6 md:w-6 text-primary" />
              </div>
              <span className="text-xs md:text-sm">BRD Ready</span>
            </div>
          </motion.div>
        </div>

        {/* Features */}
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate="visible"
          className="mt-16 md:mt-24 grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-6 max-w-5xl mx-auto"
        >
          {features.map((feature, index) => (
            <motion.div key={index} variants={staggerItem}>
              <TiltCard>
                <Card className="h-full border-glow-hover">
                  <CardContent className="p-6">
                    <feature.icon className="h-10 w-10 md:h-12 md:w-12 text-primary mb-4" />
                    <h3 className="text-lg font-semibold mb-2 font-mono">{feature.title}</h3>
                    <p className="text-sm text-muted-foreground">{feature.description}</p>
                  </CardContent>
                </Card>
              </TiltCard>
            </motion.div>
          ))}
        </motion.div>
      </main>

      {/* Footer */}
      <footer className="border-t border-border/50 mt-20">
        <div className="container mx-auto px-4 py-8 text-center text-muted-foreground text-sm">
          <p className="font-mono">Sybil &mdash; AI-powered requirements engineering</p>
        </div>
      </footer>
    </div>
  )
}
