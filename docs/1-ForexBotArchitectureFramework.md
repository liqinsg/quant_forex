# Development Plan — 全生命周期最高层开发参考规范

> **文档级别：** 项目全生命周期最高层参考规范（Top-Level Development Governance）
>
> **适用范围：** 本项目及其后续新增、重构、扩展的所有研究模块、观测模块、策略模块、工程组件和生产运行功能。
>
> **核心原则：** 本文档定义开发生命周期的治理框架、阶段边界、决策门槛与变更规则。任何具体设计、实现或流程若与本文档存在偏差，必须先明确偏差并进行讨论；未经讨论和明确决定，不得自行将偏差视为新规则，也不得静默修改本文档或既有架构。

---

## 1. 文档目的与权威性

本文件是整个开发生命周期的最高层参考文件，用于统一：

1. 设计与研究如何提出、审查和演进；
2. 系统工程如何划分模块、数据、接口与运行边界；
3. 开发如何分阶段实施、审查、测试和交付；
4. 结果如何通过历史数据、Shadow 运行和统计评估验证；
5. 何时以及依据什么证据，允许功能进入 Advisor、交易决策或生产运行；
6. 已发布功能如何持续监控、审查、回滚和迭代。

本文件不是某个单独功能的技术设计，也不是具体代码实现说明。具体模块可以拥有自己的设计规范、接口文档、测试计划和实施任务，但这些下层文件必须与本文件保持一致。

### 1.1 规范优先级

发生规范冲突时，按以下顺序处理：

1. **明确讨论后批准的项目级决议或本文件正式修订；**
2. 本文件当前有效版本；
3. 经批准的系统/模块架构规范；
4. 经批准的开发任务与实现规范；
5. 代码、注释、默认参数及工具生成的建议。

代码已经存在，不代表其设计天然正确；某项实现已经上线，也不代表它自动成为新的架构标准。

### 1.2 偏差处理原则

发现任何偏差时：

- 先记录事实：具体条款、当前实现/提案、差异及影响范围；
- 区分事实、推测、风险和建议，不得混写；
- 分析偏差产生的原因、收益、代价及潜在副作用；
- 讨论是否接受偏差、修正实现，或正式修订规范；
- 形成明确决定、理由、责任人及版本记录。

**在讨论和决定完成前，默认维持现行已批准规范。** 不得因为某个工具、LLM、开发者或代码实现提出了不同做法，就自动改变既有原则。

---

## 2. 总体开发治理模型：五层生命周期

所有功能和模块必须遵循以下五层生命周期：

1. Design & Evolution Architecture — 设计与演进架构
2. System Engineering Architecture — 系统工程架构
3. Development & Implementation Architecture — 开发与实施架构
4. Validation & Evaluation Architecture — 验证与评估架构
5. Decision & Operational Architecture — 决策与运营架构

```text
┌──────────────────────────────────────────────┐
│ 1. DESIGN & EVOLUTION                        │
│ Research question / hypotheses / definitions│
└──────────────────────┬───────────────────────┘
                       ↓
┌──────────────────────────────────────────────┐
│ 2. SYSTEM ENGINEERING                        │
│ Boundaries / data / interfaces / runtime     │
└──────────────────────┬───────────────────────┘
                       ↓
┌──────────────────────────────────────────────┐
│ 3. DEVELOPMENT & IMPLEMENTATION              │
│ Tasks / coding / tests / review / release     │
└──────────────────────┬───────────────────────┘
                       ↓
┌──────────────────────────────────────────────┐
│ 4. VALIDATION & EVALUATION                   │
│ Historical / shadow / statistical evidence   │
└──────────────────────┬───────────────────────┘
                       ↓
┌──────────────────────────────────────────────┐
│ 5. DECISION & OPERATIONS                     │
│ Go / No-Go / controlled rollout / monitoring│
└──────────────────────┬───────────────────────┘
                       │
             New evidence / issues
                       └──────────→ 回到 Design
```

五层是**治理与生命周期阶段**，不是五个必须对应为独立 Python package、类或服务的代码模块。具体工程实现可以按合理方式组织，但不得因此省略任何治理阶段。

### 2.1 生命周期不是单向瀑布流程

五层之间存在反馈循环：

- 设计阶段发现定义不清，可以返回研究问题；
- 工程阶段发现数据不可获得或接口不可靠，可以退回设计；
- 开发阶段发现实现不可测试或边界冲突，可以退回工程设计；
- 评估阶段发现假设不成立、样本不足或结果不稳定，可以继续 Shadow、重新设计或终止；
- 运营阶段发现漂移、异常或性能退化，可以暂停、回滚并重新进入设计与评估。

不得为了完成计划而强行推进到下一阶段。

### 2.2 Evidence & Governance：贯穿五层的横切原则

证据与治理不是只在评估阶段才出现的工作，而是贯穿整个生命周期：

| 阶段                  | 必须保留的证据                                         |
| --------------------- | ------------------------------------------------------ |
| Design                | 问题定义、假设、依据、反例、未知项、版本变更理由       |
| Engineering           | 数据来源、字段定义、计算规则、接口契约、边界和失败模式 |
| Development           | 代码变更、测试结果、审查记录、提交与发布版本           |
| Evaluation            | 数据覆盖、样本量、基线、统计结果、置信区间、失败案例   |
| Decision & Operations | Go/No-Go 理由、发布授权、监控指标、异常记录、回滚记录  |

任何结论都应能追溯到输入数据、计算版本、代码版本和决策记录。

---

## 3. 第一层：Design & Evolution Architecture

## 设计与演进架构

### 3.1 目标

在编写代码之前，明确“要研究或解决什么问题、为什么值得做、如何定义成功或失败”。

### 3.2 必须定义的内容

每项新功能或重大修改至少应明确：

- **Problem Statement：** 当前具体问题是什么；
- **Research Question：** 希望回答什么问题；
- **Hypothesis：** 待验证的假设是什么；
- **Evidence：** 已有数据或事实支持什么；
- **Unknowns：** 哪些内容尚未得到证实；
- **Alternatives：** 是否存在更简单或风险更低的方案；
- **Success Criteria：** 什么结果支持该假设；
- **Failure Criteria：** 什么结果会否定该假设；
- **Scope & Non-goals：** 本轮包含什么、不包含什么；
- **Limitations：** 已知限制和潜在偏差。

### 3.3 设计与演进规则

1. 不得将未经验证的假设写成事实。
2. 不得为了让方案看起来完整而虚构阶段、分数、概率或精确阈值。
3. 多个 LLM 或开发工具的意见属于审查输入，不构成自动批准。
4. 不同意见必须列出依据、分歧点和可验证方式。
5. 新版本必须说明相对上一版本改变了什么、为什么改变、影响哪些下层规范。
6. 定义应尽可能可观测、可复现、可证伪。
7. 如果研究目标尚不清楚，应先澄清问题，不应直接进入编码。

### 3.4 阶段输出

- Design Specification
- Research Questions & Hypotheses
- Scope / Non-goals
- Success & Failure Criteria
- Design Review / Decision Log
- Version History

### 3.5 进入下一层的门槛

研究目标、核心定义、范围和验收方向已经足够明确，可以设计数据与工程边界。若关键概念仍存在未解决歧义，应先讨论，不得用临时代码掩盖定义问题。

---

## 4. 第二层：System Engineering Architecture

## 系统工程架构

### 4.1 目标

将已批准的设计转化为边界清晰、数据可追溯、接口明确、运行行为可控的系统方案。

### 4.2 必须定义的内容

- 模块职责、输入、输出及禁止承担的职责；
- 数据来源、权威来源、时间语义和更新频率；
- 字段名称、类型、单位、精度、缺失值语义；
- 计算公式、参数、窗口、确认条件和边界行为；
- ID、状态、版本和关联关系；
- 模块接口及调用方向；
- 日志、存储、审计和数据保留策略；
- 异常处理、失败关闭（fail-closed）或降级行为；
- Shadow、Advisor、Execution 等运行模式之间的隔离；
- 性能、可靠性、安全性和可观测性要求。

### 4.3 模块边界原则

1. **单一职责：** 观测、研究、决策和执行职责应清晰分离。
2. **数据与行为分离：** 计算出某个值，不代表系统已确认某个事实或获准执行动作。
3. **模块独立：** 不同研究维度应保留各自原始定义，不应为了方便而混成一个未经验证的综合分数。
4. **接口显式：** 不得依赖隐式全局状态、隐式副作用或不透明的跨模块修改。
5. **可追溯：** 关键数据应能追溯到来源、时间、计算版本和代码版本。
6. **缺失值诚实表达：** Missing / Invalid / Not Available 不得静默替换为 0 或正常值。
7. **确定性：** 相同输入和相同计算版本，在定义范围内应产生可复现结果。
8. **向后兼容：** Schema 或接口变更必须评估旧数据、旧调用方和部署顺序。

