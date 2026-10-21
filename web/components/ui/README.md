# 共用 UI 元件

此資料夾是專案的 UI 基礎元件庫，主要由 shadcn/ui 產生。這些檔案不是完整頁面，也不處理加選、退選或建立帳號等業務邏輯；`app` 與 `components` 裡的功能元件會組合這些基礎元件，建立實際操作畫面。

shadcn/ui 會把元件原始碼直接放進專案，而不是將所有實作隱藏在 npm 套件裡。目前元件依照 `components.json` 使用 `radix-nova` 樣式、neutral 基準色、CSS 變數與 Lucide 圖示。若要由 shadcn/ui 重新產生元件，可使用 `npx shadcn add <名稱> --overwrite`；此指令會覆寫對應檔案，執行前應先確認差異。

## 元件用途

| 檔案 | 用途 | 專案中的例子 |
| --- | --- | --- |
| `badge.tsx` | 小型狀態標籤 | 中選、已退選、衝堂、學期狀態 |
| `button.tsx` | 按鈕及不同外觀、尺寸 | 加選、退選、登出 |
| `card.tsx` | 卡片與內容區塊 | 課程列表、表單外框 |
| `checkbox.tsx` | 核取方塊 | 選擇共同授課教師 |
| `dialog.tsx` | 對話框／彈出視窗 | 新增帳號、修改密碼 |
| `input.tsx` | 文字輸入框 | 搜尋課名、課號或教師 |
| `label.tsx` | 表單欄位標籤 | 帳號、密碼等欄位名稱 |
| `select.tsx` | 下拉選單 | 選擇課程領域或學期 |
| `separator.tsx` | 水平或垂直分隔線 | 區隔不同內容 |
| `sonner.tsx` | 全域 Toast 通知容器 | 顯示操作成功或失敗訊息 |
| `switch.tsx` | 布林開關 | 啟用或停用帳號、課程及開課權限 |
| `table.tsx` | 表格及表頭、資料列、儲存格 | 課程、教師、時段列表 |
| `tabs.tsx` | 分頁標籤 | 在同一畫面切換不同內容 |

## 底層技術

- Tailwind CSS：控制顏色、尺寸、間距、圓角及響應式外觀。
- Radix UI：提供 Dialog、Select、Switch 等元件的互動行為與無障礙支援。
- Lucide React：提供勾選、警告、關閉等圖示。
- class-variance-authority（CVA）：管理 Button、Badge 等元件的外觀與尺寸 variants。
- `cn()`：合併條件式 CSS class。
- Sonner：顯示全域 Toast 通知。

## 使用方式

頁面和功能元件透過 `@/components/ui/*` 路徑引用需要的元件：

```tsx
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export function CourseAction() {
  return (
    <Card className="p-4">
      <Badge>中選</Badge>
      <Button>退選</Button>
    </Card>
  );
}
```

簡單來說，`components/ui` 是共用的「UI 零件庫」，頁面再依功能需求組合這些零件。
