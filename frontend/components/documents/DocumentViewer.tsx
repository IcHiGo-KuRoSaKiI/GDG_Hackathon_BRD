'use client'

import { useState, useEffect } from 'react'
import { Download, FileText, Loader2, X } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { getDocumentText } from '@/lib/api/documents'
import { Document } from '@/lib/api/documents'

interface DocumentViewerProps {
  document: Document | null
  projectId: string
  open: boolean
  onClose: () => void
}

export function DocumentViewer({ document, projectId, open, onClose }: DocumentViewerProps) {
  const [text, setText] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (open && document) {
      loadDocumentText()
    }
  }, [open, document])

  const loadDocumentText = async () => {
    if (!document) return

    setLoading(true)
    setError('')
    try {
      const content = await getDocumentText(projectId, document.doc_id)
      setText(content)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load document content')
    } finally {
      setLoading(false)
    }
  }

  const handleDownload = () => {
    if (!text || !document) return

    const blob = new Blob([text], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = window.document.createElement('a')
    a.href = url
    a.download = `${document.filename}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <Dialog open={open} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-4xl h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            {document?.filename}
          </DialogTitle>
          <DialogDescription>
            {document?.chomper_metadata?.word_count || 0} words •{' '}
            {document?.chomper_metadata?.page_count || 0} pages •{' '}
            {document?.ai_metadata?.document_type || 'Unknown type'}
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto border rounded-md p-4 bg-muted/30">
          {loading && (
            <div className="flex items-center justify-center h-full">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          )}

          {error && (
            <div className="p-4 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-md">
              {error}
            </div>
          )}

          {!loading && !error && text && (
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  table: ({ children }) => (
                    <div className="overflow-x-auto my-4">
                      <table className="w-full border-collapse text-sm">{children}</table>
                    </div>
                  ),
                  thead: ({ children }) => <thead className="bg-muted/50">{children}</thead>,
                  th: ({ children }) => (
                    <th className="p-2 border text-left font-semibold">{children}</th>
                  ),
                  td: ({ children }) => (
                    <td className="p-2 border">{children}</td>
                  ),
                }}
              >
                {text}
              </ReactMarkdown>
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2 pt-4 border-t">
          <Button variant="outline" onClick={handleDownload} disabled={!text}>
            <Download className="h-4 w-4 mr-2" />
            Download
          </Button>
          <Button variant="outline" onClick={onClose}>
            <X className="h-4 w-4 mr-2" />
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
