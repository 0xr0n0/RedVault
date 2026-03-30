<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api/client'
import { useAuthStore } from '../stores/auth'
import type { Client, Asset } from '../types'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const client = ref<Client | null>(null)
const assets = ref<Asset[]>([])
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const success = ref('')
const editing = ref(false)
const form = ref<Partial<Client>>({})

const canEdit = computed(() => auth.isAdmin)
const canDelete = computed(() => auth.isAdmin)

async function fetchClient() {
  loading.value = true
  try {
    const { data } = await api.get<Client>(`/clients/${route.params.id}/`)
    client.value = data
    await fetchAssets()
  } catch {
    error.value = 'Failed to load client.'
  } finally {
    loading.value = false
  }
}

async function fetchAssets() {
  try {
    const { data } = await api.get('/assets/', { params: { client: route.params.id } })
    assets.value = data.results || data
  } catch {
    // Silently fail — assets are supplementary
  }
}

function startEdit() {
  if (!client.value) return
  form.value = { ...client.value }
  editing.value = true
  error.value = ''
  success.value = ''
}

function cancelEdit() {
  editing.value = false
  form.value = {}
}

async function handleSave() {
  saving.value = true
  error.value = ''
  success.value = ''
  try {
    const payload = {
      name: form.value.name,
      description: form.value.description,
    }
    const { data } = await api.patch<Client>(`/clients/${route.params.id}/`, payload)
    client.value = data
    editing.value = false
    success.value = 'Client updated successfully.'
    setTimeout(() => (success.value = ''), 3000)
  } catch (e: any) {
    const data = e.response?.data
    if (data && typeof data === 'object') {
      error.value = Object.entries(data)
        .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
        .join(' | ')
    } else {
      error.value = 'Failed to update client.'
    }
  } finally {
    saving.value = false
  }
}

async function handleDelete() {
  if (!confirm('Are you sure you want to delete this client? Associated assets will lose their client link.')) return
  try {
    await api.delete(`/clients/${route.params.id}/`)
    router.push('/clients')
  } catch {
    error.value = 'Failed to delete client.'
  }
}

function goToAsset(id: string) {
  router.push(`/assets/${id}`)
}

const assetTypeLabels: Record<string, string> = {
  host: 'Host',
  web_app: 'Web Application',
  api: 'API',
  network: 'Network',
  cloud: 'Cloud Resource',
  mobile: 'Mobile App',
  database: 'Database',
  other: 'Other',
}

function assetTypeLabel(type: string): string {
  return assetTypeLabels[type] ?? type
}

onMounted(fetchClient)
</script>

<template>
  <div v-if="loading" class="text-muted text-center mt-3">Loading client…</div>
  <div v-else-if="!client" class="text-center mt-3">
    <p class="text-muted">Client not found.</p>
    <router-link to="/clients" class="btn btn-secondary mt-2">← Back to Clients</router-link>
  </div>
  <div v-else>
    <!-- Header -->
    <div class="flex-between mb-2">
      <div>
        <router-link to="/clients" class="text-muted" style="font-size: 0.85rem; text-decoration: none">← Clients</router-link>
        <h1 style="margin-top: 0.5rem">{{ client.name }}</h1>
      </div>
      <div class="flex gap-1">
        <button v-if="canEdit && !editing" class="btn btn-primary" @click="startEdit">Edit</button>
        <button v-if="canDelete" class="btn btn-danger" @click="handleDelete">Delete</button>
      </div>
    </div>

    <div v-if="error" class="alert alert-error mb-2">{{ error }}</div>
    <div v-if="success" class="alert alert-success mb-2">{{ success }}</div>

    <!-- View Mode -->
    <template v-if="!editing">
      <div class="card mb-2">
        <div class="detail-grid">
          <div class="detail-item">
            <span class="detail-label">Name</span>
            <span>{{ client.name }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Assets</span>
            <span>{{ client.asset_count ?? assets.length }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Created</span>
            <span>{{ new Date(client.created_at).toLocaleDateString() }} by {{ client.created_by_username || 'Unknown' }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Last Updated</span>
            <span>{{ new Date(client.updated_at).toLocaleDateString() }}</span>
          </div>
        </div>
      </div>

      <!-- Description -->
      <div v-if="client.description" class="card mb-2">
        <h3 class="mb-1">Description</h3>
        <p style="white-space: pre-wrap; font-size: 0.9rem; color: var(--color-text-muted)">{{ client.description }}</p>
      </div>

      <!-- Associated Assets -->
      <div class="card mb-2">
        <h3 class="mb-1">Associated Assets ({{ assets.length }})</h3>
        <div v-if="assets.length === 0" class="text-muted" style="font-size: 0.85rem">No assets linked to this client.</div>
        <table v-else>
          <thead>
            <tr>
              <th>Name</th>
              <th>Type</th>
              <th>IP Address</th>
              <th>Findings</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="a in assets"
              :key="a.id"
              style="cursor: pointer"
              @click="goToAsset(a.id)"
            >
              <td style="max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">{{ a.name }}</td>
              <td><span class="badge badge-asset-type">{{ assetTypeLabel(a.asset_type) }}</span></td>
              <td class="text-muted">{{ a.ip_address || '—' }}</td>
              <td class="text-muted">{{ a.finding_count ?? 0 }}</td>
              <td class="text-muted">{{ new Date(a.created_at).toLocaleDateString() }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <!-- Edit Mode -->
    <template v-if="editing">
      <div class="card mb-2">
        <form @submit.prevent="handleSave">
          <div class="form-group">
            <label>Name</label>
            <input v-model="form.name" class="form-input" required />
          </div>

          <div class="form-group">
            <label>Description</label>
            <textarea v-model="form.description" class="form-textarea" rows="4"></textarea>
          </div>

          <div class="modal-actions">
            <button type="button" class="btn btn-secondary" @click="cancelEdit">Cancel</button>
            <button type="submit" class="btn btn-primary" :disabled="saving">
              {{ saving ? 'Saving…' : 'Save Changes' }}
            </button>
          </div>
        </form>
      </div>
    </template>
  </div>
</template>

<style scoped>
.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 1.25rem;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.detail-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--color-text-muted);
  letter-spacing: 0.5px;
}

.badge-asset-type {
  background-color: var(--color-primary);
  color: white;
  padding: 0.15rem 0.5rem;
  border-radius: var(--radius);
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  width: fit-content;
}

</style>
