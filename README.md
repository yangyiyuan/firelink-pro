# FireLink Pro - 智慧消防通信协议模拟器

基于 GB/T 26875.3-2011《城市消防远程监控系统 第3部分：报警传输网络通信协议》标准的专业级消防报警通信模拟器，为智慧消防/物联网平台提供场景化测试能力。

## 项目背景

随着物联网技术的快速发展，智慧消防已成为城市安全建设的重要组成部分。用户信息传输装置（ADU）作为连接前端消防设备与后端监控平台的关键枢纽，其通信协议的正确性直接关系到火灾报警信息的准确传输和及时响应。

GB/T 26875.3-2011 国家标准规定了城市消防远程监控系统中报警传输网络的通信协议，包括数据包结构、编码方式、传输规则等核心内容。然而，在实际开发和测试过程中，缺乏专业的协议模拟工具，导致：

- 平台开发阶段无法进行有效的端到端测试
- 协议实现正确性难以验证
- 复杂场景下的系统稳定性测试困难
- 新设备接入时缺乏标准化的测试手段

## 功能特性

### 场景模拟

- **正常状态** - 设备正常监视状态（装置状态）
- **单点火灾报警** - 单个探测器火警
- **确认火警** - 多点同时报警（确认火警）
- **故障报警** - 设备故障
- **复合报警** - 火警+故障同时发生
- **模拟量超限** - 温度/烟雾浓度超限
- **系统级火警** - 整个系统火警状态
- **装置火警** - 传输装置火警状态
- **完整火灾场景** - 完整火灾序列（4个数据包：系统火警→装置火警→部件火警→模拟量）
- **随机场景** - 随机生成一种场景

### 自动发送场景

- 支持多步骤时序组合，可配置步骤间延迟
- 内置7个系统预置模板（两点报警、故障-恢复、报警-反馈、启动-反馈、报警-反馈-恢复、监管-恢复、完整联动链路）
- 支持用户自定义场景模板（增删改查）
- 支持循环/单次执行模式
- 场景分类：火警报警、故障报警、状态恢复、联动控制、监管报警、模拟量监控、传输装置、屏蔽管理、序列场景、自定义
- 步骤支持多种信息对象类型：部件状态、系统状态、模拟量值、装置状态
- 发送前自动重建数据包（业务流水号递增、时间标签刷新）
- 优先复用已建立的长连接发送

### 信号实例管理

- 创建信号实例：绑定模板 + 自定义设备参数（源地址、目的地址、部件类型等）
- 实例预览：查看数据包解析视图
- 实例数据包解析：获取完整数据包 HEX + 视图结构
- 实例增删改查，支持标签与描述
- 使用计数与最后使用时间跟踪

### 网络功能

- 支持 TCP/UDP 发送
- **TCP 长连接管理**：建立持久连接，实时接收服务器响应
  - TCP Keepalive 探测（10秒空闲开始，3秒间隔，3次失败判定断开）
  - 基于帧结构的精确接收解析（读取控制单元中的 ADU 长度字段，不再盲扫标记符）
  - 连接断开时自动联动停止自动场景发送
- **网络配置管理**：支持多组目标服务器配置（增删改查），持久化到 `network_configs.json`
- 连接测试：TCP/UDP 连通性预检查（含输入验证）
- 连接状态实时查询：前端轮询 + WebSocket 事件双通道

### 数据包解析

- 实时解析数据包结构
- 十六进制显示
- 字段级详情展示
- 一键复制 HEX
- **HEX 数据解析 API**：通过输入十六进制字符串解析任意数据包（含输入验证）
- 支持 GB/T 26875.3-2011 标准全部类型标志解析（1~8, 21, 24~28, 61~68, 81, 84~91）
- 支持 JK-GH2013G 厂商扩展类型标志解析（128~136, 188, 189）
- 状态位可视化解码（部件状态、系统状态、装置状态位标志展开）
- 模拟量自动换算（温度、压力、气体浓度等含单位换算）
- 部件说明 GB18030 编码自动解码

### 发送历史

