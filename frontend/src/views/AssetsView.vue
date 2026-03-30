<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api/client'
import { useAuthStore } from '../stores/auth'
import type { Asset, AssetCreate, AssetType, Client } from '../types'

const router = useRouter()
const auth = useAuthStore()

const assets = ref<Asset[]>([])
const clients = ref<Client[]>([])
const loading = ref(true)
const error = ref('')
const totalCount = ref(0)
const currentPage = ref(1)

// Filters
const filterType = ref('')
const searchQuery = ref('')

// Modal
const showModal = ref(false)
const saving = ref(false)
const formError = ref('')
const form = ref<AssetCreate>({
  name: '',
  asset_type: 'host',
  ip_address: null,
  hostname: '',
  url: '',
  os: '',
  description: '',
  client: null,
})

const assetTypeOptions: { value: AssetType; label: string }[] = [
  { value: 'host', label: 'Host' },
  { value: 'web_app', label: 'Web Application' },
  { value: 'api', label: 'API' },
  { value: 'network', label: 'Network' },
  { value: 'cloud', label: 'Cloud Resource' },
  { value: 'mobile', label: 'Mobile App' },
  { value: 'database', label: 'Database' },
  { value: 'other', label: 'Other' },
]

const canCreate = computed(() => auth.isAnalyst)

async function fetchAssets() {
  loading.value = true
  try {
    const params: Record<string, string> = { page: String(currentPage.value) }
    if (filterType.value) params.asset_type = filterType.value
    if (searchQuery.value) params.search = searchQuery.value

    const { data } = await api.get('/assets/', { params })
    assets.value = data.results || data
    totalCount.value = data.count || assets.value.length
  } catch {
    error.value = 'Failed to load assets.'
  } finally {
    loading.value = false
  }
}

async function fetchClients() {
  try {
    const { data } = await api.get('/clients/')
    clients.value = data.results || data
  } catch {
    // Silently fail
  }
}

function openCreate() {
  form.value = {
    name: '',
    asset_type: 'host',
    ip_address: null,
    hostname: '',
    url: '',
    os: '',
    description: '',
    client: null,
  }
  formError.value = ''
  showModal.value = true
}

async function handleCreate() {
  formError.value = ''
  saving.value = true
  try {
    const payload: Record<string, any> = { ...form.value }
    // Clean empty optional fields
    if (!payload.ip_address) delete payload.ip_address
    if (!payload.url) delete payload.url
    await api.post('/assets/', payload)
    showModal.value = false
    await fetchAssets()
  } catch (e: any) {
    const data = e.response?.data
    if (data && typeof data === 'object') {
      formError.value = Object.entries(data)
        .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
        .join(' | ')
    } else {
      formError.value = 'Failed to create asset.'
    }
  } finally {
    saving.value = false
  }
}

function goToDetail(id: string) {
  router.push(`/assets/${id}`)
}

function handleFilter() {
  currentPage.value = 1
  fetchAssets()
}

function assetTypeLabel(type: string): string {
  return assetTypeOptions.find(o => o.value === type)?.label ?? type
}

onMounted(() => {
  fetchAssets()
  fetchClients()
})
</script>

