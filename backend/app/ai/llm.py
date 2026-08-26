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
严禁：推荐理由里不要出现「看完后再奖励自己看一部轻松电影」这类自相矛盾的建议——观影后自我照顾应是「观影之外」的事，比如散个步、把感受写下来、找人聊一聊、早点休息。"""
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


# —— 角色化解读（5 问引导）——
_HUMAN_TOUCH = (
    "【写作要求：真人感】像一位懂电影也懂人的老朋友当面说话："
    "① 用口语，不用「首先/其次/总之/综上所述」这类书面结构词；"
    "② 可以偶尔停顿、反问，带一点温度，但不要油腻、不要煽情；"
    "③ 说具体的人话，引用他原话里的某个词，让他感到「你真的在听我」；"
    "④ 不堆砌套话、不喊口号、不出现「希望这对你有帮助」这类 AI 结尾；"
    "⑤ 短句为主，像聊天，不像文章。"
)

_ROLE_SYSTEM = {
    "viewer": "你是「影境档案」的观影陪伴者。你温暖、真诚、不评判，像一位懂电影也懂人的朋友，陪伴寻影者用电影照见自己。",
    "facilitator": "你是「影境档案」的影视心理分析师/影领家督导。你面对的是专业的带领者，"
                  "输出的是「如何带领这场观影」的完整方案——不是给带领者本人做情绪抚慰，而是教他怎么带别人。",
}

_ROLE_FOCUS = {
    "viewer": "写一段 120~180 字的「观影陪伴指引」：这部片子如何呼应他的心情与处境，"
              "他可能会在哪里被触动，看完可以做点什么来照顾自己。像朋友一样说话，不贴标签、不夸大疗效。",
    "facilitator": (
        "请输出一套**可直接照做的完整带领方案**，用 Markdown 分块，包含以下 7 个板块：\n"
        "一、选片建议：首选 1 部 + 备选 2 部，各用一句话说明为什么贴合服务对象的需求与目标。\n"
        "二、带领角度：这次观影最该抓住的 1 个核心切入角度（结合需求/目标，一句话点透）。\n"
        "三、观影方式建议：明确建议「全片」还是「片段」；若建议片段，列出 2~3 个关键片段（大概位置 + 这段用来展现/引发什么）。\n"
        "四、带领流程 SOP：按「破冰 → 观影 → 讨论引导 → 收尾」四步，给出每一步的时长、具体动作和一句话术示例。\n"
        "五、讨论问题：给出 3~5 个可以直接抛给成员的讨论问题。\n"
        "六、触发风险与伦理提醒：指出这部电影可能触及的敏感点，以及带领时的分寸（不越界、不诊断、不替成员下结论）。\n"
        "七、PPT 大纲：给一个 8 页左右的 PPT 骨架（每页标题 + 该页放什么 + 建议的视觉调性），调性贴合这部电影的气质。\n"
        "要求：专业、克制、可落地、直接照做；用「一、二、三…」分块，简洁要点式表达，不写空话、不出现「希望对你有帮助」。"
    ),
}


def guided_interpretation(
    role: str,
    answers: dict[str, str],
    movies: list[dict],
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

    prompt = f"""请基于以下 5 问答案，为这位{'寻影者' if role == 'viewer' else '影领家'}提供回应。

5 问答案（需求/目标/想法/对象/主题）：
{answered}

系统匹配到的候选影片（含真实简介，请严格依据简介描述剧情，不要编造情节）：
{movie_block}

{_ROLE_FOCUS[role]}"""

    if role == "facilitator":
        prompt += "\n\n（注意：你是在给专业的影领家写「带领方案」，不是安慰他本人；影片细节必须以上面简介为准。）"
        return lc.llm_generate(_ROLE_SYSTEM[role], prompt, max_tokens=2000)

    prompt += f"\n\n{_HUMAN_TOUCH}"
    return lc.llm_generate(_ROLE_SYSTEM[role], prompt)


def template_guided_interpretation(
    role: str,
    answers: dict[str, str],
    movie_titles: list[str],
) -> str:
    """离线角色化解读（无 LLM 时的回退）。"""
    titles = "、".join(movie_titles[:3]) if movie_titles else "（暂无匹配）"
    emotion = answers.get("emotion") or "此刻"
    situation = answers.get("situation") or "当下"
    if role == "facilitator":
        return (
            f"【影领家 · 带领建议】围绕「{emotion} + {situation}」这个案例，为你匹配了：{titles}。"
            f"建议从情绪最贴近的一部先看，观影后引导大家分享「哪个瞬间最触动你」，"
            f"并留意影片触发预警，为情绪敏感的成员预留支持空间。"
        )
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
) -> str | None:
    """针对用户的观影笔记/复盘笔记，生成深度专属回应。返回 None 表示走模板。"""
    if role not in _ROLE_SYSTEM:
        role = "viewer"
    fields = "\n".join(f"- {k}: {v}" for k, v in content.items() if v) or "（空白）"

    if role == "viewer":
        focus = (
            "请以温暖、真诚、不评判的口吻，回应这位寻影者的观影笔记。"
            "① 先接住他最触动的那一点，帮他看见这份触动背后可能照见的内在；"
            "② 围绕他记下的台词与思考，给 2~3 句延展，像朋友一样陪他多走一步；"
            "③ 最后给一个小小的、可操作的观影后自我照顾建议。共 150~220 字，不要说教、不贴标签。"
        )
    else:
        focus = (
            "请以资深影领家督导的口吻，回应这份带电影复盘笔记。"
            "① 肯定其中做得好的体验环节，点出它为什么有效；"
            "② 针对「是否达成预期」和「带领收获」，给 2~3 条可落地的精进建议（如提问技巧、环节节奏、道具运用）；"
            "③ 结合他的分享意愿，鼓励沉淀可复用的带领经验。共 150~220 字，专业、克制、可执行。"
        )

    prompt = f"""影片：《{movie_title or '（未指定）'}》
角色：{'寻影者' if role == 'viewer' else '影领家'}
笔记内容：
{fields}

{focus}

{_HUMAN_TOUCH}"""
    return lc.llm_generate(_ROLE_SYSTEM[role], prompt)


def template_note_response(role: str, content: dict, movie_title: str) -> str:
    """离线笔记回应（无 LLM 时的回退）。"""
    title = movie_title or "这部影片"
    if role == "facilitator":
        gains = content.get("gains") or content.get("收获") or "带领过程"
        return (
            f"【影领家 · 复盘回应】感谢你记录这次《{title}》的带领复盘。"
            f"关于「{gains[:30]}」的收获，值得被沉淀下来——建议下次把最有效的那个体验环节固定成流程，"
            f"并留意成员的反馈节奏，持续打磨破冰与收尾的设计。每一次复盘，都在让你成为更稳的带领者。"
        )
    touched = content.get("touched_scene") or content.get("内心触动的片段") or "那个让你心动的片段"
    quote = content.get("favorite_quote") or content.get("喜欢的台词") or ""
    q = f"那句「{quote}」也值得被反复咀嚼。" if quote else ""
    return (
        f"【寻影者 · 观影回应】谢谢你记下《{title}》里「{touched[:30]}」。"
        f"能被触动的，往往正是我们心里本就有的东西。{q}"
        f"不必急着下结论，允许这份感受再停留一会儿，它会在合适的时候给你答案。"
    )
