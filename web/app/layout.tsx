import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { QueryProvider } from "@/components/query-provider";
import { Toaster } from "@/components/ui/sonner";
import "./globals.css";

// next/font 在建置時下載字型並自行託管；variable 讓 globals.css 以 CSS 變數引用
// variable 名稱必須與 globals.css 的 @theme 對應：--font-sans 供 font-sans（全站預設字型），
// --font-geist-mono 由 @theme 轉成 --font-mono 供 font-mono
// subsets 只含 latin：Geist 沒有中文字形，中文字會退回作業系統的字型
const geistSans = Geist({
  variable: "--font-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

// Next.js 依此產生 <title> 與 <meta name="description">；子版面或頁面可匯出自己的 metadata 覆寫
export const metadata: Metadata = {
  title: "教務管理系統",
  description: "輕量化教務管理系統：開課、選課、成績與歷年查詢",  // SEO 與社群分享用的描述，也就是 google 搜尋結果的摘要
};

// 這裡的 LayoutProps<"/"> 泛型參數是「此 layout 的路徑」；若有多層 layout，子 layout 的泛型參數是「子 layout 的路徑」
// LayoutProps 是 next typegen 產生的全域型別，不需 import
/** 根版面：所有頁面共用的 <html>／<body>、資料快取（TanStack Query）與全域提示訊息（toast） */
export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    // lang 讓瀏覽器與螢幕閱讀器以繁體中文處理字型與讀音
    // 兩個字型的 variable class 在 <html> 上定義 CSS 變數，整頁都能引用
    <html lang="zh-Hant-TW" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      {/* 至少與視窗等高的直向 flex 容器，子版面可用 flex-1 填滿剩餘高度；bg-muted/30 覆寫 globals.css 的 bg-background */}
      <body className="flex min-h-full flex-col bg-muted/30">
        {/* QueryProvider 是 Client Component，提供 useApiQuery／useMutation 共用的快取 */}
        {/* 也就是說，所有頁面都可以使用相同的資料快取，避免重複發送 API 請求 */}
        <QueryProvider>{children}</QueryProvider>
        {/* 全域只放一個 Toaster，任何頁面呼叫 toast() 都顯示在畫面上方中央 */}
        <Toaster richColors position="top-center" />
      </body>
    </html>
  );
}
