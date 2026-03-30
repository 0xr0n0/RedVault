<script setup lang="ts">
import { useAuthStore } from '../stores/auth'
import { useRouter } from 'vue-router'

const auth = useAuthStore()
const router = useRouter()

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="app-layout">
    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="sidebar-brand">
        <h2>RedVault</h2>
        <span class="text-muted" style="font-size: 0.75rem">Pentest Reporting</span>
      </div>

      <nav class="sidebar-nav">
        <router-link to="/" class="nav-item" active-class="" exact-active-class="router-link-active">
          📊 Dashboard
        </router-link>
        <router-link to="/findings" class="nav-item">
          📋 Findings
        </router-link>
        <router-link to="/assets" class="nav-item">
          🖥️ Assets
        </router-link>
        <router-link to="/clients" class="nav-item">
          🏢 Clients
        </router-link>
        <router-link to="/reports" class="nav-item">
          📄 Reports
        </router-link>
        <router-link v-if="auth.isAdmin" to="/users" class="nav-item">
          👥 Users
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <div class="user-info">
          <div class="user-name">{{ auth.user?.first_name }} {{ auth.user?.last_name }}</div>
          <div class="user-role badge" :class="`badge-${auth.user?.role}`">
            {{ auth.user?.role }}
          </div>
        </div>
        <button class="btn btn-secondary btn-sm" @click="handleLogout">
          Logout
        </button>
      </div>
    </aside>

    <!-- Main content -->
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  width: 240px;
  background-color: var(--color-bg-card);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  padding: 1.25rem;
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  z-index: 100;
}

.sidebar-brand {
  margin-bottom: 2rem;
}

.sidebar-brand h2 {
  font-size: 1.25rem;
  margin-bottom: 0.125rem;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  flex: 1;
}

.nav-item {
  display: block;
  padding: 0.625rem 0.75rem;
  border-radius: var(--radius);
  color: var(--color-text-muted);
  font-size: 0.9rem;
  transition: background-color 0.2s, color 0.2s;
}

.nav-item:hover {
  background-color: var(--color-bg-input);
  color: var(--color-text);
  text-decoration: none;
}

.nav-item.router-link-active {
  background-color: var(--color-primary);
  color: white;
}

.sidebar-footer {
  border-top: 1px solid var(--color-border);
  padding-top: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.user-name {
  font-size: 0.875rem;
  font-weight: 500;
}

.user-role {
  font-size: 0.65rem;
}

.main-content {
  flex: 1;
  margin-left: 240px;
  padding: 2rem;
}
</style>
