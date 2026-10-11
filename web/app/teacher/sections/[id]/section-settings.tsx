"use client";

import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, SECTION_VIEWS, useInvalidate } from "@/lib/api";
import type { Section } from "@/types";

/** 班級設定：調整人數上限、停開（只在規劃中／選課中且班級開放時顯示） */
export default function SectionSettings({ section, rosterPath }: { section: Section; rosterPath: string }) {
  // 只記錄使用者輸入中的值；未輸入時顯示伺服器上的人數上限
  const [capacityEdit, setCapacityEdit] = useState<string | null>(null);
  const capacity = capacityEdit ?? String(section.capacity);
  const invalidate = useInvalidate();

  /** 送出班級修改，成功後重新讀取名單，再清除輸入中的值 */
  const patchSection = useMutation({
    mutationFn: ({ body }: { body: object; msg: string }) =>
      api(`/api/teacher/sections/${section.section_id}`, { method: "PATCH", json: body }),
    onSuccess: async (_, { msg }) => {
      toast.success(msg);
      // 人數上限與停開會反映在我的開課、學生加退選等列表
      await invalidate(rosterPath, ...SECTION_VIEWS);
      setCapacityEdit(null);
    },
    onError: (e) => toast.error(e.message),
  });

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
        <Button
          variant="outline"
          disabled={patchSection.isPending}
          onClick={() => patchSection.mutate({ body: { capacity: Number(capacity) }, msg: "人數上限已更新" })}
        >
          更新上限
        </Button>
        {/* 已有學生選修時停用按鈕；後端同樣會拒絕 */}
        <Button
          variant="destructive"
          className="ml-auto"
          disabled={section.enrolled_count > 0 || patchSection.isPending}
          title={section.enrolled_count > 0 ? "已有學生選修，不可停開" : undefined}
          onClick={() => {
            if (confirm("確定停開此班級？停開後無法恢復，教室時段會被釋放。")) {
              patchSection.mutate({ body: { status: "Cancelled" }, msg: "班級已停開" });
            }
          }}
        >
          停開班級
        </Button>
      </CardContent>
    </Card>
  );
}