<template>
  <div>
    <div class="flex-between mb-2">
      <h1>Assets</h1>
      <button v-if="canCreate" class="btn btn-primary" @click="openCreate">+ New Asset</button>
    </div>

    <!-- Filters -->
    <div class="card mb-2" style="padding: 1rem">
      <div class="flex gap-1 flex-wrap items-center">
        <input
          v-model="searchQuery"
          class="form-input"
          placeholder="Search assets…"
          style="width: 250px"
          @keyup.enter="handleFilter"
        />
        <select v-model="filterType" class="form-select" style="width: 180px" @change="handleFilter">
          <option value="">All Types</option>
          <option v-for="t in assetTypeOptions" :key="t.value" :value="t.value">{{ t.label }}</option>
        </select>
        <button class="btn btn-secondary btn-sm" @click="handleFilter">Search</button>
      </div>
    </div>

    <div v-if="error" class="alert alert-error">{{ error }}</div>
    <div v-if="loading" class="text-muted text-center mt-3">Loading assets…</div>

    <div v-else class="card table-container">
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Client</th>
            <th>IP Address</th>
            <th>Hostname</th>
            <th>OS</th>
            <th>Findings</th>
            <th>Created</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="asset in assets"
            :key="asset.id"
            style="cursor: pointer"
            @click="goToDetail(asset.id)"
          >
            <td style="max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 500">
              {{ asset.name }}
            </td>
            <td><span class="badge badge-asset-type">{{ assetTypeLabel(asset.asset_type) }}</span></td>
            <td class="text-muted">{{ asset.client_name || '—' }}</td>
            <td class="text-muted">{{ asset.ip_address || '—' }}</td>
            <td class="text-muted">{{ asset.hostname || '—' }}</td>
            <td class="text-muted">{{ asset.os || '—' }}</td>
            <td class="text-muted">{{ asset.finding_count ?? 0 }}</td>
            <td class="text-muted">{{ new Date(asset.created_at).toLocaleDateString() }}</td>
          </tr>
          <tr v-if="assets.length === 0">
            <td colspan="8" class="text-center text-muted">No assets yet. Create your first one!</td>
          </tr>
        </tbody>
      </table>

      <div v-if="totalCount > 25" class="flex-between mt-2" style="padding: 0 1rem 1rem">
        <button class="btn btn-secondary btn-sm" :disabled="currentPage === 1" @click="currentPage--; fetchAssets()">
          ← Previous
        </button>
        <span class="text-muted">Page {{ currentPage }}</span>
        <button class="btn btn-secondary btn-sm" :disabled="assets.length < 25" @click="currentPage++; fetchAssets()">
          Next →
        </button>
      </div>
    </div>

    <!-- Create Asset Modal -->
    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal" style="max-width: 700px">
        <h2>Create Asset</h2>

        <div v-if="formError" class="alert alert-error">{{ formError }}</div>

        <form @submit.prevent="handleCreate">
          <div class="form-group">
            <label>Name</label>
            <input v-model="form.name" class="form-input" placeholder="e.g. web-server-01.example.com" required />
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem">
            <div class="form-group">
              <label>Asset Type</label>
              <select v-model="form.asset_type" class="form-select" required>
                <option v-for="t in assetTypeOptions" :key="t.value" :value="t.value">{{ t.label }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>IP Address</label>
              <input v-model="form.ip_address" class="form-input" placeholder="192.168.1.100" />
            </div>
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem">
            <div class="form-group">
              <label>Hostname</label>
              <input v-model="form.hostname" class="form-input" placeholder="web-server-01" />
            </div>
            <div class="form-group">
              <label>OS / Platform</label>
              <input v-model="form.os" class="form-input" placeholder="Ubuntu 22.04 LTS" />
            </div>
          </div>

          <div class="form-group">
            <label>URL</label>
            <input v-model="form.url" class="form-input" placeholder="https://app.example.com" />
          </div>

          <div class="form-group">
            <label>Description</label>
            <textarea v-model="form.description" class="form-textarea" rows="3" placeholder="Additional notes about this asset…"></textarea>
          </div>

          <div class="form-group">
            <label>Client</label>
            <select v-model="form.client" class="form-select">
              <option :value="null">— No Client —</option>
              <option v-for="c in clients" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
          </div>

          <div class="modal-actions">
            <button type="button" class="btn btn-secondary" @click="showModal = false">Cancel</button>
            <button type="submit" class="btn btn-primary" :disabled="saving">
              {{ saving ? 'Creating…' : 'Create Asset' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<style scoped>
.badge-asset-type {
  background-color: var(--color-primary);
  color: white;
  padding: 0.15rem 0.5rem;
  border-radius: var(--radius);
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
}
</style>
