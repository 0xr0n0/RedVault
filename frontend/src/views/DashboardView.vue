<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api/client'

const router = useRouter()
const loading = ref(true)
const error = ref('')

interface Stats {
  total: number
  open: number
  in_progress: number
  remediated: number
  closed: number
  accepted: number
  critical: number
  high: number
  medium: number
  low: number
  informational: number
  open_critical: number
  open_high: number
  open_medium: number
  open_low: number
  open_informational: number
  avg_cvss: number
  total_evidence: number
  recent_findings: {
    id: string
    title: string
    severity: string
    status: string
    created_at: string
    created_by__username: string | null
  }[]
}

const stats = ref<Stats | null>(null)

// Timeline chart
interface TimelinePoint {
  date: string
  total: number
  critical: number
  high: number
  medium: number
  low: number
  informational: number
}
const timelineData = ref<TimelinePoint[]>([])
const timelineGroup = ref<'day' | 'month'>('day')
const timelineDays = ref(90)
const timelineLoading = ref(false)

async function fetchStats() {
  loading.value = true
  try {
    const { data } = await api.get<Stats>('/findings/stats/')
    stats.value = data
  } catch {
    error.value = 'Failed to load dashboard statistics.'
  } finally {
    loading.value = false
  }
}

async function fetchTimeline() {
  timelineLoading.value = true
  try {
    const { data } = await api.get('/findings/timeline/', {
      params: { group: timelineGroup.value, days: timelineDays.value }
    })
    timelineData.value = data.data
  } catch {
    // silent — chart just won't render
  } finally {
    timelineLoading.value = false
  }
}

function switchTimelineGroup(group: 'day' | 'month') {
  timelineGroup.value = group
  if (group === 'month') timelineDays.value = 365
  else timelineDays.value = 90
  fetchTimeline()
}

// SVG chart computations
const chartWidth = 700
const chartHeight = 200
const chartPadding = { top: 20, right: 20, bottom: 30, left: 40 }
const innerWidth = chartWidth - chartPadding.left - chartPadding.right
const innerHeight = chartHeight - chartPadding.top - chartPadding.bottom

const timelineMax = computed(() => Math.max(...timelineData.value.map(d => d.total), 1))

const timelinePoints = computed(() => {
  const data = timelineData.value
  if (data.length === 0) return []
  const stepX = data.length > 1 ? innerWidth / (data.length - 1) : innerWidth / 2
  return data.map((d, i) => ({
    x: chartPadding.left + (data.length > 1 ? i * stepX : stepX),
    y: chartPadding.top + innerHeight - (d.total / timelineMax.value) * innerHeight,
    ...d,
  }))
})

const timelineLinePath = computed(() => {
  if (timelinePoints.value.length === 0) return ''
  return timelinePoints.value.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ')
})

const timelineAreaPath = computed(() => {
  if (timelinePoints.value.length === 0) return ''
  const baseline = chartPadding.top + innerHeight
  const pts = timelinePoints.value
  let path = `M ${pts[0].x} ${baseline}`
  for (const p of pts) path += ` L ${p.x} ${p.y}`
  path += ` L ${pts[pts.length - 1].x} ${baseline} Z`
  return path
})

// Y-axis labels
const yAxisLabels = computed(() => {
  const max = timelineMax.value
  const steps = [0, Math.round(max / 2), max]
  return steps.map(v => ({
    value: v,
    y: chartPadding.top + innerHeight - (v / max) * innerHeight,
  }))
})

// X-axis labels (show a subset)
const xAxisLabels = computed(() => {
  const pts = timelinePoints.value
  if (pts.length === 0) return []
  const maxLabels = 8
  const step = Math.max(1, Math.floor(pts.length / maxLabels))
  return pts.filter((_, i) => i % step === 0 || i === pts.length - 1).map(p => {
    const d = new Date(p.date)
    const label = timelineGroup.value === 'month'
      ? d.toLocaleDateString('en', { month: 'short', year: '2-digit' })
      : d.toLocaleDateString('en', { month: 'short', day: 'numeric' })
    return { x: p.x, label }
  })
})

// Stacked severity breakdown for tooltip-like display per point
const hoveredPoint = ref<(TimelinePoint & { x: number; y: number }) | null>(null)

// Computed: severity bar chart data (max value for scale)
const severityBars = computed(() => {
  if (!stats.value) return []
  const s = stats.value
  const items = [
    { label: 'Critical', count: s.critical, open: s.open_critical, color: 'var(--color-critical)' },
    { label: 'High', count: s.high, open: s.open_high, color: 'var(--color-high)' },
    { label: 'Medium', count: s.medium, open: s.open_medium, color: 'var(--color-medium)' },
    { label: 'Low', count: s.low, open: s.open_low, color: 'var(--color-low)' },
    { label: 'Info', count: s.informational, open: s.open_informational, color: 'var(--color-info)' },
  ]
  return items
})

