import { useEffect, useState } from "react";
import { KeyRound, Loader2, Save } from "lucide-react";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Field, PageLoader, SectionHeader } from "@/components/wv/bits";
import { useAuth } from "@/context/AuthContext";
import { api, errorMessage } from "@/lib/api";

function Profile() {
  const { setUser } = useAuth();
  const [form, setForm] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get("/account").then((r) => setForm({ name: r.data.name, email: r.data.email, phone: r.data.phone || "" }));
  }, []);
  if (!form) return <PageLoader />;
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const save = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const { data } = await api.patch("/account", { ...form, phone: form.phone || null });
      const { phone, ...user } = data;
      setUser(user);
      toast.success("Gegevens opgeslagen");
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={save} className="wv-panel space-y-5 p-6 sm:p-8" data-testid="account-profile-form">
      <p className="font-display text-3xl text-white">Persoonlijke gegevens</p>
      <Field label="Naam"><Input required value={form.name} onChange={set("name")} className="wv-input h-11" data-testid="account-name-input" /></Field>
      <Field label="E-mailadres" hint="Hiermee log je in.">
        <Input type="email" required value={form.email} onChange={set("email")} className="wv-input h-11" data-testid="account-email-input" />
      </Field>
      <Field label="Telefoonnummer"><Input value={form.phone} onChange={set("phone")} className="wv-input h-11" data-testid="account-phone-input" /></Field>
      <button type="submit" disabled={busy} className="wv-btn" data-testid="account-save-button">
        {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}Opslaan
      </button>
    </form>
  );
}

const EMPTY = { current_password: "", new_password: "", confirm: "" };

function Password() {
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (form.new_password.length < 8) return setError("Nieuw wachtwoord moet minimaal 8 tekens hebben.");
    if (form.new_password !== form.confirm) return setError("De nieuwe wachtwoorden komen niet overeen.");
    setBusy(true);
    try {
      await api.post("/auth/password", { current_password: form.current_password, new_password: form.new_password });
      setForm(EMPTY);
      toast.success("Wachtwoord gewijzigd");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const pw = (k, label, testId, autoComplete) => (
    <Field label={label}>
      <Input type="password" required autoComplete={autoComplete} value={form[k]} onChange={set(k)} className="wv-input h-11" data-testid={testId} />
    </Field>
  );

  return (
    <form onSubmit={submit} className="wv-panel space-y-5 p-6 sm:p-8" data-testid="account-password-form">
      <p className="font-display text-3xl text-white">Wachtwoord wijzigen</p>
      {pw("current_password", "Huidig wachtwoord", "account-current-password-input", "current-password")}
      {pw("new_password", "Nieuw wachtwoord", "account-new-password-input", "new-password")}
      {pw("confirm", "Herhaal nieuw wachtwoord", "account-confirm-password-input", "new-password")}
      {error && <p className="text-sm text-red-400" data-testid="account-password-error">{error}</p>}
      <button type="submit" disabled={busy} className="wv-btn" data-testid="account-password-submit">
        {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <KeyRound className="h-4 w-4" />}Wachtwoord wijzigen
      </button>
    </form>
  );
}

export default function Account() {
  return (
    <div data-testid="account-page">
      <SectionHeader eyebrow="Mijn account" title="Jouw gegevens" text="Pas je contactgegevens aan of kies een nieuw wachtwoord." />
      <div className="grid gap-6 lg:grid-cols-2">
        <Profile />
        <Password />
      </div>
    </div>
  );
}
