// HTTP wrapper: attaches bearer token, attaches signing headers for the
// configured signed-paths list, and performs a single refresh + retry on
// TOKEN_EXPIRED 401.

import { useAuthStore } from '@/stores/auth'
import type { ApiError, ApiResponse } from '@/types'
import { getOrCreateDeviceKey } from './deviceKey'
import { getOfflineQueue } from './offlineQueue'
import {
  buildCanonical,
  currentTimestamp,
  generateNonce,
  signRequest,
} from './requestSigner'

export interface HttpOptions {
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  path: string
  body?: unknown
  signed?: boolean
  idempotencyKey?: string
  headers?: Record<string, string>
  skipAuth?: boolean
  skipRefresh?: boolean
}

export class HttpError extends Error {
  status: number
  envelope: ApiError
  constructor(status: number, envelope: ApiError) {
    super(envelope?.error?.message?.trim() || `HTTP ${status}`)
    this.status = status
    this.envelope = envelope
  }
}

// Raised when a mutation could not be sent because the browser is offline
// (or the network request threw) and the request was enqueued for later
// replay. Callers can recognise `code === 'OFFLINE_QUEUED'` to surface a
// user-facing "action will retry" banner instead of treating it as an
// error.
export class OfflineQueuedError extends Error {
  readonly code = 'OFFLINE_QUEUED'
  readonly queueId: string
  readonly idempotencyKey: string
  constructor(queueId: string, idempotencyKey: string) {
    super('Request was queued offline and will retry when connectivity is restored.')
    this.queueId = queueId
    this.idempotencyKey = idempotencyKey
  }
}

const MUTATION_METHODS: ReadonlySet<string> = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])

function isOnline(): boolean {
  try {
    return typeof navigator === 'undefined' ? true : navigator.onLine !== false
  } catch {
    return true
  }
}

function generateIdempotencyKey(): string {
  const rand = Math.random().toString(16).slice(2, 10)
  return `idem-${Date.now()}-${rand}`
}

async function enqueueMutation(
  opts: HttpOptions,
  serializedBody: string | null,
): Promise<never> {
  const idempotencyKey = opts.idempotencyKey ?? generateIdempotencyKey()
  const queue = getOfflineQueue()
  const body = serializedBody !== null ? JSON.parse(serializedBody) : null
  const queueId = await queue.enqueue({
    method: opts.method,
    path: opts.path,
    body,
    idempotencyKey,
  })
  throw new OfflineQueuedError(queueId, idempotencyKey)
}

// Paths that require canonical ECDSA request signing (X-Request-Signature + nonce + timestamp).
// Backend enforcement is per-route via Depends(require_signed_request); this list
// tells the HTTP wrapper which outbound requests must include signing headers.
// Prefix matching is used: a path matches if it equals an entry or starts with "<entry>/".
//
// Device rotate uses signed: true at the call site (see authApi.rotateDevice) rather
// than a prefix entry here. Device challenge/activate/register do NOT use canonical
// signing — activate uses a challenge-signature payload (the private key signs the
// enrollment nonce in the request body) before any device_id exists, which is a
// distinct bootstrap mechanism.
//
// The `/api/v1/orders` prefix implicitly covers the full family of order-nested
// mutation endpoints that the backend now signs under audit-5 B2:
//   POST /orders, /orders/{id}/bargaining/offer,
//   /orders/{id}/payment/proof, /orders/{id}/payment/confirm,
//   /orders/{id}/voucher, /orders/{id}/milestones,
//   /orders/{id}/refund, /orders/{id}/refund/process,
//   /orders/{id}/after-sales, /orders/{id}/after-sales/{req}/resolve.
//
// The `/api/v1/attendance/exceptions` prefix covers POST /exceptions plus the new
// /exceptions/{id}/proof (multipart upload) and /exceptions/{id}/review endpoints.
// Keep-alive reminder: if a future signed endpoint lives OUTSIDE these two
// subtrees, add an explicit entry here.
export const SIGNED_PATHS: readonly string[] = [
  '/api/v1/auth/password/change',
  '/api/v1/candidates',         // covers /candidates/{id}/documents/upload
  '/api/v1/orders',             // covers POST /orders and every signed /orders/{id}/* sub-route (see above)
  '/api/v1/attendance/exceptions', // covers POST /exceptions, /proof, /review
]

