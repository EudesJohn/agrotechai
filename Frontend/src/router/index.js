import { createRouter, createWebHistory } from 'vue-router'
import { supabase } from '../supabase'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('../views/HomeView.vue')
    },
    {
      path: '/diagnostic',
      name: 'diagnostic',
      component: () => import('../views/DiagnosticView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/history',
      name: 'history',
      component: () => import('../views/HistoryView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/community',
      name: 'community',
      component: () => import('../views/SocialFeed.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/profile',
      name: 'profile',
      component: () => import('../views/ProfileView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/profile/:userId',
      name: 'public-profile',
      component: () => import('../views/PublicProfileView.vue')
    },
    {
      path: '/messages',
      name: 'messages',
      component: () => import('../views/ChatView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/admin',
      name: 'admin',
      component: () => import('../views/AdminView.vue'),
      meta: { requiresAuth: true }
    },
  ]
})

router.beforeEach(async (to, from, next) => {
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth)

  if (requiresAuth) {
    // Vérifier la session Supabase (sans attendre un listener)
    const { data: { session } } = await supabase.auth.getSession()
    if (!session) {
      // Timeout de sécurité après 10s (au cas où getSession échoue)
      const timeoutPromise = new Promise(resolve => setTimeout(() => resolve(null), 10000))

      const { data } = await Promise.race([
        supabase.auth.getSession(),
        timeoutPromise.then(() => ({ data: { session: null } }))
      ])

      if (!data?.session) {
        next('/')
        return
      }
    }
  }

  next()
})

export default router
