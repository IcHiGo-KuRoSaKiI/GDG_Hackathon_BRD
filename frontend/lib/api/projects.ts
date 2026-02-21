import apiClient from './client'

export interface Project {
  project_id: string
  user_id: string
  name: string
  description?: string
  created_at: string
  updated_at: string
  document_count?: number
  brd_count?: number
}

export interface CreateProjectRequest {
  name: string
  description?: string
}

export async function getProjects(): Promise<Project[]> {
  const response = await apiClient.get('/projects')
  return response.data
}

export async function getProject(projectId: string): Promise<Project> {
  const response = await apiClient.get(`/projects/${projectId}`)
  return response.data
}

export async function createProject(data: CreateProjectRequest): Promise<Project> {
  const response = await apiClient.post('/projects', data)
  return response.data
}

export async function deleteProject(projectId: string): Promise<void> {
  await apiClient.delete(`/projects/${projectId}`)
}

export interface UpdateProjectRequest {
  name?: string
  description?: string
}

export async function updateProject(
  projectId: string,
  data: UpdateProjectRequest
): Promise<Project> {
  const response = await apiClient.patch(`/projects/${projectId}`, data)
  return response.data
}

export interface ServiceUsage {
  input_tokens: number
  output_tokens: number
  cost_usd: number
  calls: number
}

export interface ProjectUsage {
  project_id: string
  total_input_tokens: number
  total_output_tokens: number
  total_tokens: number
  total_cost_usd: number
  call_count: number
  by_service: Record<string, ServiceUsage>
  last_model?: string
  last_updated?: string
}

export async function getProjectUsage(projectId: string): Promise<ProjectUsage> {
  const response = await apiClient.get(`/projects/${projectId}/usage`)
  return response.data
}
