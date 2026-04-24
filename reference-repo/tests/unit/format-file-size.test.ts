import assert from "node:assert/strict";

async function main() {
  // Dynamic import to handle path aliases — formatFileSize is a pure function
  const { formatFileSize } = await import("../../lib/formatFileSize");

  // null → "Unknown"
  assert.equal(formatFileSize(null), "Unknown", "null should return Unknown");

  // NaN → "Unknown"
  assert.equal(formatFileSize(NaN), "Unknown", "NaN should return Unknown");

  // 0 → "0 KB"
  assert.equal(formatFileSize(0), "0 KB", "0 bytes should return 0 KB");

  // 512 KB
  assert.equal(
    formatFileSize(512 * 1024),
    "512 KB",
    "512 * 1024 bytes should return 512 KB"
  );

  // Exactly 1 MB
  assert.equal(
    formatFileSize(1024 * 1024),
    "1.0 MB",
    "1024 * 1024 bytes should return 1.0 MB"
  );

  // 1.5 MB
  assert.equal(
    formatFileSize(1.5 * 1024 * 1024),
    "1.5 MB",
    "1.5 * 1024 * 1024 bytes should return 1.5 MB"
  );

  // 150 MB
  assert.equal(
    formatFileSize(150 * 1024 * 1024),
    "150.0 MB",
    "150 * 1024 * 1024 bytes should return 150.0 MB"
  );

  console.log("✓ All formatFileSize tests passed");
}

main().catch((err) => {
  console.error("Test failed:", err);
  process.exit(1);
});
