# DouK-Downloader Web UI

Web UI 模块提供图形化界面，实现抖音账号作品批量下载和单个作品下载功能。

## 功能特性

- **账号信息预览**：获取账号基本信息（昵称、作品数、粉丝数等）
- **账号批量下载**：批量下载账号发布作品、喜欢作品、收藏作品
- **单个作品下载**：输入作品链接下载单个作品
- **账号列表管理**：增删改查账号配置（mark、链接、作品类型、启用状态），数据持久化到 `settings.json`
- **下载进度展示**：实时显示下载进度、成功/失败/跳过统计
- **数据一致性**：与 CLI 模式共用配置、数据库、下载记录
- **目录命名一致**：作品保存到作者目录，格式：`UID{uid}_{nickname}_发布作品`

## 快速开始

### 1. 启动服务

```bash
# 方式一：一键启动脚本（推荐，自动激活虚拟环境）
./start-webui.sh

# 方式二：手动启动
source venv/bin/activate
python webui.py
```

服务启动后访问：http://127.0.0.1:8080

### 2. 配置 Cookie

Web UI 需要配置抖音 Cookie 才能正常使用。

参考 [Cookie 获取教程](../docs/Cookie获取教程.md) 获取 Cookie，然后：

- 方式一：通过 CLI 模式写入配置
- 方式二：直接编辑 `Volume/settings.json` 文件，填入 `cookie` 字段

### 3. 使用功能

#### 账号下载

1. 进入"账号下载"标签页
2. 输入账号主页链接（格式：`https://www.douyin.com/user/MS4wLjABAAAA...`）
3. 点击"获取账号信息"预览账号数据
4. 选择作品类型（发布作品/喜欢作品/收藏作品）
5. 可选：设置自定义标识、时间范围
6. 点击"开始下载"

#### 作品下载

1. 进入"作品下载"标签页
2. 输入作品链接
   - 完整链接：`https://www.douyin.com/video/7xxxxxxxxxxxxxx`
   - 短链接：`https://v.douyin.com/xxx/`（需网络请求解析）
3. 点击"开始下载"

#### 账号管理

1. 进入"账号管理"标签页
2. 查看已配置的账号列表（用户名、作品类型、启用状态）
3. 点击用户名超链接可在新标签页打开账号主页
4. 点击"新增账号"添加账号配置（标识名称、账号链接必填、作品类型、日期范围、启用开关）
5. 点击"编辑"修改已有账号配置
6. 点击 Toggle 开关快速启用/禁用账号
7. 点击"删除"移除账号（带确认弹窗防误删）

> 账号数据存储在 `Volume/settings.json` 的 `accounts_urls` 字段中，与 CLI 模式共用。

## API 接口

| 接口 | 方法 | 功能 |
|------|------|------|
| `/` | GET | Web UI 主页 |
| `/api/settings` | GET | 获取当前配置 |
| `/api/cookie/status` | GET | 获取 Cookie 状态 |
| `/api/account/info` | GET | 获取账号信息（不下载） |
| `/api/account/download` | POST | 账号作品批量下载 |
| `/api/detail/download` | POST | 单个作品下载 |
| `/api/progress` | GET | 获取下载进度 |
| `/api/accounts` | GET | 获取账号列表 |
| `/api/accounts` | POST | 新增账号 |
| `/api/accounts/{index}` | PUT | 更新账号 |
| `/api/accounts/{index}` | DELETE | 删除账号 |

### API 使用示例

```bash
# 获取账号信息
curl "http://127.0.0.1:8080/api/account/info?url=https://www.douyin.com/user/MS4wLjABAAA..."

# 批量下载账号作品
curl -X POST http://127.0.0.1:8080/api/account/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.douyin.com/user/MS4wLjABAAA...", "tab": "post"}'

# 下载单个作品
curl -X POST http://127.0.0.1:8080/api/detail/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.douyin.com/video/7xxxxxxxxxxxxxx"}'

# 获取账号列表
curl "http://127.0.0.1:8080/api/accounts"

# 新增账号
curl -X POST http://127.0.0.1:8080/api/accounts \
  -H "Content-Type: application/json" \
  -d '{"mark": "用户名", "url": "https://www.douyin.com/user/MS4w...", "tab": "post", "enable": true}'

# 更新账号（index 从 0 开始）
curl -X PUT http://127.0.0.1:8080/api/accounts/0 \
  -H "Content-Type: application/json" \
  -d '{"mark": "新名称", "enable": false}'

# 删除账号
curl -X DELETE http://127.0.0.1:8080/api/accounts/0
```

## 文件结构

```
src/webui/
├── __init__.py      # 模块入口
├── manager.py       # WebUIManager 类（封装下载能力）
└── server.py        # FastAPI 服务（API 路由 + 前端页面）

static/webui/
└── index.html       # Vue.js 前端页面

webui.py             # 独立启动脚本
```

## 数据一致性

Web UI 与 CLI 模式完全共用：

| 功能 | 共用资源 |
|------|----------|
| 保存目录 | `settings.json` 的 `root` + `folder_name` 配置 |
| 下载记录 | `DouK-Downloader.db` 数据库 |
| 文件命名 | `settings.json` 的 `name_format` 配置 |
| Cookie | `settings.json` 的 `cookie` 配置 |
| 目录命名 | 格式：`UID{uid}_{nickname}_发布作品` |

## 优化方向

### 1. 异步下载与进度轮询（优先级：中）

**现状**：下载接口为同步接口，大量作品下载时可能超时。

**优化方案**：
- 引入后台任务队列（使用 `asyncio.create_task`）
- 实现任务状态持久化
- 前端通过 `/api/task/{id}/status` 轮询进度
- 支持任务取消、暂停、恢复

**预估改动量**：中等（约 50-100 行代码）

### 2. WebSocket 实时进度（优先级：低）

**现状**：前端需要轮询 `/api/progress` 获取进度。

**优化方案**：
- 使用 WebSocket 推送实时下载进度
- 前端监听 WebSocket 更新界面

**预估改动量**：中等（需修改前后端）

### 3. 更多功能支持（优先级：低）

**现状**：仅支持账号发布作品和单个作品下载。

**可扩展功能**：
- TikTok 平台支持
- 合集下载
- 直播下载
- 收藏夹下载
- 下载历史查看与管理
- 多任务并行下载

### 4. 用户体验优化（优先级：低）

- 下载失败作品的错误信息展示
- 批量输入多个链接
- 从剪贴板自动识别链接
- 下载完成后通知提醒
- 深色模式支持

## 技术栈

- **后端**：FastAPI + Uvicorn
- **前端**：Vue.js 3（CDN 引入，无需构建）
- **复用**：CLI 核心下载逻辑（`TikTok` 类）

## 注意事项

1. **Cookie 必需**：未配置 Cookie 时部分功能无法使用
2. **短链接解析**：短链接需要网络请求解析重定向，可能因链接失效或网络问题失败
3. **端口占用**：默认端口 8080，如有占用可修改 `server.py` 的 `WEBUI_PORT`
4. **语言设置**：启动时自动设置中文，确保目录名使用中文格式

## 相关文档

- [虚拟环境使用指南](../docs/虚拟环境使用指南.md)
- [Cookie 获取教程](../docs/Cookie获取教程.md)
- [WebUI 技术设计方案](../docs/WebUI技术设计方案.md)