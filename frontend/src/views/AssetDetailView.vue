<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api/client'
import { useAuthStore } from '../stores/auth'
import type { Asset, AssetType, Finding, Client } from '../types'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const asset = ref<Asset | null>(null)
const findings = ref<Finding[]>([])  
const clients = ref<Client[]>([])
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const success = ref('')
const editing = ref(false)
const form = ref<Partial<Asset>>({})

const canEdit = computed(() => auth.isAnalyst)
const canDelete = computed(() => auth.isAdmin)

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

function assetTypeLabel(type: string): string {
  return assetTypeOptions.find(o => o.value === type)?.label ?? type
}

async function fetchAsset() {
  loading.value = true
  try {
    const { data } = await api.get<Asset>(`/assets/${route.params.id}/`)
    asset.value = data
    await Promise.all([fetchFindings(), fetchClients()])
  } catch {
    error.value = 'Failed to load asset.'
  } finally {
    loading.value = false
  }
}

async function fetchFindings() {
  try {
    const { data } = await api.get('/findings/', { params: { asset: route.params.id } })
    findings.value = data.results || data
  } catch {
    // Silently fail — findings are supplementary
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

function startEdit() {
  if (!asset.value) return
  form.value = { ...asset.value }
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
    const payload: Record<string, any> = {
      name: form.value.name,
      asset_type: form.value.asset_type,
      ip_address: form.value.ip_address || null,
      hostname: form.value.hostname,
      url: form.value.url,
      os: form.value.os,
      description: form.value.description,
      client: form.value.client || null,
    }
    const { data } = await api.patch<Asset>(`/assets/${route.params.id}/`, payload)
    asset.value = data
    editing.value = false
    success.value = 'Asset updated successfully.'
    setTimeout(() => (success.value = ''), 3000)
  } catch (e: any) {
    const data = e.response?.data
    if (data && typeof data === 'object') {
      error.value = Object.entries(data)
        .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
        .join(' | ')
    } else {
      error.value = 'Failed to update asset.'
    }
  } finally {
    saving.value = false
  }
}

async function handleDelete() {
  if (!confirm('Are you sure you want to delete this asset? Associated findings will NOT be deleted but will lose their asset link.')) return
  try {
    await api.delete(`/assets/${route.params.id}/`)
    router.push('/assets')
  } catch {
    error.value = 'Failed to delete asset.'
  }
}

function goToFinding(id: string) {
  router.push(`/findings/${id}`)
}

onMounted(fetchAsset)
</script>

<template>
  <div v-if="loading" class="text-muted text-center mt-3">Loading asset…</div>
  <div v-else-if="!asset" class="text-center mt-3">
    <p class="text-muted">Asset not found.</p>
    <router-link to="/assets" class="btn btn-secondary mt-2">← Back to Assets</router-link>
  </div>
  <div v-else>
    <!-- Header -->
    <div class="flex-between mb-2">
      <div>
        <router-link to="/assets" class="text-muted" style="font-size: 0.85rem; text-decoration: none">← Assets</router-link>
        <h1 style="margin-top: 0.5rem">{{ asset.name }}</h1>
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
            <span class="detail-label">Type</span>
            <span class="badge badge-asset-type">{{ assetTypeLabel(asset.asset_type) }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">IP Address</span>
            <span>{{ asset.ip_address || '—' }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Hostname</span>
            <span>{{ asset.hostname || '—' }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">URL</span>
            <span v-if="asset.url"><a :href="asset.url" target="_blank" rel="noopener">{{ asset.url }}</a></span>
            <span v-else>—</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">OS / Platform</span>
            <span>{{ asset.os || '—' }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Client</span>
            <span v-if="asset.client_name">
              <router-link :to="`/clients/${asset.client}`">{{ asset.client_name }}</router-link>
            </span>
            <span v-else>—</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Findings</span>
            <span>{{ asset.finding_count ?? findings.length }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Created</span>
            <span>{{ new Date(asset.created_at).toLocaleDateString() }} by {{ asset.created_by_username || 'Unknown' }}</span>
          </div>
        </div>
      </div>

      <!-- Description -->
      <div v-if="asset.description" class="card mb-2">
        <h3 class="mb-1">Description</h3>
        <p style="white-space: pre-wrap; font-size: 0.9rem; color: var(--color-text-muted)">{{ asset.description }}</p>
      </div>

      <!-- Associated Findings -->
      <div class="card mb-2">
        <h3 class="mb-1">Associated Findings ({{ findings.length }})</h3>
        <div v-if="findings.length === 0" class="text-muted" style="font-size: 0.85rem">No findings linked to this asset.</div>
        <table v-else>
          <thead>
            <tr>
              <th>Title</th>
              <th>Severity</th>
              <th>Status</th>
              <th>CVSS</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="f in findings"
              :key="f.id"
              style="cursor: pointer"
              @click="goToFinding(f.id)"
            >
              <td style="max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">{{ f.title }}</td>
              <td><span class="badge" :class="`badge-${f.severity}`">{{ f.severity }}</span></td>
              <td><span class="badge" :class="`badge-${f.status}`">{{ f.status.replace('_', ' ') }}</span></td>
              <td class="text-muted">{{ f.cvss_score ?? '—' }}</td>
              <td class="text-muted">{{ new Date(f.created_at).toLocaleDateString() }}</td>
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

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem">
            <div class="form-group">
              <label>Asset Type</label>
              <select v-model="form.asset_type" class="form-select" required>
                <option v-for="t in assetTypeOptions" :key="t.value" :value="t.value">{{ t.label }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>IP Address</label>
              <input v-model="form.ip_address" class="form-input" />
            </div>
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem">
            <div class="form-group">
              <label>Hostname</label>
              <input v-model="form.hostname" class="form-input" />
            </div>
            <div class="form-group">
              <label>OS / Platform</label>
              <input v-model="form.os" class="form-input" />
            </div>
          </div>

          <div class="form-group">
            <label>URL</label>
            <input v-model="form.url" class="form-input" />
          </div>

          <div class="form-group">
            <label>Client</label>
            <select v-model="form.client" class="form-select">
              <option :value="null">— No Client —</option>
              <option v-for="c in clients" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
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
