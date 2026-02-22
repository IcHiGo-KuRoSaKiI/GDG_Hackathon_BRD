'use client'

import { useState } from 'react'
import Link from 'next/link'
import { motion } from 'framer-motion'
import {
  FileText, Server, Database, Cloud, Brain, Shield, Upload,
  ArrowRight, ArrowDown, ChevronDown, ChevronUp,
  Moon, Sun, GitBranch, Layers, Cpu, Lock, Search,
  MessageSquare, CheckCircle, AlertTriangle, Filter,
  Zap, BarChart3, Hash, Globe, Box, Terminal,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { useAuthStore } from '@/lib/store/authStore'
import { useThemeStore } from '@/lib/store/themeStore'

// ── Animation variants ──────────────────────────────────

const ease = [0.25, 0.1, 0.25, 1] as const

const fadeUp = {
  hidden: { opacity: 0, y: 16 },
  visible: (delay: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.4, delay, ease },
  }),
}

const staggerContainer = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.06 } },
}

const staggerItem = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.3, ease } },
}

const pulseGlow = {
  animate: {
    boxShadow: [
      '0 0 0 0 hsl(18 100% 59% / 0)',
      '0 0 20px 4px hsl(18 100% 59% / 0.15)',
      '0 0 0 0 hsl(18 100% 59% / 0)',
    ],
    transition: { duration: 3, repeat: Infinity, ease: 'easeInOut' },
  },
}

// ── Reusable components ─────────────────────────────────

function SectionHeader({ number, title, subtitle }: { number: string; title: string; subtitle: string }) {
  return (
    <div className="mb-10 md:mb-14">
      <div className="flex items-center gap-3 mb-3">
        <span className="text-xs font-mono text-primary bg-primary/10 border border-primary/30 px-2 py-0.5">
          {number}
        </span>
        <div className="h-px flex-1 bg-border" />
      </div>
      <h2 className="text-2xl md:text-3xl font-bold font-mono uppercase tracking-wider mb-2">
        {title}
      </h2>
      <p className="text-muted-foreground text-sm md:text-base max-w-2xl">
        {subtitle}
      </p>
    </div>
  )
}

function FlowNode({
  icon: Icon,
  label,
  sublabel,
  variant = 'default',
  className = '',
  animate = false,
}: {
  icon: typeof FileText
  label: string
  sublabel?: string
  variant?: 'default' | 'primary' | 'accent' | 'muted'
  className?: string
  animate?: boolean
}) {
  const styles = {
    default: 'bg-card border-border',
    primary: 'bg-primary/10 border-primary/40',
    accent: 'bg-card border-primary/20',
    muted: 'bg-muted/50 border-border',
  }

  const Wrapper = animate ? motion.div : 'div'
  const wrapperProps = animate ? pulseGlow : {}

  return (
    <Wrapper
      {...(wrapperProps as any)}
      className={`flex flex-col items-center gap-1.5 p-3 md:p-4 border text-center min-w-[100px] ${styles[variant]} ${className}`}
    >
      <Icon className={`h-5 w-5 md:h-6 md:w-6 ${variant === 'primary' ? 'text-primary' : 'text-foreground/70'}`} />
      <span className="text-[11px] md:text-xs font-mono uppercase tracking-wider font-medium">{label}</span>
      {sublabel && <span className="text-[10px] text-muted-foreground">{sublabel}</span>}
    </Wrapper>
  )
}

function FlowArrow({ direction = 'right', className = '' }: { direction?: 'right' | 'down'; className?: string }) {
  return direction === 'right' ? (
    <div className={`flex items-center ${className}`}>
      <div className="w-6 md:w-10 h-px bg-primary/40" />
      <ArrowRight className="h-3 w-3 text-primary/60 -ml-1" />
    </div>
  ) : (
    <div className={`flex flex-col items-center ${className}`}>
      <div className="h-6 md:h-8 w-px bg-primary/40" />
      <ArrowDown className="h-3 w-3 text-primary/60 -mt-1" />
    </div>
  )
}

function TechBadge({ label }: { label: string }) {
  return (
    <span className="inline-block text-[10px] font-mono px-1.5 py-0.5 bg-primary/8 border border-primary/20 text-primary/80">
      {label}
    </span>
  )
}

