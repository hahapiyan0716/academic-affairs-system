import type { PoolConfig } from "mariadb";

/**
 * 將 mysql:// 連線字串轉為 mariadb 驅動的設定。
 *
 * MySQL 8 預設以 caching_sha2_password 驗證；在非 TLS 連線下，伺服器重啟後的第一次登入
 * 需要以 RSA 公鑰加密密碼。只在連本機時允許向伺服器索取公鑰（allowPublicKeyRetrieval），
 * 遠端連線則應改用 TLS，避免中間人偽造公鑰。
 */
export function mariadbConfig(databaseUrl: string): PoolConfig {
  const url = new URL(databaseUrl);
  const isLocal = ["localhost", "127.0.0.1", "::1"].includes(url.hostname);
  return {
    host: url.hostname,
    port: Number(url.port || 3306),
    user: decodeURIComponent(url.username),
    password: decodeURIComponent(url.password),
    database: url.pathname.slice(1),
    allowPublicKeyRetrieval: isLocal,
    connectionLimit: 10,
  };
}
