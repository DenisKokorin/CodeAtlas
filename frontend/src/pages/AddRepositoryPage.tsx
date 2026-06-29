import { useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import Layout from "../components/Layout";
import type { UserRole } from "../api/authApi";
import { createRepository } from "../api/repositoriesApi";

type AddRepositoryPageProps = {
  theme: "dark" | "light";
  toggleTheme: () => void;
  userEmail: string | null;
  onLogout: () => void;
  userRole: UserRole | null;
};

function AddRepositoryPage({ theme, toggleTheme, userEmail, onLogout, userRole }: AddRepositoryPageProps) {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [repoUrl, setRepoUrl] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      const repository = await createRepository({ name, repo_url: repoUrl, description, status: "new" });
      navigate(`/repositories/${repository.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось добавить репозиторий.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Layout title="Добавить репозиторий" navType="app" theme={theme} toggleTheme={toggleTheme} userEmail={userEmail} userRole={userRole} onLogout={onLogout}>
      <form className="form-card" onSubmit={handleSubmit}>
        <label>Название репозитория</label>
        <input type="text" placeholder="CodeAtlas" value={name} onChange={(e) => setName(e.target.value)} />

        <label>Ссылка на GitHub</label>
        <input type="url" placeholder="https://github.com/username/repository" value={repoUrl} onChange={(e) => setRepoUrl(e.target.value)} />

        <label>Описание</label>
        <textarea placeholder="Кратко опишите назначение проекта" rows={5} value={description} onChange={(e) => setDescription(e.target.value)} />

        {error && <p className="form-error">{error}</p>}

        <button className="primary-button" type="submit" disabled={isLoading}>{isLoading ? "Сохранение..." : "Сохранить"}</button>
      </form>
    </Layout>
  );
}

export default AddRepositoryPage;
