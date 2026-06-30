import { apiFetch, readErrorMessage } from "./apiClient";

export type Repository = {
  id: number;
  owner_id: number;
  name: string;
  repo_url: string;
  description: string | null;
  status: string;
  github_full_name?: string | null;
  github_default_branch?: string | null;
  github_language?: string | null;
  github_updated_at?: string | null;
  generated_documentation?: string | null;
  documentation_updated_at?: string | null;
  documentation_provider?: string | null;
  documentation_source_updated_at?: string | null;
  documentation_is_stale?: boolean;
  created_at: string;
  updated_at: string;
};

export type RepositoryData = {
  name: string;
  repo_url: string;
  description: string;
  status: string;
};

export type RepositoryUpdateData = {
  name: string;
  description: string;
  status?: string;
};

export type RepositoryListResponse = {
  items: Repository[];
  total: number;
  page: number;
  page_size: number;
};

export type RepositoryFilters = {
  search?: string;
  status?: string;
  sort_by?: string;
  sort_order?: string;
  page?: number;
  page_size?: number;
};

export type DocumentationResponse = {
  repository_id: number;
  documentation: string | null;
  provider: string | null;
  updated_at: string | null;
  source_updated_at: string | null;
  is_stale: boolean;
  documentation_version_id: number | null;
  app_version: string | null;
  revision_number: number | null;
  display_name: string | null;
  documentation_source: string | null;
};

export type DocumentationVersionListItem = {
  id: number;
  repository_id: number;
  app_version: string;
  revision_number: number;
  display_name: string;
  provider: string | null;
  source_updated_at: string | null;
  is_latest_for_app_version: boolean;
  is_latest_for_repository: boolean;
  created_at: string;
  updated_at: string;
  documentation_source: string;
};

export type DocumentationVersion = DocumentationVersionListItem & {
  documentation: string;
};

export type DocumentationVersionListResponse = {
  items: DocumentationVersionListItem[];
  total: number;
};

export type BusinessSummary = {
  title?: string;
  text?: string;
  target_audience?: string[];
  business_value?: string[];
};

export type BusinessSummaryResponse = {
  repository_id: number;
  documentation_version_id: number;
  app_version: string;
  revision_number: number;
  display_name: string;
  business_summary: BusinessSummary;
};

export type QualityCriterion = {
  value: boolean;
  label: string;
  description: string;
};

export type QualityAssessment = {
  score: number;
  max_score: number;
  score_label: string;
  summary?: string;
  criteria?: Record<string, QualityCriterion>;
  strengths?: string[];
  risks?: string[];
  recommendations?: string[];
};

export type QualityAssessmentResponse = {
  repository_id: number;
  documentation_version_id: number;
  app_version: string;
  revision_number: number;
  display_name: string;
  quality_assessment: QualityAssessment;
};

export type CriticalPartItem = {
  name?: string;
  description?: string;
  files?: string[];
  why_critical?: string;
};

export type CriticalParts = {
  title?: string;
  items?: CriticalPartItem[];
};

export type CriticalPartsResponse = {
  repository_id: number;
  documentation_version_id: number;
  app_version: string;
  revision_number: number;
  display_name: string;
  critical_parts: CriticalParts;
};

export type ExportFormat = "markdown" | "txt" | "html" | "docx" | "json";

function buildRepositoryQuery(filters: RepositoryFilters) {
  const params = new URLSearchParams();

  if (filters.search) params.set("search", filters.search);
  if (filters.status) params.set("status", filters.status);
  if (filters.sort_by) params.set("sort_by", filters.sort_by);
  if (filters.sort_order) params.set("sort_order", filters.sort_order);
  if (filters.page) params.set("page", String(filters.page));
  if (filters.page_size) params.set("page_size", String(filters.page_size));

  const query = params.toString();
  return query ? `?${query}` : "";
}

export async function getRepositories(filters: RepositoryFilters = {}) {
  const response = await apiFetch(`/repositories/${buildRepositoryQuery(filters)}`, {
    method: "GET",
  });

  if (!response.ok) throw new Error("Не удалось загрузить список репозиториев");
  return response.json() as Promise<RepositoryListResponse>;
}

export async function getRepositoryById(id: string | number) {
  const response = await apiFetch(`/repositories/${id}`, { method: "GET" });
  if (!response.ok) throw new Error("Не удалось загрузить репозиторий");
  return response.json() as Promise<Repository>;
}

