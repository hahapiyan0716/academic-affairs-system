import bcrypt from "bcryptjs";
import { Router } from "express";
import { z } from "zod";
import { prisma } from "../../db";
import { HttpError } from "../../errors";
import { currentUser } from "../../middleware/auth";

export const usersRouter = Router();

const PASSWORD = z.string().min(8, "密碼至少 8 個字元").max(100);

const TeacherProfile = z.object({
  teacher_id: z.string().trim().min(1).max(6),
  teacher_name: z.string().trim().min(1).max(50),
  dept_id: z.string().length(4).nullable().optional(),
});

const StudentProfile = z.object({
  student_id: z.string().trim().min(1).max(10),
  student_name: z.string().trim().min(1).max(30),
  dept_id: z.string().length(4),
  grade: z.number().int().min(1).max(7),
  class_code: z.string().trim().min(1).max(2),
  degree: z.union([z.literal(0), z.literal(1)]).default(0),
});

const CreateUserBody = z.discriminatedUnion("role", [
  z.object({ role: z.literal("Admin"), username: z.string().trim().min(3).max(30), password: PASSWORD }),
  z.object({
    role: z.literal("Teacher"),
    username: z.string().trim().min(3).max(30),
    password: PASSWORD,
    profile: TeacherProfile,
  }),
  z.object({
    role: z.literal("Student"),
    username: z.string().trim().min(3).max(30),
    password: PASSWORD,
    profile: StudentProfile,
  }),
]);

const userSelect = {
  user_id: true,
  username: true,
  role: true,
  is_active: true,
  created_at: true,
  last_login_at: true,
  teacher: { select: { teacher_id: true, teacher_name: true, can_open_section: true } },
  student: { select: { student_id: true, student_name: true, dept_id: true, status: true } },
} as const;

// GET /api/admin/users?role=Teacher&q=關鍵字
usersRouter.get("/", async (req, res) => {
  const query = z
    .object({
      role: z.enum(["Admin", "Teacher", "Student"]).optional(),
      q: z.string().trim().max(30).optional(),
    })
    .parse(req.query);

  const users = await prisma.userAccount.findMany({
    where: {
      role: query.role,
      ...(query.q
        ? {
            OR: [
              { username: { contains: query.q } },
              { teacher: { teacher_name: { contains: query.q } } },
              { student: { student_name: { contains: query.q } } },
            ],
          }
        : {}),
    },
    select: userSelect,
    orderBy: [{ role: "asc" }, { username: "asc" }],
  });
  res.json(users);
});

// POST /api/admin/users：建立帳號，教師／學生會在同一個交易內一併建立個人資料
usersRouter.post("/", async (req, res) => {
  const body = CreateUserBody.parse(req.body);
  const password_hash = await bcrypt.hash(body.password, 10);

  const user = await prisma.$transaction(async (tx) => {
    const account = await tx.userAccount.create({
      data: { username: body.username, password_hash, role: body.role },
    });
    if (body.role === "Teacher") {
      await tx.teacher.create({ data: { ...body.profile, user_id: account.user_id } });
    } else if (body.role === "Student") {
      await tx.student.create({
        data: { ...body.profile, status: "Enrolled", user_id: account.user_id },
      });
    }
    return tx.userAccount.findUniqueOrThrow({ where: { user_id: account.user_id }, select: userSelect });
  });

  res.status(201).json(user);
});

// PATCH /api/admin/users/:id：停用／啟用、重設密碼
usersRouter.patch("/:id", async (req, res) => {
  const userId = z.coerce.number().int().parse(req.params.id);
  const body = z
    .object({ is_active: z.boolean().optional(), password: PASSWORD.optional() })
    .refine((b) => b.is_active !== undefined || b.password !== undefined, "至少需提供一個欄位")
    .parse(req.body);

  if (body.is_active === false && String(userId) === currentUser(req).sub) {
    throw new HttpError(400, "不可停用自己的帳號");
  }

  const user = await prisma.userAccount.update({
    where: { user_id: userId },
    data: {
      is_active: body.is_active,
      password_hash: body.password ? await bcrypt.hash(body.password, 10) : undefined,
    },
    select: userSelect,
  });
  res.json(user);
});

// PATCH /api/admin/users/students/:studentId/status：變更學籍（休學／退學的學生不可選課）
usersRouter.patch("/students/:studentId/status", async (req, res) => {
  const body = z.object({ status: z.enum(["Enrolled", "Suspended", "Dropped"]) }).parse(req.body);
  const student = await prisma.student.update({
    where: { student_id: req.params.studentId },
    data: { status: body.status },
  });
  res.json(student);
});
