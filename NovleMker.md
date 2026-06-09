
---

# NovelMaker

## 百万字长篇小说 Agent 生产系统

### Version 1.2

---

# 1. 文档目标

本文档不是创意草稿，而是第一版可开工的设计文档。

目标：

```text
明确系统边界
明确模块职责
明确输入输出
明确核心数据模型
明确 MVP 开发顺序
明确第一批接口与目录结构
```

---

# 2. 项目定位

NovelMaker 是一个面向长篇网文创作的多 Agent 协同创作系统。

它不是：

```text
聊天式续写工具
单章生成器
一次性 Prompt 包装器
```

它是：

```text
有规划层
有状态层
有生成层
有审查层
有写回层
有版本层
有人类审核层
```

系统输入：

```text
一句创意
或一个故事设定
或一批已有章节
```

系统输出：

```text
结构化长篇小说项目
卷级规划
章节规划
章节正文
状态快照
可持续更新的小说工程
```

核心目标：

```text
长期剧情一致性
长期人物一致性
长期世界观一致性
长期伏笔管理
长期时间线管理
长期可恢复生产
```

---

# 3. 非目标

第一版不追求：

```text
一键生成百万字成品
复杂商业化工作流
全自动无需人工介入
一次性接入所有大模型与所有存储
```

第一版追求：

```text
先把单书工程跑通
先把状态系统跑通
先把章节规划 -> 正文 -> 审查 -> 写回闭环跑通
```

---

# 4. 设计原则

## Principle 1

Agent 不负责长期记忆。

State System 负责长期记忆。

## Principle 2

Agent 不负责全书规划。

Planner 负责全书规划。

## Principle 3

Writer 只负责生成草稿。

Judge 负责判定是否可过稿。

## Principle 4

所有关键状态必须结构化存储。

禁止仅依赖 Prompt 历史。

## Principle 5

任何剧情变更必须可追溯。

必须可回滚。

## Principle 6

所有自动化步骤都必须允许人工接管。

---

# 5. 总体架构

```text
Story Bible
    │
    ▼
Orchestrator / Scheduler
    │
    ├── Long-Term Planner
    ├── Arc Manager
    ├── Chapter Planner
    ├── Context Engine
    └── Human Review Gate
    │
    ▼
Primary Writer
    │
    ▼
Style / Emotion Rewriter
    │
    ▼
Editor Layer
    │
    ▼
Continuity Board
    ├── Lore Judge
    ├── Character Judge
    ├── Timeline Judge
    └── Power Judge
    │
    ▼
Reader Council
    │
    ▼
Rewrite Agent / Human Override
    │
    ▼
Final Chapter
    │
    ▼
State Extraction Pipeline
    │
    ▼
Canon Update + Snapshot + Versioning
    │
    └── 回写 Planner / Context Engine / Stores
```

---

# 6. 核心运行闭环

```text
创建小说项目
    ->
建立 Story Bible
    ->
生成全书规划
    ->
生成卷规划
    ->
生成未来 1~5 章规划
    ->
装配上下文包
    ->
生成章节草稿
    ->
编辑与一致性审查
    ->
必要时重写
    ->
输出 Final Chapter
    ->
抽取新事实并写回状态层
    ->
生成快照
    ->
继续下一章
```

---

# 7. 模块职责设计

## 7.1 Orchestrator / Scheduler

职责：

```text
任务编排
依赖管理
任务状态流转
失败重试
暂停 / 恢复
批量章节执行
人工审核挂起
模型路由
成本预算控制
```

输入：

```text
项目 ID
当前运行模式
目标章节范围
预算策略
人工审核策略
```

输出：

```text
任务树
运行记录
任务状态
章节级执行结果
```

## 7.2 Long-Term Planner

职责：

```text
生成全书大方向
确定主线与终局
确定主角成长路线
确定世界观约束
```

输入：

```text
创意
题材
目标字数
风格偏好
Story Bible 初稿
```

输出：

```text
book_plan
book_themes
book_endgame
power_curve
```

## 7.3 Arc Manager

职责：

```text
把全书规划拆成卷
维护每卷目标
维护卷级反派与高潮
维护卷间衔接关系
```

输出：

```text
arc_list
arc_goal
arc_conflict
arc_climax
arc_resolution
```

## 7.4 Chapter Planner

职责：

```text
把卷目标拆成未来 1~5 章执行计划
给 Writer 提供明确写作任务
给 Judge 提供预期对照
```

输出：

```text
chapter_goal
beat_list
scene_targets
new_hooks
expected_state_changes
```

## 7.5 Context Engine

职责：

```text
按 token 预算装配最小可用上下文
召回相关设定、人物、事件、时间线与伏笔
区分写作包、审查包、重写包
```

输入：

```text
当前章节规划
当前卷规划
关键角色列表
当前地点
当前时间点
最近事件
开放伏笔
冲突事实
```

