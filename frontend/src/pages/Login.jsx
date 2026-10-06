import { useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { ArrowRight, Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Logo } from "@/components/wv/Logo";
import { Field } from "@/components/wv/bits";
import { useAuth } from "@/context/AuthContext";
import { errorMessage } from "@/lib/api";

export default function Login() {
  const { user, login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email, password);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid min-h-screen bg-[#09090B] lg:grid-cols-[1.25fr_1fr]">
      <div className="relative hidden overflow-hidden lg:block">
        <img src="/images/login.jpg" alt="" className="wv-kenburns absolute inset-0 h-full w-full object-cover" />
        <div className="absolute inset-0 bg-black/55" />
        <div className="absolute inset-y-0 right-0 w-40 bg-gradient-to-l from-[#09090B] to-transparent" />
        <div className="relative flex h-full flex-col justify-between p-12">
          <Logo subtitle="Event Portal" />
          <div className="max-w-xl">
            <p className="wv-eyebrow wv-rise mb-5">Jouw avond, onze muziek</p>
            <h1 className="font-display wv-rise wv-d1 text-6xl font-medium leading-[0.95] text-white xl:text-7xl">
              Samen maken we er <em className="text-[#E5C158]">jullie</em> avond van.
            </h1>
            <p className="wv-rise wv-d2 mt-6 max-w-md text-base text-zinc-300">
              Muziek, draaischema, uitnodiging en een directe lijn met je DJ. Alles voor je event op één plek.
            </p>
          </div>
        </div>
      </div>

      <div className="flex flex-col justify-center px-6 py-12 sm:px-16">
        <div className="mb-14 lg:hidden"><Logo subtitle="Event Portal" /></div>
        <form onSubmit={submit} className="wv-rise wv-d2 w-full max-w-sm" data-testid="login-form">
          <p className="wv-eyebrow mb-4">Welkom terug</p>
          <h2 className="font-display text-4xl text-white sm:text-5xl">Inloggen</h2>
          <p className="mt-3 text-sm text-zinc-400">Log in met de gegevens die je van White Vision hebt ontvangen.</p>
          <div className="mt-10 space-y-5">
            <Field label="E-mailadres">
              <Input data-testid="login-email-input" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="wv-input h-12" placeholder="naam@voorbeeld.nl" />
            </Field>
            <Field label={<span className="flex items-center justify-between">Wachtwoord<Link to="/wachtwoord-vergeten" className="normal-case tracking-normal text-[#E5C158] hover:text-white" data-testid="forgot-password-link">Wachtwoord vergeten?</Link></span>}>
              <Input data-testid="login-password-input" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} className="wv-input h-12" />
            </Field>
          </div>
          {error && <p data-testid="login-error" className="mt-5 text-sm text-red-400">{error}</p>}
          <button type="submit" disabled={busy} data-testid="login-submit-button" className="wv-btn mt-8 h-12 w-full">
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <>Naar mijn event <ArrowRight className="h-4 w-4" /></>}
          </button>
          <p className="mt-10 text-xs text-zinc-600">Geen toegang? Neem contact op met White Vision.</p>
        </form>
      </div>
    </div>
  );
}
