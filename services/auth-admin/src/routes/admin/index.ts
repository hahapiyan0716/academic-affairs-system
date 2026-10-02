import { Router } from "express";
import { prisma } from "../../db";
import { requireAuth, requireRole } from "../../middleware/auth";
import { coursesRouter } from "./courses";
import { semestersRouter } from "./semesters";
import { teachersRouter } from "./teachers";
import { usersRouter } from "./users";

export const adminRouter = Router();

// 所有 /api/admin/* 一律需要 Admin 身分
adminRouter.use(requireAuth, requireRole("Admin"));

adminRouter.use("/users", usersRouter);
adminRouter.use("/teachers", teachersRouter);
adminRouter.use("/courses", coursesRouter);
adminRouter.use("/semesters", semestersRouter);

adminRouter.get("/departments", async (_req, res) => {
  res.json(await prisma.department.findMany({ orderBy: { dept_id: "asc" } }));
});

// 儀表板統計
adminRouter.get("/stats", async (_req, res) => {
  const [users, teachers, students, courses, current] = await Promise.all([
    prisma.userAccount.count(),
    prisma.teacher.count({ where: { can_open_section: true } }),
    prisma.student.count({ where: { status: "Enrolled" } }),
    prisma.course.count({ where: { is_active: true } }),
    prisma.semester.findFirst({
      where: { is_current: true },
      include: { _count: { select: { sections: true } } },
    }),
  ]);
  res.json({
    users,
    teachers_with_permission: teachers,
    enrolled_students: students,
    active_courses: courses,
    current_semester: current,
  });
});