const maxSeverityCount = computed(() => {
  return Math.max(...severityBars.value.map(b => b.count), 1)
})

// Status distribution for the donut-like display
const statusItems = computed(() => {
  if (!stats.value) return []
  const s = stats.value
  return [
    { label: 'Open', count: s.open, color: 'var(--color-danger)', cssClass: 'badge-open' },
    { label: 'In Progress', count: s.in_progress, color: 'var(--color-warning)', cssClass: 'badge-in_progress' },
    { label: 'Remediated', count: s.remediated, color: 'var(--color-success)', cssClass: 'badge-remediated' },
    { label: 'Closed', count: s.closed, color: 'var(--color-info)', cssClass: 'badge-closed' },
    { label: 'Accepted', count: s.accepted, color: 'var(--color-primary)', cssClass: 'badge-accepted' },
  ]
})

// Open findings requiring attention
const openCount = computed(() => stats.value ? stats.value.open + stats.value.in_progress : 0)
const resolvedCount = computed(() => stats.value ? stats.value.remediated + stats.value.closed + stats.value.accepted : 0)

// Risk score: weighted open findings
const riskScore = computed(() => {
  if (!stats.value) return 0
  const s = stats.value
  const weighted = s.open_critical * 10 + s.open_high * 7 + s.open_medium * 4 + s.open_low * 1
  return weighted
})

const riskLevel = computed(() => {
  const score = riskScore.value
  if (score === 0) return { label: 'Clear', color: 'var(--color-success)' }
  if (score <= 10) return { label: 'Low', color: 'var(--color-low)' }
  if (score <= 30) return { label: 'Moderate', color: 'var(--color-medium)' }
  if (score <= 60) return { label: 'High', color: 'var(--color-high)' }
  return { label: 'Critical', color: 'var(--color-critical)' }
})

function goToFinding(id: string) {
  router.push(`/findings/${id}`)
}

onMounted(() => {
  fetchStats()
  fetchTimeline()
})
</script>