- 双向记录：发送历史 + 接收历史
- 历史记录保存：去重后导出为 JSON 文件持久化
- 历史记录导出：JSON/CSV 格式导出
- 最大保留 1000 条实时记录

### 业务流水号管理

- 全局自增管理器（线程安全，0~65535 循环）
- 所有数据包发送共享同一序号源，确保连续发送时序号严格递增
- 支持查询当前序号和重置

## 项目结构

```
fire_alarm_simulator/
├── app.py                          # Flask 入口骨架（服务实例化 + Blueprint/SocketIO 注册）
├── requirements.txt                # Python 依赖
├── pyproject.toml                  # pytest 配置
├── README.md                       # 项目说明
├── data/
│   ├── history/                    # 历史记录保存目录
│   └── system_templates.json       # 系统预置场景模板（7个，JSON 格式）
├── protocol/                       # 协议实现模块
│   ├── __init__.py                 # 包导出（向后兼容重导出）
│   ├── core.py                     # 核心数据包构建/解析（GBT26875Packet + ADUBuilder）
│   ├── simulator.py                # 场景模拟器（FireAlarmSimulator）
│   ├── scene_catalog.py            # 场景目录定义（SCENE_CATALOG）
│   ├── sequence.py                 # 流水号管理器（SequenceManager）
│   ├── packet_view.py              # 数据包视图构建（build_packet_view + parse_adu）
│   ├── standard.py                 # GB/T 26875.3-2011 标准枚举与常量定义
│   ├── shared.py                   # 共享工具函数（时间解码、状态位解码、ByteReader 等）
│   ├── adu/                        # 应用数据单元（ADU）解析器
│   │   ├── __init__.py
│   │   ├── common.py               # 各类型信息对象的结构化解析实现
│   │   └── registry.py             # 类型标志→解析函数注册表
│   └── profiles/                   # 厂商协议扩展 Profile
│       ├── __init__.py
│       ├── jd_f53.py               # 久鼎 F53 传输装置扩展定义
│       └── jk_gh2013g.py           # JK-GH2013G 型传输装置扩展定义
├── services/                       # 业务服务模块
│   ├── __init__.py
│   ├── auto_send_scene.py          # 自动发送场景服务（模板管理、场景计划构建、数据包重建）
│   ├── connection_manager.py       # 连接管理器（统一发送、长连接、接收循环、事件回调）
│   ├── history_manager.py          # 历史记录管理器（记录、去重、保存、导出）
│   ├── scene_runner.py             # 场景运行管理器（多场景并发、线程安全、断开联动）
│   ├── signal_instance.py          # 信号实例服务（CRUD、验证、数据包解析、持久化）
│   ├── network_config.py           # 网络配置存储（CRUD + JSON 持久化）
│   ├── utils.py                    # 工具函数（parse_int、now_str、now_ms_str）
│   └── api/                        # Flask Blueprint 路由层
│       ├── __init__.py             # Blueprint 注册总入口（register_all）
│       ├── scenes_bp.py            # 场景与统计路由
│       ├── history_bp.py           # 历史记录路由（含保存/导出）
│       ├── signal_instances_bp.py  # 信号实例路由
│       ├── auto_send_bp.py         # 自动发送场景路由
│       ├── network_configs_bp.py   # 网络配置路由
│       ├── profiles_bp.py          # Profile 路由
│       ├── connection_bp.py        # 连接管理路由
│       ├── socketio_events.py      # SocketIO 事件处理器
│       ├── response_utils.py       # 统一 API 响应格式（success_response / error_response）
│       └── validators.py           # 路由输入验证（hex、port、host、scene 结构）
├── static/                         # 静态资源
│   ├── css/
│   │   └── main.css                # 全局样式
│   ├── js/
│   │   ├── main.js                 # 应用入口与初始化
│   │   ├── sceneData.js            # 场景数据转换公共模块（IIFE，含 GROUP_MAP/TEMPLATE_GROUPS/cloneScene 等）
│   │   ├── autoSend.js             # 自动发送场景编辑器与运行控制
│   │   ├── signalInstance.js       # 信号实例管理
│   │   ├── scene.js                # 场景选择与数据包展示
│   │   ├── network.js              # 网络配置与长连接管理
│   │   ├── history.js              # 发送/接收历史记录
│   │   ├── parse.js                # 协议解析与展示
│   │   ├── sendHistory.js          # 保存历史记录管理
│   │   ├── panel.js                # 面板导航编排器
│   │   ├── stats.js                # 统计信息
│   │   ├── profile.js              # Profile 切换
│   │   ├── adu-common.js           # ADU 解析展示工具（基础模块）
│   │   ├── customSelect.js         # 自定义下拉选择组件
│   │   └── utils.js                # 工具函数（toast、escapeHtml、escapeAttr）
│   └── images/                     # 图片资源
├── templates/                      # HTML 模板
│   └── index.html                  # 主页面（单页应用入口）
├── tests/                          # 测试代码（166 个测试，pytest）
│   ├── conftest.py                 # 测试 fixtures（Flask client、app_context）
│   ├── api/
│   │   ├── test_routes_smoke.py    # API 路由冒烟测试
│   │   ├── test_response_utils.py  # 统一响应格式测试
│   │   ├── test_validators.py      # 输入验证函数测试
│   │   └── test_socketio_events.py # SocketIO 事件测试
│   ├── protocol/
│   │   ├── test_module_split.py    # 协议模块拆分兼容性测试
│   │   └── test_packet_builder.py  # 数据包构建测试
│   └── services/
│       ├── test_connection_manager.py  # ConnectionManager 测试
│       ├── test_history_manager.py     # HistoryManager 测试
│       ├── test_scene_runner.py        # SceneRunner 测试
│       └── test_concurrent.py          # 并发安全测试
├── docs/
│   └── OPTIMIZATION_PLAN.md        # 优化方案文档（v3.0）
└── *.json                          # 运行时持久化文件（自动生成）
    ├── auto_send_templates.json     # 用户自定义场景模板
    ├── network_configs.json         # 网络目标配置
    └── signal_instances.json        # 信号实例数据
```

