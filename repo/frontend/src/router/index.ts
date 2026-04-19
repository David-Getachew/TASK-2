import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { requireAuthGuard, requireRoleGuard } from './guards'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/login',
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/auth/LoginView.vue'),
  },
  {
    path: '/forbidden',
    name: 'forbidden',
    component: () => import('@/views/common/ForbiddenView.vue'),
  },
  {
    path: '/session-expired',
    name: 'session-expired',
    component: () => import('@/views/common/SessionExpiredView.vue'),
  },

  // ── Candidate ────────────────────────────────────────────────────────────
  {
    path: '/candidate',
    component: () => import('@/views/candidate/CandidateLayout.vue'),
    meta: { requiresAuth: true, role: 'candidate' },
    children: [
      { path: '', name: 'candidate-dashboard', component: () => import('@/views/candidate/CandidateDashboard.vue') },
      { path: 'profile', name: 'candidate-profile', component: () => import('@/views/candidate/profile/ProfileView.vue') },
      { path: 'profile/exam-scores', name: 'candidate-exam-scores', component: () => import('@/views/candidate/profile/ExamScoresView.vue') },
      { path: 'profile/transfer-preferences', name: 'candidate-transfer-prefs', component: () => import('@/views/candidate/profile/TransferPreferencesView.vue') },
      { path: 'documents', name: 'candidate-documents', component: () => import('@/views/candidate/documents/DocumentListView.vue') },
      { path: 'documents/upload', name: 'candidate-upload', component: () => import('@/views/candidate/documents/DocumentUploadView.vue') },
      { path: 'orders', name: 'candidate-orders', component: () => import('@/views/candidate/orders/OrderListView.vue') },
      { path: 'orders/catalog', name: 'candidate-catalog', component: () => import('@/views/candidate/orders/ServiceCatalogView.vue') },
      { path: 'orders/:orderId', name: 'candidate-order-detail', component: () => import('@/views/candidate/orders/OrderDetailView.vue') },
      { path: 'orders/:orderId/bargaining', name: 'candidate-bargaining', component: () => import('@/views/candidate/orders/BargainingView.vue') },
      { path: 'orders/:orderId/payment', name: 'candidate-payment', component: () => import('@/views/candidate/orders/PaymentView.vue') },
      { path: 'orders/:orderId/after-sales', name: 'candidate-after-sales', component: () => import('@/views/candidate/orders/AfterSalesView.vue') },
      { path: 'attendance', name: 'candidate-attendance', component: () => import('@/views/candidate/attendance/ExceptionListView.vue') },
      { path: 'attendance/:exceptionId', name: 'candidate-exception-detail', component: () => import('@/views/candidate/attendance/ExceptionDetailView.vue') },
    ],
  },

  // ── Staff (proctor + reviewer) ────────────────────────────────────────────
  //
  // The staff layout admits both proctor and reviewer so they share chrome,
  // but access to each sub-route is narrowed by `meta.role` to match the
  // backend role policy. Proctor is the frontline attendance adjudicator
  // and is only allowed on the exception queue/review screens; reviewer
  // owns document / payment / order / after-sales adjudication queues
  // (see repo/backend/src/api/routes/queue.py).
  {
    path: '/staff',
    component: () => import('@/views/staff/StaffLayout.vue'),
    meta: { requiresAuth: true, role: ['proctor', 'reviewer'] },
    children: [
      { path: '', name: 'staff-dashboard', component: () => import('@/views/staff/StaffDashboard.vue') },
      { path: 'documents', name: 'staff-document-queue', component: () => import('@/views/staff/documents/DocumentQueueView.vue'), meta: { role: ['reviewer'] } },
      { path: 'documents/:documentId/review', name: 'staff-document-review', component: () => import('@/views/staff/documents/DocumentReviewView.vue'), meta: { role: ['reviewer'] } },
      { path: 'payments', name: 'staff-payment-queue', component: () => import('@/views/staff/orders/PaymentQueueView.vue'), meta: { role: ['reviewer'] } },
      { path: 'orders', name: 'staff-order-queue', component: () => import('@/views/staff/orders/OrderQueueView.vue'), meta: { role: ['reviewer'] } },
      { path: 'orders/:orderId', name: 'staff-order-detail', component: () => import('@/views/staff/orders/OrderDetailView.vue'), meta: { role: ['reviewer'] } },
      { path: 'exceptions', name: 'staff-exception-queue', component: () => import('@/views/staff/attendance/ExceptionQueueView.vue'), meta: { role: ['proctor', 'reviewer'] } },
      { path: 'exceptions/:exceptionId/review', name: 'staff-exception-review', component: () => import('@/views/staff/attendance/ExceptionReviewView.vue'), meta: { role: ['proctor', 'reviewer'] } },
      { path: 'after-sales', name: 'staff-after-sales', component: () => import('@/views/staff/orders/AfterSalesQueueView.vue'), meta: { role: ['reviewer'] } },
    ],
  },

  // ── Admin ─────────────────────────────────────────────────────────────────
  {
    path: '/admin',
    component: () => import('@/views/admin/AdminLayout.vue'),
    meta: { requiresAuth: true, role: 'admin' },
    children: [
      { path: '', name: 'admin-dashboard', component: () => import('@/views/admin/AdminDashboard.vue') },
      { path: 'users', name: 'admin-users', component: () => import('@/views/admin/UsersView.vue') },
      { path: 'queues', name: 'admin-queues', component: () => import('@/views/admin/QueuesView.vue') },
      { path: 'audit', name: 'admin-audit', component: () => import('@/views/admin/AuditLogView.vue') },
      { path: 'config', name: 'admin-config', component: () => import('@/views/admin/ConfigView.vue') },
      { path: 'forecasts', name: 'admin-forecasts', component: () => import('@/views/admin/ForecastView.vue') },
      { path: 'observability', name: 'admin-observability', component: () => import('@/views/admin/ObservabilityView.vue') },
      { path: 'exports', name: 'admin-exports', component: () => import('@/views/admin/ExportsView.vue') },
    ],
  },

  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/common/NotFoundView.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(requireAuthGuard)
router.beforeEach(requireRoleGuard)

export default router