<template>
  <div>
    <h1 class="mb-2">Dashboard</h1>

    <div v-if="error" class="alert alert-error">{{ error }}</div>
    <div v-if="loading" class="text-muted text-center mt-3">Loading statistics…</div>

    <template v-if="stats && !loading">
      <!-- ═══ TOP STAT CARDS ═══ -->
      <div class="stats-grid mb-2">
        <div class="stat-card">
          <div class="stat-number">{{ stats.total }}</div>
          <div class="stat-label">Total Findings</div>
        </div>
        <div class="stat-card">
          <div class="stat-number" style="color: var(--color-danger)">{{ openCount }}</div>
          <div class="stat-label">Open / In Progress</div>
        </div>
        <div class="stat-card">
          <div class="stat-number" style="color: var(--color-success)">{{ resolvedCount }}</div>
          <div class="stat-label">Resolved</div>
        </div>
        <div class="stat-card">
          <div class="stat-number">{{ stats.avg_cvss }}</div>
          <div class="stat-label">Avg CVSS Score</div>
        </div>
        <div class="stat-card">
          <div class="stat-number" :style="{ color: riskLevel.color }">{{ riskScore }}</div>
          <div class="stat-label">Risk Score · <span :style="{ color: riskLevel.color }">{{ riskLevel.label }}</span></div>
        </div>
        <div class="stat-card">
          <div class="stat-number">{{ stats.total_evidence }}</div>
          <div class="stat-label">Evidence Files</div>
        </div>
      </div>

      <!-- ═══ TIMELINE CHART ═══ -->
      <div class="card mb-2">
        <div class="flex-between mb-1">
          <h3>Findings Over Time</h3>
          <div class="flex gap-1">
            <button
              class="btn btn-sm"
              :class="timelineGroup === 'day' ? 'btn-primary' : 'btn-secondary'"
              @click="switchTimelineGroup('day')"
            >Daily</button>
            <button
              class="btn btn-sm"
              :class="timelineGroup === 'month' ? 'btn-primary' : 'btn-secondary'"
              @click="switchTimelineGroup('month')"
            >Monthly</button>
          </div>
        </div>

        <div v-if="timelineLoading" class="text-muted text-center" style="padding: 2rem">Loading chart…</div>
        <div v-else-if="timelineData.length === 0" class="text-muted text-center" style="padding: 2rem; font-size: 0.85rem">
          No findings in the selected time period.
        </div>
        <div v-else class="timeline-chart-container" @mouseleave="hoveredPoint = null">
          <svg :viewBox="`0 0 ${chartWidth} ${chartHeight}`" class="timeline-svg" preserveAspectRatio="xMidYMid meet">
            <!-- Grid lines -->
            <line
              v-for="yl in yAxisLabels" :key="'grid-' + yl.value"
              :x1="chartPadding.left" :y1="yl.y"
              :x2="chartWidth - chartPadding.right" :y2="yl.y"
              stroke="var(--color-border)" stroke-width="0.5" stroke-dasharray="4 4"
            />
            <!-- Y-axis labels -->
            <text
              v-for="yl in yAxisLabels" :key="'ylabel-' + yl.value"
              :x="chartPadding.left - 8" :y="yl.y + 4"
              text-anchor="end" fill="var(--color-text-muted)" font-size="11"
            >{{ yl.value }}</text>
            <!-- X-axis labels -->
            <text
              v-for="xl in xAxisLabels" :key="'xlabel-' + xl.label"
              :x="xl.x" :y="chartHeight - 5"
              text-anchor="middle" fill="var(--color-text-muted)" font-size="10"
            >{{ xl.label }}</text>
            <!-- Area fill -->
            <path :d="timelineAreaPath" fill="var(--color-primary)" opacity="0.15" />
            <!-- Line -->
            <path :d="timelineLinePath" fill="none" stroke="var(--color-primary)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
            <!-- Data points -->
            <circle
              v-for="(pt, i) in timelinePoints" :key="'pt-' + i"
              :cx="pt.x" :cy="pt.y" r="4"
              :fill="hoveredPoint?.date === pt.date ? 'var(--color-primary)' : 'var(--color-bg-card)'"
              stroke="var(--color-primary)" stroke-width="2"
              style="cursor: pointer"
              @mouseenter="hoveredPoint = pt"
            />
          </svg>
          <!-- Tooltip -->
          <div
            v-if="hoveredPoint"
            class="chart-tooltip"
            :style="{
              left: `${(hoveredPoint.x / chartWidth) * 100}%`,
              top: `${(hoveredPoint.y / chartHeight) * 100 - 5}%`
            }"
          >
            <div class="tooltip-date">{{ new Date(hoveredPoint.date).toLocaleDateString() }}</div>
            <div class="tooltip-total">{{ hoveredPoint.total }} finding{{ hoveredPoint.total !== 1 ? 's' : '' }}</div>
            <div v-if="hoveredPoint.critical" class="tooltip-row"><span style="color:var(--color-critical)">●</span> Critical: {{ hoveredPoint.critical }}</div>
            <div v-if="hoveredPoint.high" class="tooltip-row"><span style="color:var(--color-high)">●</span> High: {{ hoveredPoint.high }}</div>
            <div v-if="hoveredPoint.medium" class="tooltip-row"><span style="color:var(--color-medium)">●</span> Medium: {{ hoveredPoint.medium }}</div>
            <div v-if="hoveredPoint.low" class="tooltip-row"><span style="color:var(--color-low)">●</span> Low: {{ hoveredPoint.low }}</div>
            <div v-if="hoveredPoint.informational" class="tooltip-row"><span style="color:var(--color-info)">●</span> Info: {{ hoveredPoint.informational }}</div>
          </div>
        </div>
      </div>

      <!-- ═══ CHARTS ROW ═══ -->
      <div class="charts-grid mb-2">
        <!-- Severity Distribution (Horizontal Bar Chart) -->
        <div class="card">
          <h3 class="mb-1">Severity Distribution</h3>
          <div class="bar-chart">
            <div v-for="bar in severityBars" :key="bar.label" class="bar-row">
              <div class="bar-label">{{ bar.label }}</div>
              <div class="bar-track">
                <div
                  class="bar-fill"
                  :style="{
                    width: (bar.count / maxSeverityCount * 100) + '%',
                    backgroundColor: bar.color
                  }"
                >
                  <span v-if="bar.count" class="bar-value">{{ bar.count }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Status Breakdown -->
        <div class="card">
          <h3 class="mb-1">Status Breakdown</h3>
          <div class="status-list">
            <div v-for="item in statusItems" :key="item.label" class="status-row">
              <div class="status-dot" :style="{ backgroundColor: item.color }"></div>
              <div class="status-name">{{ item.label }}</div>
              <div class="status-count">{{ item.count }}</div>
              <div class="status-bar-track">
                <div
                  class="status-bar-fill"
                  :style="{
                    width: stats.total ? (item.count / stats.total * 100) + '%' : '0%',
                    backgroundColor: item.color
                  }"
                ></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══ OPEN FINDINGS BY SEVERITY ═══ -->
      <div class="charts-grid mb-2">
        <div class="card">
          <h3 class="mb-1">Open Findings by Severity</h3>
          <p class="text-muted mb-1" style="font-size: 0.8rem">Findings currently in "Open" status requiring attention</p>
          <div class="open-severity-grid">
            <div class="open-severity-item">
              <div class="open-severity-count" style="color: var(--color-critical)">{{ stats.open_critical }}</div>
              <div class="open-severity-label">Critical</div>
            </div>
            <div class="open-severity-item">
              <div class="open-severity-count" style="color: var(--color-high)">{{ stats.open_high }}</div>
              <div class="open-severity-label">High</div>
            </div>
            <div class="open-severity-item">
              <div class="open-severity-count" style="color: var(--color-medium)">{{ stats.open_medium }}</div>
              <div class="open-severity-label">Medium</div>
            </div>
            <div class="open-severity-item">
              <div class="open-severity-count" style="color: var(--color-low)">{{ stats.open_low }}</div>
              <div class="open-severity-label">Low</div>
            </div>
            <div class="open-severity-item">
              <div class="open-severity-count" style="color: var(--color-info)">{{ stats.open_informational }}</div>
              <div class="open-severity-label">Info</div>
            </div>
          </div>
        </div>

        <!-- Recent Findings -->
        <div class="card">
          <h3 class="mb-1">Recent Findings</h3>
          <div v-if="stats.recent_findings.length === 0" class="text-muted text-center mt-2" style="font-size: 0.85rem">
            No findings yet. Create your first one!
          </div>
          <div v-else class="recent-list">
            <div
              v-for="f in stats.recent_findings"
              :key="f.id"
              class="recent-item"
              @click="goToFinding(f.id)"
            >
              <div class="recent-title">{{ f.title }}</div>
              <div class="recent-meta">
                <span class="badge" :class="`badge-${f.severity}`">{{ f.severity }}</span>
                <span class="badge" :class="`badge-${f.status}`">{{ f.status.replace('_', ' ') }}</span>
                <span class="text-muted" style="font-size: 0.75rem">
                  {{ new Date(f.created_at).toLocaleDateString() }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
/* ═══ Stats Grid ═══ */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
  gap: 1rem;
}