## 安装运行

### 1. 安装依赖

```bash
cd fire_alarm_simulator
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python app.py
```

生产环境建议设置环境变量：

```bash
export SECRET_KEY=<your-secret-key>  # 默认使用硬编码后备值并输出警告
export CORS_ORIGINS=<allowed-origins>  # 默认 '*'
export FLASK_DEBUG=false               # 默认 true
```

### 3. 访问界面

打开浏览器访问: http://127.0.0.1:5001

### 4. 运行测试

```bash
pytest tests/ --timeout=10 -v
```

## 使用说明

### 基本操作

1. **选择场景**: 点击左侧场景卡片选择要模拟的火警场景
2. **查看数据包**: 选择场景后，数据包详情会自动显示在下方
3. **发送数据**: 点击"发送数据包"按钮将数据发送到目标服务器
4. **复制HEX**: 点击"复制HEX"可复制原始十六进制数据

### 网络配置

- **配置管理**: 支持添加、编辑、删除多组目标服务器配置（含主机地址和端口范围验证）
- **目标主机**: 接收数据的服务器地址
- **目标端口**: 接收数据的服务器端口（1~65535）
- **传输协议**: TCP 或 UDP
- **源地址**: 数据包源地址

### 长连接模式

1. 选择目标服务器后点击"连接"建立 TCP 长连接
2. 连接成功后可通过长连接发送数据包，同时自动接收服务器响应
3. 服务器响应数据会自动解析并展示在历史记录中
4. 连接断开时自动通知前端更新 UI 状态，并联动停止正在运行的自动场景

### 自动发送场景

1. 在自动发送面板选择或创建场景模板（配置数据从后端元数据动态加载）
2. 编辑场景步骤（设置类型标志、信息对象、步骤间延迟等）
3. 选择目标网络配置
4. 点击"开始"启动自动发送
5. 点击"停止"结束自动发送
6. 支持循环执行或单次执行模式

### 信号实例

