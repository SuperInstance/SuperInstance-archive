import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'
import './assets/css/main.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

// Global error handler for API errors
app.config.errorHandler = (err, instance, info) => {
  console.error('Global error:', err, info)
  
  // Handle API errors gracefully
  if (err?.response?.status === 401) {
    router.push('/login')
  }
}

app.mount('#app')