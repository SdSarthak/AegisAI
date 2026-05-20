export async function copyTextToClipboard(text: string): Promise<void> {
  if (!text) {
    throw new Error('No text provided')
  }

  if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text)
    return
  }

  if (typeof document === 'undefined') {
    throw new Error('Clipboard API not available')
  }

  const textArea = document.createElement('textarea')
  textArea.value = text
  textArea.setAttribute('readonly', '')
  textArea.style.position = 'fixed'
  textArea.style.top = '-9999px'
  textArea.style.left = '-9999px'

  document.body.appendChild(textArea)

  const selection = document.getSelection()
  const originalRange = selection && selection.rangeCount > 0
    ? selection.getRangeAt(0)
    : null

  textArea.select()
  textArea.setSelectionRange(0, textArea.value.length)

  const success = document.execCommand('copy')
  document.body.removeChild(textArea)

  if (originalRange && selection) {
    selection.removeAllRanges()
    selection.addRange(originalRange)
  }

  if (!success) {
    throw new Error('Copy command failed')
  }
}
