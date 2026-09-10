"""可插拔 LLM 层：用于生成个性化推荐理由。

- 若配置 LLM_API_KEY + LLM_BASE_URL，走 LangChain ChatOpenAI（OpenAI 兼容）。
- 否则返回 None，由推荐引擎用「模板化解释」回退（离线可用）。
"""
from __future__ import annotations

from . import lc

_SYSTEM_PROMPT = "你是影视教育与艺术治疗领域的温和顾问。"


def chat(messages: list[dict], temperature: float = 0.7, max_tokens: int = 600) -> str | None:
    """兼容旧签名：通过 LangChain ChatOpenAI 生成文本。失败返回 None。"""
    system = next((m["content"] for m in messages if m.get("role") == "system"), _SYSTEM_PROMPT)
    user = next((m["content"] for m in messages if m.get("role") == "user"), "")
    return lc.llm_generate(system, user)


def explain_recommendation(
    query: str,
    intent_labels: list[str],
    movie_title: str,
    matched_tags: list[str],
    support_audiences: list[str],
    therapy_notes: str,
) -> str | None:
    """生成「为什么推荐这部电影」的个性化解释。返回 None 表示走模板。"""
    prompt = f"""你是一位「影视教育 + 艺术治疗」的资深顾问。请用温暖、真诚、不评判的中文口吻，
写一段 100~150 字的推荐理由，解释为什么这部电影适合眼前这位观众。

观众自述：{query}
识别出的情感/境遇：{', '.join(intent_labels) if intent_labels else '（未明确）'}
影片：《{movie_title}》
与该观众匹配的标签：{', '.join(matched_tags)}
这部影片主要支持的人群：{', '.join(support_audiences)}
观影治疗说明：{therapy_notes}

要求：不要说教、不要贴标签、不要夸大疗效；像一位懂电影也懂人的朋友在说话。
严禁：推荐理由里不要出现「看完后再奖励自己看一部轻松电影」这类自相矛盾的建议——观影后自我照顾应是「观影之外」的事，比如散个步、把感受写下来、找人聊一聊、早点休息。
{_GUAN_DIAN_YING_FA}"""
    return lc.llm_generate(_SYSTEM_PROMPT, prompt)


def template_explanation(
    query: str,
    movie_title: str,
    matched_tags: list[str],
    support_audiences: list[str],
) -> str:
    """离线模板解释（无 LLM 时的回退）。"""
    tags = "、".join(matched_tags[:4]) if matched_tags else "与你此刻的心境"
    audience = "、".join(support_audiences[:3]) if support_audiences else "有相似处境的人"
    return (
        f"推荐《{movie_title}》：它触及了「{tags}」这些主题，"
        f"很多{audience}都从这部片子里获得了共鸣与新的视角。"
        f"你提到「{query[:40]}」，这部电影不急着给答案，而是陪你重新看见自己的处境，"
        f"也许看完你会感到被理解、被接住。建议在安静、不被打扰的时间观看，看完给自己留一点消化情绪的空间。"
    )


def explain_movies_batch(
    query: str,
    intent_labels: list[str],
    movies_info: list[dict],
) -> dict[str, str] | None:
    """一次 LLM 调用为多部影片批量生成推荐理由（避免多次串行/并发调用拖慢响应）。

    movies_info: [{title, matched_tags, support_audiences, therapy_notes}]
    返回 {影片标题: 推荐理由}；失败返回 None（调用方逐个回退单条 LLM / 模板）。
    """
    lines = "\n".join(
        f"{i}. 《{m['title']}》｜匹配标签：{'、'.join(m.get('matched_tags') or []) or '（无）'}｜"
        f"支持人群：{'、'.join(m.get('support_audiences') or []) or '（一般）'}｜"
        f"治疗说明：{(m.get('therapy_notes') or '')[:70]}"
        for i, m in enumerate(movies_info[:5], 1)
    )
    prompt = f"""观众自述：{query}
识别出的情感/境遇：{', '.join(intent_labels) if intent_labels else '（未明确）'}
候选影片（按推荐度从高到低）：
{lines}

请为每一部影片各写一段 60~100 字的推荐理由，说明它为什么适合眼前这位观众。
要求：温暖、真诚、不评判、不说教；像一位懂电影也懂人的朋友在说话；不要夸大疗效；不要出现「希望这对你有帮助」这类 AI 结尾。
{_GUAN_DIAN_YING_FA}

严格输出 JSON（不要多余文字），键用影片完整标题：{{"《片名》": "推荐理由", "《片名2》": "推荐理由2"}}"""
    text = lc.llm_generate(_SYSTEM_PROMPT, prompt, max_tokens=1800)
    if not text:
        return None
    import json
    import re

    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
        out: dict[str, str] = {}
        for k, v in data.items():
            title = str(k).strip().strip("《》").strip()
            if isinstance(v, str) and v.strip():
                out[title] = v.strip()
        return out or None
    except Exception:  # noqa: BLE001
        return None


