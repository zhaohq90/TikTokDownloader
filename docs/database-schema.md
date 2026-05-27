# DouK-Downloader 数据库设计文档

> 数据库文件: `volume/DouK-Downloader.db` (SQLite)

## 概览

数据库共 4 张表，按职责分为三类：

| 类别 | 表名 | 用途 |
|------|------|------|
| 配置 | `config_data` | 存储布尔型开关配置 |
| 配置 | `option_data` | 存储字符串型选项配置 |
| 业务 | `download_data` | 记录已下载作品 ID，用于去重 |
| 业务 | `mapping_data` | 缓存账号映射关系，用于文件/文件夹重命名 |

---

## 表结构详解

### 1. config_data — 布尔开关配置

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| NAME | TEXT | PRIMARY KEY | 配置项名称 |
| VALUE | INTEGER | NOT NULL, CHECK(VALUE IN (0, 1)) | 配置值，仅允许 0 或 1 |

**预置数据：**

| NAME | VALUE | 说明 |
|------|-------|------|
| Record | 1 | 是否记录已下载作品 ID（防重复下载） |
| Logger | 0 | 是否启用日志记录 |
| Disclaimer | 1 | 是否已同意免责声明 |

**操作方式：** `REPLACE INTO` (upsert 语义)

---

### 2. option_data — 字符串选项配置

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| NAME | TEXT | PRIMARY KEY | 选项名称 |
| VALUE | TEXT | NOT NULL | 选项值 |

**预置数据：**

| NAME | VALUE | 说明 |
|------|-------|------|
| Language | zh_CN | 界面语言 |

**操作方式：** `REPLACE INTO` (upsert 语义)

---

### 3. download_data — 下载记录（去重表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| ID | TEXT | PRIMARY KEY | 作品 ID（19 位数字） |

**用途：** 下载作品前查询此表，若 ID 已存在则跳过，实现防重复下载。

**当前数据量：** ~800 条

**操作方式：**
- 写入: `INSERT OR IGNORE` (幂等)
- 查询: `SELECT ID WHERE ID=?` 判断是否已下载
- 删除: 支持单条、批量、全部删除

---

### 4. mapping_data — 账号映射缓存

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| ID | TEXT | PRIMARY KEY | 账号 ID |
| NAME | TEXT | NOT NULL | 账号昵称 |
| MARK | TEXT | NOT NULL | 账号备注名 |

**用途：** 缓存账号的昵称和备注名。当账号昵称或备注名变更时，据此自动重命名已下载的文件夹和文件。

**当前数据量：** ~8 条

**操作方式：**
- 写入: `REPLACE INTO` (upsert 语义)
- 查询: `SELECT NAME, MARK WHERE ID=?` 获取映射

---

## 表关系

```
┌──────────────┐     ┌──────────────┐
│ config_data  │     │ option_data  │
│ (开关配置)    │     │ (选项配置)    │
│              │     │              │
│ NAME  (PK)   │     │ NAME  (PK)   │
│ VALUE (0|1)  │     │ VALUE (TEXT) │
└──────────────┘     └──────────────┘

┌──────────────┐     ┌──────────────┐
│download_data │     │ mapping_data │
│ (下载去重)    │     │ (账号映射)    │
│              │     │              │
│ ID   (PK)    │──┐  │ ID   (PK)    │──┐
└──────────────┘  │  │ NAME (昵称)   │  │
                  │  │ MARK (备注)   │  │
                  │  └──────────────┘  │
                  │                    │
                  │  两者 ID 语义不同   │
                  │  ┌──────────────┐  │
                  └─►│ download_data │  │
                     │ ID = 作品 ID  │  │
                     └──────────────┘  │
                                     │
                  ┌──────────────┐     │
                  │ mapping_data │◄────┘
                  │ ID = 账号 ID  │
                  └──────────────┘
```

**关键说明：**

- `download_data.ID` 是**作品 ID**，`mapping_data.ID` 是**账号 ID**，两者语义不同
- 表之间**无外键约束**，也无直接 JOIN 查询，各表独立运作
- `config_data` 和 `option_data` 同为配置表，区别仅在于值的类型约束（布尔 vs 字符串）
- `download_data` 受 `config_data.Record` 开关控制：Record=0 时不记录、不查重

## 代码入口

所有数据库操作封装在 `src/manager/database.py` 的 `Database` 类中，通过以下模块调用：

- `src/manager/recorder.py` — `DownloadRecorder` 类操作 `download_data`
- `src/manager/cache.py` — `Cache` 类操作 `mapping_data`
- `src/application/TikTokDownloader.py` — 启动时读取 `config_data` 和 `option_data`
