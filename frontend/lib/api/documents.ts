import apiClient from './client'

export interface Document {
  doc_id: string
  project_id: string
  filename: string
  original_filename: string
  storage_path: string
  text_path: string
  status: 'processing' | 'complete' | 'failed'
  error_message?: string | null
  uploaded_at: string
  processed_at?: string | null
  chomper_metadata?: {
    format: string
    page_count?: number | null
    word_count?: number
    char_count?: number
    has_images?: boolean
    has_tables?: boolean
  }
  ai_metadata?: {
    document_type?: string
    confidence?: number
    summary?: string
    key_points?: string[]
    tags?: string[]
    topic_relevance?: {
      topics: Record<string, number>
    }
    content_indicators?: {
      indicators: Record<string, boolean>
    }
    key_entities?: {
      stakeholders?: string[]
      features?: string[]
      decisions?: string[]
      dates?: string[]
      technologies?: string[]
    }
    stakeholder_sentiments?: any[]
  }
  chunk_count?: number
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
  formData.append('files', file)

  const response = await apiClient.post(`/projects/${projectId}/documents/upload`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return response.data
}

export interface DeletePreviewResponse {
  deletion_id: string
  scope: string
  project_id: string
  project_name: string
  doc_id?: string
  filename?: string
  documents_to_delete: number
  chunks_to_delete: number
  brds_to_delete: number
  storage_files_to_delete: number
  expires_at: string
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

export async function confirmDocumentDeletion(
  projectId: string,
  documentId: string,
  deletionId: string
): Promise<void> {
  await apiClient.delete(`/projects/${projectId}/documents/${documentId}`, {
    data: { deletion_id: deletionId, confirmation: 'DELETE' },
  })
}

export async function getDocumentText(
  projectId: string,
  documentId: string
): Promise<string> {
  const response = await apiClient.get(
    `/projects/${projectId}/documents/${documentId}/text`
  )
  return response.data
}
