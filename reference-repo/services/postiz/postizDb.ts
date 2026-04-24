import "server-only";
import postgres from "postgres";

if (!process.env.POSTIZ_DB_URL) {
  throw new Error("POSTIZ_DB_URL is not defined");
}

// Create singleton connection
export const postizDb = postgres(process.env.POSTIZ_DB_URL, {
  max: 10, // Connection pool size
  idle_timeout: 45,
  connect_timeout: 20,
  max_lifetime: 1800,
});
