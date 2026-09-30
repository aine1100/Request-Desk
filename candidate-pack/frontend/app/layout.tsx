import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { AppToaster } from "../components/AppToaster";
import { Shell } from "../components/Shell";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], display: "swap" });

export const metadata: Metadata = {
  title: "Dataset Request Desk",
  description: "Internal desk for robot episode dataset requests",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <script
          dangerouslySetInnerHTML={{
            __html: `if (navigator.serviceWorker) {
              navigator.serviceWorker.getRegistrations().then(function (registrations) {
                registrations.forEach(function (registration) { registration.unregister(); });
              });
            }`,
          }}
        />
        <AppToaster />
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
