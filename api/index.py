"""
MJC 七仔 v2 — WhatsApp AI Bot Webhook
Architecture: WATI → Vercel (this file) → Claude API → Supabase → WATI reply
Author: FHA / TomSee  Date: 2026-05
"""

import os, json, re, httpx
from datetime import datetime
from http.server import BaseHTTPRequestHandler
from anthropic import Anthropic
from supabase import create_client, Client

# ── Clients ──────────────────────────────────────────────────────────────────
anthropic   = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
supabase: Client = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_ANON_KEY"],
)

WATI_INSTANCE = os.environ["WATI_INSTANCE_URL"].rstrip("/")   # e.g. https://live-server-XXXXX.wati.io
WATI_TOKEN    = os.environ["WATI_API_TOKEN"]

MAX_HISTORY   = 20   # messages to keep in context

# ── System Prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """你是 MJC 七仔，MJC Leisure Sdn Bhd 专属内部旅游报价 AI 助理。

【角色定位】
- 服务对象：MJC 内部销售团队（非对外客户）
- 主要任务：协助生成马来西亚入境旅游行程报价，计算费用，整理行程亮点

【报价流程】
当客人需要报价时，按以下步骤收集信息：
1. 目的地 / 路线（如：吉隆坡 3 晚 → 槟城 2 晚）
2. 出行日期（入境 & 离境）
3. 人数（成人 / 儿童，国籍）
4. 住宿等级（3星 / 4星 / 5星）
5. 特殊需求（清真认证、专车、导游语言等）

【报价输出格式】
```
【MJC 报价草稿】
路线：...
日期：... 至 ...
人数：...
---
Day 1：[地点] — [活动摘要]
Day 2：...
...
---
费用估算（per pax）：
• 酒店：RM X
• 交通：RM X
• 导览：RM X
• 合计：约 RM X（含 SST）
---
备注：以上为初步估算，实际价格以供应商最终确认为准。
```

【语言规则】
- 默认用中文回复
- 若对方用英文，改用英文
- 专业名词保留英文（如 SST、pax、RON、FIT、GIT）

【安全规则】
- 不对外发送最终报价，所有报价需经 MJC 同事审核后再发给客户
- 不处理付款、不透露供应商联系方式
- 不确定的价格必须加「约」或「待确认」

现在请问需要帮什么？"""

# ── Supabase helpers ──────────────────────────────────────────────────────────

def get_history(phone: str) -> list[dict]:
    """Fetch last MAX_HISTORY messages for this phone number."""
    try:
        res = (supabase.table("conversations")
               .select("role,content")
               .eq("phone_number", phone)
               .order("created_at", desc=True)
               .limit(MAX_HISTORY)
               .execute())
        rows = res.data or []
        rows.reverse()          # oldest first
        return [{"role": r["role"], "content": r["content"]} for r in rows]
    except Exception as e:
        print(f"[Supabase] get_history error: {e}")
        return []


def save_message(phone: str, role: str, content: str):
    try:
        supabase.table("conversations").insert({
            "phone_number": phone,
            "role": role,
            "content": content,
        }).execute()
    except Exception as e:
        print(f"[Supabase] save_message error: {e}")


# ── WATI helper ───────────────────────────────────────────────────────────────

def send_wati_message(phone: str, message: str):
    """Send a text reply via WATI API."""
    url = f"{WATI_INSTANCE}/api/v1/sendSessionMessage/{phone}"
    headers = {"Authorization": f"Bearer {WATI_TOKEN}", "Content-Type": "application/json"}
    payload = {"messageText": message}
    try:
        r = httpx.post(url, json=payload, headers=headers, timeout=15)
        r.raise_for_status()
        print(f"[WATI] sent to {phone}: {r.status_code}")
    except Exception as e:
        print(f"[WATI] send error: {e}")


# ── Claude helper ─────────────────────────────────────────────────────────────

def ask_claude(history: list[dict], user_msg: str) -> str:
    messages = history + [{"role": "user", "content": user_msg}]
    try:
        resp = anthropic.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        return resp.content[0].text
    except Exception as e:
        print(f"[Claude] error: {e}")
        return "抱歉，七仔暂时无法处理，请稍后再试。"


# ── Vercel handler ────────────────────────────────────────────────────────────

class handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        print(f"[HTTP] {format % args}")

    def do_GET(self):
        """Health check."""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok", "bot": "MJC 七仔 v2"}).encode())

    def do_POST(self):
        content_len = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(content_len)

        try:
            data = json.loads(raw)
        except Exception:
            self._respond(400, {"error": "invalid JSON"})
            return

        # ── Parse WATI payload ─────────────────────────────────────────────
        # WATI sends: { waId, text: { body }, ... }
        phone   = data.get("waId") or data.get("phone", "")
        msg_obj = data.get("text") or {}
        user_msg = (msg_obj.get("body") or data.get("body") or "").strip()

        if not phone or not user_msg:
            self._respond(200, {"ok": True, "skip": "no phone or body"})
            return

        # Ignore status messages & bot's own messages
        msg_type = data.get("type", "")
        if msg_type not in ("", "text"):
            self._respond(200, {"ok": True, "skip": f"type={msg_type}"})
            return

        print(f"[七仔] {phone} → {user_msg[:80]}")

        # ── Process ────────────────────────────────────────────────────────
        history  = get_history(phone)
        reply    = ask_claude(history, user_msg)

        save_message(phone, "user",      user_msg)
        save_message(phone, "assistant", reply)

        send_wati_message(phone, reply)

        self._respond(200, {"ok": True})

    def _respond(self, code: int, body: dict):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())
