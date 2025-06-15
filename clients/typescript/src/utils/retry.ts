import axiosRetry, { IAxiosRetryConfig } from 'axios-retry';
import { AxiosInstance, AxiosError } from 'axios';

export interface RetryConfig {
  retries?: number;
  retryDelay?: (retryCount: number) => number;
  retryCondition?: (error: AxiosError) => boolean;
}

export function configureRetry(client: AxiosInstance, config: RetryConfig = {}): void {
  const retryConfig: IAxiosRetryConfig = {
    retries: config.retries ?? 3,
    retryDelay: config.retryDelay ?? axiosRetry.exponentialDelay,
    retryCondition: config.retryCondition ?? ((error: AxiosError) => {
      // Retry on network errors
      if (!error.response) {
        return true;
      }
      
      // Retry on specific status codes
      const retryableStatuses = [408, 429, 502, 503, 504];
      return retryableStatuses.includes(error.response.status);
    }),
    shouldResetTimeout: true
  };

  axiosRetry(client, retryConfig);
}

export function exponentialBackoffWithJitter(retryCount: number, baseDelay = 1000): number {
  // Calculate exponential backoff
  const exponentialDelay = Math.pow(2, retryCount) * baseDelay;
  
  // Add jitter (±25%)
  const jitter = exponentialDelay * 0.25 * (Math.random() * 2 - 1);
  const delayWithJitter = exponentialDelay + jitter;
  
  // Cap at 30 seconds
  return Math.min(delayWithJitter, 30000);
}