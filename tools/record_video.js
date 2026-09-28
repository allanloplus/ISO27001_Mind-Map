// 錄製 ISO27001_mindmap.mp4：以 Chrome 螢幕擷取（每張畫面都帶時間戳記）錄下 index.html?kiosk，
// 再依時間戳記把畫面對齊到旁白時間軸，確保聲音與畫面、字幕同步。
//
//   npm i -g playwright   （或使用已安裝的 Playwright）
//   pip install imageio-ffmpeg
//   node tools/record_video.js
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path'), { execFileSync } = require('child_process');

const ROOT = path.resolve(__dirname, '..');
const OUT = process.env.REC_OUT || path.join(ROOT, 'ISO27001_mindmap.mp4');
const TMP = fs.mkdtempSync(path.join(require('os').tmpdir(), 'iso-rec-'));
const FF = execFileSync('python3', ['-c', 'import imageio_ffmpeg as f;print(f.get_ffmpeg_exe())']).toString().trim();

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 900 }, ignoreHTTPSErrors: true });
  const page = await ctx.newPage();
  await page.goto('file://' + path.join(ROOT, 'index.html') + '?kiosk&paused');
  await page.waitForTimeout(3000);
  const total = Math.min(await page.evaluate(() => TOTAL), Number(process.env.REC_LIMIT || 1e9));

  const frames = [];
  const cdp = await ctx.newCDPSession(page);
  cdp.on('Page.screencastFrame', async f => {
    const file = path.join(TMP, `f${String(frames.length).padStart(6, '0')}.jpg`);
    fs.writeFileSync(file, Buffer.from(f.data, 'base64'));
    frames.push({ file, ts: f.metadata.timestamp * 1000 });
    cdp.send('Page.screencastFrameAck', { sessionId: f.sessionId }).catch(() => {});
  });
  await cdp.send('Page.startScreencast', { format: 'jpeg', quality: 88, maxWidth: 1600, maxHeight: 900, everyNthFrame: 1 });
  await page.waitForTimeout(800);
  const start = await page.evaluate(() => window.__startAt());
  process.stdout.write(`recording ${total.toFixed(1)}s ...\n`);
  await page.waitForTimeout(total * 1000 + 1500);
  await cdp.send('Page.stopScreencast');
  await browser.close();

  // concat list: each frame shown from its own timestamp until the next one
  const rel = frames.map(f => ({ file: f.file, t: (f.ts - start) / 1000 }));
  let first = 0;
  for (let i = 0; i < rel.length; i++) if (rel[i].t <= 0) first = i;
  const seq = rel.slice(first).filter(f => f.t < total);
  seq[0].t = 0;
  let list = '';
  seq.forEach((f, i) => {
    const next = i + 1 < seq.length ? seq[i + 1].t : total;
    list += `file '${f.file}'\nduration ${Math.max(0.001, next - f.t).toFixed(4)}\n`;
  });
  list += `file '${seq[seq.length - 1].file}'\n`;
  fs.writeFileSync(path.join(TMP, 'list.txt'), list);
  console.log(`${seq.length} frames, avg ${(seq.length / total).toFixed(1)} fps`);

  execFileSync(FF, ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', path.join(TMP, 'list.txt'),
    '-i', path.join(ROOT, 'assets/narration.mp3'), '-map', '0:v', '-map', '1:a',
    '-vf', 'fps=30,format=yuv420p', '-c:v', 'libx264', '-preset', 'slow', '-crf', '24',
    '-c:a', 'aac', '-b:a', '96k', '-t', String(total), '-movflags', '+faststart', OUT], { stdio: 'inherit' });
  fs.rmSync(TMP, { recursive: true, force: true });
  console.log('written', OUT);
})();
