import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, getToken, setToken } from "../api/client";
import type { Meta, User } from "../api/types";

interface AuthState {
  user: User | null;
  meta: Meta | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  demoLogin: (username: string) => Promise<void>;
  logout: () => void;
  can: (permission: string) => boolean;
}

const Ctx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<Meta>("/api/meta").then(setMeta).catch(() => setMeta(null));
    if (!getToken()) {
      setLoading(false);
      return;
    }
    api
      .get<User>("/api/auth/me")
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const onUnauth = () => {
      setToken(null);
      setUser(null);
    };
    window.addEventListener("georevive:unauthorised", onUnauth);
    return () => window.removeEventListener("georevive:unauthorised", onUnauth);
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const r = await api.post<{ token: string; user: User }>("/api/auth/login", { username, password });
    setToken(r.token);
    setUser(r.user);
  }, []);

  const demoLogin = useCallback(async (username: string) => {
    const r = await api.post<{ token: string; user: User }>("/api/auth/demo-login", { username });
    setToken(r.token);
    setUser(r.user);
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  const can = useCallback((p: string) => !!user && user.permissions.includes(p), [user]);

  return (
    <Ctx.Provider value={{ user, meta, loading, login, demoLogin, logout, can }}>{children}</Ctx.Provider>
  );
}

export function useAuth(): AuthState {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth must be used inside AuthProvider");
  return v;
}