输出：

```text
writer_context_pack
judge_context_pack
rewrite_context_pack
```

## 7.6 Primary Writer

职责：

```text
生成章节正文草稿
推进剧情
完成章节目标
保留网文节奏
```

说明：

```text
第一版采用单主 Writer
后续再扩展多 Writer 路由
```

## 7.7 Style / Emotion Rewriter

职责：

```text
强化情绪表达
修正对话质量
提升场景描写
统一文风
```

## 7.8 Editor Layer

职责：

```text
审读章节结构
检查可读性
检查节奏与留钩子
给出可执行修改意见
```

## 7.9 Continuity Board

职责：

```text
检查世界观冲突
检查人设偏移
检查时间线错误
检查战力异常
```

子模块：

```text
Lore Judge
Character Judge
Timeline Judge
Power Judge
```

## 7.10 Reader Council

职责：

```text
模拟不同读者视角
评估章节吸引力
评估追读意愿
输出主观反馈
```

## 7.11 Rewrite Agent

职责：

```text
在不破坏关键状态的前提下重写章节
优先修复特定问题
保留通过部分
```

重试策略：

```text
最大自动重写 3 次
超过阈值进入人工审核
```

## 7.12 State Extraction Pipeline

职责：

```text
从 Final Chapter 抽取结构化事实
提取事件
提取角色状态变化
提取关系变化
提取时间推进
提取伏笔状态变化
```

## 7.13 Canon Update Engine

职责：

```text
把抽取结果写回各数据存储
生成章节快照
记录版本与补丁
必要时使未来规划失效
```

---

# 8. 核心数据设计

## 8.1 三层状态模型

```text
Immutable Facts
Derived Facts
Runtime State
```

说明：

```text
Immutable Facts  最高可信度，如世界硬规则、核心血缘、不可改设定
Derived Facts    从已通过章节推导出的稳定事实
Runtime State    本轮生成过程中的临时变量和执行态
```

## 8.2 Story Bible

项目最高规则层。

字段建议：

```yaml
genre: 玄幻
tone: 热血升级
world_rules:
  - 死人不可复活
power_system:
  - 炼体
  - 筑基
  - 金丹
forbidden_rules:
  - 金丹不可秒杀元婴
author_intent:
  - 主角前期苟
  - 中期开宗立派
  - 后期飞升
```

## 8.3 World Store

记录：

```text
国家
宗门
城市
地图
秘境
势力
资源
历史事件
```

## 8.4 Character Store

建议最小结构：

```json
{
  "id": "char_mc_001",
  "name": "林凡",
  "role": "main",
  "gender": "male",
  "age": 18,
  "realm": "筑基",
  "personality": ["谨慎", "腹黑"],
  "core_motivation": "活下去并变强",
  "status": "active"
}
```

## 8.5 Character State Machine

```json
{
  "character_id": "char_mc_001",
  "chapter": 12,
  "location": "北域",
  "emotion": "愤怒",
  "hp": 80,
  "injury": "断臂",
  "goal": "复仇"
}
```

## 8.6 Relationship Graph

推荐存储：

```text
Neo4j
```

关系类型：

```text
亲属
师徒
敌对
合作
势力归属
情感
```

## 8.7 Plot Store

记录：

```text
主线
支线
当前剧情阶段
完成状态
依赖关系
```

## 8.8 Timeline Engine

记录：

```text
年月日
事件顺序
角色年龄
修炼时间
旅行时间
停留时间
```

目标：

```text
避免时间错乱
为 Judge 提供校验依据
为后续剧情推进提供硬约束
```

## 8.9 Event Store

```json
{
  "id": "event_00325",
  "chapter": 325,
  "actor_ids": ["char_mc_001"],
  "location_id": "loc_beiyu",
  "event_type": "battle",
  "summary": "林凡击败赵天龙"
}
```

## 8.10 Foreshadow Tracker

```json
{
  "id": "hook001",
  "created_in_chapter": 50,
  "content": "残缺地图",
  "status": "open",
  "expected_resolution_arc": "秘境篇"
}
```

状态：

```text
open
active
resolved
abandoned
```

## 8.11 Snapshot

每章结束后必须生成：

```text
chapter_snapshot
state_diff
active_hooks
active_characters
timeline_pointer
```

---

# 9. 任务状态机

```text
pending
running
blocked
review_required
failed
completed
cancelled
```

流转规则：

```text
pending -> running
running -> completed
running -> failed
running -> review_required
review_required -> running
failed -> running
failed -> blocked
```

---

# 10. 上下文工程设计

## 10.1 检索优先级

```text
硬规则优先
当前卷规划优先
当前章节规划优先
最近 3~10 章事件优先
当前活跃角色优先
开放伏笔优先
冲突事实优先
```

## 10.2 上下文包结构