function ExpandableDetail({ title, children }: { title: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="border border-border bg-card/50">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-muted/30 transition-colors"
      >
        <span className="text-sm font-mono font-medium">{title}</span>
        {open ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
      </button>
      {open && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          transition={{ duration: 0.2 }}
          className="px-4 pb-4 text-sm text-muted-foreground space-y-2"
        >
          {children}
        </motion.div>
      )}
    </div>
  )
}

// ── Section 1: Infrastructure ───────────────────────────

function InfrastructureSection() {
  return (
    <section id="infrastructure">
      <SectionHeader
        number="01"
        title="Infrastructure"
        subtitle="Cloud-native architecture on Google Cloud Platform with Vercel edge delivery and Terraform-managed infrastructure."
      />

      <motion.div
        variants={staggerContainer}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: '-80px' }}
        className="space-y-8"
      >
        {/* Main architecture diagram */}
        <motion.div variants={staggerItem}>
          <Card className="border-border/50 overflow-hidden">
            <CardContent className="p-6 md:p-8">
              {/* Client tier */}
              <div className="flex flex-col items-center gap-2 mb-2">
                <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest">Client Tier</span>
              </div>

              <div className="flex flex-col md:flex-row items-center justify-center gap-4 md:gap-6 mb-8">
                <FlowNode icon={Globe} label="Next.js 14" sublabel="Vercel CDN + Edge" variant="accent" />
                <FlowArrow direction="right" className="hidden md:flex" />
                <FlowArrow direction="down" className="md:hidden" />
                <FlowNode icon={Lock} label="JWT Auth" sublabel="HS256 + bcrypt" variant="muted" />
                <FlowArrow direction="right" className="hidden md:flex" />
                <FlowArrow direction="down" className="md:hidden" />
                <FlowNode icon={Server} label="FastAPI" sublabel="Cloud Run" variant="primary" animate />
              </div>

              <FlowArrow direction="down" className="mx-auto" />

              {/* Services tier */}
              <div className="flex flex-col items-center gap-2 mt-4 mb-4">
                <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest">Services Tier</span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-8">
                {[
                  { icon: Database, label: 'Firestore', sub: 'NoSQL Database' },
                  { icon: Cloud, label: 'Cloud Storage', sub: 'Document Files' },
                  { icon: Brain, label: 'Gemini 2.5 Pro', sub: 'AI Engine' },
                  { icon: Box, label: 'Artifact Registry', sub: 'Docker Images' },
                ].map((item) => (
                  <FlowNode key={item.label} icon={item.icon} label={item.label} sublabel={item.sub} variant="default" />
                ))}
              </div>

              <FlowArrow direction="down" className="mx-auto" />

              {/* Infrastructure tier */}
              <div className="flex flex-col items-center gap-2 mt-4 mb-4">
                <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest">Infrastructure as Code</span>
              </div>

              <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
                <FlowNode icon={Terminal} label="Terraform" sublabel="Cloud Run + Registry" variant="muted" />
                <FlowNode icon={Layers} label="deploy.sh" sublabel="Build + Push + Apply" variant="muted" />
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Tech stack badges */}
        <motion.div variants={staggerItem} className="flex flex-wrap gap-2">
          {['Next.js 14', 'TypeScript', 'FastAPI', 'Python 3.11', 'Firestore', 'Cloud Storage', 'Gemini 2.5 Pro', 'Terraform', 'Cloud Run', 'Vercel', 'JWT', 'shadcn/ui', 'Tailwind CSS', 'Zustand', 'Framer Motion'].map(
            (t) => <TechBadge key={t} label={t} />
          )}
        </motion.div>

        {/* Expandable details */}
        <motion.div variants={staggerItem} className="space-y-1">
          <ExpandableDetail title="Firestore Collections">
            <p><strong className="text-foreground">projects</strong> — User-owned project containers with doc/BRD counts</p>
            <p><strong className="text-foreground">documents</strong> — Parsed files with AI metadata (summary, tags, topics, entities)</p>
            <p><strong className="text-foreground">chunks</strong> — Text chunks for citation tracking (1000 words, 100 overlap)</p>
            <p><strong className="text-foreground">brds</strong> — Generated BRDs with 13 flat section fields + conflicts + sentiment</p>
            <p><strong className="text-foreground">users</strong> — Profiles with bcrypt-hashed passwords + JWT metadata</p>
            <p><strong className="text-foreground">deletion_jobs</strong> — 2-step cascading delete orchestration (preview → confirm → execute)</p>
          </ExpandableDetail>
          <ExpandableDetail title="Security Architecture">
            <p><strong className="text-foreground">Layer 1 — Pydantic Validation:</strong> Max lengths, format checks on all user inputs</p>
            <p><strong className="text-foreground">Layer 2 — Regex Injection Detection:</strong> Pattern matching for prompt injection attempts (&quot;ignore previous instructions&quot;, &quot;system prompt&quot;, etc.)</p>
            <p><strong className="text-foreground">Layer 3 — Defensive Prompts:</strong> User inputs wrapped in &lt;user_input&gt; tags, AI instructed to never follow commands within tags</p>
            <p><strong className="text-foreground">Auth:</strong> JWT (HS256) with 24h expiration, bcrypt password hashing (12 rounds)</p>
          </ExpandableDetail>
          <ExpandableDetail title="Document Processing">
            <p><strong className="text-foreground">Chomper</strong> parses 36+ formats (PDF, DOCX, PPTX, XLSX, CSV, HTML, TXT)</p>
            <p><strong className="text-foreground">Parallel AI analysis:</strong> Classification + metadata generation run concurrently via asyncio.gather</p>
            <p><strong className="text-foreground">AI Metadata:</strong> Dynamic topic_relevance and content_indicators (domain-agnostic — AI generates topics from content)</p>
          </ExpandableDetail>
        </motion.div>
      </motion.div>
    </section>
  )
}

