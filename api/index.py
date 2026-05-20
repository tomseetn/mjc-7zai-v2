"""
MJC 七仔 v2 — All-in-one handler
GET  /            → Demo Chat UI (HTML)
POST /api/chat    → Demo chat endpoint (JSON)
POST /api/webhook → WATI webhook handler (JSON)
Author: FHA / TomSee  Date: 2026-05
"""

import os, json, httpx
from http.server import BaseHTTPRequestHandler
from anthropic import Anthropic

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

MJC_LOGO_B64 = 'iVBORw0KGgoAAAANSUhEUgAAAOEAAADhCAMAAAAJbSJIAAABwlBMVEX////+AAD1+SAAAND0+QAAAMwAAADy9BX1+RX1+Q7///vx8wD/+vr///3/9/f8/cv/7e3///X+/un+LCz5+f7/29v/5ub+b2/9/tf+/uL8/cP/xMT/1dX2+kP/4OD7/bb/y8v+XV3r6/v09PT5+4X+np7/rKz6/KH3+lb+VFT+hYX+IyP+dXX+TEz+vb34+nD+//D7/KxERNYVFdFZWdr+fX3+Jyeuruv/tbXW1vX+RUWLAADFxfHi4vj+k5Nzc97+Ojr4+mf5+475+4j+j4+4uO6SkuWFheI5OdWAgOHh4eGTKSn4+2xnbm7JycmkpOmfAAAgINKWluY/QNVOTthfX9ukYWGXnZ3kJiY5UFCbQ0NfX1pTHBzPOzxreXk8PaHQ0T6fnzJ/fj15eEfNzwA5ODg8PHGNjjURES3f4UW4R0ecpKQbGyLGx0oAACwkODilpFI0NK6wUlI/P4wrKyA5AABmOztFRWFaWgMEBBfkAAC2AAEmJgBBLy8gAABPTqmsrRRzKSkuLjw/P00IPT0AGRnKzBMnJjxfX5BVVSxnZ3RMTEw9PChiYrqamafR0o1tAAC9vclxcVw7OxMAAIkYGAB0dtRKAAANaUlEQVR4nO2c+WPTyBXHLXtkpODYOZzEORzbOWyHkDh34pDDDiEEysIGwoaFbgq7S1tg6W7b7QHddlu6ZVvYq6X9f6sZjTTzRpKvRLZp5/MLZiRZ+ubNvPfmzciBgEQikUgkEolEIpFIJBKJRCKRSCQSiUQikUgkEolEIpFIJBKJRCKRSCSS/2O6BxOJWCyWGJzrbvWjnDbdifmdcjKIbPRgfmforZQZ6ctuRWFTT6qApemaFuTRdISSuZ7WPGaDRIaXS0rvMGiL7SQRgtJ4lQjlh1r0tHUzOjmlKFBfx1BBM7pjZTSUHGzZQ9fOyLlpBeub5dpi1yoYD2rcadmD10bfLpGnTK+xtsGdYG3yCCjfxj4nmu1VTH1Zu61jPlm1c0L0YLtKHDmvUCbttrkdrQ7zWT21LSXa5lOULbtxsFCn+WyJnS2U4sqobT5l2Q6AiXJj+gz0civVOElP2fpmRq3GRL7+7slA860UJMC6p6LYAeJk+rDEuVZq4ujcYvLYAOwpn1Cf0U8LrZTFmOT0ZbpoY/fEifVhI7aDP12bZvqm01ZrrmH/AhXmWqjMZJbTxyJgKohOQx+mleIM0iVO35TVQRNJT32apuv2fLCWXoxirdTXt87pm7amEHMF1wGI534omCxP5OZTBkOp3MVyUq+aiestTMG7Bjh9yjmrOeUyAI05H0pOzCfmxCSlI5Grkq9q+SbLsons8vpKfbS5Jy92UENdsJxLeCdgg7mKgxY1R4+DLK+PeZic0OmMXlierz6bna/QV1FLihrpXl7fej9tHoQeRkfBiVhHTV/Y4+2bWuFqujI1GJDIc14bHysWixvFzTHxwISXRNT8os0k0NdrJdm8ATUUvJhwXrmxpNqEFq5cAjJ3znooTDVBE09fCQi0XeiObUAN6QWvnrW5txiyUdWlDe5Y+eyZdlC4DPQpadrMxpGOkqmKueSeGuJE3tq0D3ScPeMmsbm9dBbqy0Roe4oa0DDfRFXPObYQ4jXesA8MGRKdGpvpabqmoECrztRZQLb5anKdl4EZr9jtSTeJqHmlUxgClRXbxQR1Yj7tYs3PAiVuW80xrFCU2LT5U9cMFHjeOkB6KDZfPWWjQ9BRV63mMy4KtVOV4c0a1KfYlV4cxxAquMSGSoypQKIVNgrObqo1pxoVFUZgyZ7IGz4UBXP1d6SbvMKQNRRzToXNKUaJBly2DiQ03D0b+cpNYMRQ3GxNuShsQloaHRAE2j10HqF8o758H3RTGvljDoXNmDwNC/oUuxZaaFyfEfiBDS+bjT0OhU3IaM4L+qasKN8TzNfpXgCrQOGh2TjoVFjb3KRx+qYFgWwqXz6JvkDgEhiIB2ajQ6HvNYxJQZ89BDtTJ9MnKgyZjQkxNfW55i0GeUWxahWBky8KwV5KFcYEhfrFE9+nEmKMUHq7ql9UMzAgqmZjTpgG+5uxiTFCmTnVr78NFN4yGwuw7OZrwburJAo8X/2ieoDDkCbfSaEgdbq3BKRFfdyS7qlQhApvksZu2En9nBluOQRmq19UFzDgq0XSmAIKfUxnIhmHwHRga9ztzFGXxpo4AAoXzcYy6KT+RYpRMcqTcozy3nXnqQOzR/TT6vaVvb04d2hwvpDP58sT7vVgoZOac4s5YEL/8rVZhz5lBIeOO+87Ts0qd+/Rj9v4Qe9Zf4TOebxzDaMjFNxxioSelHbSHO9J/Vv93XUVGDCC/4+vCqeOKMqP3qGfcXXpVpiekdKwNTQdQwoAZUEjnACH9s1W4GZ0vxJS5xAkiUy/8e8Hx/DULoVTiMugPwmbn0lhSg/ef/DhRx8+uI/Voo+PwDDehiY0qxhDfCdFJ80KPehacbcgsez0Q+hsSpxCYpSfki7bgUunevJn4Z9/d308Ho8bHhI9Cj/krxSmv9TP8MHQr1g/4tSnpMkR8vHxE/5kMq2yFG4Yz7z4CXE7SWM06U/DL5hjSjz6BRAYWKpmQi3pj0AXH6MMc0d6P+VONmuLlsIbeDSFsahrxoNqn4VBj44fA+sL0wqak4JQ6E+gcEyVFHu2RCcZd5ldqLkvUIVXjCf9ZXjctIT+IHzk8v0W8RAUeIm07nAm9GkQLrsIpAtnfYpyBwfJdTtgYC/zK04hdqW//twYhNjhfxw+druBBYwUdHo/yAv0p7zm4kTtZNsYcr95jBt+awWMXkPcXU4hftTfvWNOf7TfP6t0I7GPmrXSPHMzyJ9J4ZSLQGu6FFWU5+GruOUDKsiYWf0h/JgpxK704Isn5mA6U1cfNd0Ml5H6syExsu4iULFqTsYAvXCPzBen/zhOG56H399iCnEStmTE+wQ24cuwmBrwHEKFS6SR66O6L2404pgMYuys2hiChpvsw22P8QjD9cU/hceXmUJckvgyjAuohsI/hyvc6rLQR81UNmj3US3pRy4TdYnzXN13FlssYDrUlU/HSX7zF0Nyhim8QuP9hI4VvvC+1YYg0ExI2Rq+Pzufo71uAtmU3ujBF44DNCjefYJN+hgPtRmm0Oh6iy+OLIV/9byVkI/S1dEY66O+1PCjzskSHnH2cdw7SSzH0pTSV4awqb+9DhB/ailcpPGeKHz5tee9QCnfql10c27Uj0DobkFWN8Sh4rk5skhKcMfIbV7j2E4yOVMhNs2XuG1HJ77U614w4bbKwCwf9ads4S6QvUgQxTqO7I+Y94hJI/jjuyTZxqPr70a8N3NL/R8uc2XMHuyjITMSXrP7qD97ElzDhLLCTsCGs9y/WWB8bMa7LqYQ1z7v4aFKUhrt6SvXW60Kg9DchcGyNX8m9Y6qtskIO8MYfM+/op9JwJghg5D+513SS425wm1zqE6Qafo3bjUddzea8tmCjqqvCVcaHWadNEC69Io5CGnBkSjEacq3ZiupB2qPeCPS+CZUZuiKYcJngefcBSrc65BTXCclUyZzEAZo0Z8oxJnmKzoDNEfi/e+sK+ZyaAJrHAu5CWS1J3+cjNt0CbPLThk1/vucTQsj1iC0riYKjRiw8IXVPE8knvm+Z26uJ5bLI6S/PPYS2G3nMv7MlxyLuy4mTF/44YcwN7VfO35tfVy2FOIB9i2z8xB+iUuzX+7NfxZ+3ekusNOKE5rmy66gfi+By/xZ169ff8L7jav2fyJPHj58+MlxII6LUK8+5875/uUZXGQzHj//9KNnxh9IEBgynQypd5jJtj9LTK6pDKav+rU8t3ByEgYlnPg/j/715s2bb56Fvz42Ru3YIhRIN+vlqUCU96dwmPES2FvX12zgp99/6JbGjFN7C150n1bGy9TLIJ9Kv1kvgfUtMt3CT7/wgp8RZoVFHBgH1du0uWAJ9KluOOopsL5OqoYW//0s/JoNzkm2l8EEFi3sXXpUoObbCprnIGQz+5qIH/3n9ZFtwP5zji5wAwq0NpPSGaEe9GtrpbhJhqPU8Jem8dBeg21Csk2dqGVB5NuuPOcKL2Ogsa+MZEmhAP54QmAbCFywVt8sgf4t01foozAa1kofLbaOwObbYKPsZavZ9KK65t8itlc62qDCyJpVyOoH7XGwnztkb8s3BfoVBTGeyQyh3i0Xo/bfawVutxkDC9n79rsV5otRvm4kcSv+MuraNdM/ycp0U/DQhnsP7SCpmh70aXmQUMnNKHwJqhrRLF8gEDzUTSDQ8qGBbiIQFXz9KQH3wgxjpPpXGERnM+CqSXA0fsgJZHvxAz14uqTr/r4j4rZICMhU/w5RnhglNvkhuMje/Engbf3oms+vF1QzIfd7Ae70Z0V5ygp0onyixr0vYq4tan6/5OM57eVIe14dTZ9z+QtBq8e5MK8eFNkBvPKGCn7v+a3iSCmu04uu4V330iM8u8i/nHaTtXeW8XsL/r/DVDkWck89wiXgkf7hLY+qnCJanPOh6iH3fqHhRJvzy0jOLXmelDIDAwOZzNSM68qUfRYI82O8D73EHegJ6ijflFe0ahdYG3AyyLkYdY8/EEMo2JwXJd02zJyENPh25mLUw03+wDxCuSb9XFAdnbQGMmCyzFyMerAB7jqBJpr2CyUeyxSNAesxV1gPXQUHOpL55r1RH63+2DVTAlG+eMAGYBzcM1Hvi3snou/0BMI81N5/oG4LL9r3NFNfbQlNTUyBGFE8oALV25tet24S3kXS+gCZq52lqQtFrxs3Da/FpvoYAL9FuurhQFvDaSjsTfPfuLlvGlDdbwd9p6IQhoi99tJ3CuPwHOigGwd0/LWLvhrm95XJgBAYN6uh6lLr/QvjRGnpOizgmAsS6nY76TtRTtMLaxsbpoe57PghnVbjusuyBlbggssY7qBq6Gbc4zYtpDFnup4GXxLHOZq6cMn9Fi2mkW4q6CMhvt2GH0fdRhwQCsTFfVUN7bVh97SpXi7lmRTebd5cUtX9S+2sr/Zim0FGWO4MjG2rbdw9bWqM+uui+bCDOVhtb/NRapBYmux3XHbzbTAfZbTyWMxknfICq4c33grzWTh+LcFiBtS6bYo33hrz2Yw4VlhK57Ou6jBvlfkY0ZG1yd3l5eXdrexsur+ufUISiUQikUgkEolEIpFIJBKJRCKRSCQSiUQikUgkEolEIpFIJBKJRCKRSP63+C9lmVwKNF0RLgAAAABJRU5ErkJggg=='

