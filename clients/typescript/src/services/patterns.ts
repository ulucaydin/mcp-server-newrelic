import { AxiosInstance } from 'axios';
import { Pattern, SearchPatternsOptions, SearchPatternsResponse } from '../types';

export class PatternsService {
  constructor(private readonly client: AxiosInstance) {}

  /**
   * Search for patterns
   */
  async search(options?: SearchPatternsOptions): Promise<SearchPatternsResponse> {
    const params = new URLSearchParams();
    
    if (options?.query) {
      params.append('query', options.query);
    }
    if (options?.category) {
      params.append('category', options.category);
    }
    if (options?.tags && options.tags.length > 0) {
      options.tags.forEach(tag => params.append('tags', tag));
    }
    if (options?.limit !== undefined) {
      params.append('limit', options.limit.toString());
    }
    if (options?.offset !== undefined) {
      params.append('offset', options.offset.toString());
    }

    const response = await this.client.get<SearchPatternsResponse>('/patterns', {
      params: Object.fromEntries(params)
    });
    return response.data;
  }

  /**
   * Get a specific pattern by ID
   */
  async get(id: string): Promise<Pattern> {
    const response = await this.client.get<Pattern>(`/patterns/${encodeURIComponent(id)}`);
    return response.data;
  }

  /**
   * Create a new pattern
   */
  async create(pattern: Omit<Pattern, 'id' | 'createdAt' | 'updatedAt'>): Promise<Pattern> {
    const response = await this.client.post<Pattern>('/patterns', pattern);
    return response.data;
  }

  /**
   * Update an existing pattern
   */
  async update(id: string, updates: Partial<Omit<Pattern, 'id' | 'createdAt' | 'updatedAt'>>): Promise<Pattern> {
    const response = await this.client.put<Pattern>(`/patterns/${encodeURIComponent(id)}`, updates);
    return response.data;
  }

  /**
   * Delete a pattern
   */
  async delete(id: string): Promise<void> {
    await this.client.delete(`/patterns/${encodeURIComponent(id)}`);
  }

  /**
   * Execute a pattern by ID
   */
  async execute(id: string, variables?: Record<string, unknown>): Promise<{
    results: unknown[];
    metadata?: Record<string, unknown>;
  }> {
    const response = await this.client.post<{
      results: unknown[];
      metadata?: Record<string, unknown>;
    }>(`/patterns/${encodeURIComponent(id)}/execute`, { variables });
    return response.data;
  }

  /**
   * Get pattern categories
   */
  async getCategories(): Promise<string[]> {
    const response = await this.client.get<string[]>('/patterns/categories');
    return response.data;
  }

  /**
   * Get all unique tags
   */
  async getTags(): Promise<string[]> {
    const response = await this.client.get<string[]>('/patterns/tags');
    return response.data;
  }
}