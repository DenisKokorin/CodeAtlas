import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import Layout from "../components/Layout";
import type { UserRole } from "../api/authApi";
import { getRepositoryById, updateRepository } from "../api/repositoriesApi";

type EditRepositoryPageProps = {
  theme: "dark" | "light";
  toggleTheme: () => void;
  userEmail: string | null;
  onLogout: () => void;
  userRole: UserRole | null;
};

function EditRepositoryPage({ theme, toggleTheme, userEmail, onLogout, userRole }: EditRepositoryPageProps) {
  const { id } = useParams();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [repoUrl, setRepoUrl] = useState("");
  const [description, setDescription] = useState("");
  const [status, setStatus] = useState("new");
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const loadRepository = async () => {
      if (!id) {
        setError("Не указан идентификатор репозитория.");
        setIsLoading(false);
        return;
      }

      try {
        const repository = await getRepositoryById(id);
        setName(repository.name);
        setRepoUrl(repository.repo_url);
        setDescription(repository.description ?? "");
        setStatus(repository.status);
      } catch {
        setError("Не удалось загрузить данные репозитория.");
      } finally {
        setIsLoading(false);
      }
    };

    loadRepository();
  }, [id]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!id) return;

    setError("");
    setIsSaving(true);

    try {
      await updateRepository(Number(id), { name, description, status });
      navigate(`/repositories/${id}`);
    } catch {
      setError("Не удалось сохранить изменения.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Layout title="Редактировать репозиторий" navType="app" theme={theme} toggleTheme={toggleTheme} userEmail={userEmail} userRole={userRole} onLogout={onLogout}>
      {isLoading && <p className="state-message">Загрузка данных...</p>}
      {error && <p className="form-error">{error}</p>}

      {!isLoading && !error && (
        <form className="form-card" onSubmit={handleSubmit}>
          <label>Название репозитория</label>
          <input type="text" value={name} onChange={(e) => setName(e.target.value)} />

          <label>Ссылка на GitHub</label>
          <input className="readonly-input" type="text" value={repoUrl} readOnly />
          <p className="field-hint">Ссылка не редактируется, так как она определяет источник анализа.</p>

          <label>Статус</label>
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="new">new</option>
            <option value="processing">processing</option>
            <option value="ready">ready</option>
            <option value="error">error</option>
          </select>

          <label>Описание</label>
          <textarea rows={5} value={description} onChange={(e) => setDescription(e.target.value)} />

          <div className="button-group">
            <button className="primary-button" type="submit" disabled={isSaving}>{isSaving ? "Сохранение..." : "Сохранить изменения"}</button>
            <Link to={id ? `/repositories/${id}` : "/repositories"} className="secondary-button">Отмена</Link>
          </div>
        </form>
      )}
    </Layout>
  );
}

export default EditRepositoryPage;
