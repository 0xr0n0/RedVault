<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import api, { downloadMedia } from '../api/client'
import { useAuthStore } from '../stores/auth'
import type { Finding, FindingCreate, Severity, FindingStatus, Asset, GeneratedReport } from '../types'

const router = useRouter()
const auth = useAuthStore()

const findings = ref<Finding[]>([])
const assets = ref<Asset[]>([])
const loading = ref(true)
const error = ref('')
const totalCount = ref(0)
const currentPage = ref(1)

// Filters
const filterSeverity = ref('')
const filterStatus = ref('')
const searchQuery = ref('')

// Modal
const showModal = ref(false)
const saving = ref(false)
const formError = ref('')
const form = ref<FindingCreate>({
  title: '',
  description: '',
  recommendations: '',
  severity: 'medium',
  cvss_score: null,
  cvss_vector: '',
  asset: null,
  affected_assets: '',
  references: '',
  status: 'open',
  assigned_to: null,
})

const severityOptions: { value: Severity; label: string }[] = [
  { value: 'critical', label: 'Critical' },
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' },
  { value: 'informational', label: 'Informational' },
]

const statusOptions: { value: FindingStatus; label: string }[] = [
  { value: 'open', label: 'Open' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'remediated', label: 'Remediated' },
  { value: 'closed', label: 'Closed' },
  { value: 'accepted', label: 'Risk Accepted' },
]

const canCreate = computed(() => auth.isAnalyst)

// Report generation
const selectedFindings = ref<Set<string>>(new Set())
const showReportModal = ref(false)
const generating = ref(false)
const generatedReport = ref<GeneratedReport | null>(null)
const reportError = ref('')
const reportClientName = ref('')
const reportAssetName = ref('')
const reportDateFrom = ref('')
const reportDateTo = ref('')
const clients = ref<{id: string, name: string}[]>([])

const allSelected = computed(() =>
  findings.value.length > 0 && findings.value.every(f => selectedFindings.value.has(f.id))
)
const someSelected = computed(() => selectedFindings.value.size > 0)