### 4.4 观测、决策与执行的边界

默认架构边界：

```text
Market / Broker / Historical Data
              ↓
       Data & Observation
              ↓
     Research / Feature Layer
              ↓
          Advisor
              ↓
        Execution Layer
              ↓
        Broker API
```

- Observation 负责记录和计算，不应直接提交交易指令。
- Research / Feature Layer 负责形成可研究的特征，不自动获得交易权限。
- Advisor 可以消费已批准的数据和规则，但必须遵守明确的决策接口。
- Execution 负责执行已授权的动作，不应暗中重新解释研究指标。
- 任何跨层权限变化都属于架构变更，必须讨论并批准。

对于 OANDA 相关运行组件，Broker API 的实时状态应作为账户、交易和持仓状态的权威来源；不得未经批准以本地缓存或恢复文件覆盖经纪商事实。任何自动化组件的账户写入范围、标签归属和幂等规则必须在对应工程规范中明确。

### 4.5 版本与数据治理

关键观测记录至少应在适用时包含：

- `schema_version`
- `calculation_version`
- `source_timestamp`
- `observed_at`
- `instrument`
- `timeframe`
- `data_source`
- `validity_status`
- `reason_code` 或错误说明

观测记录、事后汇总和交易结果应分开保存。不得静默覆盖历史观测；更正应保留可追溯记录。

### 4.6 阶段输出

- Technical Architecture
- Module Responsibility Matrix
- Data Schema / Data Dictionary
- Interface Specification
- Runtime & Permission Boundaries
- Logging / Storage / Versioning Specification
- Failure-mode & Recovery Design

### 4.7 进入下一层的门槛

模块边界、数据契约、接口、运行模式和失败行为已明确；关键数据可获得且可验证；不存在未经讨论的职责越界。

---

## 5. 第三层：Development & Implementation Architecture

## 开发与实施架构

### 5.1 目标

将批准的工程设计分解为范围受控、可审查、可测试、可回滚的实施任务。

### 5.2 开发顺序

原则上按以下顺序实施：

1. Read-only inspection：检查现有代码、调用链、数据和历史行为；
2. Baseline capture：保存修改前行为、日志、测试和相关指标；
3. Instrumentation：先补充必要观测与审计能力；
4. Minimal implementation：只实现当前任务批准的最小范围；
5. Unit / contract tests：验证公式、接口、字段和边界；
6. Integration tests：验证模块之间的真实调用关系；
7. Regression tests：确认既有行为没有非预期变化；
8. Shadow / dry-run verification：在不产生真实副作用的模式下验证；
9. Code review：检查逻辑、范围、风险、可维护性和测试证据；
10. Controlled release：只有满足发布门槛后才可发布。

### 5.3 任务规范

每个开发任务必须明确：

- Task ID 与优先级（P0 / P1 / P2）；
- 目标和具体问题；
- 允许修改的文件、模块和接口；
- 明确禁止修改的范围；
- 预期行为及验收标准；
- 测试命令与预期结果；
- 风险和回滚方式；
- 是否允许改变运行行为；
- 是否允许调用外部 API、修改账户状态或产生真实交易副作用。

不得将多个无关目标塞入同一任务。若实施中发现任务范围不足或设计缺陷，应暂停并提出变更，不得自行扩大范围。

### 5.4 默认安全边界

除非另有明确批准：

- 新功能默认 Read-only / Shadow / Diagnostic；
- 新交易行为、自动执行开关和真实账户写入默认关闭；
- 不得在观测任务中顺带修改 Entry、Exit、SL、TP、Position Sizing、风险限制或执行流程；
- 不得以“重构顺便清理”为理由进行无关行为变更；
- 不得删除或弱化既有保护机制，除非有独立证据、明确任务和批准；
- 不得把日志输出、计算结果或测试通过误报为生产行为已生效。

### 5.5 测试与审查原则

- 测试必须对应明确的行为或不变量；
- 不能只测试理想路径，还要覆盖缺失数据、异常输入、边界值、重复调用和失败路径；
- 对时间序列和历史研究，必须检查时间对齐、未来数据泄漏、重复样本和窗口重叠；
- 对状态机，必须检查状态转换、重复确认、重启恢复和异常跳转；
- 对外部 API，必须区分本地模拟、dry-run 和真实请求；
- 测试结果必须说明实际执行了什么，不能只列计划执行的命令。

### 5.6 阶段输出

- Implementation Plan
- Scoped Task Specification
- Code Changes / Commit References
- Test & Regression Report
- Code Review Findings
- Shadow / Dry-run Evidence
- Release Candidate

### 5.7 进入下一层的门槛

实现与批准的设计一致；任务范围未被静默扩大；测试、回归和审查证据完整；已知缺陷与限制明确。仅仅“代码可以运行”不构成通过标准。

---

## 6. 第四层：Validation & Evaluation Architecture

## 验证与评估架构

### 6.1 目标

判断实现是否正确，以及研究假设是否得到数据支持。必须区分：

- **Implementation Correctness：** 代码是否按规范工作；
- **Measurement Validity：** 测量和数据是否可信；
- **Hypothesis Validity：** 研究假设是否得到支持；
- **Operational Effectiveness：** 在真实运行约束下是否有效。

这四者不能互相替代。代码正确不代表假设正确；指标相关不代表具备预测价值；回测盈利不代表生产可执行。

### 6.2 验证层次

按适用性组合使用：

1. **Unit / Contract Validation：** 公式、字段、接口和边界；
2. **Historical Validation：** 历史数据上的可复现性和分布；
3. **Out-of-sample / Walk-forward：** 检验样本外稳定性；
4. **Shadow Validation：** 实时数据下只观测、不改变交易行为；
5. **Controlled Experiment：** 在严格控制变量和风险预算下比较方案；
6. **Production Validation：** 经批准的小范围上线后持续验证。

### 6.3 评估设计要求

任何评估至少应明确：

- 研究问题和预先定义的假设；
- 数据范围、时间范围和数据来源；
- 样本筛选规则、缺失数据和排除原因；
- Baseline / Control Group；
- 对比组和唯一主要变量；
- 评价指标及计算定义；
- 样本量和样本独立性；
- 置信区间、统计不确定性和效应大小；
- 过拟合、选择偏差、幸存者偏差和数据泄漏风险；
- 失败案例及反例；
- 适用范围、不可外推范围和已知限制。

### 6.4 时间序列与交易研究特别规则

- 任何特征必须使用当时已经可获得的数据；
- 右侧确认的 Swing / Pivot 等结构，只能从确认时点之后用于决策或回测；
- 历史标签、阶段分类和统计窗口不得使用未来信息；
- 必须区分 Episode-level 与 Trade-level 统计；
- 同一市场阶段内的多笔交易可能相关，不得不加说明地视为独立样本；
- MFE / MAE 必须明确观察起点、观察期限、价格定义和成本处理；
- 比较方案时应控制入场信号、交易成本、风险预算、仓位计算和其他关键变量；
- 对照组和实验组不得因隐含参数差异而失去公平性；
- 结果应按 instrument、timeframe、regime 等适用维度拆分，避免总体均值掩盖局部失效。

### 6.5 统计结论规则

1. 报告样本量，不得只报告百分比。
2. 报告不确定性，不得把点估计写成确定事实。
3. 样本不足时，结论应为 Insufficient Evidence，而不是默认通过。
4. 结果不显著不等于证明无效；结果显著也不自动意味着具有实际价值。
5. 必须检查结果是否依赖少数品种、少数时期或少数极端样本。
6. 必须同时报告不利结果和失败案例。
7. 不得通过反复修改阈值直到结果好看，再将同一数据作为独立验证。
8. 任何参数选择与模型训练都应有独立验证或 walk-forward 设计。

### 6.6 评估结果分类

每次评估必须给出清晰结论之一：

- **PASS：** 达到预先定义的验收标准；
- **FAIL：** 关键标准未达到，或发现不可接受的问题；
- **INSUFFICIENT EVIDENCE：** 数据、样本或测试不足以作出判断；
- **INCONCLUSIVE：** 证据存在冲突或结果不稳定，需要进一步研究；
- **NOT APPLICABLE：** 该项评估确实不适用，并说明理由。

PASS 只代表对应评估范围通过，不自动授权进入交易决策或生产执行。

### 6.7 阶段输出

- Validation Plan
- Baseline & Dataset Description
- Historical / Walk-forward / Shadow Reports
- Statistical Evidence
- Failure & Error Analysis
- Limitations / Confidence Assessment
- Evaluation Verdict

### 6.8 进入下一层的门槛

评估范围、证据质量、样本限制和结论已经清晰呈现。若证据不足或结果不稳定，可以继续 Shadow 或返回设计阶段，不得强制给出 Go。

---

## 7. 第五层：Decision & Operational Architecture

