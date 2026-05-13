"""
WebUI 管理器
封装 TikTok 类的核心下载能力，提供适合 Web API 调用的接口
"""

from asyncio import Lock
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from ..application.main_terminal import TikTok
from ..link import Extractor as LinkExtractor
from ..link import ExtractorTikTok
from ..storage import RecordManager
from ..tools import ColorfulConsole

if TYPE_CHECKING:
    from ..config import Parameter
    from ..manager import Database


@dataclass
class DownloadProgress:
    """下载进度状态"""
    total: int = 0
    current: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0
    status: str = "idle"  # idle, running, completed, error
    message: str = ""
    nickname: str = ""
    mark: str = ""


@dataclass
class DownloadResult:
    """下载结果"""
    success: bool
    message: str
    data: dict = field(default_factory=dict)


class WebUIManager(TikTok):
    """
    WebUI 管理器
    继承 TikTok 类，封装账号下载和作品下载能力
    """

    def __init__(
        self,
        parameter: "Parameter",
        database: "Database",
        server_mode: bool = True,
    ):
        super().__init__(parameter, database, server_mode)
        self.progress = DownloadProgress()
        self.progress_lock = Lock()
        self.console_webui = ColorfulConsole()

    def reset_progress(self):
        """重置下载进度"""
        self.progress = DownloadProgress()

    async def update_progress(
        self,
        total: int = None,
        current: int = None,
        success: int = None,
        failed: int = None,
        skipped: int = None,
        status: str = None,
        message: str = None,
        nickname: str = None,
        mark: str = None,
    ):
        """更新下载进度"""
        async with self.progress_lock:
            if total is not None:
                self.progress.total = total
            if current is not None:
                self.progress.current = current
            if success is not None:
                self.progress.success = success
            if failed is not None:
                self.progress.failed = failed
            if skipped is not None:
                self.progress.skipped = skipped
            if status is not None:
                self.progress.status = status
            if message is not None:
                self.progress.message = message
            if nickname is not None:
                self.progress.nickname = nickname
            if mark is not None:
                self.progress.mark = mark

    def get_progress(self) -> dict:
        """获取当前下载进度"""
        return {
            "total": self.progress.total,
            "current": self.progress.current,
            "success": self.progress.success,
            "failed": self.progress.failed,
            "skipped": self.progress.skipped,
            "status": self.progress.status,
            "message": self.progress.message,
            "nickname": self.progress.nickname,
            "mark": self.progress.mark,
        }

    async def extract_sec_user_id(self, url: str) -> str:
        """
        从账号链接提取 sec_user_id
        :param url: 账号主页链接
        :return: sec_user_id 或空字符串
        """
        try:
            links = await self.links.run(url, "user")
            return links[0] if links else ""
        except Exception as e:
            self.logger.error(f"提取 sec_user_id 失败: {e}")
            return ""

    async def extract_detail_id(self, url: str) -> list[str]:
        """
        从作品链接提取作品 ID
        :param url: 作品链接
        :return: 作品 ID 列表
        """
        try:
            ids = await self.links.run(url)
            self.logger.info(f"提取作品 ID 结果: {ids}")
            if ids and isinstance(ids, list):
                valid_ids = [i for i in ids if i and isinstance(i, str)]
                return valid_ids
            return []
        except Exception as e:
            self.logger.error(f"提取作品 ID 失败: {e}")
            return []

    async def get_account_info(self, url: str) -> DownloadResult:
        """
        获取账号基本信息（不执行下载）
        使用 User 接口获取完整信息（包含 aweme_count）
        :param url: 账号主页链接
        :return: DownloadResult
        """
        sec_user_id = await self.extract_sec_user_id(url)
        if not sec_user_id:
            return DownloadResult(
                success=False,
                message="无法从链接提取账号 ID，请检查链接格式",
            )

        try:
            # 使用 User 接口获取完整信息（包含 aweme_count）
            from ..interface import User
            info = await User(
                self.parameter,
                None,
                None,
                sec_user_id,
            ).run()

            if not info:
                return DownloadResult(
                    success=False,
                    message="获取账号信息失败，请检查 Cookie 登录状态",
                )

            return DownloadResult(
                success=True,
                message="获取账号信息成功",
                data={
                    "sec_user_id": sec_user_id,
                    "uid": info.get("uid", ""),
                    "nickname": info.get("nickname", ""),
                    "unique_id": info.get("unique_id", ""),
                    "signature": info.get("signature", ""),
                    "avatar": info.get("avatar_larger", {}).get("url_list", [""])[0] if info.get("avatar_larger") else "",
                    "follower_count": info.get("follower_count", 0),
                    "following_count": info.get("following_count", 0),
                    "aweme_count": info.get("aweme_count", 0),
                    "favoriting_count": info.get("favoriting_count", 0),
                },
            )
        except Exception as e:
            return DownloadResult(
                success=False,
                message=f"获取账号信息失败: {str(e)}",
            )

    async def download_account(
        self,
        url: str,
        tab: str = "post",
        mark: str = "",
        earliest: str = "",
        latest: str = "",
        pages: int = 0,
    ) -> DownloadResult:
        """
        执行账号作品下载
        使用 CLI 相同的下载逻辑，目录名格式：UID{id_}_{name}_发布作品
        :param url: 账号主页链接
        :param tab: 作品类型 (post/favorite/collection)
        :param mark: 自定义标识
        :param earliest: 最早日期
        :param latest: 最晚日期
        :return: DownloadResult
        """
        self.reset_progress()
        await self.update_progress(status="running", message="正在解析账号链接...")

        # 提取 sec_user_id
        sec_user_id = await self.extract_sec_user_id(url)
        if not sec_user_id:
            await self.update_progress(status="error", message="无法从链接提取账号 ID")
            return DownloadResult(
                success=False,
                message="无法从链接提取账号 ID，请检查链接格式",
            )

        # 使用 User 接口获取完整账号信息
        await self.update_progress(message="正在获取账号信息...")
        from ..interface import User
        info = await User(
            self.parameter,
            None,
            None,
            sec_user_id,
        ).run()

        nickname = info.get("nickname", "") if info else ""
        uid = info.get("uid", "") if info else ""
        await self.update_progress(
            nickname=nickname,
            mark=mark or nickname,
            message=f"正在获取 {nickname or sec_user_id} 的作品列表...",
        )

        # 使用 CLI 的标准流程处理账号下载
        result = await self.deal_account_detail(
            index=0,
            sec_user_id=sec_user_id,
            mark=mark,
            tab=tab,
            earliest=earliest,
            latest=latest,
            pages=pages,
            api=False,
            source=False,
            cookie=None,
            proxy=None,
            tiktok=False,
        )

        if result:
            # 获取实际的保存路径
            prefix = self._generate_prefix(tab)
            suffix = self._generate_suffix(tab)
            # 使用 mark 或 nickname 作为标识
            final_mark = mark or nickname
            folder_name = f"{prefix}{uid}_{final_mark}_{suffix}"
            save_path = self.parameter.root.joinpath(folder_name)

            await self.update_progress(
                status="completed",
                message=f"下载完成",
            )

            return DownloadResult(
                success=True,
                message="下载完成",
                data={
                    "nickname": nickname,
                    "uid": uid,
                    "sec_user_id": sec_user_id,
                    "mark": final_mark,
                    "save_path": str(save_path),
                },
            )
        else:
            await self.update_progress(
                status="error",
                message="下载失败或账号作品为空",
            )
            return DownloadResult(
                success=False,
                message="下载失败或账号作品为空",
                data={
                    "nickname": nickname,
                    "sec_user_id": sec_user_id,
                },
            )

    async def download_detail(self, url: str) -> DownloadResult:
        """
        执行单个作品下载
        保存到作者目录，格式：UID{uid}_{nickname}_发布作品
        :param url: 作品链接
        :return: DownloadResult
        """
        self.reset_progress()
        await self.update_progress(status="running", message="正在解析作品链接...")

        # 提取作品 ID
        ids = await self.extract_detail_id(url)
        if not ids:
            await self.update_progress(status="error", message="无法从链接提取作品 ID")
            return DownloadResult(
                success=False,
                message="无法从链接提取作品 ID，请检查链接格式",
            )

        await self.update_progress(
            total=len(ids),
            message=f"共提取到 {len(ids)} 个作品",
        )

        from ..interface import Detail
        from ..storage import RecordManager

        results = []
        save_path = ""
        success_count = 0
        failed_count = 0
        skipped_count = 0

        # 设置记录器
        record = RecordManager()
        root, params, logger = record.run(self.parameter)

        async with logger(root, console=self.console_webui, **params) as recorder:
            for i, detail_id in enumerate(ids, 1):
                await self.update_progress(current=i, message=f"正在处理作品 {detail_id}...")

                # 检查是否已下载
                if await self.parameter.recorder.has_id(detail_id):
                    skipped_count += 1
                    await self.update_progress(skipped=skipped_count)
                    continue

                try:
                    # 获取作品详情
                    detail_data = await Detail(
                        self.parameter,
                        None,
                        None,
                        detail_id,
                    ).run()

                    if not detail_data:
                        failed_count += 1
                        await self.update_progress(failed=failed_count)
                        continue

                    # 通过 extractor 处理数据（添加 type、downloads、uid、nickname 等字段）
                    processed_data = await self.extractor.run(
                        [detail_data],
                        recorder,
                        tiktok=False,
                    )

                    if not processed_data:
                        failed_count += 1
                        await self.update_progress(failed=failed_count)
                        continue

                    item = processed_data[0]

                    # 从处理后的数据中提取作者信息
                    user_id = item.get("uid", "")
                    user_name = item.get("nickname", "")

                    await self.update_progress(message=f"正在下载: {user_name} 的作品")

                    if not user_id:
                        # 没有作者信息，使用默认目录下载
                        await self.downloader.run([item], "detail", tiktok=False)
                        save_path = str(root)
                    else:
                        # 使用批量下载逻辑，保存到作者目录
                        await self.downloader.run_batch(
                            [item],
                            tiktok=False,
                            mode="post",
                            user_id=user_id,
                            user_name=user_name,
                        )
                        # 更新保存路径
                        prefix = self._generate_prefix("post")
                        suffix = self._generate_suffix("post")
                        folder_name = f"{prefix}{user_id}_{user_name}_{suffix}"
                        save_path = str(self.parameter.root.joinpath(folder_name))

                    success_count += 1
                    await self.parameter.recorder.update_id(detail_id)
                    await self.update_progress(success=success_count)

                    results.append({
                        "id": detail_id,
                        "author": user_name,
                        "uid": user_id,
                        "title": item.get("desc", "")[:50],
                        "type": item.get("type", ""),
                    })

                except Exception as e:
                    failed_count += 1
                    self.logger.error(f"下载作品 {detail_id} 失败: {e}")
                    await self.update_progress(failed=failed_count)

        await self.update_progress(
            status="completed",
            success=success_count,
            failed=failed_count,
            skipped=skipped_count,
            message=f"下载完成: 成功 {success_count}, 失败 {failed_count}, 跳过 {skipped_count}",
        )

        return DownloadResult(
            success=True,
            message="下载完成",
            data={
                "total": len(ids),
                "downloaded": success_count,
                "failed": failed_count,
                "skipped": skipped_count,
                "works": results,
                "save_path": save_path,
            },
        )

    async def get_settings(self) -> dict:
        """获取当前配置"""
        return self.parameter.get_settings_data()

    async def update_settings(self, settings: dict) -> dict:
        """更新配置"""
        await self.parameter.set_settings_data(settings)
        return self.parameter.get_settings_data()

    async def get_cookie_status(self) -> dict:
        """获取 Cookie 状态"""
        return {
            "douyin": bool(self.parameter.cookie_state),
            "tiktok": bool(self.parameter.cookie_tiktok_state),
            "douyin_valid": self.parameter.cookie_state,
            "tiktok_valid": self.parameter.cookie_tiktok_state,
        }