function toggleFinding(id: string) {
  const next = new Set(selectedFindings.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selectedFindings.value = next
}

function toggleAll() {
  if (allSelected.value) {
    selectedFindings.value = new Set()
  } else {
    selectedFindings.value = new Set(findings.value.map(f => f.id))
  }
}

function openReportModal() {
  generatedReport.value = null
  reportError.value = ''
  // Auto-detect client and asset from selected findings
  const selectedList = findings.value.filter(f => selectedFindings.value.has(f.id))
  const assetNames = new Set(selectedList.map(f => f.asset_name).filter(Boolean))
  reportAssetName.value = [...assetNames].join(', ') || ''
  // Try to detect client from assets
  const clientNames = new Set<string>()
  for (const a of assets.value) {
    if (selectedList.some(f => f.asset === a.id) && a.client_name) {
      clientNames.add(a.client_name)
    }
  }
  reportClientName.value = [...clientNames].join(', ') || ''
  // Default dates
  const today = new Date().toISOString().split('T')[0]
  reportDateFrom.value = reportDateFrom.value || today
  reportDateTo.value = reportDateTo.value || today
  showReportModal.value = true
}

async function generateReport() {
  generating.value = true
  reportError.value = ''
  generatedReport.value = null
  try {
    const payload: Record<string, any> = {
      finding_ids: Array.from(selectedFindings.value),
    }
    if (reportClientName.value) payload.client_name = reportClientName.value
    if (reportAssetName.value) payload.asset_name = reportAssetName.value
    if (reportDateFrom.value) payload.date_from = reportDateFrom.value
    if (reportDateTo.value) payload.date_to = reportDateTo.value
    const { data } = await api.post('/reports/generate/', payload)
    generatedReport.value = data
  } catch (e: any) {
    const d = e.response?.data
    reportError.value = d?.detail || 'Failed to generate report.'
  } finally {
    generating.value = false
  }
}

function downloadGeneratedReport() {
  if (generatedReport.value?.file) {
    downloadMedia(generatedReport.value.file, generatedReport.value.name + '.pdf')
  }
}

async function fetchFindings() {
  loading.value = true
  try {
    const params: Record<string, string> = { page: String(currentPage.value) }
    if (filterSeverity.value) params.severity = filterSeverity.value
    if (filterStatus.value) params.status = filterStatus.value
    if (searchQuery.value) params.search = searchQuery.value

    const [findingsRes, assetsRes, clientsRes] = await Promise.all([
      api.get('/findings/', { params }),
      assets.value.length === 0 ? api.get('/assets/') : Promise.resolve(null),
      clients.value.length === 0 ? api.get('/clients/') : Promise.resolve(null),
    ])
    findings.value = findingsRes.data.results || findingsRes.data
    totalCount.value = findingsRes.data.count || findings.value.length
    if (assetsRes) assets.value = assetsRes.data.results || assetsRes.data
    if (clientsRes) clients.value = clientsRes.data.results || clientsRes.data
  } catch {
    error.value = 'Failed to load findings.'
  } finally {
    loading.value = false
  }
}

function openCreate() {
  form.value = {
    title: '',
    description: 'Describe the vulnerability here.',
    impact: 'Describe the impact of this vulnerability.',
    recommendations: '1. Step one\n2. Step two',
    severity: 'medium',
    cvss_score: null,
    cvss_vector: '',
    asset: null,
    affected_assets: '',
    references: '',
    status: 'open',
    assigned_to: null,
  }
  formError.value = ''
  showModal.value = true
}

async function handleCreate() {
  formError.value = ''
  saving.value = true
  try {
    const payload = { ...form.value }
    if (payload.cvss_score === null || payload.cvss_score === undefined) {
      delete payload.cvss_score
    }
    await api.post('/findings/', payload)
    showModal.value = false
    await fetchFindings()
  } catch (e: any) {
    const data = e.response?.data
    if (data && typeof data === 'object') {
      formError.value = Object.entries(data)
        .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
        .join(' | ')
    } else {
      formError.value = 'Failed to create finding.'
    }
  } finally {
    saving.value = false
  }
}

function goToDetail(id: string) {
  router.push(`/findings/${id}`)
}

async function deleteFinding(id: string) {
  if (!confirm('Delete this finding? This cannot be undone.')) return
  try {
    await api.delete(`/findings/${id}/`)
    selectedFindings.value = new Set([...selectedFindings.value].filter(fid => fid !== id))
    await fetchFindings()
  } catch {
    error.value = 'Failed to delete finding.'
  }
}

async function deleteSelected() {
  const count = selectedFindings.value.size
  if (!confirm(`Delete ${count} selected finding${count !== 1 ? 's' : ''}? This cannot be undone.`)) return
  try {
    const ids = Array.from(selectedFindings.value)
    await Promise.all(ids.map(id => api.delete(`/findings/${id}/`)))
    selectedFindings.value = new Set()
    await fetchFindings()
  } catch {
    error.value = 'Failed to delete some findings.'
  }
}

function handleFilter() {
  currentPage.value = 1
  fetchFindings()
}

onMounted(fetchFindings)
</script>

<template>
  <div>
    <div class="flex-between mb-2">
      <h1>Findings</h1>
      <div class="flex gap-1">
        <button
          v-if="canCreate && someSelected"
          class="btn btn-danger"
          @click="deleteSelected"
        >
          🗑 Delete ({{ selectedFindings.size }})
        </button>
        <button
          v-if="canCreate && someSelected"
          class="btn btn-report"
          @click="openReportModal"
        >
          📄 Generate Report ({{ selectedFindings.size }})
        </button>
        <button v-if="canCreate" class="btn btn-primary" @click="openCreate">+ New Finding</button>
      </div>
    </div>

    <!-- Filters -->
    <div class="card mb-2" style="padding: 1rem">
      <div class="flex gap-1 flex-wrap items-center">
        <input
          v-model="searchQuery"
          class="form-input"
          placeholder="Search findings…"
          style="width: 250px"
          @keyup.enter="handleFilter"
        />
        <select v-model="filterSeverity" class="form-select" style="width: 150px" @change="handleFilter">
          <option value="">All Severities</option>
          <option v-for="s in severityOptions" :key="s.value" :value="s.value">{{ s.label }}</option>
        </select>
        <select v-model="filterStatus" class="form-select" style="width: 150px" @change="handleFilter">
          <option value="">All Statuses</option>
          <option v-for="s in statusOptions" :key="s.value" :value="s.value">{{ s.label }}</option>
        </select>
        <button class="btn btn-secondary btn-sm" @click="handleFilter">Search</button>
      </div>
    </div>

    <div v-if="error" class="alert alert-error">{{ error }}</div>
    <div v-if="loading" class="text-muted text-center mt-3">Loading findings…</div>

    <div v-else class="card table-container">
      <table>
        <thead>
          <tr>
            <th v-if="canCreate" style="width: 40px">
              <input type="checkbox" :checked="allSelected" @change="toggleAll" title="Select all" />
            </th>
            <th>Title</th>
            <th>Severity</th>
            <th>CVSS</th>
            <th>Status</th>
            <th>Asset</th>
            <th>Assigned To</th>
            <th>Evidence</th>
            <th>Created</th>
            <th v-if="canCreate" style="width: 70px">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="finding in findings"
            :key="finding.id"
            style="cursor: pointer"
            @click="goToDetail(finding.id)"
          >
            <td v-if="canCreate" @click.stop>
              <input
                type="checkbox"
                :checked="selectedFindings.has(finding.id)"
                @change="toggleFinding(finding.id)"
              />
            </td>
            <td style="max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">
              {{ finding.title }}
            </td>
            <td><span class="badge" :class="`badge-${finding.severity}`">{{ finding.severity }}</span></td>
            <td>{{ finding.cvss_score ?? '—' }}</td>
            <td><span class="badge" :class="`badge-${finding.status}`">{{ finding.status.replace('_', ' ') }}</span></td>
            <td class="text-muted">{{ finding.asset_name || '—' }}</td>
            <td class="text-muted">{{ finding.assigned_to_username || '—' }}</td>
            <td class="text-muted">{{ finding.evidence_count ?? 0 }}</td>
            <td class="text-muted">{{ new Date(finding.created_at).toLocaleDateString() }}</td>
            <td v-if="canCreate" @click.stop>
              <button class="btn btn-danger btn-sm" @click="deleteFinding(finding.id)">🗑</button>
            </td>
          </tr>
          <tr v-if="findings.length === 0">
            <td :colspan="canCreate ? 10 : 8" class="text-center text-muted">No findings yet. Create your first one!</td>
          </tr>
        </tbody>
      </table>

      <div v-if="totalCount > 25" class="flex-between mt-2" style="padding: 0 1rem 1rem">
        <button class="btn btn-secondary btn-sm" :disabled="currentPage === 1" @click="currentPage--; fetchFindings()">
          ← Previous
        </button>
        <span class="text-muted">Page {{ currentPage }}</span>
        <button class="btn btn-secondary btn-sm" :disabled="findings.length < 25" @click="currentPage++; fetchFindings()">
          Next →
        </button>
      </div>
    </div>

    <!-- Create Finding Modal -->
    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal" style="max-width: 900px">
        <h2>Create Finding</h2>

        <div v-if="formError" class="alert alert-error">{{ formError }}</div>

        <form @submit.prevent="handleCreate">
          <div class="form-group">
            <label>Title</label>
            <input v-model="form.title" class="form-input" placeholder="e.g. SQL Injection in Login Endpoint" required />
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem">
            <div class="form-group">
              <label>Severity</label>
              <select v-model="form.severity" class="form-select" required>
                <option v-for="s in severityOptions" :key="s.value" :value="s.value">{{ s.label }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>CVSS Score</label>
              <input v-model.number="form.cvss_score" type="number" class="form-input" step="0.1" min="0" max="10" />
            </div>
            <div class="form-group">
              <label>Status</label>
              <select v-model="form.status" class="form-select">
                <option v-for="s in statusOptions" :key="s.value" :value="s.value">{{ s.label }}</option>
              </select>
            </div>
          </div>

          <div class="form-group">
            <label>CVSS Vector</label>
            <input v-model="form.cvss_vector" class="form-input" placeholder="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H" />
          </div>

          <div class="form-group">
            <label>Asset</label>
            <select v-model="form.asset" class="form-select">
              <option :value="null">— No asset —</option>
              <option v-for="a in assets" :key="a.id" :value="a.id">{{ a.name }} ({{ a.asset_type }})</option>
            </select>
          </div>

          <div class="form-group">
            <label>Description (Markdown)</label>
            <textarea v-model="form.description" class="form-textarea" rows="8" required></textarea>
          </div>

          <div class="form-group">
            <label>Impact (Markdown)</label>
            <textarea v-model="form.impact" class="form-textarea" rows="5"></textarea>
          </div>

          <div class="form-group">
            <label>Recommendations (Markdown)</label>
            <textarea v-model="form.recommendations" class="form-textarea" rows="5"></textarea>
          </div>

          <div class="form-group">
            <label>Affected Assets (one per line)</label>
            <textarea v-model="form.affected_assets" class="form-textarea" rows="3" placeholder="192.168.1.1&#10;https://app.example.com/login"></textarea>
          </div>

          <div class="form-group">
            <label>References / CVE IDs (one per line)</label>
            <textarea v-model="form.references" class="form-textarea" rows="3" placeholder="CVE-2024-1234&#10;https://nvd.nist.gov/..."></textarea>
          </div>

          <div class="modal-actions">
            <button type="button" class="btn btn-secondary" @click="showModal = false">Cancel</button>
            <button type="submit" class="btn btn-primary" :disabled="saving">
              {{ saving ? 'Creating…' : 'Create Finding' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Generate Report Modal -->
    <div v-if="showReportModal" class="modal-overlay" @click.self="showReportModal = false">
      <div class="modal" style="max-width: 600px">
        <h2>Generate PDF Report</h2>

        <div v-if="reportError" class="alert alert-error">{{ reportError }}</div>

        <div v-if="!generatedReport">
          <p class="text-muted mb-2">
            {{ selectedFindings.size }} finding{{ selectedFindings.size !== 1 ? 's' : '' }} selected.
            Findings will be sorted from most critical to least critical in the report.
          </p>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem">
            <div class="form-group">
              <label>Client Name</label>
              <input v-model="reportClientName" class="form-input" placeholder="Auto-detected from findings" />
            </div>
            <div class="form-group">
              <label>Asset / Target Name</label>
              <input v-model="reportAssetName" class="form-input" placeholder="Auto-detected from findings" />
            </div>
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem">
            <div class="form-group">
              <label>Assessment Start Date</label>
              <input v-model="reportDateFrom" type="date" class="form-input" />
            </div>
            <div class="form-group">
              <label>Assessment End Date</label>
              <input v-model="reportDateTo" type="date" class="form-input" />
            </div>
          </div>

          <div class="modal-actions">
            <button type="button" class="btn btn-secondary" @click="showReportModal = false">Cancel</button>
            <button
              class="btn btn-primary"
              :disabled="generating"
              @click="generateReport"
            >
              {{ generating ? 'Generating PDF…' : 'Generate PDF Report' }}
            </button>
          </div>
        </div>

        <div v-else class="report-success">
          <div class="success-icon">✅</div>
          <h3>PDF Report Generated!</h3>
          <p class="text-muted">{{ generatedReport.name }}</p>
          <p class="text-muted">{{ generatedReport.finding_count }} findings included</p>

          <div class="modal-actions" style="margin-top: 1.5rem">
            <button class="btn btn-secondary" @click="showReportModal = false">Close</button>
            <button class="btn btn-primary" @click="downloadGeneratedReport">⬇ Download PDF</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.btn-report {
  background-color: #059669;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: var(--radius);
  cursor: pointer;
  font-weight: 500;
  font-size: 0.875rem;
  transition: background-color 0.2s;
}

.btn-report:hover {
  background-color: #047857;
}

.report-success {
  text-align: center;
  padding: 1rem 0;
}

.success-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}
</style>
