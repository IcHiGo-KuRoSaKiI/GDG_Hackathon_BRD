'use client'

import { useRef, useState, useCallback, useEffect } from 'react'
import { cn } from '@/lib/utils/cn'

interface TiltCardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode
  tiltDeg?: number
  glowOnHover?: boolean
}

export function TiltCard({
  children,
  className,
  tiltDeg = 6,
  glowOnHover = true,
  ...props
}: TiltCardProps) {
  const ref = useRef<HTMLDivElement>(null)
  const [transform, setTransform] = useState('')
  const [isTouch, setIsTouch] = useState(false)

  useEffect(() => {
    setIsTouch('ontouchstart' in window || navigator.maxTouchPoints > 0)
  }, [])

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (isTouch || !ref.current) return
      const rect = ref.current.getBoundingClientRect()
      const x = (e.clientX - rect.left) / rect.width - 0.5
      const y = (e.clientY - rect.top) / rect.height - 0.5
      setTransform(
        `perspective(600px) rotateX(${-y * tiltDeg}deg) rotateY(${x * tiltDeg}deg) scale3d(1.02, 1.02, 1.02)`
      )
    },
    [tiltDeg, isTouch]
  )

  const handleMouseLeave = useCallback(() => {
    setTransform('')
  }, [])

  return (
    <div
      ref={ref}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      className={cn(
        'transition-transform duration-200 ease-out will-change-transform',
        glowOnHover && !isTouch && 'glow-hover',
        className
      )}
      style={{ transform: transform || undefined }}
      {...props}
    >
      {children}
    </div>
  )
}
