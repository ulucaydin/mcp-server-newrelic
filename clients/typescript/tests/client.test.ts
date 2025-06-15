import nock from 'nock';
import { UDSClient } from '../src/client';
import { APIError } from '../src/types';

describe('UDSClient', () => {
  let client: UDSClient;
  const baseURL = 'http://localhost:8080';
  const apiPath = '/api/v1';

  beforeEach(() => {
    client = new UDSClient({ baseURL: baseURL + apiPath });
    nock.cleanAll();
  });

  afterEach(() => {
    nock.cleanAll();
  });

  describe('constructor', () => {
    it('should create client with default config', () => {
      const defaultClient = new UDSClient();
      const config = defaultClient.getConfig();
      expect(config.baseURL).toBe('http://localhost:8080/api/v1');
      expect(config.userAgent).toBe('@newrelic/uds-client/1.0.0');
      expect(config.timeout).toBe(30000);
    });

    it('should create client with custom config', () => {
      const customClient = new UDSClient({
        baseURL: 'https://api.example.com',
        apiKey: 'test-key',
        retryMax: 5,
        timeout: 60000
      });
      const config = customClient.getConfig();
      expect(config.baseURL).toBe('https://api.example.com');
      expect(config.apiKey).toBe('test-key');
      expect(config.retryMax).toBe(5);
      expect(config.timeout).toBe(60000);
    });

    it('should initialize all service clients', () => {
      expect(client.discovery).toBeDefined();
      expect(client.patterns).toBeDefined();
      expect(client.query).toBeDefined();
      expect(client.dashboard).toBeDefined();
    });
  });

  describe('health', () => {
    it('should check API health', async () => {
      const healthResponse = {
        status: 'healthy',
        version: '1.0.0',
        uptime: '24h',
        components: {
          discovery: { status: 'healthy' }
        }
      };

      nock(baseURL)
        .get(`${apiPath}/health`)
        .reply(200, healthResponse);

      const health = await client.health();
      expect(health).toEqual(healthResponse);
    });
  });

  describe('error handling', () => {
    it('should handle API errors', async () => {
      const apiError: APIError = {
        error: 'not_found',
        message: 'Resource not found',
        details: { resource: 'schema' }
      };

      nock(baseURL)
        .get(`${apiPath}/health`)
        .reply(404, apiError);

      await expect(client.health()).rejects.toMatchObject({
        ...apiError,
        statusCode: 404
      });
    });

    it('should handle network errors', async () => {
      // Create client without retry for this test
      const noRetryClient = new UDSClient({ 
        baseURL: baseURL + apiPath,
        retryMax: 0 
      });
      
      nock(baseURL)
        .get(`${apiPath}/health`)
        .replyWithError('Network error');

      await expect(noRetryClient.health()).rejects.toThrow();
    });
  });

  describe('authentication', () => {
    it('should set Authorization header when API key is provided', async () => {
      const authClient = new UDSClient({
        baseURL: baseURL + apiPath,
        apiKey: 'test-api-key'
      });

      nock(baseURL, {
        reqheaders: {
          'Authorization': 'Bearer test-api-key'
        }
      })
        .get(`${apiPath}/health`)
        .reply(200, { status: 'healthy' });

      await authClient.health();
      expect(nock.isDone()).toBe(true);
    });

    it('should update API key', async () => {
      client.setApiKey('new-api-key');

      nock(baseURL, {
        reqheaders: {
          'Authorization': 'Bearer new-api-key'
        }
      })
        .get(`${apiPath}/health`)
        .reply(200, { status: 'healthy' });

      await client.health();
      expect(nock.isDone()).toBe(true);
    });
  });

  describe('retry logic', () => {
    it('should retry on 503 errors', async () => {
      const retryClient = new UDSClient({
        baseURL: baseURL + apiPath,
        retryMax: 3,
        retryWait: 10
      });

      let attempts = 0;
      nock(baseURL)
        .get(`${apiPath}/health`)
        .times(3)
        .reply(() => {
          attempts++;
          if (attempts < 3) {
            return [503, 'Service Unavailable'];
          }
          return [200, { status: 'healthy' }];
        });

      const health = await retryClient.health();
      expect(health.status).toBe('healthy');
      expect(attempts).toBe(3);
    });

    it('should not retry when retryMax is 0', async () => {
      const noRetryClient = new UDSClient({
        baseURL: baseURL + apiPath,
        retryMax: 0
      });

      let attempts = 0;
      nock(baseURL)
        .get(`${apiPath}/health`)
        .times(1)
        .reply(() => {
          attempts++;
          return [503, 'Service Unavailable'];
        });

      await expect(noRetryClient.health()).rejects.toThrow();
      expect(attempts).toBe(1);
    });
  });

  describe('custom requests', () => {
    it('should allow custom requests', async () => {
      const customResponse = { custom: 'data' };

      nock(baseURL)
        .get(`${apiPath}/custom/endpoint`)
        .reply(200, customResponse);

      const result = await client.request<typeof customResponse>({
        method: 'GET',
        url: '/custom/endpoint'
      });

      expect(result).toEqual(customResponse);
    });
  });
});