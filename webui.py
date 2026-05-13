"""
Web UI 启动脚本
独立启动 Web UI 模式，无需进入主程序菜单
"""

from asyncio import run
from pathlib import Path

from src.config import Parameter, Settings
from src.custom import PROJECT_ROOT
from src.manager import Database, DownloadRecorder
from src.module import Cookie
from src.record import BaseLogger
from src.tools import ColorfulConsole
from src.webui import WebUIServer
from src.translation import switch_language


async def main():
    """启动 Web UI 服务"""
    console = ColorfulConsole()

    print("=" * 50)
    print("DouK-Downloader Web UI".center(50))
    print("=" * 50)
    print()

    # 设置中文语言（确保目录名使用中文格式）
    switch_language("zh_CN")

    # 加载配置
    settings = Settings(PROJECT_ROOT, console)
    config = settings.read()

    # Cookie 管理
    cookie = Cookie(settings, console)

    # 初始化数据库
    database = Database()
    await database.__aenter__()

    # 下载记录器
    recorder = DownloadRecorder(database, True, console)

    # Logger
    logger = BaseLogger

    # 创建 Parameter
    parameter = Parameter(
        settings,
        cookie,
        logger=logger,
        console=console,
        **config,
        recorder=recorder,
    )
    parameter.set_headers_cookie()

    # 检查 Cookie 状态
    if not parameter.cookie_state:
        console.warning("抖音 Cookie 未配置，部分功能可能无法正常使用")
        console.print("Cookie 获取教程: https://github.com/JoeanAmier/TikTokDownloader/blob/master/docs/Cookie获取教程.md")
        print()

    # 创建并启动 Web UI 服务
    server = WebUIServer(parameter, database)

    try:
        await server.run_server()
    except KeyboardInterrupt:
        print("\n正在关闭 Web UI 服务...")
    finally:
        await database.__aexit__(None, None, None)
        if parameter:
            await parameter.close_client()


if __name__ == "__main__":
    run(main())