import { useState, type FormEvent } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";

import { ApiError } from "../api/client";
import { useAuth } from "./AuthProvider";
import { safeNextPath } from "./nextPath";
import "../styles/login.css";

type Mode = "login" | "register";

function authErrorMessage(error: unknown, mode: Mode): string {
  if (error instanceof ApiError) {
    if (error.status === 429) return "尝试次数过多，请稍后再试";
    if (error.status === 403) return error.message || "当前已关闭自助注册";
    if (error.status === 409) return "用户名或邮箱已被使用";
    if (mode === "register") return error.message || "注册失败";
    return error.message || "用户名或密码不正确";
  }
  if (error instanceof Error && error.message) return error.message;
  return "操作失败，请重试";
}

export function LoginPage() {
  const { user, status, login, register } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const next = safeNextPath(searchParams.get("next"), window.location.origin);

  const [mode, setMode] = useState<Mode>("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  if (status === "loading") {
    return (
      <div className="auth-loading">
        <div className="loader" />
        <span>CHECKING SESSION</span>
      </div>
    );
  }

  if (user) {
    return <Navigate to={next} replace />;
  }

  function switchMode(nextMode: Mode) {
    setMode(nextMode);
    setError("");
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (mode === "register") {
        await register({ username, password, displayName, email });
      } else {
        await login(username, password);
      }
      navigate(next, { replace: true });
    } catch (submitError) {
      setError(authErrorMessage(submitError, mode));
      setBusy(false);
    }
  }

  const submitLabel = busy
    ? mode === "register"
      ? "创建中…"
      : "验证中…"
    : mode === "register"
      ? "创建本地账号"
      : "进入 VibeForge";

  return (
    <div className={mode === "register" ? "login-page register" : "login-page"}>
      <main className="login-shell">
        <section className="login-intro">
          <div>
            <div className="login-brand">
              <b>V</b> VibeForge
            </div>
            <div className="login-eyebrow">PERSONAL DESIGN AGENT / PRIVATE SERVER</div>
            <h1>
              你的想法，
              <br />
              <span>只给你看。</span>
            </h1>
            <p className="login-lede">
              这个 Agent Server 已启用访问保护。登录后继续生成、查看代码变化，并把成果部署到这台机器。
            </p>
          </div>
          <div className="login-intro-foot">
            <span>
              <i />
              SQLITE SESSIONS
            </span>
            <span>
              <i />
              LOCAL PROJECTS
            </span>
            <span>
              <i />
              12888
            </span>
          </div>
        </section>

        <section className="login-card">
          <div className="login-kicker">LOCAL ACCOUNTS</div>
          <h2>进入工作台。</h2>
          <p className="login-sub">
            {mode === "register"
              ? "注册后账号、会话和项目都只保存在这台机器上。用户名 3~32 位，密码至少 8 位。"
              : "登录后继续生成、查看代码变化。账号与项目都保存在这台机器上。"}
          </p>
          <div className="login-tabs" role="tablist">
            <button
              type="button"
              className={mode === "login" ? "login-tab active" : "login-tab"}
              onClick={() => switchMode("login")}
            >
              登录
            </button>
            <button
              type="button"
              className={mode === "register" ? "login-tab active" : "login-tab"}
              onClick={() => switchMode("register")}
            >
              注册
            </button>
          </div>
          <form className="login-form" autoComplete="on" onSubmit={handleSubmit}>
            <label htmlFor="username">USERNAME</label>
            <div className="login-field">
              <input
                id="username"
                name="username"
                type="text"
                autoComplete="username"
                placeholder="用户名或邮箱"
                required
                autoFocus
                value={username}
                onChange={(event) => setUsername(event.target.value)}
              />
            </div>
            <div className="login-register-only">
              <label htmlFor="displayName">
                DISPLAY NAME <span>OPTIONAL</span>
              </label>
              <div className="login-field">
                <input
                  id="displayName"
                  name="displayName"
                  type="text"
                  autoComplete="nickname"
                  placeholder="显示名称（可选）"
                  maxLength={40}
                  value={displayName}
                  onChange={(event) => setDisplayName(event.target.value)}
                />
              </div>
              <label htmlFor="email">
                EMAIL <span>OPTIONAL</span>
              </label>
              <div className="login-field">
                <input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  placeholder="邮箱（可选）"
                  maxLength={254}
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
              </div>
            </div>
            <label htmlFor="password">PASSWORD</label>
            <div className="login-field">
              <input
                id="password"
                name="password"
                type={showPassword ? "text" : "password"}
                autoComplete={mode === "register" ? "new-password" : "current-password"}
                placeholder="输入密码"
                required
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
              <button
                type="button"
                className="login-reveal"
                aria-label={showPassword ? "隐藏密码" : "显示密码"}
                onClick={() => setShowPassword((visible) => !visible)}
              >
                {showPassword ? "隐藏" : "显示"}
              </button>
            </div>
            <button className="login-submit" type="submit" disabled={busy}>
              <span>{submitLabel}</span>
              <span>↗</span>
            </button>
            <div className="login-error" role="alert">
              {error}
            </div>
          </form>
          <div className="login-meta">
            <span>LOCAL · SQLITE</span>
            <span>VIBEFORGE / 2026</span>
          </div>
        </section>
      </main>
    </div>
  );
}