## 决策与运营架构

### 7.1 目标

将评估证据转化为正式的晋级、维持、拒绝或回滚决定，并确保已发布功能持续处于受控状态。

### 7.2 评估与决策必须分离

- **Evaluation** 回答：“证据显示了什么？”
- **Decision** 回答：“基于这些证据，我们授权做什么？”

评估报告不得自行赋予功能交易权限。任何从 Observer 到 Advisor、从 Advisor 到 Execution、从 Shadow 到 Live 的升级，都必须有单独的决策记录。

### 7.3 决策选项

每个功能在评估后应明确选择：

- **GO — Approved：** 批准进入指定的下一阶段；
- **CONDITIONAL GO：** 满足明确限制和附加条件后批准；
- **CONTINUE SHADOW：** 继续收集证据，不改变交易行为；
- **REVISE：** 返回设计或工程阶段修订；
- **NO-GO：** 拒绝当前方案；
- **RETIRE：** 停止维护或正式废弃。

INSUFFICIENT EVIDENCE 不得自动转换为 GO。

### 7.4 晋级路径

功能权限应逐级提升，不得跳级：

```text
Research / Offline
        ↓
Read-only Observer
        ↓
Shadow
        ↓
Advisor Input (approved, non-executing)
        ↓
Controlled Decision Influence
        ↓
Limited Live Validation
        ↓
Production
```

并非每个功能都需要或应该走到 Production。某些功能的合理终点可以是研究工具、诊断指标或只读观测模块。

每次晋级必须明确：

- 被批准的具体功能和版本；
- 允许影响的对象与范围；
- 不允许影响的行为；
- 账户、品种、时间周期和运行环境范围；
- 风险限制和 Kill Switch；
- 监控指标、告警阈值和负责人；
- 回滚触发条件与执行方式；
- 批准依据和批准时间。

### 7.5 生产监控

上线后持续监控：

- 数据完整性、延迟、缺失和异常分布；
- 计算结果与历史基线的偏移；
- 状态转换频率及异常跳转；
- 模型、特征和市场环境漂移；
- Advisor 输入输出的一致性；
- 执行结果与授权行为是否一致；
- 错误率、重试、重复动作和幂等性；
- 实际表现是否偏离评估阶段的适用范围。

监控异常不应被简单地解释为市场噪声。必须保留证据并调查根因。

### 7.6 回滚与暂停

出现以下情况时，应按已批准的运行策略暂停、降级或回滚：

- 数据源或关键字段不可信；
- 观测或计算结果无法复现；
- 发生未经授权的行为或跨模块副作用；
- 关键风险限制失效；
- 生产行为明显偏离已批准设计；
- 监控指标触发预定义的异常条件；
- 新证据推翻原有核心假设。

回滚应恢复到最近一个已批准且可验证的稳定版本。回滚本身也必须记录原因、时间、影响和后续调查任务。

### 7.7 阶段输出

- Go / No-Go Decision
- Release Approval
- Deployment Scope
- Monitoring & Alert Plan
- Kill Switch / Rollback Plan
- Production Review
- Follow-up Research Items

---

## 8. 跨阶段不可违反的总原则

以下原则适用于所有模块、所有开发阶段和所有工具：

### 8.1 证据优先

- Findings 与 Hypotheses 必须分开。
- 事实必须能指出来源或复现方法。
- 不得为了支持预期结论而选择性呈现数据。
- 发现与预期相反时，应保留并调查，不得忽略。

### 8.2 Observation ≠ Decision ≠ Execution

记录、计算、分类、评分和预测都不自动构成决策，更不自动构成执行授权。

### 8.3 先观测，再验证，再授权

新功能默认从 Read-only / Shadow 开始。只有经过明确评估和正式决策，才可逐步扩大权限。

### 8.4 最小变更与范围控制

- 每次任务只解决已批准的问题；
- 不进行未经批准的交易逻辑、API、风险控制或执行行为重构；
- 不以顺手清理为由引入无关变更；
- 发现额外问题时，单独记录并提出任务。

### 8.5 可复现与可审计

关键结论必须能够追溯到数据、时间、配置、计算版本、代码版本和测试结果。无法复现的结果不能作为晋级的唯一依据。

### 8.6 诚实处理未知

- Missing 不等于 Zero；
- Calculated 不等于 Confirmed；
- Correlation 不等于 Causation；
- Backtest 不等于 Live Performance；
- High Probability 不等于 High Opportunity；
- More Touches 不必然代表更强结构；
- More Indicators 不必然代表更高准确度；
- PASS 不等于获得所有运行权限。

### 8.7 允许失败与停止

项目可以得出假设不成立、方案不可行、收益不足或证据不足的结论。拒绝一个缺乏证据的方案，是有效的工程与研究结果，不是开发失败。

---

## 9. 变更治理与偏差审批

### 9.1 哪些情况必须触发讨论

以下情况必须进行正式讨论，不得由实施者自行决定：

- 改变五层生命周期或其阶段门槛；
- 改变模块职责、数据权威来源或接口边界；
- 将 Shadow / Observer 功能升级为 Advisor 或 Execution 输入；
- 改变交易 Entry / Exit / SL / TP / Position Sizing / 风险控制行为；
- 改变外部 API 的调用方式、账户写入范围或运行权限；
- 改变关键数据定义、标签、计算公式、时间语义或版本兼容策略；
- 删除、绕过或弱化既有保护机制；
- 以新的综合评分或阈值取代原有观测定义；
- 改变评估方法、基线、主要指标或晋级标准；
- 任何与本文件明确原则不一致的提案。

### 9.2 偏差提案模板

提出偏差时，至少提交：

| 项目               | 内容                                 |
| ------------------ | ------------------------------------ |
| Reference          | 对应的本文件章节或现行规范           |
| Current Rule       | 当前批准规则                         |
| Proposed Deviation | 建议偏差                             |
| Reason             | 为什么需要偏差                       |
| Evidence           | 支持偏差的事实和数据                 |
| Risks              | 潜在风险和副作用                     |
| Alternatives       | 其他可行方案                         |
| Impact             | 对设计、工程、开发、评估、运营的影响 |
| Reversibility      | 是否可回滚，如何回滚                 |
| Recommendation     | 建议接受、拒绝或继续研究             |

### 9.3 决议记录

讨论结束后，记录：

- Decision ID；
- 日期；
- 讨论主题；
- 参与审查者；
- 采用的决定；
- 决定理由和证据；
- 受影响的文件、模块和版本；
- 后续任务；
- 是否需要更新本文件。

没有明确决议的讨论，不视为规范变更。

### 9.4 本文件修订

本文件只能在明确讨论并批准后修订。每次修订必须更新版本记录，并说明：

- 修改章节；
- 修改前后的规则；
- 修改原因；
- 支持证据；
- 对现有模块和开发中任务的影响；
- 是否需要迁移、回归或重新评估。

不得通过局部任务文档、代码注释或单次 LLM 输出，悄悄改变本文件的最高层原则。

---

## 10. 项目与模块的标准生命周期清单

每个新模块、重大功能或行为变更都应按以下清单检查。并非每个小型维护任务都需要重复编写全部文档，但必须能说明哪些项目适用、哪些不适用及原因。

### A. Design

- [ ] 问题和研究目标明确
- [ ] Findings、Hypotheses、Unknowns 分离
- [ ] 设计定义可观测、可复现、可证伪
- [ ] Scope / Non-goals 明确
- [ ] Success / Failure Criteria 明确
- [ ] 设计评审和版本记录完成

### B. Engineering

- [ ] 模块职责和禁止职责明确
- [ ] 数据来源、时间语义和字段定义明确
- [ ] 公式、单位、缺失值和边界行为明确
- [ ] ID、Schema、Calculation Version 明确
- [ ] 接口和调用方向明确
- [ ] Shadow / Advisor / Execution 权限边界明确
- [ ] 日志、审计和失败处理明确

### C. Development

- [ ] 修改前状态和基线已保存
- [ ] Task Scope 和禁止修改范围明确
- [ ] 实施与批准设计一致
- [ ] Unit / Contract / Integration Tests 完成
- [ ] Regression Tests 完成
- [ ] Shadow / Dry-run 验证完成（适用时）
- [ ] Code Review 完成
- [ ] 变更、提交和测试证据可追溯

### D. Evaluation

- [ ] 评估方案和指标预先定义
- [ ] Baseline / Control Group 明确
- [ ] 数据质量和样本量已报告
- [ ] Look-ahead / Leakage / Bias 已检查
- [ ] Historical / Out-of-sample / Shadow 验证按适用性完成
- [ ] 不确定性、失败案例和局限性已报告
- [ ] 给出 PASS / FAIL / INSUFFICIENT EVIDENCE / INCONCLUSIVE 等结论

### E. Decision & Operations

