import { execSync } from "child_process";
import fs from "fs";
import path from "path";

console.log("🚀 [TypeSync] Exporting OpenAPI spec from Backend...");
execSync("python ../scripts/export_openapi.py", { stdio: "inherit" });

const openapiPath = path.resolve("../docs/openapi.json");
const outputPath = path.resolve("./src/types/api.generated.ts");

if (!fs.existsSync(openapiPath)) {
  console.error("❌ openapi.json not found!");
  process.exit(1);
}

console.log("⚡ [TypeSync] Generating TypeScript definitions...");
execSync(`npx openapi-typescript ${openapiPath} -o ${outputPath}`, { stdio: "inherit" });

console.log(`✅ [TypeSync] Successfully generated: ${outputPath}`);
