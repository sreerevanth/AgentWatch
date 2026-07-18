import { createApiClient } from "react-query-ease";
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
export const api = createApiClient({ baseURL: API_BASE_URL });
