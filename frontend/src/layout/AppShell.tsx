import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthProvider";
import { useToast } from "./ToastProvider";

function navClass({ isActive }: { isActive: boolean }): string {
  return isActive ? "current" : "";
}

export function AppShell() {
  const { user, logout } = useAuth();
  const { showToast } = useToast();
  const navigate = useNavigate();
  const [loggingOut, setLoggingOut] = useState(false);

  async function handleLogout() {
    setLoggingOut(true);
    try {
      await logout();
      navigate("/login", { replace: true });
    } catch {
      showToast("退出失败，请重试");
    } finally {
      setLoggingOut(false);
    }
  }

  return (
    <>
      <div className="ambient" aria-hidden="true">
        <i className="blob b1" />
        <i className="blob b2" />
        <i className="blob b3" />
      </div>

      <header className="topbar">
        <NavLink className="brand" to="/" aria-label="回到工作台">
          <span className="brand-mark">R</span>
          <span className="brand-copy">
            Reify
            <small>IDEA → REALITY AGENT</small>
          </span>
        </NavLink>
        <div className="top-center">
          <nav className="top-nav" aria-label="主导航">
            <NavLink to="/" end className={navClass}>
              工作台
            </NavLink>
            <NavLink to="/projects" className={navClass}>
              项目库
            </NavLink>
            {user?.role === "admin" ? (
              <NavLink to="/admin" className={navClass}>
                管理
              </NavLink>
            ) : null}
          </nav>
        </div>
        <div className="top-actions">
          <div className="conn" title="本地服务已连接">
            <i />
            <span>LOCAL</span>
          </div>
          <button
            className="icon-btn logout-btn"
            type="button"
            title="退出登录"
            aria-label="退出登录"
            disabled={loggingOut}
            onClick={() => void handleLogout()}
          >
            ↩
          </button>
          <button
            className="icon-btn"
            type="button"
            title="新任务"
            aria-label="新任务"
            onClick={() => navigate("/", { state: { newTaskAt: Date.now() } })}
          >
            ＋
          </button>
        </div>
      </header>

      <main>
        <Outlet />
      </main>
    </>
  );
}
