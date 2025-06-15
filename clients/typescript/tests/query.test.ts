import nock from 'nock';
import { UDSClient } from '../src/client';
import { QueryRequest, QueryResponse } from '../src/types';

describe('QueryService', () => {
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

  describe('execute', () => {
    it('should execute a query', async () => {
      const request: QueryRequest = {
        query: 'SELECT * FROM Transaction LIMIT 10',
        timeRange: {
          from: '2024-01-01T00:00:00Z',
          to: '2024-12-31T23:59:59Z'
        },
        options: {
          timeout: 30000,
          maxResults: 10
        }
      };

      const response: QueryResponse = {
        results: [
          {
            data: [
              { timestamp: '2024-01-01T10:00:00Z', duration: 100 },
              { timestamp: '2024-01-01T10:01:00Z', duration: 120 }
            ],
            columns: [
              { name: 'timestamp', type: 'timestamp' },
              { name: 'duration', type: 'number' }
            ]
          }
        ],
        metadata: {
          executionTime: '150ms',
          bytesProcessed: 1024000
        }
      };

      nock(baseURL)
        .post(`${apiPath}/query`, (body: any) => {
          return JSON.stringify(body) === JSON.stringify(request);
        })
        .reply(200, response);

      const result = await client.query.execute(request);
      expect(result).toEqual(response);
    });
  });

  describe('validate', () => {
    it('should validate a valid query', async () => {
      const query = 'SELECT * FROM Transaction WHERE duration > 100';
      const validation = {
        valid: true,
        warnings: ['Consider adding a time range for better performance']
      };

      nock(baseURL)
        .post(`${apiPath}/query/validate`, { query })
        .reply(200, validation);

      const result = await client.query.validate(query);
      expect(result).toEqual(validation);
    });

    it('should validate an invalid query', async () => {
      const query = 'SELECT * FORM Transaction';
      const validation = {
        valid: false,
        errors: [
          {
            line: 1,
            column: 10,
            message: "Unexpected token 'FORM', expected 'FROM'"
          }
        ]
      };

      nock(baseURL)
        .post(`${apiPath}/query/validate`, { query })
        .reply(200, validation);

      const result = await client.query.validate(query);
      expect(result).toEqual(validation);
    });
  });

  describe('suggest', () => {
    it('should get query suggestions', async () => {
      const suggestions = {
        suggestions: [
          {
            text: 'SELECT',
            type: 'keyword',
            description: 'Select statement'
          },
          {
            text: 'SET',
            type: 'keyword',
            description: 'Set variable'
          }
        ]
      };

      nock(baseURL)
        .post(`${apiPath}/query/suggest`, {
          partial: 'SE',
          eventType: 'Transaction',
          cursorPosition: 2
        })
        .reply(200, suggestions);

      const result = await client.query.suggest('SE', {
        eventType: 'Transaction',
        cursorPosition: 2
      });
      expect(result).toEqual(suggestions);
    });
  });

  describe('format', () => {
    it('should format a query', async () => {
      const unformatted = 'select * from Transaction where duration>100 limit 10';
      const formatted = {
        formatted: 'SELECT *\nFROM Transaction\nWHERE duration > 100\nLIMIT 10',
        changed: true
      };

      nock(baseURL)
        .post(`${apiPath}/query/format`, { query: unformatted })
        .reply(200, formatted);

      const result = await client.query.format(unformatted);
      expect(result).toEqual(formatted);
    });
  });

  describe('getHistory', () => {
    it('should get query history', async () => {
      const history = {
        queries: [
          {
            id: 'q123',
            query: 'SELECT * FROM Transaction',
            executedAt: '2024-12-01T10:00:00Z',
            executionTime: '120ms',
            resultCount: 1000,
            user: 'user@example.com'
          }
        ],
        total: 1
      };

      nock(baseURL)
        .get(`${apiPath}/query/history`)
        .query({
          limit: '10',
          offset: '0',
          from: '2024-12-01T00:00:00Z',
          to: '2024-12-31T23:59:59Z'
        })
        .reply(200, history);

      const result = await client.query.getHistory({
        limit: 10,
        offset: 0,
        timeRange: {
          from: '2024-12-01T00:00:00Z',
          to: '2024-12-31T23:59:59Z'
        }
      });
      expect(result).toEqual(history);
    });
  });

  describe('export', () => {
    it('should export query results', async () => {
      const csvData = 'timestamp,duration\n2024-01-01T10:00:00Z,100\n';

      nock(baseURL)
        .get(`${apiPath}/query/q123/export`)
        .query({ format: 'csv' })
        .reply(200, csvData, {
          'Content-Type': 'text/csv'
        });

      // Note: In a real browser environment, this would return a Blob
      // In Node.js test environment, we get the raw response
      const result = await client.query.export('q123', 'csv');
      expect(result).toBeDefined();
    });
  });
});