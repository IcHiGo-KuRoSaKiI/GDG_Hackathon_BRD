import apiClient from './client'

export interface BRDSection {
  title: string
  content: string
  citations?: Array<{
    id: string
    text: string
    source: string
    document_id: string
  }>
}

export interface Conflict {
  id: string
  conflict_type: string
  severity: 'low' | 'medium' | 'high'
  description: string
  affected_requirements: string[]
  sources: string[]
}

export interface SentimentAnalysis {
  overall: string
  by_stakeholder?: Record<string, string>
  by_topic?: Record<string, string>
}

export interface BRD {
  id: string
  project_id: string
  status: 'processing' | 'complete' | 'failed'
  sections: {
    executive_summary?: BRDSection
    business_objectives?: BRDSection
    stakeholders?: BRDSection
    project_scope?: BRDSection
    functional_requirements?: BRDSection
    non_functional_requirements?: BRDSection
    assumptions?: BRDSection
    success_metrics?: BRDSection
    timeline?: BRDSection
    project_background?: BRDSection
    dependencies?: BRDSection
    risks?: BRDSection
    cost_benefit?: BRDSection
  }
  conflicts?: Conflict[]
  sentiment?: SentimentAnalysis
  created_at: string
  updated_at: string
  processing_stage?: string
  processing_progress?: number
}

export interface GenerateBRDRequest {
  project_id?: string
  include_conflicts?: boolean
  include_sentiment?: boolean
}

// ---------------------------------------------------------------------------
// Backend → Frontend transform
// ---------------------------------------------------------------------------
// Backend BRD model uses different field names and a flat section structure.
// This function maps the backend response into the frontend BRD interface.

const SECTION_KEYS = [
  'executive_summary',
  'business_objectives',
  'stakeholders',
  'project_scope',
  'functional_requirements',
  'non_functional_requirements',
  'assumptions',
  'success_metrics',
  'timeline',
  'project_background',
  'dependencies',
  'risks',
  'cost_benefit',
] as const

function transformCitations(
  citations?: Array<Record<string, any>>
): BRDSection['citations'] {
  if (!citations || citations.length === 0) return undefined
  return citations.map((c, i) => ({
    id: String(i + 1),
    text: c.quote ?? c.text ?? '',
    source: c.filename ?? c.source ?? '',
    document_id: c.doc_id ?? c.document_id ?? '',
  }))
}

function transformSection(raw: any): BRDSection | undefined {
  if (!raw || !raw.content) return undefined
  return {
    title: raw.title ?? '',
    content: raw.content,
    citations: transformCitations(raw.citations),
  }
}

function transformConflicts(raw?: any[]): Conflict[] | undefined {
  if (!raw || raw.length === 0) return undefined
  return raw.map((c, i) => ({
    id: c.id ?? String(i + 1),
    conflict_type: c.conflict_type ?? 'unknown',
    severity: c.severity ?? 'medium',
    description: c.description ?? '',
    affected_requirements: c.affected_requirements ?? [],
    sources: c.sources ?? [],
  }))
}

function transformSentiment(raw?: any): SentimentAnalysis | undefined {
  if (!raw) return undefined
  return {
    overall: raw.overall_sentiment ?? raw.overall ?? '',
    by_stakeholder: raw.stakeholder_breakdown ?? raw.by_stakeholder,
    by_topic: raw.by_topic,
  }
}

function transformBRD(raw: any): BRD {
  const sections: BRD['sections'] = {}
  for (const key of SECTION_KEYS) {
    const section = transformSection(raw[key])
    if (section) {
      ;(sections as any)[key] = section
    }
  }

  // Also handle pre-transformed data that already has a sections object
  if (raw.sections && typeof raw.sections === 'object') {
    for (const key of SECTION_KEYS) {
      const section = transformSection(raw.sections[key])
      if (section) {
        ;(sections as any)[key] = section
      }
    }
  }

  const generatedAt = raw.generated_at ?? raw.created_at ?? ''

  return {
    id: raw.brd_id ?? raw.id ?? '',
    project_id: raw.project_id ?? '',
    status: 'complete', // BRDs only exist in Firestore once generation finishes
    sections,
    conflicts: transformConflicts(raw.conflicts),
    sentiment: transformSentiment(raw.sentiment),
    created_at: generatedAt,
    updated_at: raw.updated_at ?? generatedAt,
  }
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

export async function generateBRD(
  projectId: string,
  request: GenerateBRDRequest = {}
): Promise<{ brd_id: string }> {
  const response = await apiClient.post(`/projects/${projectId}/brds/generate`, {
    project_id: projectId,
    ...request
  })
  return response.data
}

export async function getBRDs(projectId: string): Promise<BRD[]> {
  const response = await apiClient.get(`/projects/${projectId}/brds`)
  const data = Array.isArray(response.data) ? response.data : []
  return data.map(transformBRD)
}

export async function getBRD(projectId: string, brdId: string): Promise<BRD> {
  const response = await apiClient.get(`/projects/${projectId}/brds/${brdId}`)
  return transformBRD(response.data)
}

export interface RefineTextRequest {
  selected_text: string
  instruction: string
  section_context?: string
  mode: 'simple' | 'agentic'
}

export interface RefineTextResponse {
  original: string
  refined: string
  sources_used?: string[]
  tool_calls_made?: Array<{
    tool: string
    parameters: Record<string, any>
  }>
}

export async function refineText(
  projectId: string,
  brdId: string,
  request: RefineTextRequest
): Promise<RefineTextResponse> {
  const response = await apiClient.post(
    `/projects/${projectId}/brds/${brdId}/refine-text`,
    request
  )
  return response.data
}

export async function updateBRDSection(
  projectId: string,
  brdId: string,
  sectionKey: string,
  content: string
): Promise<BRDSection | undefined> {
  const response = await apiClient.patch(
    `/projects/${projectId}/brds/${brdId}/sections/${sectionKey}`,
    { content }
  )
  return transformSection(response.data)
}

export async function deleteBRD(projectId: string, brdId: string): Promise<void> {
  await apiClient.delete(`/projects/${projectId}/brds/${brdId}`)
}

// ---------------------------------------------------------------------------
// Unified agentic chat
// ---------------------------------------------------------------------------

export type ResponseType = 'refinement' | 'answer' | 'generation'

export interface ChatMessageRequest {
  message: string
  section_context: string
  selected_text?: string
}

export interface ChatMessageResponse {
  content: string
  response_type: ResponseType
  sources_used?: string[]
  tool_calls_made?: string[]
}

export async function chatMessage(
  projectId: string,
  brdId: string,
  request: ChatMessageRequest
): Promise<ChatMessageResponse> {
  const response = await apiClient.post(
    `/projects/${projectId}/brds/${brdId}/chat`,
    request
  )
  return response.data
}