1. 创建信号实例：选择模板 + 设置设备参数
2. 预览实例数据包解析视图
3. 通过 SocketIO 直接发送实例数据包
4. 编辑实例的名称、描述、标签、设备参数

### 发送历史

- 双向记录发送和接收的数据
- 支持保存历史到文件（自动去重）
- 支持导出为 JSON/CSV 格式
- 支持刷新和清空操作

## 协议实现

### 数据包结构

```
+------------+-------------------+---------------+-----------+------------+
| 启动符(2B) |     控制单元(25B)  | 应用数据单元  | 校验和(1B) | 结束符(2B) |
|   @@       |                  |   (变长)      |           |    ##      |
+------------+-------------------+---------------+-----------+------------+
```

### 控制单元结构

- 业务流水号 (2字节, 0~65535 循环自增)
- 协议版本号 (2字节, 默认 1.0)
- 时间标签 (6字节, 秒/分/时/日/月/年)
- 源地址 (6字节)
- 目的地址 (6字节)
- 应用数据单元长度 (2字节, 最大1024字节)
- 命令字节 (1字节)

### 应用数据单元

- 类型标志 (1字节, 标识信息对象数据类型)
- 信息对象数目 (1字节)
- 信息对象 (变长)

### 支持的类型标志

| 范围 | 方向 | 说明 |
|------|------|------|
| 1~8 | 上行 | 建筑消防设施系统状态/部件状态/模拟量/操作信息/软件版本/系统配置/部件配置/系统时间 |
| 21, 24~28 | 上行 | 用户信息传输装置运行状态/操作信息/软件版本/配置情况/系统时间 |
| 61~68 | 下行 | 读建筑消防设施各类信息 |
| 81, 84~91 | 下行 | 读传输装置各类信息/初始化/同步时钟/查岗 |
| 128~136 | 上行 | JK-GH2013G 厂商扩展（生产日期/报名/开关机/状态恢复） |
| 188~189 | 下行 | JK-GH2013G 厂商扩展（读生产日期/设置报名时间） |

### 厂商 Profile 扩展

协议解析采用 Profile 架构，支持厂商自定义类型标志扩展与部件地址字节序配置：

- **JK-GH2013G**: 支持 128~136、188、189 类型标志的解析，包含自定义时间类型名称映射和系统地址语义说明
- **久鼎 F53**: 支持 F53 厂商协议扩展，包含部件地址字节序配置

## API 接口

所有 HTTP API 使用统一响应格式：
- 成功: `{"success": true, ...其他字段}`
- 失败: `{"success": false, "error": "错误消息", ...其他字段}`

### HTTP API

#### 场景与统计

- `GET /api/scenes` - 获取场景列表
- `GET /api/stats` - 获取统计信息（含业务流水号当前值）
- `GET /api/sequence` - 获取当前业务流水号
- `POST /api/sequence/reset` - 重置业务流水号（JSON body: `{"value": 0}`）

#### 自动发送场景

- `GET /api/auto_send/meta` - 获取自动发送场景元数据（类型标志/系统类型/部件类型/状态预设等枚举选项）
- `GET /api/auto_send/templates` - 获取所有场景模板（系统预置+用户自定义）
- `POST /api/auto_send/templates` - 创建用户自定义场景模板（含场景结构验证）
- `PUT /api/auto_send/templates/<template_id>` - 更新用户自定义场景模板
- `DELETE /api/auto_send/templates/<template_id>` - 删除用户自定义场景模板
- `POST /api/auto_send/preview` - 预览场景执行计划（含场景结构验证）
- `POST /api/parse_hex` - 解析十六进制数据包（JSON body: `{"hex": "4040..."}`, 含 HEX 格式验证）

#### 信号实例

- `GET /api/signal_instances` - 获取所有信号实例
- `POST /api/signal_instances` - 创建信号实例
- `GET /api/signal_instances/<id>` - 获取指定信号实例
- `PUT /api/signal_instances/<id>` - 更新信号实例
- `DELETE /api/signal_instances/<id>` - 删除信号实例
- `POST /api/signal_instances/<id>/preview` - 预览实例数据包
- `GET /api/signal_instances/<id>/resolve` - 解析实例数据包（返回 HEX + 视图）

