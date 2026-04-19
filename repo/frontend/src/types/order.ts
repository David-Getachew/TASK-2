export type OrderStatus =
  | 'pending_payment'
  | 'pending_fulfillment'
  | 'pending_receipt'
  | 'completed'
  | 'canceled'
  | 'refund_in_progress'
  | 'refunded'

export type PricingMode = 'fixed' | 'bargaining'

// Shape mirrors backend `schemas/order.py::ServiceItemRead`. Prior FE version
// used `base_price`/`is_active`/`pricing_mode: string` which the backend does
// not return — the real catalog uses `item_code`, `fixed_price` and a
// `bargaining_enabled` flag alongside `pricing_mode`.
export interface ServiceItem {
  id: string
  item_code: string
  name: string
  description: string | null
  pricing_mode: PricingMode
  fixed_price: string | null
  is_capacity_limited: boolean
  bargaining_enabled: boolean
  available_slots: number | null
}

// Shape mirrors backend `schemas/order.py::OrderEventRead`. Prior FE version
// used `order_id`/`prev_state`/`created_at` — backend emits `sequence_number`,
// `previous_state`, `occurred_at` instead and does not echo `order_id`.
export interface OrderEvent {
  id: string
  sequence_number: number
  event_type: string
  previous_state: OrderStatus | null
  new_state: OrderStatus
  actor_id: string | null
  actor_role: string | null
  notes: string | null
  occurred_at: string
}

export interface PaymentRecord {
  id: string
  order_id: string
  amount: string
  payment_method: string
  reference_number: string
  notes: string | null
  confirmed_by: string | null
  confirmed_at: string | null
  created_at: string
}

export interface BargainingOffer {
  id: string
  thread_id: string
  offer_number: number
  amount: string
  submitted_by: string
  // Matches backend `OfferRead.submitted_at`. BE emits the wall-clock time
  // the offer was recorded; views should render this field directly.
  submitted_at: string
  outcome: 'pending' | 'accepted' | 'expired' | null
}

export type BargainingThreadStatus =
  | 'open'
  | 'accepted'
  | 'countered'
  | 'counter_accepted'
  | 'expired'

// Shape mirrors backend `schemas/bargaining.py::BargainingThreadRead`. BE
// omits `counter_by`, `resolved_offer_id`, and `created_at`; views should not
// depend on them. `counter_at` / `resolved_at` are emitted directly.
export interface BargainingThread {
  id: string
  order_id: string
  status: BargainingThreadStatus
  window_starts_at: string
  window_expires_at: string
  offers: BargainingOffer[]
  counter_amount: string | null
  counter_count: number
  counter_at: string | null
  resolved_at: string | null
}

export interface Voucher {
  id: string
  order_id: string
  voucher_code: string
  issued_by: string
  notes: string | null
  created_at: string
}

export interface FulfillmentMilestone {
  id: string
  order_id: string
  milestone_type: string
  description: string | null
  recorded_by: string
  occurred_at: string
  created_at: string
}

export interface RefundRecord {
  id: string
  order_id: string
  amount: string
  initiated_by: string
  initiated_at: string
  processed_by: string | null
  processed_at: string | null
  rollback_applied: boolean
  reason: string | null
}

export type AfterSalesStatus = 'open' | 'resolved'

export interface AfterSalesRequest {
  id: string
  order_id: string
  requested_by: string
  request_type: string
  description: string
  status: AfterSalesStatus
  window_expires_at: string
  resolved_by: string | null
  resolved_at: string | null
  resolution_notes: string | null
  created_at: string
}

// Shape mirrors backend `schemas/order.py::OrderRead`. The backend response
// does NOT include `item_name`, `base_price`, `idempotency_key`,
// `payment_record`, or `bargaining_thread` — views should resolve the service
// item via `serviceApi.getServiceItem(item_id)` (or the service-item store)
// for display pricing/naming, and fetch the bargaining thread / payment
// proofs via their own endpoints.
export interface Order {
  id: string
  candidate_id: string
  item_id: string
  status: OrderStatus
  pricing_mode: PricingMode
  agreed_price: string | null
  auto_cancel_at: string | null
  completed_at: string | null
  canceled_at: string | null
  cancellation_reason: string | null
  created_at: string
  updated_at: string
  events: OrderEvent[]
}

export interface OrderCreate {
  item_id: string
  pricing_mode?: PricingMode
  notes?: string | null
}

export interface PaymentProofSubmit {
  payment_method: string
  reference_number: string
  amount: string
  notes?: string | null
}

export interface PaymentConfirmPayload {
  amount: string
  payment_method: string
  reference_number?: string | null
  notes?: string | null
}

export interface AfterSalesRequestCreate {
  request_type: string
  description: string
}

export interface VoucherCreate {
  notes?: string | null
}

export interface MilestoneCreate {
  milestone_type: string
  description?: string | null
  occurred_at?: string
}

export interface RefundCreate {
  amount: string
  reason?: string | null
}