SYSTEM_PROMPT = '你是 MJC 七仔，MJC Leisure Sdn Bhd 专属内部旅游报价 AI 助理。\n\n【角色定位】\n- 服务对象：MJC 内部销售团队（非对外客户）\n- 主要任务：收集行程需求，生成格式化行程单\n\n【对话流程】\n第一步：收集必要信息（每次问 1-2 个问题，不要一次全问）\n  - 目的地 / 路线\n  - 出行日期（或大概月份）\n  - 人数（成人 / 儿童）\n  - 住宿等级（3星 / 4星 / 5星）\n  - 特殊需求（餐数、门票等）\n\n第二步：信息基本收集后，提示：\n  "✅ 资料基本齐全了！随时输入「出」生成完整行程单"\n\n【行程生成触发词】\n用户输入以下任何词时，立即生成行程 HTML：\n出 / 出行程 / 出单 / 生成 / generate / 出吧 / ok出\n\n生成时只输出以下格式，头尾用标记包住，不要有其他文字：\n\n[ITINERARY_START]\n<div class="iti-wrap">\n  <div class="iti-header">\n    <img src="data:image/png;base64,__LOGO__" class="iti-logo" alt="MJC">\n    <div class="iti-company">\n      <div class="iti-cname">MJC Leisure Sdn Bhd</div>\n      <div class="iti-csub">专业马来西亚入境旅游 · Since 2006</div>\n    </div>\n  </div>\n  <div class="iti-title">[行程标题]</div>\n  <div class="iti-meta">[人数] · [住宿等级] · [日期或日期待定]</div>\n  <table class="iti-table">\n    <thead><tr><th>天数</th><th>用餐</th><th>目的地</th><th>行程内容</th><th>住宿</th></tr></thead>\n    <tbody>\n      [每天一行格式：<tr><td><b>第X天</b></td><td class="meals">早✓/✗<br>午✓/✗<br>晚✓/✗</td><td>城市</td><td>活动详情</td><td>住宿城市</td></tr>]\n    </tbody>\n  </table>\n  <div class="iti-sections">\n    <div class="iti-sec"><div class="iti-sec-title">✅ 费用包含</div><ul>[每项li]</ul></div>\n    <div class="iti-sec"><div class="iti-sec-title">❌ 费用不含</div><ul>[每项li]</ul></div>\n    <div class="iti-sec"><div class="iti-sec-title">📝 备注</div><p>[备注内容]</p></div>\n  </div>\n  <div class="iti-footer">⚡ 由 MJC 七仔 AI 生成 · 仅供内部参考，请人工审核后再发给客户</div>\n</div>\n[ITINERARY_END]\n\n用餐：含→✓ 不含→✗，第一天通常全✗，最后一天早✓其余✗\n\n【语言】默认中文\n【安全】所有行程需经 MJC 同事审核后再发给客户'

