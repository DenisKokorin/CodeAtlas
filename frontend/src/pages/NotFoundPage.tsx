import { Link } from "react-router-dom";
import Layout from "../components/Layout";
import type { UserRole } from "../api/authApi";

type NotFoundPageProps = {
  theme: "dark" | "light";
  toggleTheme: () => void;
  isAuthenticated: boolean;
  userEmail?: string | null;
  userRole: UserRole | null;
  onLogout: () => void;
};

function NotFoundPage({ theme, toggleTheme, isAuthenticated, userEmail, userRole, onLogout }: NotFoundPageProps) {
  return (
    <Layout navType="public" theme={theme} toggleTheme={toggleTheme} isAuthenticated={isAuthenticated} userEmail={userEmail} userRole={userRole} onLogout={onLogout}>
      <div className="card centered-card">
        <h2>Страница не найдена</h2>
        <p>Такого раздела в CodeAtlas нет.</p>
        <Link className="primary-button" to={isAuthenticated ? "/repositories" : "/"}>Вернуться</Link>
      </div>
    </Layout>
  );
}

export default NotFoundPage;
