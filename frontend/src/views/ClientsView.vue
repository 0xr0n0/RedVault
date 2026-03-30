<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api/client'
import { useAuthStore } from '../stores/auth'
import type { Client, ClientCreate } from '../types'

const router = useRouter()
const auth = useAuthStore()

const clients = ref<Client[]>([])
const loading = ref(true)
const error = ref('')
const totalCount = ref(0)
const currentPage = ref(1)

// Filters
const searchQuery = ref('')

// Modal
const showModal = ref(false)
const saving = ref(false)
const formError = ref('')
const form = ref<ClientCreate>({
  name: '',
  description: '',
})

const canCreate = computed(() => auth.isAdmin)

async function fetchClients() {
  loading.value = true
  try {
    const params: Record<string, string> = { page: String(currentPage.value) }
    if (searchQuery.value) params.search = searchQuery.value

    const { data } = await api.get('/clients/', { params })
    clients.value = data.results || data
    totalCount.value = data.count || clients.value.length
  } catch {
    error.value = 'Failed to load clients.'
  } finally {
    loading.value = false
  }
}

function openCreate() {
  form.value = {
    name: '',
    description: '',
  }
  formError.value = ''
  showModal.value = true
}

async function handleCreate() {
  formError.value = ''
  saving.value = true
  try {
    await api.post('/clients/', form.value)
    showModal.value = false
    await fetchClients()
  } catch (e: any) {
    const data = e.response?.data
    if (data && typeof data === 'object') {
      formError.value = Object.entries(data)
        .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
        .join(' | ')
    } else {
      formError.value = 'Failed to create client.'
    }
  } finally {
    saving.value = false
  }
}

function goToDetail(id: string) {
  router.push(`/clients/${id}`)
}

function handleFilter() {
  currentPage.value = 1
  fetchClients()
}

onMounted(fetchClients)
</script>

<template>
  <div>
    <div class="flex-between mb-2">
      <h1>Clients</h1>
      <button v-if="canCreate" class="btn btn-primary" @click="openCreate">+ New Client</button>
    </div>

    <!-- Filters -->
    <div class="card mb-2" style="padding: 1rem">
      <div class="flex gap-1 flex-wrap items-center">
        <input
          v-model="searchQuery"
          class="form-input"
          placeholder="Search clients…"
          style="width: 300px"
          @keyup.enter="handleFilter"
        />
        <button class="btn btn-secondary btn-sm" @click="handleFilter">Search</button>
      </div>
    </div>

    <div v-if="error" class="alert alert-error">{{ error }}</div>
    <div v-if="loading" class="text-muted text-center mt-3">Loading clients…</div>

    <div v-else class="card table-container">
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Description</th>
            <th>Assets</th>
            <th>Created By</th>
            <th>Created</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="client in clients"
            :key="client.id"
            style="cursor: pointer"
            @click="goToDetail(client.id)"
          >
            <td style="max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 500">
              {{ client.name }}
            </td>
            <td class="text-muted" style="max-width: 350px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">
              {{ client.description || '—' }}
            </td>
            <td class="text-muted">{{ client.asset_count ?? 0 }}</td>
            <td class="text-muted">{{ client.created_by_username || '—' }}</td>
            <td class="text-muted">{{ new Date(client.created_at).toLocaleDateString() }}</td>
          </tr>
          <tr v-if="clients.length === 0">
            <td colspan="5" class="text-center text-muted">No clients yet. Create your first one!</td>
          </tr>
        </tbody>
      </table>

      <div v-if="totalCount > 25" class="flex-between mt-2" style="padding: 0 1rem 1rem">
        <button class="btn btn-secondary btn-sm" :disabled="currentPage === 1" @click="currentPage--; fetchClients()">
          ← Previous
        </button>
        <span class="text-muted">Page {{ currentPage }}</span>
        <button class="btn btn-secondary btn-sm" :disabled="clients.length < 25" @click="currentPage++; fetchClients()">
          Next →
        </button>
      </div>
    </div>

    <!-- Create Client Modal -->
    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal" style="max-width: 550px">
        <h2>Create Client</h2>

        <div v-if="formError" class="alert alert-error">{{ formError }}</div>

        <form @submit.prevent="handleCreate">
          <div class="form-group">
            <label>Name</label>
            <input v-model="form.name" class="form-input" placeholder="e.g. Acme Corporation" required />
          </div>

          <div class="form-group">
            <label>Description</label>
            <textarea v-model="form.description" class="form-textarea" rows="3" placeholder="Notes about this client…"></textarea>
          </div>

          <div class="modal-actions">
            <button type="button" class="btn btn-secondary" @click="showModal = false">Cancel</button>
            <button type="submit" class="btn btn-primary" :disabled="saving">
              {{ saving ? 'Creating…' : 'Create Client' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>
