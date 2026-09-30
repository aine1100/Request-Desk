"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, clearSession, loadUser } from "../lib/api";
import { notifySuccess } from "../lib/toast";
import type { User } from "../lib/types";

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const cached = loadUser();
    if (!cached) {
      setUser(null);
      setReady(true);
      return;
    }
    api<User>("/api/auth/me/")
      .then((me) => {
        localStorage.setItem("desk_user", JSON.stringify(me));
        setUser(me);
      })
      .catch(() => {
        clearSession();
        setUser(null);
      })
      .finally(() => setReady(true));
  }, []);

  useEffect(() => {
    if (!ready || pathname === "/login") return;
    if (!user) router.replace("/login");
  }, [ready, user, pathname, router]);

  if (pathname === "/login") {
    return <div className="login-wrap">{children}</div>;
  }

  const staff = user && user.role !== "client";

  return (
    <div className="frame">
      <aside className="sidebar">
        <Link href="/requests" className="brand">
          <div className="mark">RD</div>
          <div>
            <strong>Request Desk</strong>
            <span className="brand-sub">Dataset orders</span>
          </div>
        </Link>
        {user && (
          <nav className="nav">
            <Link className={pathname.startsWith("/requests") ? "active" : ""} href="/requests">
              <IconList />
              Requests
            </Link>
            {user.role === "client" && (
              <Link className={pathname === "/requests/new" ? "active" : ""} href="/requests/new">
                <IconPlus />
                New request
              </Link>
            )}
            {staff && (
              <Link className={pathname.startsWith("/import") ? "active" : ""} href="/import">
                <IconUpload />
                Import episodes
              </Link>
            )}
            {staff && (
              <Link className={pathname.startsWith("/analytics") ? "active" : ""} href="/analytics">
                <IconChart />
                Analytics
              </Link>
            )}
            {user.role === "admin" && (
              <Link className={pathname.startsWith("/users") ? "active" : ""} href="/users">
                <IconPeople />
                Users
              </Link>
            )}
          </nav>
        )}
        {user && (
          <div className="sidebar-foot">
            <div className="who">
              <div className="avatar">{initials(user.name)}</div>
              <div>
                <strong>{user.name}</strong>
                <span>{user.role}</span>
              </div>
            </div>
            <button
              className="btn secondary"
              onClick={() => {
                clearSession();
                setUser(null);
                notifySuccess("Signed out");
                router.replace("/login");
              }}
            >
              Log out
            </button>
          </div>
        )}
      </aside>
      <div className="workspace">
        <header className="topbar">
          <strong>{sectionTitle(pathname)}</strong>
          {user && (
            <div className="topbar-user">
              <div className="avatar">{initials(user.name)}</div>
              <div>
                <strong>{user.name}</strong>
                <span>{user.role}</span>
              </div>
            </div>
          )}
        </header>
        <div className="page">{ready ? children : <p className="muted">Loading…</p>}</div>
      </div>
    </div>
  );
}

function sectionTitle(pathname: string) {
  if (pathname.startsWith("/requests/new")) return "New request";
  if (/^\/requests\/\d+/.test(pathname)) return "Request";
  if (pathname.startsWith("/requests")) return "Requests";
  if (pathname.startsWith("/import")) return "Import episodes";
  if (pathname.startsWith("/analytics")) return "Analytics";
  if (pathname.startsWith("/users")) return "Users";
  return "Request Desk";
}

function initials(name: string) {
  return name
    .split(" ")
    .slice(0, 2)
    .map((part) => part[0] || "")
    .join("")
    .toUpperCase();
}

function IconList() {
  return (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path d="M4 5h12M4 10h12M4 15h8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

function IconPlus() {
  return (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path d="M10 4v12M4 10h12" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

function IconUpload() {
  return (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path d="M10 13V5M7 8l3-3 3 3M4 15h12" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function IconChart() {
  return (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path d="M4 16V9M10 16V4M16 16v-5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

function IconPeople() {
  return (
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <circle cx="8" cy="7" r="2.2" stroke="currentColor" strokeWidth="1.6" />
      <path d="M4.5 15c.4-2 1.8-3 3.5-3s3.1 1 3.5 3M13 8.2a1.8 1.8 0 1 1 0-3.6M14.2 12c1.2.3 2 .9 2.3 2.2" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}
