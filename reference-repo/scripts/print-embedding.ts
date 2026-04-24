import "dotenv/config";
import { embed } from "ai";
import { openai } from "@ai-sdk/openai";

const MODEL = process.env.EMBEDDING_MODEL || "text-embedding-3-small";

async function main() {
  const query = process.argv.slice(2).join(" ") || "healthcare";
  if (!process.env.OPENAI_API_KEY) {
    console.error("OPENAI_API_KEY not set");
    process.exit(1);
  }
  const { embedding } = await embed({
    model: openai.embedding(MODEL),
    value: query,
  });
  const text = `[${embedding.join(",")}]`;
  console.log(text);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
