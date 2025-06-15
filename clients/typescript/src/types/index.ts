// Common types and interfaces for the UDS TypeScript client

export interface ClientConfig {
  baseURL?: string;
  apiKey?: string;
  timeout?: number;
  retryMax?: number;
  retryWait?: number;
  userAgent?: string;
}

export interface APIError {
  error: string;
  message: string;
  details?: Record<string, unknown>;
  statusCode?: number;
}

export interface HealthStatus {
  status: string;
  version: string;
  uptime: string;
  components: Record<string, Record<string, unknown>>;
}

// Discovery types
export interface Schema {
  name: string;
  eventType: string;
  attributes: SchemaAttribute[];
  recordCount: number;
  firstSeen: string;
  lastSeen: string;
  quality: QualityMetrics;
  metadata?: Record<string, unknown>;
}

export interface SchemaAttribute {
  name: string;
  dataType: string;
  nullable: boolean;
  cardinality: number;
  sampleValues?: unknown[];
  statistics?: AttributeStatistics;
}

export interface AttributeStatistics {
  nullCount: number;
  distinctCount: number;
  minValue?: unknown;
  maxValue?: unknown;
  avgValue?: unknown;
}

export interface QualityMetrics {
  overallScore: number;
  completeness: number;
  consistency: number;
  validity: number;
  uniqueness: number;
  details?: Record<string, unknown>;
}

export interface ListSchemasOptions {
  eventType?: string;
  minRecordCount?: number;
  maxSchemas?: number;
  sortBy?: string;
  includeMetadata?: boolean;
}

export interface ListSchemasResponse {
  schemas: Schema[];
  metadata?: DiscoveryMetadata;
}

export interface DiscoveryMetadata {
  totalSchemas: number;
  executionTime: string;
  cacheHit: boolean;
  filters?: Record<string, unknown>;
}

// Pattern types
export interface Pattern {
  id: string;
  name: string;
  description: string;
  query: string;
  category: string;
  tags?: string[];
  metadata?: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface SearchPatternsOptions {
  query?: string;
  category?: string;
  tags?: string[];
  limit?: number;
  offset?: number;
}

export interface SearchPatternsResponse {
  patterns: Pattern[];
  total: number;
  metadata?: Record<string, unknown>;
}

// Query types
export interface QueryRequest {
  query: string;
  timeRange?: TimeRange;
  variables?: Record<string, unknown>;
  options?: QueryOptions;
}

export interface TimeRange {
  from: string;
  to: string;
}

export interface QueryOptions {
  timeout?: number;
  maxResults?: number;
  includeMetadata?: boolean;
}

export interface QueryResponse {
  results: QueryResult[];
  metadata?: QueryMetadata;
}

export interface QueryResult {
  data: unknown[];
  columns?: Column[];
  totalCount?: number;
}

export interface Column {
  name: string;
  type: string;
  nullable?: boolean;
}

export interface QueryMetadata {
  executionTime: string;
  bytesProcessed?: number;
  cached?: boolean;
  warnings?: string[];
}

// Dashboard types
export interface Dashboard {
  id: string;
  name: string;
  description?: string;
  widgets: Widget[];
  layout?: LayoutConfig;
  variables?: DashboardVariable[];
  metadata?: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface Widget {
  id: string;
  type: string;
  title: string;
  query: string;
  visualization: VisualizationConfig;
  position?: Position;
  size?: Size;
}

export interface VisualizationConfig {
  type: string;
  options?: Record<string, unknown>;
}

export interface Position {
  x: number;
  y: number;
}

export interface Size {
  width: number;
  height: number;
}

export interface LayoutConfig {
  type: string;
  columns?: number;
  rows?: number;
}

export interface DashboardVariable {
  name: string;
  type: string;
  defaultValue?: unknown;
  options?: unknown[];
}

export interface ListDashboardsOptions {
  search?: string;
  tags?: string[];
  limit?: number;
  offset?: number;
}

export interface ListDashboardsResponse {
  dashboards: Dashboard[];
  total: number;
  metadata?: Record<string, unknown>;
}