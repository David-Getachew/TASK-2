// IndexedDB-backed offline mutation queue.
// Persists pending requests across page reloads; replays them when the
// connection is restored. Falls back to an in-memory queue in environments
// where IndexedDB is unavailable (e.g., unit-test jsdom with no stub).

export interface QueuedRequest {
  id: string
  method: string
  path: string
  body: unknown
  idempotencyKey: string
  enqueuedAt: string
}

export interface OfflineQueue {
  enqueue(req: Omit<QueuedRequest, 'id' | 'enqueuedAt'>): Promise<string>
  list(): Promise<QueuedRequest[]>
  remove(id: string): Promise<void>
  clear(): Promise<void>
}

// ── IndexedDB implementation ───────────────────────────────────────────────

const DB_NAME = 'merittrack-offline'
const STORE_NAME = 'queue'
const DB_VERSION = 1

function openQueueDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = globalThis.indexedDB.open(DB_NAME, DB_VERSION)
    req.onupgradeneeded = () => {
      const db = req.result
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: 'id' })
      }
    }
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

class IndexedDbQueue implements OfflineQueue {
  private dbPromise: Promise<IDBDatabase>

  constructor() {
    this.dbPromise = openQueueDb()
  }

  async enqueue(req: Omit<QueuedRequest, 'id' | 'enqueuedAt'>): Promise<string> {
    const id = `q-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`
    const item: QueuedRequest = { ...req, id, enqueuedAt: new Date().toISOString() }
    const db = await this.dbPromise
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite')
      tx.objectStore(STORE_NAME).put(item)
      tx.oncomplete = () => resolve(id)
      tx.onerror = () => reject(tx.error)
    })
  }

  async list(): Promise<QueuedRequest[]> {
    const db = await this.dbPromise
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readonly')
      const req = tx.objectStore(STORE_NAME).getAll()
      req.onsuccess = () => resolve(req.result as QueuedRequest[])
      req.onerror = () => reject(req.error)
    })
  }

  async remove(id: string): Promise<void> {
    const db = await this.dbPromise
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite')
      tx.objectStore(STORE_NAME).delete(id)
      tx.oncomplete = () => resolve()
      tx.onerror = () => reject(tx.error)
    })
  }

  async clear(): Promise<void> {
    const db = await this.dbPromise
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite')
      tx.objectStore(STORE_NAME).clear()
      tx.oncomplete = () => resolve()
      tx.onerror = () => reject(tx.error)
    })
  }
}

// ── In-memory fallback ─────────────────────────────────────────────────────

class InMemoryQueue implements OfflineQueue {
  private items: QueuedRequest[] = []

  async enqueue(req: Omit<QueuedRequest, 'id' | 'enqueuedAt'>): Promise<string> {
    const id = `q-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`
    this.items.push({ ...req, id, enqueuedAt: new Date().toISOString() })
    return id
  }

  async list(): Promise<QueuedRequest[]> {
    return [...this.items]
  }

  async remove(id: string): Promise<void> {
    this.items = this.items.filter((x) => x.id !== id)
  }

  async clear(): Promise<void> {
    this.items = []
  }
}

// ── Singleton factory ──────────────────────────────────────────────────────

let singleton: OfflineQueue | null = null

function isIndexedDbAvailable(): boolean {
  try {
    return typeof globalThis.indexedDB !== 'undefined' && globalThis.indexedDB !== null
  } catch {
    return false
  }
}

export function getOfflineQueue(): OfflineQueue {
  if (!singleton) {
    singleton = isIndexedDbAvailable() ? new IndexedDbQueue() : new InMemoryQueue()
  }
  return singleton
}

export function __resetOfflineQueueForTests(): void {
  singleton = null
}

// ── Replay helper ──────────────────────────────────────────────────────────

export async function replayQueue(): Promise<{ replayed: number; failed: number }> {
  const queue = getOfflineQueue()
  const items = await queue.list()
  let replayed = 0
  let failed = 0

  for (const item of items) {
    try {
      const { request } = await import('./http')
      await request({
        method: item.method as 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE',
        path: item.path,
        body: item.body,
        idempotencyKey: item.idempotencyKey,
      })
      await queue.remove(item.id)
      replayed++
    } catch {
      failed++
    }
  }

  return { replayed, failed }
}
