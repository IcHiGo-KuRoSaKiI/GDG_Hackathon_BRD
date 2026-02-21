'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { ArrowLeft, Upload, Loader2, FileText, Sparkles, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useToast } from '@/hooks/use-toast'
import { getProject } from '@/lib/api/projects'
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
import { calculateFileHash, extractHashFromPath } from '@/lib/utils/fileHash'
import Link from 'next/link'

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

  // Polling hook for BRD generation progress
  const { progress, stage } = useBRDPolling({
    projectId,
    enabled: isGenerating,
    onComplete: (brd) => {
      setIsGenerating(false)
      setActiveTab('brds')
      loadBRDs()
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

  const loadBRDs = async () => {
    try {
      const data = await getBRDs(projectId)
      setBRDs(data)
    } catch (err: any) {
      console.error('Failed to load BRDs:', err)
    }
  }

  useEffect(() => {
    const init = async () => {
      setLoading(true)
      await Promise.all([loadProject(), loadDocuments(), loadBRDs()])
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
      const detail = err.response?.data?.detail
      const message = typeof detail === 'string' ? detail : 'Failed to upload documents'
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

  const handleDocumentDeleted = async () => {
    await loadDocuments()
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
        description: err.response?.data?.detail || 'An error occurred',
        variant: 'destructive',
      })
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
        <div>
          <h1 className="text-3xl font-bold mb-2">{project?.name}</h1>
          {project?.description && (
            <p className="text-muted-foreground">{project.description}</p>
          )}
        </div>
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
                    key={doc.doc_id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.1 }}
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
                                    className="text-xs px-2 py-1 bg-primary/10 text-primary rounded-md"
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
            <div className="p-4 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-md">
              Some documents failed to process. Please try uploading them again.
            </div>
          )}

          {documents.length > 0 && !allDocsProcessed && (
            <div className="p-4 text-sm text-amber-600 dark:text-amber-500 bg-amber-500/10 border border-amber-500/20 rounded-md">
              Documents are still processing. BRD generation will be available once all documents are complete.
            </div>
          )}
        </TabsContent>

        {/* BRDs Tab */}
        <TabsContent value="brds" className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold">
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
                  <BRDListCard brd={brd} projectId={projectId} onDelete={handleDeleteBRD} />
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
