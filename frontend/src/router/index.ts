/**
 * Vue Router configuration with auth guards.
 */
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory('/redvault/'),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('../views/LoginView.vue'),
      meta: { guest: true },
    },
    {
      path: '/',
      component: () => import('../layouts/AppLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'Dashboard',
          component: () => import('../views/DashboardView.vue'),
        },
        {
          path: 'findings',
          name: 'Findings',
          component: () => import('../views/FindingsView.vue'),
        },
        {
          path: 'findings/:id',
          name: 'FindingDetail',
          component: () => import('../views/FindingDetailView.vue'),
          props: true,
        },
        {
          path: 'assets',
          name: 'Assets',
          component: () => import('../views/AssetsView.vue'),
        },
        {
          path: 'assets/:id',
          name: 'AssetDetail',
          component: () => import('../views/AssetDetailView.vue'),
          props: true,
        },
        {
          path: 'clients',
          name: 'Clients',
          component: () => import('../views/ClientsView.vue'),
        },
        {
          path: 'clients/:id',
          name: 'ClientDetail',
          component: () => import('../views/ClientDetailView.vue'),
          props: true,
        },
        {
          path: 'reports',
          name: 'Reports',
          component: () => import('../views/TemplatesView.vue'),
        },
        {
          path: 'users',
          name: 'Users',
          component: () => import('../views/UsersView.vue'),
          meta: { requiresAdmin: true },
        },
      ],
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
})

router.beforeEach(async (to, _from, next) => {
  const auth = useAuthStore()

  // Initialize auth state if needed
  if (auth.accessToken && !auth.user) {
    await auth.init()
  }

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return next({ name: 'Login' })
  }

  if (to.meta.guest && auth.isAuthenticated) {
    return next({ path: '/' })
  }

  if (to.meta.requiresAdmin && !auth.isAdmin) {
    return next({ path: '/' })
  }

  next()
})

export default router
