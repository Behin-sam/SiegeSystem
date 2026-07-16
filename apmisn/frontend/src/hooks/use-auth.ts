"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { apiClient } from "@/lib/api-client";
import { clearTokens, isAuthenticated, setTokens } from "@/lib/auth";
import type { LoginPayload, TokenResponse, User } from "@/types";

/** Fetches the currently authenticated user; disabled when no token is present. */
export function useCurrentUser() {
  return useQuery<User>({
    queryKey: ["auth", "me"],
    queryFn: async () => {
      const { data } = await apiClient.get<User>("/auth/me");
      return data;
    },
    enabled: isAuthenticated(),
    retry: false,
  });
}

/** Handles login submission, token persistence, and redirect to the dashboard. */
export function useLogin() {
  const router = useRouter();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: LoginPayload) => {
      const { data } = await apiClient.post<TokenResponse>("/auth/login", payload);
      return data;
    },
    onSuccess: async (data) => {
      setTokens(data.access_token, data.refresh_token);
      await queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
      router.push("/dashboard");
    },
  });
}

/** Clears session state and returns to the login screen. */
export function useLogout() {
  const router = useRouter();
  const queryClient = useQueryClient();

  return () => {
    clearTokens();
    queryClient.clear();
    router.push("/login");
  };
}
