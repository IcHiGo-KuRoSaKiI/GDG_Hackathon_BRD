import apiClient from './client'

export interface Project {
  id: string
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
