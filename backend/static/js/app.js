/* 影境档案 · 前端交互 */
(() => {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  const API = "/api/v1";
  let lastSearchLogId = null;

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

  async function sendFeedback(payload) {
    try {
      await api("/feedback", { method: "POST", body: { search_log_id: lastSearchLogId, ...payload } });
    } catch (e) {
      console.warn("反馈失败", e);
    }
  }

  // ============ 详情弹层 ============
  const modal = $("#movie-modal");
  const modalBody = $("#modal-body");

  async function openMovieById(id) {
    const full = await api(`/movies/${id}`);
    openMovie(full);
  }

  function openMovie(m) {
    const tags = (m.tags || []).map((t) => `<span class="chip chip--muted">${esc(t.name)}</span>`).join("");
    const da = m.deep_analysis || {};
    const warnings = (m.trigger_warnings || []).length
      ? `<div class="warning">${(m.trigger_warnings || []).map(esc).join("<br>")}</div>`
      : "";
    const questions = (m.discussion_questions || []).length
      ? `<ul>${(m.discussion_questions || []).map((q) => `<li>${esc(q)}</li>`).join("")}</ul>`
      : "";

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

      <div class="detail-section">
        <h4>这部影片如何支持你</h4>
        <div class="tag-row">${(m.support_types || []).map((s) => `<span class="tag-pill">${esc(s)}</span>`).join("")}</div>
        <p><strong style="color:var(--ink)">适合人群：</strong>${esc((m.support_audiences || []).join("、"))}</p>
        <p>${esc(m.therapy_notes || "")}</p>
      </div>

      ${questions ? `<div class="detail-section"><h4>观影后的讨论问题</h4>${questions}</div>` : ""}
      ${warnings ? `<div class="detail-section"><h4>观看提醒</h4>${warnings}</div>` : ""}

      <div class="detail-section">
        <h4>相关标签</h4>
        <div class="tag-row">${tags || '<span style="color:var(--ink-3);font-size:13px">暂无标签</span>'}</div>
      </div>

      <div class="detail-section" style="border-top:1px solid var(--hairline-soft);padding-top:22px">
        <h4>这部片子，帮到你了吗？</h4>
        <div class="card-actions" style="margin-top:10px">
          <button class="mini-btn" data-act="helpful">👍 帮到我了</button>
          <button class="mini-btn" data-act="not-helpful">👎 没帮到</button>
        </div>
        <div class="ask-box" style="margin:16px 0 0;max-width:none;padding:6px 6px 6px 18px">
          <input class="ask-box__input" id="tag-suggest" style="font-size:14px" placeholder="建议一个标签，比如：婆媳矛盾" />
          <button class="ask-box__submit" id="tag-submit" style="padding:10px 20px;font-size:14px">提交标签</button>
        </div>
        <p id="feedback-hint" style="font-size:12.5px;color:var(--ink-3);margin:8px 2px 0"></p>
      </div>

      <div class="detail-section" style="border-top:1px solid var(--hairline-soft);padding-top:22px">
        <h4>分享 · 观影感悟卡</h4>
        <input id="share-note" placeholder="写一句你的感悟（可留空）" style="width:100%;margin:6px 0 12px;padding:10px;border-radius:10px;border:1px solid var(--hairline-soft);background:var(--surface);color:var(--ink)" />
        <button class="ask-box__submit" id="share-gen"><span>生成卡片 · 长按保存</span></button>
        <div id="share-result" style="margin-top:14px"></div>
      </div>`;

    $$("[data-act]", modalBody).forEach((btn) =>
      btn.addEventListener("click", async () => {
        const helpful = btn.dataset.act === "helpful";
        await sendFeedback({ movie_id: m.id, helpful });
        btn.classList.add("is-on");
        btn.textContent = helpful ? "✓ 已记录" : "✓ 已记录";
        $("#feedback-hint").textContent = "感谢反馈，已记录，将帮助档案馆更懂你。";
      })
    );
    $("#tag-submit").addEventListener("click", async () => {
      const val = $("#tag-suggest").value.trim();
      if (!val) return;
      const res = await api("/feedback", {
        method: "POST",
        body: { movie_id: m.id, suggested_tag: val },
      });
      $("#feedback-hint").textContent = res.message;
      $("#tag-suggest").value = "";
    });

    // —— 分享卡片 ——
    const BOOK_QUOTES = ["生命是条长河，最终渡你的还是自己"];
    $("#share-gen").addEventListener("click", () => {
      const note = $("#share-note").value.trim();
      const quote = BOOK_QUOTES[Math.floor(Math.random() * BOOK_QUOTES.length)];
      const da = m.deep_analysis || {};
      $("#share-result").innerHTML = `
        <div class="share-card" style="background:${gradientFor(m.title)}">
          <span class="share-card__brand">影境档案 · 观电影法</span>
          <h3 class="share-card__movie">《${esc(m.title)}》</h3>
          <p class="share-card__quote">「${esc(quote)}」</p>
          ${note ? `<p class="share-card__note">—— ${esc(note)}</p>` : ""}
          <span class="share-card__theme">${esc(da.theme || "借电影，观自己")}</span>
        </div>`;
    });

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
          `<div class="badge ${b.earned ? "is-earned" : ""}"><span class="badge__icon">${b.earned ? "✦" : "·"}</span><span class="badge__name">${esc(b.name)}</span><span class="badge__desc">${esc(b.desc)}</span></div>`
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
          <h4>我的印记</h4>
          <div class="badges">${badges}</div>
        </div>
        <div class="growth-section">
          <h4>城市坐标 · 寻找同城影友</h4>
          <div style="display:flex;gap:8px">
            <input id="city-input" value="${esc(p.city)}" placeholder="填写城市，寻找同城影友" style="flex:1;border:1px solid var(--hairline-soft);border-radius:999px;padding:10px 16px;background:var(--surface);color:var(--ink)" />
            <button class="mini-btn" id="city-save">保存</button>
          </div>
        </div>
        <div class="growth-section" id="match-section">
          <h4>同频影友</h4>
          <p style="font-size:13px;color:var(--ink-3)">加载中…</p>
        </div>
        <div class="growth-section">
          <h4>「观电影法」笔记</h4>
          <div class="note-role" id="note-role" style="display:flex;gap:8px;margin-bottom:12px">
            <button class="mini-btn is-on" data-nrole="viewer">寻影者 · 观影笔记</button>
            <button class="mini-btn" data-nrole="facilitator">影领家 · 复盘笔记</button>
          </div>
          <input id="note-movie" placeholder="哪部电影（可留空，自己填写）" style="width:100%;margin-bottom:12px;padding:10px;border-radius:10px;border:1px solid var(--hairline-soft);background:var(--surface);color:var(--ink)" />
          <div id="note-fields"></div>
          <div style="margin-top:12px">
            <button class="ask-box__submit" id="note-submit"><span>提交笔记 · 获得专属回应</span></button>
          </div>
          <div id="note-result" class="interpretation" style="margin-top:12px;display:none"></div>
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
      $("#city-save").addEventListener("click", async () => {
        const city = $("#city-input").value.trim();
        if (city) {
          await api("/me/city", { method: "PATCH", body: { city } });
          $("#checkin-msg").textContent = "城市已更新：定位到「" + city + "」的同频影友";
          setTimeout(openGrowth, 400);
        }
      });

      // 同频影友
      try {
        const m = await api("/match");
        let html = "";
        if (m.city) {
          html += `<p style="font-size:13px;color:var(--ink-2);margin:0">📍 在「${esc(m.city)}」，有 ${m.same_city_count} 位同城影友。</p>`;
        } else {
          html += `<p style="font-size:13px;color:var(--ink-3);margin:0">填上城市，就能找到同城影友。</p>`;
        }
        $("#match-section").innerHTML = `<h4>同频影友</h4>${html}`;
      } catch (e) {
        $("#match-section").innerHTML = `<h4>同频影友</h4><p style="font-size:13px;color:var(--ink-3)">暂时无法加载</p>`;
      }

      // 「观电影法」笔记
      const NOTE_FIELDS = {
        viewer: [
          { key: "内心触动的片段", ph: "哪个画面、哪段情节，最触动你？" },
          { key: "喜欢的台词", ph: "有没有哪句台词，你想记下来？" },
          { key: "电影带来的思考", ph: "这部电影让你想到了什么？内心的想法？" },
        ],
        facilitator: [
          { key: "是否达成预期", ph: "对照开场前设的目标，整场观影会完成得如何？" },
          { key: "带领收获", ph: "这次带领，你有哪些成长或新发现？" },
          { key: "体验环节", ph: "从破冰→观影→引导→结尾，用了哪些技能或道具？哪个效果好？" },
          { key: "PPT精彩处", ph: "带领PPT最打动人的部分是什么？" },
          { key: "是否愿意分享PPT", ph: "愿意分享给他人吗（他人喜欢可打赏）？", select: ["愿意分享（可被打赏）", "暂不分享"] },
        ],
      };
      let noteRole = "viewer";
      // 拉取影片列表（用于按名称匹配 movie_id）
      let allMovies = [];
      try {
        allMovies = await api("/movies?limit=100");
      } catch (e) {}

      function renderNoteFields() {
        $("#note-fields").innerHTML = NOTE_FIELDS[noteRole]
          .map((f) => {
            if (f.select) {
              return `<div style="margin-bottom:12px"><label style="font-size:13px;color:var(--ink-2)">${esc(f.key)}</label>
                <select class="note-input" data-key="${esc(f.key)}" style="width:100%;margin-top:6px;padding:10px;border-radius:10px;border:1px solid var(--hairline-soft);background:var(--surface);color:var(--ink)">
                  ${f.select.map((o) => `<option>${esc(o)}</option>`).join("")}
                </select></div>`;
            }
            return `<div style="margin-bottom:12px"><label style="font-size:13px;color:var(--ink-2)">${esc(f.key)}</label>
              <textarea class="note-input" data-key="${esc(f.key)}" rows="2" placeholder="${esc(f.ph)}" style="width:100%;margin-top:6px;padding:10px;border-radius:10px;border:1px solid var(--hairline-soft);background:var(--surface);color:var(--ink);font-family:var(--font-sans);font-size:14px;resize:vertical"></textarea></div>`;
          })
          .join("");
      }
      $$("#note-role button").forEach((b) =>
        b.addEventListener("click", () => {
          noteRole = b.dataset.nrole;
          $$("#note-role button").forEach((x) => x.classList.toggle("is-on", x === b));
          renderNoteFields();
        })
      );
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
        btn.classList.add("is-loading");
        btn.querySelector("span").textContent = "正在回应…";
        try {
          const movieName = $("#note-movie").value.trim();
          let movieId = null;
          if (movieName) {
            const hit = allMovies.find((mv) => mv.title === movieName || mv.title.includes(movieName) || movieName.includes(mv.title));
            if (hit) movieId = hit.id;
            else content["电影"] = movieName; // 没匹配到库内影片，就存进笔记内容
          }
          const res = await api("/notes", { method: "POST", body: { role: noteRole, movie_id: movieId, content } });
          $("#note-result").style.display = "block";
          $("#note-result").textContent = res.llm_response;
          loadMyNotes();
        } catch (e) {
          $("#note-result").style.display = "block";
          $("#note-result").textContent = "提交失败：" + e.message;
        } finally {
          btn.classList.remove("is-loading");
          btn.querySelector("span").textContent = "提交笔记 · 获得专属回应";
        }
      });

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
              <p class="note-item__meta">${n.role === "facilitator" ? "影领家 · 复盘" : "寻影者 · 观影"} · ${esc((n.content && Object.values(n.content).filter(Boolean).join(" / ")) || "")}</p>
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

  // ============ 双角色 · 5问引导 ============
  const GUIDE_CONFIG = {
    viewer: [
      { key: "emotion", q: "此刻的你，心情如何？（可多选）", type: "tags" },
      { key: "situation", q: "你正处在什么样的境遇里？（可多选）", type: "tags" },
      { key: "value", q: "你渴望从电影里获得什么？（可多选）", type: "tags" },
      { key: "audience", q: "你现在的角色是？（自己填写）", type: "free" },
      { key: "theme", q: "你想看什么主题？（可多选或自己填写）", type: "tags+free" },
    ],
    facilitator: [
      { key: "emotion", q: "服务对象的需求是什么？", type: "free", ph: "描述服务对象的需求，如：想缓解焦虑、找回自信、走出低谷…" },
      { key: "situation", q: "服务对象想达成的目标是什么？", type: "free", ph: "描述想达成的目标，如：希望成员之间更信任、更愿意表达…" },
      { key: "value", q: "这次活动你的想法是什么？", type: "free", ph: "你打算怎么带这场活动？想用电影引发什么？" },
      { key: "audience", q: "服务对象是谁？", type: "free", ph: "描述服务对象，如：30+ 职场妈妈、青春期学生、丧亲者…" },
      { key: "theme", q: "想带大家走哪个主题方向？", type: "free", ph: "如：亲子关系、成长、丧失与哀伤、自我认同…" },
    ],
  };

  let guideRole = null;
  let guideStep = 0;
  let guideSelections = {}; // {key: [tag...]}
  let guideFree = {}; // {key: 自由填写文本}
  let guideThemes = {};

  async function loadGuideThemes() {
    guideThemes = await api("/themes");
  }

  function startGuide(role) {
    guideRole = role;
    guideStep = 0;
    guideSelections = {};
    guideFree = {};
    $("#role-select").hidden = true;
    $("#wizard").hidden = false;
    renderGuideStep();
  }

  function backToRoleSelect() {
    $("#wizard").hidden = true;
    $("#role-select").hidden = false;
    guideRole = null;
    guideSelections = {};
    guideFree = {};
  }

  function renderGuideStep() {
    const steps = GUIDE_CONFIG[guideRole];
    const step = steps[guideStep];
    $("#wizard-step").textContent = `第 ${guideStep + 1} / ${steps.length} 问`;
    $("#wizard-progress").style.width = `${((guideStep + 1) / steps.length) * 100}%`;
    $("#wizard-question").textContent = step.q;

    let html = "";
    if (step.type !== "free") {
      const tags = guideThemes[step.key] || [];
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
    for (const step of GUIDE_CONFIG[guideRole]) {
      const sel = (guideSelections[step.key] || []).join(" ");
      const free = (guideFree[step.key] || "").trim();
      answers[step.key] = [sel, free].filter(Boolean).join(" ");
    }
    return answers;
  }

  async function submitGuide() {
    const submit = $("#wizard-next");
    submit.classList.add("is-loading");
    try {
      const data = await api("/recommend/guided", {
        method: "POST",
        body: { role: guideRole, answers: buildGuideAnswers() },
      });
      lastSearchLogId = data.search_log_id;
      renderGuidedResults(data);
    } catch (e) {
      alert("推荐失败：" + e.message);
    } finally {
      submit.classList.remove("is-loading");
    }
  }

  let lastGuidedItems = [];
  let lastGuidedRole = "viewer";

  function renderGuidedResults(data) {
    resultsSection.hidden = false;
    lastGuidedItems = data.items;
    lastGuidedRole = data.role;
    $("#echo-query").textContent =
      data.role === "facilitator" ? "影领家 · 五问选片" : "寻影者 · 五问选片";
    $("#intent-tags").innerHTML = (data.intent_labels || [])
      .map((t) => `<span class="chip chip--gold">${esc(t)}</span>`)
      .join("");
    $("#results-note").textContent = "";
    const grid = $("#results-grid");
    const max = Math.max(...data.items.map((i) => i.score), 0.0001);
    const interp = data.interpretation
      ? `<div class="interpretation">${esc(data.interpretation)}</div>`
      : "";
    const pptBtn =
      data.role === "facilitator"
        ? `<div style="margin:14px 0"><button class="ask-box__submit" id="export-ppt"><span>⬇ 导出带领方案 PPT</span></button></div>`
        : "";
    grid.innerHTML = interp + pptBtn + data.items.map((item) => cardHTML(item, max)).join("");
    bindCards(grid);
    const eb = $("#export-ppt");
    if (eb) eb.addEventListener("click", exportPpt);
    resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
    observeReveal(grid);
  }

  async function exportPpt() {
    const movies = lastGuidedItems.map((it) => ({
      title: it.movie.title,
      synopsis: it.movie.synopsis,
      therapy_notes: it.movie.therapy_notes,
      trigger_warnings: it.movie.trigger_warnings,
      discussion_questions: it.movie.discussion_questions,
    }));
    const headers = { "Content-Type": "application/json" };
    const token = getToken();
    if (token) headers["Authorization"] = "Bearer " + token;
    try {
      const res = await fetch(API + "/export/ppt", {
        method: "POST",
        headers,
        body: JSON.stringify({ answers: buildGuideAnswers(), movies }),
      });
      if (!res.ok) throw new Error("导出失败");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "观电影法带领方案.pptx";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert("导出 PPT 失败：" + e.message);
    }
  }

  $$(".role-card").forEach((c) =>
    c.addEventListener("click", () => startGuide(c.dataset.role))
  );
  $("#wizard-next").addEventListener("click", () => {
    const steps = GUIDE_CONFIG[guideRole];
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
  $("#wizard-switch").addEventListener("click", backToRoleSelect);

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
  $("#login-btn").addEventListener("click", openLogin);
  loginModal.addEventListener("click", (e) => {
    if (e.target.closest("[data-close]")) {
      loginModal.hidden = true;
      document.body.style.overflow = "";
    }
  });

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
      // 延迟执行访客登录，避免阻塞页面渲染
      setTimeout(() => {
        ensureGuestLogin();
      }, 500);
      if (getToken()) $("#login-btn").textContent = "已登录 ✓";
    } catch (e) {
      console.error("初始化错误", e);
      // 显示友好的错误提示，但不阻止页面使用
      document.body.classList.add("init-error");
      console.log("页面仍可正常使用，部分功能可能受限");
    }
  })();
})();
