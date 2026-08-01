import createClient from 'openapi-fetch';
import type { paths } from './api-types';

export const api = createClient<paths>({
  baseUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
});

// Helper for extracting successful responses
export async function unwrap<T>(promise: Promise<{ data?: T; error?: unknown }>): Promise<T> {
  const { data, error } = await promise;
  if (error) {
    throw new Error(JSON.stringify(error));
  }
  return data as T;
}

