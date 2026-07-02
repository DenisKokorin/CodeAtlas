import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import DocumentationEditor from "../components/DocumentationEditor";
import Layout from "../components/Layout";
import SEO from "../components/SEO";
import type { UserRole } from "../api/authApi";
import { getRepositoryGitHubInfo, type GitHubRepositoryInfo } from "../api/githubApi";
import {
  askChatQuestion,
  createChatConversation,
  deleteRepository,
  downloadExport,
  generateDocumentation,
  getBusinessSummary,
  getChatConversations,
  getChatMessages,
  getCriticalParts,
  getDocumentationVersion,
  getDocumentationVersions,
  getLatestDocumentation,
  getQualityAssessment,
  getRepositoryById,
  rebuildChatIndex,
  type BusinessSummaryResponse,
  type ChatConversation,
  type ChatMessage,
  type CriticalPartsResponse,
  type DocumentationResponse,
  type DocumentationVersionListItem,
  type ExportFormat,
  type QualityAssessmentResponse,
  type Repository,
  updateDocumentationVersionContent,
} from "../api/repositoriesApi";

type RepositoryDetailsPageProps = {
  theme: "dark" | "light";
  toggleTheme: () => void;
  userEmail: string | null;
  onLogout: () => void;
  userRole: UserRole | null;
};

type ActiveView = "documentation" | "summary" | "critical" | "quality" | "versions" | "chat";

function safeDate(value?: string | null) {
  if (!value) return "не указано";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString("ru-RU");
}

function documentationSourceLabel(value?: string | null) {
  if (value === "manual_edit") return "Отредактировано вручную";
  return "Сгенерировано ИИ";
}

