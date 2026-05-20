"""
MJC 七仔 Demo Chat UI — 网页版测试界面
GET / → 返回聊天 HTML 页面
POST /api/chat → 直接调用 Claude，返回 JSON 回复
"""
import os, json
from http.server import BaseHTTPRequestHandler
from anthropic import Anthropic

anthropic = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SYSTEM_PROMPT = """你是 MJC 七仔，MJC Leisure Sdn Bhd 专属内部旅游报价 AI 助理。

【角色定位】
- 服务对象：MJC 内部销售团队
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

HTML = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MJC 七仔 Demo</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #f0f2f5; height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; }
  .chat-container { width: 100%; max-width: 480px; height: 90vh; background: #fff;
                    border-radius: 16px; box-shadow: 0 4px 24px rgba(0,0,0,0.12);
                    display: flex; flex-direction: column; overflow: hidden; }
  .header { background: #075E54; color: white; padding: 16px 20px;
            display: flex; align-items: center; gap: 12px; }
  .avatar { width: 40px; height: 40px; background: #25D366; border-radius: 50%;
            display: flex; align-items: center; justify-content: center; font-size: 20px; }
  .header-info h3 { font-size: 16px; font-weight: 600; }
  .header-info p { font-size: 12px; opacity: 0.8; }
  .messages { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 8px;
              background: #E5DDD5 url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23b0b0b0' fill-opacity='0.06'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E"); }
  .msg { max-width: 75%; padding: 8px 12px; border-radius: 8px; font-size: 14px; line-height: 1.5; word-wrap: break-word; }
  .msg.bot { background: #fff; align-self: flex-start; border-top-left-radius: 2px; box-shadow: 0 1px 2px rgba(0,0,0,0.1); }
  .msg.user { background: #DCF8C6; align-self: flex-end; border-top-right-radius: 2px; box-shadow: 0 1px 2px rgba(0,0,0,0.1); }
  .msg.typing { background: #fff; align-self: flex-start; color: #999; font-style: italic; }
  .msg pre { white-space: pre-wrap; font-family: inherit; font-size: 13px; }
  .input-area { padding: 12px 16px; background: #f0f2f5; display: flex; gap: 8px; align-items: flex-end; }
  textarea { flex: 1; padding: 10px 14px; border: none; border-radius: 20px; outline: none;
             font-size: 14px; font-family: inherit; resize: none; max-height: 120px; background: #fff;
             box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
  button { width: 44px; height: 44px; background: #075E54; color: white; border: none;
           border-radius: 50%; cursor: pointer; font-size: 18px; display: flex; align-items: center;
           justify-content: center; flex-shrink: 0; transition: background 0.2s; }
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
  input.value = '';
  input.style.height = 'auto';
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
  div.innerHTML = text.replace(/\\n/g, '<br>').replace(/```([\\s\\S]*?)```/g, '<pre>$1</pre>');
  document.getElementById('messages').appendChild(div);
  div.scrollIntoView({ behavior: 'smooth' });
  return div;
}

// Auto-resize textarea
document.getElementById('input').addEventListener('input', function() {
  this.style.height = 'auto';
  this.style.height = Math.min(this.scrollHeight, 120) + 'px';
});
</script>
</body>
</html>"""


class handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        print(f"[Demo] {format % args}")

    def do_GET(self):
        """Serve the chat UI."""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML.encode("utf-8"))

    def do_POST(self):
        """Handle chat messages from the UI."""
        content_len = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(content_len)
        try:
            data = json.loads(raw)
        except Exception:
            self._respond(400, {"error": "invalid JSON"})
            return

        messages = data.get("messages", [])
        if not messages:
            self._respond(400, {"error": "no messages"})
            return

        try:
            resp = anthropic.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=messages[-20:],   # keep last 20 turns
            )
            reply = resp.content[0].text
        except Exception as e:
            print(f"[Claude] error: {e}")
            reply = "抱歉，七仔暂时无法处理，请稍后再试。"

        self._respond(200, {"reply": reply})

    def _respond(self, code, body):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())
