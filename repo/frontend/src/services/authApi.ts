// Typed wrappers for each backend auth endpoint.
// Keeps request shapes and response types colocated so stores/composables
// don't need to know about raw paths or idempotency headers.

import { request } from './http'
import type {
  DeviceChallenge,
  DeviceRegistration,
  LoginResponse,
  MeResponse,
  RefreshResponse,
} from '@/types/auth'

export interface LoginPayload {
  username: string
  password: string
  nonce: string
  timestamp: string
}

export interface PasswordChangePayload {
  current_password: string
  new_password: string
  nonce: string
  timestamp: string
}

// BE `DeviceRegisterRequest` (schemas/auth.py). Used for direct service-managed
// registration only; the normal browser flow is challenge → activate (no register).
export interface DeviceRegisterPayload {
  device_fingerprint: string
  public_key_pem: string
  label?: string | null
}

// BE `DeviceChallengeRequest` (schemas/auth.py). Requires fingerprint + public key
// so the server can bind the issued nonce to the caller's device identity.
export interface DeviceChallengePayload {
  device_fingerprint: string
  public_key_pem: string
  label?: string | null
}

// BE `DeviceActivateRequest` (schemas/auth.py). Activation registers the device
// in a single atomic step — signature is computed over the raw challenge nonce
// UTF-8 bytes (not the request-canonical METHOD\nPATH\n… form).
export interface DeviceActivatePayload {
  challenge_id: string
  device_fingerprint: string
  public_key_pem: string
  signature: string
  label?: string | null
}

export function login(payload: LoginPayload): Promise<LoginResponse> {
  return request<LoginResponse>({
    method: 'POST',
    path: '/api/v1/auth/login',
    body: payload,
    skipAuth: true,
    skipRefresh: true,
  })
}

export interface RefreshPayload {
  refresh_token: string
  nonce: string
  timestamp: string
}

export function refresh(payload: RefreshPayload): Promise<RefreshResponse> {
  return request<RefreshResponse>({
    method: 'POST',
    path: '/api/v1/auth/refresh',
    body: payload,
    skipAuth: true,
    skipRefresh: true,
  })
}

export function logout(refreshToken: string): Promise<void> {
  return request<void>({
    method: 'POST',
    path: '/api/v1/auth/logout',
    body: { refresh_token: refreshToken },
    skipRefresh: true,
  })
}

export function me(): Promise<MeResponse> {
  return request<MeResponse>({
    method: 'GET',
    path: '/api/v1/auth/me',
  })
}

export function changePassword(payload: PasswordChangePayload): Promise<void> {
  return request<void>({
    method: 'POST',
    path: '/api/v1/auth/password/change',
    body: payload,
    signed: true,
  })
}

export function challenge(
  payload: DeviceChallengePayload,
): Promise<DeviceChallenge> {
  return request<DeviceChallenge>({
    method: 'POST',
    path: '/api/v1/auth/device/challenge',
    body: payload,
  })
}

// Activate consumes the enrollment challenge, verifies the signature over the
// raw nonce, registers the device atomically, and returns the assigned
// device_id. BE response model: `DeviceRegisterResponse`.
export function activate(payload: DeviceActivatePayload): Promise<DeviceRegistration> {
  return request<DeviceRegistration>({
    method: 'POST',
    path: '/api/v1/auth/device/activate',
    body: payload,
  })
}

export function registerDevice(
  payload: DeviceRegisterPayload,
): Promise<DeviceRegistration> {
  return request<DeviceRegistration>({
    method: 'POST',
    path: '/api/v1/auth/device/register',
    body: payload,
  })
}

export function rotateDevice(
  deviceId: string,
  payload: DeviceRegisterPayload,
): Promise<DeviceRegistration> {
  return request<DeviceRegistration>({
    method: 'POST',
    path: `/api/v1/auth/device/${encodeURIComponent(deviceId)}/rotate`,
    body: payload,
    signed: true,
  })
}

export function revokeDevice(deviceId: string): Promise<void> {
  return request<void>({
    method: 'DELETE',
    path: `/api/v1/auth/device/${encodeURIComponent(deviceId)}`,
  })
}
