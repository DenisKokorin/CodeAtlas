import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import Layout from "../components/Layout";
import SEO from "../components/SEO";
import type { UserRole } from "../api/authApi";
import { getRepositoryGitHubInfo, type GitHubRepositoryInfo } from "../api/githubApi";
import {
  deleteRepository,
  downloadExport,
  generateDocumentation,
  getBusinessSummary,
  getCriticalParts,
  getDocumentationVersion,
  getDocumentationVersions,
  getLatestDocumentation,
  getQualityAssessment,
  getRepositoryById,
  type BusinessSummaryResponse,
  type CriticalPartsResponse,
  type DocumentationResponse,
  type DocumentationVersionListItem,
  type ExportFormat,
  type QualityAssessmentResponse,
  type Repository,
} from "../api/repositoriesApi";

type RepositoryDetailsPageProps = {
  theme: "dark" | "light";
  toggleTheme: () => void;
  userEmail: string | null;
  onLogout: () => void;
  userRole: UserRole | null;
};

type ActiveView = "documentation" | "summary" | "critical" | "quality" | "versions";

function safeDate(value?: string | null) {
  if (!value) return "не указано";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString("ru-RU");
}

function ListBlock({ title, items }: { title: string; items?: string[] }) {
  if (!items || items.length === 0) return null;

  return (
    <div className="mini-block">
      <h4>{title}</h4>
      <ul>
        {items.map((item, index) => <li key={`${title}-${index}`}>{item}</li>)}
      </ul>
    </div>
  );
}

