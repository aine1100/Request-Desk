"use client";

import { FormEvent, useState } from "react";
import { api, saveSession } from "../../lib/api";
import { flashSuccess, notifyErrorFrom } from "../../lib/toast";
import type { User } from "../../lib/types";

export default function LoginPage() {
  const [email, setEmail] = useState("client-a@example.com");
  const [password, setPassword] = useState("client123");
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    try {
      const result = await api<{ access: string; user: User }>("/api/auth/login/", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      saveSession(result.access, result.user);
      flashSuccess(`Signed in as ${result.user.name}`);
      window.location.assign("/requests");
    } catch (err) {
      notifyErrorFrom(err, "Login failed.");
    } finally {
      setPending(false);
    }
  }

  return (
    <form className="card login-card stack" onSubmit={onSubmit}>
      <div className="login-brand">
        <div className="mark">RD</div>
        <strong>Request Desk</strong>
      </div>
      <div>
        <h1>Sign in</h1>
        <p className="lede">Use your staff or client account.</p>
      </div>
      <label>
        Email
        <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" required />
      </label>
      <label>
        Password
        <input value={password} onChange={(event) => setPassword(event.target.value)} type="password" required />
      </label>
      <button className="btn" disabled={pending} type="submit">
        {pending ? "Signing in…" : "Sign in"}
      </button>
      <div className="accounts">
        <div>admin@example.com / admin123</div>
        <div>ops1@example.com / ops123</div>
        <div>client-a@example.com / client123</div>
        <div>client-b@example.com / client123</div>
      </div>
    </form>
  );
}
