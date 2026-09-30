"use client";

import { useEffect } from "react";
import { Toaster } from "react-hot-toast";
import { showFlash } from "../lib/toast";

export function AppToaster() {
  useEffect(() => {
    showFlash();
  }, []);

  return (
    <Toaster
      position="bottom-center"
      toastOptions={{
        duration: 4000,
        style: {
          background: "#1a1a1a",
          color: "#ffffff",
          borderRadius: "12px",
          fontSize: "13px",
        },
        success: {
          iconTheme: { primary: "#ffffff", secondary: "#1a1a1a" },
        },
        error: {
          iconTheme: { primary: "#ffb4b0", secondary: "#1a1a1a" },
        },
      }}
    />
  );
}
