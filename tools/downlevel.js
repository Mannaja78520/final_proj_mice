// Lower new JavaScript syntax (?. ?? class fields ...) to what old browsers run.
// Asked 2026-11-20: an Android TV with Chrome 75 could not start Studio or Home.
// Reads JS on stdin, writes JS on stdout. Target = argv[2] (default chrome70).
// Used by tools/build_web.py; needs `npm install` in tools/ (esbuild, pinned).
const fs = require("fs");
const path = require("path");
let esbuild;
try { esbuild = require(path.join(__dirname, "node_modules", "esbuild")); }
catch (e) { process.stderr.write("esbuild missing: run npm install in tools/\n"); process.exit(3); }
const src = fs.readFileSync(0, "utf8");
const out = esbuild.transformSync(src, {target: process.argv[2] || "chrome70", charset: "utf8", legalComments: "none"});
process.stdout.write(out.code);
