import { PrismaMariaDb } from "@prisma/adapter-mariadb";
import { mariadbConfig } from "./db-config";
import { PrismaClient } from "./generated/prisma/client";
import { env } from "./env";

// Prisma 7 改用 Driver Adapter 連線；MySQL 使用官方 mariadb 驅動
const adapter = new PrismaMariaDb(mariadbConfig(env.DATABASE_URL));

export const prisma = new PrismaClient({ adapter });
