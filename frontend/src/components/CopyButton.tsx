import { useEffect, useRef, useState } from 'react'
import { Check, Copy } from 'lucide-react'
import { notify } from '../utils/toast'
import { copyTextToClipboard } from '../utils/clipboard'

interface CopyButtonProps {
  text: string
  label?: string
  copiedLabel?: string
  successMessage?: string
  className?: string
  iconOnly?: boolean
  disabled?: boolean
}

export default function CopyButton({
  text,
  label = 'Copy',
  copiedLabel = 'Copied!',
  successMessage = 'Copied!',
  className = '',
  iconOnly = false,
  disabled = false,
}: CopyButtonProps) {
  const [copied, setCopied] = useState(false)
  const timeoutRef = useRef<number | null>(null)

  useEffect(() => {
    return () => {
      if (timeoutRef.current !== null) {
        window.clearTimeout(timeoutRef.current)
      }
    }
  }, [])

  const handleCopy = async () => {
    if (disabled) {
      return
    }

    const value = text.trim()
    if (!value) {
      notify.error('Nothing to copy yet')
      return
    }

    try {
      await copyTextToClipboard(value)
      setCopied(true)
      notify.success(successMessage)

      if (timeoutRef.current !== null) {
        window.clearTimeout(timeoutRef.current)
      }

      timeoutRef.current = window.setTimeout(() => {
        setCopied(false)
      }, 1600)
    } catch {
      notify.error('Unable to copy right now')
    }
  }

  const baseClass = iconOnly
    ? 'inline-flex items-center justify-center p-2 rounded-lg border border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400 hover:text-primary-600 dark:hover:text-primary-400 hover:border-primary-200 dark:hover:border-primary-850 hover:bg-primary-50 dark:hover:bg-primary-950/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed'
    : 'inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-700 text-xs font-semibold text-gray-600 dark:text-gray-300 hover:text-primary-700 dark:hover:text-primary-400 hover:border-primary-200 dark:hover:border-primary-850 hover:bg-primary-50 dark:hover:bg-primary-950/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed'

  const buttonTitle = copied ? copiedLabel : label

  return (
    <button
      type="button"
      onClick={handleCopy}
      className={`${baseClass} ${className}`.trim()}
      title={buttonTitle}
      aria-label={buttonTitle}
      disabled={disabled}
    >
      {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
      {!iconOnly && <span>{copied ? copiedLabel : label}</span>}
    </button>
  )
}