# —— 角色化解读（5 问引导）——
_HUMAN_TOUCH = (
    "【写作要求：真人感】像一位懂电影也懂人的老朋友当面说话："
    "① 用口语，不用「首先/其次/总之/综上所述」这类书面结构词；"
    "② 可以偶尔停顿、反问，带一点温度，但不要油腻、不要煽情；"
    "③ 说具体的人话，引用他原话里的某个词，让他感到「你真的在听我」；"
    "④ 不堆砌套话、不喊口号、不出现「希望这对你有帮助」这类 AI 结尾；"
    "⑤ 短句为主，像聊天，不像文章。"
)

# 「观电影法」理论与语言：让所有回应都带这套方法论的底色
_GUAN_DIAN_YING_FA = (
    "【「观电影法」理论与语言】请自然融入「观电影法」的理念与措辞，不要生硬堆砌："
    "① 核心观：「借电影观自己」「以影入道」「一部电影，一面心镜」——电影是照见自己的镜子，不是逃离现实；"
    "② 常用词：观照、照见、投射、觉知、内在、观心、渡、和解、松绑、光亮、心灯；"
    "③ 金句：「生命是条长河，最终渡你的还是自己」；"
    "④ 立场：观电影是向内看，不评判、不诊断、不替人下结论，只陪伴与照见。"
)

_ROLE_SYSTEM = {
    "viewer": "你是「影境档案」的观影陪伴者。你温暖、真诚、不评判，像一位懂电影也懂人的朋友，陪伴寻影者用电影照见自己。",
}

_ROLE_FOCUS = {
    "viewer": "写一段 180~260 字的「观影陪伴指引」：先自然带出 2~3 部候选影片各自的推荐理由"
              "（每部一两句，说明为什么适合此刻的他，不要罗列式介绍剧情），"
              "再写他可能会在哪里被触动、看完可以做点什么来照顾自己。"
              "像朋友一样说话，不贴标签、不夸大疗效。",
}


def guided_interpretation(
    role: str,
    answers: dict[str, str],
    movies: list[dict],
    memory: str = "",
) -> str | None:
    """基于 5 问答案生成角色化解读。movies 为候选影片信息（含真实简介，避免编造剧情）。

    返回 None 表示走模板。
    """
    if role not in _ROLE_SYSTEM:
        role = "viewer"
    answered = "、".join(f"{k}:{v}" for k, v in answers.items() if v) or "（未填写）"

    movie_block = "\n".join(
        f"- 《{m.get('title', '')}》｜简介：{(m.get('synopsis') or '')[:100]}｜治疗要点：{(m.get('therapy_notes') or '')[:80]}"
        for m in (movies or [])[:3]
    ) or "（暂无）"

    memory_block = f"\n\n【这位用户的过往记忆】\n{memory}" if memory else ""

    prompt = f"""请基于以下 5 问答案，为这位寻影者提供回应。

5 问答案（需求/目标/想法/对象/主题）：
{answered}

系统匹配到的候选影片（含真实简介，请严格依据简介描述剧情，不要编造情节）：
{movie_block}
{memory_block}

{_ROLE_FOCUS[role]}

{_GUAN_DIAN_YING_FA}"""

    prompt += f"\n\n{_HUMAN_TOUCH}"
    return lc.llm_generate(_ROLE_SYSTEM[role], prompt, max_tokens=700)


