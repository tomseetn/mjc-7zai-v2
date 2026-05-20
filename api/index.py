"""
MJC 七仔 v2 — All-in-one handler
GET  /            → Demo Chat UI (HTML)
POST /api/chat    → Demo chat endpoint (JSON)
POST /api/webhook → WATI webhook handler (JSON)
GET  /health      → Health check (JSON)
Author: FHA / TomSee  Date: 2026-05
"""

import os, json, httpx
from http.server import BaseHTTPRequestHandler
from anthropic import Anthropic

# ── Lazy-init clients ─────────────────────────────────────────────────────────
_anthropic = None
_supabase  = None

def get_anthropic():
    global _anthropic
    if _anthropic is None:
        _anthropic = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _anthropic

def get_supabase():
    global _supabase
    if _supabase is None:
        from supabase import create_client
        _supabase = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_ANON_KEY"],
        )
    return _supabase

MAX_HISTORY = 20

# ── System Prompts ────────────────────────────────────────────────────────────
SYSTEM_DEMO = """你是 MJC 七仔，MJC Leisure Sdn Bhd 专属内部旅游报价 AI 助理。

【角色定位】
- 服务对象：MJC 内部销售团队（非对外客户）
- 主要任务：协助生成马来西亚入境旅游行程报价，计算费用，整理行程亮点

【报价流程】
当需要报价时，按步骤收集：目的地/路线、出行日期、人数（成人/儿童）、住宿等级、特殊需求

【报价输出格式】
【MJC 报价草稿】
路线：...  日期：... 人数：...
---
Day 1：[地点] — [活动摘要]
...
---
费用估算（per pax）：酒店 RM X / 交通 RM X / 导览 RM X / 合计约 RM X（含 SST）
备注：以上为初步估算，实际价格以供应商最终确认为准。

【语言】默认中文，英文问就英文答
【安全】所有报价需经 MJC 同事审核后再发给客户"""

SYSTEM_WATI = SYSTEM_DEMO  # same for webhook

