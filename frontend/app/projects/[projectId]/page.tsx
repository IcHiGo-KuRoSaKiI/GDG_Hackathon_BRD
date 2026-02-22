'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { Upload, Loader2, FileText, Sparkles, Trash2, Zap, DollarSign, Activity } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useToast } from '@/hooks/use-toast'
import { getProject, getProjectUsage, ProjectUsage } from '@/lib/api/projects'
import { getDocuments, uploadDocument } from '@/lib/api/documents'
import { getBRDs, generateBRD } from '@/lib/api/brds'
import { Project } from '@/lib/api/projects'
import { Document } from '@/lib/api/documents'
import { BRD } from '@/lib/api/brds'
import { DocumentViewer } from '@/components/documents/DocumentViewer'
import { DeleteDocumentDialog } from '@/components/documents/DeleteDocumentDialog'
import { DeleteBRDDialog } from '@/components/brd/DeleteBRDDialog'
import { BRDListCard } from '@/components/brd/BRDListCard'
import { GenerationProgressDialog } from '@/components/brd/GenerationProgressDialog'
import { useBRDPolling } from '@/lib/hooks/useBRDPolling'
import { EditableProjectHeader } from '@/components/projects/EditableProjectHeader'
import { Skeleton } from '@/components/ui/skeleton'
import { Breadcrumbs } from '@/components/ui/breadcrumbs'
import { calculateFileHash, extractHashFromPath } from '@/lib/utils/fileHash'
import { getApiError } from '@/lib/utils/formatters'

