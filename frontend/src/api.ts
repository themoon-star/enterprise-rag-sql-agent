export interface DemoSession {
  access_token: string;
  tenant_name: string;
  user_name: string;
  roles: string[];
}

export interface DocumentItem {
  id: string;
  title: string;
  content: string;
  source_uri: string;
  allowed_roles: string[];
}

export interface DatasourceItem {
  id: string;
  name: string;
  dialect: "postgresql";
  allowed_tables: string[];
  row_limit: number;
  statement_timeout_ms: number;
}

export interface RagResult {
  status: "answered" | "refused" | "clarification";
  answer: string;
  citations: Array<{
    document_id: string;
    title: string;
    source_uri: string;
    score: number;
    excerpt: string;
  }>;
  trace: {
    accessible_candidates: number;
    ranked_candidates: number;
    decision: string;
  };
}

export interface SqlResult {
  status: "succeeded" | "blocked" | "failed";
  sql: string | null;
  repaired: boolean;
  execution_attempts: number;
  columns: string[];
  rows: Array<Record<string, unknown>>;
  decision: string;
}

let accessToken = "";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);

  const response = await fetch(path, { ...options, headers });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({ detail: "请求失败" }));
    throw new Error(detail.detail ?? `请求失败 (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export async function openDemoSession(): Promise<DemoSession> {
  const session = await request<DemoSession>("/api/demo/session", { method: "POST" });
  accessToken = session.access_token;
  return session;
}

export function listDocuments(): Promise<DocumentItem[]> {
  return request("/api/documents");
}

export function listDatasources(): Promise<DatasourceItem[]> {
  return request("/api/datasources");
}

export function queryRag(question: string): Promise<RagResult> {
  return request("/api/rag/query", {
    method: "POST",
    body: JSON.stringify({ question, top_k: 3 }),
  });
}

export function querySql(datasourceId: string, question: string): Promise<SqlResult> {
  return request("/api/sql/query", {
    method: "POST",
    body: JSON.stringify({ datasource_id: datasourceId, question }),
  });
}

export function createDatasource(payload: {
  name: string;
  database_url: string;
  allowed_tables: string[];
}): Promise<DatasourceItem> {
  return request("/api/datasources", {
    method: "POST",
    body: JSON.stringify({ ...payload, row_limit: 100, statement_timeout_ms: 2000 }),
  });
}
