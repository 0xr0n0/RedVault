<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useRouter } from 'vue-router'

const auth = useAuthStore()
const router = useRouter()

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    await auth.login({ username: username.value, password: password.value })
    router.push('/')
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Invalid credentials. Please try again.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-container">
    <div class="login-card card">
      <div class="login-header">
        <h1>RedVault</h1>
        <p class="text-muted">Sign in to continue</p>
      </div>

      <div v-if="error" class="alert alert-error">
        {{ error }}
      </div>

      <form @submit.prevent="handleLogin">
        <div class="form-group">
          <label for="username">Username</label>
          <input
            id="username"
            v-model="username"
            type="text"
            class="form-input"
            placeholder="Enter your username"
            required
            autofocus
          />
        </div>

        <div class="form-group">
          <label for="password">Password</label>
          <input
            id="password"
            v-model="password"
            type="password"
            class="form-input"
            placeholder="Enter your password"
            required
          />
        </div>

        <button
          type="submit"
          class="btn btn-primary"
          style="width: 100%; justify-content: center; margin-top: 0.5rem"
          :disabled="loading"
        >
          {{ loading ? 'Signing in…' : 'Sign In' }}
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.login-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 1rem;
}

.login-card {
  width: 100%;
  max-width: 400px;
}

.login-header {
  text-align: center;
  margin-bottom: 2rem;
}

.login-header h1 {
  font-size: 1.5rem;
  margin-bottom: 0.25rem;
}
</style>
