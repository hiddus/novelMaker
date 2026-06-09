from app.schemas.domain import ChapterPlan, ChapterPlanCreate, Project, RetconPatch, StoryBible


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
    return ChapterPlan(
        chapter_number=payload.chapter_number,
        goal=payload.goal,
        conflict=payload.conflict,
        hook=payload.hook,
        pov_character_id=payload.pov_character_id,
        beats=beats,
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
