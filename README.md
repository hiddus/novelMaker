# NovelMaker

面向长篇网文创作的多 Agent 小说生产系统。

## 当前状态

当前仓库已经包含：

- `NovleMker.md`：可开工的架构设计文档
- `backend/`：FastAPI MVP 接口与文件型持久化实现
- `frontend/`：Vue 3 工作台，支持项目、Story Bible、角色、事件、章节规划、章节草稿、上下文包、快照与版本记录联调

## MVP 范围

第一版先打通以下链路：

- 创建项目
- 维护 Story Bible
- 维护角色
- 记录事件
- 生成章节规划
- 生成章节草稿
- 连续批量生成多章
- 自动写回事件与角色状态
- 自动生成快照与版本记录
- 按章节执行回滚
- 生成 Retcon Patch 并支持回滚后重跑
- 记录批处理任务运行历史
- 创建可暂停 / 恢复 / 重试的调度任务
- 预览增强后的上下文包（快照、角色状态、开放补丁）
- OpenAI writer 具备基础重试、超时、自动降级到 mock 与 token 估算
- 正文抽取已能识别地点、情绪、目标和关系线索
- 新增质量评审层，章节需先评审再决定是否进入 canon
- 支持人工审核通过 / 驳回，补齐 review gate 到 canon 写回的闭环
- 支持 Rewrite Agent，待审章节可自动生成修订稿并形成章节 revision 链
- 调度任务遇到待人工审核章节时会自动暂停，避免绕过 review gate
- Retcon Patch 已支持失效传播分析，可标记受影响章节、失效规划与需重算 hooks
- 支持按 Retcon Patch 自动重规划 future chapter plans，恢复 rerun 前的计划层
- SchedulerTask 已升级为多阶段调度器，可统一编排写作任务与恢复任务
- Continuity Board 已支持 Lore / Character / Timeline / Power 四类一致性审查
- Reader Council 已支持不同读者视角的追读意愿与章节吸引力评议
- Foreshadow Tracker 已支持 Hook Ledger、状态流转与回滚重建
- 提供章节级成本与质量指标面板
- Context Engine 已支持相关性评分检索、动态 token 预算和检索诊断
- SchedulerTask 已升级为后台 worker 轮询执行模型
- 查看项目聚合视图、上下文包与最新运行记录

## 当前已实现接口

```text
GET    /api/health
GET    /api/worker/status
GET    /api/projects
POST   /api/projects
GET    /api/projects/{project_id}
GET    /api/projects/{project_id}/story-bible
PUT    /api/projects/{project_id}/story-bible
GET    /api/projects/{project_id}/characters
POST   /api/projects/{project_id}/characters
GET    /api/projects/{project_id}/events
POST   /api/projects/{project_id}/events
POST   /api/projects/{project_id}/plan/book
GET    /api/projects/{project_id}/plans/chapters
POST   /api/projects/{project_id}/plan/chapter
GET    /api/projects/{project_id}/context/{chapter_number}
GET    /api/projects/{project_id}/chapters
POST   /api/projects/{project_id}/write/chapter
POST   /api/projects/{project_id}/write/batch
GET    /api/projects/{project_id}/runs
GET    /api/projects/{project_id}/snapshots
GET    /api/projects/{project_id}/versions
POST   /api/projects/{project_id}/rollback
POST   /api/projects/{project_id}/rerun
GET    /api/projects/{project_id}/task-runs
GET    /api/projects/{project_id}/retcon-patches
POST   /api/projects/{project_id}/retcon-patches/{patch_id}/replan
GET    /api/projects/{project_id}/scheduler-tasks
POST   /api/projects/{project_id}/scheduler-tasks
POST   /api/projects/{project_id}/scheduler-tasks/{task_id}/step
POST   /api/projects/{project_id}/scheduler-tasks/{task_id}/run
POST   /api/projects/{project_id}/scheduler-tasks/{task_id}/pause
POST   /api/projects/{project_id}/scheduler-tasks/{task_id}/resume
POST   /api/projects/{project_id}/scheduler-tasks/{task_id}/retry
GET    /api/projects/{project_id}/metrics
GET    /api/projects/{project_id}/metrics/summary
GET    /api/projects/{project_id}/reviews
GET    /api/projects/{project_id}/continuity-reports
GET    /api/projects/{project_id}/reader-council-reports
GET    /api/projects/{project_id}/hooks
GET    /api/projects/{project_id}/hook-state-changes
POST   /api/projects/{project_id}/reviews/{review_id}/decision
POST   /api/projects/{project_id}/reviews/{review_id}/rewrite
```

## 本地开发

### 前端

```bash
cd frontend
npm install
npm run dev
```

默认地址：

```text
http://localhost:5173/
```

### 后端

当前环境未检测到 Python，请先在本机安装 Python 3.11+。

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## 环境变量

复制根目录 `.env.example` 为 `.env`，然后按需填写：

