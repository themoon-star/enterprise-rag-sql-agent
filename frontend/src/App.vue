<script setup lang="ts">
import {
  Activity,
  ArrowRight,
  BookOpenText,
  Check,
  ChevronRight,
  Database,
  FileCheck2,
  Fingerprint,
  LayoutDashboard,
  LockKeyhole,
  Menu,
  Network,
  Plus,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  TerminalSquare,
  X,
} from "@lucide/vue";
import { computed, onMounted, ref } from "vue";

import {
  createDatasource,
  listDatasources,
  listDocuments,
  openDemoSession,
  queryRag,
  querySql,
  type DatasourceItem,
  type DemoSession,
  type DocumentItem,
  type RagResult,
  type SqlResult,
} from "./api";

type ViewName = "overview" | "knowledge" | "sql" | "datasources";

const activeView = ref<ViewName>("overview");
const menuOpen = ref(false);
const loading = ref(true);
const busy = ref(false);
const error = ref("");
const session = ref<DemoSession>();
const documents = ref<DocumentItem[]>([]);
const datasources = ref<DatasourceItem[]>([]);
const ragQuestion = ref("差旅报销需要提交哪些材料？");
const ragResult = ref<RagResult>();
const sqlQuestion = ref("sales_orders 订单数量是多少？");
const sqlResult = ref<SqlResult>();
const selectedDatasource = ref("");
const showDatasourceForm = ref(false);
const datasourceForm = ref({ name: "", database_url: "", allowed_tables: "" });

const navItems = [
  { id: "overview" as const, label: "态势总览", icon: LayoutDashboard },
  { id: "knowledge" as const, label: "知识检索", icon: BookOpenText },
  { id: "sql" as const, label: "安全问数", icon: TerminalSquare },
  { id: "datasources" as const, label: "数据源", icon: Database },
];

const pageTitle = computed(() => navItems.find((item) => item.id === activeView.value)?.label ?? "TrustQuery");
const totalTables = computed(() => new Set(datasources.value.flatMap((item) => item.allowed_tables)).size);

async function initialize() {
  try {
    session.value = await openDemoSession();
    [documents.value, datasources.value] = await Promise.all([listDocuments(), listDatasources()]);
    selectedDatasource.value = datasources.value[0]?.id ?? "";
  } catch (caught) {
    error.value = messageOf(caught);
  } finally {
    loading.value = false;
  }
}

async function runRag() {
  busy.value = true;
  error.value = "";
  try {
    ragResult.value = await queryRag(ragQuestion.value);
  } catch (caught) {
    error.value = messageOf(caught);
  } finally {
    busy.value = false;
  }
}

async function runSql() {
  if (!selectedDatasource.value) return;
  busy.value = true;
  error.value = "";
  try {
    sqlResult.value = await querySql(selectedDatasource.value, sqlQuestion.value);
  } catch (caught) {
    error.value = messageOf(caught);
  } finally {
    busy.value = false;
  }
}

async function saveDatasource() {
  busy.value = true;
  error.value = "";
  try {
    const created = await createDatasource({
      name: datasourceForm.value.name,
      database_url: datasourceForm.value.database_url,
      allowed_tables: datasourceForm.value.allowed_tables.split(",").map((table) => table.trim()),
    });
    datasources.value = [...datasources.value, created];
    datasourceForm.value = { name: "", database_url: "", allowed_tables: "" };
    showDatasourceForm.value = false;
  } catch (caught) {
    error.value = messageOf(caught);
  } finally {
    busy.value = false;
  }
}

function switchView(view: ViewName) {
  activeView.value = view;
  menuOpen.value = false;
}

function messageOf(caught: unknown): string {
  return caught instanceof Error ? caught.message : "发生未知错误";
}

function displayCell(value: unknown): string {
  return value === null ? "—" : String(value);
}

onMounted(initialize);
</script>

