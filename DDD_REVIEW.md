# 首页单股分析模块 DDD 架构合规性审查报告与重构计划

## 1. 总体评估

当前“首页单股分析模块”虽然在目录结构上采用了分层架构（Web, Application, Domain, Infrastructure），但在**职责划分**和**依赖倒置**的实现上存在显著缺陷。核心业务逻辑（如多智能体协作流程、Prompt构建策略、分析结果聚合）严重泄露到基础设施层，导致领域层呈现“贫血模型”特征，无法有效表达业务规则。

## 2. 详细审查

### 2.1 领域层 (Domain Layer)
*   **当前状态**: 仅包含数据传输对象（DTO，如 `StockDataBundle`, `AnalysisResult`）和接口定义（Ports）。
*   **问题**: 
    *   **贫血模型**: `AnalysisResult` 等对象仅用于承载数据，缺乏业务行为（如验证、状态流转、结果合并）。
    *   **聚合根缺失**: 没有明确的聚合根来维护分析过程的一致性和完整性。
    *   **业务逻辑缺失**: 核心的“多智能体分析”逻辑（如 Agent 角色定义、交互流程）未在领域层体现。

### 2.2 应用层 (Application Layer)
*   **当前状态**: `AnalyzeSingleStockUseCase` 负责编排数据获取、分析调用和持久化。
*   **问题**:
    *   **流程编排过重**: UseCase 承担了过多的过程式逻辑，直接操作 DTO，而不是调用领域对象的方法。
    *   **逻辑泄露**: 部分数据准备和校验逻辑散落在 UseCase 中。

### 2.3 基础设施层 (Infrastructure Layer)
*   **当前状态**: `DeepSeekAnalyzer` (在 `deepseek_agents.py` 中) 实现了具体的分析逻辑。
*   **问题**:
    *   **严重逻辑泄露**: Agent 的角色定义、System Prompt、Prompt 模板填充、团队讨论流程等核心业务规则被硬编码在基础设施层。这违背了 DDD 中“基础设施层应只提供技术实现”的原则。
    *   **高耦合**: `DeepSeekAnalyzer` 内部直接依赖了特定的数据 Fetcher (如 `RiskDataFetcher`) 来格式化数据，导致基础设施组件之间耦合。

### 2.4 用户接口层 (Web Layer)
*   **当前状态**: Streamlit 页面通过 `analysis_service.py` 调用 UseCase。
*   **问题**:
    *   **隐式依赖**: `analysis_service.py` 使用 Service Locator 模式 (`DIContainer.get_...`) 获取依赖，而不是通过构造函数注入，降低了可测试性和清晰度。

## 3. 违背 DDD 原则的设计问题汇总

1.  **领域逻辑泄露到基础设施层**: Prompt 工程和 Agent 编排是业务的核心，却被放在了 Infra 层。
2.  **贫血领域模型**: Domain 层只有数据结构，没有行为。
3.  **缺乏聚合根**: 无法保证分析对象（StockAnalysis）在生命周期内的不变量。
4.  **依赖倒置不彻底**: 虽然定义了 Port，但 Infra 层的实现包含了业务规则，导致 Domain 层实际上无法独立于具体实现（如 DeepSeek）。

## 4. 架构优化方案

### 4.1 重新设计领域模型
引入 **`StockAnalysis`** 作为聚合根，管理分析的生命周期和状态。

*   **Aggregate Root**: `StockAnalysis`
    *   属性: `id`, `stock_info`, `status`, `agent_reviews`, `final_decision`
    *   行为: `start_analysis()`, `add_agent_review()`, `conclude_analysis()`
*   **Entities**: `AnalysisAgent` (代表一个分析智能体)
*   **Value Objects**: `AgentRole` (技术/基本面/风险...), `AnalysisContent`
*   **Domain Services**: `AnalysisOrchestrator` (负责协调 Agent 交互策略)

### 4.2 重构基础设施层
将 `DeepSeekAnalyzer` 拆分为：
1.  **LLMProvider** (纯技术实现): 仅负责发送 Prompt 接收 Response。
2.  **PromptRepository** (可选): 管理 Prompt 模板。
业务逻辑（如 Prompt 的构建和 Agent 的调度）移回领域层或应用层。

### 4.3 优化应用层
`AnalyzeSingleStockUseCase` 将变得更简洁，主要负责：
1.  加载/创建 `StockAnalysis` 聚合根。
2.  调用领域服务执行分析。
3.  保存聚合根。

## 5. 重构计划

### 阶段一：领域核心重构 (预计 2 天)
1.  创建 `src/aiagents_stock/domain/analysis/model.py`，定义 `StockAnalysis` 聚合根及相关实体。
2.  定义 `AgentInteractionPolicy` 策略接口，用于描述 Agent 如何协作。

### 阶段二：基础设施解耦 (预计 2 天)
1.  从 `DeepSeekAnalyzer` 中剥离业务逻辑（Prompt 模板、角色定义）。
2.  实现纯粹的 `LLMClient` 适配器。

### 阶段三：应用层适配 (预计 1 天)
1.  重写 `AnalyzeSingleStockUseCase`，使其操作新的领域模型。
2.  更新 `AnalysisRecordRepository` 以支持聚合根的持久化。

### 阶段四：验证与测试 (预计 1 天)
1.  编写单元测试验证领域逻辑（不依赖外部 LLM）。
2.  运行集成测试确保端到端流程通畅。

## 6. 风险缓解
*   **保持兼容性**: 在重构期间，保留旧的 `analysis_service.py` 接口，通过 Adapter 模式适配新架构，确保前端无需大规模修改。
*   **增量迁移**: 先迁移“单股分析”模块，验证成功后再推广到其他模块。