```text
OPENAI_API_KEY=
NOVELMAKER_LLM_PROVIDER=openai
NOVELMAKER_OPENAI_BASE_URL=https://api.openai.com/v1
NOVELMAKER_OPENAI_MODEL=gpt-4o-mini
NOVELMAKER_DATA_DIR=backend/data
NOVELMAKER_USE_MOCK_WRITER=true
```

说明：

- 当前环境尚未配置真实 OpenAI Key
- 默认使用 `mock writer` 跑通接口闭环
- 后续可替换为真实 LLM 生成链路

## 当前能力边界

当前版本已经能作为“开发中的小说生产工作台”使用，但还不能宣称已实现“稳定输出 100 万字网络小说”。

距离该目标还需要继续完成：

- Context Engine 的真实检索与裁剪
- 更强的 State Extraction / Canon Update
- Snapshot / Versioning / Retcon Patch 的正式回滚链路
- Human Review Gate
- 真实 LLM 路由、重试、缓存与成本控制
- PostgreSQL / Neo4j / Qdrant 正式存储层
- 更强的批量章节执行与长期一致性评估

当前的 `Retcon Patch` 已可记录失效版本和建议重跑起点，但还没有做到：

- 自动重建角色关系图和时间线约束
- 真正的后台异步任务调度与暂停 / 恢复

当前的 `SchedulerTask` 已支持：

- 创建写作任务
- 创建 recovery 任务
- 单步推进
- 启动后台执行
- 暂停
- 恢复
- 失败后重试
- `replanning -> rerunning -> awaiting_review -> completed` 阶段流转

当前版本已带进程内后台 worker，会持续轮询 `running` 状态任务。

但目前仍不是独立进程 / 外部消息队列架构。

当前的 `Context Engine` 已支持：

- Story Bible 摘要
- 最近事件摘要
- 最近角色状态摘要
- 开放 Retcon Patch 摘要
- token 预算展示
- 按章节规划和 premise 生成 query terms
- 对事件 / 状态 / 快照 / 补丁 / 角色做相关性评分
- 按预算动态裁剪摘要内容
- 返回检索诊断与选择理由

当前的 `State Extraction` 已支持基础规则抽取：

- 地点关键词
- 情绪关键词
- 目标关键词
- 关系变化线索
- 地点迁移信号
- 目标推进信号

当前的 `Review Layer` 已支持：

- 逻辑分
- 连续性分
- 人物表现分
- 钩子分
- 总评与是否通过
- 问题清单与重写建议
- 关联 Continuity Board 报告
- 关联 Reader Council 报告
- 人工审核通过 / 驳回
- 人工通过后写回 canon，人工驳回后标记章节为 rejected
- 自动重写待审章节，并生成新的 revision 草稿重新进入评审

当前的 `Continuity Board` 已支持：

- Lore Judge：检查禁忌设定命中与世界观锚点缺失
- Character Judge：检查活跃角色缺席、POV 角色缺失与关系推进不足
- Timeline Judge：检查开放补丁未收敛、时间推进不明确与地点转场缺失
- Power Judge：检查角色战力跨度异常
- 结构化落库 continuity reports，并在前端工作台查看 issue 详情

当前的 `Reader Council` 已支持：

- Core Reader：评估主线推进与阶段性回报
- Fast Paced Reader：评估节奏密度与追更冲动
- Emotion Reader：评估情绪代入与人物关系反馈
- 计算章节追读分、回报分与节奏分
- 结构化落库 reader council reports，并进入前端工作台与指标面板

当前的 `Foreshadow Tracker` 已支持：

- Hook Ledger：正式记录每条伏笔的创建章、状态、最近触达章与预期回收线
- Hook State Change：记录 create / activate / resolve / abandon 四类状态变化
- Context Engine 将 open hooks 作为检索优先级之一，并进入 Writer / Rewrite prompt
- Snapshot 会记录 active_hook_ids
- Rollback 会裁剪 hook state changes，并重建 hook ledger

当前的 `Retcon Patch` 已支持：

- 识别受影响章节范围
- 标记失效章节规划
- 提取需要重算的 hooks
- 标记是否需要状态层重新写回
- 生成 impact summary 供 rerun 参考
- 一键自动重建 future chapter plans

当前的指标层已支持：

- 每章 token 估算
- 每章成本估算
- 每章质量分、抽取分、钩子分
- 每章读者分
- 开放伏笔数、已回收伏笔数、伏笔回收率
- fallback 次数统计
- 最近告警聚合

当前的 `OpenAI writer` 已支持：

- 超时控制
- 重试
- `auto` 模式失败自动降级到 mock
- prompt / completion token 粗略估算

但当前环境仍未配置真实 `OPENAI_API_KEY`，所以只能验证 mock 链路与 OpenAI 代码路径本身。

## 下一步建议

建议按以下顺序继续推进：

1. 完成 `Context Engine + Story Bible + Event/Character` 的真实上下文包装
2. 接入真实 OpenAI writer，并加入 run 级错误处理与重试
3. 实现章节通过后的 `State Extraction + Canon Update`
4. 加入 `Snapshot / Versioning / Rollback`
5. 再做批量章节生成与长篇稳定性优化
