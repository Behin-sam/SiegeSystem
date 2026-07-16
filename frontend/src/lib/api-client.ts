import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";

import { getAccessToken, getRefreshToken, setTokens, clearTokens } from "@/lib/auth";

/**
 * Shared Axios instance for all backend calls. Requests are routed through
 * Next.js rewrites (see next.config.ts) so the browser only ever talks to
 * same-origin `/api/*`. A response interceptor performs a single silent
 * refresh-token retry on 401s before giving up and clearing the session.
 */
export const apiClient = axios.create({
  baseURL: "/api/v1",
  headers: { "Content-Type": "application/json" },
});

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let isRefreshing = false;
let pendingQueue: Array<() => void> = [];

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined;

    if (error.response?.status !== 401 || !originalRequest || originalRequest._retry) {
      return Promise.reject(error);
    }

    const refreshToken = getRefreshToken();
    if (!refreshToken) {
      clearTokens();
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    if (isRefreshing) {
      return new Promise((resolve) => {
        pendingQueue.push(() => resolve(apiClient(originalRequest)));
      });
    }

    try {
      isRefreshing = true;
      const { data } = await apiClient.post("/auth/refresh", null, {
        params: { refresh_token: refreshToken },
      });
      setTokens(data.access_token, data.refresh_token);
      pendingQueue.forEach((run) => run());
      pendingQueue = [];
      return apiClient(originalRequest);
    } catch (refreshError) {
      clearTokens();
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);