- [ ] Evaluation 与 Release Decision 分离
- [ ] Go / No-Go 决议明确
- [ ] 晋级范围和权限明确
- [ ] 监控、告警和 Kill Switch 明确
- [ ] 回滚条件与步骤明确
- [ ] 上线后复查计划明确
- [ ] 新发现已进入后续研究或设计任务

---

## 11. 标准交付物目录建议

建议按项目实际情况组织文件，不要求每个模块都创建空文件：

```text
docs/
├── Development_plan.md              # 本文件：全生命周期最高层规范
├── architecture/
│   ├── system_architecture.md
│   ├── module_boundaries.md
│   ├── data_schema.md
│   └── runtime_permissions.md
├── design/
│   └── <module>_design.md
├── development/
│   ├── implementation_plan.md
│   └── task_specs/
├── validation/
│   ├── validation_plan.md
│   └── reports/
├── operations/
│   ├── release_decisions.md
│   ├── monitoring_plan.md
│   └── rollback_plan.md
└── decisions/
    └── decision_log.md
```

目录结构可以根据仓库现状调整；目录名称不是强制接口。重要的是文档职责、内容和追溯关系不能丢失。

---

## 12. 版本记录

| Version | Date       | Change                                                           |
| ------- | ---------- | ---------------------------------------------------------------- |
| 1.0     | 2026-11-02 | 建立五层全生命周期治理框架、阶段门槛、偏差讨论机制和跨阶段原则。 |

---

## 13. 最终治理声明

本文件的目的不是增加流程负担，也不是要求每个小改动都进行繁复审批；其目的是防止研究假设未经验证就变成交易规则，防止工程实现悄悄改变系统行为，防止测试通过被误认为策略有效，以及防止生产权限在缺乏证据和授权的情况下逐步扩大。

**任何偏差都可以提出；任何规则都可以在充分证据和明确讨论后修订；但任何偏差都不得未经讨论就自动成为新规则。**

在没有正式决议之前，遵循当前已批准的架构、范围和运行边

Development Plan — 全生命周期最高层开发参考规范

> **文档级别：** 项目全生命周期最高层参考规范（Top-Level Development Governance）
>
> **适用范围：** 本项目及其后续新增、重构、扩展的所有研究模块、观测模块、策略模块、工程组件和生产运行功能。
>
> **核心原则：** 本文档定义开发生命周期的治理框架、阶段边界、决策门槛与变更规则。任何具体设计、实现或流程若与本文档存在偏差，必须先明确偏差并进行讨论；未经讨论和明确决定，不得自行将偏差视为新规则，也不得静默修改本文档或既有架构。

---

1. 文档目的与权威性
   本文件是整个开发生命周期的最高层参考文件，用于统一：
   设计与研究如何提出、审查和演进；
   系统工程如何划分模块、数据、接口与运行边界；
   开发如何分阶段实施、审查、测试和交付；
   结果如何通过历史数据、Shadow 运行和统计评估验证；
   何时以及依据什么证据，允许功能进入 Advisor、交易决策或生产运行；
   已发布功能如何持续监控、审查、回滚和迭代。
   本文件不是某个单独功能的技术设计，也不是具体代码实现说明。具体模块可以拥有自己的设计规范、接口文档、测试计划和实施任务，但这些下层文件必须与本文件保持一致。
   1.1 规范优先级
   发生规范冲突时，按以下顺序处理：
   明确讨论后批准的项目级决议或本文件正式修订；
   本文件当前有效版本；
   经批准的系统/模块架构规范；
   经批准的开发任务与实现规范；
   代码、注释、默认参数及工具生成的建议。
   代码已经存在，不代表其设计天然正确；某项实现已经上线，也不代表它自动成为新的架构标准。
   1.2 偏差处理原则
   发现任何偏差时：
   先记录事实：具体条款、当前实现/提案、差异及影响范围；
   区分事实、推测、风险和建议，不得混写；
   分析偏差产生的原因、收益、代价及潜在副作用；
   讨论是否接受偏差、修正实现，或正式修订规范；
   形成明确决定、理由、责任人及版本记录。
   在讨论和决定完成前，默认维持现行已批准规范。 不得因为某个工具、LLM、开发者或代码实现提出了不同做法，就自动改变既有原则。

---

2. 总体开发治理模型：五层生命周期
   所有功能和模块必须遵循以下五层生命周期：
   Design & Evolution Architecture — 设计与演进架构
   System Engineering Architecture — 系统工程架构
   Development & Implementation Architecture — 开发与实施架构
   Validation & Evaluation Architecture — 验证与评估架构
   Decision & Operational Architecture — 决策与运营架构

```text
┌──────────────────────────────────────────────┐
│ 1. DESIGN & EVOLUTION                        │
│ Research question / hypotheses / definitions│
└──────────────────────┬───────────────────────┘
                       ↓
┌──────────────────────────────────────────────┐
│ 2. SYSTEM ENGINEERING                        │
│ Boundaries / data / interfaces / runtime     │
└──────────────────────┬───────────────────────┘
                       ↓
┌──────────────────────────────────────────────┐
│ 3. DEVELOPMENT & IMPLEMENTATION              │
│ Tasks / coding / tests / review / release     │
└──────────────────────┬───────────────────────┘
                       ↓
┌──────────────────────────────────────────────┐
│ 4. VALIDATION & EVALUATION                   │
│ Historical / shadow / statistical evidence   │
└──────────────────────┬───────────────────────┘
                       ↓
┌──────────────────────────────────────────────┐
│ 5. DECISION & OPERATIONS                     │
│ Go / No-Go / controlled rollout / monitoring│
└──────────────────────┬───────────────────────┘
                       │
             New evidence / issues
                       └──────────→ 回到 Design
```

五层是治理与生命周期阶段，不是五个必须对应为独立 Python package、类或服务的代码模块。具体工程实现可以按合理方式组织，但不得因此省略任何治理阶段。
2.1 生命周期不是单向瀑布流程
五层之间存在反馈循环：
设计阶段发现定义不清，可以返回研究问题；
工程阶段发现数据不可获得或接口不可靠，可以退回设计；
开发阶段发现实现不可测试或边界冲突，可以退回工程设计；
评估阶段发现假设不成立、样本不足或结果不稳定，可以继续 Shadow、重新设计或终止；
运营阶段发现漂移、异常或性能退化，可以暂停、回滚并重新进入设计与评估。
不得为了完成计划而强行推进到下一阶段。
2.2 Evidence & Governance：贯穿五层的横切原则
证据与治理不是只在评估阶段才出现的工作，而是贯穿整个生命周期：
阶段	必须保留的证据
Design	问题定义、假设、依据、反例、未知项、版本变更理由
Engineering	数据来源、字段定义、计算规则、接口契约、边界和失败模式
Development	代码变更、测试结果、审查记录、提交与发布版本
Evaluation	数据覆盖、样本量、基线、统计结果、置信区间、失败案例
Decision & Operations	Go/No-Go 理由、发布授权、监控指标、异常记录、回滚记录
任何结论都应能追溯到输入数据、计算版本、代码版本和决策记录。
------------------------------------------------------------

3. 第一层：Design & Evolution Architecture
   设计与演进架构
   3.1 目标
   在编写代码之前，明确“要研究或解决什么问题、为什么值得做、如何定义成功或失败”。
   3.2 必须定义的内容
   每项新功能或重大修改至少应明确：
   Problem Statement： 当前具体问题是什么；
   Research Question： 希望回答什么问题；
   Hypothesis： 待验证的假设是什么；
   Evidence： 已有数据或事实支持什么；
   Unknowns： 哪些内容尚未得到证实；
   Alternatives： 是否存在更简单或风险更低的方案；
   Success Criteria： 什么结果支持该假设；
   Failure Criteria： 什么结果会否定该假设；
   Scope & Non-goals： 本轮包含什么、不包含什么；
   Limitations： 已知限制和潜在偏差。
   3.3 设计与演进规则
   不得将未经验证的假设写成事实。
   不得为了让方案看起来完整而虚构阶段、分数、概率或精确阈值。
   多个 LLM 或开发工具的意见属于审查输入，不构成自动批准。
   不同意见必须列出依据、分歧点和可验证方式。
   新版本必须说明相对上一版本改变了什么、为什么改变、影响哪些下层规范。
   定义应尽可能可观测、可复现、可证伪。
   如果研究目标尚不清楚，应先澄清问题，不应直接进入编码。
   3.4 阶段输出
   Design Specification
   Research Questions & Hypotheses
   Scope / Non-goals
   Success & Failure Criteria
   Design Review / Decision Log
   Version History
   3.5 进入下一层的门槛
   研究目标、核心定义、范围和验收方向已经足够明确，可以设计数据与工程边界。若关键概念仍存在未解决歧义，应先讨论，不得用临时代码掩盖定义问题。

---

