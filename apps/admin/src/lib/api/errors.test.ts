/**
 * Unit tests for src/lib/api/errors.ts
 *
 * Covers: ApiError base class, all subclasses, and the errorForStatus()
 * factory function that maps HTTP status codes to the right error type.
 */
import { describe, expect, it } from 'vitest';

import {
  ApiError,
  ConflictError,
  ForbiddenError,
  NetworkError,
  NotFoundError,
  ServerError,
  UnauthorizedError,
  ValidationError,
  errorForStatus,
} from './errors';

// ---------------------------------------------------------------------------
// Base class — ApiError
// ---------------------------------------------------------------------------

describe('ApiError', () => {
  const err = new ApiError('bad request', 400, { detail: 'oops' }, '/v1/test');

  it('is an instance of Error', () => {
    expect(err).toBeInstanceOf(Error);
  });

  it('stores the message', () => {
    expect(err.message).toBe('bad request');
  });

  it('stores the HTTP status', () => {
    expect(err.status).toBe(400);
  });

  it('stores the response body', () => {
    expect(err.body).toEqual({ detail: 'oops' });
  });

  it('stores the request path', () => {
    expect(err.path).toBe('/v1/test');
  });

  it('has name "ApiError"', () => {
    expect(err.name).toBe('ApiError');
  });
});

// ---------------------------------------------------------------------------
// Subclasses — instanceof chain + name property
// ---------------------------------------------------------------------------

describe('NotFoundError', () => {
  const err = new NotFoundError('not found', 404, null, '/v1/heritage/xyz');

  it('is instanceof ApiError', () => {
    expect(err).toBeInstanceOf(ApiError);
  });

  it('is instanceof NotFoundError', () => {
    expect(err).toBeInstanceOf(NotFoundError);
  });

  it('has name "NotFoundError"', () => {
    expect(err.name).toBe('NotFoundError');
  });

  it('is NOT instanceof UnauthorizedError', () => {
    expect(err).not.toBeInstanceOf(UnauthorizedError);
  });
});

describe('UnauthorizedError', () => {
  const err = new UnauthorizedError('unauthorized', 401, null, '/v1/auth/me');

  it('is instanceof ApiError', () => {
    expect(err).toBeInstanceOf(ApiError);
  });

  it('has name "UnauthorizedError"', () => {
    expect(err.name).toBe('UnauthorizedError');
  });
});

describe('ForbiddenError', () => {
  const err = new ForbiddenError('forbidden', 403, null, '/v1/admin/users');

  it('is instanceof ApiError', () => {
    expect(err).toBeInstanceOf(ApiError);
  });

  it('has name "ForbiddenError"', () => {
    expect(err.name).toBe('ForbiddenError');
  });
});

describe('ValidationError', () => {
  const body = [{ loc: ['name'], msg: 'field required' }];
  const err = new ValidationError('validation failed', 422, body, '/v1/heritage');

  it('is instanceof ApiError', () => {
    expect(err).toBeInstanceOf(ApiError);
  });

  it('stores the validation body', () => {
    expect(err.body).toEqual(body);
  });

  it('has name "ValidationError"', () => {
    expect(err.name).toBe('ValidationError');
  });
});

describe('ConflictError', () => {
  const err = new ConflictError('conflict', 409, null, '/v1/tenants');

  it('is instanceof ApiError', () => {
    expect(err).toBeInstanceOf(ApiError);
  });

  it('has name "ConflictError"', () => {
    expect(err.name).toBe('ConflictError');
  });
});

describe('ServerError', () => {
  const err = new ServerError('internal error', 500, null, '/v1/ai/chat');

  it('is instanceof ApiError', () => {
    expect(err).toBeInstanceOf(ApiError);
  });

  it('has name "ServerError"', () => {
    expect(err.name).toBe('ServerError');
  });
});

describe('NetworkError', () => {
  const err = new NetworkError('ECONNREFUSED', 0, null, '/v1/health');

  it('is instanceof ApiError', () => {
    expect(err).toBeInstanceOf(ApiError);
  });

  it('has name "NetworkError"', () => {
    expect(err.name).toBe('NetworkError');
  });
});

// ---------------------------------------------------------------------------
// errorForStatus() — factory mapping
// ---------------------------------------------------------------------------

describe('errorForStatus()', () => {
  const body = { detail: 'test' };
  const path = '/v1/test';
  const msg = 'test error';

  it('returns UnauthorizedError for 401', () => {
    const err = errorForStatus(401, body, path, msg);
    expect(err).toBeInstanceOf(UnauthorizedError);
    expect(err.status).toBe(401);
  });

  it('returns ForbiddenError for 403', () => {
    const err = errorForStatus(403, body, path, msg);
    expect(err).toBeInstanceOf(ForbiddenError);
    expect(err.status).toBe(403);
  });

  it('returns NotFoundError for 404', () => {
    const err = errorForStatus(404, body, path, msg);
    expect(err).toBeInstanceOf(NotFoundError);
    expect(err.status).toBe(404);
  });

  it('returns ConflictError for 409', () => {
    const err = errorForStatus(409, body, path, msg);
    expect(err).toBeInstanceOf(ConflictError);
    expect(err.status).toBe(409);
  });

  it('returns ValidationError for 422', () => {
    const err = errorForStatus(422, body, path, msg);
    expect(err).toBeInstanceOf(ValidationError);
    expect(err.status).toBe(422);
  });

  it('returns ServerError for 500', () => {
    const err = errorForStatus(500, body, path, msg);
    expect(err).toBeInstanceOf(ServerError);
    expect(err.status).toBe(500);
  });

  it('returns ServerError for 503', () => {
    const err = errorForStatus(503, body, path, msg);
    expect(err).toBeInstanceOf(ServerError);
    expect(err.status).toBe(503);
  });

  it('returns ServerError for any 5xx', () => {
    for (const code of [500, 501, 502, 503, 504, 599]) {
      expect(errorForStatus(code, body, path, msg)).toBeInstanceOf(ServerError);
    }
  });

  it('returns generic ApiError for 400', () => {
    const err = errorForStatus(400, body, path, msg);
    expect(err).toBeInstanceOf(ApiError);
    expect(err).not.toBeInstanceOf(ValidationError);
    expect(err).not.toBeInstanceOf(NotFoundError);
  });

  it('returns generic ApiError for unhandled 4xx codes', () => {
    const err = errorForStatus(429, body, path, msg);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(429);
  });

  it('propagates message, body, and path to the created error', () => {
    const err = errorForStatus(404, body, path, msg);
    expect(err.message).toBe(msg);
    expect(err.body).toBe(body);
    expect(err.path).toBe(path);
  });

  it('all returned errors are instances of ApiError (instanceof chain)', () => {
    const codes = [401, 403, 404, 409, 422, 500, 503, 400];
    for (const code of codes) {
      expect(errorForStatus(code, null, '/', '')).toBeInstanceOf(ApiError);
    }
  });
});
