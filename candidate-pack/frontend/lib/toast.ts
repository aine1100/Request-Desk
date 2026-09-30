"use client";

import toast from "react-hot-toast";

const FLASH_KEY = "desk_flash";

export function notify(message: string) {
  toast(message);
}

export function notifySuccess(message: string) {
  toast.success(message);
}

export function notifyError(message: string) {
  toast.error(message);
}

export function notifyErrorFrom(err: unknown, fallback: string) {
  notifyError(err instanceof Error ? err.message : fallback);
}

export function flashSuccess(message: string) {
  sessionStorage.setItem(FLASH_KEY, JSON.stringify({ message, type: "success" }));
}

export function showFlash() {
  const raw = sessionStorage.getItem(FLASH_KEY);
  if (!raw) return;
  sessionStorage.removeItem(FLASH_KEY);
  try {
    const parsed = JSON.parse(raw) as { message?: string; type?: string };
    if (!parsed.message) return;
    if (parsed.type === "error") toast.error(parsed.message);
    else toast.success(parsed.message);
  } catch {
    sessionStorage.removeItem(FLASH_KEY);
  }
}