```json
{
  "story_bible": {},
  "book_plan": {},
  "arc_plan": {},
  "chapter_plan": {},
  "active_characters": [],
  "recent_events": [],
  "open_hooks": [],
  "timeline_state": {},
  "hard_constraints": []
}
```

## 10.3 不同 Agent 的上下文差异

```text
Writer      更偏规划、角色、最近事件、开放伏笔
Judge       更偏硬规则、快照、冲突事实、数值边界
Rewrite     更偏问题列表、原稿、约束边界、必须保留信息
```

---

# 11. 写回与追溯设计

## 11.1 抽取内容

每章通过后自动抽取：

```text
新增事件
角色位置变化
角色情绪变化
角色关系变化
时间推进
战力变化
伏笔新增 / 推进 / 回收
```

## 11.2 Retcon Patch

任何对已通过章节的修改必须写入补丁：

```json
{
  "patch_id": "patch_0001",
  "reason": "修复时间线冲突",
  "affected_chapters": [32, 33, 34],
  "invalidated_plans": ["arc_02_plan_v3"],
  "requires_recompute_hooks": ["hook017"],
  "requires_state_rollback": true
}
```

## 11.3 版本化规则

```text
每章一个快照
每次通过生成一个版本号
每次重写生成 diff
每次回滚必须指定目标快照
```

---

# 12. 人工审核设计

## 12.1 必须进入人工审核的节点

```text
开书定盘
卷结尾
主角重大转折
核心设定变更
连续 3 次重写失败
关键冲突分超过阈值
```

## 12.2 Human Override 权限

```text
改规划
改设定
冻结事实
强制通过
强制回滚
终止任务
```

---

# 13. 技术设计

## 13.1 技术栈

Frontend：

```text
Vue 3
TypeScript
Vite
Monaco Editor
```

Backend：

```text
FastAPI
Pydantic
服务分层架构
文件型持久化作为 MVP
```

Storage：

```text
MVP: JSON 文件持久化
Phase 2: PostgreSQL + Neo4j + Qdrant
ObjectStore: 草稿、快照、导出文件
```

LLM Routing：

```text
OpenAI
Claude
Qwen
Gemini
DeepSeek
```

## 13.2 仓库结构

```text
ccworld/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── schemas/
│   │   └── services/
│   └── requirements.txt
├── frontend/
├── docs/
└── NovleMker.md
```

## 13.3 后端分层

```text
api       对外接口
core      配置与应用装配
schemas   请求与响应模型
services  核心业务逻辑
```

---

# 14. 第一版 API 设计

## 14.1 Project API

```text
GET    /api/health
GET    /api/projects
POST   /api/projects
GET    /api/projects/{project_id}
```

## 14.2 Character API

```text
GET    /api/projects/{project_id}/characters
POST   /api/projects/{project_id}/characters
```

## 14.3 Event API

```text
GET    /api/projects/{project_id}/events
POST   /api/projects/{project_id}/events
```

## 14.4 Planning API

```text
POST   /api/projects/{project_id}/plan/book
POST   /api/projects/{project_id}/plan/chapter
GET    /api/projects/{project_id}/plans/chapters
```

## 14.5 Writing API

```text
POST   /api/projects/{project_id}/write/chapter
GET    /api/projects/{project_id}/chapters
```

---

# 15. MVP 范围

## 15.1 Phase 1

必须完成：

```text
项目管理
角色管理
事件管理
章节规划
章节生成任务
JSON 文件持久化
基础前端工作台
```

## 15.2 Phase 2

继续完成：

```text
上下文工程
状态抽取
Canon Update
Snapshot / Versioning
Reader Council
```

## 15.3 Phase 3

继续完成：

```text
Human Review Gate
Retcon Patch
成本面板
自动批量生成
外部向量检索
```

---

# 16. 质量指标

系统指标：

```text
章节通过率
重写率
设定冲突率
时间线冲突率
伏笔回收率
单章成本
单章耗时
```

自动停机条件：

```text
连续失败 >= 3
冲突分超过阈值
成本超过预算
关键角色状态异常
```

---

# 17. 环境与配置

第一版环境变量：

```text
OPENAI_API_KEY=
NOVELMAKER_DATA_DIR=./data
NOVELMAKER_USE_MOCK_WRITER=true
```

说明：

```text
当前环境未配置 OpenAI Key
MVP 默认允许 mock writer 运行
接入真实 LLM 后可切换到真实生成链路
```

---

# 18. 结论

NovelMaker 不是一个“会写小说的单体 Agent”，而是一个由规划、状态、生成、审查、写回、版本化和人工审核共同组成的小说生产系统。

系统真正的护城河不在某个 Prompt，而在于：

```text
稳定的状态系统
可控的上下文工程
可追溯的版本机制
可恢复的调度系统
可人工接管的生产闭环
```