4. 第二层：System Engineering Architecture
   系统工程架构
   4.1 目标
   将已批准的设计转化为边界清晰、数据可追溯、接口明确、运行行为可控的系统方案。
   4.2 必须定义的内容
   模块职责、输入、输出及禁止承担的职责；
   数据来源、权威来源、时间语义和更新频率；
   字段名称、类型、单位、精度、缺失值语义；
   计算公式、参数、窗口、确认条件和边界行为；
   ID、状态、版本和关联关系；
   模块接口及调用方向；
   日志、存储、审计和数据保留策略；
   异常处理、失败关闭（fail-closed）或降级行为；
   Shadow、Advisor、Execution 等运行模式之间的隔离；
   性能、可靠性、安全性和可观测性要求。
   4.3 模块边界原则
   单一职责： 观测、研究、决策和执行职责应清晰分离。
   数据与行为分离： 计算出某个值，不代表系统已确认某个事实或获准执行动作。
   模块独立： 不同研究维度应保留各自原始定义，不应为了方便而混成一个未经验证的综合分数。
   接口显式： 不得依赖隐式全局状态、隐式副作用或不透明的跨模块修改。
   可追溯： 关键数据应能追溯到来源、时间、计算版本和代码版本。
   缺失值诚实表达： Missing / Invalid / Not Available 不得静默替换为 0 或正常值。
   确定性： 相同输入和相同计算版本，在定义范围内应产生可复现结果。
   向后兼容： Schema 或接口变更必须评估旧数据、旧调用方和部署顺序。
   4.4 观测、决策与执行的边界
   默认架构边界：

```text
Market / Broker / Historical Data
              ↓
       Data & Observation
              ↓
     Research / Feature Layer
              ↓
          Advisor
              ↓
        Execution Layer
              ↓
        Broker API
```

Observation 负责记录和计算，不应直接提交交易指令。
Research / Feature Layer 负责形成可研究的特征，不自动获得交易权限。
Advisor 可以消费已批准的数据和规则，但必须遵守明确的决策接口。
Execution 负责执行已授权的动作，不应暗中重新解释研究指标。
任何跨层权限变化都属于架构变更，必须讨论并批准。
对于 OANDA 相关运行组件，Broker API 的实时状态应作为账户、交易和持仓状态的权威来源；不得未经批准以本地缓存或恢复文件覆盖经纪商事实。任何自动化组件的账户写入范围、标签归属和幂等规则必须在对应工程规范中明确。
4.5 版本与数据治理
关键观测记录至少应在适用时包含：
`schema_version`
`calculation_version`
`source_timestamp`
`observed_at`
`instrument`
`timeframe`
`data_source`
`validity_status`
`reason_code` 或错误说明
观测记录、事后汇总和交易结果应分开保存。不得静默覆盖历史观测；更正应保留可追溯记录。
4.6 阶段输出
Technical Architecture
Module Responsibility Matrix
Data Schema / Data Dictionary
Interface Specification
Runtime & Permission Boundaries
Logging / Storage / Versioning Specification
Failure-mode & Recovery Design
4.7 进入下一层的门槛
模块边界、数据契约、接口、运行模式和失败行为已明确；关键数据可获得且可验证；不存在未经讨论的职责越界。
------------------------------------------------------------------------------------------------------

5. 第三层：Development & Implementation Architecture
   开发与实施架构
   5.1 目标
   将批准的工程设计分解为范围受控、可审查、可测试、可回滚的实施任务。
   5.2 开发顺序
   原则上按以下顺序实施：
   Read-only inspection：检查现有代码、调用链、数据和历史行为；
   Baseline capture：保存修改前行为、日志、测试和相关指标；
   Instrumentation：先补充必要观测与审计能力；
   Minimal implementation：只实现当前任务批准的最小范围；
   Unit / contract tests：验证公式、接口、字段和边界；
   Integration tests：验证模块之间的真实调用关系；
   Regression tests：确认既有行为没有非预期变化；
   Shadow / dry-run verification：在不产生真实副作用的模式下验证；
   Code review：检查逻辑、范围、风险、可维护性和测试证据；
   Controlled release：只有满足发布门槛后才可发布。
   5.3 任务规范
   每个开发任务必须明确：
   Task ID 与优先级（P0 / P1 / P2）；
   目标和具体问题；
   允许修改的文件、模块和接口；
   明确禁止修改的范围；
   预期行为及验收标准；
   测试命令与预期结果；
   风险和回滚方式；
   是否允许改变运行行为；
   是否允许调用外部 API、修改账户状态或产生真实交易副作用。
   不得将多个无关目标塞入同一任务。若实施中发现任务范围不足或设计缺陷，应暂停并提出变更，不得自行扩大范围。
   5.4 默认安全边界
   除非另有明确批准：
   新功能默认 Read-only / Shadow / Diagnostic；
   新交易行为、自动执行开关和真实账户写入默认关闭；
   不得在观测任务中顺带修改 Entry、Exit、SL、TP、Position Sizing、风险限制或执行流程；
   不得以“重构顺便清理”为理由进行无关行为变更；
   不得删除或弱化既有保护机制，除非有独立证据、明确任务和批准；
   不得把日志输出、计算结果或测试通过误报为生产行为已生效。
   5.5 测试与审查原则
   测试必须对应明确的行为或不变量；
   不能只测试理想路径，还要覆盖缺失数据、异常输入、边界值、重复调用和失败路径；
   对时间序列和历史研究，必须检查时间对齐、未来数据泄漏、重复样本和窗口重叠；
   对状态机，必须检查状态转换、重复确认、重启恢复和异常跳转；
   对外部 API，必须区分本地模拟、dry-run 和真实请求；
   测试结果必须说明实际执行了什么，不能只列计划执行的命令。
   5.6 阶段输出
   Implementation Plan
   Scoped Task Specification
   Code Changes / Commit References
   Test & Regression Report
   Code Review Findings
   Shadow / Dry-run Evidence
   Release Candidate
   5.7 进入下一层的门槛
   实现与批准的设计一致；任务范围未被静默扩大；测试、回归和审查证据完整；已知缺陷与限制明确。仅仅“代码可以运行”不构成通过标准。

---

6. 第四层：Validation & Evaluation Architecture
   验证与评估架构
   6.1 目标
   判断实现是否正确，以及研究假设是否得到数据支持。必须区分：
   Implementation Correctness： 代码是否按规范工作；
   Measurement Validity： 测量和数据是否可信；
   Hypothesis Validity： 研究假设是否得到支持；
   Operational Effectiveness： 在真实运行约束下是否有效。
   这四者不能互相替代。代码正确不代表假设正确；指标相关不代表具备预测价值；回测盈利不代表生产可执行。
   6.2 验证层次
   按适用性组合使用：
   Unit / Contract Validation： 公式、字段、接口和边界；
   Historical Validation： 历史数据上的可复现性和分布；
   Out-of-sample / Walk-forward： 检验样本外稳定性；
   Shadow Validation： 实时数据下只观测、不改变交易行为；
   Controlled Experiment： 在严格控制变量和风险预算下比较方案；
   Production Validation： 经批准的小范围上线后持续验证。
   6.3 评估设计要求
   任何评估至少应明确：
   研究问题和预先定义的假设；
   数据范围、时间范围和数据来源；
   样本筛选规则、缺失数据和排除原因；
   Baseline / Control Group；
   对比组和唯一主要变量；
   评价指标及计算定义；
   样本量和样本独立性；
   置信区间、统计不确定性和效应大小；
   过拟合、选择偏差、幸存者偏差和数据泄漏风险；
   失败案例及反例；
   适用范围、不可外推范围和已知限制。
   6.4 时间序列与交易研究特别规则
   任何特征必须使用当时已经可获得的数据；
   右侧确认的 Swing / Pivot 等结构，只能从确认时点之后用于决策或回测；
   历史标签、阶段分类和统计窗口不得使用未来信息；
   必须区分 Episode-level 与 Trade-level 统计；
   同一市场阶段内的多笔交易可能相关，不得不加说明地视为独立样本；
   MFE / MAE 必须明确观察起点、观察期限、价格定义和成本处理；
   比较方案时应控制入场信号、交易成本、风险预算、仓位计算和其他关键变量；
   对照组和实验组不得因隐含参数差异而失去公平性；
   结果应按 instrument、timeframe、regime 等适用维度拆分，避免总体均值掩盖局部失效。
   6.5 统计结论规则
   报告样本量，不得只报告百分比。
   报告不确定性，不得把点估计写成确定事实。
   样本不足时，结论应为 Insufficient Evidence，而不是默认通过。
   结果不显著不等于证明无效；结果显著也不自动意味着具有实际价值。
   必须检查结果是否依赖少数品种、少数时期或少数极端样本。
   必须同时报告不利结果和失败案例。
   不得通过反复修改阈值直到结果好看，再将同一数据作为独立验证。
   任何参数选择与模型训练都应有独立验证或 walk-forward 设计。
   6.6 评估结果分类
   每次评估必须给出清晰结论之一：
   PASS： 达到预先定义的验收标准；
   FAIL： 关键标准未达到，或发现不可接受的问题；
   INSUFFICIENT EVIDENCE： 数据、样本或测试不足以作出判断；
   INCONCLUSIVE： 证据存在冲突或结果不稳定，需要进一步研究；
   NOT APPLICABLE： 该项评估确实不适用，并说明理由。
   PASS 只代表对应评估范围通过，不自动授权进入交易决策或生产执行。
   6.7 阶段输出
   Validation Plan
   Baseline & Dataset Description
   Historical / Walk-forward / Shadow Reports
   Statistical Evidence
   Failure & Error Analysis
   Limitations / Confidence Assessment
   Evaluation Verdict
   6.8 进入下一层的门槛
   评估范围、证据质量、样本限制和结论已经清晰呈现。若证据不足或结果不稳定，可以继续 Shadow 或返回设计阶段，不得强制给出 Go。

