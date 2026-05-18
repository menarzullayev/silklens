/**
 * Typed error hierarchy for SilkLens API calls.
 *
 * Routes / Server Components / Client Components can `instanceof`-check the
 * concrete subclass to render the right UI (e.g. 404 → "not found" page,
 * 403 → "access denied" page) without parsing strings.
 */
export class ApiError extends Error {
  override readonly name: string = 'ApiError';
  readonly status: number;
  readonly body: unknown;
  readonly path: string;

  constructor(message: string, status: number, body: unknown, path: string) {
    super(message);
    this.status = status;
    this.body = body;
    this.path = path;
  }
}

export class NotFoundError extends ApiError {
  override readonly name = 'NotFoundError';
}

export class UnauthorizedError extends ApiError {
  override readonly name = 'UnauthorizedError';
}

export class ForbiddenError extends ApiError {
  override readonly name = 'ForbiddenError';
}

export class ValidationError extends ApiError {
  override readonly name = 'ValidationError';
}

export class ConflictError extends ApiError {
  override readonly name = 'ConflictError';
}

export class ServerError extends ApiError {
  override readonly name = 'ServerError';
}

export class NetworkError extends ApiError {
  override readonly name = 'NetworkError';
}

export function errorForStatus(
  status: number,
  body: unknown,
  path: string,
  message: string,
): ApiError {
  switch (status) {
    case 401:
      return new UnauthorizedError(message, status, body, path);
    case 403:
      return new ForbiddenError(message, status, body, path);
    case 404:
      return new NotFoundError(message, status, body, path);
    case 409:
      return new ConflictError(message, status, body, path);
    case 422:
      return new ValidationError(message, status, body, path);
    default:
      if (status >= 500) return new ServerError(message, status, body, path);
      return new ApiError(message, status, body, path);
  }
}
