// 錄製 ISO27001_mindmap.mp4：錄下 index.html?kiosk&rec 的畫面，網頁會在每一格畫面底部印上當下的動畫時間（條碼），
// 再依條碼把每一格放到旁白時間軸上的正確位置，確保聲音、畫面與字幕同步。
//
//   npm i -g playwright            （或使用已安裝的 Playwright）
//   pip install imageio-ffmpeg pillow numpy
//   node tools/record_video.js
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path'), { execFileSync } = require('child_process');

const ROOT = path.resolve(__dirname, '..');
const OUT = process.env.REC_OUT || path.join(ROOT, 'ISO27001_mindmap.mp4');
const TMP = fs.mkdtempSync(path.join(require('os').tmpdir(), 'iso-rec-'));
const FF = execFileSync('python3', ['-c', 'import imageio_ffmpeg as f;print(f.get_ffmpeg_exe())']).toString().trim();

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 916 }, ignoreHTTPSErrors: true });
  const page = await ctx.newPage();
  await page.goto('file://' + path.join(ROOT, 'index.html') + '?kiosk&rec&paused');
  await page.waitForTimeout(3000);
  const total = Math.min(await page.evaluate(() => TOTAL), Number(process.env.REC_LIMIT || 1e9));

  const files = [];
  const cdp = await ctx.newCDPSession(page);
  cdp.on('Page.screencastFrame', f => {
    const file = path.join(TMP, `f${String(files.length).padStart(6, '0')}.jpg`);
    fs.writeFileSync(file, Buffer.from(f.data, 'base64'));
    files.push(file);
    cdp.send('Page.screencastFrameAck', { sessionId: f.sessionId }).catch(() => {});
  });
  await cdp.send('Page.startScreencast', { format: 'jpeg', quality: 90, maxWidth: 1600, maxHeight: 916, everyNthFrame: 1 });
  await page.waitForTimeout(800);
  await page.evaluate(() => window.__startAt());
  process.stdout.write(`recording ${total.toFixed(1)}s ...\n`);
  await page.waitForTimeout(total * 1000 + 1500);
  await cdp.send('Page.stopScreencast');
  await browser.close();

  // read the time stamp of every frame
  fs.writeFileSync(path.join(TMP, 'files.json'), JSON.stringify(files));
  const times = JSON.parse(execFileSync('python3', ['-c', `
import json,sys,numpy as np
from PIL import Image
out=[]
for f in json.load(open(sys.argv[1])):
    row=np.asarray(Image.open(f).convert('L'))[908]
    bits=[int(row[int((i+.5)*1600/24)]>128) for i in range(24)]
    out.append(sum(b<<(23-i) for i,b in enumerate(bits))/1000)
print(json.dumps(out))`, path.join(TMP, 'files.json')], { maxBuffer: 1 << 26 }).toString());

  // keep frames in time order; each is shown from its own time until the next one
  let seq = files.map((file, i) => ({ file, t: times[i] })).filter(f => f.t <= total);
  const lastZero = seq.map(f => f.t).lastIndexOf(0);
  seq = seq.slice(Math.max(0, lastZero)).filter((f, i, a) => i === 0 || f.t > a[i - 1].t);
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
    '-vf', 'crop=1600:900:0:0,fps=30,format=yuv420p', '-c:v', 'libx264', '-preset', 'slow', '-crf', '24',
    '-c:a', 'aac', '-b:a', '96k', '-t', String(total), '-movflags', '+faststart', OUT], { stdio: 'inherit' });
  fs.rmSync(TMP, { recursive: true, force: true });
  console.log('written', OUT);
})();
