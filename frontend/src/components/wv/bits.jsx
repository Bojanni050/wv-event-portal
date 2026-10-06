import { Navigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { STATUSES } from "@/lib/constants";

export const SectionHeader = ({ eyebrow, title, text, action, testId }) => (
  <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between" data-testid={testId}>
    <div className="max-w-2xl">
      {eyebrow && <p className="wv-eyebrow mb-3">{eyebrow}</p>}
      <h1 className="font-display text-4xl font-medium leading-[1.05] text-white sm:text-5xl">{title}</h1>
      {text && <p className="mt-3 text-sm text-zinc-400 sm:text-base">{text}</p>}
    </div>
    {action}
  </div>
);

export const EmptyState = ({ title, text, action, icon: Icon }) => (
  <div className="wv-panel flex flex-col items-start gap-3 p-8" data-testid="empty-state">
    {Icon && <Icon className="h-6 w-6 text-[#D4AF37]" strokeWidth={1.5} />}
    <p className="font-display text-2xl text-white">{title}</p>
    {text && <p className="max-w-md text-sm text-zinc-400">{text}</p>}
    {action}
  </div>
);

export const PageLoader = () => (
  <div className="flex min-h-[50vh] items-center justify-center" data-testid="page-loader">
    <Loader2 className="h-6 w-6 animate-spin text-[#D4AF37]" />
  </div>
);

const STATUS_STYLE = {
  new: "border-sky-400/40 text-sky-300",
  preparing: "border-[#D4AF37]/50 text-[#E5C158]",
  ready: "border-emerald-400/50 text-emerald-300",
  completed: "border-zinc-500/50 text-zinc-400",
};

export const StatusBadge = ({ status, testId }) => (
  <span
    data-testid={testId || "status-badge"}
    className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium uppercase tracking-wider ${STATUS_STYLE[status] || STATUS_STYLE.new}`}
  >
    <span className="h-1.5 w-1.5 rounded-full bg-current" />
    {STATUSES[status] || status}
  </span>
);

export const ProgressLine = ({ value, className = "" }) => (
  <div className={`h-[3px] w-full overflow-hidden bg-white/[0.08] ${className}`}>
    <div className="h-full bg-[#D4AF37]" style={{ width: `${value}%`, transition: "width 900ms ease" }} />
  </div>
);

export function ProtectedRoute({ roles, children }) {
  const { user } = useAuth();
  if (user === null) return <PageLoader />;
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />;
  return children;
}

export const Field = ({ label, children, hint }) => (
  <label className="block">
    <span className="mb-1.5 block text-[11px] font-medium uppercase tracking-[0.18em] text-zinc-500">{label}</span>
    {children}
    {hint && <span className="mt-1 block text-xs text-zinc-500">{hint}</span>}
  </label>
);
