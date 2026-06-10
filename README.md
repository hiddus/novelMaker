# NovelMaker

面向长篇网文创作的多 Agent 小说生产系统。

## 当前状态

当前仓库已经包含：

- `NovleMker.md`：可开工的架构设计文档
- `backend/`：FastAPI MVP 接口与文件型持久化实现
- `frontend/`：Vue 3 工作台，支持项目、Story Bible、角色、事件、章节规划、章节草稿、上下文包、长期记忆、快照与版本记录联调

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
- 预览增强后的上下文包（快照、角色状态、开放补丁、长期记忆）
- OpenAI-compatible writer 具备基础重试、超时、自动降级到 mock 与 token 估算
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
- SchedulerTask 已升级为持久化队列驱动的 worker 执行模型，支持嵌入式 worker 与独立 worker 入口
- Runtime Governance 已支持预算阈值、连续失败阈值、冲突分阈值与关键状态异常阻断
- Long-Term Memory 已支持把章节、事件、角色状态、快照、伏笔、补丁与评审沉淀为统一记忆索引
- Context Engine 已支持长期记忆召回、命中诊断与 retrieval trace 落库
- 工作台已支持运行评估总览，可聚合展示预算使用率、队列积压、治理阻断任务、近期关键停机信号，以及状态图谱批量 recovery 建议窗口
- 查看项目聚合视图、上下文包与最新运行记录

## 当前已实现接口