<template>
  <div class="app-shell">
    <button class="mobile-menu" aria-label="打开导航" @click="menuOpen = true">
      <Menu :size="20" />
    </button>
    <div v-if="menuOpen" class="nav-backdrop" @click="menuOpen = false" />

    <aside class="sidebar" :class="{ open: menuOpen }">
      <div class="brand-row">
        <div class="brand-mark">
          <Fingerprint :size="24" />
        </div>
        <div><strong>TrustQuery</strong><span>CONTROL PLANE</span></div>
        <button class="close-menu" aria-label="关闭导航" @click="menuOpen = false">
          <X :size="20" />
        </button>
      </div>

      <p class="nav-label">
        WORKSPACE
      </p>
      <nav aria-label="主导航">
        <button
          v-for="item in navItems"
          :key="item.id"
          :class="{ active: activeView === item.id }"
          @click="switchView(item.id)"
        >
          <component :is="item.icon" :size="18" />
          <span>{{ item.label }}</span>
          <ChevronRight v-if="activeView === item.id" :size="16" class="nav-arrow" />
        </button>
      </nav>

      <div class="guard-card">
        <div class="guard-title">
          <ShieldCheck :size="18" /><span>策略引擎在线</span>
        </div>
        <p>租户身份、ACL 与 SQL AST 策略均在服务端强制执行。</p>
        <div class="guard-code">
          POLICY / ENFORCED
        </div>
      </div>
    </aside>

    <main>
      <header class="topbar">
        <div>
          <p class="eyebrow">
            ACME / ENTERPRISE AI
          </p>
          <h1>{{ pageTitle }}</h1>
        </div>
        <div class="identity">
          <div class="status-dot" />
          <div><strong>{{ session?.tenant_name ?? "正在建立可信会话" }}</strong><span>{{ session?.user_name }}</span></div>
        </div>
      </header>

      <div v-if="error" class="error-banner" role="alert">
        <Activity :size="18" />{{ error }}
      </div>
      <div v-if="loading" class="loading-panel" aria-live="polite">
        <div class="scan-line" />正在校验租户会话与策略快照…
      </div>

      <template v-else>
        <section v-if="activeView === 'overview'" class="view-stack">
          <div class="hero-panel">
            <div>
              <p class="eyebrow amber">
                AUDITABLE BY DESIGN
              </p>
              <h2>每一次回答，都能解释<br>“为什么允许”。</h2>
              <p>将企业知识检索与自然语言问数放进同一条可审计决策链：身份先行、权限前置、证据可追溯、SQL 双层只读。</p>
              <button class="primary-action" @click="switchView('sql')">
                检查安全问数链路 <ArrowRight :size="17" />
              </button>
            </div>
            <div class="decision-chain" aria-label="决策链状态">
              <div><span>01</span><Fingerprint :size="19" /><strong>Token verified</strong><small>tenant / role</small></div>
              <div><span>02</span><Network :size="19" /><strong>Policy filtered</strong><small>ACL before rank</small></div>
              <div><span>03</span><FileCheck2 :size="19" /><strong>Evidence bound</strong><small>citation / refusal</small></div>
              <div><span>04</span><LockKeyhole :size="19" /><strong>Query constrained</strong><small>AST + read only</small></div>
            </div>
          </div>

          <div class="metric-grid">
            <article><span>可访问知识</span><strong>{{ documents.length }}</strong><small>tenant-scoped documents</small></article>
            <article><span>只读数据源</span><strong>{{ datasources.length }}</strong><small>encrypted credentials</small></article>
            <article><span>授权数据表</span><strong>{{ totalTables }}</strong><small>AST allowlist targets</small></article>
            <article class="accent-metric">
              <span>SQL 修复预算</span><strong>1</strong><small>full revalidation required</small>
            </article>
          </div>

          <div class="two-column">
            <article class="panel">
              <div class="panel-heading">
                <div>
                  <p class="eyebrow">
                    KNOWLEDGE SCOPE
                  </p><h3>当前可见知识</h3>
                </div><BookOpenText :size="22" />
              </div>
              <ul class="resource-list">
                <li v-for="document in documents" :key="document.id">
                  <div class="resource-icon">
                    <FileCheck2 :size="17" />
                  </div>
                  <div><strong>{{ document.title }}</strong><span>{{ document.source_uri }}</span></div>
                  <span class="role-chip">{{ document.allowed_roles[0] ?? "tenant" }}</span>
                </li>
              </ul>
            </article>
            <article class="panel trace-panel">
              <div class="panel-heading">
                <div>
                  <p class="eyebrow">
                    LATEST POLICY SNAPSHOT
                  </p><h3>执行不变量</h3>
                </div><Activity :size="22" />
              </div>
              <div class="trace-row">
                <span>tenant_from_token</span><b>PASS</b>
              </div>
              <div class="trace-row">
                <span>acl_before_ranking</span><b>PASS</b>
              </div>
              <div class="trace-row">
                <span>single_readonly_statement</span><b>PASS</b>
              </div>
              <div class="trace-row">
                <span>repair_budget</span><b>01</b>
              </div>
            </article>
          </div>
        </section>

        <section v-else-if="activeView === 'knowledge'" class="view-stack">
          <div class="section-intro">
            <div>
              <p class="eyebrow">
                EVIDENCE-GROUNDED RAG
              </p><h2>先确定可见范围，再计算相关性。</h2>
            </div><span class="policy-badge"><ShieldCheck :size="16" /> ACL BEFORE RANK</span>
          </div>
          <div class="query-layout">
            <article class="panel query-panel">
              <label for="rag-question">向企业知识提问</label>
              <textarea id="rag-question" v-model="ragQuestion" rows="4" />
              <div class="suggestion-row">
                <button @click="ragQuestion = 'VPN 登录失败后会锁定多久？'">
                  VPN 锁定策略
                </button>
                <button @click="ragQuestion = '差旅报销需要提交哪些材料？'">
                  差旅报销材料
                </button>
                <button @click="ragQuestion = '未知产品的退款规则是什么？'">
                  测试证据拒答
                </button>
              </div>
              <button class="primary-action" :disabled="busy" @click="runRag">
                <Search :size="17" />{{ busy ? "检索中…" : "执行可信检索" }}
              </button>
            </article>
            <article class="panel audit-card">
              <p class="eyebrow">
                DECISION TRACE
              </p>
              <template v-if="ragResult">
                <div class="result-status" :class="ragResult.status">
                  <Check :size="18" />{{ ragResult.status }}
                </div>
                <h3>{{ ragResult.answer }}</h3>
                <div v-for="citation in ragResult.citations" :key="citation.document_id" class="citation-card">
                  <strong>{{ citation.title }} <span>{{ citation.score.toFixed(3) }}</span></strong>
                  <p>{{ citation.excerpt }}</p><small>{{ citation.source_uri }}</small>
                </div>
                <div class="mono-trace">
                  visible={{ ragResult.trace.accessible_candidates }} · ranked={{ ragResult.trace.ranked_candidates }} · {{ ragResult.trace.decision }}
                </div>
              </template>
              <div v-else class="empty-state">
                <Sparkles :size="30" /><span>执行一次检索后，这里会展示回答、引用与决策轨迹。</span>
              </div>
            </article>
          </div>
        </section>

        <section v-else-if="activeView === 'sql'" class="view-stack">
          <div class="section-intro">
            <div>
              <p class="eyebrow">
                SECURE TEXT-TO-SQL
              </p><h2>自然语言进入，受约束的只读查询出去。</h2>
            </div><span class="policy-badge"><LockKeyhole :size="16" /> AST + DB READ ONLY</span>
          </div>
          <article class="panel sql-composer">
            <div class="field-row">
              <label>只读数据源<select v-model="selectedDatasource"><option v-for="source in datasources" :key="source.id" :value="source.id">{{ source.name }}</option></select></label>
              <label>自然语言问题<input v-model="sqlQuestion"></label>
              <button class="primary-action" :disabled="busy || !selectedDatasource" @click="runSql">
                <Send :size="17" />{{ busy ? "执行中…" : "生成并执行" }}
              </button>
            </div>
            <div class="suggestion-row">
              <button @click="sqlQuestion = 'sales_orders 订单数量是多少？'">
                订单数量
              </button>
              <button @click="sqlQuestion = 'sales_orders 销售额总额是多少？'">
                销售总额
              </button>
              <button @click="sqlQuestion = 'customers 数量是多少？'">
                客户数量
              </button>
            </div>
          </article>

          <div v-if="sqlResult" class="sql-result-grid">
            <article class="panel code-panel">
              <div class="panel-heading">
                <div>
                  <p class="eyebrow">
                    NORMALIZED QUERY
                  </p><h3>已执行 SQL</h3>
                </div><span class="result-status" :class="sqlResult.status">{{ sqlResult.status }}</span>
              </div>
              <pre><code>{{ sqlResult.sql ?? 'SQL was blocked before execution' }}</code></pre>
              <div class="sql-steps">
                <div class="done">
                  <span>1</span><div><strong>Schema scoped</strong><small>仅暴露授权表结构</small></div>
                </div>
                <div class="done">
                  <span>2</span><div><strong>AST validated</strong><small>单条查询 / 表白名单 / LIMIT</small></div>
                </div>
                <div :class="{ done: sqlResult.status === 'succeeded' }">
                  <span>3</span><div><strong>Read-only executed</strong><small>timeout / transaction</small></div>
                </div>
              </div>
              <div class="mono-trace">
                attempts={{ sqlResult.execution_attempts }} · repaired={{ sqlResult.repaired }} · {{ sqlResult.decision }}
              </div>
            </article>
            <article class="panel result-table-panel">
              <div class="panel-heading">
                <div>
                  <p class="eyebrow">
                    RESULT SET
                  </p><h3>查询结果</h3>
                </div><span>{{ sqlResult.rows.length }} rows</span>
              </div>
              <div class="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th v-for="column in sqlResult.columns" :key="column">
                        {{ column }}
                      </th>
                    </tr>
                  </thead><tbody>
                    <tr v-for="(row, index) in sqlResult.rows" :key="index">
                      <td v-for="column in sqlResult.columns" :key="column">
                        {{ displayCell(row[column]) }}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </article>
          </div>
        </section>

        <section v-else class="view-stack">
          <div class="section-intro">
            <div>
              <p class="eyebrow">
                TENANT DATASOURCES
              </p><h2>凭证加密保存，查询默认只读。</h2>
            </div><button class="primary-action" @click="showDatasourceForm = !showDatasourceForm">
              <Plus :size="17" />添加数据源
            </button>
          </div>
          <form v-if="showDatasourceForm" class="panel datasource-form" @submit.prevent="saveDatasource">
            <label>显示名称<input v-model="datasourceForm.name" required placeholder="例如：经营分析只读库"></label>
            <label>PostgreSQL 连接串<input
              v-model="datasourceForm.database_url"
              required
              type="password"
              autocomplete="new-password"
              placeholder="postgresql://readonly_user:••••@host/db"
            ></label>
            <label>允许的表（逗号分隔）<input v-model="datasourceForm.allowed_tables" required placeholder="sales_orders, customers"></label>
            <p><LockKeyhole :size="15" />连接串只在服务端加密存储，响应与列表永不回显。</p>
            <button class="primary-action" :disabled="busy" type="submit">
              保存加密配置
            </button>
          </form>
          <div class="datasource-grid">
            <article v-for="source in datasources" :key="source.id" class="panel datasource-card">
              <div class="database-glyph">
                <Database :size="26" />
              </div>
              <div>
                <p class="eyebrow">
                  POSTGRESQL / READ ONLY
                </p><h3>{{ source.name }}</h3>
              </div>
              <dl>
                <div><dt>Table allowlist</dt><dd>{{ source.allowed_tables.join(', ') }}</dd></div><div><dt>Row ceiling</dt><dd>{{ source.row_limit }}</dd></div><div><dt>Statement timeout</dt><dd>{{ source.statement_timeout_ms }} ms</dd></div><div>
                  <dt>Credential state</dt><dd class="safe-text">
                    <ShieldCheck :size="15" /> encrypted
                  </dd>
                </div>
              </dl>
            </article>
          </div>
        </section>
      </template>
    </main>
  </div>
</template>
