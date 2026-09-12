/* 寻影者 · 前端交互 */
(() => {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  const API = "/api/v1";

  // 海报渐变色板（暖调电影质感）
  const PALETTE = [
    ["#3a2c1d", "#6b4a2a"],
    ["#1f2a33", "#3d5a6b"],
    ["#2e1f2a", "#5d3a52"],
    ["#16261f", "#2f4f3c"],
    ["#3a2416", "#7a4a1f"],
    ["#20232e", "#4a4f6b"],
    ["#2c1f18", "#59422f"],
    ["#1c2a2e", "#3f5a58"],
  ];
  const gradientFor = (title) => {
    let h = 0;
    for (const c of title || "") h = (h * 31 + c.charCodeAt(0)) >>> 0;
    const [a, b] = PALETTE[h % PALETTE.length];
    return `linear-gradient(158deg, ${a} 0%, ${b} 100%)`;
  };

  const esc = (s) =>
    String(s ?? "").replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
    );

  const posterHTML = (movie, glyphSize = 78) => `
    <div class="poster" style="background:${gradientFor(movie.title)}">
      <span class="poster__glyph" style="font-size:${glyphSize}px">${esc(movie.title.charAt(0))}</span>
      <span class="poster__title">${esc(movie.title)}</span>
    </div>`;

  const TOKEN_KEY = "cinelib_token";
  const getToken = () => localStorage.getItem(TOKEN_KEY);
  const setToken = (t) => localStorage.setItem(TOKEN_KEY, t);

  async function api(path, opts = {}) {
    const headers = { "Content-Type": "application/json" };
    const token = getToken();
    if (token) headers["Authorization"] = "Bearer " + token;
    const res = await fetch(API + path, {
      headers,
      ...opts,
      body: opts.body ? JSON.stringify(opts.body) : undefined,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `请求失败 (${res.status})`);
    }
    return res.json();
  }

  const rateLine = (m) => `
    <span class="rating"><span class="rating__src">${esc(m.rating_domestic_source)}</span>
      <span class="rating__val">${m.rating_domestic || "—"}</span></span>
    <span class="meta-dot">·</span>
    <span class="rating"><span class="rating__src">${esc(m.rating_international_source)}</span>
      <span class="rating__val">${m.rating_international || "—"}</span></span>`;

  // ============ 推荐结果容器 ============
  const resultsSection = $("#results");

  function cardHTML(item, maxScore) {
    const m = item.movie;
    const rel = Math.max(55, Math.round((item.score / maxScore) * 100));
    const hitTags = (m.tags || [])
      .filter((t) => item.matched_tags.includes(t.name))
      .slice(0, 3);
    const tagHTML = hitTags
      .map((t) => `<span class="tag-pill tag-pill--hit">${esc(t.name)}</span>`)
      .join("");
    return `
      <article class="movie-pill reveal" data-id="${m.id}">
        <div class="movie-pill__poster" style="background:${gradientFor(m.title)}">${esc(m.title.charAt(0))}</div>
        <div class="movie-pill__main">
          <h3 class="movie-pill__title">${esc(m.title)}</h3>
          <p class="movie-pill__meta">${m.year} · ${esc(m.director)} · ${m.rating_domestic} 分</p>
        </div>
        <div class="movie-pill__tags">${tagHTML}</div>
        <span class="movie-pill__score">${rel}%</span>
      </article>`;
  }

  function bindCards(root) {
    $$(".movie-pill", root).forEach((card) => {
      card.addEventListener("click", () => openMovieById(Number(card.dataset.id)));
    });
  }

  // ============ 详情弹层 ============
  const modal = $("#movie-modal");
  const modalBody = $("#modal-body");

  async function openMovieById(id) {
    const full = await api(`/movies/${id}`);
    openMovie(full);
  }

  function openMovie(m) {
    const da = m.deep_analysis || {};
    const warnings = (m.trigger_warnings || []).length
      ? `<div class="warning">${(m.trigger_warnings || []).map(esc).join("<br>")}</div>`
      : "";

    // 有 5 问答案 → 请求 AI 按「此刻的你」个性化解读；否则展示通用内容
    const hasAnswers = !!lastGuideAnswers && Object.values(lastGuideAnswers).some((v) => v && String(v).trim());
    const supportBox = hasAnswers
      ? `<div class="detail-section">
          <h4>这部影片如何支持你</h4>
          <div id="personal-support" class="personal-box">
            <p class="personal-loading">正在为你细细解读，稍等片刻…</p>
          </div>
        </div>`
      : `<div class="detail-section">
          <h4>这部影片如何支持你</h4>
          <div class="tag-row">${(m.support_types || []).map((s) => `<span class="tag-pill">${esc(s)}</span>`).join("")}</div>
          <p><strong style="color:var(--ink)">适合人群：</strong>${esc((m.support_audiences || []).join("、"))}</p>
          <p>${esc(m.therapy_notes || "")}</p>
        </div>
        ${(m.discussion_questions || []).length
          ? `<div class="detail-section"><h4>观影后的讨论问题</h4><ul>${(m.discussion_questions || []).map((q) => `<li>${esc(q)}</li>`).join("")}</ul></div>`
          : ""}`;

    modalBody.innerHTML = `
      <div class="detail-hero">
        ${posterHTML(m, 96)}
        <div>
          <h3 class="detail-title">${esc(m.title)}</h3>
          <p class="detail-en">${esc(m.title_en)}</p>
        </div>
        <div class="detail-meta">
          <span>${m.year}</span><span class="meta-dot">·</span>
          <span>${esc(m.director)} 执导</span><span class="meta-dot">·</span>
          <span>${esc(m.country)}</span><span class="meta-dot">·</span>
          <span>${m.duration_min} 分钟</span>
        </div>
      </div>

      <p class="detail-synopsis">${esc(m.synopsis)}</p>

      <div class="detail-section">
        <h4>主创 · 评分</h4>
        <div class="detail-meta" style="margin:0 0 6px">${rateLine(m)}</div>
        <p>主演：${esc((m.cast || []).join("、"))}</p>
        <p>类型：${esc((m.genres || []).join(" · "))}</p>
      </div>

      <div class="detail-section">
        <h4>深度解读</h4>
        <div class="analysis-grid">
          <div class="analysis-box"><h5>主题</h5><p>${esc(da.theme || "—")}</p></div>
          <div class="analysis-box"><h5>艺术价值</h5><p>${esc(da.art_value || "—")}</p></div>
          <div class="analysis-box"><h5>教育价值</h5><p>${esc(da.edu_value || "—")}</p></div>
          <div class="analysis-box"><h5>治疗价值</h5><p>${esc(da.therapy_value || "—")}</p></div>
        </div>
      </div>

      ${supportBox}
      ${warnings ? `<div class="detail-section"><h4>观看提醒</h4>${warnings}</div>` : ""}

      <div class="detail-section" style="border-top:1px solid var(--hairline-soft);padding-top:22px">
        <h4>把这份触动，留下来</h4>
        <p style="font-size:13.5px;color:var(--ink-2);margin:4px 0 14px">观影后的感受值得被写下。去「我的观心」写一篇「观电影法」笔记，档案馆会给你一份专属回应，帮你把这份触动留在生命里。</p>
        <button class="ask-box__submit" id="to-notes-btn"><span>🪔 去我的观心 · 写下观影笔记</span></button>
      </div>`;

    // 按 5 问答案请求个性化解读（异步，不阻塞弹层）
    if (hasAnswers) {
      (async () => {
        const box = $("#personal-support");
        try {
          const res = await api(`/movies/${m.id}/personal`, {
            method: "POST",
            body: { answers: lastGuideAnswers },
          });
          if (!box) return;
          const qs = (res.questions || []).length
            ? `<div class="detail-section" style="margin-top:18px">
                <h4>观影观己 · 带着问题去看</h4>
                <ul class="personal-questions">${res.questions.map((q) => `<li>${esc(q)}</li>`).join("")}</ul>
              </div>`
            : "";
          box.innerHTML = `
            <div class="personal-support">${esc(res.support || "这部影片如何支持你，留给你在观影中去体会。")}</div>
            ${qs}`;
        } catch (e) {
          if (!box) return;
          box.innerHTML = `
            <div class="tag-row">${(m.support_types || []).map((s) => `<span class="tag-pill">${esc(s)}</span>`).join("")}</div>
            <p>${esc(m.therapy_notes || "")}</p>
            <p style="font-size:12.5px;color:var(--ink-3);margin-top:8px">个性化解读暂时不可用，先看看这份通用指引。</p>`;
        }
      })();
    }

    // 引导去「我的观心」写笔记（自动带上这部影片）
    const toNotes = $("#to-notes-btn");
    if (toNotes) {
      toNotes.addEventListener("click", () => {
        closeModal();
        openGrowth().then(() => {
          const nm = $("#note-movie");
          if (nm) nm.value = m.title;
          const wrap = $("#note-wrap");
          if (wrap) wrap.scrollIntoView({ behavior: "smooth", block: "center" });
        });
      });
    }

    modal.hidden = false;
    document.body.style.overflow = "hidden";
  }

  function closeModal() {
    modal.hidden = true;
    document.body.style.overflow = "";
  }
  modal.addEventListener("click", (e) => {
    if (e.target.closest("[data-close]")) closeModal();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !modal.hidden) closeModal();
  });

  // ============ 我的观心（成长中心） ============
  const growthModal = $("#growth-modal");
  async function openGrowth() {
    try {
      const p = await api("/me/progress");
      const lights = Array.from({ length: 21 }, (_, i) =>
        `<span class="light-dot ${i < p.checkin_days ? "is-lit" : ""}">${i < p.checkin_days ? "🕯" : "·"}</span>`
      ).join("");
      const badges = p.badges
        .map((b) =>
          `<div class="badge ${b.earned ? "is-earned" : ""}" ${b.earned ? 'data-earned="1"' : ""}>
            <span class="badge__icon">${b.earned ? "🕯" : "🔒"}</span>
            <span class="badge__name">${esc(b.name)}</span>
            <span class="badge__desc">${esc(b.desc)}</span>
            ${b.earned ? '<span class="badge__lit">已点亮</span>' : ""}
          </div>`
        )
        .join("");
      $("#growth-body").innerHTML = `
        <div class="growth-hero">
          <p class="section-kicker">我的观心</p>
          <h3 class="growth-level">${esc(p.level_name)}</h3>
          <p class="growth-level-desc">${esc(p.level_desc)}</p>
          <div class="growth-bar"><span style="width:${p.progress_pct}%"></span></div>
          <p class="growth-next">下一段位：${esc(p.next_level_name)}</p>
        </div>
        <div class="growth-stats">
          <div><strong>${p.checkin_days}</strong><span>点亮心灯</span></div>
          <div><strong>${p.note_count}</strong><span>观影笔记</span></div>
          <div><strong>${p.search_count}</strong><span>寻影次数</span></div>
          <div><strong>${p.checkin_streak}</strong><span>连续天数</span></div>
        </div>
        <div class="growth-section">
          <h4>21天观电影法打卡践行</h4>
          <div class="lights">${lights}</div>
          <button class="ask-box__submit" id="checkin-btn"><span>点亮今天 🕯</span></button>
          <p id="checkin-msg" style="color:var(--gold-soft);font-size:13px;margin-top:8px"></p>
        </div>
        <div class="growth-section">
          <h4>「观电影法」笔记</h4>
          <p class="note-guide">🪞 这个故事里，有哪一点像你的人生脚本？</p>
          <div id="note-wrap">
            <input id="note-movie" placeholder="哪部电影（可留空，自己填写）" style="width:100%;margin-bottom:12px;padding:10px;border-radius:10px;border:1px solid var(--hairline-soft);background:var(--surface);color:var(--ink)" />
            <div id="note-fields"></div>
            <div style="margin-top:12px">
              <button class="ask-box__submit" id="note-submit"><span>提交笔记 · 获得专属回应</span></button>
            </div>
            <div id="note-result" class="interpretation" style="margin-top:12px;display:none"></div>
          </div>
        </div>
        <div class="growth-section">
          <h4>🎬 我的人生电影</h4>
          <p class="life-log__tip">每一次观己都留在这里。同一条线出现了几次、哪一次松动了，回看时看得见。</p>
          <div id="my-life-logs"><p style="font-size:13px;color:var(--ink-3)">加载中…</p></div>
        </div>
        <div class="growth-section">
          <h4>👣 我的印记</h4>
          <div class="badges">${badges}</div>
        </div>
        <div class="growth-section">
          <h4>我的笔记</h4>
          <div id="my-notes"><p style="font-size:13px;color:var(--ink-3)">加载中…</p></div>
        </div>`;
      growthModal.hidden = false;
      document.body.style.overflow = "hidden";

      $("#checkin-btn").addEventListener("click", async () => {
        const r = await api("/checkin", { method: "POST", body: {} });
        $("#checkin-msg").textContent = r.message;
        setTimeout(openGrowth, 400);
      });

      // 「观电影法」观影笔记字段（第三项对应「看别人的故事 ↔ 自己的人生」联动）
      const NOTE_FIELDS = [
        { key: "内心触动的片段", ph: "哪个画面、哪段情节，最触动你？" },
        { key: "喜欢的台词", ph: "有没有哪句台词，你想记下来？" },
        { key: "像你人生脚本的地方", ph: "这个故事、这个角色，有哪一点像你自己的人生脚本？" },
        { key: "电影带来的思考", ph: "这部电影让你想到了什么？内心的想法？" },
      ];

      // 拉取影片列表（用于按名称匹配 movie_id）
      let allMovies = [];
      try {
        allMovies = await api("/movies?limit=100");
      } catch (e) {}

      function renderNoteFields() {
        $("#note-fields").innerHTML = NOTE_FIELDS
          .map(
            (f) =>
              `<div style="margin-bottom:12px"><label style="font-size:13px;color:var(--ink-2)">${esc(f.key)}</label>
              <textarea class="note-input" data-key="${esc(f.key)}" rows="2" placeholder="${esc(f.ph)}" style="width:100%;margin-top:6px;padding:10px;border-radius:10px;border:1px solid var(--hairline-soft);background:var(--surface);color:var(--ink);font-family:var(--font-sans);font-size:14px;resize:vertical"></textarea></div>`
          )
          .join("");
      }
      renderNoteFields();
      $("#note-submit").addEventListener("click", async () => {
        const content = {};
        $$(".note-input").forEach((el) => { content[el.dataset.key] = el.value.trim(); });
        const filled = Object.values(content).filter(Boolean).length;
        if (!filled) {
          $("#note-result").style.display = "block";
          $("#note-result").textContent = "先写下一点感受，再提交吧。";
          return;
        }
        const btn = $("#note-submit");
        btn.classList.add("is-loading", "is-waiting");
        btn.querySelector("span").textContent = "专属回应正在为你而来……";
        try {
          const movieName = $("#note-movie").value.trim();
          let movieId = null;
          if (movieName) {
            const hit = allMovies.find((mv) => mv.title === movieName || mv.title.includes(movieName) || movieName.includes(mv.title));
            if (hit) movieId = hit.id;
            else content["电影"] = movieName; // 没匹配到库内影片，就存进笔记内容
          }
          const res = await api("/notes", { method: "POST", body: { role: "viewer", movie_id: movieId, content } });
          $("#note-result").style.display = "block";
          $("#note-result").textContent = res.llm_response;
          loadMyNotes();
        } catch (e) {
          $("#note-result").style.display = "block";
          $("#note-result").textContent = "提交失败：" + e.message;
        } finally {
          btn.classList.remove("is-loading", "is-waiting");
          btn.querySelector("span").textContent = "提交笔记 · 获得专属回应";
        }
      });

      // 我的人生电影（观己档案）
      async function loadMyLifeLogs() {
        try {
          const logs = await api("/life/logs");
          if (!logs.length) {
            $("#my-life-logs").innerHTML = '<p style="font-size:13px;color:var(--ink-3)">还没有放映过自己的人生电影——去首页「看自己的人生电影」试试。</p>';
            return;
          }
          $("#my-life-logs").innerHTML = logs
            .map(
              (lg) => `
            <div class="life-log">
              <div class="life-log__head">
                <span class="life-log__title">《${esc(lg.title || "未命名")}》</span>
                <span class="life-log__date">${esc(String(lg.created_at || "").slice(0, 10))}</span>
              </div>
              ${lg.tagline ? `<p class="life-log__tagline">「${esc(lg.tagline)}」</p>` : ""}
              ${lg.pattern ? `<p class="life-log__pattern">那条线：${esc(lg.pattern)}</p>` : ""}
              <button class="mini-btn life-log__toggle" type="button">展开看这一次的回应</button>
              <div class="life-log__review" hidden>${esc(lg.review || "")}</div>
            </div>`
            )
            .join("");
          $$(".life-log__toggle").forEach((b) =>
            b.addEventListener("click", () => {
              const box = b.parentElement.querySelector(".life-log__review");
              box.hidden = !box.hidden;
              b.textContent = box.hidden ? "展开看这一次的回应" : "收起";
            })
          );
        } catch (e) {
          $("#my-life-logs").innerHTML = '<p style="font-size:13px;color:var(--ink-3)">人生电影档案加载失败</p>';
        }
      }
      loadMyLifeLogs();

      // 我的笔记列表
      async function loadMyNotes() {
        try {
          const notes = await api("/notes");
          if (!notes.length) {
            $("#my-notes").innerHTML = `<p style="font-size:13px;color:var(--ink-3)">还没有笔记，写下第一篇吧。</p>`;
            return;
          }
          $("#my-notes").innerHTML = notes.map((n) => `
            <div class="note-item">
              <p class="note-item__meta">${n.role === "facilitator" ? "复盘笔记 · 历史" : "寻影者 · 观影"} · ${esc((n.content && Object.values(n.content).filter(Boolean).join(" / ")) || "")}</p>
              <p class="note-item__resp">${esc(n.llm_response || "")}</p>
            </div>`).join("");
        } catch (e) {
          $("#my-notes").innerHTML = `<p style="font-size:13px;color:var(--ink-3)">笔记加载失败</p>`;
        }
      }
      loadMyNotes();
    } catch (e) {
      $("#growth-body").innerHTML = `<p style="color:var(--ink-2)">加载观心数据失败：${esc(e.message)}</p>`;
      growthModal.hidden = false;
      document.body.style.overflow = "hidden";
    }
  }
  $("#growth-btn").addEventListener("click", openGrowth);
  growthModal.addEventListener("click", (e) => {
    if (e.target.closest("[data-close]")) {
      growthModal.hidden = true;
      document.body.style.overflow = "";
    }
  });

  // ============ 入场动画 ============
  const io = new IntersectionObserver(
    (entries) =>
      entries.forEach((en) => {
        if (en.isIntersecting) {
          en.target.classList.add("is-visible");
          io.unobserve(en.target);
        }
      }),
    { threshold: 0.12 }
  );
  function observeReveal(root) {
    $$(".reveal:not(.is-visible)", root).forEach((el) => io.observe(el));
  }

  // ============ 公众号 H5 静默登录 ============
  function handleMpLogin() {
    // 只处理「登录回调带回来的 token」，不再自动跳转微信登录
    // （避免微信内置浏览器里自动跳转导致黑屏/服务错误；登录改为点按钮触发）
    try {
      const params = new URLSearchParams(location.search);
      const token = params.get("token");
      if (token) {
        setToken(token);
        params.delete("token");
        const qs = params.toString();
        history.replaceState(null, "", location.pathname + (qs ? "?" + qs : "") + location.hash);
      }
    } catch (e) {
      console.warn("登录回调处理失败", e);
    }
  }

  // 浏览器访客自动登录（开发模式）：给每位访客一个稳定身份，让「观心」等功能可用
  async function ensureGuestLogin() {
    if (getToken()) return;
    try {
      let code = localStorage.getItem("cine_guest_code");
      if (!code) {
        code = "guest-" + Math.random().toString(36).slice(2, 10);
        localStorage.setItem("cine_guest_code", code);
      }
      const data = await api("/auth/wx-login", {
        method: "POST",
        body: { code },
      });
      setToken(data.token);
    } catch (e) {
      console.warn("访客登录失败", e);
    }
  }

  // ============ 看别人的电影 · 5问选片 ============
  const GUIDE_CONFIG = [
    { key: "emotion", q: "此刻的你，心情如何？", type: "free", ph: "如：焦虑、迷茫、疲惫、期待、平静…" },
    { key: "situation", q: "你正处在什么样的境遇里？", type: "free", ph: "如：刚换了工作、孩子升学、独自在外打拼、家人需要照顾…" },
    { key: "value", q: "你希望从电影中获得什么？（可多选或自己填写）", type: "tags+free", ph: "如：获得力量、被理解、找回方向…" },
    { key: "audience", q: "你的专业 / 职业是？（现实中的身份标签，可多选或自己填写）", type: "tags+free", ph: "如：设计师、教师、全职妈妈、创业者、学生…" },
    { key: "theme", q: "你想看什么主题？（可多选或自己填写）", type: "tags+free" },
  ];
  const EXTRA_AUDIENCE_TAGS = ["影领家", "影视心理分析师", "HR"];

  let guideStep = 0;
  let guideSelections = {}; // {key: [tag...]}
  let guideFree = {}; // {key: 自由填写文本}
  let guideThemes = {};

  async function loadGuideThemes() {
    guideThemes = await api("/themes");
  }

  function resetGuide() {
    guideStep = 0;
    guideSelections = {};
    guideFree = {};
    renderGuideStep();
  }

  function renderGuideStep() {
    const steps = GUIDE_CONFIG;
    const step = steps[guideStep];
    $("#wizard-step").textContent = `第 ${guideStep + 1} / ${steps.length} 问`;
    $("#wizard-progress").style.width = `${((guideStep + 1) / steps.length) * 100}%`;
    $("#wizard-question").textContent = step.q;

    let html = "";
    if (step.type !== "free") {
      let tags = guideThemes[step.key] || [];
      if (step.key === "audience") {
        tags = tags.concat(EXTRA_AUDIENCE_TAGS.map((n) => ({ name: n })));
      }
      const sel = guideSelections[step.key] || [];
      html += `<div class="wizard__chips">${tags
        .map((t) => {
          const on = sel.includes(t.name);
          return `<button class="chip chip--tag ${on ? "is-selected" : ""}" data-tag="${esc(t.name)}">${esc(t.name)}</button>`;
        })
        .join("")}</div>`;
    }
    if (step.type === "free" || step.type === "tags+free") {
      html += `<input id="wizard-free" placeholder="${esc(step.ph || "自己填写")}" value="${esc(guideFree[step.key] || "")}" style="width:100%;margin:2px 0 0;padding:11px 14px;border-radius:999px;border:1px solid var(--hairline-soft);background:var(--surface);color:var(--ink)" />`;
    }
    $("#wizard-chips").innerHTML = html;

    // 多选切换（不整块重渲染，避免输入框失焦）
    $$("#wizard-chips .chip--tag").forEach((c) =>
      c.addEventListener("click", () => {
        const arr = guideSelections[step.key] || (guideSelections[step.key] = []);
        const i = arr.indexOf(c.dataset.tag);
        if (i >= 0) {
          arr.splice(i, 1);
          c.classList.remove("is-selected");
        } else {
          arr.push(c.dataset.tag);
          c.classList.add("is-selected");
        }
      })
    );
    const freeInput = $("#wizard-free");
    if (freeInput) {
      freeInput.addEventListener("input", () => {
        guideFree[step.key] = freeInput.value;
      });
    }

    $("#wizard-back").hidden = guideStep === 0;
    const btn = $("#wizard-next");
    btn.querySelector("span").textContent =
      guideStep === steps.length - 1 ? "为你推荐" : "下一步 →";
  }

  function buildGuideAnswers() {
    const answers = {};
    for (const step of GUIDE_CONFIG) {
      const sel = (guideSelections[step.key] || []).join(" ");
      const free = (guideFree[step.key] || "").trim();
      answers[step.key] = [sel, free].filter(Boolean).join(" ");
    }
    return answers;
  }

  async function submitGuide() {
    const submit = $("#wizard-next");
    const label = submit.querySelector("span");
    submit.classList.add("is-loading", "is-waiting");
    submit.disabled = true;
    if (label) label.textContent = "专属回应正在为你而来……";
    try {
      lastGuideAnswers = buildGuideAnswers(); // 记住本次 5 问答案
      const data = await api("/recommend/top3", {
        method: "POST",
        body: { role: "viewer", answers: lastGuideAnswers },
      });
      renderTop3Results(data);
    } catch (e) {
      alert("推荐失败：" + e.message);
    } finally {
      submit.classList.remove("is-loading", "is-waiting");
      submit.disabled = false;
      if (label) label.textContent = "为你推荐";
    }
  }

  let lastGuideAnswers = null; // 最近一次 5 问答案

  function top3CardHTML(mv, i) {
    return `
      <article class="top3-card reveal">
        <span class="top3-card__rank">${i + 1}</span>
        <div class="top3-card__main">
          <h3 class="top3-card__title">《${esc(mv.title)}》</h3>
          <p class="top3-card__meta">${esc(mv.year || "—")} · ${esc(mv.country || "")} · ${esc(mv.director || "佚名")} 执导 · ${esc(mv.genre || "")}</p>
          ${mv.rating ? `<span class="top3-card__rating">豆瓣 ${esc(mv.rating)}</span>` : ""}
          <p class="top3-card__synopsis">${esc(mv.synopsis || "")}</p>
          ${mv.angle ? `<p class="top3-card__angle">🎬 <strong>建议切入角度</strong>：${esc(mv.angle)}</p>` : ""}
          <p class="top3-card__reason">${esc(mv.reason || "")}</p>
        </div>
      </article>`;
  }

  function renderTop3Results(data) {
    // 提交后进入「结果视图」：隐藏向导，只展示结果 + 返回首页
    $("#wizard").hidden = true;
    resultsSection.hidden = false;
    $("#echo-query").textContent = "为你挑选的三部电影";
    $("#intent-tags").innerHTML = "";
    $("#results-note").textContent = "";
    const grid = $("#results-grid");
    grid.innerHTML =
      (data.movies || []).map((mv, i) => top3CardHTML(mv, i)).join("") +
      `<div style="text-align:center;margin-top:22px">
         <button class="board-enter" id="back-home-btn"><span>← 返回首页</span></button>
       </div>`;
    const bh = $("#back-home-btn");
    if (bh) bh.addEventListener("click", backHome);
    window.scrollTo({ top: 0, behavior: "smooth" });
    resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
    observeReveal(grid);
  }

  $("#wizard-next").addEventListener("click", () => {
    const steps = GUIDE_CONFIG;
    if (guideStep < steps.length - 1) {
      guideStep++;
      renderGuideStep();
    } else {
      submitGuide();
    }
  });
  $("#wizard-back").addEventListener("click", () => {
    if (guideStep > 0) {
      guideStep--;
      renderGuideStep();
    }
  });

  // ============ 登录（微信 / 手机号） ============
  const loginModal = $("#login-modal");
  function openLogin() {
    $("#login-body").innerHTML = `
      <div class="login-hero">
        <p class="section-kicker">Sign in</p>
        <h3 class="login-title">登录 · 让档案馆更懂你</h3>
        <p class="login-sub">登录后，会获得更精准的电影推荐、「观电影法」笔记回应等专属体验。</p>
      </div>
      <div class="login-options">
        <button class="login-opt" id="wx-login-btn">
          <span class="login-opt__icon">💬</span>
          <span><strong>微信登录</strong><small>识别你正在使用的微信号</small></span>
        </button>
      </div>`;
    loginModal.hidden = false;
    document.body.style.overflow = "hidden";

    $("#wx-login-btn").addEventListener("click", () => {
      const isWeChat = /MicroMessenger/i.test(navigator.userAgent);
      if (isWeChat) {
        const back = encodeURIComponent(location.href);
        location.replace(`/api/v1/auth/mp/authorize?redirect_uri=${back}&scope=snsapi_base`);
      } else {
        alert("请在微信中打开本页面，即可使用微信登录");
      }
    });
  }
  loginModal.addEventListener("click", (e) => {
    if (e.target.closest("[data-close]")) {
      loginModal.hidden = true;
      document.body.style.overflow = "";
    }
  });

  // ============ 你的人生电影 · 观己观心 ============
  let lifeProfile = {}; // 当前角色档案（供对话使用）
  let lifeChatHistory = []; // 人生电影对话历史 [{role, content}]

  function lifePosterColors(title) {
    let h = 0;
    for (const c of title || "") h = (h * 31 + c.charCodeAt(0)) >>> 0;
    return PALETTE[h % PALETTE.length];
  }

  function wrapText(ctx, text, maxWidth) {
    const chars = [...String(text)];
    const lines = [];
    let line = "";
    for (const ch of chars) {
      if (ctx.measureText(line + ch).width > maxWidth && line) {
        lines.push(line);
        line = ch;
      } else {
        line += ch;
      }
    }
    if (line) lines.push(line);
    return lines;
  }

  // 电影元素：取景框四角
  function frameCorners(ctx, W, H, m, len, color) {
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    const seg = [
      [[m, m + len], [m, m], [m + len, m]],
      [[W - m - len, m], [W - m, m], [W - m, m + len]],
      [[m, H - m - len], [m, H - m], [m + len, H - m]],
      [[W - m - len, H - m], [W - m, H - m], [W - m, H - m - len]],
    ];
    seg.forEach((pts) => {
      ctx.beginPath();
      ctx.moveTo(pts[0][0], pts[0][1]);
      ctx.lineTo(pts[1][0], pts[1][1]);
      ctx.lineTo(pts[2][0], pts[2][1]);
      ctx.stroke();
    });
  }

  // 电影元素：一排胶片齿孔
  function sprocketRow(ctx, cx, y, width, color) {
    const n = 15, gap = width / n;
    ctx.fillStyle = color;
    for (let i = 0; i < n; i++) {
      ctx.fillRect(cx - width / 2 + i * gap + 3, y, gap - 7, 9);
    }
  }

  function drawLifePoster(data, name) {
    const W = 750, H = 1000;
    const canvas = document.createElement("canvas");
    canvas.width = W; canvas.height = H;
    const ctx = canvas.getContext("2d");

    // —— 纸感底色 + 极淡纸纹 ——
    ctx.fillStyle = "#F7F2E8";
    ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = "rgba(120,105,85,0.045)";
    for (let i = 0; i < 1000; i++) {
      ctx.fillRect(Math.random() * W, Math.random() * H, 1, 1);
    }

    const INK = "rgba(46,42,36,0.94)";
    const GOLD = "rgba(176,140,72,0.92)";
    const GOLD_SOFT = "rgba(176,140,72,0.42)";
    const GREY = "rgba(96,88,76,0.72)";
    ctx.textAlign = "center";
    ctx.lineCap = "round";

    // 取景框四角（不进入文字区）
    frameCorners(ctx, W, H, 46, 44, GOLD_SOFT);

    // 顶部品牌 + 齿孔装饰
    ctx.fillStyle = GREY;
    ctx.font = "500 21px 'Songti SC','Noto Serif SC',serif";
    ctx.fillText("禅 说 电 影 · 寻 影 者", W / 2, 106);
    sprocketRow(ctx, W / 2, 134, 300, "rgba(176,140,72,0.30)");

    // —— 中部留白处的电影元素：光圈（镜头）+ 柔和光晕，全部在文字区之上 ——
    const cx = W / 2, cy = 392;
    const halo = ctx.createRadialGradient(cx, cy, 10, cx, cy, 240);
    halo.addColorStop(0, "rgba(176,140,72,0.10)");
    halo.addColorStop(0.55, "rgba(176,140,72,0.045)");
    halo.addColorStop(1, "rgba(176,140,72,0)");
    ctx.fillStyle = halo;
    ctx.fillRect(0, 150, W, 480);

    ctx.strokeStyle = "rgba(176,140,72,0.34)";
    ctx.lineWidth = 1.6;
    [58, 92, 126].forEach((r, i) => {
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.stroke();
      // 光圈叶片：每圈画 6 段短弧，做出镜头光圈的感觉
      ctx.save();
      ctx.strokeStyle = `rgba(176,140,72,${0.30 - i * 0.06})`;
      for (let k = 0; k < 6; k++) {
        const a0 = (Math.PI * 2 * k) / 6 + 0.35;
        ctx.beginPath();
        ctx.arc(cx, cy, r, a0, a0 + 0.5);
        ctx.stroke();
      }
      ctx.restore();
    });
    ctx.fillStyle = "rgba(176,140,72,0.5)";
    ctx.beginPath();
    ctx.arc(cx, cy, 4.5, 0, Math.PI * 2);
    ctx.fill();

    // —— 文字区（严格从 y=650 起，与上方元素互不重叠）——
    let ty = 650;
    ctx.fillStyle = INK;
    const rawTitle = `《${data.title}》`;
    const fs = rawTitle.length <= 9 ? 60 : rawTitle.length <= 13 ? 50 : 42;
    ctx.font = `700 ${fs}px 'Songti SC','Noto Serif SC',serif`;
    const titleLines = wrapText(ctx, rawTitle, W - 170).slice(0, 2);
    for (const ln of titleLines) { ctx.fillText(ln, W / 2, ty); ty += fs + 12; }

    // 类型
    ctx.fillStyle = GOLD;
    ctx.font = "500 23px 'Songti SC',serif";
    ctx.fillText((data.genre || "人生电影").replace(/\s*\/\s*/g, " · "), W / 2, ty + 6);
    ty += 46;

    // 海报文案
    ctx.fillStyle = INK;
    ctx.font = "400 29px 'Songti SC',serif";
    const tagLines = wrapText(ctx, data.tagline || "", W - 400).slice(0, 2);   // 右侧留给二维码
    for (const ln of tagLines) { ctx.fillText(ln, W / 2, ty + 26); ty += 42; }

    // —— 底部：主演 / 金句（居中，上移一点，给右下角二维码腾位置）——
    ctx.fillStyle = GREY;
    ctx.font = "400 22px 'Songti SC',serif";
    ctx.fillText(`主演 · ${name || "你"}`, W / 2, H - 136);
    ctx.strokeStyle = GOLD_SOFT;
    ctx.lineWidth = 1.4;
    ctx.beginPath();
    ctx.moveTo(W / 2 - 58, H - 114);
    ctx.lineTo(W / 2 + 58, H - 114);
    ctx.stroke();
    ctx.fillStyle = GOLD;
    ctx.font = "400 20px 'Songti SC',serif";
    ctx.fillText("跳出人生这场戏，带着觉知勇敢如戏", W / 2, H - 86);

    // —— 右下角二维码：扫码进入「寻影者」，方便转发 ——
    if (typeof qrcode === "function") {
      try {
        const qr = qrcode(0, "M");
        qr.addData(location.origin + "/");
        qr.make();
        const n = qr.getModuleCount();
        const size = 120, pad = 8;
        const qx = W - 46 - 14 - size;
        const qy = H - 46 - 30 - size;
        ctx.fillStyle = "rgba(255,255,255,0.95)";
        ctx.fillRect(qx - pad, qy - pad, size + pad * 2, size + pad * 2);
        const cell = size / n;
        ctx.fillStyle = "rgba(46,42,36,0.95)";
        for (let r = 0; r < n; r++) {
          for (let c = 0; c < n; c++) {
            if (qr.isDark(r, c)) {
              ctx.fillRect(qx + c * cell, qy + r * cell, Math.ceil(cell), Math.ceil(cell));
            }
          }
        }
        ctx.fillStyle = GREY;
        ctx.font = "400 15px 'Songti SC',serif";
        ctx.fillText("扫码 · 开始寻找", qx + size / 2, qy - pad - 9);
      } catch (e) {}
    }

    return canvas.toDataURL("image/png");
  }

  // —— 角色档案草稿：未填完退出后，5 分钟内回来可继续 ——
  const LIFE_DRAFT_KEY = "life_draft";
  const LIFE_DRAFT_TTL = 5 * 60 * 1000;
  const LIFE_FIELD_IDS = ["life-role-name", "life-movie-name", "life-born", "life-turning", "life-2026"];

  function lifeFieldValues() {
    return LIFE_FIELD_IDS.map((id) => ($("#" + id) ? $("#" + id).value : ""));
  }

  function saveLifeDraft() {
    try {
      const vals = lifeFieldValues();
      if (!vals.some((v) => v && v.trim())) {
        localStorage.removeItem(LIFE_DRAFT_KEY);
        return;
      }
      localStorage.setItem(
        LIFE_DRAFT_KEY,
        JSON.stringify({
          role_name: vals[0], movie_name: vals[1], born_story: vals[2],
          turning_story: vals[3], story_2026: vals[4], ts: Date.now(),
        })
      );
    } catch (e) {}
  }

  function readLifeDraft() {
    try {
      const raw = localStorage.getItem(LIFE_DRAFT_KEY);
      if (!raw) return null;
      const d = JSON.parse(raw);
      if (!d || !d.ts || Date.now() - d.ts > LIFE_DRAFT_TTL) {
        localStorage.removeItem(LIFE_DRAFT_KEY);
        return null;
      }
      const filled = [d.role_name, d.movie_name, d.born_story, d.turning_story, d.story_2026]
        .some((v) => v && String(v).trim());
      return filled ? d : null;
    } catch (e) {
      return null;
    }
  }

  function clearLifeDraft() {
    try { localStorage.removeItem(LIFE_DRAFT_KEY); } catch (e) {}
  }

  function applyLifeDraft(d) {
    const vals = [d.role_name, d.movie_name, d.born_story, d.turning_story, d.story_2026];
    LIFE_FIELD_IDS.forEach((id, i) => {
      const el = $("#" + id);
      if (el) el.value = vals[i] || "";
    });
  }

  function showLifeDraftPrompt(d) {
    const old = $("#life-draft-prompt");
    if (old) old.remove();
    const div = document.createElement("div");
    div.id = "life-draft-prompt";
    div.className = "life-draft";
    div.innerHTML = `
      <span>上次你填到一半，是否继续？</span>
      <button id="life-draft-resume">继续填写</button>
      <button id="life-draft-restart">重新开始</button>`;
    const form = $("#life-form");
    if (!form) return;
    form.prepend(div);
    $("#life-draft-resume").addEventListener("click", () => {
      applyLifeDraft(d);
      saveLifeDraft();
      div.remove();
    });
    $("#life-draft-restart").addEventListener("click", () => {
      clearLifeDraft();
      LIFE_FIELD_IDS.forEach((id) => { const el = $("#" + id); if (el) el.value = ""; });
      div.remove();
    });
  }

  function resetLifeForm() {
    clearLifeDraft();
    LIFE_FIELD_IDS.forEach((id) => {
      const el = $("#" + id);
      if (el) el.value = "";
    });
    const prompt = $("#life-draft-prompt");
    if (prompt) prompt.remove();
    $("#life-result").hidden = true;
    $("#life-form").hidden = false;
    $("#life-form").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function renderLifeResult(data) {
    const roleName = $("#life-role-name").value.trim() || "你";
    const poster = drawLifePoster(data, roleName);
    lifeChatHistory = [];
    $("#life-result").hidden = false;
    $("#life-result").innerHTML = `
      <div class="life-film">
        <img class="life-poster" src="${poster}" alt="${esc(data.title)} 海报" />
        <p class="life-poster-tip">👆 长按上方海报，可保存分享</p>
        <div class="life-film__meta">
          <span class="life-film__genre">${esc(data.genre || "人生电影")}</span>
          <span class="life-film__tagline">「${esc(data.tagline || "")}」</span>
        </div>
        <p class="life-film__review">${esc(data.review || "")}</p>
        ${data.id ? '<p class="life-saved">✅ 这一次已经存入「我的观心 · 我的人生电影」</p>' : ""}

        <div class="life-chat">
          <h4 class="life-chat__title">🪞 看完这一幕，你想说点什么？</h4>
          <p class="life-chat__tip">写下你的感受、想法或疑问，我陪你继续看这场戏。</p>
          <div class="life-chat__log" id="life-chat-log"></div>
          <div class="life-chat__bar">
            <input id="life-chat-input" placeholder="写下你的感受或想法…" />
            <button id="life-chat-send">发送</button>
          </div>
        </div>

        <div class="life-actions">
          <button class="board-enter" id="life-again"><span>↻ 重新建立角色档案</span></button>
          <button class="board-enter board-enter--ghost" id="life-home-btn"><span>回到首页</span></button>
        </div>

        <p class="life-again-tip">🌱 人生还有很多幕——下次回来，可以换一段人生故事（另一段转折、另一个当下的困惑）再观一次自己。<br />每一幕，都会给你新的看见。</p>
      </div>`;
    $("#life-again").addEventListener("click", resetLifeForm);
    $("#life-home-btn").addEventListener("click", backHome);
    $("#life-chat-send").addEventListener("click", sendLifeChat);
    $("#life-chat-input").addEventListener("keydown", (e) => {
      if (e.key === "Enter") sendLifeChat();
    });
  }

  function appendChatBubble(kind, text) {
    const log = $("#life-chat-log");
    if (!log) return null;
    const div = document.createElement("div");
    div.className = `chat-bubble chat-bubble--${kind}`;
    div.textContent = text;
    log.appendChild(div);
    div.scrollIntoView({ behavior: "smooth", block: "nearest" });
    return div;
  }

  async function sendLifeChat() {
    const input = $("#life-chat-input");
    if (!input) return;
    const msg = input.value.trim();
    if (!msg) return;
    input.value = "";
    appendChatBubble("user", msg);
    const loading = appendChatBubble("ai", "……");
    try {
      const res = await api("/life/chat", {
        method: "POST",
        body: {
          profile: lifeProfile,
          context: lastGuideAnswers || {},
          history: lifeChatHistory.slice(),
          message: msg,
        },
      });
      lifeChatHistory.push({ role: "user", content: msg });
      lifeChatHistory.push({ role: "assistant", content: res.reply });
      if (loading) loading.textContent = res.reply;
    } catch (e) {
      if (loading) loading.textContent = "回应失败：" + e.message;
    }
  }

  // 建立角色档案 → 生成「你的人生电影」
  $("#life-submit").addEventListener("click", async () => {
    const roleName = $("#life-role-name").value.trim();
    if (!roleName) { alert("先写下你的角色名吧"); return; }
    const btn = $("#life-submit");
    btn.classList.add("is-loading", "is-waiting");
    btn.disabled = true;
    btn.querySelector("span").textContent = "专属回应正在为你而来……";
    try {
      lifeProfile = {
        role_name: roleName,
        movie_name: $("#life-movie-name").value.trim(),
        born_story: $("#life-born").value.trim(),
        turning_story: $("#life-turning").value.trim(),
        story_2026: $("#life-2026").value.trim(),
      };
      const data = await api("/life/movie", {
        method: "POST",
        body: { profile: lifeProfile, context: lastGuideAnswers || {} },
      });
      clearLifeDraft(); // 已生成，草稿使命完成
      $("#life-form").hidden = true;
      renderLifeResult(data);
    } catch (e) {
      alert("生成失败：" + e.message);
    } finally {
      btn.classList.remove("is-loading", "is-waiting");
      btn.disabled = false;
      btn.querySelector("span").textContent = "放映我的人生电影";
    }
  });

  // ============ 首页双板块：进入式交互 ============
  function backHome() {
    $("#guide").hidden = false;
    $("#life").hidden = false;
    $("#wizard").hidden = true;
    $("#life-form").hidden = true;
    $("#life-result").hidden = true;
    resultsSection.hidden = true;
    $("#guide-enter").style.display = "";
    $("#life-enter").style.display = "";
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  function enterGuide() {
    $("#life").hidden = true;
    $("#wizard").hidden = false;
    $("#guide-enter").style.display = "none";
    renderGuideStep();
    // 直接滚到问答题，点一次就能开始回答
    $("#wizard").scrollIntoView({ behavior: "smooth", block: "start" });
  }
  function enterLife() {
    $("#guide").hidden = true;
    $("#life-form").hidden = false;
    $("#life-enter").style.display = "none";
    // 若 5 分钟内填过一半就退出，询问是否继续（避免用户反复填写）
    const draft = readLifeDraft();
    if (draft) {
      showLifeDraftPrompt(draft);
      applyLifeDraft(draft);
    }
    // 直接滚到角色档案问答内容
    $("#life-form").scrollIntoView({ behavior: "smooth", block: "start" });
  }
  $("#guide-enter").addEventListener("click", enterGuide);
  $("#life-enter").addEventListener("click", enterLife);
  // 实时保存草稿，用户中途退出也不丢
  LIFE_FIELD_IDS.forEach((id) => {
    const el = $("#" + id);
    if (el) el.addEventListener("input", saveLifeDraft);
    if (el) el.addEventListener("change", saveLifeDraft);
  });

  // ============ 项目二维码（页脚 · 扫码进入 / 可保存转发）============
  function initSiteQR() {
    const img = $("#site-qr-img");
    const save = $("#site-qr-save");
    if (!img || typeof qrcode !== "function") return;
    try {
      const qr = qrcode(0, "M");
      qr.addData(location.origin + "/");
      qr.make();
      const n = qr.getModuleCount();
      const size = 480, pad = 36;
      const canvas = document.createElement("canvas");
      canvas.width = canvas.height = size + pad * 2;
      const ctx = canvas.getContext("2d");
      ctx.fillStyle = "#FFFFFF";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      const cell = size / n;
      ctx.fillStyle = "#100E0C";
      for (let r = 0; r < n; r++) {
        for (let c = 0; c < n; c++) {
          if (qr.isDark(r, c)) {
            ctx.fillRect(pad + c * cell, pad + r * cell, Math.ceil(cell), Math.ceil(cell));
          }
        }
      }
      const url = canvas.toDataURL("image/png");
      img.src = url;
      if (save) save.href = url;
    } catch (e) {
      console.warn("生成二维码失败", e);
    }
  }

  // ============ 初始化 ============
  (async function init() {
    try {
      handleMpLogin();
      observeReveal(document);
      try {
        await loadGuideThemes();
      } catch (e) {
        console.warn("加载主题失败", e);
        // 主题加载失败不影响其他功能，继续运行
      }
      initSiteQR(); // 页脚项目二维码
      // 首页先展示两个板块入口，用户点击「开始」后进入对应向导
      // 延迟执行访客登录，避免阻塞页面渲染
      setTimeout(() => {
        ensureGuestLogin();
      }, 500);
    } catch (e) {
      console.error("初始化错误", e);
      // 显示友好的错误提示，但不阻止页面使用
      document.body.classList.add("init-error");
      console.log("页面仍可正常使用，部分功能可能受限");
    }
  })();
})();