HTML_PAGE = '<!DOCTYPE html>\n<html lang="zh">\n<head>\n<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width, initial-scale=1.0">\n<title>MJC 七仔 Demo</title>\n<style>\n\n*{box-sizing:border-box;margin:0;padding:0}\nbody{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#f0f2f5;height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center}\n.chat-container{width:100%;max-width:560px;height:93vh;background:#fff;border-radius:16px;box-shadow:0 4px 24px rgba(0,0,0,.12);display:flex;flex-direction:column;overflow:hidden}\n.header{background:#075E54;color:#fff;padding:14px 18px;display:flex;align-items:center;gap:12px;flex-shrink:0}\n.avatar{width:40px;height:40px;background:#25D366;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:20px}\n.header-info h3{font-size:16px;font-weight:600}\n.header-info p{font-size:12px;opacity:.8}\n.messages{flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:6px;background:#E5DDD5}\n.msg{max-width:80%;padding:8px 12px;border-radius:8px;font-size:14px;line-height:1.55;word-wrap:break-word}\n.msg.bot{background:#fff;align-self:flex-start;border-top-left-radius:2px;box-shadow:0 1px 2px rgba(0,0,0,.1)}\n.msg.user{background:#DCF8C6;align-self:flex-end;border-top-right-radius:2px;box-shadow:0 1px 2px rgba(0,0,0,.1)}\n.msg.typing{background:#fff;align-self:flex-start;color:#999;font-style:italic}\n.msg pre{white-space:pre-wrap;font-family:inherit;font-size:13px;background:#f5f5f5;padding:6px;border-radius:4px}\n.msg.itinerary{max-width:100%;padding:0;background:transparent;align-self:stretch;box-shadow:none}\n.iti-wrap{background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.15);border:1px solid #ddd}\n.iti-header{background:linear-gradient(135deg,#075E54,#128C7E);padding:16px 20px;display:flex;align-items:center;gap:14px}\n.iti-logo{width:58px;height:58px;object-fit:contain;background:#fff;border-radius:50%;padding:4px}\n.iti-cname{color:#fff;font-size:16px;font-weight:700}\n.iti-csub{color:rgba(255,255,255,.8);font-size:11px;margin-top:3px}\n.iti-title{background:#f8f8f8;padding:12px 16px;font-size:16px;font-weight:700;color:#075E54;border-bottom:2px solid #075E54}\n.iti-meta{padding:7px 16px;font-size:12px;color:#666;background:#fafafa;border-bottom:1px solid #eee}\n.iti-table{width:100%;border-collapse:collapse;font-size:13px}\n.iti-table th{background:#075E54;color:#fff;padding:8px 10px;text-align:left;font-weight:600;font-size:12px}\n.iti-table td{padding:8px 10px;border-bottom:1px solid #eee;vertical-align:top}\n.iti-table tr:nth-child(even) td{background:#f9fffe}\n.iti-table td.meals{font-size:12px;color:#444;white-space:nowrap;line-height:1.9}\n.iti-sections{padding:14px 16px;display:flex;flex-direction:column;gap:10px}\n.iti-sec-title{font-weight:700;font-size:13px;margin-bottom:5px}\n.iti-sec ul{padding-left:18px;font-size:13px;color:#444}\n.iti-sec ul li{margin-bottom:2px}\n.iti-sec p{font-size:13px;color:#444}\n.iti-footer{background:#f0f2f5;padding:8px 16px;font-size:11px;color:#999;text-align:center;border-top:1px solid #eee}\n.tip-bar{background:#e8f5e9;border-top:1px solid #c8e6c9;padding:6px 14px;font-size:12px;color:#2e7d32;text-align:center;flex-shrink:0}\n.input-area{padding:10px 14px;background:#f0f2f5;display:flex;gap:8px;align-items:flex-end;flex-shrink:0}\ntextarea{flex:1;padding:10px 14px;border:none;border-radius:20px;outline:none;font-size:14px;font-family:inherit;resize:none;max-height:100px;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.1)}\nbutton{width:42px;height:42px;background:#075E54;color:#fff;border:none;border-radius:50%;cursor:pointer;font-size:18px;display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:background .2s}\nbutton:hover{background:#128C7E}\nbutton:disabled{background:#ccc;cursor:not-allowed}\n.demo-badge{text-align:center;padding:4px;font-size:11px;color:#999;background:#f0f2f5;flex-shrink:0}\n\n</style>\n</head>\n<body>\n<div class="chat-container">\n  <div class="header">\n    <div class="avatar">🤖</div>\n    <div class="header-info">\n      <h3>MJC 七仔</h3>\n      <p>内部旅游报价助理 · Demo 版</p>\n    </div>\n  </div>\n  <div class="messages" id="messages">\n    <div class="msg bot">你好！我是 MJC 七仔 👋<br>请问这次行程的目的地和大概天数是什么？</div>\n  </div>\n  <div class="tip-bar">💡 资料收集完后，输入「<b>出</b>」即可生成行程单</div>\n  <div class="demo-badge">⚡ Demo 演示版 — Powered by Claude AI + FHA</div>\n  <div class="input-area">\n    <textarea id="input" placeholder="输入消息..." rows="1"></textarea>\n    <button id="sendBtn" onclick="sendMsg()">➤</button>\n  </div>\n</div>\n<script>\n\nvar chatHistory = [];\n\nfunction sendMsg() {\n  var input = document.getElementById(\'input\');\n  var msg = input.value.trim();\n  if (!msg) return;\n  addMsg(msg, \'user\');\n  input.value = \'\';\n  input.style.height = \'auto\';\n  document.getElementById(\'sendBtn\').disabled = true;\n  var typing = addMsg(\'七仔正在思考...\', \'typing\');\n  chatHistory.push({role: \'user\', content: msg});\n  fetch(\'/api/chat\', {\n    method: \'POST\',\n    headers: {\'Content-Type\': \'application/json\'},\n    body: JSON.stringify({messages: chatHistory})\n  }).then(function(r){ return r.json(); }).then(function(data) {\n    typing.remove();\n    var reply = data.reply || \'抱歉，出错了，请重试\';\n    chatHistory.push({role: \'assistant\', content: reply});\n    renderReply(reply);\n    document.getElementById(\'sendBtn\').disabled = false;\n  }).catch(function(e) {\n    typing.remove();\n    addMsg(\'连接错误，请检查网络\', \'bot\');\n    document.getElementById(\'sendBtn\').disabled = false;\n  });\n}\n\nfunction renderReply(text) {\n  var startTag = \'[ITINERARY_START]\';\n  var endTag = \'[ITINERARY_END]\';\n  var si = text.indexOf(startTag);\n  var ei = text.indexOf(endTag);\n  if (si !== -1 && ei !== -1) {\n    var html = text.substring(si + startTag.length, ei).trim();\n    var div = document.createElement(\'div\');\n    div.className = \'msg itinerary\';\n    div.innerHTML = html;\n    document.getElementById(\'messages\').appendChild(div);\n    div.scrollIntoView({behavior: \'smooth\'});\n  } else {\n    addMsg(text, \'bot\');\n  }\n}\n\nfunction addMsg(text, type) {\n  var div = document.createElement(\'div\');\n  div.className = \'msg \' + type;\n  if (type === \'user\') {\n    div.textContent = text;\n  } else {\n    var html = text\n      .replace(/&/g, \'&amp;\')\n      .replace(/</g, \'&lt;\')\n      .replace(/>/g, \'&gt;\')\n      .replace(/\\n/g, \'<br>\')\n      .replace(/\\*\\*([^*]+)\\*\\*/g, \'<b>$1</b>\');\n    div.innerHTML = html;\n  }\n  document.getElementById(\'messages\').appendChild(div);\n  div.scrollIntoView({behavior: \'smooth\'});\n  return div;\n}\n\ndocument.getElementById(\'input\').addEventListener(\'input\', function() {\n  this.style.height = \'auto\';\n  this.style.height = Math.min(this.scrollHeight, 100) + \'px\';\n});\n\ndocument.getElementById(\'input\').addEventListener(\'keydown\', function(e) {\n  if (e.key === \'Enter\' && !e.shiftKey) {\n    e.preventDefault();\n    sendMsg();\n  }\n});\n\n</script>\n</body>\n</html>'

