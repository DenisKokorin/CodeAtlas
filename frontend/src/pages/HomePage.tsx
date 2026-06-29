import { Link } from "react-router-dom";
import Layout from "../components/Layout";
import SEO from "../components/SEO";
import type { UserRole } from "../api/authApi";

type HomePageProps = {
  theme: "dark" | "light";
  toggleTheme: () => void;
  isAuthenticated: boolean;
  userEmail?: string | null;
  onLogout: () => void;
  userRole: UserRole | null;
};

function HomePage({
  theme,
  toggleTheme,
  isAuthenticated,
  userEmail,
  onLogout,
  userRole,
}: HomePageProps) {
  return (
    <Layout
      navType="public"
      theme={theme}
      toggleTheme={toggleTheme}
      isAuthenticated={isAuthenticated}
      userEmail={userEmail}
      userRole={userRole}
      onLogout={onLogout}
    >
      <SEO
        title="Главная"
        description="CodeAtlas помогает понимать структуру GitHub-репозитория, генерировать документацию и оценивать качество проекта."
      />

      <section className="hero">
        <div className="hero-text">
          <p className="hero-badge">Понимай систему целиком</p>

          <h1>Генерация документации для GitHub-репозиториев с помощью ИИ</h1>

          <p className="hero-description">
            Добавьте ссылку на репозиторий, укажите версию приложения и получите
            техническую документацию, Business Summary, критичные части проекта и
            оценку качества в одном рабочем пространстве.
          </p>

          <div className="hero-actions">
            <Link
              to={isAuthenticated ? "/repositories" : "/register"}
              className="primary-button"
            >
              {isAuthenticated ? "Перейти к репозиториям" : "Начать работу"}
            </Link>

            {!isAuthenticated && (
              <Link to="/login" className="secondary-button">
                Войти
              </Link>
            )}
          </div>
        </div>

        <div className="hero-demo">
          <div className="demo-window">
            <div className="demo-header">
              <span />
              <span />
              <span />
            </div>

            <div className="demo-body">
              <p><strong>Repository URL</strong></p>
              <div className="demo-input">https://github.com/team/product</div>

              <p><strong>App version</strong></p>
              <div className="demo-status">1.0.0 → revision 1</div>

              <p><strong>Результат</strong></p>
              <div className="demo-docs">
                CodeAtlas сформировал документацию, summary для руководителя и
                dashboard с оценкой инфраструктуры проекта.
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="features">
        <div className="feature-card">
          <h3>1. Добавьте репозиторий</h3>
          <p>Укажите ссылку на GitHub и сохраните проект в личном кабинете.</p>
        </div>

        <div className="feature-card">
          <h3>2. Укажите версию</h3>
          <p>Документация хранится по версиям приложения и ревизиям.</p>
        </div>

        <div className="feature-card">
          <h3>3. Получите анализ</h3>
          <p>Сервис показывает документацию, summary, критичные части и оценку проекта.</p>
        </div>
      </section>
    </Layout>
  );
}

export default HomePage;
