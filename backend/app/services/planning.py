from app.schemas.domain import ChapterPlan, ChapterPlanCreate, ChapterPlanEnhancedSpec, Project, RetconPatch, StoryBible


def generate_book_plan(project: Project) -> dict[str, object]:
    return {
        "project_id": project.id,
        "title": project.title,
        "genre": project.genre,
        "book_plan": {
            "theme": f"{project.genre}成长与秩序重构",
            "endgame": "主角完成自身成长并重塑世界格局",
            "power_curve": ["生存", "立足", "崛起", "称雄", "飞升"],
        },
    }


def build_chapter_plan(payload: ChapterPlanCreate) -> ChapterPlan:
    beats = [
        f"开场明确目标：{payload.goal}",
        f"制造冲突：{payload.conflict}",
        "推动角色做出选择并承担代价",
        f"结尾留下钩子：{payload.hook}",
    ]
    
    # 生成增强规范
    enhanced_spec = ChapterPlanEnhancedSpec(
        爽点类型=payload.爽点类型 if payload.爽点类型 else "升级爽",
        爽点描述=payload.爽点描述 or f"本章设计爽点：{payload.conflict}中的胜利或突破",
        爽点强度=payload.爽点强度 if payload.爽点强度 else 7,
        爽点位置=payload.爽点位置 if payload.爽点位置 else "中后段",
        节奏类型=payload.节奏类型 if payload.节奏类型 else "快节奏",
        转折点数量=payload.转折点数量 if payload.转折点数量 else 3,
        节奏描述=payload.节奏描述 or f"采用{payload.节奏类型 or '快节奏'}，至少{payload.转折点数量 or 3}个转折点",
        钩子类型=payload.钩子类型 if payload.钩子类型 else "悬念钩",
        钩子描述=payload.钩子描述 or payload.hook,
        钩子强度=payload.钩子强度 if payload.钩子强度 else 7,
        场景数量=payload.场景数量 if payload.场景数量 else 3,
        场景列表=payload.场景列表 or [
            f"开场：{payload.goal}的起点",
            f"发展：围绕{ payload.conflict}展开冲突",
            f"高潮：爽点爆发 + 钩子设置"
        ],
        情绪起点=payload.情绪起点 if payload.情绪起点 else "平稳",
        情绪终点=payload.情绪终点 if payload.情绪终点 else "期待",
        情绪转折点=payload.情绪转折点 if payload.情绪转折点 else 2,
        质量检查点=payload.质量检查点 or [
            f"剧情推进：本章是否推进{payload.goal}",
            f"爽点密度：是否包含{payload.爽点类型 or '升级爽'}",
            f"节奏控制：是否有{payload.转折点数量 or 3}个以上转折",
            f"钩子设置：结尾是否形成追读意愿",
            f"人物一致：角色行为是否符合人设",
        ],
    )
    
    return ChapterPlan(
        chapter_number=payload.chapter_number,
        goal=payload.goal,
        conflict=payload.conflict,
        hook=payload.hook,
        pov_character_id=payload.pov_character_id,
        beats=beats,
        enhanced_spec=enhanced_spec,
    )


def build_replanned_chapter_plans(
    project: Project,
    story_bible: StoryBible,
    patch: RetconPatch,
    tone: str,
) -> list[ChapterPlan]:
    chapter_numbers = patch.affected_chapter_numbers or [patch.recommended_rerun_from]
    hook_pool = patch.requires_recompute_hooks or [f"围绕{project.title}主线制造新的推进悬念"]
    conflict_prefix = patch.reason or "修复回滚后的剧情连续性"
    author_intent = "、".join(story_bible.author_intent[:2]) or project.premise

    plans: list[ChapterPlan] = []
    for index, chapter_number in enumerate(chapter_numbers, start=1):
        inherited_hook = hook_pool[min(index - 1, len(hook_pool) - 1)]
        goal = f"重建第 {chapter_number} 章后的剧情推进，延续{author_intent}"
        conflict = f"{conflict_prefix}，并处理第 {chapter_number} 章与后续章节的连续性断点"
        hook = f"{inherited_hook}，同时为第 {chapter_number + 1} 章留下新的追读钩子"
        plan = build_chapter_plan(
            ChapterPlanCreate(
                chapter_number=chapter_number,
                goal=goal,
                conflict=conflict,
                hook=hook,
            )
        ).model_copy(
            update={
                "source": "auto_replan",
                "patch_id": patch.id,
                "beats": [
                    f"承接回滚后状态，明确第 {chapter_number} 章的新目标",
                    f"围绕补丁原因处理冲突：{patch.reason}",
                    f"修复连续性问题并重新铺设后续主线",
                    f"保留网文节奏与基调：{tone}",
                    f"结尾钩子：{hook}",
                ],
            }
        )
        plans.append(plan)
    return plans
