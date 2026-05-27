# 数据保存模式说明

## 配置方式

在 `volume/settings.json` 中设置 `storage_format` 字段：

```json
"storage_format": "sql"
```

可选值：

| 值 | 说明 |
|---|---|
| `""` | 不保存任何详细数据（仅记录作品 ID 用于去重） |
| `"csv"` | 保存为 CSV 文件 |
| `"xlsx"` | 保存为 Excel 文件 |
| `"sql"` | 保存为 SQLite 数据库 |

当前配置：**sql**

---

## 数据库文件分布

启用 `storage_format` 后，详细数据保存到 `{root}/Data/` 目录下，按数据类型分库：

| 数据类型 | 数据库文件 | 表名规则 | 触发场景 |
|----------|-----------|----------|----------|
| 作品详情 | `DetailData.db` | `Download_{账号昵称}` | 批量下载账号作品 |
| 合辑详情 | `MixData.db` | `Download_{合辑标题}` | 下载合辑作品 |
| 搜索结果(作品) | `SearchData.db` | `Download_{关键词}` | 搜索作品 |
| 搜索结果(用户) | `SearchData.db` | `Download_{关键词}` | 搜索用户 |
| 搜索结果(直播) | `SearchData.db` | `Download_{关键词}` | 搜索直播 |
| 评论数据 | `CommentData.db` | `Download_{账号昵称}` | 下载评论 |
| 账号数据 | `UserData.db` | `Download_{账号昵称}` | 采集账号信息 |
| 热榜数据 | `BoardData.db` | `Download_{关键词}` | 采集热榜 |

> 注意：这些数据库与 `DouK-Downloader.db`（主配置/去重库）是独立的。

---

## 作品详情字段（DetailData）

下载账号作品时保存的全部字段：

| 字段名 | 中文含义 | 类型 | 提取来源 |
|--------|---------|------|----------|
| `type` | 作品类型 | TEXT | 视频 / 图集 / 实况 |
| `collection_time` | 采集时间 | TEXT | 本地采集时刻 |
| `uid` | UID | TEXT | `data.author.uid` |
| `sec_uid` | SEC_UID | TEXT | `data.author.sec_uid` |
| `unique_id` | ID | TEXT | `data.author.unique_id` |
| `id` | 作品ID | TEXT | `data.aweme_id` |
| **`desc`** | **作品描述** | **TEXT** | **`data.desc`（即文案）** |
| `text_extra` | 作品话题 | TEXT | `data.text_extra` |
| `duration` | 视频时长 | TEXT | `data.video.duration` |
| `height` | 视频高度 | INTEGER | `data.video.bit_rate` |
| `width` | 视频宽度 | INTEGER | `data.video.bit_rate` |
| `share_url` | 作品链接 | TEXT | 根据类型拼接生成 |
| `create_time` | 发布时间 | TEXT | `data.create_time` |
| `uri` | 视频URI | TEXT | `data.video.play_addr.uri` |
| `nickname` | 账号昵称 | TEXT | `data.author.nickname` |
| `user_age` | 年龄 | INTEGER | `data.author.user_age` |
| `signature` | 账号签名 | TEXT | `data.author.signature` |
| `downloads` | 下载地址 | TEXT | `data.video.bit_rate` |
| `music_author` | 音乐作者 | TEXT | `data.music.author` |
| `music_title` | 音乐标题 | TEXT | `data.music.title` |
| `music_url` | 音乐链接 | TEXT | `data.music.play_url` |
| `static_cover` | 静态封面 | TEXT | `data.video.cover` |
| `dynamic_cover` | 动态封面 | TEXT | `data.video.dynamic_cover` |
| `tag` | 隐藏标签 | TEXT | `data.*` |
| `digg_count` | 点赞数量 | INTEGER | `data.statistics.digg_count` |
| `comment_count` | 评论数量 | INTEGER | `data.statistics.comment_count` |
| `collect_count` | 收藏数量 | INTEGER | `data.statistics.collect_count` |
| `share_count` | 分享数量 | INTEGER | `data.statistics.share_count` |
| `play_count` | 播放数量 | INTEGER | `data.statistics.play_count` |
| `extra` | 额外信息 | TEXT | `data.anchor_info`（JSON） |

---

## 评论数据字段（CommentData）

| 字段名 | 中文含义 | 类型 |
|--------|---------|------|
| `collection_time` | 采集时间 | TEXT |
| `cid` | 评论ID | TEXT |
| `create_time` | 评论时间 | TEXT |
| `uid` | UID | TEXT |
| `sec_uid` | SEC_UID | TEXT |
| `nickname` | 账号昵称 | TEXT |
| `signature` | 账号签名 | TEXT |
| `user_age` | 年龄 | INTEGER |
| `ip_label` | IP归属地 | TEXT |
| `text` | 评论内容 | TEXT |
| `sticker` | 评论表情 | TEXT |
| `image` | 评论图片 | TEXT |
| `digg_count` | 点赞数量 | INTEGER |
| `reply_comment_total` | 回复数量 | INTEGER |
| `reply_id` | 回复ID | TEXT |
| `reply_to_reply_id` | 回复对象 | TEXT |

---

## 账号数据字段（UserData）

| 字段名 | 中文含义 | 类型 |
|--------|---------|------|
| `collection_time` | 采集时间 | TEXT |
| `nickname` | 昵称 | TEXT |
| `url` | 账号链接 | TEXT |
| `signature` | 账号签名 | TEXT |
| `unique_id` | 抖音号 | TEXT |
| `user_age` | 年龄 | INTEGER |
| `gender` | 性别 | TEXT |
| `country` | 国家 | TEXT |
| `province` | 省份 | TEXT |
| `city` | 城市 | TEXT |
| `district` | 地区 | TEXT |
| `ip_location` | IP归属地 | TEXT |
| `verify` | 标签 | TEXT |
| `enterprise` | 企业 | TEXT |
| `sec_uid` | SEC_UID | TEXT |
| `uid` | UID | TEXT |
| `short_id` | SHORT_ID | TEXT |
| `avatar` | 头像链接 | TEXT |
| `cover` | 背景图链接 | TEXT |
| `aweme_count` | 作品数量 | INTEGER |
| `total_favorited` | 获赞数量 | INTEGER |
| `favoriting_count` | 喜欢数量 | INTEGER |
| `follower_count` | 粉丝数量 | INTEGER |
| `following_count` | 关注数量 | INTEGER |
| `max_follower_count` | 粉丝最大值 | INTEGER |

---

## 与 DouK-Downloader.db 的关系

`DouK-Downloader.db` 是主数据库，与数据存储数据库各自独立：

```
DouK-Downloader.db          {root}/Data/DetailData.db
┌──────────────────┐        ┌──────────────────────┐
│ config_data      │        │ Download_拿拿不了铁    │
│ (开关配置)        │        │  - type, desc, id...  │
│                  │        ├──────────────────────┤
│ option_data      │        │ Download_云姑娘       │
│ (选项配置)        │        │  - type, desc, id...  │
│                  │        └──────────────────────┘
│ download_data    │
│ (下载去重,仅ID)   │
│
│ mapping_data     │
│ (账号映射缓存)    │
└──────────────────┘
```

- `download_data.ID` = 作品 ID（用于去重判断）
- `DetailData.db` 中的 `id` 字段 = 同一个作品 ID（含完整信息）
- 两者**无外键关联**，通过 ID 值隐性对应
