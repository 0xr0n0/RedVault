<script setup lang="ts">
import { ref, onMounted, onUpdated, computed, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import api, { downloadMedia, backendBase } from '../api/client'
import { useAuthStore } from '../stores/auth'
import type { Finding, Evidence, Severity, FindingStatus, Asset, FindingHistoryEntry } from '../types'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

// Backend origin for media files

const finding = ref<Finding | null>(null)
const assets = ref<Asset[]>([])
const history = ref<FindingHistoryEntry[]>([])
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const success = ref('')
const editing = ref(false)
const copyFeedback = ref<string | null>(null)

// Evidence upload
const uploadingEvidence = ref(false)
const evidenceCaption = ref('')
const evidenceFileInput = ref<HTMLInputElement | null>(null)

// Edit form — textarea refs for cursor insertion
const form = ref<Partial<Finding>>({})
const descriptionTextarea = ref<HTMLTextAreaElement | null>(null)
const impactTextarea = ref<HTMLTextAreaElement | null>(null)
const recommendationsTextarea = ref<HTMLTextAreaElement | null>(null)

const canEdit = computed(() => auth.isAnalyst)
const canDelete = computed(() => auth.isAdmin)

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

// Configure DOMPurify to allow img tags (for evidence embedded in markdown)
// Only backend-origin URLs are allowed by the CSP img-src header
const DOMPURIFY_CONFIG = {
  ALLOWED_TAGS: [
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'br', 'hr',
    'ul', 'ol', 'li', 'blockquote', 'pre', 'code',
    'strong', 'em', 'del', 'a', 'img', 'table', 'thead',
    'tbody', 'tr', 'th', 'td', 'span', 'div', 'sub', 'sup',
  ],
  ALLOWED_ATTR: [
    'href', 'target', 'rel', 'class', 'id',
    'src', 'alt', 'title', 'width', 'height',  // img attributes
  ],
  ALLOW_DATA_ATTR: false,
  // Allow http(s), data, and relative URIs — blocks javascript: and other dangerous schemes
  ALLOWED_URI_REGEXP: /^(?:(?:https?|data):|\/?[\w])/i,
}

function renderMarkdown(md: string): string {
  const raw = marked(md || '', { async: false }) as string
  // Rewrite relative /media/ src to absolute backend URLs so images load directly
  const withAbsoluteMedia = raw.replace(
    /src="(\/media\/[^"]*)"/gi,
    `src="${backendBase}$1"`
  )
  return DOMPurify.sanitize(withAbsoluteMedia, DOMPURIFY_CONFIG)
}

/** Inject copy buttons on all <pre> blocks inside .markdown-preview */
function injectCopyButtons() {
  document.querySelectorAll('.markdown-preview pre').forEach((pre) => {
    if (pre.querySelector('.copy-code-btn')) return // already injected
    const btn = document.createElement('button')
    btn.className = 'copy-code-btn'
    btn.textContent = 'Copy'
    btn.addEventListener('click', async () => {
      const codeEl = pre.querySelector('code')
      const code = codeEl ? codeEl.textContent || '' : (pre as HTMLElement).textContent?.replace(btn.textContent || '', '').trim() || ''
      try {
        await navigator.clipboard.writeText(code)
        btn.textContent = 'Copied!'
        btn.classList.add('copied')
        setTimeout(() => {
          btn.textContent = 'Copy'
          btn.classList.remove('copied')
        }, 2000)
      } catch {
        btn.textContent = 'Failed'
        setTimeout(() => { btn.textContent = 'Copy' }, 2000)
      }
    })
    ;(pre as HTMLElement).style.position = 'relative'
    pre.appendChild(btn)
  })
}

onUpdated(() => nextTick(() => { injectCopyButtons() }))

/** Build markdown image syntax for an evidence item */
function evidenceMarkdown(ev: Evidence): string {
  const caption = ev.caption || ev.file.split('/').pop() || 'evidence'
  // Sanitize caption to prevent markdown injection
  const safeCaption = caption.replace(/[\[\]\(\)]/g, '')
  return `![${safeCaption}](${ev.file})`
}

/** Copy evidence markdown tag to clipboard */
async function copyEvidenceMarkdown(ev: Evidence) {
  try {
    await navigator.clipboard.writeText(evidenceMarkdown(ev))
    copyFeedback.value = ev.id
    setTimeout(() => (copyFeedback.value = null), 2000)
  } catch {
    error.value = 'Failed to copy to clipboard.'
  }
}

