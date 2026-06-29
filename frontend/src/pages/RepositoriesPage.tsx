import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import Layout from "../components/Layout";
import type { UserRole } from "../api/authApi";
import { deleteRepository, getRepositories, type Repository } from "../api/repositoriesApi";

type RepositoriesPageProps = {
  theme: "dark" | "light";
  toggleTheme: () => void;
  userEmail: string | null;
  onLogout: () => void;
  userRole: UserRole | null;
};

function RepositoriesPage({ theme, toggleTheme, userEmail, onLogout, userRole }: RepositoriesPageProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState(searchParams.get("search") ?? "");
  const [status, setStatus] = useState(searchParams.get("status") ?? "");
  const [sortBy, setSortBy] = useState(searchParams.get("sort_by") ?? "id");
  const [sortOrder, setSortOrder] = useState(searchParams.get("sort_order") ?? "desc");
  const [pageSize, setPageSize] = useState(Number(searchParams.get("page_size") ?? 5));
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  const page = Number(searchParams.get("page") ?? 1);

  const loadRepositories = async () => {
    setIsLoading(true);
    setError("");

    try {
      const data = await getRepositories({
        search: searchParams.get("search") ?? undefined,
        status: searchParams.get("status") ?? undefined,
        sort_by: searchParams.get("sort_by") ?? "id",
        sort_order: searchParams.get("sort_order") ?? "desc",
        page,
        page_size: Number(searchParams.get("page_size") ?? 5),
      });
      setRepositories(data.items);
      setTotal(data.total);
    } catch {
      setError("Не удалось загрузить список репозиториев.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadRepositories();
  }, [searchParams]);

  const handleApplyFilters = () => {
    const params: Record<string, string> = {
      page: "1",
      page_size: String(pageSize),
      sort_by: sortBy,
      sort_order: sortOrder,
    };
    if (search.trim()) params.search = search.trim();
    if (status) params.status = status;
    setSearchParams(params);
  };

  const handleResetFilters = () => {
    setSearch("");
    setStatus("");
    setSortBy("id");
    setSortOrder("desc");
    setPageSize(5);
    setSearchParams({ page: "1", page_size: "5", sort_by: "id", sort_order: "desc" });
  };

  const handleDelete = async (repositoryId: number) => {
    if (!confirm("Удалить этот репозиторий?")) return;
    try {
      await deleteRepository(repositoryId);
      await loadRepositories();
    } catch {
      setError("Не удалось удалить репозиторий.");
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <Layout title="Мои репозитории" navType="app" theme={theme} toggleTheme={toggleTheme} userEmail={userEmail} userRole={userRole} onLogout={onLogout}>
      <div className="section-top section-top-split">
        <div>
          <p className="section-kicker">Workspace</p>
          <h2>Репозитории для анализа</h2>
          <p>Добавляйте GitHub-проекты, генерируйте документацию и отслеживайте версии.</p>
        </div>
        <Link to="/repositories/new" className="primary-button">Добавить репозиторий</Link>
      </div>

      <div className="card filter-card">
        <h3>Фильтрация и сортировка</h3>
        <div className="form-grid">
          <div>
            <label>Поиск</label>
            <input type="text" placeholder="Название, ссылка или описание" value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
          <div>
            <label>Статус</label>
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">Все статусы</option>
              <option value="new">new</option>
              <option value="processing">processing</option>
              <option value="ready">ready</option>
              <option value="error">error</option>
            </select>
          </div>
          <div>
            <label>Сортировать по</label>
            <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
              <option value="id">ID</option>
              <option value="name">Название</option>
              <option value="status">Статус</option>
              <option value="created_at">Дата создания</option>
              <option value="documentation_updated_at">Дата документации</option>
            </select>
          </div>
          <div>
            <label>Порядок</label>
            <select value={sortOrder} onChange={(e) => setSortOrder(e.target.value)}>
              <option value="desc">По убыванию</option>
              <option value="asc">По возрастанию</option>
            </select>
          </div>
        </div>

        <div className="button-group">
          <button type="button" className="primary-button" onClick={handleApplyFilters}>Применить</button>
          <button type="button" className="secondary-button" onClick={handleResetFilters}>Сбросить</button>
        </div>
      </div>

      {isLoading && <p className="state-message">Загрузка репозиториев...</p>}
      {error && <p className="form-error">{error}</p>}

      {!isLoading && !error && repositories.length === 0 && (
        <div className="card">
          <h3>Репозитории не найдены</h3>
          <p>Добавьте первый репозиторий или измените параметры поиска.</p>
        </div>
      )}

      {!isLoading && !error && repositories.length > 0 && (
        <>
          <p className="state-message">Найдено записей: {total}. Страница {page} из {totalPages}.</p>
          <div className="repo-list">
            {repositories.map((repository) => (
              <div className="repo-card" key={repository.id}>
                <div className="repo-card-head">
                  <div>
                    <h3>{repository.name}</h3>
                    <p>{repository.description ?? "Описание не указано"}</p>
                  </div>
                  <span className={`status-pill status-${repository.status}`}>{repository.status}</span>
                </div>
                <p className="mono-link">{repository.repo_url}</p>
                {repository.documentation_updated_at && (
                  <p>Последняя документация: {new Date(repository.documentation_updated_at).toLocaleString("ru-RU")}</p>
                )}
                <div className="button-group">
                  <Link to={`/repositories/${repository.id}`} className="secondary-button">Открыть</Link>
                  <Link to={`/repositories/${repository.id}/edit`} className="secondary-button">Редактировать</Link>
                  <button type="button" className="nav-logout" onClick={() => handleDelete(repository.id)}>Удалить</button>
                </div>
              </div>
            ))}
          </div>
          <div className="button-group">
            <button className="secondary-button" disabled={page <= 1} onClick={() => setSearchParams(new URLSearchParams({ ...Object.fromEntries(searchParams), page: String(page - 1) }))}>Назад</button>
            <button className="secondary-button" disabled={page >= totalPages} onClick={() => setSearchParams(new URLSearchParams({ ...Object.fromEntries(searchParams), page: String(page + 1) }))}>Вперёд</button>
          </div>
        </>
      )}
    </Layout>
  );
}

export default RepositoriesPage;
