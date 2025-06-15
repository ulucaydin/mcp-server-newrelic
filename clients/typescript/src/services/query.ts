import { AxiosInstance } from 'axios';
import { QueryRequest, QueryResponse } from '../types';

export class QueryService {
  constructor(private readonly client: AxiosInstance) {}

  /**
   * Execute a query
   */
  async execute(request: QueryRequest): Promise<QueryResponse> {
    const response = await this.client.post<QueryResponse>('/query', request);
    return response.data;
  }

  /**
   * Validate a query without executing it
   */
  async validate(query: string): Promise<{
    valid: boolean;
    errors?: Array<{
      line: number;
      column: number;
      message: string;
    }>;
    warnings?: string[];
  }> {
    const response = await this.client.post<{
      valid: boolean;
      errors?: Array<{
        line: number;
        column: number;
        message: string;
      }>;
      warnings?: string[];
    }>('/query/validate', { query });
    return response.data;
  }

  /**
   * Get query suggestions based on partial input
   */
  async suggest(partial: string, context?: {
    eventType?: string;
    cursorPosition?: number;
  }): Promise<{
    suggestions: Array<{
      text: string;
      type: string;
      description?: string;
      insertText?: string;
    }>;
  }> {
    const response = await this.client.post<{
      suggestions: Array<{
        text: string;
        type: string;
        description?: string;
        insertText?: string;
      }>;
    }>('/query/suggest', {
      partial,
      ...context
    });
    return response.data;
  }

  /**
   * Format a query
   */
  async format(query: string): Promise<{
    formatted: string;
    changed: boolean;
  }> {
    const response = await this.client.post<{
      formatted: string;
      changed: boolean;
    }>('/query/format', { query });
    return response.data;
  }

  /**
   * Get query history
   */
  async getHistory(options?: {
    limit?: number;
    offset?: number;
    timeRange?: {
      from: string;
      to: string;
    };
  }): Promise<{
    queries: Array<{
      id: string;
      query: string;
      executedAt: string;
      executionTime: string;
      resultCount?: number;
      user?: string;
    }>;
    total: number;
  }> {
    const params = new URLSearchParams();
    
    if (options?.limit !== undefined) {
      params.append('limit', options.limit.toString());
    }
    if (options?.offset !== undefined) {
      params.append('offset', options.offset.toString());
    }
    if (options?.timeRange) {
      params.append('from', options.timeRange.from);
      params.append('to', options.timeRange.to);
    }

    const response = await this.client.get<{
      queries: Array<{
        id: string;
        query: string;
        executedAt: string;
        executionTime: string;
        resultCount?: number;
        user?: string;
      }>;
      total: number;
    }>('/query/history', {
      params: Object.fromEntries(params)
    });
    return response.data;
  }

  /**
   * Export query results
   */
  async export(queryId: string, format: 'csv' | 'json' | 'parquet'): Promise<Blob> {
    const response = await this.client.get(`/query/${encodeURIComponent(queryId)}/export`, {
      params: { format },
      responseType: 'blob'
    });
    return response.data as Blob;
  }
}