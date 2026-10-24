import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api/client";
import type { AdminUser, AdminUsersResponse, AuditEntry, AuditResponse } from "../api/types";
import { useToast } from "../layout/ToastProvider";

function formatBytes(bytes: number): string {
  if (bytes > 1024 * 1024 * 1024) return (bytes / 1024 / 1024 / 1024).toFixed(1) + " GB";
  if (bytes > 1024 * 1024) return (bytes / 1024 / 1024).toFixed(1) + " MB";
  return Math.max(0, Math.round(bytes / 1024)) + " KB";
}

function shortTime(value: string | null): string {
  if (!value) return "从未登录";
  return value.replace("T", " ").slice(0, 16);
}

export function AdminPage() {
  const { showToast } = useToast();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyUser, setBusyUser] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [userData, auditData] = await Promise.all([
        api<AdminUsersResponse>("/api/admin/users"),
        api<AuditResponse>("/api/admin/audit?limit=100"),
      ]);
      setUsers(userData.items);
      setAudit(auditData.items);
      setError(null);
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : "管理数据加载失败";
      setError(message);
      showToast("管理数据加载失败：" + message);
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  useEffect(() => {
    void load();
  }, [load]);

  async function applyStatus(user: AdminUser) {
    setBusyUser(user.id);
    try {
      await api("/api/admin/users/" + encodeURIComponent(user.id) + "/status", {
        method: "POST",
        body: JSON.stringify({ disabled: !user.disabled }),
      });
      showToast(user.disabled ? "用户已启用" : "用户已禁用");
      await load();
    } catch (reason) {
      showToast(
        "操作失败：" + (reason instanceof Error ? reason.message : "未知错误"),
      );
    } finally {
      setBusyUser(null);
    }
  }

  async function revokeSessions(user: AdminUser) {
    setBusyUser(user.id);
    try {
      await api(
        "/api/admin/users/" + encodeURIComponent(user.id) + "/revoke-sessions",
        { method: "POST" },
      );
      showToast("该用户的会话已全部撤销");
      await load();
    } catch (reason) {
      showToast(
        "操作失败：" + (reason instanceof Error ? reason.message : "未知错误"),
      );
    } finally {
      setBusyUser(null);
    }
  }

  const totalProjects = users.reduce((sum, user) => sum + user.projects, 0);
  const totalStorage = users.reduce((sum, user) => sum + user.storage_bytes, 0);

  return (
    <section className="projects-view view-enter">
      <header className="projects-hero">
        <div className="eyebrow">
          <span className="pulse-dot" />
          ADMIN / LOCAL
        </div>
        <h1>
          用户与
          <br />
          <span className="gradient-text">审计。</span>
        </h1>
        <p>
          查看所有账号的存储与项目占用，禁用异常账号、撤销会话，并追踪最近的管理与项目操作。
        </p>
        <div className="project-stats">
          <span className="stat-pill">
            <b>{users.length}</b> 用户
          </span>
          <span className="stat-pill">
            <b>{totalProjects}</b> 项目
          </span>
          <span className="stat-pill">
            <b>{formatBytes(totalStorage)}</b> 存储
          </span>
        </div>
      </header>

      {error ? (
        <div className="empty-state">
          管理数据加载失败：{error}。
          <button className="filter-chip" type="button" onClick={() => void load()}>
            重试
          </button>
        </div>
      ) : loading && !users.length ? (
        <div className="empty-state">正在加载管理数据…</div>
      ) : (
        <>
          <div className="admin-table" role="list" aria-label="用户列表">
            {users.map((user) => (
              <div className="admin-row" role="listitem" key={user.id}>
                <div>
                  <b>{user.display_name || user.username}</b>
                  <small>
                    @{user.username} · {user.role}
                    {user.disabled ? " · DISABLED" : ""}
                  </small>
                </div>
                <div className="admin-meta">
                  {user.projects} 项目
                  <br />
                  {formatBytes(user.storage_bytes)}
                </div>
                <div className="admin-meta">
                  {(user.created_at || "").slice(0, 10)}
                  <br />
                  {shortTime(user.last_login_at)}
                </div>
                <div className="admin-meta">
                  {user.email || "未填写邮箱"}
                  <br />
                  {user.disabled ? "登录已停用" : "账号正常"}
                </div>
                <div className="admin-actions">
                  <button
                    type="button"
                    aria-label={(user.disabled ? "启用 " : "禁用 ") + user.username}
                    className={user.disabled ? "" : "danger"}
                    disabled={busyUser === user.id}
                    onClick={() => void applyStatus(user)}
                  >
                    {user.disabled ? "启用" : "禁用"}
                  </button>
                  <button
                    type="button"
                    aria-label={"下线 " + user.username}
                    disabled={busyUser === user.id}
                    onClick={() => void revokeSessions(user)}
                  >
                    下线
                  </button>
                </div>
              </div>
            ))}
          </div>

          <div className="admin-table">
            <div className="panel-kicker" style={{ marginTop: 18 }}>
              AUDIT LOG
            </div>
            {audit.length ? (
              <div className="audit-list">
                {audit.map((item) => (
                  <div className="audit-row" key={item.id}>
                    <span>{item.ts.replace("T", " ").slice(0, 19)}</span>
                    <span>
                      <b>{item.action}</b> · {item.detail || item.project_id || "-"}
                    </span>
                    <span>{item.user_id || "system"}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state small">还没有审计记录。</div>
            )}
          </div>
        </>
      )}

      <div className="admin-foot">
        <Link to="/">← 回到工作台</Link>
        <button className="filter-chip" type="button" onClick={() => void load()}>
          刷新数据
        </button>
      </div>
    </section>
  );
}
