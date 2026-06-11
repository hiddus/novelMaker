import json
import time
from datetime import UTC, datetime
from urllib.parse import urljoin
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import get_settings
from app.schemas.domain import (
    ChapterDraft,
    ChapterPlan,
    ContextPack,
    Project,
    ReviewReport,
    RewriteChapterRequest,
    WriteChapterRequest,
    WritingRun,
)
from app.services.webnovel_knowledge import (
    generate_写作指导包,
    generate_爽点指导,
    generate_节奏指导,
    generate_钩子指导,
    QUALITY_STANDARDS,
    爽点库,
    节奏模板,
    钩子库,
)


def _estimate_tokens(text: str) -> int:
    # A lightweight approximation good enough for budgeting and run logs.
    return max(1, len(text) // 4)


def _truncate(text: str, max_chars: int) -> str:
    return text if len(text) <= max_chars else f"{text[: max_chars - 3]}..."


def _provider_label() -> str:
    settings = get_settings()
    return "DeepSeek" if settings.llm_provider.lower() == "deepseek" else "OpenAI"


def estimate_tokens(text: str) -> int:
    return _estimate_tokens(text)


def provider_label() -> str:
    return _provider_label()


def resolve_writer_mode(requested_mode: str) -> str:
    settings = get_settings()
    if requested_mode == "auto":
        return "mock" if settings.use_mock_writer or not settings.openai_api_key else "openai"
    return requested_mode


def call_openai_compatible(messages: list[dict[str, str]], *, temperature: float = 0.7) -> str:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY 未配置，无法使用 LLM writer")

    request_body = {
        "model": settings.openai_model,
        "messages": messages,
        "temperature": temperature,
    }

    request = Request(
        urljoin(settings.openai_base_url.rstrip("/") + "/", "chat/completions"),
        method="POST",
        data=json.dumps(request_body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        },
    )

    last_error: Exception | None = None
    for attempt in range(settings.openai_max_retries + 1):
        try:
            with urlopen(request, timeout=settings.openai_timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
        except (HTTPError, URLError) as exc:
            last_error = exc
            if attempt >= settings.openai_max_retries:
                raise RuntimeError(f"{_provider_label()} 请求失败: {exc}") from exc
            time.sleep(settings.openai_retry_backoff_seconds * (attempt + 1))

    raise RuntimeError(f"{_provider_label()} 请求失败: {last_error}")


def _resolve_plan(payload: WriteChapterRequest, plans: list[ChapterPlan]) -> ChapterPlan | None:
    if payload.plan_id is not None:
        return next((plan for plan in plans if plan.id == payload.plan_id), None)
    return next((plan for plan in plans if plan.chapter_number == payload.chapter_number), None)


def _mock_chapter(
    project: Project,
    payload: WriteChapterRequest,
    matched_plan: ChapterPlan | None,
) -> ChapterDraft:
    settings = get_settings()

    title = f"第{payload.chapter_number}章 新的推进"
    summary = "根据章节规划生成的第一版草稿。"

    if matched_plan is None:
        content = (
            f"《{project.title}》第{payload.chapter_number}章草稿。\n\n"
            "当前未找到章节规划，因此本章仅生成一个最小示例正文。"
        )
    else:
        beat_lines = "\n".join(f"- {beat}" for beat in matched_plan.beats)
        content = (
            f"《{project.title}》第{payload.chapter_number}章草稿\n\n"
            f"章节目标：{matched_plan.goal}\n"
            f"核心冲突：{matched_plan.conflict}\n"
            f"结尾钩子：{matched_plan.hook}\n\n"
            "节奏设计：\n"
            f"{beat_lines}\n\n"
            "正文示例：\n"
            "主角在外部压力与内部欲望之间做出选择，推动本章核心冲突落地，"
            "并在结尾留下下一章的行动钩子。"
        )
        summary = matched_plan.goal

    return ChapterDraft(
        chapter_number=payload.chapter_number,
        title=title,
        content=content,
        summary=summary,
        source="mock" if settings.use_mock_writer else "llm",
    )


def _openai_prompt(
    project: Project,
    payload: WriteChapterRequest,
    context_pack: ContextPack,
) -> str:
    # 基础信息
    plan_text = (
        "无章节规划"
        if context_pack.chapter_plan is None
        else (
            f"章节目标：{context_pack.chapter_plan.goal}\n"
            f"核心冲突：{context_pack.chapter_plan.conflict}\n"
            f"结尾钩子：{context_pack.chapter_plan.hook}"
        )
    )
    
    # 增强规范信息
    enhanced_plan_text = ""
    if context_pack.chapter_plan and context_pack.chapter_plan.enhanced_spec:
        spec = context_pack.chapter_plan.enhanced_spec
        enhanced_plan_text = f"""
【增强规划规范】

爽点设计：
- 类型：{spec.爽点类型}
- 描述：{spec.爽点描述}
- 强度：{spec.爽点强度}/10
- 位置：{spec.爽点位置}

节奏设计：
- 类型：{spec.节奏类型}
- 转折点：{spec.转折点数量}个
- 描述：{spec.节奏描述}

钩子设计：
- 类型：{spec.钩子类型}
- 描述：{spec.钩子描述}
- 强度：{spec.钩子强度}/10

场景设计：
- 数量：{spec.场景数量}个
- 列表：
"""
        for i, 场景 in enumerate(spec.场景列表, 1):
            enhanced_plan_text += f"  {i}. {场景}\n"
        
        enhanced_plan_text += f"""
情绪曲线：
- 起点：{spec.情绪起点}
- 终点：{spec.情绪终点}
- 转折点：{spec.情绪转折点}个

质量检查点：
"""
        for i, 检查点 in enumerate(spec.质量检查点, 1):
            enhanced_plan_text += f"  {i}. {检查点}\n"
    
    # 角色信息（增强）
    character_lines = "\n".join(
        f"- {character.name} / {character.role} / {character.realm} / 性格：{', '.join(character.personality)} / 动机：{character.core_motivation}"
        for character in context_pack.active_characters
    ) or "- 暂无角色"
    
    # 开放伏笔（增强）
    hook_lines = "\n".join(
        f"- {item.status} / 第{item.created_in_chapter}章 / {item.content} / 预期回收：{item.expected_resolution_arc}"
        for item in context_pack.open_hooks
    ) or "- 暂无开放伏笔"
    
    # 硬约束
    constraint_lines = "\n".join(f"- {item}" for item in context_pack.hard_constraints) or "- 无"
    
    # 预算说明
    budget_lines = "\n".join(
        f"- {key}: {value}" for key, value in context_pack.token_budget.items()
    ) or "- 无"

    # 获取题材风格指导
    from app.services.webnovel_knowledge import 题材风格指南
    题材风格 = 题材风格指南.get(project.genre, 题材风格指南.get("玄幻", {}))
    
    # 网文写作指导
    网文指导 = f"""
【网文写作专业指导】

你是网文写作专家，精通爽点设计、节奏控制、钩子技巧和追读心理学。

核心原则：
1. 爽点密度：每章至少2个明确爽点，爽点强度>=6分
2. 节奏控制：保持网文节奏密度，至少3个明确转折点
3. 钩子强度：结尾钩子评分>=7分，形成追读意愿
4. 追读心理：构建期待感、回报感、危机感、代入感

爽点设计技巧：
- 升级爽：铺垫压力 -> 突破过程 -> 实力展现 -> 对比强化
- 打脸爽：铺垫嘲讽 -> 压抑情绪 -> 反击时机 -> 碾压表现 -> 围观反应
- 逆袭爽：铺垫劣势 -> 压抑情绪 -> 爆发时机 -> 反转过程 -> 对比强化
- 收获爽：铺垫期待 -> 收获过程 -> 收获价值 -> 后续影响

节奏控制技巧：
- 快节奏：前1/4快速铺垫冲突 -> 中1/2密集冲突和转折 -> 后1/4高潮爆发+强钩子
- 慢节奏：前1/3缓慢铺垫 -> 中1/3渐进推进 -> 后1/3设置钩子
- 高潮节奏：前1/5快速铺垫 -> 中3/5高潮爆发 -> 后1/5收尾+强钩子

钩子设计技巧：
- 悬念钩：留下未解之谜，设置读者期待，延迟解答
- 反转钩：铺垫反转线索，设置反转预期，延迟反转揭晓
- 威胁钩：制造明确威胁，设置危机感，延迟威胁解决
- 期待钩：设置明确目标，设置读者期待，延迟目标实现

追读心理学：
- 期待感：设置明确目标、悬念、反转、危机
- 回报感：设计明确爽点，保证爽点强度，及时给予回报
- 危机感：制造明确危机，强化危机强度，适度延迟解决
- 代入感：塑造可代入人物，描写代入场景、情绪、选择

【题材风格指南 - {project.genre}】

风格特点：{', '.join(题材风格.get('风格特点', []))}
语言风格：{题材风格.get('语言风格', '')}
核心要素：{', '.join(题材风格.get('核心要素', []))}
常用词汇：{', '.join(题材风格.get('常用词汇', []))}
爽点侧重：{', '.join(题材风格.get('爽点侧重', []))}
节奏建议：{题材风格.get('节奏建议', '')}
"""

    # 质量标准
    质量标准文本 = """
【质量标准】

每章必须达到以下标准：
- 剧情推进度 >= 6分：本章推进主线或支线
- 人物一致性 >= 7分：角色行为符合人设
- 世界观遵守 >= 8分：遵守硬规则和力量体系
- 追读钩子 >= 7分：结尾形成追读意愿
- 爽点密度 >= 6分：至少2个明确爽点
- 节奏控制 >= 6分：至少3个明确转折点
- 语言质量 >= 7分：不出戏、流畅、有画面感
"""

    settings = get_settings()
    prompt = (
        f"你是网文写作专家，为《{project.title}》生成第{payload.chapter_number}章草稿。\n\n"
        f"题材：{project.genre}\n"
        f"基调：{payload.tone}\n"
        f"项目 premise：{project.premise}\n\n"
        
        f"{网文指导}\n\n"
        
        f"{质量标准文本}\n\n"
        
        f"【章节规划】\n{plan_text}\n\n"
        
        f"{enhanced_plan_text}\n\n"
        
        f"【活跃角色】\n{character_lines}\n\n"
        
        f"【开放伏笔】\n{hook_lines}\n\n"
        
        f"【Story Bible 摘要】\n{context_pack.story_bible_summary}\n\n"
        
        f"【最近事件摘要】\n{context_pack.event_summary}\n\n"
        
        f"【角色状态摘要】\n{context_pack.character_state_summary}\n\n"
        
        f"【补丁摘要】\n{context_pack.patch_summary}\n\n"
        
        f"【检索优先级】\n{chr(10).join(f'- {item}' for item in context_pack.retrieval_priorities)}\n\n"
        
        f"【上下文说明】\n{context_pack.context_summary}\n\n"
        
        f"【硬约束】\n{constraint_lines}\n\n"
        
        f"【预算说明】\n{budget_lines}\n\n"
        
        "【写作要求】\n"
        "- 字数：2000-3000字\n"
        "- 爽点密度：至少2个明确爽点\n"
        "- 钩子强度：结尾钩子评分>=7分\n"
        "- 节奏密度：至少3个明确转折点\n"
        "- 语言质量：不出戏、流畅、有画面感\n\n"
        
        "请输出中文网络小说章节正文，包含标题和至少 6 段内容。"
    )
    return _truncate(prompt, settings.writer_max_prompt_chars)


def build_chapter_prompt(
    project: Project,
    payload: WriteChapterRequest,
    context_pack: ContextPack,
) -> str:
    return _openai_prompt(project, payload, context_pack)


def _rewrite_prompt(
    project: Project,
    chapter: ChapterDraft,
    review: ReviewReport,
    payload: RewriteChapterRequest,
    context_pack: ContextPack,
) -> str:
    # 增强角色信息
    character_lines = "\n".join(
        f"- {character.name} / {character.role} / {character.realm} / 性格：{', '.join(character.personality)} / 动机：{character.core_motivation}"
        for character in context_pack.active_characters
    ) or "- 暂无角色"
    
    # 增强伏笔信息
    hook_lines = "\n".join(
        f"- {item.status} / 第{item.created_in_chapter}章 / {item.content} / 预期回收：{item.expected_resolution_arc}"
        for item in context_pack.open_hooks
    ) or "- 暂无开放伏笔"
    
    findings = "\n".join(f"- {item}" for item in review.findings) or "- 无"
    suggestions = "\n".join(f"- {item}" for item in review.rewrite_suggestions) or "- 无"
    constraint_lines = "\n".join(f"- {item}" for item in context_pack.hard_constraints) or "- 无"
    note = payload.note.strip() or "无额外说明"

    # 网文重写指导
    网文重写指导 = """
【网文重写专业指导】

你是网文重写专家，擅长修复章节质量问题并提升整体质量。

重写原则：
1. 保留可用骨架：保留原有剧情骨架和核心冲突
2. 针对性修复：重点修复评审发现的具体问题
3. 质量提升：在修复基础上提升爽点、节奏、钩子等质量要素
4. 连续性保护：不得破坏关键设定与连续性

爽点增强技巧：
- 升级爽：强化突破过程的细节描写，增加对比强化
- 打脸爽：增加围观反应描写，强化碾压感
- 逆袭爽：增加压抑情绪描写，强化反转冲击力
- 收获爽：增加收获价值描写，强化回报感

节奏优化技巧：
- 增加转折：添加转折点，提升节奏密度
- 强化冲突：增加冲突细节，提升冲突强度
- 加快节奏：删除冗余铺垫，加快节奏推进
- 优化分布：调整爽点和转折的分布位置

钩子强化技巧：
- 悬念钩：在结尾增加未解之谜
- 反转钩：在结尾增加反转线索
- 威胁钩：在结尾增加危机信号
- 期待钩：在结尾增加明确的下一步目标

评分目标：
- 逻辑分 >= 7.0
- 连续性分 >= 6.5
- 人物分 >= 7.0
- 钩子分 >= 7.0
- 爽点密度分 >= 6.0
- 节奏控制分 >= 6.0
- 追读意愿分 >= 6.0
"""

    # 增强规范信息
    enhanced_plan_text = ""
    if context_pack.chapter_plan and context_pack.chapter_plan.enhanced_spec:
        spec = context_pack.chapter_plan.enhanced_spec
        enhanced_plan_text = f"""
【章节增强规划规范】

爽点设计：
- 类型：{spec.爽点类型}
- 描述：{spec.爽点描述}
- 强度：{spec.爽点强度}/10
- 位置：{spec.爽点位置}

节奏设计：
- 类型：{spec.节奏类型}
- 转折点：{spec.转折点数量}个
- 描述：{spec.节奏描述}

钩子设计：
- 类型：{spec.钩子类型}
- 描述：{spec.钩子描述}
- 强度：{spec.钩子强度}/10

场景设计：
- 数量：{spec.场景数量}个
- 列表：
"""
        for i, 场景 in enumerate(spec.场景列表, 1):
            enhanced_plan_text += f"  {i}. {场景}\n"
        
        enhanced_plan_text += f"""
情绪曲线：
- 起点：{spec.情绪起点}
- 终点：{spec.情绪终点}
- 转折点：{spec.情绪转折点}个

质量检查点：
"""
        for i, 检查点 in enumerate(spec.质量检查点, 1):
            enhanced_plan_text += f"  {i}. {检查点}\n"

    settings = get_settings()
    prompt = (
        f"你是网文重写专家，请重写《{project.title}》第{chapter.chapter_number}章。\n\n"
        f"题材：{project.genre}\n"
        f"基调：{payload.tone}\n"
        f"项目 premise：{project.premise}\n\n"
        
        f"{网文重写指导}\n\n"
        
        f"【当前章节信息】\n"
        f"标题：{chapter.title}\n"
        f"摘要：{chapter.summary}\n"
        f"字数：{len(chapter.content)}字符\n\n"
        
        f"【增强规划规范】\n{enhanced_plan_text}\n\n"
        
        f"【评审发现的问题】\n{findings}\n\n"
        
        f"【重写建议】\n{suggestions}\n\n"
        
        f"【人工补充说明】\n{note}\n\n"
        
        f"【活跃角色】\n{character_lines}\n\n"
        
        f"【开放伏笔】\n{hook_lines}\n\n"
        
        f"【Story Bible 摘要】\n{context_pack.story_bible_summary}\n\n"
        
        f"【最近事件摘要】\n{context_pack.event_summary}\n\n"
        
        f"【角色状态摘要】\n{context_pack.character_state_summary}\n\n"
        
        f"【硬约束】\n{constraint_lines}\n\n"
        
        "【重写要求】\n"
        "- 保留可用剧情骨架\n"
        "- 优先修复评审发现的具体问题\n"
        "- 提升爽点密度和钩子强度\n"
        "- 优化节奏控制和转折点分布\n"
        "- 不得破坏关键设定与连续性\n"
        "- 字数：2000-3000字\n\n"
        
        "请输出中文网络小说章节正文，包含标题和至少 6 段内容。"
    )
    return _truncate(prompt, settings.writer_max_prompt_chars)


def _generate_with_openai_prompt(
    prompt: str,
    chapter_number: int,
    summary: str,
) -> tuple[ChapterDraft, int, int]:
    content = call_openai_compatible(
        [
            {
                "role": "system",
                "content": "你是一个擅长中文长篇网文创作的写作专家，精通爽点设计、节奏控制、钩子技巧和追读心理学。",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.7,
    )
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    title = lines[0] if lines else f"第{chapter_number}章"
    summary = (
        summary
    )

    prompt_tokens_estimate = _estimate_tokens(prompt)
    completion_tokens_estimate = _estimate_tokens(content)

    return ChapterDraft(
        chapter_number=chapter_number,
        title=title,
        content=content,
        summary=summary,
        source="llm",
    ), prompt_tokens_estimate, completion_tokens_estimate


def _generate_with_openai(
    project: Project,
    payload: WriteChapterRequest,
    context_pack: ContextPack,
) -> tuple[ChapterDraft, int, int]:
    prompt = _openai_prompt(project, payload, context_pack)
    summary = (
        context_pack.chapter_plan.goal
        if context_pack.chapter_plan is not None
        else "基于上下文生成的章节草稿"
    )
    return _generate_with_openai_prompt(prompt, payload.chapter_number, summary)


def create_chapter_draft(
    project: Project,
    payload: WriteChapterRequest,
    plans: list[ChapterPlan],
    context_pack: ContextPack,
) -> tuple[WritingRun, ChapterDraft]:
    matched_plan = _resolve_plan(payload, plans)
    settings = get_settings()
    requested_mode = payload.writer_mode
    writer_mode = resolve_writer_mode(requested_mode)

    run = WritingRun(
        project_id=project.id,
        chapter_number=payload.chapter_number,
        status="running",
        writer_mode=writer_mode,
        message="正在生成章节草稿",
        model_name=settings.openai_model if writer_mode == "openai" else "mock-writer",
    )

    try:
        if writer_mode == "openai":
            run.attempts = settings.openai_max_retries + 1
            chapter, prompt_tokens, completion_tokens = _generate_with_openai(
                project,
                payload,
                context_pack,
            )
            run.prompt_tokens_estimate = prompt_tokens
            run.completion_tokens_estimate = completion_tokens
            run.total_tokens_estimate = prompt_tokens + completion_tokens
        else:
            chapter = _mock_chapter(project, payload, matched_plan)
            run.prompt_tokens_estimate = _estimate_tokens(json.dumps(context_pack.model_dump(mode="json"), ensure_ascii=False))
            run.completion_tokens_estimate = _estimate_tokens(chapter.content)
            run.total_tokens_estimate = run.prompt_tokens_estimate + run.completion_tokens_estimate
        run.status = "completed"
        run.message = "章节草稿已生成"
        run.updated_at = datetime.now(UTC)
        return run, chapter
    except Exception as exc:
        run.error_history.append(str(exc))
        if requested_mode == "auto":
            fallback_chapter = _mock_chapter(project, payload, matched_plan)
            run.status = "completed"
            run.fallback_used = True
            run.message = f"{_provider_label()} 失败，已自动降级到 mock writer: {exc}"
            run.model_name = "mock-writer"
            run.prompt_tokens_estimate = _estimate_tokens(
                json.dumps(context_pack.model_dump(mode="json"), ensure_ascii=False)
            )
            run.completion_tokens_estimate = _estimate_tokens(fallback_chapter.content)
            run.total_tokens_estimate = run.prompt_tokens_estimate + run.completion_tokens_estimate
            run.updated_at = datetime.now(UTC)
            return run, fallback_chapter
        run.status = "failed"
        run.message = str(exc)
        run.updated_at = datetime.now(UTC)
        raise


def create_rewrite_draft(
    project: Project,
    payload: RewriteChapterRequest,
    chapter: ChapterDraft,
    review: ReviewReport,
    context_pack: ContextPack,
    revision_number: int,
) -> tuple[WritingRun, ChapterDraft]:
    settings = get_settings()
    requested_mode = payload.writer_mode
    writer_mode = resolve_writer_mode(requested_mode)

    run = WritingRun(
        project_id=project.id,
        chapter_number=chapter.chapter_number,
        status="running",
        writer_mode=writer_mode,
        message=f"正在重写第 {chapter.chapter_number} 章草稿",
        model_name=settings.openai_model if writer_mode == "openai" else "mock-rewriter",
    )

    rewrite_summary = f"{chapter.summary}（第 {revision_number} 版修订）"
    try:
        if writer_mode == "openai":
            run.attempts = settings.openai_max_retries + 1
            prompt = _rewrite_prompt(project, chapter, review, payload, context_pack)
            rewritten, prompt_tokens, completion_tokens = _generate_with_openai_prompt(
                prompt,
                chapter.chapter_number,
                rewrite_summary,
            )
            run.prompt_tokens_estimate = prompt_tokens
            run.completion_tokens_estimate = completion_tokens
            run.total_tokens_estimate = prompt_tokens + completion_tokens
        else:
            suggestions = "；".join(review.rewrite_suggestions) or "补强章节目标、冲突与钩子"
            rewritten = ChapterDraft(
                chapter_number=chapter.chapter_number,
                title=f"{chapter.title}（修订版）",
                content=(
                    f"{chapter.title}（修订版）\n\n"
                    f"原章节摘要：{chapter.summary}\n"
                    f"重点修复：{suggestions}\n"
                    f"人工补充：{payload.note or '无'}\n\n"
                    "修订正文：\n"
                    "本次重写会保留原有剧情推进骨架，补强章节目标的显性推进、冲突压迫感、"
                    "角色互动与结尾钩子，使章节更适合继续进入评审与后续 canon 写回。"
                ),
                summary=rewrite_summary,
                source="mock" if settings.use_mock_writer else "llm",
            )
            run.prompt_tokens_estimate = _estimate_tokens(
                json.dumps(
                    {
                        "chapter": chapter.model_dump(mode="json"),
                        "review": review.model_dump(mode="json"),
                        "context": context_pack.model_dump(mode="json"),
                    },
                    ensure_ascii=False,
                )
            )
            run.completion_tokens_estimate = _estimate_tokens(rewritten.content)
            run.total_tokens_estimate = run.prompt_tokens_estimate + run.completion_tokens_estimate

        rewritten = rewritten.model_copy(
            update={
                "revision_number": revision_number,
                "parent_chapter_id": chapter.id,
                "rewrite_source_review_id": review.id,
                "is_current": True,
            }
        )
        run.status = "completed"
        run.message = f"第 {chapter.chapter_number} 章修订稿已生成"
        run.updated_at = datetime.now(UTC)
        return run, rewritten
    except Exception as exc:
        run.error_history.append(str(exc))
        if requested_mode == "auto":
            fallback_payload = payload.model_copy(update={"writer_mode": "mock"})
            fallback_run, fallback_chapter = create_rewrite_draft(
                project,
                fallback_payload,
                chapter,
                review,
                context_pack,
                revision_number,
            )
            fallback_run.fallback_used = True
            fallback_run.error_history = run.error_history + fallback_run.error_history
            fallback_run.message = f"{_provider_label()} 失败，已自动降级到 mock rewriter: {exc}"
            return fallback_run, fallback_chapter
        run.status = "failed"
        run.message = str(exc)
        run.updated_at = datetime.now(UTC)
        raise
