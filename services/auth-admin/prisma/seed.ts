// 種子程式：先執行 seed.sql 匯入業務資料，再以 bcrypt 建立登入帳號並與教師／學生連結
// 執行方式：npm run db:seed（需在空的資料庫上執行，通常搭配 npm run db:reset）
import "dotenv/config";
import bcrypt from "bcryptjs";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { PrismaMariaDb } from "@prisma/adapter-mariadb";
import { mariadbConfig } from "../src/db-config";
import { PrismaClient } from "../src/generated/prisma/client";

const databaseUrl = process.env.DATABASE_URL;
const seedPassword = process.env.SEED_PASSWORD;
if (!databaseUrl) throw new Error("缺少 DATABASE_URL");
if (!seedPassword || seedPassword.length < 8) {
  throw new Error("請在 .env 設定 SEED_PASSWORD（至少 8 個字元），作為所有種子帳號的初始密碼");
}

const prisma = new PrismaClient({ adapter: new PrismaMariaDb(mariadbConfig(databaseUrl)) });

/** 去除註解後以「行尾分號」切分成單一敘述（Driver Adapter 一次只能執行一個敘述） */
function splitSqlStatements(sql: string): string[] {
  return sql
    .split(/\r?\n/)
    .map((line) => line.replace(/--.*$/, "").trimEnd())
    .join("\n")
    .split(/;\s*(?:\n|$)/)
    .map((s) => s.trim())
    .filter(Boolean);
}

async function main() {
  const sqlPath = fileURLToPath(new URL("./seed.sql", import.meta.url));
  const statements = splitSqlStatements(readFileSync(sqlPath, "utf8"));

  await prisma.$transaction(
    async (tx) => {
      for (const statement of statements) {
        await tx.$executeRawUnsafe(statement);
      }
    },
    { timeout: 60_000 },
  );
  console.log(`已執行 seed.sql：${statements.length} 個敘述`);

  const password_hash = await bcrypt.hash(seedPassword!, 10);

  const admin = await prisma.userAccount.create({
    data: { username: "admin", password_hash, role: "Admin" },
  });

  const teachers = await prisma.teacher.findMany({ orderBy: { teacher_id: "asc" } });
  for (const t of teachers) {
    await prisma.userAccount.create({
      data: {
        username: t.teacher_id,
        password_hash,
        role: "Teacher",
        teacher: { connect: { teacher_id: t.teacher_id } },
      },
    });
  }

  const students = await prisma.student.findMany({ orderBy: { student_id: "asc" } });
  for (const s of students) {
    await prisma.userAccount.create({
      data: {
        username: s.student_id,
        password_hash,
        role: "Student",
        student: { connect: { student_id: s.student_id } },
      },
    });
  }

  // 為初始具開課權限的教師補上稽核紀錄
  const granted = teachers.filter((t) => t.can_open_section);
  await prisma.teacherPermissionLog.createMany({
    data: granted.map((t) => ({ teacher_id: t.teacher_id, granted: true, changed_by: admin.user_id })),
  });

  console.log(`已建立帳號：admin ×1、教師 ×${teachers.length}、學生 ×${students.length}`);
}

main()
  .catch((err) => {
    console.error(err);
    process.exitCode = 1;
  })
  .finally(() => prisma.$disconnect());