export async function createRepository(data: RepositoryData) {
  const response = await apiFetch("/repositories/", {
    method: "POST",
    body: JSON.stringify(data),
  });

  if (!response.ok) throw new Error(await readErrorMessage(response, "Не удалось создать репозиторий"));
  return response.json() as Promise<Repository>;
}

export async function updateRepository(id: number, data: RepositoryUpdateData) {
  const response = await apiFetch(`/repositories/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });

  if (!response.ok) throw new Error("Не удалось обновить репозиторий");
  return response.json() as Promise<Repository>;
}

export async function deleteRepository(id: number) {
  const response = await apiFetch(`/repositories/${id}`, { method: "DELETE" });
  if (!response.ok) throw new Error("Не удалось удалить репозиторий");
  return response.json() as Promise<Repository>;
}

export async function generateDocumentation(repositoryId: number, appVersion: string) {
  const response = await apiFetch(`/repositories/${repositoryId}/generate-documentation`, {
    method: "POST",
    body: JSON.stringify({ app_version: appVersion }),
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response, "Не удалось сгенерировать документацию"));
  }

  return response.json() as Promise<DocumentationResponse>;
}

export async function getLatestDocumentation(repositoryId: number) {
  const response = await apiFetch(`/repositories/${repositoryId}/documentation`, { method: "GET" });
  if (!response.ok) throw new Error("Документация ещё не сгенерирована");
  return response.json() as Promise<DocumentationResponse>;
}

export async function getDocumentationVersions(repositoryId: number) {
  const response = await apiFetch(`/repositories/${repositoryId}/documentation/versions`, { method: "GET" });
  if (!response.ok) throw new Error("Не удалось загрузить версии документации");
  return response.json() as Promise<DocumentationVersionListResponse>;
}

export async function updateDocumentationVersionContent(
  repositoryId: number,
  versionId: number,
  documentation: string
) {
  const response = await apiFetch(`/repositories/${repositoryId}/documentation/versions/${versionId}/content`, {
    method: "PUT",
    body: JSON.stringify({ documentation }),
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response, "Не удалось сохранить документацию"));
  }

  return response.json() as Promise<DocumentationVersion>;
}

export async function getDocumentationVersion(repositoryId: number, versionId: number) {
  const response = await apiFetch(`/repositories/${repositoryId}/documentation/versions/${versionId}`, { method: "GET" });
  if (!response.ok) throw new Error("Не удалось загрузить выбранную версию документации");
  return response.json() as Promise<DocumentationVersion>;
}

export async function getBusinessSummary(repositoryId: number, versionId?: number) {
  const path = versionId
    ? `/repositories/${repositoryId}/documentation/versions/${versionId}/business-summary`
    : `/repositories/${repositoryId}/business-summary`;

  const response = await apiFetch(path, { method: "GET" });
  if (!response.ok) throw new Error("Business Summary пока недоступен");
  return response.json() as Promise<BusinessSummaryResponse>;
}

export async function getQualityAssessment(repositoryId: number, versionId?: number) {
  const path = versionId
    ? `/repositories/${repositoryId}/documentation/versions/${versionId}/quality-assessment`
    : `/repositories/${repositoryId}/quality-assessment`;

  const response = await apiFetch(path, { method: "GET" });
  if (!response.ok) throw new Error("Оценка проекта пока недоступна");
  return response.json() as Promise<QualityAssessmentResponse>;
}

export async function getCriticalParts(repositoryId: number, versionId?: number) {
  const path = versionId
    ? `/repositories/${repositoryId}/documentation/versions/${versionId}/critical-parts`
    : `/repositories/${repositoryId}/critical-parts`;

  const response = await apiFetch(path, { method: "GET" });
  if (!response.ok) throw new Error("Критичные части проекта пока недоступны");
  return response.json() as Promise<CriticalPartsResponse>;
}

export async function downloadExport(
  repositoryId: number,
  format: ExportFormat,
  versionId?: number
) {
  const path = versionId
    ? `/repositories/${repositoryId}/documentation/versions/${versionId}/export?format=${format}`
    : `/repositories/${repositoryId}/export?format=${format}`;

  const response = await apiFetch(path, { method: "GET" });

  if (!response.ok) throw new Error("Не удалось экспортировать документацию");

  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const filenameMatch = disposition.match(/filename="?([^";]+)"?/i);
  const filename = filenameMatch?.[1] ?? `documentation.${format}`;
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
