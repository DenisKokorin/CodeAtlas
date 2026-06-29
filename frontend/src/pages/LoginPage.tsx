import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import Layout from "../components/Layout";
import SEO from "../components/SEO";
import { loginUser, type UserRole } from "../api/authApi";

type LoginPageProps = {
  theme: "dark" | "light";
  toggleTheme: () => void;
  onLogin: (
    accessToken: string,
    refreshToken: string,
    email: string,
    role: UserRole
  ) => void;
};

function LoginPage({ theme, toggleTheme, onLogin }: LoginPageProps) {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      const result = await loginUser({ email, password });
      onLogin(
        result.access_token,
        result.refresh_token,
        result.user.email,
        result.user.role
      );
      navigate("/repositories");
    } catch {
      setError("Не удалось войти. Проверьте почту и пароль.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Layout title="Авторизация" navType="auth" theme={theme} toggleTheme={toggleTheme}>
      <SEO title="Авторизация" description="Вход в CodeAtlas." />

      <form className="form-card" onSubmit={handleSubmit}>
        <label>Почта</label>
        <input
          type="email"
          placeholder="user@example.com"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />

        <label>Пароль</label>
        <input
          type="password"
          placeholder="Введите пароль"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />

        {error && <p className="form-error">{error}</p>}

        <button className="primary-button" type="submit" disabled={isLoading}>
          {isLoading ? "Вход..." : "Войти"}
        </button>

        <p className="auth-hint">
          <span className="auth-hint-text">Нет аккаунта? </span>
          <Link to="/register" className="auth-hint-link">Зарегистрироваться</Link>
        </p>
      </form>
    </Layout>
  );
}

export default LoginPage;
