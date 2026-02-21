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
  requirement_1: {
    id: string
    text: string
    source: string
    stakeholder?: string
  }
  requirement_2: {
    id: string
    text: string
    source: string
    stakeholder?: string
  }
  conflict_type: string
  severity: 'low' | 'medium' | 'high'
  resolution?: string
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
    scope?: BRDSection
    functional_requirements?: BRDSection
    non_functional_requirements?: BRDSection
    user_stories?: BRDSection
    data_requirements?: BRDSection
    integration_requirements?: BRDSection
    security_requirements?: BRDSection
    assumptions?: BRDSection
    constraints?: BRDSection
    risks?: BRDSection
  }
  conflicts?: Conflict[]
  sentiment?: SentimentAnalysis
  created_at: string
  updated_at: string
  processing_stage?: string
  processing_progress?: number
}

export interface GenerateBRDRequest {
  include_conflicts?: boolean
  include_sentiment?: boolean
}

export async function generateBRD(
  projectId: string,
  request: GenerateBRDRequest = {}
): Promise<{ brd_id: string }> {
  const response = await apiClient.post(`/projects/${projectId}/brds/generate`, request)
  return response.data
}

export async function getBRDs(projectId: string): Promise<BRD[]> {
  const response = await apiClient.get(`/projects/${projectId}/brds`)
  return response.data
}

export async function getBRD(projectId: string, brdId: string): Promise<BRD> {
  const response = await apiClient.get(`/projects/${projectId}/brds/${brdId}`)
  return response.data
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