export default function ProjectDetailPage() {
  const params = useParams()
  const router = useRouter()
  const { toast } = useToast()
  const projectId = params.projectId as string

  const [project, setProject] = useState<Project | null>(null)
  const [documents, setDocuments] = useState<Document[]>([])
  const [brds, setBRDs] = useState<BRD[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null)
  const [viewerOpen, setViewerOpen] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [documentToDelete, setDocumentToDelete] = useState<Document | null>(null)
  const [deleteBRDDialogOpen, setDeleteBRDDialogOpen] = useState(false)
  const [brdToDelete, setBRDToDelete] = useState<BRD | null>(null)
  const [activeTab, setActiveTab] = useState('documents')
  const [isGenerating, setIsGenerating] = useState(false)
  const [usage, setUsage] = useState<ProjectUsage | null>(null)

  // Polling hook for BRD generation progress
  const { progress, stage } = useBRDPolling({
    projectId,
    enabled: isGenerating,
    onComplete: (brd) => {
      setIsGenerating(false)
      setActiveTab('brds')
      loadBRDs()
      loadUsage()
      toast({
        title: 'BRD generated successfully',
        description: 'Your Business Requirements Document is ready to view',
      })
    },
  })

  const loadProject = async () => {
    try {
      const data = await getProject(projectId)
      setProject(data)
    } catch (err: any) {
      setError(getApiError(err, 'Failed to load project'))
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

  const loadBRDs = async () => {
    try {
      const data = await getBRDs(projectId)
      setBRDs(data)
    } catch (err: any) {
      console.error('Failed to load BRDs:', err)
    }
  }

  const loadUsage = async () => {
    try {
      const data = await getProjectUsage(projectId)
      if (data.call_count > 0) setUsage(data)
    } catch {
      // Non-critical — silently ignore
    }
  }

  useEffect(() => {
    const init = async () => {
      setLoading(true)
      await Promise.all([loadProject(), loadDocuments(), loadBRDs(), loadUsage()])
      setLoading(false)
    }
    init()
  }, [projectId])

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return

    setUploading(true)
    try {
      let uploadedCount = 0
      let duplicateCount = 0

      for (const file of Array.from(files)) {
        // Calculate file hash
        const fileHash = await calculateFileHash(file)

        // Check if this hash already exists
        const existingDoc = documents.find((doc) => {
          const docHash = extractHashFromPath(doc.storage_path)
          return docHash === fileHash
        })

        if (existingDoc) {
          duplicateCount++
          toast({
            title: 'Duplicate file detected',
            description: `"${file.name}" was already uploaded as "${existingDoc.filename}"`,
            variant: 'destructive',
          })
          continue
        }

        // Upload if not a duplicate
        await uploadDocument(projectId, file)
        uploadedCount++
      }

      await loadDocuments()

      if (uploadedCount > 0) {
        toast({
          title: 'Upload successful',
          description: `Uploaded ${uploadedCount} document${uploadedCount > 1 ? 's' : ''}`,
        })
      }
    } catch (err: any) {
      const message = getApiError(err, 'Failed to upload documents')
      setError(message)
      toast({
        title: 'Upload failed',
        description: message,
        variant: 'destructive',
      })
    } finally {
      setUploading(false)
    }
  }

  const handleDocumentClick = (doc: Document) => {
    setSelectedDocument(doc)
    setViewerOpen(true)
  }

  const handleDeleteClick = (e: React.MouseEvent, doc: Document) => {
    e.stopPropagation() // Prevent opening the viewer
    setDocumentToDelete(doc)
    setDeleteDialogOpen(true)
  }

  const handleDocumentDeleted = () => {
    // Optimistically remove from list (backend deletes in background)
    if (documentToDelete) {
      setDocuments((prev) =>
        prev.filter((d) => d.doc_id !== documentToDelete.doc_id)
      )
      toast({
        title: 'Document deleted',
        description: `"${documentToDelete.filename}" has been removed.`,
      })
    }
  }

  const handleDeleteBRD = (brd: BRD) => {
    // Don't allow deletion of BRDs without IDs (still processing)
    if (!brd.id) {
      toast({
        title: 'Cannot delete BRD',
        description: 'This BRD is still being generated. Please wait for it to complete.',
        variant: 'destructive',
      })
      return
    }
    setBRDToDelete(brd)
    setDeleteBRDDialogOpen(true)
  }

  const handleBRDDeleted = async () => {
    await loadBRDs()
    toast({
      title: 'BRD deleted',
      description: 'The BRD has been successfully deleted',
    })
  }

  const handleGenerateBRD = async () => {
    try {
      setIsGenerating(true)
      await generateBRD(projectId, {
        include_conflicts: true,
        include_sentiment: true,
      })
      // Polling will handle the rest
    } catch (err: any) {
      setIsGenerating(false)
      toast({
        title: 'Failed to start BRD generation',
        description: getApiError(err, 'An error occurred'),
        variant: 'destructive',
      })
    }
  }

  if (loading) {
    return (
      <div className="p-4 md:p-8 space-y-6">
        {/* Header skeleton */}
        <div>
          <Skeleton className="h-5 w-32 mb-4" />
          <Skeleton className="h-8 w-72 mb-2" />
          <Skeleton className="h-4 w-48" />
        </div>
        {/* Tabs skeleton */}
        <Skeleton className="h-10 w-64" />
        {/* Cards skeleton */}
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="flex items-center gap-4 p-5 border border-border">
              <Skeleton className="h-10 w-10" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-4 w-48" />
                <Skeleton className="h-3 w-32" />
              </div>
              <Skeleton className="h-6 w-20" />
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (error && !project) {
    return (
      <div className="p-8">
        <div className="p-4 text-sm text-destructive bg-destructive/10 border border-destructive/20">
          {error}
        </div>
      </div>
    )
  }

  const allDocsProcessed = documents.length > 0 && documents.every(d => d.status === 'complete')
  const hasFailedDocs = documents.some(d => d.status === 'failed')

  return (
    <div className="p-4 md:p-8">
      {/* Header */}
      <div className="mb-6 md:mb-8">
        <Breadcrumbs
          items={[
            { label: 'Projects', href: '/dashboard' },
            { label: project?.name || 'Project' },
          ]}
          className="mb-4"
        />
        {project && (
          <EditableProjectHeader
            project={project}
            onUpdate={(updated) => setProject(updated)}
          />
        )}

        {/* LLM Usage Summary */}
        {usage && (
          <div className="mt-4 flex flex-wrap items-center gap-3 text-sm">
            <div className="flex items-center gap-4 px-4 py-2.5 bg-muted/50">
              <span className="flex items-center gap-1.5 text-muted-foreground" title="Total tokens across all LLM calls">
                <Zap className="h-3.5 w-3.5" />
                <span className="font-medium text-foreground">
                  {usage.total_tokens >= 1_000_000
                    ? `${(usage.total_tokens / 1_000_000).toFixed(1)}M`
                    : `${(usage.total_tokens / 1000).toFixed(0)}k`}
                </span>
                <span>tokens</span>
              </span>
              <span className="text-muted-foreground/30">|</span>
              <span className="flex items-center gap-1.5 text-muted-foreground" title="Estimated total LLM cost">
                <DollarSign className="h-3.5 w-3.5" />
                <span className="font-medium text-foreground">${usage.total_cost_usd.toFixed(4)}</span>
              </span>
              <span className="text-muted-foreground/30">|</span>
              <span className="flex items-center gap-1.5 text-muted-foreground" title="Total LLM API calls">
                <Activity className="h-3.5 w-3.5" />
                <span className="font-medium text-foreground">{usage.call_count}</span>
                <span>calls</span>
              </span>
            </div>
            {usage.by_service && Object.keys(usage.by_service).length > 0 && (
              <div className="hidden md:flex items-center gap-2 text-xs text-muted-foreground">
                {Object.entries(usage.by_service).map(([service, data]) => (
                  <span key={service} className="px-2 py-1 bg-muted/30" title={`${data.calls} calls, $${data.cost_usd.toFixed(4)}`}>
                    {service.replace(/_/g, ' ')}: ${data.cost_usd.toFixed(4)}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="mb-6">
          <TabsTrigger value="documents">
            Documents ({documents.length})
          </TabsTrigger>
          <TabsTrigger value="brds">
            BRDs ({brds.length})
          </TabsTrigger>
        </TabsList>

        {/* Documents Tab */}
        <TabsContent value="documents" className="space-y-6">
          {/* Upload Zone */}
          <Card>
            <CardHeader>
              <CardTitle>Upload Documents</CardTitle>
            </CardHeader>
            <CardContent>
              <label
                htmlFor="file-upload"
                className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-border cursor-pointer hover:bg-accent transition-colors"
              >
                <div className="flex flex-col items-center justify-center pt-5 pb-6">
                  <Upload className="h-8 w-8 mb-2 text-muted-foreground" />
                  <p className="text-sm text-muted-foreground">
                    {uploading ? 'Uploading...' : 'Click to upload or drag and drop'}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    PDF, DOCX, PPTX, XLSX, CSV, TXT, MD, HTML
                  </p>
                </div>
                <input
                  id="file-upload"
                  type="file"
                  className="hidden"
                  multiple
                  accept=".pdf,.docx,.pptx,.xlsx,.csv,.txt,.md,.html"
                  onChange={handleFileUpload}
                  disabled={uploading}
                />
              </label>
            </CardContent>
          </Card>

          {/* Documents List */}
          <div className="space-y-4">
            <h2 className="text-xl font-semibold font-mono">
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
                    key={doc.doc_id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.25, delay: Math.min(index * 0.06, 0.3) }}
                  >
                    <Card
                      className="cursor-pointer hover:bg-accent/50 transition-colors"
                      onClick={() => handleDocumentClick(doc)}
                    >
                      <CardContent className="p-6">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center space-x-2 mb-2">
                              <FileText className="h-5 w-5 text-primary" />
                              <h3 className="font-medium">{doc.filename}</h3>
                              {doc.status === 'processing' && (
                                <span className="text-xs px-2 py-1 bg-amber-500/10 text-amber-500">
                                  Processing...
                                </span>
                              )}
                              {doc.status === 'complete' && (
                                <span className="text-xs px-2 py-1 bg-emerald-500/10 text-emerald-500">
                                  ✓ Complete
                                </span>
                              )}
                              {doc.status === 'failed' && (
                                <span className="text-xs px-2 py-1 bg-destructive/10 text-destructive">
                                  Failed
                                </span>
                              )}
                            </div>

                            {doc.ai_metadata?.summary && (
                              <p className="text-sm text-muted-foreground mb-2">
                                {doc.ai_metadata.summary}
                              </p>
                            )}

                            {doc.ai_metadata?.tags && doc.ai_metadata.tags.length > 0 && (
                              <div className="flex flex-wrap gap-2 mb-2">
                                {doc.ai_metadata.tags.map((tag, i) => (
                                  <span
                                    key={i}
                                    className="text-xs px-2 py-1 bg-primary/10 text-primary"
                                  >
                                    {tag}
                                  </span>
                                ))}
                              </div>
                            )}

                            {doc.ai_metadata?.document_type && (
                              <p className="text-xs text-muted-foreground">
                                Type: {doc.ai_metadata.document_type} ({doc.chomper_metadata?.word_count || 0} words)
                              </p>
                            )}
                          </div>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="text-muted-foreground hover:text-destructive"
                            onClick={(e) => handleDeleteClick(e, doc)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  </motion.div>
                ))}
              </div>
            )}
          </div>

          {hasFailedDocs && (
            <div className="p-4 text-sm text-destructive bg-destructive/10 border border-destructive/20">
              Some documents failed to process. Please try uploading them again.
            </div>
          )}

          {documents.length > 0 && !allDocsProcessed && (
            <div className="p-4 text-sm text-amber-600 dark:text-amber-500 bg-amber-500/10 border border-amber-500/20">
              Documents are still processing. BRD generation will be available once all documents are complete.
            </div>
          )}
        </TabsContent>

        {/* BRDs Tab */}
        <TabsContent value="brds" className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold font-mono">
              Generated BRDs ({brds.length})
            </h2>
            <Button
              size="lg"
              disabled={!allDocsProcessed || documents.length === 0 || isGenerating}
              className="gap-2"
              onClick={handleGenerateBRD}
            >
              <Sparkles className="h-5 w-5" />
              Generate New BRD
            </Button>
          </div>

          {brds.length === 0 ? (
            <Card>
              <CardContent className="p-12 text-center text-muted-foreground">
                <Sparkles className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p className="mb-2">No BRDs generated yet</p>
                <p className="text-sm">
                  Upload and process documents, then generate your first BRD
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4">
              {brds.map((brd, index) => (
                <motion.div
                  key={brd.id || `brd-${index}`}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                >
                  <BRDListCard
                    brd={brd}
                    projectId={projectId}
                    onDelete={handleDeleteBRD}
                    onUpdate={(updated) => setBRDs((prev) => prev.map((b) => b.id === updated.id ? updated : b))}
                  />
                </motion.div>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>

      <DocumentViewer
        document={selectedDocument}
        projectId={projectId}
        open={viewerOpen}
        onClose={() => setViewerOpen(false)}
      />

      <DeleteDocumentDialog
        document={documentToDelete}
        projectId={projectId}
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
        onDeleted={handleDocumentDeleted}
      />

      <DeleteBRDDialog
        brd={brdToDelete}
        projectId={projectId}
        open={deleteBRDDialogOpen}
        onClose={() => setDeleteBRDDialogOpen(false)}
        onDeleted={handleBRDDeleted}
      />

      <GenerationProgressDialog
        open={isGenerating}
        documentCount={documents.length}
        progress={progress}
        stage={stage}
      />
    </div>
  )
}
