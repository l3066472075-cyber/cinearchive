"""导出「可分享的独立 HTML 文件」。

把 seed_data.py 里的电影档案 + 标签 + 推荐逻辑，打包成一个自包含的单文件 HTML：
- 无需后端 / 无需网络 / 无需服务器，双击即可在任意浏览器打开
- 内置全部电影数据与一个轻量客户端推荐引擎（意图识别 + 标签匹配）
用法：.venv/bin/python -m app.export_share_html
输出：cinelib/cinearchive.html
"""
from __future__ import annotations

import json
from pathlib import Path

from .ai.recommender import SYNONYMS
from .seed_data import MOVIES, TAGS

REPO_DIR = Path(__file__).resolve().parent.parent.parent

# 组装电影数据
_movies = []
for i, m in enumerate(MOVIES, start=1):
    _movies.append(
        {
            "id": i,
            "title": m["title"],
            "title_en": m["title_en"],
            "year": m["year"],
            "director": m["director"],
            "cast": m["cast"],
            "country": m["country"],
            "duration": m["duration_min"],
            "genres": m["genres"],
            "rating_domestic": m["rating_domestic"],
            "rating_international": m["rating_international"],
            "synopsis": m["synopsis"],
            "analysis": m["deep_analysis"],
            "audiences": m["support_audiences"],
            "support_types": m["support_types"],
            "therapy_notes": m["therapy_notes"],
            "warnings": m["trigger_warnings"],
            "questions": m["discussion_questions"],
            "tags": m["tags"],
        }
    )

_tags = {name: {"category": c, "desc": d} for name, (c, d) in TAGS.items()}
_tag_names = list(_tags.keys())

MOVIES_JSON = json.dumps(_movies, ensure_ascii=False)
TAGS_JSON = json.dumps(_tags, ensure_ascii=False)
TAG_NAMES_JSON = json.dumps(_tag_names, ensure_ascii=False)
SYNONYMS_JSON = json.dumps(SYNONYMS, ensure_ascii=False)

HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
<title>影境档案 · 好电影的深度档案馆</title>
<meta name="description" content="从多部经典电影中，为您挑选适合当下心境的影片——影视教育 × 艺术治疗。" />
<meta name="theme-color" content="#100e0c" />
<style>
:root{--bg:#100e0c;--surface:#1a1612;--surface-2:#211c15;--hairline:rgba(214,177,110,.16);--hairline-soft:rgba(214,177,110,.09);--ink:#ece3d3;--ink-2:#b9ad99;--ink-3:#82776a;--gold:#c9a15c;--gold-rgb:201,161,92;--gold-soft:#e5c98f;--gold-deep:#9a793e;--danger:#c96a5c;--font-serif:"Songti SC","STSong","SimSun",serif;--font-sans:-apple-system,"PingFang SC","Microsoft YaHei",system-ui,sans-serif;--ease:cubic-bezier(.22,1,.36,1)}
body[data-brand="yingling"]{--gold:#7b9bd6;--gold-soft:#a9c3ee;--gold-deep:#5a78b0;--gold-rgb:123,155,214;--hairline:rgba(150,180,225,.16);--hairline-soft:rgba(150,180,225,.09)}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);background:radial-gradient(1400px 800px at 50% -12%,#1d1812 0%,var(--bg) 58%);color:var(--ink);font-family:var(--font-sans);line-height:1.7;-webkit-font-smoothing:antialiased;overflow-x:hidden}
.container{width:min(680px,calc(100% - 36px));margin-inline:auto}
.site-header{position:sticky;top:0;z-index:20;display:flex;align-items:center;gap:16px;padding:16px 18px;background:rgba(16,14,12,.92);border-bottom:1px solid var(--hairline-soft)}
.brand{display:flex;align-items:baseline;gap:10px;text-decoration:none;color:var(--ink)}
.brand__mark{font-family:Georgia,serif;font-size:19px;font-weight:600;letter-spacing:.12em;color:var(--gold-soft)}
.brand__cn{font-family:var(--font-serif);font-size:14px;letter-spacing:.28em;color:var(--ink-2)}
.brand__tagline{margin-left:auto;font-size:11.5px;letter-spacing:.04em;color:var(--ink-3)}
.brand-switch{display:flex;gap:3px;flex-shrink:0;background:var(--surface);border:1px solid var(--hairline-soft);border-radius:999px;padding:3px}
.brand-switch button{border:none;background:transparent;color:var(--ink-3);font-size:11.5px;padding:4px 11px;border-radius:999px;cursor:pointer;transition:all .2s}
.brand-switch button.is-active{background:linear-gradient(135deg,var(--gold-soft),var(--gold));color:#1c1408}
.hero{padding:clamp(48px,9vh,88px) 18px 30px;text-align:center}
.hero__eyebrow{margin:0 0 20px;font-size:12.5px;letter-spacing:.4em;color:var(--gold);text-transform:uppercase}
.hero__title{margin:0;font-family:var(--font-serif);font-weight:700;font-size:clamp(34px,7vw,52px);line-height:1.25;letter-spacing:.02em}
.hero__title em{font-style:normal;background:linear-gradient(120deg,var(--gold-soft),var(--gold) 55%,var(--gold-deep));-webkit-background-clip:text;background-clip:text;color:transparent}
.hero__sub{margin:20px auto 0;font-size:15.5px;font-weight:300;color:var(--ink-2)}
.hero__ai-note{margin:14px 0 0;font-size:12.5px;letter-spacing:.05em;color:var(--gold-soft)}
.ask-box{display:flex;align-items:center;gap:8px;max-width:620px;margin:30px auto 0;padding:7px 7px 7px 20px;background:var(--surface);border:1px solid var(--hairline);border-radius:999px;transition:border-color .3s var(--ease),box-shadow .3s var(--ease)}
.ask-box:focus-within{border-color:var(--gold-deep);box-shadow:0 0 0 4px rgba(var(--gold-rgb),.22)}
.ask-box__icon{color:var(--gold);display:inline-flex;flex-shrink:0}
.ask-box__input{flex:1;min-width:0;background:transparent;border:none;outline:none;color:var(--ink);font-family:var(--font-sans);font-size:15.5px;padding:11px 0}
.ask-box__input::placeholder{color:var(--ink-3)}
.ask-box__submit{display:inline-flex;align-items:center;gap:8px;flex-shrink:0;padding:11px 20px;border:none;border-radius:999px;background:linear-gradient(135deg,var(--gold-soft),var(--gold) 60%,var(--gold-deep));color:#1c1408;font-size:14.5px;font-weight:500;letter-spacing:.04em;cursor:pointer}
.hero__examples{display:flex;flex-wrap:wrap;justify-content:center;gap:9px;margin-top:20px}
.hero__examples-label{font-size:12.5px;color:var(--ink-3)}
.chip{display:inline-flex;align-items:center;padding:6px 13px;border-radius:999px;font-size:12.5px;line-height:1.4;cursor:pointer;transition:all .25s var(--ease)}
.chip--ghost{background:transparent;border:1px solid var(--hairline);color:var(--ink-2)}
.chip--ghost:hover{border-color:var(--gold-deep);color:var(--gold-soft)}
.chip--gold{background:rgba(var(--gold-rgb),.16);border:1px solid rgba(var(--gold-rgb),.38);color:var(--gold-soft)}
.chip--tag{background:var(--surface);border:1px solid var(--hairline-soft);color:var(--ink-2)}
.chip--tag:hover{border-color:var(--gold-deep);color:var(--gold-soft);transform:translateY(-1px)}
.chip--muted{background:var(--surface-2);border:1px solid var(--hairline-soft);color:var(--ink-2)}
.section-kicker{margin:0 0 8px;font-family:Georgia,serif;font-size:13px;letter-spacing:.32em;color:var(--gold);text-transform:uppercase}
.tags-section{padding:10px 0 40px}
.tags-section__head{text-align:center;margin-bottom:26px}
.tags-section__title{margin:0;font-family:var(--font-serif);font-weight:600;font-size:clamp(19px,4vw,24px);letter-spacing:.03em}
.tag-groups{display:flex;flex-direction:column;gap:20px}
.tag-group__label{display:flex;align-items:center;gap:10px;margin:0 0 11px;font-family:Georgia,serif;font-size:12.5px;letter-spacing:.24em;text-transform:uppercase;color:var(--gold)}
.tag-group__label::after{content:"";flex:1;height:1px;background:var(--hairline-soft)}
.tag-group__chips{display:flex;flex-wrap:wrap;gap:7px}
.results{padding:16px 0 40px}
.results__head{display:flex;align-items:flex-end;justify-content:space-between;gap:16px;margin-bottom:8px}
.results__query{margin:0;font-family:var(--font-serif);font-weight:600;font-size:21px;color:var(--ink)}
.results__query span{color:var(--gold-soft)}
.results__intent{display:flex;flex-wrap:wrap;gap:6px;justify-content:flex-end}
.results__note{margin:0 0 18px;font-size:12.5px;color:var(--ink-3)}
.results__grid{display:flex;flex-direction:column;gap:9px}
.movie-pill{display:flex;align-items:center;gap:13px;padding:9px 14px 9px 11px;background:linear-gradient(180deg,var(--surface),var(--surface-2));border:1px solid var(--hairline-soft);border-radius:16px;cursor:pointer;transition:transform .3s var(--ease),border-color .3s var(--ease)}
.movie-pill:hover{transform:translateY(-2px);border-color:rgba(var(--gold-rgb),.45)}
.movie-pill__poster{flex-shrink:0;width:42px;height:42px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-family:var(--font-serif);font-weight:700;font-size:19px;color:rgba(255,255,255,.92)}
.movie-pill__main{flex:1;min-width:0}
.movie-pill__title{margin:0;font-family:var(--font-serif);font-weight:600;font-size:15.5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.movie-pill__meta{margin:2px 0 0;font-size:11.5px;color:var(--ink-3);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.movie-pill__tags{display:flex;gap:5px;flex-shrink:0}
.movie-pill__score{flex-shrink:0;font-family:Georgia,serif;font-size:16px;font-weight:700;color:var(--gold-soft);min-width:42px;text-align:right}
.tag-pill{padding:3px 9px;border-radius:999px;font-size:11px;background:rgba(var(--gold-rgb),.09);border:1px solid var(--hairline-soft);color:var(--ink-2);white-space:nowrap}
.tag-pill--hit{background:rgba(var(--gold-rgb),.2);border-color:rgba(var(--gold-rgb),.42);color:var(--gold-soft)}
.site-footer{margin-top:40px;padding:40px 0 50px;border-top:1px solid var(--hairline-soft);text-align:center}
.site-footer p{margin:6px 0 0;color:var(--ink-3);font-size:12.5px}
.activity-section{padding:10px 0 50px}
.activity-list{display:flex;flex-direction:column;gap:12px}
.activity-card{display:flex;align-items:flex-start;gap:14px;padding:18px 20px;background:linear-gradient(180deg,var(--surface),var(--surface-2));border:1px solid var(--hairline-soft);border-radius:16px}
.activity-card__badge{flex-shrink:0;margin-top:2px;padding:3px 11px;border-radius:999px;font-size:11.5px;font-weight:500;color:#1c1408;background:linear-gradient(135deg,var(--gold-soft),var(--gold))}
.activity-card__title{margin:0;font-family:var(--font-serif);font-weight:600;font-size:16px}
.activity-card__desc{margin:4px 0 0;font-size:13px;color:var(--ink-3)}
.extra-section{padding:10px 0 50px}
.extra-list{display:flex;flex-direction:column;gap:10px}
.extra-card{display:block;padding:14px 18px;background:var(--surface);border:1px solid var(--hairline-soft);border-radius:14px;color:var(--ink-2);text-decoration:none;font-size:14px;transition:all .25s}
.extra-card:hover{border-color:var(--gold-deep);color:var(--gold-soft)}
.guide-section{padding:8px 0 30px}
.role-select{text-align:center}
.role-cards{display:flex;gap:14px;justify-content:center;flex-wrap:wrap;margin-top:22px}
.role-card{display:flex;flex-direction:column;align-items:center;gap:8px;width:200px;padding:26px 20px;background:linear-gradient(180deg,var(--surface),var(--surface-2));border:1px solid var(--hairline-soft);border-radius:18px;cursor:pointer;transition:all .3s}
.role-card:hover{transform:translateY(-3px);border-color:var(--gold-deep)}
.role-card__icon{font-size:30px}
.role-card__name{font-family:var(--font-serif);font-weight:600;font-size:18px}
.role-card__desc{font-size:12.5px;color:var(--ink-3)}
.wizard{max-width:560px;margin:30px auto 0}
.wizard__progress{height:4px;background:var(--surface-2);border-radius:999px;overflow:hidden;margin-bottom:16px}
.wizard__progress span{display:block;height:100%;background:linear-gradient(90deg,var(--gold-soft),var(--gold));transition:width .3s}
.wizard__step{margin:0 0 6px;font-size:12px;letter-spacing:.2em;color:var(--ink-3);text-transform:uppercase}
.wizard__question{margin:0 0 18px;font-family:var(--font-serif);font-weight:600;font-size:22px}
.wizard__chips{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:22px}
.wizard__chips .chip--tag.is-selected{background:rgba(var(--gold-rgb),.22);border-color:var(--gold-deep);color:var(--gold-soft)}
.wizard__nav{display:flex;gap:10px;justify-content:flex-end;align-items:center}
.interpretation{padding:16px 18px;border-radius:14px;border:1px solid var(--hairline);background:rgba(var(--gold-rgb),.08);color:var(--ink-2);font-size:14px;line-height:1.9;margin-bottom:6px;white-space:pre-wrap}
.modal{position:fixed;inset:0;z-index:50;display:flex;align-items:center;justify-content:center;padding:20px}
.modal[hidden]{display:none!important}
.modal__backdrop{position:absolute;inset:0;background:rgba(8,6,4,.82)}
.modal__dialog{position:relative;width:min(680px,100%);max-height:86vh;overflow-y:auto;background:linear-gradient(180deg,var(--surface),var(--bg));border:1px solid var(--hairline);border-radius:20px}
.modal__close{position:sticky;top:14px;float:right;margin:14px 14px 0 0;z-index:2;width:36px;height:36px;border-radius:50%;border:1px solid var(--hairline);background:var(--surface-2);color:var(--ink-2);font-size:14px;cursor:pointer}
.modal__body{padding:6px 26px 34px}
.detail-hero{display:grid;grid-template-columns:90px 1fr;gap:20px;align-items:end;margin-bottom:24px}
.poster{position:relative;aspect-ratio:2/3;border-radius:10px;overflow:hidden;display:flex;align-items:flex-end;padding:12px}
.poster::before{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,0) 45%,rgba(0,0,0,.55) 100%)}
.poster__title{position:relative;font-family:var(--font-serif);font-weight:600;font-size:14px;color:rgba(255,255,255,.94);letter-spacing:.06em;writing-mode:vertical-rl}
.detail-title{margin:0;font-family:var(--font-serif);font-weight:700;font-size:26px}
.detail-en{margin:3px 0 0;font-family:Georgia,serif;font-style:italic;color:var(--ink-3);font-size:14px}
.detail-meta{margin:12px 0 0;display:flex;flex-wrap:wrap;gap:6px 14px;font-size:13px;color:var(--ink-2)}
.meta-dot{color:var(--ink-3)}
.detail-synopsis{font-size:14.5px;line-height:1.95;color:var(--ink);border-left:2px solid var(--gold-deep);padding-left:16px;margin:0 0 22px}
.detail-section{margin-bottom:22px}
.detail-section h4{margin:0 0 9px;font-family:var(--font-serif);font-size:13.5px;font-weight:600;letter-spacing:.14em;color:var(--gold)}
.detail-section p,.detail-section li{font-size:13.5px;color:var(--ink-2);font-weight:300;line-height:1.9}
.detail-section ul{margin:0;padding-left:18px}
.analysis-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.analysis-box{padding:13px 15px;border-radius:11px;background:var(--surface-2);border:1px solid var(--hairline-soft)}
.analysis-box h5{margin:0 0 5px;font-size:12.5px;color:var(--gold-soft);font-weight:500;letter-spacing:.08em}
.analysis-box p{margin:0;font-size:12.5px;color:var(--ink-2)}
.tag-row{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px}
.warning{padding:11px 15px;border-radius:10px;border:1px solid rgba(201,106,92,.4);background:rgba(201,106,92,.1);color:#e0a99b;font-size:12.5px}
.rating{display:inline-flex;align-items:center;gap:4px}
.rating__src{color:var(--ink-3);font-size:11px}
.rating__val{color:var(--gold-soft);font-weight:500}
@media(max-width:520px){.brand__tagline{display:none}.movie-pill__tags{display:none}.movie-pill{padding:8px 11px}.movie-pill__poster{width:36px;height:36px;font-size:16px}.analysis-grid{grid-template-columns:1fr}.ask-box{padding-left:14px}.ask-box__submit{padding:11px 14px}.ask-box__submit span{display:none}}
</style>
</head>
<body>
<header class="site-header">
  <a class="brand" href="#top"><span class="brand__mark" id="brand-name">禅说电影</span><span class="brand__cn">影境档案</span></a>
  <span class="brand__tagline" id="brand-tagline">以影入道 · 借影观心</span>
  <div class="brand-switch" id="brand-switch">
    <button data-brand="chanshuo" class="is-active">禅说电影</button>
    <button data-brand="yingling">影领圈</button>
  </div>
</header>

<main id="top">
  <section class="hero">
    <p class="hero__eyebrow">影视教育 × 艺术治疗</p>
    <h1 class="hero__title">让一部好电影，<br><em>接住此刻的你</em></h1>
    <p class="hero__sub">从多部经典电影中，为您挑选适合当下心境的影片。</p>
    <p class="hero__ai-note">✦ 即将接入大模型 · AI 智能选片与深度解读</p>
    <form class="ask-box" id="recommend-form" autocomplete="off">
      <span class="ask-box__icon"><svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="11" cy="11" r="7"></circle><path d="M21 21l-4.35-4.35"></path></svg></span>
      <input id="query-input" class="ask-box__input" type="text" placeholder="说说你此刻的心情…" />
      <button class="ask-box__submit" type="submit"><span>为我推荐</span></button>
    </form>
    <div class="hero__examples">
      <span class="hero__examples-label">试着说说：</span>
      <button class="chip chip--ghost" data-query="我很焦虑，工作让我很累">我很焦虑，工作让我很累</button>
      <button class="chip chip--ghost" data-query="刚失去亲人，很难过">刚失去亲人，很难过</button>
      <button class="chip chip--ghost" data-query="孩子学习压力大，我也很无力">孩子学习压力大，我也很无力</button>
      <button class="chip chip--ghost" data-query="刚看完一部片，特别兴奋">刚看完一部片，特别兴奋</button>
    </div>
  </section>

  <section class="guide-section">
    <div class="container">
      <div class="role-select" id="role-select">
        <p class="section-kicker">Choose your role</p>
        <h2 class="tags-section__title">你以什么身份，走进这座档案馆？</h2>
        <div class="role-cards">
          <button class="role-card" data-role="viewer">
            <span class="role-card__icon">🎬</span>
            <span class="role-card__name">寻影者</span>
            <span class="role-card__desc">为自己，寻一部懂你的电影</span>
          </button>
          <button class="role-card" data-role="facilitator">
            <span class="role-card__icon">🧭</span>
            <span class="role-card__name">影领家</span>
            <span class="role-card__desc">为他人选片、带观影</span>
          </button>
        </div>
      </div>
      <div class="wizard" id="wizard" hidden>
        <div class="wizard__progress"><span id="wizard-progress"></span></div>
        <p class="wizard__step" id="wizard-step">第 1 / 5 问</p>
        <h2 class="wizard__question" id="wizard-question"></h2>
        <div class="wizard__chips" id="wizard-chips"></div>
        <div class="wizard__nav">
          <button class="mini-btn" id="wizard-back" hidden>← 上一步</button>
          <button class="ask-box__submit" id="wizard-next"><span>下一步 →</span></button>
        </div>
      </div>
    </div>
  </section>

  <section class="tags-section">
    <div class="container">
      <header class="tags-section__head">
        <p class="section-kicker">Pick a mood</p>
        <h2 class="tags-section__title">或，选择一个贴近你的标签</h2>
      </header>
      <div class="tag-groups" id="tag-groups"></div>
    </div>
  </section>

  <section class="results" id="results" hidden>
    <div class="container">
      <header class="results__head">
        <div><p class="section-kicker">为你挑选</p><h2 class="results__query">“<span id="echo-query"></span>”</h2></div>
        <div class="results__intent" id="intent-tags"></div>
      </header>
      <div class="results__grid" id="results-grid"></div>
    </div>
  </section>

  <section class="activity-section">
    <div class="container">
      <header class="tags-section__head">
        <p class="section-kicker">Now Showing</p>
        <h2 class="tags-section__title">全国观影联动</h2>
      </header>
      <!-- ⬇️⬇️ 活动编辑区开始：在这里增改活动卡片 ⬇️⬇️ -->
      <div class="activity-list">
        <article class="activity-card">
          <span class="activity-card__badge">进行中</span>
          <div><h3 class="activity-card__title">本周联动观影 · 主题征集中</h3>
          <p class="activity-card__desc">时间、形式、参与方式、往期回顾等，在此处编辑。</p></div>
        </article>
      </div>
      <!-- ⬆️⬆️ 活动编辑区结束 ⬆️⬆️ -->
    </div>
  </section>

  <section class="extra-section">
    <div class="container">
      <header class="tags-section__head">
        <p class="section-kicker">Go Deeper</p>
        <h2 class="tags-section__title">延伸阅读 · 工具包</h2>
      </header>
      <!-- ⬇️ 链接占位区：把 href="#" 换成真实文章/视频/工具包链接 ⬇️ -->
      <div class="extra-list">
        <a class="extra-card" href="#">📖 相关文章 · 标题待填</a>
        <a class="extra-card" href="#">🎬 相关视频 · 标题待填</a>
        <a class="extra-card" href="#">🧰 观影工具包 · 标题待填</a>
      </div>
      <!-- ⬆️ 链接占位区结束 ⬆️ -->
    </div>
  </section>
</main>

<footer class="site-footer">
  <div class="container">
    <span class="brand__mark">CineArchive</span> <span class="brand__cn">影境档案</span>
    <p>影视教育 · 艺术治疗 · 一座会生长的好电影档案馆</p>
  </div>
</footer>

<div class="modal" id="movie-modal" hidden>
  <div class="modal__backdrop" data-close></div>
  <div class="modal__dialog" role="dialog" aria-modal="true">
    <button class="modal__close" data-close aria-label="关闭">✕</button>
    <div class="modal__body" id="modal-body"></div>
  </div>
</div>

<script>
const MOVIES = __MOVIES_JSON__;
const TAGS = __TAGS_JSON__;
const SYNONYMS = __SYNONYMS_JSON__;
const TAG_NAMES = __TAG_NAMES_JSON__;

const $ = (s, r=document) => r.querySelector(s);
const $$ = (s, r=document) => Array.from(r.querySelectorAll(s));
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const PALETTE = [["#3a2c1d","#6b4a2a"],["#1f2a33","#3d5a6b"],["#2e1f2a","#5d3a52"],["#16261f","#2f4f3c"],["#3a2416","#7a4a1f"],["#20232e","#4a4f6b"],["#2c1f18","#59422f"],["#1c2a2e","#3f5a58"]];
const gradientFor = t => { let h=0; for(const c of (t||"")) h=(h*31+c.charCodeAt(0))>>>0; const [a,b]=PALETTE[h%PALETTE.length]; return `linear-gradient(158deg,${a} 0%,${b} 100%)`; };

function extractIntent(q){
  const labels = [];
  for(const name of TAG_NAMES) if(q.includes(name)) labels.push(name);
  for(const [canonical, kws] of Object.entries(SYNONYMS)) if(kws.some(k => q.includes(k))) labels.push(canonical);
  return [...new Set(labels)];
}

function recommend(query, limit=6){
  const intent = extractIntent(query);
  const q = query.toLowerCase();
  const scored = MOVIES.map(m => {
    const matched = intent.filter(t => m.tags.includes(t));
    const tagScore = intent.length ? matched.length / intent.length : 0;
    const hay = (m.title + m.title_en + m.synopsis + m.tags.join("") + (m.audiences||[]).join("")).toLowerCase();
    let kw = 0; for(const ch of q){ if(ch !== " " && hay.includes(ch)) kw++; } kw = q ? kw/q.length : 0;
    const quality = (m.rating_domestic + m.rating_international) / 20;
    const score = intent.length ? (0.55*tagScore + 0.25*kw + 0.2*quality) : (0.7*kw + 0.3*quality);
    return {movie:m, matched, score};
  });
  scored.sort((a,b) => b.score - a.score);
  return {intent, items: scored.slice(0, limit)};
}

const CAT_LABEL = {emotion:"此刻的心情", situation:"正处的境遇", audience:"我是谁", value:"我渴望", theme:"想看的主题"};
function loadTagOptions(){
  const groups = {};
  for(const [name, t] of Object.entries(TAGS)) (groups[t.category] = groups[t.category] || []).push(name);
  const order = ["emotion","situation","audience","value","theme"];
  $("#tag-groups").innerHTML = order.filter(c => groups[c]).map(c => `
    <div class="tag-group">
      <p class="tag-group__label">${CAT_LABEL[c]||c}</p>
      <div class="tag-group__chips">${groups[c].map(t => `<button class="chip chip--tag" data-tag="${esc(t)}">${esc(t)}</button>`).join("")}</div>
    </div>`).join("");
}

function cardHTML(item, max){
  const m = item.movie;
  const rel = Math.max(55, Math.round(item.score/max*100));
  const tags = (m.tags||[]).filter(t => item.matched.includes(t)).slice(0,3);
  return `<article class="movie-pill" data-id="${m.id}">
    <div class="movie-pill__poster" style="background:${gradientFor(m.title)}">${esc(m.title.charAt(0))}</div>
    <div class="movie-pill__main"><h3 class="movie-pill__title">${esc(m.title)}</h3>
      <p class="movie-pill__meta">${m.year} · ${esc(m.director)} · ${m.rating_domestic} 分</p></div>
    <div class="movie-pill__tags">${tags.map(t => `<span class="tag-pill tag-pill--hit">${esc(t)}</span>`).join("")}</div>
    <span class="movie-pill__score">${rel}%</span></article>`;
}

function renderResults(query){
  const {intent, items} = recommend(query);
  $("#results").hidden = false;
  $("#echo-query").textContent = query;
  $("#intent-tags").innerHTML = intent.length ? intent.map(t => `<span class="chip chip--gold">${esc(t)}</span>`).join("") : `<span class="chip chip--muted">未识别到明确情绪</span>`;
  const max = Math.max(...items.map(i => i.score), 0.0001);
  $("#results-grid").innerHTML = items.map(it => cardHTML(it, max)).join("");
  $$(".movie-pill").forEach(p => p.addEventListener("click", () => openMovie(Number(p.dataset.id))));
  $("#results").scrollIntoView({behavior:"smooth", block:"start"});
}

function openMovie(id){
  const m = MOVIES.find(x => x.id === id); if(!m) return;
  const da = m.analysis || {};
  const rateLine = `<span class="rating"><span class="rating__src">豆瓣</span><span class="rating__val">${m.rating_domestic}</span></span><span class="meta-dot">·</span><span class="rating"><span class="rating__src">IMDb</span><span class="rating__val">${m.rating_international}</span></span>`;
  const warnings = (m.warnings||[]).length ? `<div class="warning">${m.warnings.map(esc).join("<br>")}</div>` : "";
  const questions = (m.questions||[]).length ? `<ul>${m.questions.map(q => `<li>${esc(q)}</li>`).join("")}</ul>` : "";
  $("#modal-body").innerHTML = `
    <div class="detail-hero">
      <div class="poster" style="background:${gradientFor(m.title)}"><span class="poster__title">${esc(m.title)}</span></div>
      <div><h3 class="detail-title">${esc(m.title)}</h3><p class="detail-en">${esc(m.title_en)}</p></div>
      <div class="detail-meta"><span>${m.year}</span><span class="meta-dot">·</span><span>${esc(m.director)} 执导</span><span class="meta-dot">·</span><span>${esc(m.country)}</span><span class="meta-dot">·</span><span>${m.duration} 分钟</span></div>
    </div>
    <p class="detail-synopsis">${esc(m.synopsis)}</p>
    <div class="detail-section"><h4>主创 · 评分</h4><div class="detail-meta" style="margin:0 0 6px">${rateLine}</div><p>主演：${esc((m.cast||[]).join("、"))}</p><p>类型：${esc((m.genres||[]).join(" · "))}</p></div>
    <div class="detail-section"><h4>深度解读</h4><div class="analysis-grid">
      <div class="analysis-box"><h5>主题</h5><p>${esc(da.theme||"—")}</p></div>
      <div class="analysis-box"><h5>艺术价值</h5><p>${esc(da.art_value||"—")}</p></div>
      <div class="analysis-box"><h5>教育价值</h5><p>${esc(da.edu_value||"—")}</p></div>
      <div class="analysis-box"><h5>治疗价值</h5><p>${esc(da.therapy_value||"—")}</p></div>
    </div></div>
    <div class="detail-section"><h4>这部影片如何支持你</h4>
      <div class="tag-row">${(m.support_types||[]).map(s => `<span class="tag-pill">${esc(s)}</span>`).join("")}</div>
      <p><strong style="color:var(--ink)">适合人群：</strong>${esc((m.audiences||[]).join("、"))}</p>
      <p>${esc(m.therapy_notes||"")}</p></div>
    ${questions ? `<div class="detail-section"><h4>观影后的讨论问题</h4>${questions}</div>` : ""}
    ${warnings ? `<div class="detail-section"><h4>观看提醒</h4>${warnings}</div>` : ""}
    <div class="detail-section"><h4>相关标签</h4><div class="tag-row">${(m.tags||[]).map(t => `<span class="chip chip--muted">${esc(t)}</span>`).join("")}</div></div>`;
  $("#movie-modal").hidden = false;
  document.body.style.overflow = "hidden";
}

$("#recommend-form").addEventListener("submit", e => { e.preventDefault(); const q = $("#query-input").value.trim(); if(q) renderResults(q); });
$$(".chip[data-query]").forEach(c => c.addEventListener("click", () => { $("#query-input").value = c.dataset.query; renderResults(c.dataset.query); }));
document.addEventListener("click", e => { const c = e.target.closest(".chip--tag"); if(c){ $("#query-input").value = c.dataset.tag; renderResults(c.dataset.tag); } });
$("#movie-modal").addEventListener("click", e => { if(e.target.closest("[data-close]")){ $("#movie-modal").hidden = true; document.body.style.overflow = ""; } });
document.addEventListener("keydown", e => { if(e.key === "Escape"){ $("#movie-modal").hidden = true; document.body.style.overflow = ""; } });

/* —— 双角色 · 5问引导（离线版，标签匹配）—— */
const GUIDE_CONFIG = {
  viewer: [
    { key: "emotion", q: "此刻的你，心情如何？" },
    { key: "situation", q: "你正处在什么样的境遇里？" },
    { key: "value", q: "你渴望从电影里获得什么？" },
    { key: "audience", q: "你现在的角色是？" },
    { key: "theme", q: "你想看什么主题？" },
  ],
  facilitator: [
    { key: "emotion", q: "服务对象的需求是什么？" },
    { key: "situation", q: "服务对象想达成的目标是什么？" },
    { key: "value", q: "这次活动你的想法是什么？" },
    { key: "audience", q: "服务对象是谁？" },
    { key: "theme", q: "想带大家走哪个主题方向？" },
  ],
};
const CAT_TAGS = {};
for(const [name, t] of Object.entries(TAGS)) (CAT_TAGS[t.category] = CAT_TAGS[t.category] || []).push(name);
let guideRole = null, guideStep = 0, guideAnswers = {};
function startGuide(role){
  guideRole = role; guideStep = 0; guideAnswers = {};
  $("#role-select").hidden = true; $("#wizard").hidden = false; renderGuideStep();
}
function renderGuideStep(){
  const steps = GUIDE_CONFIG[guideRole], step = steps[guideStep];
  $("#wizard-step").textContent = `第 ${guideStep+1} / ${steps.length} 问`;
  $("#wizard-progress").style.width = ((guideStep+1)/steps.length*100) + "%";
  $("#wizard-question").textContent = step.q;
  const tags = CAT_TAGS[step.key] || [];
  $("#wizard-chips").innerHTML = tags.map(t => `<button class="chip chip--tag ${guideAnswers[step.key]===t?"is-selected":""}" data-tag="${esc(t)}">${esc(t)}</button>`).join("");
  $$("#wizard-chips .chip--tag").forEach(c => c.addEventListener("click", () => { guideAnswers[step.key] = c.dataset.tag; renderGuideStep(); }));
  $("#wizard-back").hidden = guideStep === 0;
  $("#wizard-next").querySelector("span").textContent = guideStep === steps.length-1 ? "生成推荐" : "下一步 →";
}
function localInterpretation(role, answers, titles){
  const ts = titles.slice(0,3).join("、") || "（暂无匹配）";
  const em = answers.emotion || "此刻", si = answers.situation || "当下";
  if(role === "facilitator") return `【影领家 · 带领建议】围绕「${em} + ${si}」这个案例，为你匹配了：${ts}。建议从情绪最贴近的一部先看，观影后引导大家分享「哪个瞬间最触动你」，并留意影片触发预警，为情绪敏感的成员预留支持空间。`;
  return `【寻影者 · 观影陪伴】此刻的「${em}」与「${si}」，为你挑选了：${ts}。建议在安静不被打扰的时候观看，不必急着「看懂」，允许自己被某个画面、某句台词轻轻接住；看完给自己留一点时间，把涌上来的感受写下来。`;
}
function renderGuidedResults(){
  const query = Object.values(guideAnswers).filter(Boolean).join(" ");
  const { intent, items } = recommend(query);
  $("#results").hidden = false;
  $("#echo-query").textContent = guideRole === "facilitator" ? "影领家 · 五问选片" : "寻影者 · 五问选片";
  $("#intent-tags").innerHTML = intent.length ? intent.map(t => `<span class="chip chip--gold">${esc(t)}</span>`).join("") : `<span class="chip chip--muted">未识别到明确情绪</span>`;
  const max = Math.max(...items.map(i => i.score), 0.0001);
  const titles = items.map(i => i.movie.title);
  $("#results-grid").innerHTML = `<div class="interpretation">${esc(localInterpretation(guideRole, guideAnswers, titles))}</div>` + items.map(it => cardHTML(it, max)).join("");
  $$(".movie-pill").forEach(p => p.addEventListener("click", () => openMovie(Number(p.dataset.id))));
  $("#results").scrollIntoView({behavior:"smooth", block:"start"});
}
$$(".role-card").forEach(c => c.addEventListener("click", () => startGuide(c.dataset.role)));
$("#wizard-next").addEventListener("click", () => {
  const steps = GUIDE_CONFIG[guideRole];
  if(guideStep < steps.length-1){ guideStep++; renderGuideStep(); } else { renderGuidedResults(); }
});
$("#wizard-back").addEventListener("click", () => { if(guideStep > 0){ guideStep--; renderGuideStep(); } });

/* —— 品牌切换（禅说电影 / 影领圈）—— */
const BRANDS = {
  chanshuo: { name: "禅说电影", tagline: "以影入道 · 借影观心" },
  yingling: { name: "影领圈", tagline: "让电影领你同行" },
};
function applyBrand(key){
  const b = BRANDS[key] || BRANDS.chanshuo;
  document.body.dataset.brand = key;
  $("#brand-name").textContent = b.name;
  $("#brand-tagline").textContent = b.tagline;
  $$(".brand-switch button").forEach(x => x.classList.toggle("is-active", x.dataset.brand === key));
  try { localStorage.setItem("cine_brand", key); } catch(e){}
}
document.addEventListener("click", e => {
  const btn = e.target.closest(".brand-switch button");
  if(btn) applyBrand(btn.dataset.brand);
});
applyBrand((() => { try { return localStorage.getItem("cine_brand"); } catch(e){ return null; } })() || "chanshuo");

loadTagOptions();
</script>
</body>
</html>
"""

html = (
    HTML.replace("__MOVIES_JSON__", MOVIES_JSON)
    .replace("__TAGS_JSON__", TAGS_JSON)
    .replace("__SYNONYMS_JSON__", SYNONYMS_JSON)
    .replace("__TAG_NAMES_JSON__", TAG_NAMES_JSON)
)

out = REPO_DIR / "cinearchive.html"
out.write_text(html, encoding="utf-8")
print(f"[export] 已生成独立分享文件：{out}")
print(f"[export] 大小：{out.stat().st_size / 1024:.1f} KB，含 {len(_movies)} 部电影 / {len(_tags)} 个标签")
