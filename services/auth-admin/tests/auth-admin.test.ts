// 整合測試：連 .env 設定的資料庫（需先執行 npm run db:reset 建立種子資料）
import request from "supertest";
import { afterAll, describe, expect, it } from "vitest";
import { createApp } from "../src/app";
import { prisma } from "../src/db";

const app = createApp();
const PASSWORD = process.env.SEED_PASSWORD!;

/** 登入並回傳 cookie 字串 */
async function login(username: string): Promise<string> {
  const res = await request(app).post("/api/auth/login").send({ username, password: PASSWORD });
  expect(res.status).toBe(200);
  const cookie = res.headers["set-cookie"]?.[0];
  expect(cookie).toBeDefined();
  return cookie!.split(";")[0];
}

afterAll(async () => {
  await prisma.$disconnect();
});

describe("認證", () => {
  it("登入成功時設定 httpOnly、SameSite=Lax 的 cookie，且回應不含 token", async () => {
    const res = await request(app).post("/api/auth/login").send({ username: "S001", password: PASSWORD });
    expect(res.status).toBe(200);
    expect(res.body.user).toMatchObject({ role: "Student", student_id: "S001", name: "張飛" });
    expect(JSON.stringify(res.body)).not.toContain("eyJ"); // JWT 只在 cookie 中
    const cookie = res.headers["set-cookie"][0];
    expect(cookie).toMatch(/HttpOnly/);
    expect(cookie).toMatch(/SameSite=Lax/);
  });

  it("密碼錯誤與帳號不存在回傳相同訊息，避免帳號列舉", async () => {
    const wrongPw = await request(app).post("/api/auth/login").send({ username: "S001", password: "wrong-password" });
    const noUser = await request(app).post("/api/auth/login").send({ username: "nobody", password: "wrong-password" });
    expect(wrongPw.status).toBe(401);
    expect(noUser.status).toBe(401);
    expect(wrongPw.body.detail).toBe(noUser.body.detail);
  });

  it("未登入或 token 遭竄改時回傳 401", async () => {
    expect((await request(app).get("/api/auth/me")).status).toBe(401);
    const res = await request(app).get("/api/auth/me").set("Cookie", "access_token=eyJhbGciOiJub25lIn0.e30.");
    expect(res.status).toBe(401);
  });

  it("/api/auth/me 回傳目前登入者", async () => {
    const cookie = await login("T001");
    const res = await request(app).get("/api/auth/me").set("Cookie", cookie);
    expect(res.body.user).toMatchObject({ role: "Teacher", teacher_id: "T001" });
  });
});

describe("管理員權限", () => {
  it("非管理員呼叫 /api/admin/* 回傳 403", async () => {
    for (const username of ["S001", "T001"]) {
      const res = await request(app).get("/api/admin/users").set("Cookie", await login(username));
      expect(res.status).toBe(403);
    }
  });

  it("切換開課權限時同一交易寫入稽核紀錄", async () => {
    const cookie = await login("admin");
    const before = await prisma.teacher.findUniqueOrThrow({ where: { teacher_id: "T005" } });
    const logsBefore = await prisma.teacherPermissionLog.count({ where: { teacher_id: "T005" } });

    try {
      const res = await request(app)
        .patch("/api/admin/teachers/T005/permission")
        .set("Cookie", cookie)
        .send({ can_open_section: !before.can_open_section });
      expect(res.status).toBe(200);
      expect(res.body.can_open_section).toBe(!before.can_open_section);
      expect(await prisma.teacherPermissionLog.count({ where: { teacher_id: "T005" } })).toBe(logsBefore + 1);
    } finally {
      // 還原權限並移除本測試產生的稽核紀錄
      await prisma.teacher.update({
        where: { teacher_id: "T005" },
        data: { can_open_section: before.can_open_section },
      });
      const extra = await prisma.teacherPermissionLog.findMany({
        where: { teacher_id: "T005" },
        orderBy: { log_id: "desc" },
        take: 1,
      });
      await prisma.teacherPermissionLog.deleteMany({ where: { log_id: { in: extra.map((l) => l.log_id) } } });
    }
  });

  it("輸入驗證失敗回傳 400", async () => {
    const res = await request(app)
      .patch("/api/admin/teachers/T005/permission")
      .set("Cookie", await login("admin"))
      .send({ can_open_section: "yes" });
    expect(res.status).toBe(400);
  });

  it("不可停用自己的帳號", async () => {
    const cookie = await login("admin");
    const admin = await prisma.userAccount.findUniqueOrThrow({ where: { username: "admin" } });
    const res = await request(app)
      .patch(`/api/admin/users/${admin.user_id}`)
      .set("Cookie", cookie)
      .send({ is_active: false });
    expect(res.status).toBe(400);
  });

  it("課程庫：重複的課程代碼回傳 409", async () => {
    const res = await request(app)
      .post("/api/admin/courses")
      .set("Cookie", await login("admin"))
      .send({ course_no: "A0001", course_name: "重複", course_type: "Elective", credit: 2 });
    expect(res.status).toBe(409);
  });
});
