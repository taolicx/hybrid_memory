"""WebUI 服务器模块"""
import asyncio
import json
from pathlib import Path
from typing import Any

from aiohttp import web


class WebUIServer:
    """WebUI 服务器 - 提供记忆管理界面"""

    def __init__(self, long_term_memory: Any, short_term_memory: Any, config: dict, data_dir: str):
        self.long_term_memory = long_term_memory
        self.short_term_memory = short_term_memory
        self.config = config
        self.data_dir = Path(data_dir)
        
        self.host = config.get("host", "127.0.0.1")
        self.port = config.get("port", 9241)
        self.username = config.get("username", "admin")
        self.password = config.get("password", "admin")
        
        self.app = web.Application()
        self._setup_routes()
        self.runner: web.AppRunner | None = None
        self._authenticated_sessions: dict[str, bool] = {}

    def _setup_routes(self):
        """设置路由"""
        self.app.router.add_get("/", self.handle_index)
        self.app.router.add_get("/api/memories/long", self.handle_get_long_memories)
        self.app.router.add_get("/api/memories/short", self.handle_get_short_memories)
        self.app.router.add_post("/api/memories/long", self.handle_add_long_memory)
        self.app.router.add_post("/api/memories/short", self.handle_add_short_memory)
        self.app.router.add_put("/api/memories/long/{id}", self.handle_update_long_memory)
        self.app.router.add_put("/api/memories/short/{id}", self.handle_update_short_memory)
        self.app.router.add_delete("/api/memories/long/{id}", self.handle_delete_long_memory)
        self.app.router.add_delete("/api/memories/short/{id}", self.handle_delete_short_memory)
        self.app.router.add_get("/api/stats", self.handle_stats)
        self.app.router.add_post("/api/login", self.handle_login)
        self.app.router.add_post("/api/logout", self.handle_logout)

    async def start(self):
        """启动服务器"""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, self.host, self.port)
        await site.start()

    async def stop(self):
        """停止服务器"""
        if self.runner:
            await self.runner.cleanup()

    def _check_auth(self, request: web.Request) -> bool:
        """检查认证"""
        session_id = request.cookies.get("session_id")
        return session_id and self._authenticated_sessions.get(session_id, False)

    async def handle_index(self, request: web.Request) -> web.Response:
        """主页"""
        html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HybridMemory 管理面板</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { background: #fff; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .header h1 { color: #333; }
        .nav { display: flex; gap: 10px; margin-top: 15px; }
        .nav button { padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; background: #e0e0e0; }
        .nav button.active { background: #4CAF50; color: white; }
        .content { background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .tab { display: none; }
        .tab.active { display: block; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #f5f5f5; font-weight: 600; }
        .btn { padding: 6px 12px; border: none; border-radius: 4px; cursor: pointer; margin: 2px; }
        .btn-primary { background: #4CAF50; color: white; }
        .btn-danger { background: #f44336; color: white; }
        .btn-edit { background: #2196F3; color: white; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; font-weight: 500; }
        .form-group input, .form-group textarea { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
        .form-group textarea { min-height: 100px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .stat-card { background: #f9f9f9; padding: 15px; border-radius: 8px; text-align: center; }
        .stat-card .number { font-size: 32px; font-weight: bold; color: #4CAF50; }
        .stat-card .label { color: #666; margin-top: 5px; }
        .login-form { max-width: 400px; margin: 100px auto; }
        .login-form input { margin-bottom: 15px; }
        .login-form button { width: 100%; padding: 12px; }
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); }
        .modal.active { display: flex; align-items: center; justify-content: center; }
        .modal-content { background: white; padding: 20px; border-radius: 8px; max-width: 500px; width: 90%; }
        .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
        .modal-close { background: none; border: none; font-size: 24px; cursor: pointer; }
    </style>
</head>
<body>
    <div class="container" id="app">
        <div class="header">
            <h1>HybridMemory 管理面板</h1>
            <div class="nav">
                <button class="active" onclick="showTab('stats')">统计</button>
                <button onclick="showTab('long')">长期记忆</button>
                <button onclick="showTab('short')">短期记忆</button>
                <button onclick="logout()">退出</button>
            </div>
        </div>
        
        <div class="content">
            <div id="stats" class="tab active">
                <div class="stats">
                    <div class="stat-card">
                        <div class="number" id="longCount">-</div>
                        <div class="label">长期记忆</div>
                    </div>
                    <div class="stat-card">
                        <div class="number" id="sessionCount">-</div>
                        <div class="label">会话数</div>
                    </div>
                    <div class="stat-card">
                        <div class="number" id="messageCount">-</div>
                        <div class="label">消息数</div>
                    </div>
                </div>
                <button class="btn btn-primary" onclick="loadStats()">刷新</button>
            </div>
            
            <div id="long" class="tab">
                <h2>长期记忆</h2>
                <div class="form-group">
                    <input type="text" id="longSearch" placeholder="搜索记忆..." onkeyup="searchLongTerm()">
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>内容</th>
                            <th>重要性</th>
                            <th>创建时间</th>
                            <th>操作</th>
                        </tr>
                    </thead>
                    <tbody id="longTable"></tbody>
                </table>
            </div>
            
            <div id="short" class="tab">
                <h2>短期记忆</h2>
                <table>
                    <thead>
                        <tr>
                            <th>会话ID</th>
                            <th>消息数</th>
                            <th>操作</th>
                        </tr>
                    </thead>
                    <tbody id="shortTable"></tbody>
                </table>
            </div>
        </div>
    </div>
    
    <div class="modal" id="editModal">
        <div class="modal-content">
            <div class="modal-header">
                <h3 id="modalTitle">编辑记忆</h3>
                <button class="modal-close" onclick="closeModal()">&times;</button>
            </div>
            <div class="form-group">
                <label>内容</label>
                <textarea id="editContent"></textarea>
            </div>
            <input type="hidden" id="editId">
            <input type="hidden" id="editType">
            <button class="btn btn-primary" onclick="saveEdit()">保存</button>
        </div>
    </div>
    
    <script>
        let isLoggedIn = false;
        
        function checkAuth() {
            const token = localStorage.getItem('token');
            if (!token) {
                showLogin();
            } else {
                isLoggedIn = true;
                loadStats();
                loadLongMemories();
                loadShortMemories();
            }
        }
        
        function showLogin() {
            document.getElementById('app').innerHTML = '<div class="login-form"><h2>登录</h2><input type="text" id="username" placeholder="用户名"><input type="password" id="password" placeholder="密码"><button class="btn btn-primary" onclick="login()">登录</button></div>';
        }
        
        async function login() {
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            
            const resp = await fetch('/api/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({username, password})
            });
            
            if (resp.ok) {
                const data = await resp.json();
                localStorage.setItem('token', data.token);
                location.reload();
            } else {
                alert('登录失败');
            }
        }
        
        function logout() {
            localStorage.removeItem('token');
            location.reload();
        }
        
        function showTab(tabId) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.nav button').forEach(b => b.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            event.target.classList.add('active');
        }
        
        async function loadStats() {
            const resp = await fetch('/api/stats');
            const data = await resp.json();
            document.getElementById('longCount').textContent = data.long_count;
            document.getElementById('sessionCount').textContent = data.session_count;
            document.getElementById('messageCount').textContent = data.message_count;
        }
        
        async function loadLongMemories() {
            const resp = await fetch('/api/memories/long');
            const memories = await resp.json();
            const tbody = document.getElementById('longTable');
            tbody.innerHTML = memories.map(m => `
                <tr>
                    <td>${m.id}</td>
                    <td>${m.content.substring(0, 100)}${m.content.length > 100 ? '...' : ''}</td>
                    <td>${m.importance}</td>
                    <td>${new Date(m.created_at * 1000).toLocaleString()}</td>
                    <td>
                        <button class="btn btn-edit" onclick="editMemory(${m.id}, 'long', '${escapeHtml(m.content)}')">编辑</button>
                        <button class="btn btn-danger" onclick="deleteMemory(${m.id}, 'long')">删除</button>
                    </td>
                </tr>
            `).join('');
        }
        
        async function loadShortMemories() {
            const resp = await fetch('/api/memories/short');
            const sessions = await resp.json();
            const tbody = document.getElementById('shortTable');
            tbody.innerHTML = sessions.map(s => `
                <tr>
                    <td>${s.session_id}</td>
                    <td>${s.message_count}</td>
                    <td>
                        <button class="btn btn-danger" onclick="clearSession('${s.session_id}')">清除</button>
                    </td>
                </tr>
            `).join('');
        }
        
        function searchLongTerm() {
            const query = document.getElementById('longSearch').value.toLowerCase();
            const rows = document.querySelectorAll('#longTable tr');
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(query) ? '' : 'none';
            });
        }
        
        function editMemory(id, type, content) {
            document.getElementById('editId').value = id;
            document.getElementById('editType').value = type;
            document.getElementById('editContent').value = unescapeHtml(content);
            document.getElementById('modalTitle').textContent = '编辑' + (type === 'long' ? '长期' : '短期') + '记忆';
            document.getElementById('editModal').classList.add('active');
        }
        
        function closeModal() {
            document.getElementById('editModal').classList.remove('active');
        }
        
        async function saveEdit() {
            const id = document.getElementById('editId').value;
            const type = document.getElementById('editType').value;
            const content = document.getElementById('editContent').value;
            
            const resp = await fetch(`/api/memories/${type}/${id}`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({content})
            });
            
            if (resp.ok) {
                closeModal();
                if (type === 'long') loadLongMemories();
            } else {
                alert('保存失败');
            }
        }
        
        async function deleteMemory(id, type) {
            if (!confirm('确定要删除这条记忆吗？')) return;
            
            const resp = await fetch(`/api/memories/${type}/${id}`, {method: 'DELETE'});
            if (resp.ok) {
                if (type === 'long') loadLongMemories();
                loadStats();
            }
        }
        
        async function clearSession(sessionId) {
            if (!confirm('确定要清除这个会话的记忆吗？')) return;
            
            const resp = await fetch(`/api/memories/short/${sessionId}`, {method: 'DELETE'});
            if (resp.ok) {
                loadShortMemories();
                loadStats();
            }
        }
        
        function escapeHtml(text) {
            return text.replace(/'/g, "\\'").replace(/"/g, '\\"');
        }
        
        function unescapeHtml(text) {
            return text.replace(/\\'/g, "'").replace(/\\"/g, '"');
        }
        
        checkAuth();
    </script>
</body>
</html>"""
        return web.Response(text=html, content_type="text/html")

    async def handle_login(self, request: web.Request) -> web.Response:
        """处理登录"""
        try:
            data = await request.json()
            if data.get("username") == self.username and data.get("password") == self.password:
                import uuid
                session_id = str(uuid.uuid4())
                self._authenticated_sessions[session_id] = True
                return web.json_response({"success": True, "token": session_id})
        except Exception:
            pass
        return web.json_response({"success": False}, status=401)

    async def handle_logout(self, request: web.Request) -> web.Response:
        """处理登出"""
        return web.json_response({"success": True})

    async def handle_stats(self, request: web.Request) -> web.Response:
        """获取统计"""
        long_count = await self.long_term_memory.get_memory_count()
        short_stats = self.short_term_memory.get_stats()
        
        return web.json_response({
            "long_count": long_count,
            "session_count": short_stats.get("session_count", 0),
            "message_count": short_stats.get("message_count", 0)
        })

    async def handle_get_long_memories(self, request: web.Request) -> web.Response:
        """获取长期记忆列表"""
        limit = int(request.query.get("limit", 100))
        offset = int(request.query.get("offset", 0))
        memories = await self.long_term_memory.get_all_memories(limit, offset)
        return web.json_response(memories)

    async def handle_get_short_memories(self, request: web.Request) -> web.Response:
        """获取短期记忆列表"""
        sessions = self.short_term_memory.get_all_sessions()
        return web.json_response(sessions)

    async def handle_add_long_memory(self, request: web.Request) -> web.Response:
        """添加长期记忆"""
        try:
            data = await request.json()
            memory_id = await self.long_term_memory.add_memory(
                content=data.get("content", ""),
                session_id=data.get("session_id", "manual"),
                importance=data.get("importance", 0.5)
            )
            return web.json_response({"id": memory_id})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def handle_add_short_memory(self, request: web.Request) -> web.Response:
        """添加短期记忆"""
        try:
            data = await request.json()
            message_id = self.short_term_memory.add_message(
                session_id=data.get("session_id", "manual"),
                role=data.get("role", "user"),
                content=data.get("content", "")
            )
            return web.json_response({"id": message_id})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def handle_update_long_memory(self, request: web.Request) -> web.Response:
        """更新长期记忆"""
        memory_id = int(request.match_info["id"])
        data = await request.json()
        success = await self.long_term_memory.update_memory(memory_id, data.get("content", ""))
        return web.json_response({"success": success})

    async def handle_update_short_memory(self, request: web.Request) -> web.Response:
        """更新短期记忆"""
        memory_id = int(request.match_info["id"])
        data = await request.json()
        success = self.short_term_memory.update_memory(memory_id, data.get("content", ""))
        return web.json_response({"success": success})

    async def handle_delete_long_memory(self, request: web.Request) -> web.Response:
        """删除长期记忆"""
        memory_id = int(request.match_info["id"])
        success = await self.long_term_memory.delete_memory(memory_id)
        return web.json_response({"success": success})

    async def handle_delete_short_memory(self, request: web.Request) -> web.Response:
        """删除短期记忆"""
        session_id = request.match_info["id"]
        self.short_term_memory.clear_session(session_id)
        return web.json_response({"success": True})