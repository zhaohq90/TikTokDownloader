"""
WebUI FastAPI 服务
提供 Web UI 界面和 API 接口
"""

from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from uvicorn import Config, Server

from ..custom import SERVER_HOST, SERVER_PORT
from .manager import WebUIManager, DownloadResult

if TYPE_CHECKING:
    from ..config import Parameter
    from ..manager import Database


class AccountDownloadRequest(BaseModel):
    """账号下载请求"""
    url: str
    tab: str = "post"
    mark: str = ""
    earliest: str = ""
    latest: str = ""
    pages: int = 0


class DetailDownloadRequest(BaseModel):
    """作品下载请求"""
    url: str


class SettingsUpdateRequest(BaseModel):
    """配置更新请求"""
    cookie: str = ""
    root: str = ""
    folder_name: str = ""
    download: bool = True


class ApiResponse(BaseModel):
    """统一 API 响应格式"""
    success: bool
    message: str
    data: dict = {}


class WebUIServer:
    """
    WebUI FastAPI 服务
    """

    # WebUI 默认端口
    WEBUI_HOST = "127.0.0.1"
    WEBUI_PORT = 8080

    def __init__(
        self,
        parameter: "Parameter",
        database: "Database",
    ):
        self.parameter = parameter
        self.database = database
        self.manager = None
        self.server = None

    async def initialize(self):
        """初始化 WebUIManager"""
        self.manager = WebUIManager(
            self.parameter,
            self.database,
            server_mode=True,
        )

    def get_frontend_html(self) -> str:
        """获取前端 HTML 内容"""
        html_path = Path(__file__).parent.parent.parent / "static" / "webui" / "index.html"
        if html_path.exists():
            return html_path.read_text(encoding="utf-8")
        # 如果前端文件不存在，返回默认页面
        return self._get_default_html()

    def _get_default_html(self) -> str:
        """默认前端页面"""
        return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DouK-Downloader Web UI</title>
    <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; }
        .container { max-width: 800px; margin: 20px auto; padding: 20px; }
        .card { background: white; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .title { font-size: 24px; color: #333; margin-bottom: 20px; text-align: center; }
        .tabs { display: flex; border-bottom: 2px solid #eee; margin-bottom: 20px; }
        .tab { padding: 10px 20px; cursor: pointer; color: #666; }
        .tab.active { color: #ff2d55; border-bottom: 2px solid #ff2d55; margin-bottom: -2px; }
        .form-group { margin-bottom: 15px; }
        .form-label { display: block; margin-bottom: 5px; color: #333; font-weight: 500; }
        .form-input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; }
        .form-select { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
        .btn { padding: 12px 24px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; }
        .btn-primary { background: #ff2d55; color: white; }
        .btn-primary:hover { background: #e6194b; }
        .btn-primary:disabled { background: #ccc; cursor: not-allowed; }
        .progress { margin-top: 20px; padding: 15px; background: #f9f9f9; border-radius: 4px; }
        .progress-bar { height: 20px; background: #eee; border-radius: 4px; overflow: hidden; }
        .progress-fill { height: 100%; background: #ff2d55; transition: width 0.3s; }
        .progress-text { margin-top: 10px; color: #666; }
        .result { margin-top: 20px; padding: 15px; background: #e8f5e9; border-radius: 4px; display: none; }
        .result.error { background: #ffebee; }
        .result.show { display: block; }
        .status-bar { padding: 10px 20px; background: #333; color: white; text-align: center; font-size: 12px; }
        .inline-form { display: flex; gap: 10px; align-items: center; }
        .inline-form .form-group { flex: 1; }
        .settings-item { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #eee; }
        .settings-label { color: #333; }
        .settings-value { color: #666; }
    </style>
</head>
<body>
    <div id="app" class="container">
        <h1 class="title">DouK-Downloader Web UI</h1>

        <div class="tabs">
            <div class="tab" :class="{ active: activeTab === 'account' }" @click="activeTab = 'account'">账号下载</div>
            <div class="tab" :class="{ active: activeTab === 'detail' }" @click="activeTab = 'detail'">作品下载</div>
            <div class="tab" :class="{ active: activeTab === 'settings' }" @click="activeTab = 'settings'">设置</div>
            <div class="tab" :class="{ active: activeTab === 'records' }" @click="activeTab = 'records'">记录</div>
        </div>

        <!-- 账号下载 -->
        <div class="card" v-if="activeTab === 'account'">
            <div class="form-group">
                <label class="form-label">账号主页链接</label>
                <input class="form-input" v-model="accountForm.url" placeholder="https://www.douyin.com/user/MS4wLjABAAAA..." />
            </div>
            <div class="inline-form">
                <div class="form-group">
                    <label class="form-label">作品类型</label>
                    <select class="form-select" v-model="accountForm.tab">
                        <option value="post">发布作品</option>
                        <option value="favorite">喜欢作品</option>
                        <option value="collection">收藏作品</option>
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label">自定义标识</label>
                    <input class="form-input" v-model="accountForm.mark" placeholder="可选" />
                </div>
            </div>
            <div class="inline-form">
                <div class="form-group">
                    <label class="form-label">最早日期</label>
                    <input class="form-input" type="date" v-model="accountForm.earliest" />
                </div>
                <div class="form-group">
                    <label class="form-label">最晚日期</label>
                    <input class="form-input" type="date" v-model="accountForm.latest" />
                </div>
            </div>
            <button class="btn btn-primary" @click="downloadAccount" :disabled="loading">
                {{ loading ? '下载中...' : '开始下载' }}
            </button>

            <div class="progress" v-if="progress.status !== 'idle'">
                <div class="progress-bar">
                    <div class="progress-fill" :style="{ width: progressPercent }"></div>
                </div>
                <div class="progress-text">
                    {{ progress.message }}
                    <br>成功: {{ progress.success }} | 失败: {{ progress.failed }} | 跳过: {{ progress.skipped }} | 总计: {{ progress.total }}
                </div>
            </div>

            <div class="result" :class="{ show: accountResult, error: !accountResult?.success }" v-if="accountResult">
                {{ accountResult.message }}
            </div>
        </div>

        <!-- 作品下载 -->
        <div class="card" v-if="activeTab === 'detail'">
            <div class="form-group">
                <label class="form-label">作品链接</label>
                <input class="form-input" v-model="detailForm.url" placeholder="https://v.douyin.com/xxx/" />
            </div>
            <button class="btn btn-primary" @click="downloadDetail" :disabled="loading">
                {{ loading ? '下载中...' : '开始下载' }}
            </button>

            <div class="progress" v-if="progress.status !== 'idle'">
                <div class="progress-bar">
                    <div class="progress-fill" :style="{ width: progressPercent }"></div>
                </div>
                <div class="progress-text">
                    {{ progress.message }}
                    <br>成功: {{ progress.success }} | 失败: {{ progress.failed }} | 跳过: {{ progress.skipped }} | 总计: {{ progress.total }}
                </div>
            </div>

            <div class="result" :class="{ show: detailResult, error: !detailResult?.success }" v-if="detailResult">
                {{ detailResult.message }}
            </div>
        </div>

        <!-- 设置 -->
        <div class="card" v-if="activeTab === 'settings'">
            <div class="settings-item">
                <span class="settings-label">抖音 Cookie</span>
                <span class="settings-value">{{ cookieStatus.douyin ? '已配置' : '未配置' }}</span>
            </div>
            <div class="settings-item">
                <span class="settings-label">TikTok Cookie</span>
                <span class="settings-value">{{ cookieStatus.tiktok ? '已配置' : '未配置' }}</span>
            </div>
            <div class="settings-item">
                <span class="settings-label">保存目录</span>
                <span class="settings-value">{{ settings.folder_name || 'Download' }}</span>
            </div>
            <div class="settings-item">
                <span class="settings-label">自动下载</span>
                <span class="settings-value">{{ settings.download ? '开启' : '关闭' }}</span>
            </div>
        </div>

        <!-- 记录 -->
        <div class="card" v-if="activeTab === 'records'">
            <p style="color: #666; text-align: center;">下载记录功能正在开发中...</p>
        </div>

        <div class="status-bar">
            DouK-Downloader Web UI | Cookie: {{ cookieStatus.douyin ? '已配置' : '未配置' }} | 保存目录: {{ settings.folder_name || 'Download' }}
        </div>
    </div>

    <script>
    const { createApp, ref, computed, onMounted } = Vue;

    createApp({
        setup() {
            const activeTab = ref('account');
            const loading = ref(false);
            const progress = ref({ status: 'idle', total: 0, current: 0, success: 0, failed: 0, skipped: 0, message: '' });
            const cookieStatus = ref({ douyin: false, tiktok: false });
            const settings = ref({});

            const accountForm = ref({ url: '', tab: 'post', mark: '', earliest: '', latest: '', pages: 0 });
            const detailForm = ref({ url: '' });
            const accountResult = ref(null);
            const detailResult = ref(null);

            const progressPercent = computed(() => {
                if (progress.value.total === 0) return '0%';
                return ((progress.value.current / progress.value.total) * 100) + '%';
            });

            const fetchProgress = async () => {
                if (loading.value) {
                    try {
                        const res = await fetch('/api/progress');
                        const data = await res.json();
                        progress.value = data.data;
                        if (data.data.status === 'completed' || data.data.status === 'error') {
                            loading.value = false;
                        } else {
                            setTimeout(fetchProgress, 1000);
                        }
                    } catch (e) {
                        console.error('获取进度失败', e);
                    }
                }
            };

            const downloadAccount = async () => {
                if (!accountForm.value.url) {
                    accountResult.value = { success: false, message: '请输入账号链接' };
                    return;
                }
                loading.value = true;
                progress.value = { status: 'running', total: 0, current: 0, success: 0, failed: 0, skipped: 0, message: '正在启动下载...' };
                accountResult.value = null;

                try {
                    const res = await fetch('/api/account/download', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(accountForm.value)
                    });
                    const data = await res.json();
                    accountResult.value = data;
                    progress.value = { ...progress.value, ...data.data, status: 'completed' };
                } catch (e) {
                    accountResult.value = { success: false, message: '请求失败: ' + e.message };
                }
                loading.value = false;
            };

            const downloadDetail = async () => {
                if (!detailForm.value.url) {
                    detailResult.value = { success: false, message: '请输入作品链接' };
                    return;
                }
                loading.value = true;
                progress.value = { status: 'running', total: 0, current: 0, success: 0, failed: 0, skipped: 0, message: '正在启动下载...' };
                detailResult.value = null;

                try {
                    const res = await fetch('/api/detail/download', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(detailForm.value)
                    });
                    const data = await res.json();
                    detailResult.value = data;
                    progress.value = { ...progress.value, ...data.data, status: 'completed' };
                } catch (e) {
                    detailResult.value = { success: false, message: '请求失败: ' + e.message };
                }
                loading.value = false;
            };

            const loadSettings = async () => {
                try {
                    const res = await fetch('/api/settings');
                    const data = await res.json();
                    settings.value = data.data;
                } catch (e) {
                    console.error('加载设置失败', e);
                }
            };

            const loadCookieStatus = async () => {
                try {
                    const res = await fetch('/api/cookie/status');
                    const data = await res.json();
                    cookieStatus.value = data.data;
                } catch (e) {
                    console.error('加载 Cookie 状态失败', e);
                }
            };

            onMounted(() => {
                loadSettings();
                loadCookieStatus();
            });

            return {
                activeTab, loading, progress, progressPercent, cookieStatus, settings,
                accountForm, detailForm, accountResult, detailResult,
                downloadAccount, downloadDetail
            };
        }
    }).mount('#app');
    </script>
</body>
</html>"""

    def setup_routes(self):
        """设置 API 路由"""

        @self.server.get("/", response_class=HTMLResponse)
        async def index():
            """Web UI 主页"""
            return self.get_frontend_html()

        @self.server.get("/api/settings")
        async def get_settings():
            """获取配置"""
            if not self.manager:
                raise HTTPException(status_code=500, detail="Manager not initialized")
            data = await self.manager.get_settings()
            return ApiResponse(success=True, message="获取配置成功", data=data)

        @self.server.post("/api/settings")
        async def update_settings(request: SettingsUpdateRequest):
            """更新配置"""
            if not self.manager:
                raise HTTPException(status_code=500, detail="Manager not initialized")
            data = await self.manager.update_settings(request.model_dump(exclude_none=True))
            return ApiResponse(success=True, message="更新配置成功", data=data)

        @self.server.get("/api/cookie/status")
        async def get_cookie_status():
            """获取 Cookie 状态"""
            if not self.manager:
                raise HTTPException(status_code=500, detail="Manager not initialized")
            data = await self.manager.get_cookie_status()
            return ApiResponse(success=True, message="获取 Cookie 状态成功", data=data)

        @self.server.get("/api/account/info")
        async def get_account_info(url: str):
            """获取账号信息"""
            if not self.manager:
                raise HTTPException(status_code=500, detail="Manager not initialized")
            result: DownloadResult = await self.manager.get_account_info(url)
            return ApiResponse(
                success=result.success,
                message=result.message,
                data=result.data,
            )

        @self.server.post("/api/account/download")
        async def download_account(request: AccountDownloadRequest):
            """账号作品下载"""
            if not self.manager:
                raise HTTPException(status_code=500, detail="Manager not initialized")
            result: DownloadResult = await self.manager.download_account(
                url=request.url,
                tab=request.tab,
                mark=request.mark,
                earliest=request.earliest,
                latest=request.latest,
                pages=request.pages,
            )
            return ApiResponse(
                success=result.success,
                message=result.message,
                data=result.data,
            )

        @self.server.post("/api/detail/download")
        async def download_detail(request: DetailDownloadRequest):
            """单个作品下载"""
            if not self.manager:
                raise HTTPException(status_code=500, detail="Manager not initialized")
            result: DownloadResult = await self.manager.download_detail(url=request.url)
            return ApiResponse(
                success=result.success,
                message=result.message,
                data=result.data,
            )

        @self.server.get("/api/progress")
        async def get_progress():
            """获取下载进度"""
            if not self.manager:
                raise HTTPException(status_code=500, detail="Manager not initialized")
            data = self.manager.get_progress()
            return ApiResponse(success=True, message="获取进度成功", data=data)

    async def run_server(
        self,
        host: str = None,
        port: int = None,
        log_level: str = "info",
    ):
        """启动 WebUI 服务"""
        host = host or self.WEBUI_HOST
        port = port or self.WEBUI_PORT

        # 初始化 Manager
        await self.initialize()

        # 创建 FastAPI 应用
        self.server = FastAPI(
            title="DouK-Downloader Web UI",
            version="1.0",
            description="DouK-Downloader Web UI 服务",
        )

        # 设置路由
        self.setup_routes()

        # 挂载静态文件（如果存在）
        static_path = Path(__file__).parent.parent.parent / "static"
        if static_path.exists():
            self.server.mount("/static", StaticFiles(directory=str(static_path)), name="static")

        # 启动服务
        config = Config(
            self.server,
            host=host,
            port=port,
            log_level=log_level,
        )
        server = Server(config)

        print(f"\nWeb UI 服务已启动: http://{host}:{port}")
        print("按 Ctrl+C 停止服务\n")

        await server.serve()