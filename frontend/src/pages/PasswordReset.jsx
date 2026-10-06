import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowLeft, Check, Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Logo } from "@/components/wv/Logo";
import { Field } from "@/components/wv/bits";
import { api, errorMessage } from "@/lib/api";

const Shell = ({ children }) => (
  <div className="flex min-h-screen flex-col justify-center bg-[#09090B] px-6 py-12 sm:px-16">
    <div className="mx-auto w-full max-w-sm">
      <Logo subtitle="Event Portal" className="mb-14" />
      <div className="wv-rise">{children}</div>
      <Link to="/login" className="mt-10 inline-flex items-center gap-2 text-xs text-zinc-500 hover:text-white" data-testid="back-to-login">
        <ArrowLeft className="h-3.5 w-3.5" /> Terug naar inloggen
      </Link>
    </div>
  </div>
);

const Done = ({ title, text, testId }) => (
  <div data-testid={testId}>
    <span className="mb-6 flex h-11 w-11 items-center justify-center rounded-full bg-[#D4AF37] text-black"><Check className="h-5 w-5" /></span>
    <h1 className="font-display text-4xl text-white">{title}</h1>
    <p className="mt-3 text-sm text-zinc-400">{text}</p>
  </div>
);

export function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(null);
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const { data } = await api.post("/auth/forgot-password", { email });
      setSent(data.message);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Shell>
      {sent ? <Done title="Check je inbox" text={sent} testId="forgot-success" /> : (
        <form onSubmit={submit} data-testid="forgot-form">
          <p className="wv-eyebrow mb-4">Wachtwoord vergeten</p>
          <h1 className="font-display text-4xl text-white sm:text-5xl">Geen zorgen</h1>
          <p className="mt-3 text-sm text-zinc-400">Vul je e-mailadres in. We sturen je een link om een nieuw wachtwoord in te stellen.</p>
          <div className="mt-10">
            <Field label="E-mailadres">
              <Input type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} className="wv-input h-12" data-testid="forgot-email-input" />
            </Field>
          </div>
          {error && <p className="mt-5 text-sm text-red-400" data-testid="forgot-error">{error}</p>}
          <button type="submit" disabled={busy} className="wv-btn mt-8 h-12 w-full" data-testid="forgot-submit-button">
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Stuur resetlink"}
          </button>
        </form>
      )}
    </Shell>
  );
}

export function ResetPassword() {
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const [form, setForm] = useState({ password: "", confirm: "" });
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState(token ? "" : "Deze link is ongeldig. Vraag een nieuwe aan.");
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (form.password.length < 8) return setError("Je wachtwoord moet minimaal 8 tekens hebben.");
    if (form.password !== form.confirm) return setError("De wachtwoorden komen niet overeen.");
    setBusy(true);
    try {
      await api.post("/auth/reset-password", { token, new_password: form.password });
      setDone(true);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  if (done) {
    return (
      <Shell>
        <Done title="Wachtwoord ingesteld" text="Je kunt nu inloggen met je nieuwe wachtwoord." testId="reset-success" />
        <Link to="/login" className="wv-btn mt-8 h-12 w-full" data-testid="reset-login-button">Naar inloggen</Link>
      </Shell>
    );
  }

  return (
    <Shell>
      <form onSubmit={submit} data-testid="reset-form">
        <p className="wv-eyebrow mb-4">Nieuw wachtwoord</p>
        <h1 className="font-display text-4xl text-white sm:text-5xl">Kies een wachtwoord</h1>
        <div className="mt-10 space-y-5">
          <Field label="Nieuw wachtwoord" hint="Minimaal 8 tekens.">
            <Input type="password" required autoComplete="new-password" value={form.password} onChange={set("password")} className="wv-input h-12" data-testid="reset-password-input" />
          </Field>
          <Field label="Herhaal wachtwoord">
            <Input type="password" required autoComplete="new-password" value={form.confirm} onChange={set("confirm")} className="wv-input h-12" data-testid="reset-confirm-input" />
          </Field>
        </div>
        {error && (
          <p className="mt-5 text-sm text-red-400" data-testid="reset-error">
            {error} <Link to="/wachtwoord-vergeten" className="underline">Nieuwe link aanvragen</Link>
          </p>
        )}
        <button type="submit" disabled={busy || !token} className="wv-btn mt-8 h-12 w-full" data-testid="reset-submit-button">
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Wachtwoord opslaan"}
        </button>
      </form>
    </Shell>
  );
}