.stat-card {
  background-color: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 1.25rem;
  text-align: center;
  box-shadow: var(--shadow);
}

.stat-number {
  font-size: 2rem;
  font-weight: 700;
  line-height: 1.2;
  margin-bottom: 0.25rem;
}

.stat-label {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

/* ═══ Charts Grid ═══ */
.charts-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

@media (max-width: 900px) {
  .charts-grid {
    grid-template-columns: 1fr;
  }
}

/* ═══ Horizontal Bar Chart ═══ */
.bar-chart {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.bar-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.bar-label {
  width: 60px;
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--color-text-muted);
  text-align: right;
  flex-shrink: 0;
}

.bar-track {
  flex: 1;
  height: 28px;
  background-color: var(--color-bg);
  border-radius: var(--radius);
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: var(--radius);
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding-right: 0.5rem;
  min-width: 0;
  transition: width 0.6s ease;
}

.bar-value {
  font-size: 0.75rem;
  font-weight: 700;
  color: white;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.4);
}

/* ═══ Status Breakdown ═══ */
.status-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.status-row {
  display: grid;
  grid-template-columns: 12px 90px 40px 1fr;
  align-items: center;
  gap: 0.5rem;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.status-name {
  font-size: 0.85rem;
}

.status-count {
  font-size: 0.85rem;
  font-weight: 700;
  text-align: right;
}

.status-bar-track {
  height: 8px;
  background-color: var(--color-bg);
  border-radius: 4px;
  overflow: hidden;
}

.status-bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.6s ease;
}

/* ═══ Open Severity Grid ═══ */
.open-severity-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 0.75rem;
  text-align: center;
}

.open-severity-count {
  font-size: 2rem;
  font-weight: 700;
  line-height: 1.2;
}

.open-severity-label {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  text-transform: uppercase;
  margin-top: 0.25rem;
}

/* ═══ Recent Findings ═══ */
.recent-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.recent-item {
  padding: 0.625rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  cursor: pointer;
  transition: background-color 0.2s;
}

.recent-item:hover {
  background-color: var(--color-bg-input);
}

.recent-title {
  font-size: 0.85rem;
  font-weight: 500;
  margin-bottom: 0.375rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.recent-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

/* ═══ Timeline Chart ═══ */
.timeline-chart-container {
  position: relative;
  width: 100%;
}

.timeline-svg {
  width: 100%;
  height: auto;
  display: block;
}

.chart-tooltip {
  position: absolute;
  transform: translate(-50%, -100%);
  background-color: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 0.5rem 0.75rem;
  font-size: 0.75rem;
  pointer-events: none;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
  z-index: 10;
  white-space: nowrap;
}

.tooltip-date {
  font-weight: 600;
  margin-bottom: 0.25rem;
  color: var(--color-text);
}

.tooltip-total {
  color: var(--color-primary);
  font-weight: 700;
  margin-bottom: 0.25rem;
}

.tooltip-row {
  color: var(--color-text-muted);
  font-size: 0.7rem;
}
</style>
