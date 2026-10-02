import { Router } from "express";
import { z } from "zod";
import { prisma } from "../../db";

export const semestersRouter = Router();

const STATUS = z.enum(["Planning", "Enrolling", "InProgress", "Finished"]);

semestersRouter.get("/", async (_req, res) => {
  const semesters = await prisma.semester.findMany({
    include: { _count: { select: { sections: true } } },
    orderBy: { semester_id: "desc" },
  });
  res.json(semesters);
});

// POST /api/admin/semesters：semester_id 由學年與學期組成，例如 115 學年第 2 學期 → '1152'
semestersRouter.post("/", async (req, res) => {
  const body = z
    .object({ acad_year: z.number().int().min(100).max(999), term: z.number().int().min(1).max(3) })
    .parse(req.body);
  const semester = await prisma.semester.create({
    data: { semester_id: `${body.acad_year}${body.term}`, ...body },
  });
  res.status(201).json(semester);
});

// PATCH /api/admin/semesters/:id：切換學期狀態，或設為「目前學期」
semestersRouter.patch("/:id", async (req, res) => {
  const body = z
    .object({ status: STATUS.optional(), is_current: z.literal(true).optional() })
    .parse(req.body);

  const semester = await prisma.$transaction(async (tx) => {
    // 「目前學期」只能有一個：先清除其他學期的旗標，再設定本學期
    if (body.is_current) {
      await tx.semester.updateMany({ where: { is_current: true }, data: { is_current: false } });
    }
    return tx.semester.update({ where: { semester_id: req.params.id }, data: body });
  });
  res.json(semester);
});
