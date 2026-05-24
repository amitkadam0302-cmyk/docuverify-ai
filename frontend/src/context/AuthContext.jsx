import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { getMe, login as loginRequest, register as registerRequest } from "../services/api.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(localStorage.getItem("docuverify_token"));
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(Boolean(token));

  useEffect(() => {
    let active = true;
    if (!token) {
      setLoading(false);
      return () => {
        active = false;
      };
    }

    setLoading(true);
    getMe()
      .then((response) => {
        if (active) setUser(response.data);
      })
      .catch(() => {
        localStorage.removeItem("docuverify_token");
        if (active) {
          setToken(null);
          setUser(null);
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [token]);

  useEffect(() => {
    function handleExpired() {
      localStorage.removeItem("docuverify_token");
      setToken(null);
      setUser(null);
      setLoading(false);
    }
    window.addEventListener("docuverify:auth-expired", handleExpired);
    return () => window.removeEventListener("docuverify:auth-expired", handleExpired);
  }, []);

  async function login(email, password) {
    const response = await loginRequest(email.trim().toLowerCase(), password);
    localStorage.setItem("docuverify_token", response.data.access_token);
    setToken(response.data.access_token);
    setUser(response.data.user);
    return response.data.user;
  }

  async function register(payload) {
    return registerRequest(payload);
  }

  function logout() {
    localStorage.removeItem("docuverify_token");
    setToken(null);
    setUser(null);
  }

  async function refreshUser() {
    const response = await getMe();
    setUser(response.data);
    return response.data;
  }

  const value = useMemo(
    () => ({ token, user, loading, isAuthenticated: Boolean(token), login, register, logout, refreshUser }),
    [token, user, loading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
