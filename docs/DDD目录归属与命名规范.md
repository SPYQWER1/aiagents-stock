# DDD 目录归属与命名规范

本规范基于 DDD 四层架构（用户接口层、应用层、领域层、基础设施层）与聚合根、实体、值对象、领域服务、仓储、工厂等核心概念，明确目录归属规则与命名约定，适用于本项目的后续演进与新增功能。

## 1. 分层目录归属规则

| 层级 | 目录归属 | 职责边界 | 允许依赖 |
|---|---|---|---|
| 用户接口层（Presentation） | src/aiagents_stock/web、src/aiagents_stock/features | 处理 UI、交互、视图模型、请求参数解析 | 只能依赖应用层、领域层的 DTO/值对象 |
| 应用层（Application） | src/aiagents_stock/application | 编排用例、事务协调、调用领域对象与端口 | 依赖领域层与端口接口 |
| 领域层（Domain） | src/aiagents_stock/domain | 领域模型、规则与行为、端口定义 | 不依赖其他层 |
| 基础设施层（Infrastructure） | src/aiagents_stock/infrastructure、src/aiagents_stock/db、src/aiagents_stock/integrations、src/aiagents_stock/notifications、src/aiagents_stock/reporting | 数据持久化、外部系统接入、第三方 SDK、消息/通知 | 依赖领域层的端口与模型 |

## 2. 目录划分与归属说明

### 2.1 用户接口层

- web/
  - pages/：页面级入口（Streamlit 页面）
  - components/：可复用组件
  - adapters/：UI 到应用层的适配
  - utils/：纯 UI 工具与解析
- features/
  - 现存功能模块聚合，偏 UI + 业务编排的遗留实现
  - 新功能优先放到 web/ + application/ + domain/ + infrastructure 四层结构中

### 2.2 应用层

- application/<bounded_context>/use_cases.py
  - 用例编排与流程控制
  - 不包含业务规则，业务规则由领域模型完成

### 2.3 领域层

- domain/<bounded_context>/model.py
  - 聚合根、实体、值对象
- domain/<bounded_context>/services.py
  - 领域服务接口与纯领域逻辑服务
- domain/<bounded_context>/ports.py
  - 仓储/外部能力端口接口（协议/抽象）
- domain/<bounded_context>/dto.py
  - 领域内传输对象与不可变数据结构

### 2.4 基础设施层

- infrastructure/<bounded_context>/persistence/
  - 仓储实现（数据库、文件等）
- infrastructure/adapters/
  - 端口适配器实现（数据源、外部 API）
- infrastructure/ai/
  - AI 编排与模型客户端
- db/
  - 数据库连接与底层存储实现

## 3. 核心概念归属规则

| 概念 | 归属层级 | 目录建议 | 命名约定 |
|---|---|---|---|
| 聚合根（Aggregate Root） | 领域层 | domain/<context>/model.py | <AggregateName> |
| 实体（Entity） | 领域层 | domain/<context>/model.py | <EntityName> |
| 值对象（Value Object） | 领域层 | domain/<context>/model.py 或 dto.py | <ValueName> |
| 领域服务（Domain Service） | 领域层 | domain/<context>/services.py | <ActionName>Service |
| 仓储接口（Repository Port） | 领域层 | domain/<context>/ports.py | <AggregateName>Repository |
| 仓储实现（Repository Adapter） | 基础设施层 | infrastructure/<context>/persistence/ | <Storage><AggregateName>Repository |
| 工厂（Factory） | 领域层为主 | domain/<context>/factories.py | <AggregateName>Factory |
| 应用用例（Use Case） | 应用层 | application/<context>/use_cases.py | <Verb><Noun>UseCase |

## 4. 命名约定

### 4.1 文件与目录

- 有界上下文目录：使用业务名词，小写加下划线
  - 例：analysis、main_force
- 用例文件：use_cases.py
- 端口定义：ports.py
- 领域模型：model.py
- 领域服务：services.py
- 领域工厂：factories.py 或 <aggregate>_factory.py
- 仓储实现：<storage>_repository.py
  - 例：sqlite_repository.py、mysql_repository.py
- 适配器实现：<source>_provider.py、<name>_adapter.py

### 4.2 类与函数

- 聚合根/实体：名词，使用大驼峰
  - 例：StockAnalysis、AgentReview
- 值对象：名词，使用大驼峰，强调不可变
  - 例：StockInfo、AnalysisContent
- 领域服务：动词 + Service
  - 例：RiskEvaluateService
- 用例类：动词 + 用例对象 + UseCase
  - 例：AnalyzeSingleStockUseCase
- 仓储接口：<AggregateName>Repository
  - 例：StockAnalysisRepository
- 仓储实现：<Storage><AggregateName>Repository
  - 例：SqliteStockAnalysisRepository

## 5. 依赖方向与隔离规则

- 领域层不依赖应用层、用户接口层、基础设施层
- 应用层可依赖领域层与端口接口，不依赖具体基础设施实现
- 基础设施层实现领域端口，不反向依赖应用层
- 用户接口层不直接操作基础设施层，必须通过应用层用例

## 6. 与当前项目结构的对照

- 用户接口层
  - src/aiagents_stock/web/
  - src/aiagents_stock/features/
- 应用层
  - src/aiagents_stock/application/analysis/use_cases.py
  - src/aiagents_stock/application/main_force/use_cases.py
- 领域层
  - src/aiagents_stock/domain/analysis/{model.py, ports.py, services.py, dto.py}
  - src/aiagents_stock/domain/main_force/{model.py, ports.py}
- 基础设施层
  - src/aiagents_stock/infrastructure/
  - src/aiagents_stock/db/
  - src/aiagents_stock/integrations/
  - src/aiagents_stock/notifications/
  - src/aiagents_stock/reporting/

## 7. 参考（官方）

- https://learn.microsoft.com/en-us/dotnet/architecture/microservices/microservice-ddd-cqrs-patterns/ddd-oriented-microservice
