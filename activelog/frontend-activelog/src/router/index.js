import { createRouter, createWebHistory } from 'vue-router'
import { authAPI } from '@/services/api'

// Import views
import Login from '@/views/auth/Login.vue'
import Register from '@/views/auth/Register.vue'
import Dashboard from '@/views/Dashboard.vue'
import Workouts from '@/views/workouts/Workouts.vue'
import WorkoutNew from '@/views/workouts/WorkoutNew.vue'
import WorkoutDetail from '@/views/workouts/WorkoutDetail.vue'
import Nutrition from '@/views/nutrition/Nutrition.vue'
import NutritionLog from '@/views/nutrition/NutritionLog.vue'
import Insights from '@/views/insights/Insights.vue'
import Profile from '@/views/Profile.vue'

const routes = [
  {
    path: '/',
    redirect: '/dashboard'
  },
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { requiresAuth: false }
  },
  {
    path: '/register',
    name: 'Register',
    component: Register,
    meta: { requiresAuth: false }
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: Dashboard,
    meta: { requiresAuth: true }
  },
  {
    path: '/workouts',
    name: 'Workouts',
    component: Workouts,
    meta: { requiresAuth: true }
  },
  {
    path: '/workout/new',
    name: 'WorkoutNew',
    component: WorkoutNew,
    meta: { requiresAuth: true, showBack: true }
  },
  {
    path: '/workout/:id',
    name: 'WorkoutDetail',
    component: WorkoutDetail,
    meta: { requiresAuth: true, showBack: true }
  },
  {
    path: '/nutrition',
    name: 'Nutrition',
    component: Nutrition,
    meta: { requiresAuth: true }
  },
  {
    path: '/nutrition/log',
    name: 'NutritionLog',
    component: NutritionLog,
    meta: { requiresAuth: true, showBack: true }
  },
  {
    path: '/insights',
    name: 'Insights',
    component: Insights,
    meta: { requiresAuth: true }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: Profile,
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Global auth guard
router.beforeEach(async (to, from, next) => {
  const requiresAuth = to.meta.requiresAuth !== false
  const token = localStorage.getItem('activelog_token')

  if (requiresAuth && !token) {
    next('/login')
    return
  }

  if (requiresAuth && token) {
    try {
      // Verify token is still valid
      await authAPI.verifyToken()
      next()
    } catch (error) {
      // Token invalid, redirect to login
      localStorage.removeItem('activelog_token')
      localStorage.removeItem('activelog_user')
      next('/login')
    }
    return
  }

  // If already logged in and trying to access auth pages, redirect to dashboard
  if (!requiresAuth && token && (to.path === '/login' || to.path === '/register')) {
    next('/dashboard')
    return
  }

  next()
})

export default router