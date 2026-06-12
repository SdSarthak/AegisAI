/**
 * GuardExplanation — color-coded token viewer for Guard SHAP/LIME results.
 *
 * Renders the original text with each token wrapped in a <span> tinted by
 * the sign + magnitude of its attribution: red pushes the model toward the
 * predicted (usually flagged) class, blue pushes away. The opacity is the
 * normalized magnitude — at-a-glance you see which tokens carry weight.
 *
 * Tooltip on each token shows the numeric attribution; the panel header
 * shows the predicted label, confidence, and explanation latency.
 */

import { useMemo } from 'react'
import { Brain, Clock } from 'lucide-react'

import type { GuardExplainResponse, GuardTokenAttribution } from '../services/api'

interface Props {
  text: string
  explanation: GuardExplainResponse
}

interface RenderSegment {
  kind: 'token' | 'gap'
  start: number
  end: number
  text: string
  token?: GuardTokenAttribution
}

// Build a flat list of segments covering the entire input text. Anywhere
// a token's char_span sits, we emit a `token` segment; gaps between
// consecutive tokens (whitespace, punctuation tokens dropped by the
// tokenizer) become plain `gap` text.
function buildSegments(
  text: string,
  tokens: GuardTokenAttribution[],
): RenderSegment[] {
  // Tokens may come back unsorted (LIME doesn't guarantee order); sort by
  // start offset, dropping any overlapping ones to keep render stable.
  const sorted = [...tokens]
    .filter((t) => t.char_span[1] > t.char_span[0])
    .sort((a, b) => a.char_span[0] - b.char_span[0])

  const segments: RenderSegment[] = []
  let cursor = 0
  for (const tok of sorted) {
    const [start, end] = tok.char_span
    if (start < cursor || end > text.length) continue // overlap / oob — skip
    if (start > cursor) {
      segments.push({
        kind: 'gap',
        start: cursor,
        end: start,
        text: text.slice(cursor, start),
      })
    }
    segments.push({
      kind: 'token',
      start,
      end,
      text: text.slice(start, end),
      token: tok,
    })
    cursor = end
  }
  if (cursor < text.length) {
    segments.push({
      kind: 'gap',
      start: cursor,
      end: text.length,
      text: text.slice(cursor),
    })
  }
  return segments
}

// Map attribution to a Tailwind background class. Intensity in 5 buckets
// because Tailwind doesn't take dynamic class names from a compiler.
function tokenClass(attribution: number, maxAbs: number): string {
  if (maxAbs === 0) return 'bg-gray-50'
  const intensity = Math.min(Math.abs(attribution) / maxAbs, 1)
  const bucket = Math.ceil(intensity * 5) // 1..5
  if (attribution > 0) {
    return [
      '',
      'bg-red-50',
      'bg-red-100',
      'bg-red-200',
      'bg-red-300',
      'bg-red-400',
    ][bucket]
  }
  return [
    '',
    'bg-sky-50',
    'bg-sky-100',
    'bg-sky-200',
    'bg-sky-300',
    'bg-sky-400',
  ][bucket]
}

function decisionPillClass(label: string): string {
  const l = label.toLowerCase()
  if (l === 'malicious')
    return 'bg-red-100 text-red-700 border-red-200'
  if (l === 'suspicious')
    return 'bg-amber-100 text-amber-700 border-amber-200'
  return 'bg-emerald-100 text-emerald-700 border-emerald-200'
}

