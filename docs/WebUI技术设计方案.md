# Web UI 技术设计方案

## 1. 项目背景

DouK-Downloader 是一个抖音/TikTok 数据采集工具，目前提供以下运行模式：
- **终端交互模式** - CLI 命令行交互
- **Web API 模式** - FastAPI REST API（仅数据获取，不执行下载）
- **后台监听模式** - 剪贴板监听下载

本次目标是新增 **Web UI 模式**，提供图形化界面，实现：
- 输入账号链接，批量下载账号作品
- 输入单个作品链接，下载作品
- 与 CLI 模式保持数据一致性（保存目录、下载记录等）

## 2. 设计原则

- **零修改原有代码** - 仅新增代码，不改动现有模块
- **复用现有能力** - 直接调用 CLI 核心逻辑
- **数据一致性** - 共用配置文件、数据库、下载记录

## 3. 现有能力分析

### 3.1 核心类结构

```
src/
├── application/
│   ├── TikTokDownloader.py    # 主入口，配置初始化
│   ├── main_terminal.py       # CLI 核心：TikTok 类
│   └── main_server.py         # Web API：APIServer 类
│   └── main_monitor.py        # 剪贴板监听
├── interface/                  # API 接口层（可独立调用）
│   ├── account.py             # Account - 账号作品获取
│   ├── detail.py              # Detail - 单作品获取
│   └── template.py            # API 基类
├── downloader/
│   └── download.py            # Downloader - 文件下载执行
├── extract/
│   └── extractor.py           # Extractor - 数据提取
├── link/
│   ├── extractor.py           # LinkExtractor - 链接解析（抖音）
│   └── extractor_tiktok.py    # ExtractorTikTok - 链接解析（TikTok）
├── config/
│   ├── settings.py            # Settings - 配置管理
│   └── parameter.py           # Parameter - 参数验证
├── manager/
│   ├── database.py            # Database - SQLite 数据库
│   ├── recorder.py            # DownloadRecorder - 下载记录
│   └── cache.py               # Cache - 缓存管理
├── storage/
│   └── manager.py             # RecordManager - CSV/XLSX/SQLite 存储
└── tools/
    └── console.py             # ColorfulConsole - 控制台输出
```

### 3.2 TikTok 类核心方法（可直接复用）

| 方法 | 功能 | 参数 |
|------|------|------|
| `check_sec_user_id(url, tiktok)` | 从链接提取 sec_user_id | url: 账号链接 |
| `_get_account_data(sec_user_id, tab, ...)` | 获取账号作品数据列表 | tab: post/favorite/collection |
| `_batch_process_detail(data, mode, ...)` | 批量处理作品（提取+下载） | mode: post/favorite/mix |
| `_handle_detail(ids, tiktok, record)` | 处理单个作品下载 | ids: 作品ID列表 |
| `download_detail_batch(data, type_, ...)` | 执行批量下载 | data: 作品数据列表 |
| `get_user_info_data(sec_user_id)` | 获取账号信息 | sec_user_id |
| `deal_account_detail(index, sec_user_id, ...)` | 完整账号下载流程 | 完整参数集 |
| `deal_mix_detail(mix_id, id_, ...)` | 合集下载流程 | mix_id, detail_id |

### 3.3 链接解析器

```python
# 抖音链接解析
from src.link import Extractor as LinkExtractor
links = LinkExtractor(parameter)
ids = await links.run(url, type_="user")  # 返回 sec_user_id 列表
ids = await links.run(url, type_="detail")  # 返回作品 ID 列表
ids = await links.run(url, type_="mix")  # 返回 (mix_id, 作品ID列表)
ids = await links.run(url, type_="live")  # 返回 web_rid 列表

# TikTok 链接解析
from src.link import ExtractorTikTok
links_tiktok = ExtractorTikTok(parameter)
```

### 3.4 数据存储

**配置文件**：`Volume/settings.json`
- `root` - 保存根目录
- `folder_name` - 默认文件夹名
- `name_format` - 文件名格式
- `cookie` / `cookie_tiktok` - Cookie
- `download` - 是否下载文件

**数据库**：`Volume/DouK-Downloader.db`
- `download_data` 表 - 已下载作品 ID 记录
- `mapping_data` 表 - 账号/合集映射缓存
- `config_data` 表 - 功能配置
- `option_data` 表 - 选项配置

## 4. 架构设计

### 4.1 新增文件结构

```
src/webui/
├── __init__.py              # 模块入口
├── server.py                # Web UI FastAPI 服务
├── manager.py               # WebUIManager - 封装 TikTok 类
└── routes/
    ├── __init__.py
    ├── account.py           # 账号下载 API
    └── detail.py            # 作品下载 API
```

### 4.2 依赖关系

```
WebUIManager (新增)
    ├── 继承 TikTok (main_terminal.py)
    ├── 复用 Parameter (config)
    ├── 复用 Database (manager)
    ├── 复用 Settings (config)
    └── 复用 Downloader/Extractor

WebUIServer (新增)
    ├── 创建 WebUIManager
    ├── 定义 FastAPI 路由
    └── 提供 Web UI 前端页面
```

### 4.3 启动流程

