# 实地调研加权透视

加权透视汇总的真实业务分析小型项目。完整模拟客户、痛点、上下游、算法公式与一天工作剧本见 [BUSINESS.md](BUSINESS.md)。

## 模块与业务流程
数据接入（JSON/CSV、字段验证、批次指纹）→ 参数化分析（异步 Python worker）→ 双盲复核（两票制独立结论、收齐前互隐身份意见、第三人仲裁）→ 定时分发（本地收件箱、CSV/JSON、SHA256）；另有业务总览和审计轨迹。
三个贯穿全栈的实体：Dataset 数据批次、Job 分析任务、Report 分发计划；辅助 User、Audit、Delivery，以及双盲复核的 ReviewRound 送审轮次与 ReviewVote 独立票。

## 快速启动
```bash
cp .env.example .env
docker compose up -d --build --wait
docker compose exec -T backend python -m scripts.seed_demo
```
访问 http://localhost:18218；后端文档 http://localhost:19218/docs；数据库宿主端口 17718。
`SEED_DEMO=true` 自动幂等 seed；不覆盖用户修改。手动 seed 命令可重复执行。

## 演示账号与权限
|账号|密码|真实权限|
|---|---|---|
|admin@demo.local|Demo123!|接入、执行、送审、复核、仲裁、分发、暂停、读取与下载|
|admin2@demo.local|Demo123!|第二位管理员，用于独立复核与未参与第三人仲裁|
|analyst@demo.local|Demo123!|接入、执行、送审与复核；不能安排分发|
|analyst2@demo.local|Demo123!|第二位分析员，保证非发起人复核人不少于两名|
|viewer@demo.local|Demo123!|只读与下载，不能送审或签署|

## 双盲复核规则
- 仅 admin/analyst 可送审，且发起人不能复核自己的结论；系统自动指定两名非发起人复核人各占一个独立席位。
- 收齐两票前严格双盲：复核人只能看到自己的身份与意见，对方席位仅显示「待提交/已提交」；越权查看与代签在服务端拒绝（前端按钮显示不作数）。
- 两票通过 → 自动批准并解盲，可安排分发；两票驳回 → 退回，重送生成新的送审编号（序号递增、旧票不复制、不串票）；一票通过一票驳回 → 进入仲裁，由未参与且非发起人的管理员承接并签署。
- 轮次关闭后到达的意见登记为迟到意见，归原送审编号、标记 late、不参与计票；同一复核人重复投票被拒，重试不重复记票；签署经行锁串行化，并发签署不串票。
- 复核工作台（双盲复核页）可查进度；定案解盲后可查每名复核人的身份、结论与理由。
- 双盲上线前的旧批准标记为「历史通过」保留效力；旧分发计划在补完一次双盲复核前暂停归档，已有附件保持原文不动。单人 `/jobs/{id}/approve` 已停用。

## 技术与本地开发
Python 3.12 / FastAPI / SQLAlchemy / NumPy / SciPy / scikit-learn；PostgreSQL 16；Redis 7；Nginx；原生 HTML CSS JavaScript ES modules（用户指定）。后端所有校验、持久化和算法在服务端。无前端打包步骤。
后端：安装 backend/requirements.txt，设置 DATABASE_URL、REDIS_URL、JWT_SECRET、ARTIFACT_DIR 后在 backend/ 执行 `python -m migrations.initial`、`python -m scripts.seed_demo`、`uvicorn src.main:app`，另开 `python -m src.worker`。前端使用带 /api 反向代理的 Nginx，直接打开 index.html 不支持 API。

## 目录与工程约定
backend/src/{models,schemas,services,routes,controllers,middlewares,constants,config,utils}；backend/scripts/seed_demo.py；backend/migrations/initial.py。
frontend/src/{api,stores,types,components/common,hooks,pages,router,utils,constants}。
Role 枚举：admin/analyst/viewer；JobStatus：queued/running/completed/failed；ReviewRoundStatus：pending/in_arbiter/approved/rejected；ReviewDecision：approve/reject。后端 backend/src/constants/enums.py，前端 frontend/src/constants/enums.js；路由权限在 middlewares/auth.py；页面按相同角色控制操作入口。双盲复核后端在 src/services/reviews.py、src/routes/reviews.py、src/utils/review_serialization.py，前端在 src/components/common/review-panel.js 与 src/pages/reviews.js。

## 环境变量与 Docker
COMPOSE_PROJECT_NAME=survey-pivot；FRONTEND_PORT=18218；BACKEND_PORT=19218；DB_PORT=17718；DB_PASSWORD、JWT_SECRET 见 .env.example；SEED_DEMO 默认 true。共享命名产物卷供后端下载与 worker 写入，数据库/Redis 各持久卷。
恰好五服务均有健康检查。Redis 队列加 SQL 排队状态兜底；worker 按 next_run 生成本地收件箱文件。周期 60 秒至 30 天。分发结果为批准分析的固定快照；若需新数据重新计算并建立新计划。当前不连接邮件或企业聊天。
错误响应、请求编号、Redis 每 IP 每分钟 240 次限流、JWT 和数据库操作审计。演示密钥与密码仅供本机模拟；生产部署前配置独立密钥与账号。

## 数据与验收
所有数据为固定随机种子生成的模拟业务数据，不能作为实际生产决策证据。项目独立算法、输入边界及业务局限详见 BUSINESS.md。测试与截图统一存放 ../../test-artifacts/gb-1019/，源码不含日志/截图/测试报告。
清理本项目演示数据：`docker compose down -v --remove-orphans`（会删除本项目命名卷）。

## License
MIT，见 LICENSE。