/** Insert evidence markdown at cursor position in a textarea and update the form field */
function insertEvidenceInto(field: 'description' | 'impact' | 'recommendations', ev: Evidence) {
  const textarea = field === 'description' ? descriptionTextarea.value : field === 'impact' ? impactTextarea.value : recommendationsTextarea.value
  const md = evidenceMarkdown(ev)

  if (!textarea) {
    // Fallback: append to end
    form.value[field] = (form.value[field] || '') + '\n' + md + '\n'
    return
  }

  const start = textarea.selectionStart
  const end = textarea.selectionEnd
  const current = form.value[field] || ''

  // Insert at cursor, wrapping with newlines for clean markdown
  const before = current.substring(0, start)
  const after = current.substring(end)
  const needNewlineBefore = before.length > 0 && !before.endsWith('\n') ? '\n' : ''
  const needNewlineAfter = after.length > 0 && !after.startsWith('\n') ? '\n' : ''

  form.value[field] = before + needNewlineBefore + md + needNewlineAfter + after

  // Restore focus and set cursor after inserted text
  nextTick(() => {
    textarea.focus()
    const newPos = start + needNewlineBefore.length + md.length
    textarea.setSelectionRange(newPos, newPos)
  })
}

async function fetchFinding() {
  loading.value = true
  try {
    const [findingRes, assetsRes] = await Promise.all([
      api.get<Finding>(`/findings/${route.params.id}/`),
      assets.value.length === 0 ? api.get('/assets/') : Promise.resolve(null),
    ])
    finding.value = findingRes.data
    if (assetsRes) assets.value = assetsRes.data.results || assetsRes.data
    await fetchHistory()
  } catch {
    error.value = 'Failed to load finding.'
  } finally {
    loading.value = false
  }
}

async function fetchHistory() {
  try {
    const { data } = await api.get(`/findings/${route.params.id}/history/`)
    history.value = data.results || data
  } catch {
    // Silently fail — history is supplementary
  }
}

const fieldLabels: Record<string, string> = {
  title: 'Title',
  description: 'Description',
  impact: 'Impact',
  recommendations: 'Recommendations',
  severity: 'Severity',
  cvss_score: 'CVSS Score',
  cvss_vector: 'CVSS Vector',
  asset: 'Asset',
  affected_assets: 'Affected Assets',
  references: 'References',
  status: 'Status',
  assigned_to: 'Assigned To',
}

function fieldLabel(field: string): string {
  return fieldLabels[field] || field
}

function isLongText(val: string | number | null | undefined): boolean {
  return typeof val === 'string' && val.length > 80
}

function formatVal(val: string | number | null | undefined): string {
  if (val === null || val === undefined || val === '' || val === 'None') return '—'
  return String(val)
}

function startEdit() {
  if (!finding.value) return
  form.value = { ...finding.value }
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
      title: form.value.title,
      description: form.value.description,
      impact: form.value.impact,
      recommendations: form.value.recommendations,
      severity: form.value.severity,
      cvss_score: form.value.cvss_score,
      cvss_vector: form.value.cvss_vector,
      asset: form.value.asset || null,
      affected_assets: form.value.affected_assets,
      references: form.value.references,
      status: form.value.status,
      assigned_to: form.value.assigned_to,
    }
    const { data } = await api.patch<Finding>(`/findings/${route.params.id}/`, payload)
    finding.value = data
    editing.value = false
    success.value = 'Finding updated successfully.'
    await fetchHistory()
    setTimeout(() => (success.value = ''), 3000)
  } catch (e: any) {
    const data = e.response?.data
    if (data && typeof data === 'object') {
      error.value = Object.entries(data)
        .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
        .join(' | ')
    } else {
      error.value = 'Failed to save finding.'
    }
  } finally {
    saving.value = false
  }
}

async function handleDelete() {
  if (!confirm('Are you sure you want to delete this finding? This cannot be undone.')) return
  try {
    await api.delete(`/findings/${route.params.id}/`)
    router.push('/findings')
  } catch {
    error.value = 'Failed to delete finding.'
  }
}

function prefillCaption() {
  const fileEl = evidenceFileInput.value
  if (fileEl?.files?.length) {
    evidenceCaption.value = fileEl.files[0].name
  }
}

