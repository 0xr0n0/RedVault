<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../api/client'
import type { User, UserCreate, UserUpdate } from '../types'

const users = ref<User[]>([])
const loading = ref(true)
const error = ref('')
const showModal = ref(false)
const editingUser = ref<User | null>(null)

// Form fields
const form = ref<UserCreate & { is_active?: boolean }>({
  username: '',
  email: '',
  password: '',
  first_name: '',
  last_name: '',
  role: 'analyst',
})
const formError = ref('')
const saving = ref(false)

async function fetchUsers() {
  loading.value = true
  try {
    const { data } = await api.get('/users/?page_size=100')
    users.value = data.results || data
  } catch (e: any) {
    error.value = 'Failed to load users.'
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingUser.value = null
  form.value = {
    username: '',
    email: '',
    password: '',
    first_name: '',
    last_name: '',
    role: 'analyst',
  }
  formError.value = ''
  showModal.value = true
}

function openEdit(user: User) {
  editingUser.value = user
  form.value = {
    username: user.username,
    email: user.email,
    password: '',
    first_name: user.first_name,
    last_name: user.last_name,
    role: user.role,
    is_active: user.is_active,
  }
  formError.value = ''
  showModal.value = true
}

async function handleSubmit() {
  formError.value = ''
  saving.value = true
  try {
    if (editingUser.value) {
      // Update
      const payload: UserUpdate = { ...form.value }
      if (!payload.password) delete payload.password
      await api.patch(`/users/${editingUser.value.id}/`, payload)
    } else {
      // Create
      await api.post('/users/', form.value)
    }
    showModal.value = false
    await fetchUsers()
  } catch (e: any) {
    const data = e.response?.data
    if (data && typeof data === 'object') {
      formError.value = Object.entries(data)
        .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
        .join(' | ')
    } else {
      formError.value = 'Failed to save user.'
    }
  } finally {
    saving.value = false
  }
}

async function toggleActive(user: User) {
  try {
    await api.patch(`/users/${user.id}/`, { is_active: !user.is_active })
    await fetchUsers()
  } catch {
    error.value = 'Failed to update user status.'
  }
}

onMounted(fetchUsers)
</script>

<template>
  <div>
    <div class="flex-between mb-2">
      <h1>Users Management</h1>
      <button class="btn btn-primary" @click="openCreate">+ New User</button>
    </div>

    <div v-if="error" class="alert alert-error">{{ error }}</div>

    <div v-if="loading" class="text-muted text-center mt-3">Loading users…</div>

    <div v-else class="card table-container">
      <table>
        <thead>
          <tr>
            <th>Username</th>
            <th>Email</th>
            <th>Name</th>
            <th>Role</th>
            <th>Active</th>
            <th>Joined</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in users" :key="user.id">
            <td>{{ user.username }}</td>
            <td>{{ user.email }}</td>
            <td>{{ user.first_name }} {{ user.last_name }}</td>
            <td><span class="badge" :class="`badge-${user.role}`">{{ user.role }}</span></td>
            <td>
              <span :style="{ color: user.is_active ? 'var(--color-success)' : 'var(--color-danger)' }">
                {{ user.is_active ? '✓ Active' : '✗ Inactive' }}
              </span>
            </td>
            <td class="text-muted">{{ new Date(user.date_joined).toLocaleDateString() }}</td>
            <td>
              <div class="flex gap-1">
                <button class="btn btn-secondary btn-sm" @click="openEdit(user)">Edit</button>
                <button
                  class="btn btn-sm"
                  :class="user.is_active ? 'btn-danger' : 'btn-primary'"
                  @click="toggleActive(user)"
                >
                  {{ user.is_active ? 'Deactivate' : 'Activate' }}
                </button>
              </div>
            </td>
          </tr>
          <tr v-if="users.length === 0">
            <td colspan="7" class="text-center text-muted">No users found.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Modal: Create / Edit User -->
    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal">
        <h2>{{ editingUser ? 'Edit User' : 'Create User' }}</h2>

        <div v-if="formError" class="alert alert-error">{{ formError }}</div>

        <form @submit.prevent="handleSubmit">
          <div class="form-group">
            <label>Username</label>
            <input v-model="form.username" class="form-input" required />
          </div>
          <div class="form-group">
            <label>Email</label>
            <input v-model="form.email" type="email" class="form-input" required />
          </div>
          <div class="form-group">
            <label>{{ editingUser ? 'New Password (leave blank to keep)' : 'Password' }}</label>
            <input
              v-model="form.password"
              type="password"
              class="form-input"
              :required="!editingUser"
              minlength="8"
            />
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem">
            <div class="form-group">
              <label>First Name</label>
              <input v-model="form.first_name" class="form-input" required />
            </div>
            <div class="form-group">
              <label>Last Name</label>
              <input v-model="form.last_name" class="form-input" required />
            </div>
          </div>
          <div class="form-group">
            <label>Role</label>
            <select v-model="form.role" class="form-select">
              <option value="admin">Admin</option>
              <option value="analyst">Analyst</option>
              <option value="viewer">Viewer</option>
            </select>
          </div>
          <div v-if="editingUser" class="form-group">
            <label>
              <input type="checkbox" v-model="form.is_active" />
              Active
            </label>
          </div>

          <div class="modal-actions">
            <button type="button" class="btn btn-secondary" @click="showModal = false">Cancel</button>
            <button type="submit" class="btn btn-primary" :disabled="saving">
              {{ saving ? 'Saving…' : (editingUser ? 'Update' : 'Create') }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>
