"use client";

import { FormEvent, useEffect, useState } from "react";
import { Dropdown } from "../../components/Dropdown";
import { api } from "../../lib/api";
import { notifyErrorFrom, notifySuccess } from "../../lib/toast";
import type { Role, User } from "../../lib/types";

const ROLE_OPTIONS: { value: Role; label: string }[] = [
  { value: "client", label: "Client" },
  { value: "operator", label: "Operator" },
  { value: "admin", label: "Admin" },
];

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>("client");
  const [organisation, setOrganisation] = useState("");

  async function load() {
    setUsers(await api<User[]>("/api/users/"));
  }

  useEffect(() => {
    load().catch((err) => notifyErrorFrom(err, "Could not load users."));
  }, []);

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    try {
      await api("/api/users/", {
        method: "POST",
        body: JSON.stringify({ email, name, password, role, organisation }),
      });
      setEmail("");
      setName("");
      setPassword("");
      setOrganisation("");
      notifySuccess(`Created ${email}`);
      await load();
    } catch (err) {
      notifyErrorFrom(err, "Could not create the user.");
    }
  }

  async function patch(user: User, changes: Partial<User>) {
    try {
      await api(`/api/users/${user.id}/`, {
        method: "PATCH",
        body: JSON.stringify(changes),
      });
      if (changes.role) notifySuccess(`${user.name} is now ${changes.role}`);
      else if (changes.is_active === false) notifySuccess(`${user.name} deactivated`);
      else if (changes.is_active === true) notifySuccess(`${user.name} activated`);
      else notifySuccess(`${user.name} updated`);
      await load();
    } catch (err) {
      notifyErrorFrom(err, "Could not update the user.");
    }
  }

  return (
    <div className="stack">
      <div>
        <h1>Users</h1>
        <p className="lede">Admins create accounts, change roles, and deactivate people.</p>
      </div>
      <form className="card stack" onSubmit={onCreate}>
        <div className="grid">
          <label>Name<input value={name} onChange={(event) => setName(event.target.value)} required /></label>
          <label>Email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label>
          <label>Password<input value={password} onChange={(event) => setPassword(event.target.value)} required minLength={8} /></label>
          <div>
            <span className="field-label">Role</span>
            <Dropdown label="Role" value={role} options={ROLE_OPTIONS} onChange={setRole} />
          </div>
        </div>
        <label>
          Organisation
          <input value={organisation} onChange={(event) => setOrganisation(event.target.value)} />
        </label>
        <button className="btn" type="submit">Create user</button>
      </form>
      <div className="card table-card">
        <table>
          <thead>
            <tr><th>Name</th><th>Email</th><th>Role</th><th>Active</th></tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id}>
                <td>{user.name}</td>
                <td>{user.email}</td>
                <td>
                  <Dropdown
                    label={`Role for ${user.name}`}
                    value={user.role}
                    options={ROLE_OPTIONS}
                    onChange={(next) => patch(user, { role: next })}
                  />
                </td>
                <td>
                  <button className="btn secondary" onClick={() => patch(user, { is_active: !user.is_active })}>
                    {user.is_active ? "Deactivate" : "Activate"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
