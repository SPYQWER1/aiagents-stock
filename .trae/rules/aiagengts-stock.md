1.使用python的streamlit框架构建的web应用
2.需提供完善的中文注释，包括函数、类、模块等的注释，注释需符合python的docstring规范
3.遵从ddd四层架构规范：
    1. 表现层（Presentation Layer）：负责处理用户交互，展示业务数据。
    2. 应用层（Application Layer）：协调业务用例，调度领域对象，管控全局事务。
    3. 领域层（Domain Layer）：领域层封装核心业务逻辑与领域模型，是系统的业务中心，不依赖于外部技术。
    4. 基础设施层（Infrastructure Layer）：负责与外部系统（如数据库、API、消息队列等）进行交互,提供通用的技术实现。