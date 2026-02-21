import apiClient from './client'

export interface Document {
  id: string
  project_id: string
  filename: string
  file_type: string
  file_size: number
  status: 'processing' | 'complete' | 'failed'
  ai_summary?: string
  ai_tags?: string[]
  ai_sentiment?: {
    overall: string
    score: number
  }
  ai_topics?: Array<{
    topic: string
    confidence: number
  }>
  created_at: string
  updated_at: string
  processing_progress?: number
}

export async function getDocuments(projectId: string): Promise<Document[]> {
  const response = await apiClient.get(`/projects/${projectId}/documents`)
  return response.data
}

export async function getDocument(projectId: string, documentId: string): Promise<Document> {
  const response = await apiClient.get(`/projects/${projectId}/documents/${documentId}`)
  return response.data
}

export async function uploadDocument(projectId: string, file: File): Promise<Document> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await apiClient.post(`/projects/${projectId}/documents/upload`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return response.data
}

export async function deleteDocument(projectId: string, documentId: string): Promise<void> {
  await apiClient.delete(`/projects/${projectId}/documents/${documentId}`)
}

export interface DeletePreviewResponse {
  document: Document
  brd_ids_to_delete: string[]
  warning_message: string
}

export async function previewDocumentDeletion(
  projectId: string,
  documentId: string
): Promise<DeletePreviewResponse> {
  const response = await apiClient.delete(
    `/projects/${projectId}/documents/${documentId}/preview`
  )
  return response.data
}
