'use client'

import { motion } from 'framer-motion'
import { cn } from '@/lib/utils/cn'

interface TextRevealProps {
  text: string
  className?: string
  as?: 'h1' | 'h2' | 'h3' | 'p' | 'span'
  delay?: number
  staggerSpeed?: number
}

const containerVariants = {
  hidden: {},
  visible: (stagger: number) => ({
    transition: {
      staggerChildren: stagger,
    },
  }),
}

const charVariants = {
  hidden: { opacity: 0, y: 12, filter: 'blur(4px)' },
  visible: {
    opacity: 1,
    y: 0,
    filter: 'blur(0px)',
    transition: { duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] as const },
  },
}

export function TextReveal({
  text,
  className,
  as: Tag = 'h1',
  delay = 0,
  staggerSpeed = 0.03,
}: TextRevealProps) {
  const MotionTag = motion(Tag)

  return (
    <MotionTag
      className={cn('flex flex-wrap', className)}
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      custom={staggerSpeed}
      transition={{ delayChildren: delay }}
    >
      {text.split('').map((char, i) => (
        <motion.span
          key={`${char}-${i}`}
          variants={charVariants}
          className={char === ' ' ? 'w-[0.3em]' : undefined}
        >
          {char === ' ' ? '\u00A0' : char}
        </motion.span>
      ))}
    </MotionTag>
  )
}

/* Word-level reveal for subtitles */
interface WordRevealProps {
  text: string
  className?: string
  delay?: number
}

export function WordReveal({ text, className, delay = 0 }: WordRevealProps) {
  return (
    <motion.p
      className={cn('flex flex-wrap gap-x-[0.3em]', className)}
      initial="hidden"
      animate="visible"
      variants={{
        hidden: {},
        visible: { transition: { staggerChildren: 0.05, delayChildren: delay } },
      }}
    >
      {text.split(' ').map((word, i) => (
        <motion.span
          key={`${word}-${i}`}
          variants={{
            hidden: { opacity: 0, y: 8 },
            visible: { opacity: 1, y: 0, transition: { duration: 0.3 } },
          }}
        >
          {word}
        </motion.span>
      ))}
    </motion.p>
  )
}