def template_guided_interpretation(
    role: str,
    answers: dict[str, str],
    movie_titles: list[str],
) -> str:
    """离线角色化解读（无 LLM 时的回退）。"""
    titles = "、".join(movie_titles[:3]) if movie_titles else "（暂无匹配）"
    emotion = answers.get("emotion") or "此刻"
    situation = answers.get("situation") or "当下"
    return (
        f"【寻影者 · 观影陪伴】此刻的「{emotion}」与「{situation}」，为你挑选了：{titles}。"
        f"建议在安静不被打扰的时候观看，不必急着「看懂」，允许自己被某个画面、某句台词轻轻接住；"
        f"看完给自己留一点时间，把涌上来的感受写下来。"
    )


# —— 「观电影法」笔记的深度专属回应 ——
def respond_to_note(
    role: str,
    content: dict,
    movie_title: str,
    memory: str = "",
) -> str | None:
    """针对用户的观影笔记，生成深度专属回应。返回 None 表示走模板。"""
    if role not in _ROLE_SYSTEM:
        role = "viewer"
    fields = "\n".join(f"- {k}: {v}" for k, v in content.items() if v) or "（空白）"

    focus = (
        "请以温暖、真诚、不评判的口吻，回应这位寻影者的观影笔记。"
        "① 先接住他最触动的那一点，帮他看见这份触动背后可能照见的内在；"
        "② 围绕他记下的台词与思考，给 2~3 句延展，像朋友一样陪他多走一步；"
        "③ 最后给一个小小的、可操作的观影后自我照顾建议。共 150~220 字，不要说教、不贴标签。"
    )

    memory_block = f"\n\n【这位用户的过往笔记】\n{memory}" if memory else ""

    prompt = f"""影片：《{movie_title or '（未指定）'}》
笔记内容：
{fields}
{memory_block}

{focus}

{_GUAN_DIAN_YING_FA}

{_HUMAN_TOUCH}"""
    return lc.llm_generate(_ROLE_SYSTEM[role], prompt)


def template_note_response(role: str, content: dict, movie_title: str) -> str:
    """离线笔记回应（无 LLM 时的回退）。"""
    title = movie_title or "这部影片"
    touched = content.get("touched_scene") or content.get("内心触动的片段") or "那个让你心动的片段"
    quote = content.get("favorite_quote") or content.get("喜欢的台词") or ""
    q = f"那句「{quote}」也值得被反复咀嚼。" if quote else ""
    return (
        f"【寻影者 · 观影回应】谢谢你记下《{title}》里「{touched[:30]}」。"
        f"能被触动的，往往正是我们心里本就有的东西。{q}"
        f"不必急着下结论，允许这份感受再停留一会儿，它会在合适的时候给你答案。"
    )


def personalize_movie(movie: dict, answers: dict) -> dict | None:
    """根据用户 5 问答案，生成亲切的「这部影片如何支持你」+「观影观己」讨论问题。

    返回 {"support": str, "questions": [str]}；失败返回 None（前端回退通用内容）。
    """
    prompt = f"""用户填写的五个问题（这是他的真实处境，务必紧扣；他没提到的内容不要硬扯）：
- 此刻的心情/需求：{answers.get('emotion') or '未填'}
- 正处的境遇：{answers.get('situation') or '未填'}
- 渴望获得：{answers.get('value') or '未填'}
- 角色/身份：{answers.get('audience') or '未填'}
- 想看的主题：{answers.get('theme') or '未填'}

影片《{movie.get('title', '')}》简介：{(movie.get('synopsis') or '')[:150]}
治疗要点：{(movie.get('therapy_notes') or '')[:100]}

请像一位懂电影也懂你的老朋友，亲切地写两段（总约 260 字）：
第一段「支持」：这部影片如何支持「此刻的你」——紧扣他上面填的心情/境遇/渴望；他只提到孩子才提孩子，没说就不提；不说道理，像朋友聊天。
第二段「问题」：给 3 个「观影观己」的讨论问题，围绕「影片中哪些片段触动到了你」「这些桥段和你的生活有哪些类似」展开，并自然融入他的回答。

严格输出 JSON（不要多余文字）：{{"support": "…", "questions": ["…", "…", "…"]}}"""
    text = lc.llm_generate(_ROLE_SYSTEM["viewer"], prompt, max_tokens=700)
    if not text:
        return None
    import json
    import re

    # 优先解析 JSON
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(0))
            support = str(data.get("support", "")).strip()
            questions = [str(q).strip() for q in data.get("questions", []) if str(q).strip()]
            if support or questions:
                return {"support": support, "questions": questions[:4]}
        except Exception:  # noqa: BLE001
            pass
    return None