---

7. 第五层：Decision & Operational Architecture
   决策与运营架构
   7.1 目标
   将评估证据转化为正式的晋级、维持、拒绝或回滚决定，并确保已发布功能持续处于受控状态。
   7.2 评估与决策必须分离
   Evaluation 回答：“证据显示了什么？”
   Decision 回答：“基于这些证据，我们授权做什么？”
   评估报告不得自行赋予功能交易权限。任何从 Observer 到 Advisor、从 Advisor 到 Execution、从 Shadow 到 Live 的升级，都必须有单独的决策记录。
   7.3 决策选项
   每个功能在评估后应明确选择：
   GO — Approved： 批准进入指定的下一阶段；
   CONDITIONAL GO： 满足明确限制和附加条件后批准；
   CONTINUE SHADOW： 继续收集证据，不改变交易行为；
   REVISE： 返回设计或工程阶段修订；
   NO-GO： 拒绝当前方案；
   RETIRE： 停止维护或正式废弃。
   INSUFFICIENT EVIDENCE 不得自动转换为 GO。
   7.4 晋级路径
   功能权限应逐级提升，不得跳级：

```text
Research / Offline
        ↓
Read-only Observer
        ↓
Shadow
        ↓
Advisor Input (approved, non-executing)
        ↓
Controlled Decision Influence
        ↓
Limited Live Validation
        ↓
Production
```

并非每个功能都需要或应该走到 Production。某些功能的合理终点可以是研究工具、诊断指标或只读观测模块。
每次晋级必须明确：
被批准的具体功能和版本；
允许影响的对象与范围；
不允许影响的行为；
账户、品种、时间周期和运行环境范围；
风险限制和 Kill Switch；
监控指标、告警阈值和负责人；
回滚触发条件与执行方式；
批准依据和批准时间。
7.5 生产监控
上线后持续监控：
数据完整性、延迟、缺失和异常分布；
计算结果与历史基线的偏移；
状态转换频率及异常跳转；
模型、特征和市场环境漂移；
Advisor 输入输出的一致性；
执行结果与授权行为是否一致；
错误率、重试、重复动作和幂等性；
实际表现是否偏离评估阶段的适用范围。
监控异常不应被简单地解释为市场噪声。必须保留证据并调查根因。
7.6 回滚与暂停
出现以下情况时，应按已批准的运行策略暂停、降级或回滚：
数据源或关键字段不可信；
观测或计算结果无法复现；
发生未经授权的行为或跨模块副作用；
关键风险限制失效；
生产行为明显偏离已批准设计；
监控指标触发预定义的异常条件；
新证据推翻原有核心假设。
回滚应恢复到最近一个已批准且可验证的稳定版本。回滚本身也必须记录原因、时间、影响和后续调查任务。
7.7 阶段输出
Go / No-Go Decision
Release Approval
Deployment Scope
Monitoring & Alert Plan
Kill Switch / Rollback Plan
Production Review
Follow-up Research Items
------------------------

8. 跨阶段不可违反的总原则
   以下原则适用于所有模块、所有开发阶段和所有工具：
   8.1 证据优先
   Findings 与 Hypotheses 必须分开。
   事实必须能指出来源或复现方法。
   不得为了支持预期结论而选择性呈现数据。
   发现与预期相反时，应保留并调查，不得忽略。
   8.2 Observation ≠ Decision ≠ Execution
   记录、计算、分类、评分和预测都不自动构成决策，更不自动构成执行授权。
   8.3 先观测，再验证，再授权
   新功能默认从 Read-only / Shadow 开始。只有经过明确评估和正式决策，才可逐步扩大权限。
   8.4 最小变更与范围控制
   每次任务只解决已批准的问题；
   不进行未经批准的交易逻辑、API、风险控制或执行行为重构；
   不以顺手清理为由引入无关变更；
   发现额外问题时，单独记录并提出任务。
   8.5 可复现与可审计
   关键结论必须能够追溯到数据、时间、配置、计算版本、代码版本和测试结果。无法复现的结果不能作为晋级的唯一依据。
   8.6 诚实处理未知
   Missing 不等于 Zero；
   Calculated 不等于 Confirmed；
   Correlation 不等于 Causation；
   Backtest 不等于 Live Performance；
   High Probability 不等于 High Opportunity；
   More Touches 不必然代表更强结构；
   More Indicators 不必然代表更高准确度；
   PASS 不等于获得所有运行权限。
   8.7 允许失败与停止
   项目可以得出假设不成立、方案不可行、收益不足或证据不足的结论。拒绝一个缺乏证据的方案，是有效的工程与研究结果，不是开发失败。

---

9. 变更治理与偏差审批
   9.1 哪些情况必须触发讨论
   以下情况必须进行正式讨论，不得由实施者自行决定：
   改变五层生命周期或其阶段门槛；
   改变模块职责、数据权威来源或接口边界；
   将 Shadow / Observer 功能升级为 Advisor 或 Execution 输入；
   改变交易 Entry / Exit / SL / TP / Position Sizing / 风险控制行为；
   改变外部 API 的调用方式、账户写入范围或运行权限；
   改变关键数据定义、标签、计算公式、时间语义或版本兼容策略；
   删除、绕过或弱化既有保护机制；
   以新的综合评分或阈值取代原有观测定义；
   改变评估方法、基线、主要指标或晋级标准；
   任何与本文件明确原则不一致的提案。
   9.2 偏差提案模板
   提出偏差时，至少提交：
   项目	内容
   Reference	对应的本文件章节或现行规范
   Current Rule	当前批准规则
   Proposed Deviation	建议偏差
   Reason	为什么需要偏差
   Evidence	支持偏差的事实和数据
   Risks	潜在风险和副作用
   Alternatives	其他可行方案
   Impact	对设计、工程、开发、评估、运营的影响
   Reversibility	是否可回滚，如何回滚
   Recommendation	建议接受、拒绝或继续研究
   9.3 决议记录
   讨论结束后，记录：
   Decision ID；
   日期；
   讨论主题；
   参与审查者；
   采用的决定；
   决定理由和证据；
   受影响的文件、模块和版本；
   后续任务；
   是否需要更新本文件。
   没有明确决议的讨论，不视为规范变更。
   9.4 本文件修订
   本文件只能在明确讨论并批准后修订。每次修订必须更新版本记录，并说明：
   修改章节；
   修改前后的规则；
   修改原因；
   支持证据；
   对现有模块和开发中任务的影响；
   是否需要迁移、回归或重新评估。
   不得通过局部任务文档、代码注释或单次 LLM 输出，悄悄改变本文件的最高层原则。

---

10. 项目与模块的标准生命周期清单
    每个新模块、重大功能或行为变更都应按以下清单检查。并非每个小型维护任务都需要重复编写全部文档，但必须能说明哪些项目适用、哪些不适用及原因。
    A. Design
    [ ] 问题和研究目标明确
    [ ] Findings、Hypotheses、Unknowns 分离
    [ ] 设计定义可观测、可复现、可证伪
    [ ] Scope / Non-goals 明确
    [ ] Success / Failure Criteria 明确
    [ ] 设计评审和版本记录完成
    B. Engineering
    [ ] 模块职责和禁止职责明确
    [ ] 数据来源、时间语义和字段定义明确
    [ ] 公式、单位、缺失值和边界行为明确
    [ ] ID、Schema、Calculation Version 明确
    [ ] 接口和调用方向明确
    [ ] Shadow / Advisor / Execution 权限边界明确
    [ ] 日志、审计和失败处理明确
    C. Development
    [ ] 修改前状态和基线已保存
    [ ] Task Scope 和禁止修改范围明确
    [ ] 实施与批准设计一致
    [ ] Unit / Contract / Integration Tests 完成
    [ ] Regression Tests 完成
    [ ] Shadow / Dry-run 验证完成（适用时）
    [ ] Code Review 完成
    [ ] 变更、提交和测试证据可追溯
    D. Evaluation
    [ ] 评估方案和指标预先定义
    [ ] Baseline / Control Group 明确
    [ ] 数据质量和样本量已报告
    [ ] Look-ahead / Leakage / Bias 已检查
    [ ] Historical / Out-of-sample / Shadow 验证按适用性完成
    [ ] 不确定性、失败案例和局限性已报告
    [ ] 给出 PASS / FAIL / INSUFFICIENT EVIDENCE / INCONCLUSIVE 等结论
    E. Decision & Operations
    [ ] Evaluation 与 Release Decision 分离
    [ ] Go / No-Go 决议明确
    [ ] 晋级范围和权限明确
    [ ] 监控、告警和 Kill Switch 明确
    [ ] 回滚条件与步骤明确
    [ ] 上线后复查计划明确
    [ ] 新发现已进入后续研究或设计任务

