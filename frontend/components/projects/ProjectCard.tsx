'use client'

import Link from 'next/link'
import { motion } from 'framer-motion'
import { FileText, File, Clock, Trash2 } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Project } from '@/lib/api/projects'
import { formatRelativeTime } from '@/lib/utils/formatters'

interface ProjectCardProps {
  project: Project
  onDelete?: (project: Project) => void
}

export function ProjectCard({ project, onDelete }: ProjectCardProps) {
  const handleDeleteClick = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    onDelete?.(project)
  }

  return (
    <Link href={`/projects/${project.project_id}`}>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
      >
        <Card className="h-full cursor-pointer relative group">
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <FileText className="h-5 w-5 text-primary" />
                <span className="truncate">{project.name}</span>
              </div>
              {onDelete && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"
                  onClick={handleDeleteClick}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              )}
            </CardTitle>
            {project.description && (
              <CardDescription className="line-clamp-2">
                {project.description}
              </CardDescription>
            )}
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex items-center space-x-4 text-sm text-muted-foreground">
              <div className="flex items-center space-x-1">
                <File className="h-4 w-4" />
                <span>{project.document_count || 0} docs</span>
              </div>
              <div className="flex items-center space-x-1">
                <FileText className="h-4 w-4" />
                <span>{project.brd_count || 0} BRDs</span>
              </div>
            </div>
            <div className="flex items-center space-x-1 text-xs text-muted-foreground">
              <Clock className="h-3 w-3" />
              <span>Updated {formatRelativeTime(project.updated_at)}</span>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </Link>
  )
}
