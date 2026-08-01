import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { NextIntlClientProvider } from 'next-intl';
import { getLocale, getMessages } from 'next-intl/server';
import { AppShell } from "@/components/AppShell";
import { Providers } from "@/components/providers/Providers";
import { StaffingProvider } from "@/lib/staffing";
import "../globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "----font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "FinanceIntel Dashboard",
  description: "Financial Intelligence for Media Buyers",
};

export default async function RootLayout({
  children,
  params,
}: Readonly<{
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}>) {
  const locale = await getLocale();
  const messages = await getMessages();

  return (
    <html
      lang={locale}
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <NextIntlClientProvider messages={messages}>
          <Providers>
            <StaffingProvider>
              <AppShell>
                {children}
              </AppShell>
            </StaffingProvider>
          </Providers>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
