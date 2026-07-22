import { createRouter, createWebHistory } from 'vue-router'
import { auth } from '../firebase'

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

  if (requiresAuth && !auth.currentUser) {
    // Attendre que Firebase ait fini de restaurer la session
    const user = await new Promise(resolve => {
      const unsubscribe = auth.onAuthStateChanged(user => {
        unsubscribe()
        resolve(user)
      })
      // Timeout de sécurité après 10s (pas 500ms) pour éviter la race condition
      setTimeout(() => {
        unsubscribe()
        resolve(auth.currentUser)
      }, 10000)
    })

    if (!user) {
      next('/')
      return
    }
  }

  next()
})

export default router
