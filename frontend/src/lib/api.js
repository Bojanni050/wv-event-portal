import axios from "axios";

export const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
export const api = axios.create({ baseURL: API, withCredentials: true });

let refreshing = null;
api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config;
    const isAuthCall = original?.url?.startsWith("/auth/");
    if (error.response?.status === 401 && original && !original._retry && !isAuthCall) {
      original._retry = true;
      refreshing = refreshing || api.post("/auth/refresh").finally(() => (refreshing = null));
      try {
        await refreshing;
        return api(original);
      } catch {
        window.dispatchEvent(new Event("wv:logout"));
      }
    }
    return Promise.reject(error);
  }
);

export function errorMessage(e) {
  const detail = e?.response?.data?.detail;
  if (detail == null) return e?.message || "Er ging iets mis. Probeer het opnieuw.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => d?.msg || JSON.stringify(d)).join(" ");
  return detail.msg || String(detail);
}

export const fileUrl = (id) => `${API}/files/${id}/download`;
