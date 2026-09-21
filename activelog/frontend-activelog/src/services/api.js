// ActiveLog API Service - Connects to SuperInstance production backend
// Integration with operational services: Auth (8001), AI Insights (8090), User Management (8092), 
// Workout Sessions (8093), Nutrition Tracking (8094)

import axios from 'axios'

// API Configuration connecting to operational SuperInstance services
const API_CONFIG = {
  BASE_URL: '/api', // Proxied through Vite to API Gateway (8088)
  SERVICES: {
    AUTH: 'http://localhost:8001',
    USER_MANAGEMENT: 'http://localhost:8092', 
    AI_INSIGHTS: 'http://localhost:8090',
    WORKOUT_SESSIONS: 'http://localhost:8093',
    NUTRITION_TRACKING: 'http://localhost:8094'
  },
  TIMEOUT: 10000
}

// Create axios instance with default configuration
const apiClient = axios.create({
  baseURL: API_CONFIG.BASE_URL,
  timeout: API_CONFIG.TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor - Add JWT token from localStorage
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('activelog_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor - Handle errors and token refresh
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear invalid token and redirect to login
      localStorage.removeItem('activelog_token')
      localStorage.removeItem('activelog_user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Authentication API - Connects to SuperInstance Auth Service (port 8001)
export const authAPI = {
  async login(email, password) {
    const response = await apiClient.post('/auth/login', { email, password })
    const { token, user } = response.data
    
    // Store authentication data
    localStorage.setItem('activelog_token', token)
    localStorage.setItem('activelog_user', JSON.stringify(user))
    
    return { token, user }
  },

  async register(userData) {
    const response = await apiClient.post('/auth/register', userData)
    const { token, user } = response.data
    
    localStorage.setItem('activelog_token', token)
    localStorage.setItem('activelog_user', JSON.stringify(user))
    
    return { token, user }
  },

  async logout() {
    localStorage.removeItem('activelog_token')
    localStorage.removeItem('activelog_user')
    window.location.href = '/login'
  },

  async verifyToken() {
    try {
      const response = await apiClient.get('/auth/verify')
      return response.data
    } catch (error) {
      this.logout()
      throw error
    }
  }
}

// User Management API - Connects to AI-integrated User Management Service (port 8092)
export const userAPI = {
  async getProfile() {
    const response = await apiClient.get('/user/profile')
    return response.data
  },

  async updateProfile(profileData) {
    const response = await apiClient.put('/user/profile', profileData)
    return response.data
  },

  async getFitnessGoals() {
    const response = await apiClient.get('/user/fitness-goals')
    return response.data
  },

  async updateFitnessGoals(goals) {
    const response = await apiClient.put('/user/fitness-goals', goals)
    return response.data
  },

  async getDashboardData() {
    const response = await apiClient.get('/user/dashboard')
    return response.data
  }
}

// Workout Sessions API - Connects to Workout Sessions Service (port 8093)
export const workoutAPI = {
  async getWorkouts(params = {}) {
    const response = await apiClient.get('/workouts', { params })
    return response.data
  },

  async getWorkout(workoutId, includeAIInsights = false) {
    const response = await apiClient.get(`/workouts/${workoutId}`, {
      params: { include_ai_insights: includeAIInsights }
    })
    return response.data
  },

  async createWorkout(workoutData) {
    const response = await apiClient.post('/workouts', workoutData)
    return response.data
  },

  async updateWorkout(workoutId, updateData) {
    const response = await apiClient.put(`/workouts/${workoutId}`, updateData)
    return response.data
  },

  async addExercise(workoutId, exerciseData) {
    const response = await apiClient.post(`/workouts/${workoutId}/exercises`, exerciseData)
    return response.data
  },

  async getDashboardStats(days = 30) {
    const response = await apiClient.get('/dashboard/stats', { params: { days } })
    return response.data
  },

  async getWorkoutAIInsights(workoutId) {
    const response = await apiClient.get(`/workouts/${workoutId}/ai-insights`)
    return response.data
  }
}

// Nutrition Tracking API - Connects to Nutrition Tracking Service (port 8094)
export const nutritionAPI = {
  async logFood(nutritionData) {
    const response = await apiClient.post('/nutrition', nutritionData)
    return response.data
  },

  async getNutritionDay(date, includeAIInsights = false) {
    const response = await apiClient.get(`/nutrition/day/${date}`, {
      params: { include_ai_insights: includeAIInsights }
    })
    return response.data
  },

  async getNutritionWeek(startDate) {
    const response = await apiClient.get('/nutrition/week', {
      params: { start_date: startDate }
    })
    return response.data
  },

  async searchFood(foodName, limit = 10) {
    const response = await apiClient.get(`/nutrition/search/${foodName}`, {
      params: { limit }
    })
    return response.data
  },

  async getNutritionGoals() {
    const response = await apiClient.get('/nutrition/goals')
    return response.data
  },

  async updateNutritionGoals(goals) {
    const response = await apiClient.put('/nutrition/goals', goals)
    return response.data
  },

  async deleteNutritionEntry(entryId) {
    const response = await apiClient.delete(`/nutrition/${entryId}`)
    return response.data
  },

  async getMobileDashboard() {
    const response = await apiClient.get('/nutrition/mobile-dashboard')
    return response.data
  },

  async getAIInsights(days = 7) {
    const response = await apiClient.get('/nutrition/ai-insights', {
      params: { days }
    })
    return response.data
  }
}

// AI Insights API - Connects to AI Insights Service (port 8090) with vector embeddings
export const aiAPI = {
  async getWorkoutInsights(workoutSessionId, analysisType = 'comprehensive') {
    const response = await apiClient.post('/workout/insights', {
      workout_session_id: workoutSessionId,
      analysis_type: analysisType
    })
    return response.data
  },

  async getNutritionInsights(userId, daysBack = 7, focus = 'balance') {
    const response = await apiClient.post('/nutrition/insights', {
      user_id: userId,
      days_back: daysBack,
      focus
    })
    return response.data
  },

  async getPersonalizedRecommendations(userId, recommendationType = 'workout') {
    const response = await apiClient.post('/recommendations/personalized', {
      user_id: userId,
      recommendation_type: recommendationType
    })
    return response.data
  },

  async getFitnessTrends(userId, timeframe = 'monthly') {
    const response = await apiClient.get(`/user/${userId}/fitness-trends`, {
      params: { timeframe }
    })
    return response.data
  },

  async storeWorkoutEmbedding(workoutSessionId) {
    const response = await apiClient.post('/workout/store-embedding', {
      workout_session_id: workoutSessionId
    })
    return response.data
  }
}

// Health check for all services
export const healthAPI = {
  async checkAllServices() {
    const services = [
      { name: 'AI Insights', endpoint: '/ai-insights/health' },
      { name: 'User Management', endpoint: '/user-management/health' },
      { name: 'Workout Sessions', endpoint: '/workout-sessions/health' },
      { name: 'Nutrition Tracking', endpoint: '/nutrition-tracking/health' }
    ]

    const results = {}
    
    for (const service of services) {
      try {
        const response = await apiClient.get(service.endpoint)
        results[service.name] = { status: 'healthy', data: response.data }
      } catch (error) {
        results[service.name] = { status: 'error', error: error.message }
      }
    }
    
    return results
  }
}

// Export configured axios client for direct use
export default apiClient