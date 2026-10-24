import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "./AuthProvider";

export function ProtectedRoute() {
  const { status, user } = useAuth();
  const location = useLocation();

  if (status === "loading") {
    return (
      <div className="auth-loading">
        <div className="loader" />
        <span>CHECKING SESSION</span>
      </div>
    );
  }

  if (!user) {
    const next = location.pathname + location.search;
    return <Navigate to={"/login?next=" + encodeURIComponent(next)} replace />;
  }

  return <Outlet />;
}