#### 网络配置

- `GET /api/network_configs` - 获取所有网络配置
- `GET /api/network_configs/<id>` - 获取指定网络配置
- `POST /api/network_configs` - 创建网络配置（含主机地址和端口范围验证）
- `PUT /api/network_configs/<id>` - 更新网络配置
- `DELETE /api/network_configs/<id>` - 删除网络配置

#### 连接管理

- `GET /api/connection_status` - 获取当前长连接状态
- `POST /api/test_connection` - 测试目标服务器连通性（含主机地址和端口范围验证）

#### 历史记录

- `GET /api/history` - 获取发送/接收历史（默认最近50条）
- `POST /api/clear_history` - 清空历史
- `POST /api/history/save` - 保存历史到文件（自动去重）
- `GET /api/history/list` - 获取已保存的历史文件列表
- `GET /api/history/saved/<id>` - 获取指定历史文件内容
- `DELETE /api/history/saved/<id>` - 删除指定历史文件
- `GET /api/history/export` - 导出当前历史为 JSON/CSV
- `GET /api/history/saved/<id>/export` - 导出指定历史文件为 JSON/CSV

#### Profile

- `GET /api/profiles` - 获取所有 Profile 列表
- `GET /api/profile` - 获取当前 Profile
- `PUT /api/profile` - 切换当前 Profile

### WebSocket 事件

#### 数据包操作

- `generate_packet` - 生成数据包
- `send_packet` - 发送数据包（短连接）

#### 自动发送

- `start_auto_send` - 开始自动发送
- `stop_auto_send` - 停止自动发送
- `start_auto_scene` - 开始自动发送场景（支持多步骤时序）
- `start_auto_scenes` - 开始多场景自动发送
- `stop_auto_scene` - 停止自动发送场景

#### 长连接管理

- `connect_target` - 建立到目标服务器的长连接
- `disconnect_target` - 断开长连接
- `send_via_connection` - 通过长连接发送数据包

#### 信号实例

- `start_signal_instance` - 启动信号实例发送
- `stop_signal_instance` - 停止信号实例发送

#### 服务器推送事件

- `target_connected` - 长连接已建立
- `target_disconnected` - 长连接已断开
- `target_connection_error` - 长连接错误
- `target_data_received` - 接收到服务器数据（含自动解析结果）
- `auto_scene_started` - 自动场景已启动
- `auto_scene_step_result` - 自动场景步骤执行结果
- `auto_scene_completed` - 自动场景一轮执行完成
- `auto_scene_stopped` - 自动场景已停止
- `auto_scene_error` - 自动场景执行错误
- `template_changed` - HTML 模板文件变更（热重载）

## 技术栈

- **后端**: Python + Flask + Flask-SocketIO (async_mode=threading)
- **前端**: HTML5 + CSS3 + JavaScript（IIFE 模块化，无框架依赖）
- **通信**: WebSocket + Socket.IO
- **协议**: GB/T 26875.3-2011 + 厂商 Profile 扩展
- **编码**: 部件说明支持 GB18030 编码/解码
- **测试**: pytest (166 个测试，覆盖协议层、服务层、API 层)

## 注意事项

1. 确保目标服务器已启动并监听指定端口
2. TCP 长连接模式需要目标服务器接受连接，连接后可双向通信
3. UDP 模式不需要预先建立连接，仅支持发送
4. 自动发送场景优先复用已建立的长连接，确保能接收服务器响应
5. TCP 长连接内置 Keepalive 探测，连接异常断开时自动联动停止自动场景
6. 业务流水号为全局共享，所有数据包发送自动递增（0~65535 循环）
7. 默认监听端口为 5001（非 5000）
8. 生产环境务必通过环境变量设置 `SECRET_KEY`，未设置时启动会输出警告日志
9. 支持 Flask 热重载模式，修改代码后服务自动重启

## 许可证

MIT License