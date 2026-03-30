/* TypeScript interfaces matching the Django API. */

export interface User {
  id: number
  username: string
  email: string
  first_name: string
  last_name: string
  role: 'admin' | 'analyst' | 'viewer'
  is_active: boolean
  date_joined: string
  last_login: string | null
}

export interface UserCreate {
  username: string
  email: string
  password: string
  first_name: string
  last_name: string
  role: 'admin' | 'analyst' | 'viewer'
}

export interface UserUpdate {
  username?: string
  email?: string
  password?: string
  first_name?: string
  last_name?: string
  role?: 'admin' | 'analyst' | 'viewer'
  is_active?: boolean
}

export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'informational'
export type FindingStatus = 'open' | 'in_progress' | 'remediated' | 'closed' | 'accepted'
export type AssetType = 'host' | 'web_app' | 'api' | 'network' | 'cloud' | 'mobile' | 'database' | 'other'

export interface Client {
  id: string
  name: string
  description: string
  asset_count?: number
  created_by: number | null
  created_by_username: string | null
  created_at: string
  updated_at: string
}

export interface ClientCreate {
  name: string
  description?: string
}

export interface Asset {
  id: string
  name: string
  asset_type: AssetType
  ip_address: string | null
  hostname: string
  url: string
  os: string
  description: string
  client: string | null
  client_name: string | null
  finding_count?: number
  created_by: number | null
  created_by_username: string | null
  created_at: string
  updated_at: string
}

export interface AssetCreate {
  name: string
  asset_type: AssetType
  ip_address?: string | null
  hostname?: string
  url?: string
  os?: string
  description?: string
  client?: string | null
}

export interface AssetMinimal {
  id: string
  name: string
  asset_type: AssetType
  ip_address: string | null
  hostname: string
}

export interface Finding {
  id: string
  title: string
  description: string
  impact: string
  recommendations: string
  severity: Severity
  cvss_score: number | null
  cvss_vector: string
  asset: string | null
  asset_name?: string | null
  asset_detail?: AssetMinimal | null
  affected_assets: string
  references: string
  status: FindingStatus
  created_by: number | null
  created_by_username: string | null
  assigned_to: number | null
  assigned_to_username: string | null
  evidences?: Evidence[]
  evidence_count?: number
  created_at: string
  updated_at: string
}

export interface FindingCreate {
  title: string
  description: string
  impact?: string
  recommendations?: string
  severity: Severity
  cvss_score?: number | null
  cvss_vector?: string
  asset?: string | null
  affected_assets?: string
  references?: string
  status?: FindingStatus
  assigned_to?: number | null
}

export interface Evidence {
  id: string
  file: string
  caption: string
  uploaded_by: number | null
  uploaded_by_username: string
  uploaded_at: string
}

export interface FindingHistoryChange {
  old: string | number | null
  new: string | number | null
}

export interface FindingHistoryEntry {
  id: string
  finding: string
  action: 'created' | 'updated' | 'deleted'
  changes: Record<string, FindingHistoryChange>
  changed_by: number | null
  changed_by_username: string | null
  timestamp: string
}

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface LoginRequest {
  username: string
  password: string
}

export interface TokenPair {
  access: string
  refresh: string
}

// ── Report Templates ──
export interface ReportTemplate {
  id: string
  name: string
  description: string
  file: string
  uploaded_by: number | null
  uploaded_by_username: string | null
  created_at: string
  updated_at: string
}

export interface GeneratedReport {
  id: string
  name: string
  template: string | null
  template_name: string | null
  file: string
  finding_count: number
  generated_by: number | null
  generated_by_username: string | null
  created_at: string
}
