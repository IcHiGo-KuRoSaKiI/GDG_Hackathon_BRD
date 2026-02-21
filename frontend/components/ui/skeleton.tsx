import { cn } from '@/lib/utils'

function Skeleton({
  className,
  shimmer = true,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { shimmer?: boolean }) {
  return (
    <div
      className={cn(
        'rounded-md',
        shimmer ? 'skeleton-shimmer' : 'animate-pulse bg-muted',
        className
      )}
      {...props}
    />
  )
}

export { Skeleton }
