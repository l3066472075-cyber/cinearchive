# 影境档案 · CineArchive

一座「会生长的好电影档案馆」—— 用于 **影视教育 + 艺术治疗**。

不是视频库，而是好电影的**深度档案**：集结元数据、深度解读与情感/治疗维度，让用户用一句
「此刻的心情」，换回一部真正懂他的电影；而每一次搜索与反馈，都会成为这座档案馆的新养分。

```
用户："我现在很无力，和青春期孩子交流不顺"
系统：识别「无力感 · 亲子冲突 · 青春期」→ 推荐《怦然心动》《死亡诗社》《头脑特工队》…
     并解释为什么是它、它能怎么帮到你；这次搜索也被记录下来，喂养这座库。
```

---

## 快速开始（零配置，离线可跑）

```bash
cd backend

# 1) 创建虚拟环境并安装依赖（需要 uv，或改用 python -m venv + pip）
uv venv --python python3 .venv
uv pip install --python .venv/bin/python -r requirements.txt

# 2) 启动（首次启动自动建表 + 写入 14 部精选好电影）
.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

打开：

- 前端（推荐体验入口）：<http://127.0.0.1:8000/>
- API 交互文档：<http://127.0.0.1:8000/docs>
- 健康检查：<http://127.0.0.1:8000/api/v1/health>

> 需要 Node/Python 环境。已在本机验证：`uv 0.12` + Python 3.12 + Node 23。

---

## 接入真实大模型（可选，让推荐理由更个性化）

复制 `.env.example` 为 `.env` 并填写，重启服务即生效：

```bash
cd backend
cp .env.example .env
# 编辑 .env 填入你的 key，然后重启 uvicorn
```

只需填**大模型**（生成个性化推荐理由）两个变量即可；嵌入模型留空则用离线哈希（够用）：

```dotenv
LLM_API_KEY=你的key
LLM_BASE_URL=你的OpenAI兼容base_url
LLM_MODEL=模型名
```

**各家 `LLM_BASE_URL` + `LLM_MODEL` 写法**（都是 OpenAI 兼容接口）：

| 服务商 | LLM_BASE_URL | LLM_MODEL 示例 |
| --- | --- | --- |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| 通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus` |
| 智谱 GLM | `https://open.bigmodel.cn/api/paas/v4` | `glm-4-flash` |
| Kimi (Moonshot) | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` |
| 硅基流动 | `https://api.siliconflow.cn/v1` | `deepseek-ai/DeepSeek-V3` |

> 注意：`LLM_BASE_URL` 要写到 **`/v1`** 这一级。若需接真实向量嵌入，再填 `EMBEDDING_BASE_URL`/`EMBEDDING_API_KEY`/`EMBEDDING_MODEL`。

不配置也能完整运行：系统自动回退到**离线哈希嵌入 + 模板化推荐理由**（响应里的 `engine` 字段会显示 `offline`，配置后变 `llm`）。

---

## 核心 API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/v1/auth/wx-login` | 微信静默登录：code → openid → 签发 JWT |
| GET | `/api/v1/auth/me` | 当前登录用户（需 `Authorization: Bearer`） |
| POST | `/api/v1/recommend` | 情绪/境遇自述 → 电影推荐 + 理由（LangGraph 驱动） |
| POST | `/api/v1/search` | 关键字/语义搜索（写入搜索日志） |
| GET | `/api/v1/movies` | 影片列表（可按主题/人群/评分过滤） |
| GET | `/api/v1/movies/{id}` | 影片完整档案（深度解读 + 治疗维度） |
| POST | `/api/v1/feedback` | 反馈；`suggested_tag` 自动入库挂片 |
| GET | `/api/v1/themes` | 按分类组织标签（前端筛选） |
| GET | `/api/v1/insights` | 库增长洞察（大家在找什么 / 未被满足的心事） |
| GET | `/api/v1/health` | 健康检查 |

**推荐示例**：

```bash
curl -X POST http://127.0.0.1:8000/api/v1/recommend \
  -H "Content-Type: application/json" \
  -d '{"query":"我很焦虑，工作让我很累"}'
```

**静默登录示例**（开发模式：无 AppID 时用 code 派生伪 openid）：

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/wx-login \
  -H "Content-Type: application/json" -d '{"code":"wx-login-code"}'