---

11. 标准交付物目录建议
    建议按项目实际情况组织文件，不要求每个模块都创建空文件：

```text
docs/
├── Development_plan.md              # 本文件：全生命周期最高层规范
├── architecture/
│   ├── system_architecture.md
│   ├── module_boundaries.md
│   ├── data_schema.md
│   └── runtime_permissions.md
├── design/
│   └── <module>_design.md
├── development/
│   ├── implementation_plan.md
│   └── task_specs/
├── validation/
│   ├── validation_plan.md
│   └── reports/
├── operations/
│   ├── release_decisions.md
│   ├── monitoring_plan.md
│   └── rollback_plan.md
└── decisions/
    └── decision_log.md
```

目录结构可以根据仓库现状调整；目录名称不是强制接口。重要的是文档职责、内容和追溯关系不能丢失。
----------------------------------------------------------------------------------------------

12. 版本记录
    Version	Date	Change
    1.0	2026-11-02	建立五层全生命周期治理框架、阶段门槛、偏差讨论机制和跨阶段原则。

---

13. 最终治理声明
    本文件的目的不是增加流程负担，也不是要求每个小改动都进行繁复审批；其目的是防止研究假设未经验证就变成交易规则，防止工程实现悄悄改变系统行为，防止测试通过被误认为策略有效，以及防止生产权限在缺乏证据和授权的情况下逐步扩大。
    任何偏差都可以提出；任何规则都可以在充分证据和明确讨论后修订；但任何偏差都不得未经讨论就自动成为新规则。
    在没有正式决议之前，遵循当前已批准的架构、范围和运行边界

你的总结基本正确。我认为你已经把这个项目从单纯的 Forex Bot 功能开发，提升到了一个完整的量化研究与工程演进体系。

不过，我建议补充第 5 项，而且稍微调整一下五个部分之间的关系。

我理解我们现在正在建立的是以下五层架构。

# c

01

设计架构 — Design & Evolution Architecture

我们研究什么，以及为什么研究？

- 研究目标与问题定义
- 核心概念与理论假设
- 生命周期定义
- 设计评审与多 LLM 交叉讨论
- 版本迭代与设计变更记录

输出：Design Specification、Hypotheses、Version History

02

工程架构 — Engineering Architecture

系统应该如何组织？

- 模块划分与职责边界
- 数据结构与数据流
- 模块之间的接口
- Trend Lifecycle / Market Structure / Market Context
- Logging、Storage、ID、版本管理
- Shadow 与 Live 的隔离

输出：Technical Architecture、Data Schema、Interface Specification

03

开发架构 — Development Architecture

按什么顺序开发，如何保证不引入新问题？

- P0 / P1 / P2 优先级
- 分阶段实施
- 每个 Task 的严格边界
- Coding、Code Review、Testing
- Regression Test
- Git Branch / Commit / Release 管理

输出：Implementation Plan、Task Specification、Test Report

04

评估架构 — Evaluation Architecture

如何证明设计有效？

- 历史回测
- 实时 Shadow Observation
- A/B Testing
- Walk-forward Validation
- MFE / MAE / PnL
- Statistical Significance
- Baseline Comparison
- Failure Analysis

输出：Research Report、Statistical Evidence、Validation Result

05

决策与运营架构 — Decision & Operational Architecture

研究结果如何转化成实际系统能力？

- 是否接受研究假设？
- 是否允许进入 Advisor？
- 是否允许影响交易决策？
- 是否进入小规模 Live 验证？
- Performance Monitoring
- Model / Data Drift Monitoring
- 异常检测与回滚
- 版本升级和持续审查

输出：Go / No-Go Decision、Release Approval、Monitoring & Rollback Plan

# 六、五层之间的关系

这里有一个非常重要的区别：

这五项不是五个独立的工作包，而是一个持续循环。

