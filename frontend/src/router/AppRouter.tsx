import { Navigate, Route, Routes } from "react-router-dom";
import HomePage from "../pages/HomePage";
import LoginPage from "../pages/LoginPage";
import RegisterPage from "../pages/RegisterPage";
import RepositoriesPage from "../pages/RepositoriesPage";
import AddRepositoryPage from "../pages/AddRepositoryPage";
import EditRepositoryPage from "../pages/EditRepositoryPage";
import RepositoryDetailsPage from "../pages/RepositoryDetailsPage";
import NotFoundPage from "../pages/NotFoundPage";
import type { UserRole } from "../api/authApi";

type AppRouterProps = {
  theme: "dark" | "light";
  toggleTheme: () => void;
  token: string | null;
  userEmail: string | null;
  userRole: UserRole | null;
  isAuthenticated: boolean;
  onLogin: (
    accessToken: string,
    refreshToken: string,
    email: string,
    role: UserRole
  ) => void;
  onLogout: () => void;
};

function AppRouter(props: AppRouterProps) {
  const {
    theme,
    toggleTheme,
    token,
    userEmail,
    userRole,
    isAuthenticated,
    onLogin,
    onLogout,
  } = props;

  const appProps = { theme, toggleTheme, userEmail, userRole, onLogout };

  return (
    <Routes>
      <Route
        path="/"
        element={
          <HomePage
            theme={theme}
            toggleTheme={toggleTheme}
            isAuthenticated={isAuthenticated}
            userEmail={userEmail}
            userRole={userRole}
            onLogout={onLogout}
          />
        }
      />
      <Route
        path="/login"
        element={<LoginPage theme={theme} toggleTheme={toggleTheme} onLogin={onLogin} />}
      />
      <Route
        path="/register"
        element={<RegisterPage theme={theme} toggleTheme={toggleTheme} onLogin={onLogin} />}
      />
      <Route
        path="/repositories"
        element={isAuthenticated && token ? <RepositoriesPage {...appProps} /> : <Navigate to="/login" replace />}
      />
      <Route
        path="/repositories/new"
        element={isAuthenticated && token ? <AddRepositoryPage {...appProps} /> : <Navigate to="/login" replace />}
      />
      <Route
        path="/repositories/:id"
        element={isAuthenticated && token ? <RepositoryDetailsPage {...appProps} /> : <Navigate to="/login" replace />}
      />
      <Route
        path="/repositories/:id/edit"
        element={isAuthenticated && token ? <EditRepositoryPage {...appProps} /> : <Navigate to="/login" replace />}
      />
      <Route
        path="*"
        element={
          <NotFoundPage
            theme={theme}
            toggleTheme={toggleTheme}
            isAuthenticated={isAuthenticated}
            userEmail={userEmail}
            userRole={userRole}
            onLogout={onLogout}
          />
        }
      />
    </Routes>
  );
}

export default AppRouter;
