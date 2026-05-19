# protocol

`fire_alarm_simulator/protocol/` 是当前项目的统一协议层，负责沉淀 GB/T 26875.3-2011 标准定义、厂商扩展定义、数据包编解码、ADU 结构化解析和场景生成所依赖的共享逻辑。

## 目录结构

```text
protocol/
├── __init__.py
├── README.md
├── standard.py
├── shared.py
├── core.py
├── adu/
│   ├── __init__.py
│   ├── common.py
│   └── registry.py
└── profiles/
    ├── __init__.py
    └── jk_gh2013g.py
```

## 模块职责

### `standard.py`

- 只放国标层定义。
- 包含命令字、类型标志、系统类型、部件类型、模拟量类型、状态位说明等稳定常量。
- 不放厂商自定义类型，不放解析流程代码。

### `profiles/`

- 每个厂商或设备族一个 profile 文件。
- 当前已有 `jk_gh2013g.py`，用于承载 Excel 中整理出的自定义类型值、时间字段语义、系统地址特殊含义等。
- profile 只描述“厂商补充规则”，不直接承担完整解析流程。

### `shared.py`

- 放公共上下文和工具函数。
- 包括：
  - 标准层与 profile 层合并后的字典视图
  - `ByteReader`
  - 时间标签、字符串、状态位等基础解码工具
  - 类型来源判断和通用 note 生成
- 原则上这里不放场景生成逻辑，也不放按 `type_flag` 分发逻辑。

### `adu/common.py`

- 放 ADU 信息对象级别的解析函数。
- 例如：
  - 系统状态
  - 部件状态
  - 模拟量
  - 操作信息
  - 查询目标
  - 厂商时间类对象
- 这些函数关注“如何从负载中读出对象”，不关心总的类型分发表。

### `adu/registry.py`

- 按 `type_flag` 注册解析器。
- `PARSER_REGISTRY` 是当前 ADU 解析入口的唯一注册表。
- 新增类型时，优先在这里注册，而不是回到 `core.py` 里继续堆条件分支。

### `core.py`

- 保留统一对外入口。
- 当前负责：
  - `parse_adu()`
  - `GBT26875Packet`
  - `ADUBuilder`
  - `build_packet_view()`
  - `FireAlarmSimulator`
- `core.py` 不再承载各类对象级 ADU 解析细节，只做上下文组装、注册表分发和结果包装。

## 当前解析链路

1. `GBT26875Packet.parse_packet()` 负责总帧解析。
2. `parse_adu()` 负责：
   - 读取 `type_flag` 与 `info_count`
   - 生成类型来源、方向、profile note
   - 从 `adu/registry.py` 选择解析器
   - 统一包装结构化结果
3. `build_packet_view()` 负责把总帧解析结果与 ADU 解析结果合并为前后端共用结构。

## 扩展规范

### 新增标准类型

如果是国标层的补充：

1. 先改 `standard.py`
2. 再在 `adu/common.py` 中补对象级解析函数
3. 最后在 `adu/registry.py` 注册对应 `type_flag`

### 新增厂商扩展

如果是新厂家或新设备型号：

1. 在 `profiles/` 下新增一个文件
2. 定义：
   - `PROFILE_KEY`
   - `PROFILE_NAME`
   - 自定义 `TYPE_FLAG` 映射
   - 特殊字段语义和备注
3. 如该 profile 需要特殊对象结构：
   - 在 `adu/common.py` 新增解析函数，或继续拆成新的 `adu/*.py`
4. 在 `adu/registry.py` 注册对应类型

### 新增 ADU 类型解析器

建议新增步骤：

1. 在 `adu/common.py` 增加对象解析函数
2. 函数输入统一为 `ByteReader` 和必要上下文
3. 输出统一为 `List[Dict[str, Any]]`
4. 在 `adu/registry.py` 注册到 `PARSER_REGISTRY`
5. 在 `tests/test_protocol.py` 增加固定样例

## 测试约束

- 当前测试文件为 `tests/test_protocol.py`
- 约束如下：
  - 每个已支持的 `type_flag` 至少有 1 个固定样例
  - `build_packet_view()` 输出必须稳定
  - `parse_hex` 接口输出的 `summary/fields/status_flags` 必须稳定

运行方式：

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

## 设计原则

- 标准层和厂商层分离
- 生成器和解析器共用同一套协议定义
- Web 后端、CLI 模拟器、前端展示都消费统一结构化结果
- `core.py` 做入口，不做大而全实现
- 新增类型优先“注册解析器”，避免继续在单文件堆逻辑

## 现阶段边界

- 当前“协议字典层”仍是 Python 模块，不是外部 JSON/YAML 数据源。
- 当前 ADU 解析虽然已经模块化，但 `adu/common.py` 仍偏大，后续可继续按主题拆分：
  - `status.py`
  - `query.py`
  - `device.py`
  - `vendor_custom.py`

## 维护建议

- 如果 Excel 还会继续扩展，下一阶段可以考虑做“Excel -> profile 数据”的生成脚本。
- 如果将来接第二家厂商，优先新增 `profiles/<vendor>.py`，不要直接改 `standard.py`。