function mapVersionToDocumentationResponse(
  repositoryId: number,
  version: {
    id: number;
    documentation: string;
    provider: string | null;
    created_at: string;
    updated_at: string;
    source_updated_at: string | null;
    app_version: string;
    revision_number: number;
    display_name: string;
    documentation_source: string;
  }
): DocumentationResponse {
  return {
    repository_id: repositoryId,
    documentation: version.documentation,
    provider: version.provider,
    updated_at: version.updated_at ?? version.created_at,
    source_updated_at: version.source_updated_at,
    is_stale: false,
    documentation_version_id: version.id,
    app_version: version.app_version,
    revision_number: version.revision_number,
    display_name: version.display_name,
    documentation_source: version.documentation_source,
  };
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
  const [isEditingDocumentation, setIsEditingDocumentation] = useState(false);
  const [editedDocumentation, setEditedDocumentation] = useState("");
  const [isSavingDocumentation, setIsSavingDocumentation] = useState(false);
  const [saveEditError, setSaveEditError] = useState("");
  const [activeView, setActiveView] = useState<ActiveView>("documentation");
  const [appVersion, setAppVersion] = useState("1.0.0");
  const [isLoading, setIsLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isGithubLoading, setIsGithubLoading] = useState(false);
  const [error, setError] = useState("");
  const [generationError, setGenerationError] = useState("");
  const [blockInfo, setBlockInfo] = useState("");
  const [chatConversations, setChatConversations] = useState<ChatConversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<number | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatError, setChatError] = useState("");
  const [chatInfo, setChatInfo] = useState("");
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [isChatIndexing, setIsChatIndexing] = useState(false);
  const [isSendingMessage, setIsSendingMessage] = useState(false);

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
    setSaveEditError("");
    setIsEditingDocumentation(false);

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

  const loadChatConversations = async (selectedConversationId?: number | null) => {
    if (!repositoryId) return;

    setChatError("");

    try {
      const conversations = await getChatConversations(repositoryId);
      setChatConversations(conversations.items);

      if (conversations.items.length === 0) {
        setActiveConversationId(null);
        setChatMessages([]);
        return;
      }

      const nextConversationId = selectedConversationId ?? activeConversationId;
      const existingConversation = nextConversationId
        ? conversations.items.find((conversation) => conversation.id === nextConversationId)
        : undefined;

      setActiveConversationId(existingConversation?.id ?? conversations.items[0].id);
    } catch (err) {
      setChatError(err instanceof Error ? err.message : "Не удалось загрузить историю чата.");
    }
  };

  const loadChatMessages = async (conversationId: number) => {
    if (!repositoryId) return;

    setIsChatLoading(true);
    setChatError("");

    try {
      const messages = await getChatMessages(repositoryId, conversationId);
      setChatMessages(messages.items);
    } catch (err) {
      setChatError(err instanceof Error ? err.message : "Не удалось загрузить сообщения чата.");
    } finally {
      setIsChatLoading(false);
    }
  };

  useEffect(() => {
    if (activeView !== "chat" || !repositoryId) {
      return;
    }

    void loadChatConversations();
  }, [activeView, repositoryId]);

  useEffect(() => {
    if (activeView !== "chat" || !activeConversationId) {
      return;
    }

    void loadChatMessages(activeConversationId);
  }, [activeView, activeConversationId]);

  const handleBuildChatIndex = async () => {
    if (!repositoryId) return;

    setIsChatIndexing(true);
    setChatError("");
    setChatInfo("");

    try {
      const result = await rebuildChatIndex(repositoryId);
      setChatInfo(`Индекс собран: ${result.total_chunks} чанков (${result.provider}).`);
    } catch (err) {
      setChatError(err instanceof Error ? err.message : "Не удалось собрать индекс знаний.");
    } finally {
      setIsChatIndexing(false);
    }
  };

  const handleStartNewConversation = async () => {
    if (!repositoryId) return;

    setChatError("");
    setChatInfo("");

    try {
      const conversation = await createChatConversation(repositoryId, "Новый чат");
      setChatConversations((current) => [conversation, ...current]);
      setActiveConversationId(conversation.id);
      setChatMessages([]);
    } catch (err) {
      setChatError(err instanceof Error ? err.message : "Не удалось создать новый чат.");
    }
  };

  const handleSendMessage = async (event?: React.FormEvent) => {
    event?.preventDefault();

    if (!repositoryId) return;

    const trimmedQuestion = chatInput.trim();
    if (!trimmedQuestion || isSendingMessage) return;

    setIsSendingMessage(true);
    setChatError("");
    setChatInfo("");

    try {
      let conversationId = activeConversationId;

      if (!conversationId) {
        const conversation = await createChatConversation(repositoryId, trimmedQuestion.slice(0, 60));
        conversationId = conversation.id;
        setActiveConversationId(conversation.id);
        setChatConversations((current) => [conversation, ...current]);
      }

      if (!conversationId) return;

      await askChatQuestion(repositoryId, conversationId, trimmedQuestion);
      setChatInput("");
      await loadChatConversations(conversationId);
      await loadChatMessages(conversationId);
    } catch (err) {
      setChatError(err instanceof Error ? err.message : "Не удалось отправить сообщение.");
    } finally {
      setIsSendingMessage(false);
    }
  };

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
      setDocumentation(mapVersionToDocumentationResponse(repositoryId, version));
      setSelectedVersionId(versionId);
      setIsEditingDocumentation(false);
      setSaveEditError("");
      await loadBlocks(versionId);
      setActiveView("documentation");
    } catch {
      setGenerationError("Не удалось открыть выбранную версию документации.");
    }
  };

  const handleStartEdit = () => {
    if (!documentation?.documentation) return;

    setEditedDocumentation(documentation.documentation);
    setSaveEditError("");
    setIsEditingDocumentation(true);
  };

  const handleCancelEdit = () => {
    setSaveEditError("");
    setEditedDocumentation(documentation?.documentation ?? "");
    setIsEditingDocumentation(false);
  };

  const handleSaveEdit = async () => {
    if (!repositoryId || !documentation?.documentation_version_id) {
      setSaveEditError("Не удалось определить версию документации для сохранения.");
      return;
    }

    if (!editedDocumentation.trim()) {
      setSaveEditError("Документация не может быть пустой.");
      return;
    }

    setIsSavingDocumentation(true);
    setSaveEditError("");

    try {
      const updatedVersion = await updateDocumentationVersionContent(
        repositoryId,
        documentation.documentation_version_id,
        editedDocumentation,
      );

      setDocumentation(mapVersionToDocumentationResponse(repositoryId, updatedVersion));
      setVersions((currentVersions) =>
        currentVersions.map((version) =>
          version.id === updatedVersion.id
            ? {
                ...version,
                updated_at: updatedVersion.updated_at,
                documentation_source: updatedVersion.documentation_source,
              }
            : version,
        ),
      );
      setIsEditingDocumentation(false);
    } catch (err) {
      setSaveEditError(err instanceof Error ? err.message : "Не удалось сохранить документацию.");
    } finally {
      setIsSavingDocumentation(false);
    }
  };

  const handleLatestVersion = async () => {
    setSelectedVersionId(null);
    setIsEditingDocumentation(false);
    setSaveEditError("");
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
                <div><strong>Source</strong><span>{documentation?.documentation ? documentationSourceLabel(documentation.documentation_source) : "—"}</span></div>
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
            <button className={activeView === "chat" ? "active" : ""} onClick={() => setActiveView("chat")}>RAG Chat</button>
          </div>

          {blockInfo && <p className="state-message">{blockInfo}</p>}

          {activeView === "documentation" && (
            <div className="card">
              <div className="repo-card-head">
                <div>
                  <div className="title-row">
                    <h3>{documentation?.display_name ?? "Сгенерированная документация"}</h3>
                    {documentation?.documentation && (
                      <span className={`source-badge source-${documentation.documentation_source ?? "generated"}`}>
                        {documentationSourceLabel(documentation.documentation_source)}
                      </span>
                    )}
                  </div>
                  <p>Мультиформатный экспорт применяется только к основной документации.</p>
                </div>
                <div className="export-buttons">
                  {documentation?.documentation && !isEditingDocumentation && (
                    <button type="button" className="primary-button" onClick={handleStartEdit}>
                      Редактировать документацию
                    </button>
                  )}
                  {(["markdown", "txt", "html", "docx", "json"] as ExportFormat[]).map((format) => (
                    <button
                      key={format}
                      type="button"
                      className="secondary-button"
                      onClick={() => handleExport(format)}
                      disabled={!documentation?.documentation || isEditingDocumentation}
                    >
                      {format.toUpperCase()}
                    </button>
                  ))}
                </div>
              </div>

              {!documentation?.documentation && <p>Документация ещё не сгенерирована.</p>}
              {saveEditError && <p className="form-error">{saveEditError}</p>}

              {documentation?.documentation && isEditingDocumentation && (
                <div className="documentation-editor-wrap">
                  <DocumentationEditor
                    key={documentation.documentation_version_id ?? "latest"}
                    markdown={editedDocumentation}
                    onChange={setEditedDocumentation}
                  />
                  <div className="editor-actions">
                    <button type="button" className="primary-button" disabled={isSavingDocumentation} onClick={handleSaveEdit}>
                      {isSavingDocumentation ? "Сохранение..." : "Сохранить изменения"}
                    </button>
                    <button type="button" className="secondary-button" disabled={isSavingDocumentation} onClick={handleCancelEdit}>
                      Отмена
                    </button>
                  </div>
                </div>
              )}

              {documentation?.documentation && !isEditingDocumentation && (
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
                    <span>{documentationSourceLabel(version.documentation_source)}</span>
                    {version.is_latest_for_repository && <em>Актуальная</em>}
                  </button>
                ))}
              </div>
            </div>
          )}

          {activeView === "chat" && (
            <div className="card chat-card">
              <div className="repo-card-head">
                <div>
                  <h3>RAG-чат по репозиторию</h3>
                  <p>Задавайте вопросы про структуру проекта, документацию и код.</p>
                </div>
                <div className="chat-actions">
                  <button type="button" className="secondary-button" onClick={handleBuildChatIndex} disabled={isChatIndexing}>
                    {isChatIndexing ? "Сборка..." : "Собрать индекс"}
                  </button>
                  <button type="button" className="primary-button" onClick={handleStartNewConversation}>
                    Новый чат
                  </button>
                </div>
              </div>

              {chatInfo && <p className="state-message">{chatInfo}</p>}
              {chatError && <p className="form-error">{chatError}</p>}

              <div className="chat-shell">
                <aside className="chat-sidebar">
                  <h4>Разговоры</h4>
                  {chatConversations.length === 0 && <p className="state-message">Пока нет сохранённых разговоров.</p>}
                  <div className="chat-conversation-list">
                    {chatConversations.map((conversation) => (
                      <button
                        type="button"
                        key={conversation.id}
                        className={`chat-conversation-item ${activeConversationId === conversation.id ? "active" : ""}`}
                        onClick={() => {
                          setActiveConversationId(conversation.id);
                        }}
                      >
                        <strong>{conversation.title ?? "Новый чат"}</strong>
                        <span>{safeDate(conversation.updated_at)}</span>
                      </button>
                    ))}
                  </div>
                </aside>

                <div className="chat-panel">
                  {isChatLoading && <p className="state-message">Загрузка сообщений...</p>}

                  {!activeConversationId && !isChatLoading && (
                    <div className="chat-empty-state">
                      <p>Начните новый чат или выберите существующий разговор.</p>
                    </div>
                  )}

                  {activeConversationId && (
                    <div className="chat-messages">
                      {chatMessages.map((message) => (
                        <div key={message.id} className={`chat-message ${message.role}`}>
                          <div className="chat-message-meta">
                            <strong>{message.role === "user" ? "Вы" : "ИИ-ассистент"}</strong>
                            <span>{safeDate(message.created_at)}</span>
                          </div>
                          <div className="chat-message-body">
                            <ReactMarkdown>{message.content}</ReactMarkdown>
                          </div>
                          {message.sources && message.sources.length > 0 && (
                            <div className="chat-sources">
                              <strong>Источники:</strong>
                              <ul>
                                {message.sources.map((source) => (
                                  <li key={`${message.id}-${source.chunk_id}`}>
                                    {source.source_path ?? source.chunk_type}
                                    {source.relevance_score ? ` · ${source.relevance_score.toFixed(2)}` : ""}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  <form className="chat-composer" onSubmit={handleSendMessage}>
                    <textarea
                      value={chatInput}
                      onChange={(event) => setChatInput(event.target.value)}
                      placeholder="Спросите про проект, документацию или код..."
                      rows={4}
                      disabled={isSendingMessage}
                    />
                    <div className="chat-composer-actions">
                      <span className="chat-hint">Ответы строятся на индексированном контексте репозитория.</span>
                      <button type="submit" className="primary-button" disabled={isSendingMessage || !chatInput.trim()}>
                        {isSendingMessage ? "Отправка..." : "Отправить"}
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </Layout>
  );
}

export default RepositoryDetailsPage;
