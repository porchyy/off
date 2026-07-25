import { createServer } from 'node:http';
import { DatabaseSync } from 'node:sqlite';
import { readFile, stat, mkdir } from 'node:fs/promises';
import { join, normalize, extname } from 'node:path';

const root = process.cwd();
// Keep operational data outside the source tree. Override with POSTUREAI_DATA_DIR if needed.
const dataDir = process.env.POSTUREAI_DATA_DIR || 'E:\\PostureAI\\data';
await mkdir(dataDir, { recursive: true });
const dbPath = join(dataDir, 'postureai.sqlite');
const db = new DatabaseSync(dbPath);
db.exec('PRAGMA journal_mode = WAL; PRAGMA busy_timeout = 5000;');
db.exec(`CREATE TABLE IF NOT EXISTS samples (id INTEGER PRIMARY KEY, score REAL NOT NULL, neck REAL, shoulders REAL, torso REAL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS alerts (id INTEGER PRIMARY KEY, severity TEXT NOT NULL, message TEXT NOT NULL, created_at TEXT NOT NULL);`);
const json = (res, status, body) => { res.writeHead(status, {'content-type':'application/json; charset=utf-8'}); res.end(JSON.stringify(body)); };
const types = {'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json; charset=utf-8','.svg':'image/svg+xml'};
async function body(req) { let raw=''; for await (const c of req) { raw += c; if(raw.length > 100000) throw Error('Payload too large'); } return JSON.parse(raw || '{}'); }

createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);
  try {
    if (url.pathname === '/api/samples' && req.method === 'POST') {
      const {score, neck, shoulders, torso} = await body(req);
      if (![score, neck, shoulders, torso].every(Number.isFinite) || score < 0 || score > 100) return json(res,400,{error:'Invalid metrics'});
      db.prepare('INSERT INTO samples (score,neck,shoulders,torso,created_at) VALUES (?,?,?,?,?)').run(score,neck,shoulders,torso,new Date().toISOString());
      return json(res,201,{ok:true});
    }
    if (url.pathname === '/api/alerts' && req.method === 'POST') {
      const {severity,message} = await body(req);
      if (!['caution','risk'].includes(severity) || typeof message !== 'string' || message.length > 160) return json(res,400,{error:'Invalid alert'});
      db.prepare('INSERT INTO alerts (severity,message,created_at) VALUES (?,?,?)').run(severity,message,new Date().toISOString()); return json(res,201,{ok:true});
    }
    if (url.pathname === '/api/summary' && req.method === 'GET') {
      const since = new Date(); since.setHours(0,0,0,0);
      const row = db.prepare('SELECT COUNT(*) AS samples, ROUND(AVG(score)) AS average FROM samples WHERE created_at >= ?').get(since.toISOString());
      const alerts = db.prepare('SELECT id,severity,message,created_at FROM alerts WHERE created_at >= ? ORDER BY id DESC LIMIT 10').all(since.toISOString());
      return json(res,200,{...row, alerts});
    }
    if (url.pathname === '/api/data' && req.method === 'DELETE') { db.exec('DELETE FROM samples; DELETE FROM alerts;'); return json(res,200,{ok:true}); }
    if (req.method !== 'GET' && req.method !== 'HEAD') return json(res,405,{error:'Method not allowed'});
    const pathname = url.pathname === '/' ? '/index.html' : url.pathname;
    const file = normalize(join(root, pathname));
    if (!file.startsWith(root) || file.endsWith('.sqlite') || file.includes('.github')) return json(res,403,{error:'Forbidden'});
    const info = await stat(file); if (!info.isFile()) return json(res,404,{error:'Not found'});
    res.writeHead(200, {'content-type':types[extname(file)] || 'application/octet-stream','cache-control':'no-store'}); if(req.method === 'HEAD') return res.end(); res.end(await readFile(file));
  } catch (error) { console.error(error); json(res,500,{error:'Server error'}); }
}).listen(3000, () => console.log(`PostureAI ready at http://localhost:3000 (database: ${dbPath})`));
