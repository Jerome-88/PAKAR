import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import type { ReactNode } from "react";
import {
  ApiError,
  getCurrentUser,
  loginUser,
  logoutUser,
  registerUser,
} from "../api/client";
import type { AuthUser } from "../api/client";
import { AuthContext } from "./auth-context";
import type { AuthContextValue } from "./auth-context";
import { setAuthStorageNamespace } from "./storageNamespace";
import { publicDemoOnly } from "../config/publicDemo";

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(!publicDemoOnly);
  const [connectionError, setConnectionError] = useState("");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (publicDemoOnly) return;
    let active = true;
    getCurrentUser()
      .then((currentUser) => {
        if (!active) return;
        setAuthStorageNamespace(currentUser.id);
        setUser(currentUser);
      })
      .catch((error: unknown) => {
        if (error instanceof ApiError && error.status === 401) return;
        setConnectionError(error instanceof Error ? error.message : "Backend belum dapat dihubungi.");
      })
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [attempt]);

  useEffect(() => {
    const expireSession = () => {
      queryClient.clear();
      setAuthStorageNamespace(null);
      setUser(null);
    };
    window.addEventListener("auth-session-expired", expireSession);
    return () => window.removeEventListener("auth-session-expired", expireSession);
  }, [queryClient]);

  const establishSession = (currentUser: AuthUser) => {
    queryClient.clear();
    setAuthStorageNamespace(currentUser.id);
    setUser(currentUser);
    return currentUser;
  };

  const value: AuthContextValue = {
    user,
    loading,
    connectionError,
    retryConnection: () => { setLoading(true); setConnectionError(""); setAttempt(value => value + 1); },
    login: (input) => loginUser(input).then(establishSession),
    register: (input) => registerUser(input).then(establishSession),
    logout: async () => {
      await logoutUser();
      queryClient.clear();
      setAuthStorageNamespace(null);
      setUser(null);
    },
  };

  return <AuthContext value={value}>{children}</AuthContext>;
}
