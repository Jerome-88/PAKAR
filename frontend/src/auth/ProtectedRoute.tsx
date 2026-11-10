import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "./useAuth";

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { loading, user, connectionError, retryConnection } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <main className="auth-loading" aria-live="polite">
        <img
          className="auth-loading-mark"
          src="/pakar-mark.svg"
          alt=""
          aria-hidden="true"
        />
        <p>Menyiapkan ruang kerja…</p>
      </main>
    );
  }

  if (connectionError) {
    return <main className="auth-loading"><div role="alert"><h1>Ruang kerja belum tersambung</h1><p>{connectionError}</p></div><button className="button primary" onClick={retryConnection}>Coba hubungkan lagi</button></main>;
  }

  if (!user) {
    const next = `${location.pathname}${location.search}${location.hash}`;
    return <Navigate to={`/login?next=${encodeURIComponent(next)}`} replace />;
  }

  return children;
}
