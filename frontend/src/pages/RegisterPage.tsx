import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import Layout from "../components/Layout";
import SEO from "../components/SEO";
import { registerUser, type UserRole } from "../api/authApi";

type RegisterPageProps = {
  theme: "dark" | "light";
  toggleTheme: () => void;
  onLogin: (
    accessToken: string,
    refreshToken: string,
    email: string,
    role: UserRole
  ) => void;
};

function RegisterPage({ theme, toggleTheme, onLogin }: RegisterPageProps) {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      const result = await registerUser({ username, email, password });
      onLogin(
        result.access_token,
        result.refresh_token,
        result.user.email,
        result.user.role
      );
      navigate("/repositories");
    } catch {
      setError("Не удалось зарегистрироваться. Проверьте данные или попробуйте другую почту.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Layout title="Регистрация" navType="auth" theme={theme} toggleTheme={toggleTheme}>
      <SEO title="Регистрация" description="Регистрация в CodeAtlas." />

      <form className="form-card" onSubmit={handleSubmit}>
        <label>Имя пользователя</label>
        <input
          type="text"
          placeholder="Например, mikhail"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
        />

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
          placeholder="Минимум 6 символов"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />

        {error && <p className="form-error">{error}</p>}

        <button className="primary-button" type="submit" disabled={isLoading}>
          {isLoading ? "Регистрация..." : "Зарегистрироваться"}
        </button>

        <p className="auth-hint">
          <span className="auth-hint-text">Уже есть аккаунт? </span>
          <Link to="/login" className="auth-hint-link">Войти</Link>
        </p>
      </form>
    </Layout>
  );
}

export default RegisterPage;