# → { "token": "eyJ...", "openid": "dev_...", "is_new_user": true, "wx_enabled": false }
```

---

## 微信静默登录

在小程序端用 `Taro.login()` 拿到 `code` 后调用 `/api/v1/auth/wx-login`，后端用
`code2session` 换 `openid` 并签发 JWT；后续请求携带 `Authorization: Bearer <token>`。

在 `backend/.env` 里配置（AppID/AppSecret 你提供后填入即可真实跑通）：

```dotenv
WX_APPID=wx你的appid
WX_APP_SECRET=你的secret
JWT_SECRET=改成随机长字符串
```

未配置时自动进入**开发模式**（`wx_enabled=false`），用 `code` 派生稳定伪 openid，便于本地联调。

### 公众号 H5 静默登录（网页授权 OAuth）

公众号内打开的网页用的是**另一套接口**（`sns/oauth2/access_token`），已内置：

- `GET /api/v1/auth/mp/authorize?redirect_uri=<回跳地址>`：跳到微信网页授权页（`snsapi_base` 静默，无需用户确认）
- `GET /api/v1/auth/mp/callback?code=&state=`：微信回调 → 换 openid → 签发 JWT → 回跳 `redirect_uri?token=...`

前端已在微信内置浏览器里自动检测并走这套流程，无需额外改动。

**推荐示例**：

```bash
curl -X POST http://127.0.0.1:8000/api/v1/recommend \
  -H "Content-Type: application/json" \
  -d '{"query":"我很焦虑，工作让我很累"}'
```

---

## 嵌入公众号菜单

公众号内嵌的是一个 **H5 网页**（当前 `static/` 这个前端），把它挂到公众号底部菜单即可：

1. **部署到公网**：把后端 + 前端部署到一台有**备案域名 + HTTPS** 的服务器（如阿里云/腾讯云），拿到 `https://你的域名/`。
2. **配置公众号域名**（公众号后台 → 设置与开发 → 公众号设置）：
   - 「业务域名」填你的域名（并按要求放校验文件）
   - 「网页授权域名」填你的域名（用于静默登录 OAuth）
3. **加菜单**：公众号后台 → 自定义菜单 → 添加菜单 → 选「跳转网页」→ 填入 `https://你的域名/`。
4. **配置登录**（`backend/.env`）：填 `WX_APPID` / `WX_APP_SECRET`，以及回调地址
   `MP_OAUTH_REDIRECT_URI=https://你的域名/api/v1/auth/mp/callback`。
5. 用户在微信里点菜单 → 打开 H5 → 自动静默登录（`snsapi_base`）→ 搜索/反馈落到其账号。

> 前提：需**认证的公众号**才有网页授权能力；域名需 ICP 备案。

---

## 项目结构

```
cinelib/
├── docs/设计蓝图.md          # 完整设计规格书（数据模型/AI引擎/API/自增长闭环/IA）
└── backend/
    ├── app/
    │   ├── main.py           # FastAPI 入口
    │   ├── config.py         # 配置（环境变量）
    │   ├── db.py             # SQLite + SQLAlchemy
    │   ├── models.py         # 数据模型
    │   ├── schemas.py        # Pydantic Schema
    │   ├── seed_data.py      # 14 部精选好电影 + 标签体系
    │   ├── seed.py           # 建表 + 写入种子（幂等）
    │   ├── auth.py           # JWT + 微信 code2session + 鉴权依赖
    │   ├── ai/
    │   │   ├── graph.py      # LangGraph 推荐状态图（意图→检索→重排→解释）
    │   │   ├── lc.py         # LangChain 集成（ChatOpenAI / OpenAIEmbeddings）
    │   │   ├── embeddings.py # 可插拔嵌入（离线 n-gram 回退）
    │   │   ├── llm.py        # 可插拔 LLM（模板回退）
    │   │   └── recommender.py# 意图识别/向量索引/标签词典等基础能力
    │   ├── services/
    │   │   ├── library.py    # 影片查询/搜索
    │   │   └── growth.py     # 搜索即喂养闭环（日志/反馈/洞察）
    │   └── routers/          # API 路由（auth/recommend/search/movies/feedback/meta）
    ├── static/               # 网页前端（原生 HTML/CSS/JS，无构建，作 H5 预览）
    └── requirements.txt
```

---

## 设计要点速览

- **三维标签体系**：`情感 / 境遇 / 人群 / 价值 / 主题` 五类标签，是「人」与「片」对齐的桥梁。
- **LangGraph 推荐引擎**：推荐流程编排为「意图识别 → 语义检索 → 标签重排 → 理由生成」状态图；
  LLM 与 Embedding 走 LangChain（OpenAI 兼容），离线回退可跑。
- **微信静默登录**：`Taro.login()` → `code2session` → JWT，搜索/反馈落到用户维度。
- **搜索即喂养**：搜索日志 + 反馈闭环，让标签与档案随使用不断生长（详见 `docs/设计蓝图.md`）。
- **负责任推荐**：触发预警、治疗使用说明、讨论问题，艺术治疗场景的伦理底线。
- **高级美感前端**：暖调深色电影质感 + 衬线大标题 + 胶片颗粒 + 细腻动效。

## 技术栈

- **后端**：Python + FastAPI + SQLAlchemy + SQLite + **LangChain / LangGraph** + PyJWT（前后端分离，REST API）
- **前端（网页版，已实现）**：原生 HTML/CSS/JS，作 H5 预览
- **前端（微信小程序，规划中）**：Taro + React + TypeScript，微信静默登录
