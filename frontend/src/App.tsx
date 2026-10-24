import { AuthProvider } from "./auth/AuthProvider";
import { ToastProvider } from "./layout/ToastProvider";
import { AppRoutes } from "./router";

export function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <AppRoutes />
      </ToastProvider>
    </AuthProvider>
  );
}
