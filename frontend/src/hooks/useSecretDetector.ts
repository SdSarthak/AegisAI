/**
 * useSecretDetector — detects secrets, API keys, and PII in prompt text.
 * Issue #201 — Prompt secret detector
 *
 * Runs entirely client-side (no API call) using regex patterns.
 * Returns a list of detected secret types so the UI can warn the user
 * before the prompt is submitted to any LLM endpoint.
 */

import { useMemo } from 'react'

export interface SecretMatch {
  type: string
  pattern: string
  severity: 'high' | 'medium' | 'low'
}

interface DetectorRule {
  type: string
  severity: 'high' | 'medium' | 'low'
  regex: RegExp
}

const RULES: DetectorRule[] = [
  { type: 'OpenAI API Key',        severity: 'high',   regex: /sk-[A-Za-z0-9]{20,}/g },
  { type: 'Anthropic API Key',     severity: 'high',   regex: /sk-ant-[A-Za-z0-9_-]{20,}/g },
  { type: 'Google API Key',        severity: 'high',   regex: /AIza[0-9A-Za-z_-]{35}/g },
  { type: 'AWS Access Key',        severity: 'high',   regex: /AKIA[0-9A-Z]{16}/g },
  { type: 'GitHub Token',          severity: 'high',   regex: /gh[pousr]_[A-Za-z0-9]{36,}/g },
  { type: 'Stripe Secret Key',     severity: 'high',   regex: /sk_live_[0-9a-zA-Z]{24,}/g },
  { type: 'Stripe Publishable Key',severity: 'medium', regex: /pk_live_[0-9a-zA-Z]{24,}/g },
  { type: 'JWT Token',             severity: 'high',   regex: /eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/g },
  { type: 'Bearer Token',          severity: 'high',   regex: /Bearer\s+[A-Za-z0-9._~+/-]+=*/gi },
  {
    type: 'Env Variable with Secret',
    severity: 'high',
    regex: /(?:API_KEY|SECRET_KEY|ACCESS_TOKEN|AUTH_TOKEN|PRIVATE_KEY|PASSWORD|PASSWD|DB_PASSWORD)\s*=\s*\S+/gi,
  },
  { type: 'Private Key Block',     severity: 'high',   regex: /-----BEGIN\s+(?:RSA\s+)?PRIVATE KEY-----/g },
  { type: 'Password in URL',       severity: 'high',   regex: /[a-zA-Z]+:\/\/[^:]+:[^@]+@/g },
  { type: 'Phone Number',          severity: 'medium', regex: /(?:\+?[1-9]\d{0,2}[\s.-])?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}/g },
  { type: 'Email Address',         severity: 'low',    regex: /[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g },
  { type: 'Credit Card Number',    severity: 'high',   regex: /\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b/g },
]

function redact(value: string): string {
  if (value.length <= 8) return '***'
  return value.slice(0, 4) + '***' + value.slice(-4)
}

export function detectSecrets(text: string): SecretMatch[] {
  if (!text.trim()) return []
  const matches: SecretMatch[] = []
  const seen = new Set<string>()
  for (const rule of RULES) {
    rule.regex.lastIndex = 0
    let match: RegExpExecArray | null
    while ((match = rule.regex.exec(text)) !== null) {
      const key = `${rule.type}:${match[0]}`
      if (!seen.has(key)) {
        seen.add(key)
        matches.push({ type: rule.type, pattern: redact(match[0]), severity: rule.severity })
      }
      if (match[0].length === 0) rule.regex.lastIndex++
    }
  }
  return matches
}

export function useSecretDetector(text: string): SecretMatch[] {
  return useMemo(() => detectSecrets(text), [text])
}