export function shouldSign(path: string): boolean {
  return SIGNED_PATHS.some((p) => path === p || path.startsWith(`${p}/`))
}

export async function request<T>(opts: HttpOptions): Promise<T> {
  return executeRequest<T>(opts, false)
}

async function executeRequest<T>(opts: HttpOptions, isRetry: boolean): Promise<T> {
  const auth = useAuthStore()
  const headers: Record<string, string> = {
    Accept: 'application/json',
    ...(opts.headers ?? {}),
  }
  const hasJsonBody = opts.body !== undefined && opts.body !== null
  const serializedBody = hasJsonBody ? JSON.stringify(opts.body) : null
  if (hasJsonBody) headers['Content-Type'] = 'application/json'
  if (opts.idempotencyKey) headers['Idempotency-Key'] = opts.idempotencyKey
  if (!opts.skipAuth && auth.tokens?.access_token) {
    headers['Authorization'] = `Bearer ${auth.tokens.access_token}`
  }

  // Offline-ready: if the browser reports itself offline before we even
  // issue the fetch, divert retryable mutations to the offline queue so
  // they can be replayed once connectivity is restored. GETs and already-
  // retried requests fall through to a normal fetch (which will surface
  // the network error to the caller). We check this BEFORE signing so an
  // un-enrolled device or a signing failure does not mask the offline
  // enqueue path — replay will re-sign with fresh credentials.
  if (
    !isRetry &&
    MUTATION_METHODS.has(opts.method) &&
    !isOnline()
  ) {
    await enqueueMutation(opts, serializedBody)
  }

  if (opts.signed ?? shouldSign(opts.path)) {
    await attachSigningHeaders(headers, opts, serializedBody)
  }

  let response: Response
  try {
    response = await fetch(opts.path, {
      method: opts.method,
      body: serializedBody ?? undefined,
      headers,
      credentials: 'same-origin',
    })
  } catch (networkErr) {
    if (!isRetry && MUTATION_METHODS.has(opts.method)) {
      await enqueueMutation(opts, serializedBody)
    }
    throw networkErr
  }

  let envelope: ApiResponse<T> | null = null
  try {
    envelope = (await response.json()) as ApiResponse<T>
  } catch {
    envelope = null
  }

  if (!response.ok) {
    const errorBody = envelope as ApiError | null
    if (
      !isRetry &&
      !opts.skipRefresh &&
      response.status === 401 &&
      errorBody?.error?.code === 'TOKEN_EXPIRED'
    ) {
      const refreshed = await auth.refresh()
      if (refreshed) return executeRequest<T>(opts, true)
    }
    throw new HttpError(
      response.status,
      errorBody ?? {
        success: false,
        error: { code: 'HTTP_ERROR', message: `HTTP ${response.status}` },
        meta: { trace_id: 'unknown', timestamp: new Date().toISOString() },
      },
    )
  }

  if (envelope && 'data' in envelope) {
    return envelope.data as T
  }
  return undefined as T
}

async function attachSigningHeaders(
  headers: Record<string, string>,
  opts: HttpOptions,
  serializedBody: string | null,
): Promise<void> {
  await addSigningHeaders(headers, opts.method, opts.path, serializedBody)
}

/**
 * Computes and attaches ECDSA signing headers to the given headers map.
 * Accepts a body as string (JSON) or Uint8Array (binary/multipart).
 * Use this for non-JSON requests (e.g. multipart file uploads) that still require signing.
 */
export async function addSigningHeaders(
  headers: Record<string, string>,
  method: string,
  path: string,
  body: string | Uint8Array | null,
): Promise<void> {
  const record = await getOrCreateDeviceKey()
  if (!record.deviceId) {
    throw new Error('Device not registered; call enrollDevice() before signing.')
  }
  const ts = currentTimestamp()
  const nonce = generateNonce()
  const sig = await signRequest(record.privateKey, { method, path, timestamp: ts, nonce, deviceId: record.deviceId, body })
  headers['X-Timestamp'] = ts
  headers['X-Nonce'] = nonce
  headers['X-Device-ID'] = record.deviceId
  headers['X-Request-Signature'] = sig
}
