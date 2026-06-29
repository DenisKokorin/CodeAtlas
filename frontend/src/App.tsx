import { BrowserRouter } from "react-router-dom";
import { useEffect, useState } from "react";
import AppRouter from "./router/AppRouter";
import { logoutUser, type UserRole } from "./api/authApi";

function App() {
  const [theme, setTheme] = useState<"dark" | "light">(() => {
    const savedTheme = localStorage.getItem("theme");
    return savedTheme === "dark" || savedTheme === "light" ? savedTheme : "light";
  });

  const [token, setToken] = useState<string | null>(
    localStorage.getItem("auth_token")
  );
  const [userEmail, setUserEmail] = useState<string | null>(
    localStorage.getItem("auth_email")
  );
  const [userRole, setUserRole] = useState<UserRole | null>(() => {
    const savedRole = localStorage.getItem("auth_role");
    return savedRole === "admin" || savedRole === "user" ? savedRole : null;
  });

  useEffect(() => {
    document.body.classList.remove("theme-dark", "theme-light");
    document.body.classList.add(theme === "dark" ? "theme-dark" : "theme-light");
    localStorage.setItem("theme", theme);
  }, [theme]);

  const handleLogin = (
    accessToken: string,
    refreshToken: string,
    email: string,
    role: UserRole
  ) => {
    localStorage.setItem("auth_token", accessToken);
    localStorage.setItem("refresh_token", refreshToken);
    localStorage.setItem("auth_email", email);
    localStorage.setItem("auth_role", role);
    setToken(accessToken);
    setUserEmail(email);
    setUserRole(role);
  };

  const handleLogout = async () => {
    const refreshToken = localStorage.getItem("refresh_token");
    if (refreshToken) {
      await logoutUser(refreshToken);
    }
    localStorage.removeItem("auth_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("auth_email");
    localStorage.removeItem("auth_role");
    setToken(null);
    setUserEmail(null);
    setUserRole(null);
  };

  return (
    <BrowserRouter>
      <AppRouter
        theme={theme}
        toggleTheme={() => setTheme((prev) => (prev === "dark" ? "light" : "dark"))}
        token={token}
        userEmail={userEmail}
        userRole={userRole}
        isAuthenticated={Boolean(token)}
        onLogin={handleLogin}
        onLogout={handleLogout}
      />
    </BrowserRouter>
  );
}

export default App;
