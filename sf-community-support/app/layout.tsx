import type { Metadata } from "next";
import { Work_Sans, Inter, Caveat } from "next/font/google";
import "./globals.css";

const workSans = Work_Sans({
  subsets: ["latin"],
  variable: "--font-work-sans",
  display: "swap",
});

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const caveat = Caveat({
  subsets: ["latin"],
  variable: "--font-caveat",
  display: "swap",
});

export const metadata: Metadata = {
  title: "SF Small Business Support",
  description: "Save SF's Soul - One mom & pop at a time",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${workSans.variable} ${inter.variable} ${caveat.variable} antialiased bg-[#FDFDF9] text-[#4A5568]`}
      >
        {children}
      </body>
    </html>
  );
}
