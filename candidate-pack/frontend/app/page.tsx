"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { loadUser } from "../lib/api";

export default function HomePage() {
  const router = useRouter();
  useEffect(() => {
    router.replace(loadUser() ? "/requests" : "/login");
  }, [router]);
  return <p className="muted">Loading…</p>;
}
