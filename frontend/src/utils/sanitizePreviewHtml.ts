const BLOCKED_TAGS = new Set([
  'script',
  'style',
  'iframe',
  'object',
  'embed',
  'link',
  'meta',
  'base',
  'form',
  'input',
  'button',
  'select',
  'option',
  'textarea',
  'svg',
  'math',
  'template',
])

const URL_ATTRIBUTES = new Set(['href', 'src', 'xlink:href', 'formaction', 'poster'])
const SAFE_URL_PATTERN = /^(?:https?:|mailto:|tel:|#|\/(?!\/)|\.\.?\/)/i

function isSafeUrl(value: string): boolean {
  const trimmed = value.trim()
  if (!trimmed) {
    return true
  }

  if (SAFE_URL_PATTERN.test(trimmed)) {
    return true
  }

  return false
}

function sanitizeElement(root: ParentNode): void {
  const elements = Array.from(root.querySelectorAll('*'))

  for (const element of elements) {
    const tagName = element.tagName.toLowerCase()

    if (BLOCKED_TAGS.has(tagName)) {
      element.remove()
      continue
    }

    for (const attribute of Array.from(element.attributes)) {
      const name = attribute.name.toLowerCase()
      const value = attribute.value

      if (name.startsWith('on') || name === 'style' || name === 'srcdoc') {
        element.removeAttribute(attribute.name)
        continue
      }

      if (URL_ATTRIBUTES.has(name) && !isSafeUrl(value)) {
        element.removeAttribute(attribute.name)
      }
    }
  }
}

export function sanitizePreviewHtml(html: string): string {
  if (typeof document === 'undefined') {
    return html
  }

  const template = document.createElement('template')
  template.innerHTML = html
  sanitizeElement(template.content)
  return template.innerHTML
}
