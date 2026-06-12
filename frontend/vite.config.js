import { defineConfig } from "vite";
import { resolve, relative } from "path";
import { readdirSync, statSync, existsSync, mkdirSync, copyFileSync, readFileSync, writeFileSync } from "fs";

const root = process.cwd();
const SKIP = new Set(["node_modules", "dist", "public", ".git"]);

function walk(dir) {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    if (entry.isDirectory() && SKIP.has(entry.name)) return [];
    const full = resolve(dir, entry.name);
    return entry.isDirectory()
      ? walk(full)
      : entry.isFile() && entry.name.endsWith(".html") ? [full] : [];
  });
}

const htmlFiles = walk(root);
const input = Object.fromEntries(
  htmlFiles.map((file) => [
    file === resolve(root, "index.html")
      ? "index"
      : relative(root, file).replace(/\.html$/, ""),
    file,
  ])
);

// classic scripts (assets/*.js) ไม่อยู่ใน module graph ของ Vite → copy เข้า dist เองหลัง build
function copyClassicJs() {
  return {
    name: "copy-classic-js",
    closeBundle() {
      const src = resolve(root, "assets");
      const out = resolve(root, "dist", "assets");
      if (!existsSync(src)) return;
      if (!existsSync(out)) mkdirSync(out, { recursive: true });
      for (const f of readdirSync(src)) {
        if (f.endsWith(".js") && statSync(resolve(src, f)).isFile()) {
          copyFileSync(resolve(src, f), resolve(out, f));
        }
      }
      // cache-busting: ใส่ ?v=<build> ให้ classic scripts ทุก dist HTML
      // (ชื่อไฟล์คงที่ ไม่มี hash → เลี่ยงเบราว์เซอร์/CDN cache เวอร์ชันเก่าหลัง deploy)
      const ver = Date.now().toString(36);
      const distDir = resolve(root, "dist");
      if (existsSync(distDir)) {
        for (const html of walk(distDir)) {
          let t = readFileSync(html, "utf8");
          const n = t.replace(/((?:\.\.\/)?assets\/(?:api|shell|gantt)\.js)(\?v=[^"']*)?/g, `$1?v=${ver}`);
          if (n !== t) writeFileSync(html, n);
        }
      }
    },
  };
}

export default defineConfig({
  plugins: [copyClassicJs()],
  build: {
    rollupOptions: { input },
  },
});
