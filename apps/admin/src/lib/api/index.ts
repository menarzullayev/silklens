export { apiFetch, type ApiRequest } from './client';
export {
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

export * as heritageApi from './heritage';
export * as tenantsApi from './tenants';
export * as systemApi from './system';
export * as aiApi from './ai';
export * as vocabApi from './vocab';
export * as reviewsApi from './reviews';