# ── Demo Chat UI HTML ─────────────────────────────────────────────────────────
HTML = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MJC 七仔 Demo</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #f0f2f5; height: 100vh; display: flex; flex-direction: column;
         align-items: center; justify-content: center; }
  .chat-container { width: 100%; max-width: 480px; height: 90vh; background: #fff;
                    border-radius: 16px; box-shadow: 0 4px 24px rgba(0,0,0,0.12);
                    display: flex; flex-direction: column; overflow: hidden; }
  .header { background: #075E54; color: white; padding: 16px 20px;
            display: flex; align-items: center; gap: 12px; }
  .avatar { width: 40px; height: 40px; background: #25D366; border-radius: 50%;
            display: flex; align-items: center; justify-content: center; font-size: 20px; }
  .header-info h3 { font-size: 16px; font-weight: 600; }
  .header-info p { font-size: 12px; opacity: 0.8; }
  .messages { flex: 1; overflow-y: auto; padding: 16px; display: flex;
              flex-direction: column; gap: 8px;
              background: #E5DDD5; }
  .msg { max-width: 75%; padding: 8px 12px; border-radius: 8px; font-size: 14px;
         line-height: 1.5; word-wrap: break-word; }
  .msg.bot  { background: #fff; align-self: flex-start; border-top-left-radius: 2px;
              box-shadow: 0 1px 2px rgba(0,0,0,0.1); }
  .msg.user { background: #DCF8C6; align-self: flex-end; border-top-right-radius: 2px;
              box-shadow: 0 1px 2px rgba(0,0,0,0.1); }
  .msg.typing { background: #fff; align-self: flex-start; color: #999; font-style: italic; }
  .msg pre { white-space: pre-wrap; font-family: inherit; font-size: 13px; }
  .input-area { padding: 12px 16px; background: #f0f2f5; display: flex; gap: 8px; align-items: flex-end; }
  textarea { flex: 1; padding: 10px 14px; border: none; border-radius: 20px; outline: none;
             font-size: 14px; font-family: inherit; resize: none; max-height: 120px;
             background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
  button { width: 44px; height: 44px; background: #075E54; color: white; border: none;
           border-radius: 50%; cursor: pointer; font-size: 18px; display: flex;
           align-items: center; justify-content: center; flex-shrink: 0;
           transition: background 0.2s; }
  button:hover { background: #128C7E; }
  button:disabled { background: #ccc; cursor: not-allowed; }
  .demo-badge { text-align: center; padding: 6px; font-size: 11px; color: #999; background: #f0f2f5; }
</style>
</head>
<body>
<div class="chat-container">
  <div class="header">
    <div class="avatar">🤖</div>
    <div class="header-info">
      <h3>MJC 七仔</h3>
      <p>内部旅游报价助理 · Demo 版</p>
    </div>
  </div>
  <div class="messages" id="messages">
    <div class="msg bot">你好！我是 MJC 七仔 👋<br>请问需要帮你做什么报价？</div>
  </div>
  <div class="demo-badge">⚡ Demo 演示版 — Powered by Claude AI + FHA</div>
  <div class="input-area">
    <textarea id="input" placeholder="输入消息..." rows="1"
      onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();send();}"></textarea>
    <button id="sendBtn" onclick="send()">➤</button>
  </div>
</div>
<script>
const history = [];
async function send() {
  const input = document.getElementById('input');
  const msg = input.value.trim();
  if (!msg) return;
  addMsg(msg, 'user');
  input.value = ''; input.style.height = 'auto';
  document.getElementById('sendBtn').disabled = true;
  const typing = addMsg('七仔正在思考...', 'typing');
  try {
    history.push({ role: 'user', content: msg });
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: history })
    });
    const data = await res.json();
    typing.remove();
    const reply = data.reply || '抱歉，出错了，请重试';
    history.push({ role: 'assistant', content: reply });
    addMsg(reply, 'bot');
  } catch(e) {
    typing.remove();
    addMsg('连接错误，请检查网络', 'bot');
  }
  document.getElementById('sendBtn').disabled = false;
}
function addMsg(text, type) {
  const div = document.createElement('div');
  div.className = 'msg ' + type;
  div.innerHTML = text.replace(/\\n/g,'<br>').replace(/```([\\s\\S]*?)```/g,'<pre>$1</pre>');
  document.getElementById('messages').appendChild(div);
  div.scrollIntoView({ behavior: 'smooth' });
  return div;
}
document.getElementById('input').addEventListener('input', function() {
  this.style.height = 'auto';
  this.style.height = Math.min(this.scrollHeight, 120) + 'px';
});
</script>
</body>
</html>"""

# ── Supabase helpers ──────────────────────────────────────────────────────────

def get_history(phone: str) -> list:
    try:
        sb = get_supabase()
        res = (sb.table("conversations")
               .select("role,content")
               .eq("phone_number", phone)
               .order("created_at", desc=True)
               .limit(MAX_HISTORY)
               .execute())
        rows = res.data or []
        rows.reverse()
        return [{"role": r["role"], "content": r["content"]} for r in rows]
    except Exception as e:
        print(f"[Supabase] get_history error: {e}")
        return []

def save_message(phone: str, role: str, content: str):
    try:
        get_supabase().table("conversations").insert({
            "phone_number": phone, "role": role, "content": content,
        }).execute()
    except Exception as e:
        print(f"[Supabase] save_message error: {e}")

# ── WATI helper ───────────────────────────────────────────────────────────────

def send_wati_message(phone: str, message: str):
    instance = os.environ.get("WATI_INSTANCE_URL", "").rstrip("/")
    token    = os.environ.get("WATI_API_TOKEN", "")
    if not instance or not token:
        print("[WATI] env vars not set, skipping")
        return
    try:
        r = httpx.post(
            f"{instance}/api/v1/sendSessionMessage/{phone}",
            json={"messageText": message},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=15,
        )
        r.raise_for_status()
    except Exception as e:
        print(f"[WATI] send error: {e}")

# ── Claude helper ─────────────────────────────────────────────────────────────

def ask_claude(messages: list, system: str) -> str:
    try:
        resp = get_anthropic().messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=system,
            messages=messages[-20:],
        )
        return resp.content[0].text
    except Exception as e:
        print(f"[Claude] error: {e}")
        return "抱歉，七仔暂时无法处理，请稍后再试。"

# ── Vercel handler (all-in-one) ───────────────────────────────────────────────

class handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        print(f"[HTTP] {format % args}")

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/demo"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML.encode("utf-8"))
        else:
            # health check for /health or /api/webhook GET
            self._respond(200, {"status": "ok", "bot": "MJC 七仔 v2"})

    def do_POST(self):
        path = self.path.split("?")[0]
        content_len = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(content_len)
        try:
            data = json.loads(raw)
        except Exception:
            self._respond(400, {"error": "invalid JSON"})
            return

        if path == "/api/chat":
            # Demo UI chat
            messages = data.get("messages", [])
            if not messages:
                self._respond(400, {"error": "no messages"})
                return
            reply = ask_claude(messages, SYSTEM_DEMO)
            self._respond(200, {"reply": reply})

        elif path in ("/api/webhook", "/webhook"):
            # WATI webhook
            phone    = data.get("waId") or data.get("phone", "")
            msg_obj  = data.get("text") or {}
            user_msg = (msg_obj.get("body") or data.get("body") or "").strip()
            if not phone or not user_msg:
                self._respond(200, {"ok": True, "skip": "no phone or body"})
                return
            if data.get("type", "") not in ("", "text"):
                self._respond(200, {"ok": True, "skip": "non-text"})
                return
            print(f"[七仔] {phone} → {user_msg[:80]}")
            history  = get_history(phone)
            reply    = ask_claude(history + [{"role":"user","content":user_msg}], SYSTEM_WATI)
            save_message(phone, "user", user_msg)
            save_message(phone, "assistant", reply)
            send_wati_message(phone, reply)
            self._respond(200, {"ok": True})

        else:
            self._respond(404, {"error": "not found"})

    def _respond(self, code: int, body: dict):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())
