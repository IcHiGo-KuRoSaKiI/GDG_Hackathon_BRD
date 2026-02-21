'use client'

import Link from 'next/link'
import { motion } from 'framer-motion'
import { FileText, File, Clock } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Project } from '@/lib/api/projects'
import { formatRelativeTime } from '@/lib/utils/formatters'

interface ProjectCardProps {
  project: Project
}

export function ProjectCard({ project }: ProjectCardProps) {
  return (
    <Link href={`/projects/${project.id}`}>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        whileHover={{ scale: 1.02, y: -4 }}
        transition={{ duration: 0.2 }}
      >
        <Card className="h-full border-border/50 hover:shadow-lg hover:border-primary/50 transition-all cursor-pointer">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <FileText className="h-5 w-5 text-primary" />
              <span className="truncate">{project.name}</span>
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
