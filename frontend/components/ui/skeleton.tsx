import { cn } from '@/lib/utils'

function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        'bg-muted/50 backdrop-blur-sm animate-pulse',
        className
      )}
      {...props}
    />
  )
}

export { Skeleton }