\#chatgpt-mermaid-\_r_jq\_{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;fill:rgb(13, 13, 13);}@keyframes edge-animation-frame{from{stroke-dashoffset:0;}}@keyframes dash{to{stroke-dashoffset:0;}}#chatgpt-mermaid-\_r_jq\_ .edge-animation-slow{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 50s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-\_r_jq\_ .edge-animation-fast{stroke-dasharray:9,5!important;stroke-dashoffset:900;animation:dash 20s linear infinite;stroke-linecap:round;}#chatgpt-mermaid-\_r_jq\_ .error-icon{fill:rgb(243, 243, 243);}#chatgpt-mermaid-\_r_jq\_ .error-text{fill:rgb(13, 13, 13);stroke:rgb(13, 13, 13);}#chatgpt-mermaid-\_r_jq\_ .edge-thickness-normal{stroke-width:1px;}#chatgpt-mermaid-\_r_jq\_ .edge-thickness-thick{stroke-width:3.5px;}#chatgpt-mermaid-\_r_jq\_ .edge-pattern-solid{stroke-dasharray:0;}#chatgpt-mermaid-\_r_jq\_ .edge-thickness-invisible{stroke-width:0;fill:none;}#chatgpt-mermaid-\_r_jq\_ .edge-pattern-dashed{stroke-dasharray:3;}#chatgpt-mermaid-\_r_jq\_ .edge-pattern-dotted{stroke-dasharray:2;}#chatgpt-mermaid-\_r_jq\_ .marker{fill:rgb(143, 143, 143);stroke:rgb(143, 143, 143);}#chatgpt-mermaid-\_r_jq\_ .marker.cross{stroke:rgb(143, 143, 143);}#chatgpt-mermaid-\_r_jq\_ svg{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:16px;}#chatgpt-mermaid-\_r_jq\_ p{margin:0;}#chatgpt-mermaid-\_r_jq\_ .label{font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";color:rgb(13, 13, 13);}#chatgpt-mermaid-\_r_jq\_ .cluster-label text{fill:rgb(13, 13, 13);}#chatgpt-mermaid-\_r_jq\_ .cluster-label span{color:rgb(13, 13, 13);}#chatgpt-mermaid-\_r_jq\_ .cluster-label span p{background-color:transparent;}#chatgpt-mermaid-\_r_jq\_ .label text,#chatgpt-mermaid-\_r_jq\_ span{fill:rgb(13, 13, 13);color:rgb(13, 13, 13);}#chatgpt-mermaid-\_r_jq\_ .node rect,#chatgpt-mermaid-\_r_jq\_ .node circle,#chatgpt-mermaid-\_r_jq\_ .node ellipse,#chatgpt-mermaid-\_r_jq\_ .node polygon,#chatgpt-mermaid-\_r_jq\_ .node path{fill:rgb(222, 234, 251);stroke:rgb(83, 154, 248);stroke-width:1px;}#chatgpt-mermaid-\_r_jq\_ .rough-node .label text,#chatgpt-mermaid-\_r_jq\_ .node .label text,#chatgpt-mermaid-\_r_jq\_ .image-shape .label,#chatgpt-mermaid-\_r_jq\_ .icon-shape .label{text-anchor:middle;}#chatgpt-mermaid-\_r_jq\_ .node .katex path{fill:#000;stroke:#000;stroke-width:1px;}#chatgpt-mermaid-\_r_jq\_ .rough-node .label,#chatgpt-mermaid-\_r_jq\_ .node .label,#chatgpt-mermaid-\_r_jq\_ .image-shape .label,#chatgpt-mermaid-\_r_jq\_ .icon-shape .label{text-align:center;}#chatgpt-mermaid-\_r_jq\_ .node.clickable{cursor:pointer;}#chatgpt-mermaid-\_r_jq\_ .root .anchor path{fill:rgb(143, 143, 143)!important;stroke-width:0;stroke:rgb(143, 143, 143);}#chatgpt-mermaid-\_r_jq\_ .arrowheadPath{fill:rgb(143, 143, 143);}#chatgpt-mermaid-\_r_jq\_ .edgePath .path{stroke:rgb(143, 143, 143);stroke-width:1px;}#chatgpt-mermaid-\_r_jq\_ .flowchart-link{stroke:rgb(143, 143, 143);fill:none;}#chatgpt-mermaid-\_r_jq\_ .edgeLabel{background-color:rgb(252, 252, 252);text-align:center;}#chatgpt-mermaid-\_r_jq\_ .edgeLabel p{background-color:rgb(252, 252, 252);}#chatgpt-mermaid-\_r_jq\_ .edgeLabel rect{opacity:0.5;background-color:rgb(252, 252, 252);fill:rgb(252, 252, 252);}#chatgpt-mermaid-\_r_jq\_ .labelBkg{background-color:rgba(252, 252, 252, 0.5);}#chatgpt-mermaid-\_r_jq\_ .cluster rect{fill:rgb(243, 243, 243);stroke:rgba(0, 0, 0, 0.1);stroke-width:1px;}#chatgpt-mermaid-\_r_jq\_ .cluster text{fill:rgb(13, 13, 13);}#chatgpt-mermaid-\_r_jq\_ .cluster span{color:rgb(13, 13, 13);}#chatgpt-mermaid-\_r_jq\_ div.mermaidTooltip{position:absolute;text-align:center;max-width:200px;padding:2px;font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";font-size:12px;background:rgb(243, 243, 243);border:1px solid rgba(0, 0, 0, 0.1);border-radius:2px;pointer-events:none;z-index:100;}#chatgpt-mermaid-\_r_jq\_ .flowchartTitleText{text-anchor:middle;font-size:18px;fill:rgb(13, 13, 13);}#chatgpt-mermaid-\_r_jq\_ rect.text{fill:none;stroke-width:0;}#chatgpt-mermaid-\_r_jq\_ .icon-shape,#chatgpt-mermaid-\_r_jq\_ .image-shape{background-color:rgb(252, 252, 252);text-align:center;}#chatgpt-mermaid-\_r_jq\_ .icon-shape p,#chatgpt-mermaid-\_r_jq\_ .image-shape p{background-color:rgb(252, 252, 252);padding:2px;}#chatgpt-mermaid-\_r_jq\_ .icon-shape .label rect,#chatgpt-mermaid-\_r_jq\_ .image-shape .label rect{opacity:0.5;background-color:rgb(252, 252, 252);fill:rgb(252, 252, 252);}#chatgpt-mermaid-\_r_jq\_ .label-icon{display:inline-block;height:1em;overflow:visible;vertical-align:-0.125em;}#chatgpt-mermaid-\_r_jq\_ .node .label-icon path{fill:currentColor;stroke:revert;stroke-width:revert;}#chatgpt-mermaid-\_r_jq\_ .node .neo-node{stroke:rgb(83, 154, 248);}#chatgpt-mermaid-\_r_jq\_ [data-look="neo"].node rect,#chatgpt-mermaid-\_r_jq\_ [data-look="neo"].cluster rect,#chatgpt-mermaid-\_r_jq\_ [data-look="neo"].node polygon{stroke:url(#chatgpt-mermaid-\_r_jq\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_jq\_ [data-look="neo"].swimlane.cluster rect{filter:none;}#chatgpt-mermaid-\_r_jq\_ [data-look="neo"].node path{stroke:url(#chatgpt-mermaid-\_r_jq\_-gradient);stroke-width:1px;}#chatgpt-mermaid-\_r_jq\_ [data-look="neo"].node .outer-path{filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_jq\_ [data-look="neo"].node .neo-line path{stroke:rgb(83, 154, 248);filter:none;}#chatgpt-mermaid-\_r_jq\_ [data-look="neo"].node circle{stroke:url(#chatgpt-mermaid-\_r_jq\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_jq\_ [data-look="neo"].node circle .state-start{fill:#000000;}#chatgpt-mermaid-\_r_jq\_ [data-look="neo"].icon-shape .icon{fill:url(#chatgpt-mermaid-\_r_jq\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_jq\_ [data-look="neo"].icon-shape .icon-neo path{stroke:url(#chatgpt-mermaid-\_r_jq\_-gradient);filter:drop-shadow( 1px 2px 2px rgba(185,185,185,1));}#chatgpt-mermaid-\_r_jq\_ .node text{font-size:14px;font-weight:600;letter-spacing:normal;fill:rgb(0, 79, 153);}#chatgpt-mermaid-\_r_jq\_ .edgeLabels text{font-size:13px;font-weight:600;letter-spacing:-0.08px;fill:rgb(0, 79, 153);}#chatgpt-mermaid-\_r_jq\_ .node tspan[font-weight="normal"],#chatgpt-mermaid-\_r_jq\_ .edgeLabels tspan[font-weight="normal"]{font-weight:600;}#chatgpt-mermaid-\_r_jq\_ .edgeLabel .label rect{opacity:1;rx:13px;ry:13px;fill:rgb(245, 250, 255);stroke:rgb(206, 219, 229);stroke-width:1px;}#chatgpt-mermaid-\_r_jq\_ .node rect,#chatgpt-mermaid-\_r_jq\_ .node circle,#chatgpt-mermaid-\_r_jq\_ .node ellipse,#chatgpt-mermaid-\_r_jq\_ .node polygon,#chatgpt-mermaid-\_r_jq\_ .node path{fill:rgb(229, 243, 255);stroke:rgba(0, 0, 0, 0.1);stroke-width:1px;}#chatgpt-mermaid-\_r_jq\_ .node rect{rx:16px;ry:16px;}#chatgpt-mermaid-\_r_jq\_ .mermaid-decision .label-container{fill:rgb(245, 250, 255);stroke:rgb(206, 219, 229);stroke-dasharray:2,2;}#chatgpt-mermaid-\_r_jq\_ .edgePaths .flowchart-link{stroke:rgb(143, 143, 143);stroke-width:1px;stroke-linecap:round;stroke-linejoin:round;}#chatgpt-mermaid-\_r_jq\_ .marker{fill:rgb(143, 143, 143);stroke:rgb(143, 143, 143);}#chatgpt-mermaid-\_r_jq\_ :root{--mermaid-font-family:-apple-system-body,ui-sans-serif,-apple-system,system-ui,"Segoe UI",Helvetica,"Apple Color Emoji",Arial,sans-serif,"Segoe UI Emoji","Segoe UI Symbol";}01 Design & Evolution02 Engineering Architecture03 Development Architecture04 Evaluation Architecture05 Decision & OperationsControlled Integration / LiveProduction MonitoringApprovedRejected or Insufficient EvidenceNew findings / anomalies

例如，我们现在研究 Trend Lifecycle：

1. 设计层：定义趋势生命周期及其研究假设。
2. 工程层：设计 Trend ID、State Machine、Observation Schema。
3. 开发层：先实现 Observer，再实现 Logging 和测试。
4. 评估层：收集数据，研究不同阶段的 MFE、MAE。
5. 决策层：决定生命周期信息是否值得进入 Advisor。

如果评估不通过，就回到设计层重新研究，而不是继续增加交易规则。

# 七、我认为还应该贯穿五层的一项原则

Evidence & Governance（证据与治理）

它不一定需要成为第六个独立架构，但应该贯穿全部五层。

例如：

| 阶段        | 必须回答的问题         |
| ----------- | ---------------------- |
| Design      | 这个假设有什么依据？   |
| Engineering | 计算是否可以复现？     |
| Development | 修改是否经过验证？     |
| Evaluation  | 结果是否有统计支持？   |
| Decision    | 什么证据允许系统升级？ |

特别是 Decision 阶段，不能因为某次回测表现不错，就直接进入 Live。

应该有明确的 Promotion Criteria 和 Rollback Criteria。

这也符合我们一直坚持的 Shadow-first、Audit-first 原则。

# 八、我的最终建议

我建议正式把这五项定义为：

| 编号 | 中文名称       | 英文名称                                  |
| ---- | -------------- | ----------------------------------------- |
| 1    | 设计与演进架构 | Design & Evolution Architecture           |
| 2    | 系统工程架构   | System Engineering Architecture           |
| 3    | 开发与实施架构 | Development & Implementation Architecture |
| 4    | 验证与评估架构 | Validation & Evaluation Architecture      |
| 5    | 决策与运营架构 | Decision & Operational Architecture       |

还有一点值得强调：

这五层应该成为所有新功能的统一开发标准，而不只是 Trend Lifecycle 项目的专用流程。

未来无论是：

- Trend Lifecycle
- Market Structure
- Remaining Opportunity
- CNN Model
- JPY Composite
- Monte Carlo Regime
- SL/TP Guardian

都应该遵循同一套五层架构。

这样我们最终建立的就不只是一个 Forex Bot，而是一套可以持续研究、验证、升级和审计的量化交易系统。

我认为这才是这轮架构讨论真正应该留下来的成果。
