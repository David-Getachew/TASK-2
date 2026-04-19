import { request } from './http'
import type { BargainingThread } from '@/types/order'
import { currentTimestamp, generateNonce } from './requestSigner'

export function submitOffer(
  orderId: string,
  amount: string,
): Promise<{ id: string; offer_number: number; amount: string }> {
  return request({
    method: 'POST',
    path: `/api/v1/orders/${encodeURIComponent(orderId)}/bargaining/offer`,
    body: { amount, nonce: generateNonce(), timestamp: currentTimestamp() },
  })
}

export function getBargainingThread(orderId: string): Promise<BargainingThread> {
  return request<BargainingThread>({
    method: 'GET',
    path: `/api/v1/orders/${encodeURIComponent(orderId)}/bargaining`,
  })
}

export function acceptOffer(
  orderId: string,
  offerId: string,
): Promise<BargainingThread> {
  return request<BargainingThread>({
    method: 'POST',
    path: `/api/v1/orders/${encodeURIComponent(orderId)}/bargaining/accept`,
    body: {
      offer_id: offerId,
      nonce: generateNonce(),
      timestamp: currentTimestamp(),
    },
  })
}

export function counterOffer(
  orderId: string,
  counterAmount: string,
  notes?: string,
): Promise<BargainingThread> {
  return request<BargainingThread>({
    method: 'POST',
    path: `/api/v1/orders/${encodeURIComponent(orderId)}/bargaining/counter`,
    body: { counter_amount: counterAmount, notes: notes ?? null },
  })
}

export function acceptCounter(orderId: string): Promise<BargainingThread> {
  return request<BargainingThread>({
    method: 'POST',
    path: `/api/v1/orders/${encodeURIComponent(orderId)}/bargaining/accept-counter`,
    body: { nonce: generateNonce(), timestamp: currentTimestamp() },
  })
}
