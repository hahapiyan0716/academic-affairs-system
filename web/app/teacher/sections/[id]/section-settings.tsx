"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import type { Section } from "@/types";

/** 班級設定：調整人數上限、停開（只在規劃中／選課中且班級開放時顯示） */
export default function SectionSettings({ section, onChanged }: { section: Section; onChanged: () => void }) {
  // 只記錄使用者輸入中的值；未輸入時顯示伺服器上的人數上限
  const [capacityEdit, setCapacityEdit] = useState<string | null>(null);
  const capacity = capacityEdit ?? String(section.capacity);

  /** 送出班級修改，成功後清除輸入中的值並通知父元件重新讀取 */
  async function patchSection(body: object, msg: string) {
    try {
      await api(`/api/teacher/sections/${section.section_id}`, { method: "PATCH", json: body });
      toast.success(msg);
      setCapacityEdit(null);
      onChanged();
    } catch (e) {
      toast.error((e as Error).message);
    }
  }

  return (
    <Card className="mb-6">
      <CardHeader>
        <CardTitle className="text-base">班級設定</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-wrap items-end gap-3">
        <div className="grid gap-1.5">
          <Label>人數上限（目前已選 {section.enrolled_count} 人）</Label>
          <Input
            type="number"
            className="w-32"
            min={section.enrolled_count || 1}
            value={capacity}
            onChange={(e) => setCapacityEdit(e.target.value)}
          />
        </div>
        <Button variant="outline" onClick={() => patchSection({ capacity: Number(capacity) }, "人數上限已更新")}>
          更新上限
        </Button>
        {/* 已有學生選修時停用按鈕；後端同樣會拒絕 */}
        <Button
          variant="destructive"
          className="ml-auto"
          disabled={section.enrolled_count > 0}
          title={section.enrolled_count > 0 ? "已有學生選修，不可停開" : undefined}
          onClick={() => {
            if (confirm("確定停開此班級？停開後無法恢復，教室時段會被釋放。")) {
              patchSection({ status: "Cancelled" }, "班級已停開");
            }
          }}
        >
          停開班級
        </Button>
      </CardContent>
    </Card>
  );
}
