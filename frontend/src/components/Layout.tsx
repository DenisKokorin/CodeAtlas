import type { ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import type { UserRole } from "../api/authApi";

type LayoutProps = {
  title?: string;
  children: ReactNode;
  navType: "public" | "auth" | "app";
  theme: "dark" | "light";
  toggleTheme: () => void;
  isAuthenticated?: boolean;
  userEmail?: string | null;
  userRole?: UserRole | null;
  onLogout?: () => void;
};

function Layout({
  title,
  children,
  navType,
  theme,
  toggleTheme,
  isAuthenticated = false,
  userEmail = null,
  userRole = null,
  onLogout,
}: LayoutProps) {
  const navigate = useNavigate();

  const handleLogoutClick = () => {
    if (onLogout) onLogout();
    navigate("/login");
  };

  return (
    <div className="page">
      <header className="header">
        <div className="header-inner">
          <div className="header-left">
            <Link to="/" className="logo">
              CodeAtlas
            </Link>

            <button
              type="button"
              className="theme-switch"
              onClick={toggleTheme}
              aria-label="Переключить тему"
            >
              <span className={`theme-switch-track ${theme === "light" ? "light" : ""}`}>
                <span className="theme-switch-thumb" />
              </span>
              <span className="theme-switch-label">
                {theme === "dark" ? "Тёмная" : "Светлая"}
              </span>
            </button>
          </div>

          {title && <h1 className="page-title">{title}</h1>}

          <nav className="nav">
            {navType === "public" && !isAuthenticated && (
              <>
                <Link to="/login">Войти</Link>
                <Link to="/register" className="nav-button">Регистрация</Link>
              </>
            )}

            {((navType === "public" && isAuthenticated) || navType === "app") && (
              <>
                <Link to="/repositories">Мои репозитории</Link>
                {userEmail && (
                  <span className="user-email">
                    {userEmail} · {userRole ?? "user"}
                  </span>
                )}
                <button type="button" className="nav-logout" onClick={handleLogoutClick}>
                  Выйти
                </button>
              </>
            )}

            {navType === "auth" && (
              <>
                <Link to="/">Главная</Link>
                <Link to="/login">Войти</Link>
                <Link to="/register" className="nav-button">Регистрация</Link>
              </>
            )}
          </nav>
        </div>
      </header>

      <main className="content">{children}</main>
    </div>
  );
}

export default Layout;