```text
GET    /api/health
GET    /api/worker/status
POST   /api/worker/start
POST   /api/worker/stop
POST   /api/worker/run-once
GET    /api/llm/status
POST   /api/llm/diagnose
GET    /api/llm/diagnostics
POST   /api/llm/test-run
GET    /api/llm/test-runs
GET    /api/projects/{project_id}/llm/preflights
POST   /api/projects/{project_id}/llm/preflight
GET    /api/projects
POST   /api/projects
GET    /api/projects/{project_id}
GET    /api/projects/{project_id}/governance/policy
PUT    /api/projects/{project_id}/governance/policy
GET    /api/projects/{project_id}/governance-events
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
GET    /api/projects/{project_id}/memories
GET    /api/projects/{project_id}/memory-index/status
POST   /api/projects/{project_id}/memory-index/rebuild
POST   /api/projects/{project_id}/memories/rebuild
GET    /api/projects/{project_id}/memory-traces
GET    /api/projects/{project_id}/ops-summary
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
GET    /api/projects/{project_id}/queue-jobs
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

独立 worker 可单独启动：

```bash
cd backend
.venv\Scripts\activate
python -m app.worker_runner
```

## 环境变量

复制根目录 `.env.example` 为 `.env`，然后按需填写：

```text
OPENAI_API_KEY=
NOVELMAKER_LLM_PROVIDER=deepseek
NOVELMAKER_OPENAI_BASE_URL=https://api.deepseek.com/v1
NOVELMAKER_OPENAI_MODEL=deepseek-chat
NOVELMAKER_DATA_DIR=backend/data
NOVELMAKER_USE_MOCK_WRITER=false
```

说明：

- 已兼容 OpenAI-compatible 路由，可切到 DeepSeek 等兼容接口
- 将 `NOVELMAKER_USE_MOCK_WRITER=true` 可强制退回 mock writer
- 当前 `.env.example` 提供的是 DeepSeek-compatible 示例，若使用 OpenAI 可自行替换 `provider`、`base_url` 与 `model`

## 当前能力边界

当前版本已经能作为“开发中的小说生产工作台”使用，但还不能宣称已实现“稳定输出 100 万字网络小说”。

距离该目标还需要继续完成：

- 更强的 State Extraction / Canon Update 与角色关系图谱
- 真实 LLM 端到端验证、缓存与更精细的成本控制
- PostgreSQL / Neo4j / Qdrant 正式存储层
- 外部消息队列 / 多 worker 协调架构
- 更强的批量章节执行评估与长篇一致性巡检

当前的 `Retcon Patch` 已可记录失效版本、建议重跑起点，并在 rollback / rerun 时同步裁剪和重建状态图谱；但仍没有做到：

- 基于外部消息队列的跨进程任务编排
- 更大规模章节链路下的自动回归巡检与批量一致性验证

当前的 `SchedulerTask` 已支持：

- 创建写作任务
- 创建 recovery 任务
- 单步推进
- 启动后台执行
- 入队后由 worker 自动认领和续跑
- 暂停
- 恢复
- 失败后重试
- `replanning -> rerunning -> awaiting_review -> governance_blocked -> completed` 阶段流转
- 预算耗尽、连续失败、冲突分超阈值、状态异常时自动阻断
- 治理事件流与人工 pause / resume / retry 审计

当前版本的 `worker / queue` 已支持：

- `QueueJob` 持久化队列，记录待执行、租约中、完成、失败与取消状态
- API 进程内嵌 worker，可持续认领队列任务并逐步推进 `SchedulerTask`
- 独立 worker 入口：`python -m app.worker_runner`
- Worker 状态接口可查看 backlog、最近认领 job、处理数和失败数
- 前端工作台可查看 worker 状态和项目级队列 job 列表

当前版本已经不是“仅进程内扫 `running` 任务”的旧模型，但仍未接入 Redis / RabbitMQ / Kafka 这类外部消息队列。

当前的 `Context Engine` 已支持：

- Story Bible 摘要
- 最近事件摘要
- 最近角色状态摘要
- 开放 Retcon Patch 摘要
- 长期记忆摘要
- token 预算展示
- 按章节规划和 premise 生成 query terms
- 对事件 / 状态 / 快照 / 补丁 / 角色做相关性评分
- 对长期记忆条目做统一召回与排序
- 按预算动态裁剪摘要内容
- 返回检索诊断、选择理由与 memory retrieval traces

当前的 `Long-Term Memory` 已支持：

- 将章节、事件、角色状态、快照、伏笔、补丁、评审和读者反馈沉淀为统一记忆条目
- 在构建 `ContextPack` 时自动重建记忆索引
- 按本地稀疏向量索引召回长期记忆，并保留 Qdrant 兼容切换入口
- 记录每次召回的 query terms、命中条目与命中原因
- 在前端工作台查看记忆索引状态、检索后端与召回轨迹

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
- 旧 revision 对应的 stale review 不能再被人工批准或继续重写，避免旧稿分叉污染 canon
- 治理层与长期记忆索引默认只消费当前 revision 对应的 review，旧评审不会继续形成阻断或检索噪声

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
- rollback 后会同步裁剪关系边、时间线节点与时间线约束，避免未来章图谱残留
- rerun 前会先清理目标章节及之后的旧写回数据，再重建 chapter/state/graph/timeline
- patch 完成 rerun 后会回写关闭对应的 patch 型 timeline warning，避免旧风险永久悬挂
- 同一章节的 canon projection 支持幂等重写，重复写回会先替换旧的 event/state/graph/timeline/snapshot/version/hook projection，再重建当前章状态
- 单章 canon projection 已收口为一次 store 提交，减少 event/state/graph/timeline/hook/snapshot/version 分步落盘时的半成品窗口
- recovery / rerun 必须覆盖补丁建议重跑起点到影响窗口末章，避免只重跑半截就提前关闭 patch
- 运行总览与项目详情内置状态图谱巡检，可发现 current chapter 缺 review/report/projection、快照/版本悬空引用、关系链缺 current head、关系/时间线多 current 链尾、跨章演化链章节顺序倒挂，以及 timeline node 自身断链等问题
- 状态图谱巡检会为每条断链生成结构化修复建议，推导建议 recovery 起点与恢复窗口
- 状态图谱巡检还会聚合项目级批量恢复计划，自动给出统一 recovery 起止章节、重点异常类别与摘要
- 对 relationship / timeline / reference 这类可能污染前后链头的断链，恢复建议会自动前移到更安全的恢复起点，而不是只从报错章开始
- 工作台可从状态图谱巡检面板一键载入或直接创建 recovery 任务，不再需要手工抄写修复章节范围
- `ops-summary` 与运行评估总览也会抬升展示项目级恢复计划，可直接在更高层摘要里载入或创建批量 recovery
- 工作台同时支持单条诊断修复和项目级批量 recovery，便于在多条断链同时出现时直接按统一窗口恢复
- recovery 任务除 patch 驱动模式外，也支持无 patch 的直接恢复重跑，用于修复 projection / graph / timeline 写回断链；但若仍存在开放 Retcon Patch，则必须优先走绑定 patch 的 recovery
- 人工审核通过时会校验章节 projection 是否完整；若 version / snapshot / extracted update / relationship / timeline / hook 链任一侧残缺，会自动重建 canon 写回

当前的时间线约束层已支持：

- 同章重写回时按约束签名同步更新，不再只做追加写入
- 每条约束带 `evolution_key / previous_constraint_id / is_current / resolved_in_chapter`，可显式表示演化链
- patch 型 warning 在 rerun 完成后标记为 `resolved`
- 新约束会接续上一条同类风险，形成“起点 -> 延续 -> 闭合”的链式记录
- `ordering / presence` 默认只在邻近章节窗口内持续生效
- `travel` 约束会额外保留一个章节窗口，用于观察转场是否被补足
- 超出活动窗口且未继续命中的非 patch 风险会自动转为 `resolved`
- 工作台可直接查看每条时间线约束的前序约束、当前态和解决章
- 上下文构建会优先携带仍在活动窗口内的未闭合 timeline 风险，以及仍未消化的 patch 风险
- 运行评估总览会继续聚合活跃风险数、延续型风险数、已闭合风险数和最近风险链摘要
- rollback / rerun 截断未来章节后，会重建时间线约束链的 `is_current`，恢复截断点之前仍应生效的当前风险

当前的指标层已支持：

- 每章 token 估算
- 每章成本估算
- 每章质量分、抽取分、钩子分
- 每章读者分
- 开放伏笔数、已回收伏笔数、伏笔回收率
- fallback 次数统计
- 最近告警聚合
- 批量执行评估总览、队列积压和治理阻断信号聚合

当前的 `Runtime Governance` 已支持：

- 配置总预算、单章预算、连续失败阈值
- 配置最小评审分、最小读者分、冲突分阈值和延续时间线风险阈值
- 对 `review_required`、Reader Council 弱反馈和关键状态异常执行自动暂停
- 对持续未闭合的时间线风险链执行治理阻断，避免带着旧风险继续扩写
- 对关键状态图谱断链执行治理阻断，普通写作会在前置检查被拦截，recovery 任务则只允许在收尾前继续修复
- 状态图谱治理阻断会附带建议 recovery 窗口与重点异常类别，避免只报错不指路
- 仅对绑定 patch 的 recovery 放行补丁治理 gate；无 patch recovery 只用于状态图谱修复，且不能绕过开放 Retcon Patch 的前置阻断
- 对预算超限、连续失败阈值命中和高冲突风险执行自动阻断
- 对未消化的 `Retcon Patch` 执行前置阻断，要求先完成 replan + rerun
- 在任务对象中记录治理状态、预算消耗与最近一次治理原因
- 在前端工作台查看治理策略和治理事件流

当前的 `OpenAI-compatible writer` 已支持：

- 超时控制
- 重试
- `auto` 模式失败自动降级到 mock
- prompt / completion token 粗略估算
- 自定义 `base_url` 与模型名，适配 DeepSeek 等兼容接口
- `GET /api/llm/status` 查看 provider readiness、route、model 与 mock 状态
- `POST /api/llm/diagnose` 执行连通性探测
- `GET /api/llm/diagnostics` 查看诊断历史
- `POST /api/llm/test-run` 执行最小试运行并返回输出摘要
- `GET /api/llm/test-runs` 查看试运行历史
- `POST /api/projects/{project_id}/llm/preflight` 对指定章节执行无副作用的章节级 smoke run，返回 context 装配结果、prompt 预览和输出摘要
- `GET /api/projects/{project_id}/llm/preflights` 查看章节级 preflight 历史
- 运行评估总览会把 LLM 风险拆成 `config / connectivity / fallback / preflight` 四类 issue buckets
- 运行评估总览会把时间线风险拆成活跃 / 延续 / 已闭合三类演化计数
- 工作台会展示最近 LLM 健康趋势，串联 diagnose / preflight / fallback / governance 事件
- 显式 `openai` 模式会在写作、重写、批量执行和调度前做 readiness 预检，避免任务在 provider 未就绪时盲跑
- scheduler 在运行时若检测到 live provider 不可用，会将任务转为治理阻断并记录 `llm` 信号事件

运行评估总览同时会展示开放补丁数、已重规划待 rerun 的补丁数与补丁风险摘要，用于识别“rollback 后尚未消化补丁”的窗口期。

前端工作台也已新增 LLM 诊断卡片，可直接查看 readiness、连通性探测结果、试运行输出、章节级 preflight 结果与最近历史记录。

但当前会话运行环境缺少可用 Python 命令，因此这里仍未在沙箱内完成真实后端进程级联调。

## 下一步建议

建议按以下顺序继续推进：

1. 接入正式向量库 / 外部检索层，替换当前 JSON 记忆索引实现
2. 继续增强状态图谱闭环，补批量巡检、演化链诊断和跨章一致性校验
3. 验证真实 DeepSeek / OpenAI-compatible 端到端生成链路
4. 将当前文件型队列升级为外部消息队列与多 worker 协调架构
5. 继续补长篇稳定性评估与自动巡检
