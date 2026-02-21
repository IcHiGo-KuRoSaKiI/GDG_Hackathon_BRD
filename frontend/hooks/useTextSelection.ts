'use client'

import { useCallback, useEffect, useRef, useState } from 'react'

export interface TextSelectionState {
  selectedText: string
  sectionKey: string
  toolbarPosition: { top: number; left: number }
  isActive: boolean
  mode: 'refine' | 'generate'
  clearSelection: () => void
}

/**
 * Detects text selection inside a container and shows a floating toolbar.
 *
 * Uses a callback-ref pattern: pass the DOM element directly (not a ref)
 * so the useEffect re-runs when the element mounts after async loading.
 *
 *   const [el, setEl] = useState<HTMLDivElement | null>(null)
 *   <div ref={setEl}>…</div>
 *   const selection = useTextSelection(el)
 */
export function useTextSelection(
  container: HTMLElement | null
): TextSelectionState {
  const [selectedText, setSelectedText] = useState('')
  const [sectionKey, setSectionKey] = useState('')
  const [toolbarPosition, setToolbarPosition] = useState({ top: 0, left: 0 })
  const [isActive, setIsActive] = useState(false)
  const [mode, setMode] = useState<'refine' | 'generate'>('refine')
  const clearTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  // Track mousedown so we can dismiss on single-click in mouseup
  // without causing a re-render mid-selection
  const pendingDismissRef = useRef(false)

  const clearSelection = useCallback(() => {
    setIsActive(false)
    setSelectedText('')
    setSectionKey('')
    window.getSelection()?.removeAllRanges()
  }, [])

  // Walk up DOM to find data-section-key
  const findSectionKey = useCallback((node: Node | null): string => {
    let el = node instanceof HTMLElement ? node : node?.parentElement ?? null
    while (el) {
      const key = el.getAttribute('data-section-key')
      if (key) return key
      el = el.parentElement
    }
    return ''
  }, [])

  useEffect(() => {
    if (!container) return

    // Only cancel pending timeout — NO setState here to avoid
    // re-renders that destroy the browser's in-progress selection
    const handleMouseDown = () => {
      if (clearTimeoutRef.current) clearTimeout(clearTimeoutRef.current)
      pendingDismissRef.current = true
    }

    const handleMouseUp = () => {
      if (clearTimeoutRef.current) clearTimeout(clearTimeoutRef.current)
      clearTimeoutRef.current = setTimeout(() => {
        const sel = window.getSelection()
        if (!sel || sel.rangeCount === 0 || sel.isCollapsed) {
          // Single click (collapsed) → dismiss toolbar if it was showing
          if (pendingDismissRef.current) {
            setIsActive(false)
          }
          pendingDismissRef.current = false
          return
        }

        const range = sel.getRangeAt(0)

        // Selection must be within our container
        if (!container.contains(range.commonAncestorContainer)) {
          pendingDismissRef.current = false
          return
        }

        const text = sel.toString().trim()
        if (text.length === 0) {
          pendingDismissRef.current = false
          return
        }

        const key = findSectionKey(range.startContainer)
        if (!key) {
          pendingDismissRef.current = false
          return
        }

        const rect = range.getBoundingClientRect()
        const containerRect = container.getBoundingClientRect()

        setSelectedText(text)
        setSectionKey(key)
        setMode('refine')
        setToolbarPosition({
          top: rect.top - containerRect.top - 44,
          left: rect.left - containerRect.left + rect.width / 2,
        })
        setIsActive(true)
        pendingDismissRef.current = false
      }, 10)
    }

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') clearSelection()
    }

    container.addEventListener('mousedown', handleMouseDown)
    container.addEventListener('mouseup', handleMouseUp)
    document.addEventListener('keydown', handleKeyDown)

    return () => {
      container.removeEventListener('mousedown', handleMouseDown)
      container.removeEventListener('mouseup', handleMouseUp)
      document.removeEventListener('keydown', handleKeyDown)
      if (clearTimeoutRef.current) clearTimeout(clearTimeoutRef.current)
    }
  }, [container, findSectionKey, clearSelection])

  return { selectedText, sectionKey, toolbarPosition, isActive, mode, clearSelection }
}