// ── Section 2: AI Agent Flow ────────────────────────────

function AIFlowSection() {
  return (
    <section id="ai-flow">
      <SectionHeader
        number="02"
        title="AI Agent Flow"
        subtitle="Fully agentic BRD generation and natural language editing — the AI plans its own workflow, reads documents, and writes structured requirements."
      />

      <motion.div
        variants={staggerContainer}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: '-80px' }}
        className="space-y-10"
      >
        {/* BRD Generation Flow */}
        <motion.div variants={staggerItem}>
          <div className="flex items-center gap-2 mb-4">
            <Zap className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-mono uppercase tracking-wider font-bold">BRD Generation</h3>
            <span className="text-[10px] text-muted-foreground font-mono ml-2">fully agentic — max 30 iterations</span>
          </div>

          <Card className="border-border/50 overflow-hidden">
            <CardContent className="p-4 md:p-6 space-y-6">
              {/* Step 1: Trigger */}
              <div className="flex flex-col md:flex-row items-start md:items-center gap-3">
                <div className="shrink-0 w-7 h-7 bg-primary/10 border border-primary/30 flex items-center justify-center">
                  <span className="text-[11px] font-mono font-bold text-primary">1</span>
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium">User clicks &ldquo;Generate BRD&rdquo;</p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    POST /brds/generate — fire-and-forget background task, returns 202 Accepted
                  </p>
                </div>
              </div>

              {/* Step 2: Discovery */}
              <div className="flex flex-col md:flex-row items-start md:items-center gap-3">
                <div className="shrink-0 w-7 h-7 bg-primary/10 border border-primary/30 flex items-center justify-center">
                  <span className="text-[11px] font-mono font-bold text-primary">2</span>
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium">AI discovers documents</p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Calls <code className="text-primary/80">list_project_documents()</code> — gets doc list with AI metadata (summaries, tags, topics)
                  </p>
                </div>
                <TechBadge label="real tool" />
              </div>

              {/* Step 3: Deep Read */}
              <div className="flex flex-col md:flex-row items-start md:items-center gap-3">
                <div className="shrink-0 w-7 h-7 bg-primary/10 border border-primary/30 flex items-center justify-center">
                  <span className="text-[11px] font-mono font-bold text-primary">3</span>
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium">AI reads full document text</p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Calls <code className="text-primary/80">get_full_document_text()</code> — reads entire document, not chunks. No RAG = no context loss.
                  </p>
                </div>
                <TechBadge label="real tool" />
              </div>

              {/* Step 4: Cross-reference */}
              <div className="flex flex-col md:flex-row items-start md:items-center gap-3">
                <div className="shrink-0 w-7 h-7 bg-primary/10 border border-primary/30 flex items-center justify-center">
                  <span className="text-[11px] font-mono font-bold text-primary">4</span>
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium">AI cross-references documents</p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Calls <code className="text-primary/80">search_documents_by_topic()</code> and <code className="text-primary/80">search_documents_by_content()</code>
                  </p>
                </div>
                <TechBadge label="real tool" />
              </div>

              {/* Step 5: Section writing */}
              <div className="flex flex-col md:flex-row items-start md:items-center gap-3">
                <div className="shrink-0 w-7 h-7 bg-primary border border-primary flex items-center justify-center">
                  <span className="text-[11px] font-mono font-bold text-primary-foreground">5</span>
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium">AI writes 13 BRD sections</p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Calls <code className="text-primary/80">submit_brd_section()</code> &times;13 — <strong>virtual tool</strong> (intercepted, not executed). Each section includes markdown content + citations.
                  </p>
                  <div className="flex flex-wrap gap-1 mt-2">
                    {['executive_summary', 'business_objectives', 'stakeholders', 'functional_requirements', 'non_functional_requirements', 'assumptions', 'success_metrics', 'timeline', 'project_background', 'project_scope', 'dependencies', 'risks', 'cost_benefit'].map((s) => (
                      <span key={s} className="text-[9px] font-mono px-1 py-0.5 bg-muted border border-border text-muted-foreground">
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
                <TechBadge label="virtual tool" />
              </div>

              {/* Step 6: Analysis */}
              <div className="flex flex-col md:flex-row items-start md:items-center gap-3">
                <div className="shrink-0 w-7 h-7 bg-primary border border-primary flex items-center justify-center">
                  <span className="text-[11px] font-mono font-bold text-primary-foreground">6</span>
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium">AI submits conflict + sentiment analysis</p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Calls <code className="text-primary/80">submit_analysis()</code> — detects contradictions across documents, extracts stakeholder sentiment, lists key concerns
                  </p>
                </div>
                <TechBadge label="virtual tool" />
              </div>

              {/* Step 7: Assembly */}
              <div className="flex flex-col md:flex-row items-start md:items-center gap-3">
                <div className="shrink-0 w-7 h-7 bg-primary/10 border border-primary/30 flex items-center justify-center">
                  <span className="text-[11px] font-mono font-bold text-primary">7</span>
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium">Backend assembles BRD</p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Collects all virtual tool outputs → builds BRD model → stores in Firestore. Frontend polls and detects new BRD.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Virtual Tool Pattern explanation */}
        <motion.div variants={staggerItem}>
          <Card className="border-primary/20 bg-primary/[0.03]">
            <CardContent className="p-4 md:p-6">
              <div className="flex items-start gap-3">
                <AlertTriangle className="h-5 w-5 text-primary shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-sm font-mono font-bold mb-2">Why Virtual Tools?</h4>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Gemini API cannot combine <code className="text-primary/80">tools</code> (function calling) with{' '}
                    <code className="text-primary/80">response_mime_type: &quot;application/json&quot;</code> (structured output) in the same request.
                    Our workaround: define virtual tools that the AI &ldquo;calls&rdquo; — but the backend intercepts the function call arguments as structured data instead of executing them.
                    This gives us both agentic tool-calling AND structured output in one pipeline.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Natural Language Editing Flow */}
        <motion.div variants={staggerItem}>
          <div className="flex items-center gap-2 mb-4">
            <MessageSquare className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-mono uppercase tracking-wider font-bold">Natural Language Editing</h3>
            <span className="text-[10px] text-muted-foreground font-mono ml-2">unified chat — max 8 iterations</span>
          </div>

          <Card className="border-border/50">
            <CardContent className="p-4 md:p-6">
              <div className="flex flex-col lg:flex-row items-stretch gap-4">
                {/* Left: User interaction */}
                <div className="flex-1 space-y-3">
                  <p className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest mb-2">User Interaction</p>

                  <div className="flex items-center gap-2 p-3 bg-muted/30 border border-border">
                    <Search className="h-4 w-4 text-muted-foreground shrink-0" />
                    <span className="text-xs">Select text in BRD viewer</span>
                  </div>
                  <FlowArrow direction="down" className="mx-auto" />
                  <div className="flex items-center gap-2 p-3 bg-muted/30 border border-border">
                    <MessageSquare className="h-4 w-4 text-primary shrink-0" />
                    <span className="text-xs">&ldquo;Make this more concise&rdquo;</span>
                  </div>
                  <FlowArrow direction="down" className="mx-auto" />
                  <div className="flex items-center gap-2 p-3 bg-primary/10 border border-primary/30">
                    <CheckCircle className="h-4 w-4 text-primary shrink-0" />
                    <span className="text-xs font-medium">Accept &amp; Replace — or Iterate</span>
                  </div>
                </div>

                {/* Divider */}
                <div className="hidden lg:block w-px bg-border" />
                <div className="lg:hidden h-px bg-border" />

                {/* Right: Backend processing */}
                <div className="flex-1 space-y-3">
                  <p className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest mb-2">Backend Processing</p>

                  <div className="p-3 bg-muted/30 border border-border">
                    <div className="flex items-center gap-2 mb-1">
                      <Shield className="h-3.5 w-3.5 text-warning shrink-0" />
                      <span className="text-xs font-medium">3-Layer Security</span>
                    </div>
                    <p className="text-[10px] text-muted-foreground">Pydantic → Regex injection scan → Defensive prompt wrapping</p>
                  </div>

                  <div className="p-3 bg-muted/30 border border-border">
                    <div className="flex items-center gap-2 mb-1">
                      <Brain className="h-3.5 w-3.5 text-primary shrink-0" />
                      <span className="text-xs font-medium">AI Self-Classification</span>
                    </div>
                    <p className="text-[10px] text-muted-foreground">
                      AI calls <code className="text-primary/80">submit_response(content, type)</code>
                    </p>
                    <div className="flex gap-1 mt-1.5">
                      <span className="text-[9px] font-mono px-1 py-0.5 bg-primary/10 border border-primary/20 text-primary">refinement</span>
                      <span className="text-[9px] font-mono px-1 py-0.5 bg-muted border border-border text-muted-foreground">answer</span>
                      <span className="text-[9px] font-mono px-1 py-0.5 bg-primary/10 border border-primary/20 text-primary">generation</span>
                    </div>
                  </div>

                  <div className="p-3 bg-muted/30 border border-border">
                    <div className="flex items-center gap-2 mb-1">
                      <Cpu className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                      <span className="text-xs font-medium">Frontend Response</span>
                    </div>
                    <p className="text-[10px] text-muted-foreground">
                      refinement/generation → &ldquo;Accept &amp; Replace&rdquo; bar | answer → plain chat message
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={staggerItem} className="space-y-1">
          <ExpandableDetail title="Real vs Virtual Tools">
            <p><strong className="text-foreground">Real tools</strong> execute actual backend functions — list_project_documents, get_full_document_text, search_documents_by_topic, search_documents_by_content</p>
            <p><strong className="text-foreground">Virtual tools</strong> are intercepted before execution — submit_brd_section, submit_analysis, submit_response. The backend extracts the function call arguments as structured JSON data.</p>
            <p><strong className="text-foreground">Why?</strong> Gemini API limitation: tools + response_mime_type cannot coexist. Virtual tools give us structured output through function calling.</p>
          </ExpandableDetail>
          <ExpandableDetail title="Token Configuration">
            <p><strong className="text-foreground">BRD Generation:</strong> 65,536 output tokens, max 30 iterations, temperature 0.2</p>
            <p><strong className="text-foreground">Chat/Refinement:</strong> 16,384 output tokens, max 8 iterations, temperature 0.2</p>
            <p><strong className="text-foreground">Lesson learned:</strong> Initial 8,192 token limit caused empty responses — Gemini ran out of output space after reading documents. Raised to 65,536.</p>
          </ExpandableDetail>
        </motion.div>
      </motion.div>
    </section>
  )
}

