import { createApp } from "./app";
import { prisma } from "./db";
import { env } from "./env";

const server = createApp().listen(env.PORT, () => {
  console.log(`auth-admin 服務已啟動：http://localhost:${env.PORT}`);
});

// 優雅關閉：先停止接受新連線，再釋放資料庫連線池
for (const signal of ["SIGINT", "SIGTERM"] as const) {
  process.on(signal, () => {
    server.close(async () => {
      await prisma.$disconnect();
      process.exit(0);
    });
  });
}