def get_history(phone):
    try:
        res = (get_supabase().table("conversations")
               .select("role,content").eq("phone_number", phone)
               .order("created_at", desc=True).limit(MAX_HISTORY).execute())
        rows = res.data or []
        rows.reverse()
        return [{"role": r["role"], "content": r["content"]} for r in rows]
    except Exception as e:
        print(f"[Supabase] get_history error: {e}")
        return []

def save_message(phone, role, content):
    try:
        get_supabase().table("conversations").insert(
            {"phone_number": phone, "role": role, "content": content}
        ).execute()
    except Exception as e:
        print(f"[Supabase] save_message error: {e}")

def send_wati_message(phone, message):
    instance = os.environ.get("WATI_INSTANCE_URL", "").rstrip("/")
    token    = os.environ.get("WATI_API_TOKEN", "")
    if not instance or not token:
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

def ask_claude(messages, system):
    try:
        resp = get_anthropic().messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            system=system,
            messages=messages[-20:],
        )
        return resp.content[0].text
    except Exception as e:
        print(f"[Claude] error: {e}")
        return "抱歉，七仔暂时无法处理，请稍后再试。"

class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[HTTP] {format % args}")

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/demo"):
            body = HTML_PAGE.replace("__LOGO__", MJC_LOGO_B64).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)
        else:
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
            messages = data.get("messages", [])
            if not messages:
                self._respond(400, {"error": "no messages"})
                return
            system = SYSTEM_PROMPT.replace("__LOGO__", MJC_LOGO_B64)
            reply  = ask_claude(messages, system)
            self._respond(200, {"reply": reply})

        elif path in ("/api/webhook", "/webhook"):
            phone    = data.get("waId") or data.get("phone", "")
            msg_obj  = data.get("text") or {}
            user_msg = (msg_obj.get("body") or data.get("body") or "").strip()
            if not phone or not user_msg:
                self._respond(200, {"ok": True, "skip": "no phone or body"})
                return
            if data.get("type", "") not in ("", "text"):
                self._respond(200, {"ok": True, "skip": "non-text"})
                return
            history = get_history(phone)
            system  = SYSTEM_PROMPT.replace("__LOGO__", MJC_LOGO_B64)
            reply   = ask_claude(history + [{"role":"user","content":user_msg}], system)
            save_message(phone, "user", user_msg)
            save_message(phone, "assistant", reply)
            send_wati_message(phone, reply)
            self._respond(200, {"ok": True})
        else:
            self._respond(404, {"error": "not found"})

    def _respond(self, code, body):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())