// ── Section 3: Enron Preprocessing ──────────────────────

function PreprocessingSection() {
  return (
    <section id="preprocessing">
      <SectionHeader
        number="03"
        title="Data Preprocessing"
        subtitle="Multi-tier NLP funnel that filters 517K Enron emails down to curated project datasets using heuristic scoring and semantic embeddings."
      />

      <motion.div
        variants={staggerContainer}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: '-80px' }}
        className="space-y-8"
      >
        {/* Funnel visualization */}
        <motion.div variants={staggerItem}>
          <Card className="border-border/50 overflow-hidden">
            <CardContent className="p-4 md:p-6">
              {/* Tier 0 */}
              <div className="relative">
                <div className="flex items-center gap-3 mb-3">
                  <span className="text-[10px] font-mono text-muted-foreground bg-muted px-1.5 py-0.5 border border-border">TIER 0</span>
                  <span className="text-xs font-medium">Parse &amp; Stream</span>
                  <span className="text-[10px] text-muted-foreground ml-auto font-mono">517,401 emails</span>
                </div>
                <div className="ml-4 pl-4 border-l-2 border-primary/20 pb-6">
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                    <div className="p-2.5 bg-muted/30 border border-border">
                      <p className="text-[10px] font-mono text-muted-foreground mb-1">enron_loader.py</p>
                      <p className="text-xs">Stream CSV in 5000-row batches</p>
                      <p className="text-[10px] text-muted-foreground mt-1">Parse RFC 822 headers + body</p>
                    </div>
                    <div className="p-2.5 bg-muted/30 border border-border">
                      <p className="text-[10px] font-mono text-muted-foreground mb-1">Deduplication</p>
                      <p className="text-xs">Key: subject + sender + date</p>
                      <p className="text-[10px] text-muted-foreground mt-1">Normalize Re:/FW: prefixes</p>
                    </div>
                    <div className="p-2.5 bg-muted/30 border border-border">
                      <p className="text-[10px] font-mono text-muted-foreground mb-1">Parallel</p>
                      <p className="text-xs">multiprocessing.Pool</p>
                      <p className="text-[10px] text-muted-foreground mt-1">CPU-bound parsing distributed</p>
                    </div>
                  </div>
                </div>

                {/* Tier 1 */}
                <div className="flex items-center gap-3 mb-3">
                  <span className="text-[10px] font-mono text-primary bg-primary/10 px-1.5 py-0.5 border border-primary/30">TIER 1</span>
                  <span className="text-xs font-medium">Heuristic Filter</span>
                  <span className="text-[10px] text-muted-foreground ml-auto font-mono">517K → 78K (15%)</span>
                </div>
                <div className="ml-4 pl-4 border-l-2 border-primary/30 pb-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div className="space-y-1.5">
                      <p className="text-[10px] font-mono text-success uppercase">Positive Signals</p>
                      {[
                        ['+0.30', 'BRD keywords in body'],
                        ['+0.20', 'BRD keywords in subject'],
                        ['+0.15', 'Targeted (1-10 recipients)'],
                        ['+0.15', 'Substantial body (50-500 words)'],
                        ['+0.10', 'Action language (?, "please review")'],
                        ['+0.10', 'Good folder (inbox, sent)'],
                      ].map(([score, label]) => (
                        <div key={label} className="flex items-center gap-2 text-xs">
                          <span className="font-mono text-success text-[10px] w-10 shrink-0">{score}</span>
                          <span className="text-muted-foreground">{label}</span>
                        </div>
                      ))}
                    </div>
                    <div className="space-y-1.5">
                      <p className="text-[10px] font-mono text-destructive uppercase">Negative Signals</p>
                      {[
                        ['-0.30', 'Noise keywords (lunch, birthday)'],
                        ['-0.20', 'Noise subject patterns (FW: FW:)'],
                        ['-0.20', 'Mass email (20+ recipients)'],
                        ['-0.15', 'Noise folder (deleted_items, spam)'],
                        ['-0.10', 'Trivially short (<15 words)'],
                      ].map(([score, label]) => (
                        <div key={label} className="flex items-center gap-2 text-xs">
                          <span className="font-mono text-destructive text-[10px] w-10 shrink-0">{score}</span>
                          <span className="text-muted-foreground">{label}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-1">
                    <span className="text-[9px] font-mono px-1 py-0.5 bg-muted border border-border text-muted-foreground">47 BRD keywords</span>
                    <span className="text-[9px] font-mono px-1 py-0.5 bg-muted border border-border text-muted-foreground">50+ generic subjects</span>
                    <span className="text-[9px] font-mono px-1 py-0.5 bg-muted border border-border text-muted-foreground">12 newsletter patterns</span>
                    <span className="text-[9px] font-mono px-1 py-0.5 bg-muted border border-border text-muted-foreground">9 junk folders</span>
                  </div>
                </div>

                {/* Tier 2 */}
                <div className="flex items-center gap-3 mb-3">
                  <span className="text-[10px] font-mono text-primary bg-primary/10 px-1.5 py-0.5 border border-primary/30">TIER 2</span>
                  <span className="text-xs font-medium">Embedding Filter</span>
                  <span className="text-[10px] text-muted-foreground ml-auto font-mono">78K → 2K (top 2.5%)</span>
                </div>
                <div className="ml-4 pl-4 border-l-2 border-primary/40 pb-6">
                  <div className="space-y-2">
                    <div className="flex flex-col sm:flex-row gap-2">
                      <div className="flex-1 p-2.5 bg-muted/30 border border-border">
                        <p className="text-[10px] font-mono text-primary mb-1">Gemini text-embedding-004</p>
                        <p className="text-xs text-muted-foreground">768-dim vectors for all emails + 10 seed queries</p>
                      </div>
                      <div className="flex-1 p-2.5 bg-muted/30 border border-border">
                        <p className="text-[10px] font-mono text-primary mb-1">Cosine Similarity</p>
                        <p className="text-xs text-muted-foreground">Each email scored against all BRD seed queries</p>
                      </div>
                    </div>
                    <div className="p-2.5 bg-primary/[0.04] border border-primary/20">
                      <p className="text-xs">
                        <strong className="text-foreground">Combined score:</strong>{' '}
                        <code className="text-primary/80 text-[11px]">0.3 &times; heuristic + 0.7 &times; embedding</code>
                      </p>
                      <p className="text-[10px] text-muted-foreground mt-1">Cost: ~$0.10 for 50K emails &bull; Speed: ~5 min with batching + concurrency</p>
                    </div>
                  </div>
                </div>

                {/* Tier 3 */}
                <div className="flex items-center gap-3 mb-3">
                  <span className="text-[10px] font-mono text-muted-foreground bg-muted px-1.5 py-0.5 border border-border">TIER 3</span>
                  <span className="text-xs font-medium">Export &amp; Upload</span>
                  <span className="text-[10px] text-muted-foreground ml-auto font-mono">→ Sybil project</span>
                </div>
                <div className="ml-4 pl-4 border-l-2 border-border">
                  <p className="text-xs text-muted-foreground">
                    Export filtered emails as .txt files → Upload to Sybil API in batches (5 files/batch, 2s delay) → Chomper parses → Gemini classifies → Ready for BRD generation
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Auto-Discovery Phase */}
        <motion.div variants={staggerItem}>
          <div className="flex items-center gap-2 mb-4">
            <Search className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-mono uppercase tracking-wider font-bold">Auto-Discovery</h3>
            <span className="text-[10px] text-muted-foreground font-mono ml-2">eda_discover.py — finds project threads automatically</span>
          </div>

          <Card className="border-border/50">
            <CardContent className="p-4 md:p-6">
              <div className="space-y-3">
                <div className="p-3 bg-muted/30 border border-border">
                  <p className="text-xs font-medium mb-1">Thread Scoring Formula</p>
                  <code className="text-[11px] text-primary/80 block font-mono leading-relaxed">
                    score = email_count &times; capped_senders &times; log2(avg_words)<br />
                    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&times; project_indicator_bonus (10x)<br />
                    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&times; brd_signal_density_bonus (1-4x)<br />
                    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&times; blast_email_penalty (0.5x)
                  </code>
                </div>
                <div className="p-3 bg-muted/30 border border-border">
                  <p className="text-xs font-medium mb-1">Output per Project</p>
                  <p className="text-[10px] text-muted-foreground">
                    Rank, name, discovery score, email count, unique senders, extracted keywords (TF, no IDF), 5 auto-generated seed queries for embedding filter
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* ML techniques table */}
        <motion.div variants={staggerItem}>
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-mono uppercase tracking-wider font-bold">ML Techniques Used</h3>
          </div>

          <Card className="border-border/50">
            <CardContent className="p-0 overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-border bg-muted/30">
                    <th className="text-left p-3 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">Technique</th>
                    <th className="text-left p-3 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">Location</th>
                    <th className="text-left p-3 font-mono text-[10px] uppercase tracking-wider text-muted-foreground">Purpose</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    ['Gemini text-embedding-004', 'embedding_filter.py', 'Semantic email representation (768-dim vectors)'],
                    ['Cosine similarity', 'embedding_filter.py', 'Relevance scoring vs BRD seed queries'],
                    ['Term frequency (TF)', 'eda_discover.py', 'Keyword extraction (no IDF, stopwords removed)'],
                    ['Weighted feature scoring', 'heuristic_filter.py', 'Rule-based relevance classification'],
                    ['Hybrid ranking', 'curate_project.py', '0.3 heuristic + 0.7 embedding combination'],
                  ].map(([tech, loc, purpose], i) => (
                    <tr key={i} className="border-b border-border/50 last:border-0">
                      <td className="p-3 font-medium">{tech}</td>
                      <td className="p-3 font-mono text-primary/80">{loc}</td>
                      <td className="p-3 text-muted-foreground">{purpose}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>

          <p className="text-xs text-muted-foreground mt-3 italic">
            No custom models were trained. The pipeline uses pre-trained Gemini embeddings combined with hand-crafted heuristic features — standard NLP practice when labeled training data is unavailable.
          </p>
        </motion.div>

        <motion.div variants={staggerItem} className="space-y-1">
          <ExpandableDetail title="Why Heuristics + Embeddings (Not Pure ML)?">
            <p><strong className="text-foreground">No labeled data:</strong> We had no &ldquo;this email is BRD-relevant&rdquo; labels to train a classifier</p>
            <p><strong className="text-foreground">Cost efficiency:</strong> Heuristics are free; embeddings cost ~$0.10 for 50K emails; a fine-tuned model costs orders of magnitude more</p>
            <p><strong className="text-foreground">Interpretability:</strong> Every filtering decision can be traced to specific rules and scores</p>
            <p><strong className="text-foreground">Speed:</strong> Full pipeline runs in ~10 minutes on 500K emails</p>
          </ExpandableDetail>
          <ExpandableDetail title="What's Hardcoded?">
            <p><strong className="text-foreground">9 junk folders</strong> — deleted_items, spam, calendar, etc.</p>
            <p><strong className="text-foreground">50+ generic subjects</strong> — &ldquo;hi&rdquo;, &ldquo;lunch&rdquo;, &ldquo;meeting&rdquo;, &ldquo;fyi&rdquo;, etc.</p>
            <p><strong className="text-foreground">12 newsletter patterns</strong> — regex for &ldquo;daily report&rdquo;, &ldquo;press release&rdquo;, etc.</p>
            <p><strong className="text-foreground">47 BRD keywords</strong> — &ldquo;requirements&rdquo;, &ldquo;stakeholder&rdquo;, &ldquo;timeline&rdquo;, etc.</p>
            <p><strong className="text-foreground">Scoring weights</strong> — 0.30, 0.20, 0.15, etc.</p>
            <p className="mt-2 italic">This is standard feature engineering — the same approach used in production NLP systems. The keyword lists encode domain knowledge about BRD relevance.</p>
          </ExpandableDetail>
        </motion.div>
      </motion.div>
    </section>
  )
}