# —— 「你的人生电影」：像看电影一样看自己的人生 ——
_LIFE_SYSTEM = (
    "你是「影境档案」的人生电影放映员。你温和、笃定、有诗意，"
    "像一位坐在放映厅里陪他看「他自己这部人生电影」的老朋友，"
    "看见他、鼓励他、欣赏他，但不评判、不诊断、不替他下结论。"
)


def life_movie(profile: dict) -> dict | None:
    """角色档案 · 你的人生电影：根据角色名 / 电影名 / 出生故事 / 转折故事 / 2026 故事，生成一部人生电影。
    返回 {"title": 片名, "genre": 类型, "tagline": 海报文案, "review": 影评式看见}；失败返回 None。
    """
    role_name = profile.get("role_name") or "你"
    movie_name = profile.get("movie_name") or "（未起名）"
    born_story = profile.get("born_story") or "（未写）"
    turning_story = profile.get("turning_story") or "（未写）"
    story_2026 = profile.get("story_2026") or "（未写）"

    prompt = f"""眼前这个人，把自己看成一部正在上映的人生电影，建立了一份「角色档案」。请像观电影法说的「借电影观自己」那样，陪他把自己的来处、转折与正在经历的故事，串成一部完整而温暖的人生电影。

他的角色档案：
- 角色名：{role_name}
- 他给自己的人生电影起的名字：{movie_name}
- 出生故事（0-6 岁）：{born_story}
- 转折（重要）故事：{turning_story}
- 正在经历的故事（2026）：{story_2026}

请为他写 4 段（总约 420 字，温暖、真诚、不油腻不煽情、不说教、不贴标签）：
1. 片名：为「他的人生电影」定一个贴切的片名（中文，8 字以内；若他起的名字很好，可以沿用或略作升华）。
2. 类型：用 1~2 个词描述他人生故事的气质（如：成长/公路/家庭/治愈/传记…）。
3. 海报文案：一句 15~25 字的海报标语，像电影海报上的那句话，看见并欣赏他。
4. 影评：像写影评一样回看他的人生——把他的出生故事、转折故事与 2026 正在经历的故事串成一条线，把「角色 / 观者 / 导演 / 编剧」这几种眼光自然揉进去（他作为人生主角的表演、台下观者的回望、导演对这场戏的调度、编剧早埋下的伏笔……），灵活运用、点到即止，不要每段都套刻板句式；多依据他写下的具体事实去看见、鼓励、欣赏他，并望向他正在经历的 2026，鼓励他出演自己想要的剧情。是欣赏与鼓励，不是说教。

{_HUMAN_TOUCH}

严格输出 JSON（不要多余文字）：
{{"title": "…", "genre": "…", "tagline": "…", "review": "…"}}"""
    text = lc.llm_generate(_LIFE_SYSTEM, prompt, max_tokens=1100)
    if not text:
        return None
    import json
    import re

    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(0))
            out = {
                "title": str(data.get("title", "")).strip() or (movie_name or f"{role_name}的人生电影"),
                "genre": str(data.get("genre", "")).strip() or "人生电影",
                "tagline": str(data.get("tagline", "")).strip(),
                "review": str(data.get("review", "")).strip(),
            }
            if out["tagline"] or out["review"]:
                return out
        except Exception:  # noqa: BLE001
            pass
    return None


