import { Router } from "express";
import { z } from "zod";
import { prisma } from "../../db";

export const coursesRouter = Router();

const CourseBody = z.object({
  course_no: z.string().trim().length(5),
  course_name: z.string().trim().min(1).max(50),
  course_type: z.enum(["Required", "Elective"]),
  credit: z.number().int().min(0).max(10),
  dept_id: z.string().length(4).nullable().optional(),
  fields: z.array(z.string().trim().min(1).max(50)).max(10).default([]),
});

const courseInclude = {
  fields: { select: { field_name: true } },
  department: { select: { dept_name: true } },
  _count: { select: { sections: true } },
} as const;

// GET /api/admin/courses：課程庫（含領域、已開班次數）
coursesRouter.get("/", async (_req, res) => {
  const courses = await prisma.course.findMany({
    include: courseInclude,
    orderBy: { course_no: "asc" },
  });
  res.json(courses);
});

coursesRouter.post("/", async (req, res) => {
  const { fields, ...course } = CourseBody.parse(req.body);
  const created = await prisma.course.create({
    data: {
      ...course,
      // 巢狀寫入：Prisma 會在同一個交易內一併建立 CurriculumField
      fields: { create: [...new Set(fields)].map((field_name) => ({ field_name })) },
    },
    include: courseInclude,
  });
  res.status(201).json(created);
});

// PATCH /api/admin/courses/:no：修改課程資訊；fields 有傳入時整批取代
// 課程不提供刪除，改用 is_active 停用，以保留歷年開課紀錄的參照完整性
coursesRouter.patch("/:no", async (req, res) => {
  const body = CourseBody.omit({ course_no: true })
    .partial()
    .extend({ is_active: z.boolean().optional() })
    .parse(req.body);
  const { fields, ...course } = body;

  const updated = await prisma.course.update({
    where: { course_no: req.params.no },
    data: {
      ...course,
      ...(fields
        ? { fields: { deleteMany: {}, create: [...new Set(fields)].map((field_name) => ({ field_name })) } }
        : {}),
    },
    include: courseInclude,
  });
  res.json(updated);
});