```
用户选择 "Web UI 模式"
    ↓
TikTokDownloader.server_webui()
    ↓
创建 WebUIServer(parameter, database)
    ↓
FastAPI 服务启动 (http://127.0.0.1:8080)
    ↓
用户访问 Web UI 页面
    ↓
调用 API → WebUIManager 方法 → 执行下载
```

## 5. API 设计

### 5.1 账号下载 API

**POST /api/account/download**

请求参数：
```json
{
    "url": "https://www.douyin.com/user/MS4wLjABAAAA...",
    "tab": "post",
    "mark": "",
    "earliest": "",
    "latest": "",
    "pages": 0
}
```

响应：
```json
{
    "success": true,
    "message": "下载完成",
    "data": {
        "nickname": "用户昵称",
        "total": 100,
        "downloaded": 50,
        "skipped": 50
    }
}
```

**GET /api/account/info**

请求参数：`url` (Query)

响应：账号基本信息（昵称、ID、作品数等）

### 5.2 作品下载 API

**POST /api/detail/download**

请求参数：
```json
{
    "url": "https://v.douyin.com/xxx/"
}
```

响应：
```json
{
    "success": true,
    "message": "下载完成",
    "data": {
        "title": "作品标题",
        "type": "视频/图集",
        "path": "保存路径"
    }
}
```

### 5.3 配置管理 API

**GET /api/settings** - 获取当前配置
**POST /api/settings** - 更新配置（Cookie等）
**GET /api/status** - 获取下载状态/进度

### 5.4 下载记录 API

**GET /api/records** - 获取已下载作品列表
**DELETE /api/records/{id}** - 删除下载记录

## 6. 数据一致性保证

### 6.1 共用配置

Web UI 与 CLI 共用 `settings.json`：
- 保存目录由 `root` + `folder_name` 决定
- 文件命名由 `name_format` 决定
- Cookie 由 `cookie` 参数决定

### 6.2 共用下载记录

共用 `DouK-Downloader.db`：
- 作品下载后 ID 写入 `download_data` 表
- 重复下载自动跳过（`DownloadRecorder.has_id()`）
- 账号映射缓存存储在 `mapping_data` 表

### 6.3 初始化流程

```python
# Web UI 服务初始化（复用 CLI 初始化逻辑）
async def init_webui():
    # 1. 加载配置
    settings = Settings(PROJECT_ROOT, console)
    config = settings.read()

    # 2. 创建 Parameter
    parameter = Parameter(settings, cookie, **config)

    # 3. 连接数据库
    database = Database()
    await database.__aenter__()

    # 4. 创建 WebUIManager（复用 TikTok 类）
    manager = WebUIManager(parameter, database)

    return manager
```

## 7. 前端设计

### 7.1 页面布局

```
┌─────────────────────────────────────────────┐
│  DouK-Downloader Web UI                      │
├─────────────────────────────────────────────┤
│  [账号下载] [作品下载] [设置] [记录]          │
├─────────────────────────────────────────────┤
│                                              │
│  账号下载页面:                               │
│  ┌─────────────────────────────────────────┐│
│  │ 账号链接: [___________________________] ││
│  │ 类型: [发布作品 ▼] 标识: [___________] ││
│  │ 时间范围: [开始] ~ [结束]              ││
│  │                               [开始下载] ││
│  └─────────────────────────────────────────┘│
│                                              │
│  下载进度: ████████░░░░ 50/100              │
│                                              │
├─────────────────────────────────────────────┤
│  状态: Cookie 已配置 | 下载目录: /Download   │
└─────────────────────────────────────────────┘
```

### 7.2 技术选型

**方案 A：纯静态 HTML + Vue.js**
- 轻量、无需额外依赖
- FastAPI 静态文件托管

**方案 B：Gradio**
- Python 原生，快速开发
- 适合简单交互场景

**方案 C：FastAPI + Jinja2 模板**
- 服务端渲染
- 简单直接

**推荐方案：方案 A**（静态 HTML + Vue.js）

## 8. 实现步骤

### Phase 1: 核心模块（后端）

1. 创建 `src/webui/__init__.py`
2. 创建 `src/webui/manager.py` - WebUIManager 类
3. 创建 `src/webui/server.py` - FastAPI 服务
4. 创建 API 路由处理函数

### Phase 2: 前端界面

1. 创建 `static/webui/index.html`
2. 实现账号下载表单
3. 实现作品下载表单
4. 实现进度显示
5. 实现配置页面

### Phase 3: 集成

1. 修改 `TikTokDownloader.py` 添加 Web UI 模式入口（可选）
2. 或创建独立启动脚本 `webui.py`

### Phase 4: 测试与优化

1. 测试账号下载功能
2. 测试作品下载功能
3. 验证数据一致性
4. 性能优化（异步进度反馈）

## 9. 风险与限制

### 9.1 技术限制

- 下载过程为异步执行，前端需实时获取进度
- 大量下载时可能阻塞，需考虑后台任务队列

### 9.2 功能限制

- 首期仅支持抖音平台（TikTok 可后续扩展）
- 首期仅支持账号发布作品下载和单个作品下载

## 10. 后续扩展

- 支持 TikTok 平台
- 支持合集下载
- 支持直播下载
- 支持收藏/收藏夹下载
- 下载队列管理
- 多任务并行下载

---

**文档版本**: v1.0
**创建日期**: 2026-05-13