async function handleUploadEvidence() {
  const fileEl = evidenceFileInput.value
  if (!fileEl?.files?.length) return

  uploadingEvidence.value = true
  const formData = new FormData()
  formData.append('file', fileEl.files[0])
  formData.append('caption', evidenceCaption.value || fileEl.files[0].name)

  try {
    await api.post(`/findings/${route.params.id}/evidence/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    evidenceCaption.value = ''
    fileEl.value = ''
    await fetchFinding()
  } catch {
    error.value = 'Failed to upload evidence.'
  } finally {
    uploadingEvidence.value = false
  }
}

const IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']
function isImageFile(path: string): boolean {
  const lower = path.toLowerCase()
  return IMAGE_EXTENSIONS.some(ext => lower.endsWith(ext))
}

async function deleteEvidence(evidenceId: string) {
  if (!confirm('Delete this evidence?')) return
  try {
    await api.delete(`/findings/${route.params.id}/evidence/${evidenceId}/`)
    await fetchFinding()
  } catch {
    error.value = 'Failed to delete evidence.'
  }
}

onMounted(fetchFinding)
</script>

<template>
  <div>
    <div class="flex-between mb-2">
      <div class="flex items-center gap-1">
        <button class="btn btn-secondary btn-sm" @click="router.push('/findings')">← Back</button>
        <h1 v-if="finding && !editing">{{ finding.title }}</h1>
      </div>
      <div v-if="finding && !editing" class="flex gap-1">
        <button v-if="canEdit" class="btn btn-primary" @click="startEdit">Edit</button>
        <button v-if="canDelete" class="btn btn-danger" @click="handleDelete">Delete</button>
      </div>
    </div>

    <div v-if="error" class="alert alert-error">{{ error }}</div>
    <div v-if="success" class="alert alert-success">{{ success }}</div>
    <div v-if="loading" class="text-muted text-center mt-3">Loading finding…</div>

    <!-- ═══ VIEW MODE ═══ -->
    <template v-if="finding && !editing">
      <div class="finding-layout">
        <!-- Left column: Finding details -->
        <div class="finding-main">
          <!-- Metadata bar -->
          <div class="card mb-2" style="padding: 1rem">
            <div class="flex gap-1 flex-wrap items-center">
              <span class="badge" :class="`badge-${finding.severity}`">{{ finding.severity }}</span>
              <span class="badge" :class="`badge-${finding.status}`">{{ finding.status.replace('_', ' ') }}</span>
              <span v-if="finding.cvss_score" class="text-muted">CVSS: {{ finding.cvss_score }}</span>
              <span v-if="finding.cvss_vector" class="text-muted" style="font-size: 0.8rem; font-family: monospace">{{ finding.cvss_vector }}</span>
              <span class="text-muted" style="margin-left: auto">
                by {{ finding.created_by_username || 'unknown' }} · {{ new Date(finding.created_at).toLocaleDateString() }}
              </span>
            </div>
          </div>

          <!-- Description -->
          <div class="card mb-2">
            <h3 class="mb-1">Description</h3>
            <div class="markdown-preview" v-html="renderMarkdown(finding.description)"></div>
          </div>

          <!-- Impact -->
          <div v-if="finding.impact" class="card mb-2">
            <h3 class="mb-1">Impact</h3>
            <div class="markdown-preview" v-html="renderMarkdown(finding.impact)"></div>
          </div>

          <!-- Recommendations -->
          <div v-if="finding.recommendations" class="card mb-2">
            <h3 class="mb-1">Recommendations</h3>
            <div class="markdown-preview" v-html="renderMarkdown(finding.recommendations)"></div>
          </div>

          <!-- Affected Assets -->
          <div v-if="finding.asset_detail || finding.affected_assets" class="card mb-2">
            <h3 class="mb-1">Affected Assets</h3>
            <div v-if="finding.asset_detail" style="margin-bottom: 0.5rem">
              <router-link :to="`/assets/${finding.asset_detail.id}`" style="font-weight: 500">
                🖥️ {{ finding.asset_detail.name }}
              </router-link>
              <span class="text-muted" style="font-size: 0.8rem; margin-left: 0.5rem">
                {{ finding.asset_detail.asset_type }} {{ finding.asset_detail.ip_address ? `• ${finding.asset_detail.ip_address}` : '' }}
              </span>
            </div>
            <pre v-if="finding.affected_assets" style="background: var(--color-bg); padding: 0.75rem; border-radius: var(--radius); font-size: 0.85rem; white-space: pre-wrap">{{ finding.affected_assets }}</pre>
          </div>

          <!-- References -->
          <div v-if="finding.references" class="card mb-2">
            <h3 class="mb-1">References / CVE IDs</h3>
            <pre style="background: var(--color-bg); padding: 0.75rem; border-radius: var(--radius); font-size: 0.85rem; white-space: pre-wrap">{{ finding.references }}</pre>
          </div>

          <!-- Evidence -->
          <div class="card mb-2">
            <h3 class="mb-1">Evidence ({{ finding.evidences?.length || 0 }})</h3>

            <div v-if="finding.evidences?.length" style="margin-bottom: 1rem">
              <div v-for="ev in finding.evidences" :key="ev.id" style="padding: 0.5rem 0; border-bottom: 1px solid var(--color-border)">
                <div class="flex-between" style="margin-bottom: 0.5rem">
                  <div>
                    <a href="#" @click.prevent="downloadMedia(ev.file, ev.caption || ev.file.split('/').pop())">{{ ev.caption || ev.file.split('/').pop() }}</a>
                    <span class="text-muted" style="font-size: 0.8rem; margin-left: 0.5rem">
                      uploaded by {{ ev.uploaded_by_username }}
                    </span>
                  </div>
                  <div class="flex gap-1">
                    <button v-if="canEdit" class="btn btn-danger btn-sm" @click="deleteEvidence(ev.id)">×</button>
                  </div>
                </div>
                <img
                  v-if="isImageFile(ev.file)"
                  :src="ev.file.startsWith('http') ? ev.file : `${backendBase}${ev.file}`"
                  :alt="ev.caption || ev.file.split('/').pop()"
                  style="max-width: 100%; max-height: 400px; border-radius: var(--radius); border: 1px solid var(--color-border)"
                />
              </div>
            </div>

            <div v-if="canEdit" class="flex gap-1 items-center flex-wrap">
              <input ref="evidenceFileInput" type="file" style="font-size: 0.85rem" @change="prefillCaption" />
              <input v-model="evidenceCaption" class="form-input" placeholder="Name (defaults to filename)" style="width: 250px" />
              <button class="btn btn-primary btn-sm" :disabled="uploadingEvidence" @click="handleUploadEvidence">
                {{ uploadingEvidence ? 'Uploading…' : 'Upload' }}
              </button>
            </div>
          </div>
        </div>

        <!-- Right column: Chronology sidebar -->
        <aside class="finding-sidebar">
          <div class="card chronology-card">
            <h3 class="mb-1">Chronology ({{ history.length }})</h3>
            <div v-if="history.length === 0" class="text-muted" style="font-size: 0.85rem">No history recorded yet.</div>
            <div v-else class="timeline">
              <div v-for="entry in history" :key="entry.id" class="timeline-entry">
                <div class="timeline-dot" :class="`dot-${entry.action}`"></div>
                <div class="timeline-content">
                  <div class="timeline-header">
                    <span class="timeline-action badge" :class="`badge-action-${entry.action}`">{{ entry.action }}</span>
                    <span class="timeline-user">{{ entry.changed_by_username || 'System' }}</span>
                    <span class="timeline-time">{{ new Date(entry.timestamp).toLocaleString() }}</span>
                  </div>
                  <div v-if="Object.keys(entry.changes).length" class="timeline-changes">
                    <div v-for="(change, field) in entry.changes" :key="field" class="change-row">
                      <span class="change-field">{{ fieldLabel(String(field)) }}</span>
                      <template v-if="entry.action === 'created'">
                        <span v-if="!isLongText(change.new)" class="change-value change-new">{{ formatVal(change.new) }}</span>
                        <span v-else class="change-value change-new text-truncate" :title="String(change.new)">{{ formatVal(change.new).substring(0, 50) }}…</span>
                      </template>
                      <template v-else>
                        <div class="change-diff">
                          <span v-if="!isLongText(change.old)" class="change-value change-old">{{ formatVal(change.old) }}</span>
                          <span v-else class="change-value change-old text-truncate" :title="String(change.old)">{{ formatVal(change.old).substring(0, 50) }}…</span>
                          <span class="change-arrow">→</span>
                          <span v-if="!isLongText(change.new)" class="change-value change-new">{{ formatVal(change.new) }}</span>
                          <span v-else class="change-value change-new text-truncate" :title="String(change.new)">{{ formatVal(change.new).substring(0, 50) }}…</span>
                        </div>
                      </template>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </template>

    <!-- ═══ EDIT MODE ═══ -->
    <template v-if="finding && editing">
      <form @submit.prevent="handleSave">
        <div class="card mb-2">
          <div class="form-group">
            <label>Title</label>
            <input v-model="form.title" class="form-input" required />
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem">
            <div class="form-group">
              <label>Severity</label>
              <select v-model="form.severity" class="form-select">
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
            <input v-model="form.cvss_vector" class="form-input" />
          </div>
        </div>

        <!-- Description: Split Pane Editor -->
        <div class="card mb-2">
          <div class="flex-between mb-1">
            <h3>Description (Markdown)</h3>
            <div v-if="finding?.evidences?.length" class="evidence-insert-menu">
              <span class="text-muted" style="font-size: 0.8rem; margin-right: 0.5rem">Insert evidence:</span>
              <button
                v-for="ev in finding.evidences"
                :key="'desc-' + ev.id"
                type="button"
                class="btn btn-secondary btn-sm"
                style="font-size: 0.75rem"
                title="Insert image at cursor"
                @click="insertEvidenceInto('description', ev)"
              >
                📷 {{ ev.caption || ev.file.split('/').pop() }}
              </button>
            </div>
          </div>
          <div class="split-editor">
            <textarea ref="descriptionTextarea" v-model="form.description" class="form-textarea" rows="12"></textarea>
            <div class="markdown-preview" v-html="renderMarkdown(form.description || '')"></div>
          </div>
        </div>

        <!-- Impact: Split Pane Editor -->
        <div class="card mb-2">
          <div class="flex-between mb-1">
            <h3>Impact (Markdown)</h3>
            <div v-if="finding?.evidences?.length" class="evidence-insert-menu">
              <span class="text-muted" style="font-size: 0.8rem; margin-right: 0.5rem">Insert evidence:</span>
              <button
                v-for="ev in finding.evidences"
                :key="'imp-' + ev.id"
                type="button"
                class="btn btn-secondary btn-sm"
                style="font-size: 0.75rem"
                title="Insert image at cursor"
                @click="insertEvidenceInto('impact', ev)"
              >
                📷 {{ ev.caption || ev.file.split('/').pop() }}
              </button>
            </div>
          </div>
          <div class="split-editor">
            <textarea ref="impactTextarea" v-model="form.impact" class="form-textarea" rows="8"></textarea>
            <div class="markdown-preview" v-html="renderMarkdown(form.impact || '')"></div>
          </div>
        </div>

        <!-- Recommendations: Split Pane Editor -->
        <div class="card mb-2">
          <div class="flex-between mb-1">
            <h3>Recommendations (Markdown)</h3>
            <div v-if="finding?.evidences?.length" class="evidence-insert-menu">
              <span class="text-muted" style="font-size: 0.8rem; margin-right: 0.5rem">Insert evidence:</span>
              <button
                v-for="ev in finding.evidences"
                :key="'rec-' + ev.id"
                type="button"
                class="btn btn-secondary btn-sm"
                style="font-size: 0.75rem"
                title="Insert image at cursor"
                @click="insertEvidenceInto('recommendations', ev)"
              >
                📷 {{ ev.caption || ev.file.split('/').pop() }}
              </button>
            </div>
          </div>
          <div class="split-editor">
            <textarea ref="recommendationsTextarea" v-model="form.recommendations" class="form-textarea" rows="8"></textarea>
            <div class="markdown-preview" v-html="renderMarkdown(form.recommendations || '')"></div>
          </div>
        </div>

        <div class="card mb-2">
          <div class="form-group">
            <label>Asset</label>
            <select v-model="form.asset" class="form-select">
              <option :value="null">— No asset —</option>
              <option v-for="a in assets" :key="a.id" :value="a.id">{{ a.name }} ({{ a.asset_type }})</option>
            </select>
          </div>
          <div class="form-group">
            <label>Affected Assets (one per line)</label>
            <textarea v-model="form.affected_assets" class="form-textarea" rows="4"></textarea>
          </div>
          <div class="form-group">
            <label>References / CVE IDs (one per line)</label>
            <textarea v-model="form.references" class="form-textarea" rows="4"></textarea>
          </div>
        </div>

        <div class="flex gap-1" style="justify-content: flex-end">
          <button type="button" class="btn btn-secondary" @click="cancelEdit">Cancel</button>
          <button type="submit" class="btn btn-primary" :disabled="saving">
            {{ saving ? 'Saving…' : 'Save Changes' }}
          </button>
        </div>
      </form>
    </template>
  </div>
</template>

<style scoped>
.evidence-insert-menu {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.375rem;
}

/* Constrain evidence images in markdown preview */
:deep(.markdown-preview img) {
  max-width: 100%;
  height: auto;
  border-radius: var(--radius);
  border: 1px solid var(--color-border);
  margin: 0.5rem 0;
}

/* Copy code button */
:deep(.markdown-preview pre) {
  position: relative;
}

:deep(.copy-code-btn) {
  position: absolute;
  top: 0.4rem;
  right: 0.4rem;
  padding: 0.2rem 0.55rem;
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--color-text-muted);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s, background-color 0.2s, color 0.2s;
  z-index: 2;
}

:deep(pre:hover .copy-code-btn) {
  opacity: 1;
}

:deep(.copy-code-btn:hover) {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}

:deep(.copy-code-btn.copied) {
  background: #22c55e;
  color: white;
  border-color: #22c55e;
  opacity: 1;
}

/* ── Two-column layout ── */
.finding-layout {
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 1.5rem;
  align-items: start;
}

.finding-main {
  min-width: 0; /* prevent overflow */
}

.finding-sidebar {
  position: sticky;
  top: 1rem;
  max-height: calc(100vh - 2rem);
  overflow-y: auto;
}

.chronology-card {
  max-height: calc(100vh - 3rem);
  overflow-y: auto;
}

/* Responsive: stack on narrow screens */
@media (max-width: 900px) {
  .finding-layout {
    grid-template-columns: 1fr;
  }

  .finding-sidebar {
    position: static;
    max-height: none;
  }

  .chronology-card {
    max-height: none;
  }
}

/* ── Timeline / Chronology ── */
.timeline {
  position: relative;
  padding-left: 1.5rem;
}

.timeline::before {
  content: '';
  position: absolute;
  left: 0.45rem;
  top: 0;
  bottom: 0;
  width: 2px;
  background: var(--color-border);
}

.timeline-entry {
  position: relative;
  margin-bottom: 1rem;
}

.timeline-entry:last-child {
  margin-bottom: 0;
}

.timeline-dot {
  position: absolute;
  left: -1.3rem;
  top: 0.3rem;
  width: 0.55rem;
  height: 0.55rem;
  border-radius: 50%;
  border: 2px solid var(--color-border);
  background: var(--color-bg-card);
  z-index: 1;
}

.dot-created {
  background: #22c55e;
  border-color: #22c55e;
}

.dot-updated {
  background: var(--color-primary);
  border-color: var(--color-primary);
}

.dot-deleted {
  background: #ef4444;
  border-color: #ef4444;
}

.timeline-content {
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 0.6rem 0.75rem;
}

.timeline-header {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  margin-bottom: 0.4rem;
  flex-wrap: wrap;
}

.timeline-action {
  font-size: 0.65rem;
  font-weight: 600;
  text-transform: uppercase;
  padding: 0.1rem 0.35rem;
  border-radius: var(--radius);
}

.badge-action-created {
  background: #22c55e;
  color: white;
}

.badge-action-updated {
  background: var(--color-primary);
  color: white;
}

.badge-action-deleted {
  background: #ef4444;
  color: white;
}

.timeline-user {
  font-weight: 500;
  font-size: 0.78rem;
}

.timeline-time {
  color: var(--color-text-muted);
  font-size: 0.72rem;
  width: 100%;
}

.timeline-changes {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.change-row {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  font-size: 0.78rem;
  line-height: 1.35;
}

.change-field {
  font-weight: 600;
  color: var(--color-text-muted);
  font-size: 0.72rem;
}

.change-diff {
  display: flex;
  align-items: flex-start;
  gap: 0.25rem;
  flex-wrap: wrap;
}

.change-value {
  padding: 0.05rem 0.3rem;
  border-radius: 3px;
  font-size: 0.75rem;
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
  word-break: break-word;
}

.change-old {
  background: rgba(239, 68, 68, 0.12);
  color: #ef4444;
  text-decoration: line-through;
}

.change-new {
  background: rgba(34, 197, 94, 0.12);
  color: #22c55e;
}

.change-arrow {
  color: var(--color-text-muted);
  flex-shrink: 0;
  font-size: 0.75rem;
}

.text-truncate {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: inline-block;
}
</style>