function RepositoryDetailsPage({ theme, toggleTheme, userEmail, onLogout, userRole }: RepositoryDetailsPageProps) {
  const { id } = useParams();
  const navigate = useNavigate();
  const repositoryId = id ? Number(id) : null;

  const [repository, setRepository] = useState<Repository | null>(null);
  const [githubInfo, setGithubInfo] = useState<GitHubRepositoryInfo | null>(null);
  const [documentation, setDocumentation] = useState<DocumentationResponse | null>(null);
  const [versions, setVersions] = useState<DocumentationVersionListItem[]>([]);
  const [businessSummary, setBusinessSummary] = useState<BusinessSummaryResponse | null>(null);
  const [qualityAssessment, setQualityAssessment] = useState<QualityAssessmentResponse | null>(null);
  const [criticalParts, setCriticalParts] = useState<CriticalPartsResponse | null>(null);
  const [selectedVersionId, setSelectedVersionId] = useState<number | null>(null);
  const [activeView, setActiveView] = useState<ActiveView>("documentation");
  const [appVersion, setAppVersion] = useState("1.0.0");
  const [isLoading, setIsLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isGithubLoading, setIsGithubLoading] = useState(false);
  const [error, setError] = useState("");
  const [generationError, setGenerationError] = useState("");
  const [blockInfo, setBlockInfo] = useState("");

  const loadBlocks = async (versionId?: number) => {
    if (!repositoryId) return;

    setBlockInfo("");

    const [summaryResult, qualityResult, criticalResult] = await Promise.allSettled([
      getBusinessSummary(repositoryId, versionId),
      getQualityAssessment(repositoryId, versionId),
      getCriticalParts(repositoryId, versionId),
    ]);

    setBusinessSummary(summaryResult.status === "fulfilled" ? summaryResult.value : null);
    setQualityAssessment(qualityResult.status === "fulfilled" ? qualityResult.value : null);
    setCriticalParts(criticalResult.status === "fulfilled" ? criticalResult.value : null);

    if (
      summaryResult.status === "rejected" &&
      qualityResult.status === "rejected" &&
      criticalResult.status === "rejected"
    ) {
      setBlockInfo("Дополнительные блоки пока недоступны. Сгенерируйте документацию.");
    }
  };

  const loadRepository = async () => {
    if (!repositoryId) {
      setError("Не указан идентификатор репозитория.");
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError("");
    setGenerationError("");

    try {
      const repositoryData = await getRepositoryById(repositoryId);
      setRepository(repositoryData);

      const docsResult = await Promise.allSettled([
        getLatestDocumentation(repositoryId),
        getDocumentationVersions(repositoryId),
      ]);

      if (docsResult[0].status === "fulfilled") {
        setDocumentation(docsResult[0].value);
        setSelectedVersionId(null);
      } else {
        setDocumentation(null);
      }

      if (docsResult[1].status === "fulfilled") {
        setVersions(docsResult[1].value.items);
      } else {
        setVersions([]);
      }

      await loadBlocks();

      setIsGithubLoading(true);
      try {
        const githubData = await getRepositoryGitHubInfo(repositoryId);
        setGithubInfo(githubData);
      } catch {
        setGithubInfo(null);
      } finally {
        setIsGithubLoading(false);
      }
    } catch {
      setError("Не удалось загрузить данные репозитория.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadRepository();
  }, [id]);

  const handleGenerate = async () => {
    if (!repositoryId) return;

    setGenerationError("");
    setIsGenerating(true);

    try {
      const result = await generateDocumentation(repositoryId, appVersion);
      setDocumentation(result);
      setSelectedVersionId(null);
      await loadRepository();
      setActiveView("documentation");
    } catch (err) {
      setGenerationError(err instanceof Error ? err.message : "Не удалось сгенерировать документацию.");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSelectVersion = async (versionId: number) => {
    if (!repositoryId) return;

    try {
      const version = await getDocumentationVersion(repositoryId, versionId);
      setDocumentation({
        repository_id: repositoryId,
        documentation: version.documentation,
        provider: version.provider,
        updated_at: version.created_at,
        source_updated_at: version.source_updated_at,
        is_stale: false,
        documentation_version_id: version.id,
        app_version: version.app_version,
        revision_number: version.revision_number,
        display_name: version.display_name,
      });
      setSelectedVersionId(versionId);
      await loadBlocks(versionId);
      setActiveView("documentation");
    } catch {
      setGenerationError("Не удалось открыть выбранную версию документации.");
    }
  };

  const handleLatestVersion = async () => {
    setSelectedVersionId(null);
    await loadRepository();
    setActiveView("documentation");
  };

  const handleDelete = async () => {
    if (!repository || !confirm("Удалить этот репозиторий?")) return;

    try {
      await deleteRepository(repository.id);
      navigate("/repositories");
    } catch {
      setError("Не удалось удалить репозиторий.");
    }
  };

  const handleExport = async (format: ExportFormat) => {
    if (!repositoryId) return;

    try {
      await downloadExport(repositoryId, format, selectedVersionId ?? undefined);
    } catch {
      setGenerationError("Не удалось экспортировать документацию.");
    }
  };

  const quality = qualityAssessment?.quality_assessment;
  const scorePercent = quality ? Math.min(100, Math.max(0, (quality.score / quality.max_score) * 100)) : 0;

  return (
    <Layout title="Репозиторий" navType="app" theme={theme} toggleTheme={toggleTheme} userEmail={userEmail} userRole={userRole} onLogout={onLogout}>
      <SEO title={repository?.name ?? "Репозиторий"} description="Детальная страница репозитория в CodeAtlas." />

      <div className="section-top">
        <Link to="/repositories" className="back-link">&lt; Назад к списку</Link>
      </div>

      {isLoading && <p className="state-message">Загрузка репозитория...</p>}
      {error && <p className="form-error">{error}</p>}

      {!isLoading && !error && repository && (
        <>
          <div className="details-grid">
            <div className="card repo-main-card">
              <div className="repo-card-head">
                <div>
                  <p className="section-kicker">Repository</p>
                  <h2>{repository.name}</h2>
                </div>
                <span className={`status-pill status-${repository.status}`}>{repository.status}</span>
              </div>

              <p className="mono-link">{repository.repo_url}</p>
              {repository.description && <p>{repository.description}</p>}

              <div className="meta-grid">
                <div><strong>Provider</strong><span>{documentation?.provider ?? repository.documentation_provider ?? "—"}</span></div>
                <div><strong>App version</strong><span>{documentation?.app_version ?? "—"}</span></div>
                <div><strong>Revision</strong><span>{documentation?.revision_number ?? "—"}</span></div>
                <div><strong>Updated</strong><span>{safeDate(documentation?.updated_at ?? repository.documentation_updated_at)}</span></div>
              </div>

              <div className="button-group">
                <Link to={`/repositories/${repository.id}/edit`} className="secondary-button">Редактировать</Link>
                <button type="button" className="nav-logout" onClick={handleDelete}>Удалить</button>
              </div>
            </div>

            <div className="card generation-card">
              <h3>Генерация документации</h3>
              <p>Укажите версию приложения. Для той же версии будет создана новая ревизия.</p>
              <label>Версия приложения</label>
              <input value={appVersion} onChange={(e) => setAppVersion(e.target.value)} placeholder="1.0.0" />
              {generationError && <p className="form-error">{generationError}</p>}
              <button type="button" className="primary-button" disabled={isGenerating} onClick={handleGenerate}>
                {isGenerating ? "Генерация..." : "Сгенерировать"}
              </button>
            </div>
          </div>

          <div className="card">
            <h3>Информация из GitHub</h3>
            {isGithubLoading && <p className="state-message">Загрузка данных GitHub...</p>}
            {!isGithubLoading && !githubInfo && <p className="state-message">GitHub API сейчас недоступен или требуется token.</p>}
            {githubInfo && (
              <div className="meta-grid">
                <div><strong>Full name</strong><span>{githubInfo.full_name ?? "—"}</span></div>
                <div><strong>Language</strong><span>{githubInfo.language ?? "—"}</span></div>
                <div><strong>Stars</strong><span>{githubInfo.stars}</span></div>
                <div><strong>Forks</strong><span>{githubInfo.forks}</span></div>
                <div><strong>Issues</strong><span>{githubInfo.open_issues}</span></div>
                <div><strong>Default branch</strong><span>{githubInfo.default_branch ?? "—"}</span></div>
              </div>
            )}
          </div>

          <div className="tabs">
            <button className={activeView === "documentation" ? "active" : ""} onClick={() => setActiveView("documentation")}>Документация</button>
            <button className={activeView === "summary" ? "active" : ""} onClick={() => setActiveView("summary")}>Business Summary</button>
            <button className={activeView === "critical" ? "active" : ""} onClick={() => setActiveView("critical")}>Критичные части</button>
            <button className={activeView === "quality" ? "active" : ""} onClick={() => setActiveView("quality")}>Оценка проекта</button>
            <button className={activeView === "versions" ? "active" : ""} onClick={() => setActiveView("versions")}>Версии</button>
          </div>

          {blockInfo && <p className="state-message">{blockInfo}</p>}

          {activeView === "documentation" && (
            <div className="card">
              <div className="repo-card-head">
                <div>
                  <h3>{documentation?.display_name ?? "Сгенерированная документация"}</h3>
                  <p>Мультиформатный экспорт применяется только к основной документации.</p>
                </div>
                <div className="export-buttons">
                  {(["markdown", "txt", "html", "docx", "json"] as ExportFormat[]).map((format) => (
                    <button key={format} type="button" className="secondary-button" onClick={() => handleExport(format)} disabled={!documentation?.documentation}>
                      {format.toUpperCase()}
                    </button>
                  ))}
                </div>
              </div>

              {!documentation?.documentation && <p>Документация ещё не сгенерирована.</p>}
              {documentation?.documentation && (
                <div className="documentation-preview markdown-content">
                  <ReactMarkdown>{documentation.documentation}</ReactMarkdown>
                </div>
              )}
            </div>
          )}

          {activeView === "summary" && (
            <div className="card">
              <h3>{businessSummary?.business_summary.title ?? "Business Summary"}</h3>
              {!businessSummary && <p>Business Summary пока недоступен.</p>}
              {businessSummary && (
                <>
                  <p className="summary-text">{businessSummary.business_summary.text}</p>
                  <div className="two-columns">
                    <ListBlock title="Для кого полезно" items={businessSummary.business_summary.target_audience} />
                    <ListBlock title="Бизнес-ценность" items={businessSummary.business_summary.business_value} />
                  </div>
                </>
              )}
            </div>
          )}

          {activeView === "critical" && (
            <div className="card">
              <h3>{criticalParts?.critical_parts.title ?? "Критичные части проекта"}</h3>
              {!criticalParts && <p>Описание критичных частей пока недоступно.</p>}
              {criticalParts?.critical_parts.items?.map((part, index) => (
                <div className="critical-card" key={`${part.name}-${index}`}>
                  <h4>{part.name ?? `Часть ${index + 1}`}</h4>
                  {part.description && <p>{part.description}</p>}
                  {part.why_critical && <p><strong>Почему критично:</strong> {part.why_critical}</p>}
                  {part.files && part.files.length > 0 && (
                    <p className="mono-link">{part.files.join(" · ")}</p>
                  )}
                </div>
              ))}
            </div>
          )}

          {activeView === "quality" && (
            <div className="card quality-card">
              <h3>Оценка проекта</h3>
              {!quality && <p>Оценка проекта пока недоступна.</p>}
              {quality && (
                <>
                  <div className="quality-dashboard">
                    <div className="score-widget">
                      <div className="score-number">{quality.score.toFixed(1)}</div>
                      <div className="score-max">из {quality.max_score}</div>
                      <div className="score-label">{quality.score_label}</div>
                      <div className="score-bar"><span style={{ width: `${scorePercent}%` }} /></div>
                    </div>
                    <div className="quality-summary">
                      <h4>Итог</h4>
                      <p>{quality.summary}</p>
                    </div>
                  </div>

                  <div className="criteria-grid">
                    {Object.entries(quality.criteria ?? {}).map(([key, criterion]) => (
                      <div className={`criterion-card ${criterion.value ? "ok" : "bad"}`} key={key}>
                        <span>{criterion.value ? "✓" : "!"}</span>
                        <div>
                          <h4>{criterion.label}</h4>
                          <p>{criterion.description}</p>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="three-columns">
                    <ListBlock title="Сильные стороны" items={quality.strengths} />
                    <ListBlock title="Риски" items={quality.risks} />
                    <ListBlock title="Рекомендации" items={quality.recommendations} />
                  </div>
                </>
              )}
            </div>
          )}

          {activeView === "versions" && (
            <div className="card">
              <div className="repo-card-head">
                <div>
                  <h3>История версий</h3>
                  <p>Откройте любую ревизию документации для выбранной версии приложения.</p>
                </div>
                <button type="button" className="secondary-button" onClick={handleLatestVersion}>Актуальная версия</button>
              </div>

              {versions.length === 0 && <p>Версий документации пока нет.</p>}
              <div className="version-list">
                {versions.map((version) => (
                  <button
                    type="button"
                    className={`version-card ${selectedVersionId === version.id || (!selectedVersionId && version.is_latest_for_repository) ? "selected" : ""}`}
                    key={version.id}
                    onClick={() => handleSelectVersion(version.id)}
                  >
                    <strong>{version.display_name}</strong>
                    <span>App version {version.app_version}</span>
                    <span>Создано: {safeDate(version.created_at)}</span>
                    {version.is_latest_for_repository && <em>Актуальная</em>}
                  </button>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </Layout>
  );
}

export default RepositoryDetailsPage;