def life_daily(story: str, name: str = "") -> dict | None:
    """针对用户当天经历的一段「剧情」，用电影视角复盘回应。
    返回 {"title": 今日片名, "review": 影评式回应}；失败返回 None。
    """
    name_block = f"他叫{name}。" if name else ""
    prompt = f"""{name_block}他刚把今天生活里发生的一段「剧情」写了下来：

「{story}」

请你像一位懂他人生这部电影的老朋友，把今天这段经历当成他「人生电影」里的一幕，给他一段 150~220 字的回应：
- 先看见：用一两句点出这段「剧情」里他真实的心情或选择（不评判）；
- 再欣赏：欣赏他在这幕里的一个闪光处（哪怕很小）；
- 后回味：把这段剧情放进他人生的长镜头里，给他一句温柔又有力的鼓励。
不要说教、不贴标签、不出现「希望对你有帮助」。

{_HUMAN_TOUCH}

严格输出 JSON（不要多余文字）：{{"title": "为这一幕起个片名（10字内）", "review": "…"}}"""
    text = lc.llm_generate(_LIFE_SYSTEM, prompt, max_tokens=600)
    if not text:
        return None
    import json
    import re

    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(0))
            out = {
                "title": str(data.get("title", "")).strip() or "今日这一幕",
                "review": str(data.get("review", "")).strip(),
            }
            if out["review"]:
                return out
        except Exception:  # noqa: BLE001
            pass
    return None


def recommend_top3(answers: dict) -> list[dict] | None:
    """LLM 直接根据用户 5 问答案，从海量电影中推荐最合适的 3 部（不限影片库）。

    返回 [{title, year, director, genre, synopsis, reason}...]；失败返回 None。
    """
    prompt = f"""请根据这位观众的真实情况，从你了解的所有电影里，为他挑选 3 部最适合他现在看的电影。

他的 5 个回答：
- 此刻的心情/需求：{answers.get('emotion') or '未填'}
- 正处的境遇：{answers.get('situation') or '未填'}
- 渴望获得：{answers.get('value') or '未填'}
- 专业/职业（现实身份）：{answers.get('audience') or '未填'}
- 想看的主题：{answers.get('theme') or '未填'}

要求：
1. 3 部电影，按契合度从高到低；可以是任何国家、任何年代的经典或当代电影，不要只挑大众爆款，要真的贴合他此刻的处境与心情。
2. 每部给：片名（中文）、年份、导演、国家、类型（2~3 个词）、豆瓣评分（尽量准确，1~10 的一位小数，若不确定就给一个合理区间值）、一句话简介（真实剧情，不编造）、以及一段 60~90 字的推荐理由——推荐理由必须紧扣他上面填的具体情况（他的心情、境遇、职业、渴望），让他感到「这真的懂我」。
3. 语气像一位懂电影也懂人的老朋友，不说教、不贴标签、不夸大疗效。

严格输出 JSON（不要多余文字）：
{{"movies": [{{"title":"…","year":"…","director":"…","country":"…","genre":"…","rating":"…","synopsis":"…","reason":"…"}}]}}"""
    text = lc.llm_generate(_ROLE_SYSTEM["viewer"], prompt, max_tokens=1200)
    if not text:
        return None
    import json
    import re

    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
        movies = data.get("movies") or []
        out = []
        for mv in movies:
            if not isinstance(mv, dict):
                continue
            title = str(mv.get("title", "")).strip()
            if not title:
                continue
            out.append(
                {
                    "title": title,
                    "year": str(mv.get("year", "")).strip(),
                    "director": str(mv.get("director", "")).strip(),
                    "country": str(mv.get("country", "")).strip(),
                    "genre": str(mv.get("genre", "")).strip(),
                    "rating": str(mv.get("rating", "")).strip(),
                    "synopsis": str(mv.get("synopsis", "")).strip(),
                    "reason": str(mv.get("reason", "")).strip(),
                }
            )
        return out[:3] or None
    except Exception:  # noqa: BLE001
        return None