export default function GuardExplanation({ text, explanation }: Props) {
  const maxAbs = useMemo(
    () =>
      explanation.tokens.reduce(
        (m, t) => Math.max(m, Math.abs(t.attribution)),
        0,
      ),
    [explanation.tokens],
  )

  const segments = useMemo(
    () => buildSegments(text, explanation.tokens),
    [text, explanation.tokens],
  )

  // Top 3 tokens by absolute attribution — surfaced as a list for screen
  // readers and quick auditor scanning.
  const topTokens = useMemo(
    () =>
      [...explanation.tokens]
        .sort((a, b) => Math.abs(b.attribution) - Math.abs(a.attribution))
        .slice(0, 3),
    [explanation.tokens],
  )

  return (
    <section
      className="bg-white border border-gray-200 rounded-xl p-5 space-y-5"
      aria-label="Guard explanation"
    >
      <header className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="p-2 bg-indigo-50 rounded-lg">
            <Brain className="w-5 h-5 text-indigo-600" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">Why was this flagged?</h3>
            <p className="text-sm text-gray-500 mt-0.5">
              Token-level attribution from{' '}
              <span className="font-mono uppercase text-xs">
                {explanation.method}
              </span>{' '}
              · model v{explanation.model_version}
            </p>
          </div>
        </div>
        <div className="flex flex-col items-end gap-1">
          <span
            className={`inline-flex items-center px-3 py-1 rounded-full border text-xs font-medium ${decisionPillClass(explanation.predicted_label)}`}
          >
            {explanation.predicted_label} · {(explanation.predicted_proba * 100).toFixed(1)}%
          </span>
          <span className="text-xs text-gray-400 inline-flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {explanation.latency_ms.toFixed(0)} ms
          </span>
        </div>
      </header>

      <div>
        <p className="text-xs uppercase tracking-wide text-gray-400 mb-2">
          Highlighted prompt
        </p>
        <div
          className="font-mono text-sm leading-7 whitespace-pre-wrap break-words bg-gray-50 border border-gray-200 rounded-lg p-3"
          role="region"
          aria-label="Color-coded prompt tokens"
        >
          {segments.map((seg, i) =>
            seg.kind === 'gap' ? (
              <span key={i}>{seg.text}</span>
            ) : (
              <span
                key={i}
                className={`${tokenClass(seg.token!.attribution, maxAbs)} rounded px-0.5 transition-colors`}
                tabIndex={0}
                title={`${seg.token!.token}: ${seg.token!.attribution >= 0 ? '+' : ''}${seg.token!.attribution.toFixed(3)}`}
                aria-label={`Token ${seg.token!.token}, attribution ${seg.token!.attribution.toFixed(3)}`}
              >
                {seg.text}
              </span>
            ),
          )}
        </div>
        <div className="flex items-center gap-4 text-xs text-gray-500 mt-2">
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block w-3 h-3 rounded bg-red-300" />
            pushes toward <span className="font-medium">{explanation.predicted_label}</span>
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block w-3 h-3 rounded bg-sky-300" />
            pushes away
          </span>
        </div>
      </div>

      <div>
        <p className="text-xs uppercase tracking-wide text-gray-400 mb-2">
          Top contributing tokens
        </p>
        <ul className="space-y-1">
          {topTokens.map((t, i) => (
            <li
              key={`${t.token}-${t.char_span[0]}-${i}`}
              className="flex items-center justify-between text-sm"
            >
              <code className="font-mono text-gray-800">{t.token}</code>
              <span
                className={`font-mono tabular-nums ${t.attribution >= 0 ? 'text-red-600' : 'text-sky-600'}`}
              >
                {t.attribution >= 0 ? '+' : ''}
                {t.attribution.toFixed(3)}
              </span>
            </li>
          ))}
        </ul>
      </div>

      <details className="text-xs text-gray-500">
        <summary className="cursor-pointer hover:text-gray-700">
          What do these numbers mean?
        </summary>
        <p className="mt-2 leading-relaxed">
          Attributions are{' '}
          <a
            href="https://shap.readthedocs.io/en/latest/example_notebooks/text_examples/sentiment_analysis/Emotion%20classification%20multiclass%20example.html"
            target="_blank"
            rel="noopener noreferrer"
            className="text-indigo-600 hover:underline"
          >
            Shapley values
          </a>{' '}
          when method is <span className="font-mono">shap</span>, or LIME's
          local-linear coefficients otherwise. Magnitude reflects influence;
          sign indicates direction. They sum (approximately) to{' '}
          <span className="font-mono">
            {(explanation.predicted_proba - explanation.base_value).toFixed(3)}
          </span>{' '}
          — the gap between the base prediction (
          <span className="font-mono">
            {explanation.base_value.toFixed(3)}
          </span>
          ) and the actual confidence on this input.
        </p>
      </details>
    </section>
  )
}