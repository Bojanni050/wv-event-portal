import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api } from "@/lib/api";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);

  const loadMe = useCallback(async () => {
    try {
      const { data } = await api.get("/auth/me");
      setUser(data);
    } catch {
      try {
        await api.post("/auth/refresh");
        const { data } = await api.get("/auth/me");
        setUser(data);
      } catch {
        setUser(false);
      }
    }
  }, []);

  useEffect(() => {
    loadMe();
    const onLogout = () => setUser(false);
    window.addEventListener("wv:logout", onLogout);
    return () => window.removeEventListener("wv:logout", onLogout);
  }, [loadMe]);

  const login = async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    setUser(data);
    return data;
  };

  const logout = async () => {
    await api.post("/auth/logout").catch(() => {});
    setUser(false);
  };

  const isStaff = !!user && ["admin", "dj"].includes(user.role);
  return <AuthCtx.Provider value={{ user, login, logout, isStaff }}>{children}</AuthCtx.Provider>;
}

export const useAuth = () => useContext(AuthCtx);