// ── Main Page ───────────────────────────────────────────

export default function ArchitecturePage() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const { theme, toggleTheme } = useThemeStore()

  return (
    <div className="min-h-screen bg-background dot-grid">
      {/* Header */}
      <header className="border-b border-border/50 bg-background/60 backdrop-blur-xl sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="flex items-center space-x-2">
              <FileText className="h-6 w-6 text-primary" />
              <span className="text-sm font-mono uppercase tracking-wider font-bold text-foreground">Sybil</span>
            </Link>
            <div className="w-px h-5 bg-border" />
            <span className="text-xs font-mono text-muted-foreground uppercase tracking-wider">Architecture</span>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="icon" onClick={toggleTheme}>
              {theme === 'dark' ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
            </Button>
            {isAuthenticated ? (
              <Link href="/dashboard">
                <Button variant="ghost" size="sm">Dashboard</Button>
              </Link>
            ) : (
              <Link href="/login">
                <Button variant="ghost" size="sm">Login</Button>
              </Link>
            )}
          </div>
        </div>
      </header>

      {/* Hero */}
      <div className="container mx-auto px-4 py-12 md:py-16">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease }}
        >
          <h1 className="text-3xl md:text-5xl font-bold font-mono uppercase tracking-wider mb-4">
            System Architecture
          </h1>
          <p className="text-muted-foreground text-sm md:text-base max-w-2xl mb-8">
            How Sybil transforms raw documents into structured Business Requirements Documents — from infrastructure to AI agent orchestration to data preprocessing.
          </p>

          {/* Jump links */}
          <div className="flex flex-wrap gap-2">
            {[
              { href: '#infrastructure', label: '01 Infrastructure' },
              { href: '#ai-flow', label: '02 AI Agent Flow' },
              { href: '#preprocessing', label: '03 Data Preprocessing' },
            ].map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="text-xs font-mono px-3 py-1.5 border border-border bg-card hover:border-primary/40 hover:bg-primary/5 transition-colors"
              >
                {link.label}
              </a>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Sections */}
      <div className="container mx-auto px-4 pb-20 space-y-20 md:space-y-28">
        <InfrastructureSection />
        <AIFlowSection />
        <PreprocessingSection />
      </div>

      {/* Footer */}
      <footer className="border-t border-border/50">
        <div className="container mx-auto px-4 py-8 text-center text-muted-foreground text-sm">
          <p className="font-mono">Sybil &mdash; AI-powered requirements engineering</p>
        </div>
      </footer>
    </div>
  )
}
