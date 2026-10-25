import { useEffect, useState, type CSSProperties, type FormEvent } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";

import { ApiError } from "../api/client";
import { useAuth } from "./AuthProvider";
import { safeNextPath } from "./nextPath";
import "../styles/login.css";

type Mode = "login" | "register";

const BOOT_SEQUENCE = ["handshake…", "session…", "ready"];

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
  const [boot, setBoot] = useState("");
  const [opening, setOpening] = useState(false);

  useEffect(() => {
    let index = 0;
    const timer = window.setInterval(() => {
      if (index < BOOT_SEQUENCE.length) {
        setBoot(BOOT_SEQUENCE[index]);
        index += 1;
        if (index >= BOOT_SEQUENCE.length) window.clearInterval(timer);
      }
    }, 420);
    return () => window.clearInterval(timer);
  }, []);

  if (status === "loading") {
    return (
      <div className="login-page">
        <div className="auth-loading">
          <div className="loader" />
          <span>CHECKING SESSION</span>
        </div>
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

  function enterWorkspace() {
    const reduce =
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
    if (reduce) {
      navigate(next, { replace: true });
      return;
    }
    setOpening(true);
    window.setTimeout(() => navigate(next, { replace: true }), 520);
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
      enterWorkspace();
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
      : "进入 Reify";

  const pageClass =
    "login-page" +
    (mode === "register" ? " register" : "") +
    (opening ? " opening" : "");

  return (
    <div className={pageClass}>
      <main className="login-shell">
        <svg className="login-powerline" viewBox="0 0 400 2" aria-hidden="true">
          <path d="M0 1 H400" />
        </svg>
        <h1 className="login-wordmark" aria-label="Reify">
          {"REIFY".split("").map((letter, index) => (
            <span key={index} style={{ "--i": index } as CSSProperties}>
              {letter}
            </span>
          ))}
        </h1>
        <p className="login-tagline">ONE SENTENCE. MADE REAL.</p>
        <p className="login-boot" aria-live="polite">
          {boot}
        </p>
        <p className="login-lede">
          {mode === "register"
            ? "注册后账号与项目只保存在这台机器上。用户名 3~32 位，密码至少 8 位。"
            : "一句话，实现你的想法。"}
        </p>
        <div className="login-tabs" role="tablist" aria-label="账号方式">
          <button
            type="button"
            role="tab"
            aria-selected={mode === "login"}
            className={mode === "login" ? "login-tab active" : "login-tab"}
            onClick={() => switchMode("login")}
          >
            登录
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === "register"}
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
          <span>LOCAL · SQLITE SESSIONS</span>
          <span>PRIVATE SERVER · 12888</span>
        </div>
      </main>
    </div>
  );
}
