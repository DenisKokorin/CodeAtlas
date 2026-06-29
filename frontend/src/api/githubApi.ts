import { apiFetch } from "./apiClient";

export type GitHubRepositoryInfo = {
  full_name: string | null;
  html_url: string | null;
  description: string | null;
  language: string | null;
  stars: number;
  forks: number;
  open_issues: number;
  default_branch: string | null;
  updated_at: string | null;
};

export async function analyzeRepository(repoUrl: string): Promise<GitHubRepositoryInfo> {
  const response = await apiFetch("/repositories/analyze", {
    method: "POST",
    body: JSON.stringify({ repo_url: repoUrl }),
  });

  if (!response.ok) {
    throw new Error("Не удалось получить информацию из GitHub");
  }

  return response.json();
}

export async function getRepositoryGitHubInfo(repositoryId: number): Promise<GitHubRepositoryInfo> {
  const response = await apiFetch(`/repositories/${repositoryId}/github-info`, {
    method: "GET",
  });

  if (!response.ok) {
    throw new Error("Не удалось загрузить информацию из GitHub");
  }

  return response.json();
}
