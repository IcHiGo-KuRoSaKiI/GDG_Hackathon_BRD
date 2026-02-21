'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { ArrowLeft, Upload, Loader2, FileText, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { getProject } from '@/lib/api/projects'
import { getDocuments, uploadDocument } from '@/lib/api/documents'
import { Project } from '@/lib/api/projects'
import { Document } from '@/lib/api/documents'
import Link from 'next/link'

export default function ProjectDetailPage() {
  const params = useParams()
  const router = useRouter()
  const projectId = params.projectId as string

  const [project, setProject] = useState<Project | null>(null)
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')

  const loadProject = async () => {
    try {
      const data = await getProject(projectId)
      setProject(data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load project')
    }
  }

  const loadDocuments = async () => {
    try {
      const data = await getDocuments(projectId)
      setDocuments(data)
    } catch (err: any) {
      console.error('Failed to load documents:', err)
    }
  }

  useEffect(() => {
    const init = async () => {
      setLoading(true)
      await loadProject()
      await loadDocuments()
      setLoading(false)
    }
    init()
  }, [projectId])

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return

    setUploading(true)
    try {
      for (const file of Array.from(files)) {
        await uploadDocument(projectId, file)
      }
      await loadDocuments()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to upload documents')
    } finally {
      setUploading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (error && !project) {
    return (
      <div className="p-8">
        <div className="p-4 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-md">
          {error}
        </div>
      </div>
    )
  }

  const allDocsProcessed = documents.length > 0 && documents.every(d => d.status === 'complete')
  const hasFailedDocs = documents.some(d => d.status === 'failed')

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <Link href="/dashboard">
          <Button variant="ghost" className="mb-4">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Projects
          </Button>
        </Link>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold mb-2">{project?.name}</h1>
            {project?.description && (
              <p className="text-muted-foreground">{project.description}</p>
            )}
          </div>
          <Button
            size="lg"
            disabled={!allDocsProcessed || documents.length === 0}
            className="gap-2"
          >
            <Sparkles className="h-5 w-5" />
            Generate BRD
          </Button>
        </div>
      </div>

      {/* Upload Zone */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle>Upload Documents</CardTitle>
        </CardHeader>
        <CardContent>
          <label
            htmlFor="file-upload"
            className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-border rounded-lg cursor-pointer hover:bg-accent transition-colors"
          >
            <div className="flex flex-col items-center justify-center pt-5 pb-6">
              <Upload className="h-8 w-8 mb-2 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">
                {uploading ? 'Uploading...' : 'Click to upload or drag and drop'}
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                PDF, DOCX, TXT, MD
              </p>
            </div>
            <input
              id="file-upload"
              type="file"
              className="hidden"
              multiple
              accept=".pdf,.docx,.txt,.md"
              onChange={handleFileUpload}
              disabled={uploading}
            />
          </label>
        </CardContent>
      </Card>

      {/* Documents List */}
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">
          Documents ({documents.length})
        </h2>

        {documents.length === 0 ? (
          <Card>
            <CardContent className="p-8 text-center text-muted-foreground">
              <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No documents yet. Upload some to get started!</p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4">
            {documents.map((doc, index) => (
              <motion.div
                key={doc.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <Card>
                  <CardContent className="p-6">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 mb-2">
                          <FileText className="h-5 w-5 text-primary" />
                          <h3 className="font-medium">{doc.filename}</h3>
                          {doc.status === 'processing' && (
                            <span className="text-xs px-2 py-1 bg-amber-500/10 text-amber-500 rounded-full">
                              Processing...
                            </span>
                          )}
                          {doc.status === 'complete' && (
                            <span className="text-xs px-2 py-1 bg-emerald-500/10 text-emerald-500 rounded-full">
                              ✓ Complete
                            </span>
                          )}
                          {doc.status === 'failed' && (
                            <span className="text-xs px-2 py-1 bg-destructive/10 text-destructive rounded-full">
                              Failed
                            </span>
                          )}
                        </div>

                        {doc.ai_summary && (
                          <p className="text-sm text-muted-foreground mb-2">
                            {doc.ai_summary}
                          </p>
                        )}

                        {doc.ai_tags && doc.ai_tags.length > 0 && (
                          <div className="flex flex-wrap gap-2 mb-2">
                            {doc.ai_tags.map((tag, i) => (
                              <span
                                key={i}
                                className="text-xs px-2 py-1 bg-primary/10 text-primary rounded-md"
                              >
                                {tag}
                              </span>
                            ))}
                          </div>
                        )}

                        {doc.ai_sentiment && (
                          <p className="text-xs text-muted-foreground">
                            Sentiment: {doc.ai_sentiment.overall} ({(doc.ai_sentiment.score * 100).toFixed(0)}%)
                          </p>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        )}
      </div>

      {hasFailedDocs && (
        <div className="mt-4 p-4 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-md">
          Some documents failed to process. Please try uploading them again.
        </div>
      )}

      {documents.length > 0 && !allDocsProcessed && (
        <div className="mt-4 p-4 text-sm text-amber-600 dark:text-amber-500 bg-amber-500/10 border border-amber-500/20 rounded-md">
          Documents are still processing. The "Generate BRD" button will be enabled once all documents are complete.
        </div>
      )}
    </div>
  )
}
