import { Router } from "express";
import { z } from "zod";
import { prisma } from "../../db";
import { currentUser } from "../../middleware/auth";

export const teachersRouter = Router();

// GET /api/admin/teachers：教師清單與目前的開課權限
teachersRouter.get("/", async (_req, res) => {
  const teachers = await prisma.teacher.findMany({
    select: {
      teacher_id: true,
      teacher_name: true,
      dept_id: true,
      can_open_section: true,
      user: { select: { username: true, is_active: true } },
      permission_logs: {
        orderBy: { changed_at: "desc" },
        take: 1,
        select: { changed_at: true, granted: true, admin: { select: { username: true } } },
      },
    },
    orderBy: { teacher_id: "asc" },
  });
  res.json(teachers);
});

// PATCH /api/admin/teachers/:id/permission：授予或收回開課權限
// 權限變更與稽核紀錄在同一個交易內寫入，確保兩者一致
teachersRouter.patch("/:id/permission", async (req, res) => {
  const { can_open_section } = z.object({ can_open_section: z.boolean() }).parse(req.body);
  const adminId = Number(currentUser(req).sub);

  const teacher = await prisma.$transaction(async (tx) => {
    const updated = await tx.teacher.update({
      where: { teacher_id: req.params.id },
      data: { can_open_section },
    });
    await tx.teacherPermissionLog.create({
      data: { teacher_id: updated.teacher_id, granted: can_open_section, changed_by: adminId },
    });
    return updated;
  });

  res.json(teacher);
});

// GET /api/admin/teachers/:id/permission-logs：權限異動歷程
teachersRouter.get("/:id/permission-logs", async (req, res) => {
  const logs = await prisma.teacherPermissionLog.findMany({
    where: { teacher_id: req.params.id },
    orderBy: { changed_at: "desc" },
    select: { log_id: true, granted: true, changed_at: true, admin: { select: { username: true } } },
  });
  res.json(logs);
});
