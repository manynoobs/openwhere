// The production build must never ship hand-written fixture data.
import { existsSync, readdirSync } from "node:fs";

const dir = new URL("../public/data/fixtures", import.meta.url);
if (existsSync(dir) && readdirSync(dir).length) {
  console.error("Refusing to build: public/data/fixtures/ still has files. Ship real pipeline output only.");
  process.exit(1);
}
