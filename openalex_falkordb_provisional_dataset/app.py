import os
import sys
import json
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from queries import OpenAlexRepository

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

repo = OpenAlexRepository()

HTML_PAGE = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenAlex Knowledge Graph Explorer | FalkorDB</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #0b0f19;
            --bg-card: rgba(18, 24, 39, 0.75);
            --bg-card-hover: rgba(28, 36, 56, 0.85);
            --border-color: rgba(255, 255, 255, 0.08);
            --accent-primary: #3b82f6;
            --accent-glow: rgba(59, 130, 246, 0.35);
            --accent-emerald: #10b981;
            --accent-amber: #f59e0b;
            --accent-purple: #8b5cf6;
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: radial-gradient(circle at 15% 15%, #131b2e 0%, var(--bg-base) 100%);
            color: var(--text-main);
            min-height: 100vh;
            line-height: 1.5;
            padding-bottom: 50px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 30px 20px;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 25px;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 30px;
        }

        .logo-group h1 {
            font-size: 24px;
            font-weight: 800;
            background: linear-gradient(135deg, #60a5fa, #c084fc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.5px;
        }
        .logo-group p {
            color: var(--text-muted);
            font-size: 13px;
        }

        .badge-status {
            background: rgba(16, 185, 129, 0.15);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.3);
            padding: 6px 14px;
            border-radius: 9999px;
            font-size: 12px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .pulse-dot {
            width: 8px;
            height: 8px;
            background: #10b981;
            border-radius: 50%;
            box-shadow: 0 0 10px #10b981;
            animation: pulse 1.8s infinite;
        }
        @keyframes pulse {
            0% { transform: scale(0.9); opacity: 0.8; }
            50% { transform: scale(1.3); opacity: 1; }
            100% { transform: scale(0.9); opacity: 0.8; }
        }

        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 18px;
            margin-bottom: 35px;
        }
        .stat-card {
            background: var(--bg-card);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 20px;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }
        .stat-card:hover {
            transform: translateY(-3px);
            border-color: rgba(59, 130, 246, 0.4);
            box-shadow: 0 10px 25px -5px var(--accent-glow);
        }
        .stat-card h3 {
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            color: var(--text-muted);
            margin-bottom: 8px;
        }
        .stat-card .value {
            font-size: 28px;
            font-weight: 800;
            color: #fff;
        }
        .stat-card .desc {
            font-size: 12px;
            color: #64748b;
            margin-top: 4px;
        }

        /* Tabs */
        .tab-nav {
            display: flex;
            gap: 10px;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 25px;
            padding-bottom: 5px;
        }
        .tab-btn {
            background: none;
            border: none;
            color: var(--text-muted);
            font-size: 14px;
            font-weight: 600;
            padding: 10px 18px;
            cursor: pointer;
            border-radius: 8px;
            transition: all 0.2s;
        }
        .tab-btn:hover {
            color: var(--text-main);
            background: rgba(255, 255, 255, 0.05);
        }
        .tab-btn.active {
            color: #fff;
            background: rgba(59, 130, 246, 0.2);
            border: 1px solid rgba(59, 130, 246, 0.3);
        }

        .tab-content { display: none; }
        .tab-content.active { display: block; animation: fadeIn 0.3s ease; }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(5px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* Card Section */
        .panel {
            background: var(--bg-card);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 25px;
        }
        .panel h2 {
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        /* Search Bar */
        .search-box {
            display: flex;
            gap: 12px;
            margin-bottom: 15px;
        }
        .search-input {
            flex: 1;
            background: rgba(11, 15, 25, 0.8);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 12px 16px;
            color: #fff;
            font-size: 14px;
            outline: none;
            transition: all 0.2s;
        }
        .search-input:focus {
            border-color: var(--accent-primary);
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.25);
        }
        .btn-primary {
            background: linear-gradient(135deg, #2563eb, #3b82f6);
            color: #fff;
            border: none;
            padding: 12px 24px;
            border-radius: 10px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }
        .btn-primary:hover {
            opacity: 0.92;
            transform: translateY(-1px);
        }

        .chips {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            align-items: center;
            font-size: 13px;
            color: var(--text-muted);
        }
        .chip {
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid var(--border-color);
            padding: 4px 10px;
            border-radius: 6px;
            cursor: pointer;
            font-family: 'Fira Code', monospace;
            font-size: 12px;
            transition: all 0.2s;
        }
        .chip:hover {
            background: rgba(59, 130, 246, 0.2);
            color: #93c5fd;
            border-color: #3b82f6;
        }

        /* Tables */
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
            font-size: 14px;
        }
        th, td {
            padding: 12px 14px;
            text-align: left;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }
        th {
            background: rgba(255, 255, 255, 0.03);
            color: var(--text-muted);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 11px;
            letter-spacing: 0.6px;
        }
        tr:hover td {
            background: rgba(255, 255, 255, 0.02);
        }
        .code-pill {
            background: rgba(147, 197, 253, 0.1);
            color: #93c5fd;
            padding: 2px 8px;
            border-radius: 4px;
            font-family: 'Fira Code', monospace;
            font-size: 12px;
        }

        /* Cypher Console */
        .cypher-area {
            width: 100%;
            height: 100px;
            background: #060911;
            border: 1px solid var(--border-color);
            border-radius: 10px;
            color: #38bdf8;
            font-family: 'Fira Code', monospace;
            font-size: 13px;
            padding: 14px;
            outline: none;
            resize: vertical;
            margin-bottom: 12px;
        }
        .cypher-area:focus {
            border-color: var(--accent-primary);
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo-group">
                <h1>OpenAlex Knowledge Graph Dashboard</h1>
                <p>Hệ quản trị CSDL đồ thị FalkorDB (RedisGraph Engine) • Đồ án NoSQL</p>
            </div>
            <div class="badge-status">
                <div class="pulse-dot"></div>
                <span>FalkorDB Online • Port 6379</span>
            </div>
        </header>

        <!-- Stats Grid -->
        <div class="stats-grid" id="statsGrid">
            <div class="stat-card">
                <h3>Tổng số bài báo (Works)</h3>
                <div class="value" id="statWorks">55,119</div>
                <div class="desc">Cohort giai đoạn 2018 - 2025</div>
            </div>
            <div class="stat-card">
                <h3>Lượt tác giả (Authorships)</h3>
                <div class="value" id="statAuths">1,118,807</div>
                <div class="desc">Đã kiểm soát loại bỏ 88 lỗi ngoại lệ</div>
            </div>
            <div class="stat-card">
                <h3>Hồ sơ tác giả (Authors)</h3>
                <div class="value" id="statAuthors">314,279</div>
                <div class="desc">Các nhà khoa học đã được định danh ID</div>
            </div>
            <div class="stat-card">
                <h3>Mạng lưới đồng tác giả</h3>
                <div class="value" id="statEdges">2,462,025</div>
                <div class="desc">Quan hệ COAUTHORED_WITH có trọng số</div>
            </div>
        </div>

        <!-- Navigation Tabs -->
        <div class="tab-nav">
            <button class="tab-btn active" onclick="switchTab('authorTab')">Tra cứu Tác giả</button>
            <button class="tab-btn" onclick="switchTab('analyticsTab')">Bảng xếp hạng & Phân tích</button>
            <button class="tab-btn" onclick="switchTab('candidatesTab')">Link Prediction (Ứng viên)</button>
            <button class="tab-btn" onclick="switchTab('consoleTab')">Cypher Query Console</button>
        </div>

        <!-- TAB 1: Tra cứu tác giả -->
        <div id="authorTab" class="tab-content active">
            <div class="panel">
                <h2>🔍 Tra cứu Hồ sơ & Mạng lưới Tác giả</h2>
                <div class="search-box">
                    <input type="text" id="authorSearchInput" class="search-input" placeholder="Nhập Author ID (ví dụ: A5013041243 hoặc A5045075334)..." value="A5013041243">
                    <button class="btn-primary" onclick="searchAuthor()">Tìm kiếm</button>
                </div>
                <div class="chips">
                    <span>Gợi ý mẫu:</span>
                    <span class="chip" onclick="quickSearch('A5013041243')">A5013041243 (529 bài báo)</span>
                    <span class="chip" onclick="quickSearch('A5089379373')">A5089379373 (Top 1 Năng suất)</span>
                    <span class="chip" onclick="quickSearch('A5045075334')">A5045075334 (18 bài báo)</span>
                </div>
            </div>

            <div id="authorResult" style="display: none;">
                <div class="stats-grid">
                    <div class="stat-card">
                        <h3>Mã định danh tác giả</h3>
                        <div class="value" style="font-size: 22px;" id="profileAid">-</div>
                        <div class="desc">OpenAlex Normalized ID</div>
                    </div>
                    <div class="stat-card">
                        <h3>Tổng số công trình</h3>
                        <div class="value" style="color: #60a5fa;" id="profileWorks">-</div>
                        <div class="desc">Đã công bố trong cơ sở dữ liệu</div>
                    </div>
                    <div class="stat-card">
                        <h3>Số đồng tác giả tìm thấy</h3>
                        <div class="value" style="color: #34d399;" id="profileCoauthors">-</div>
                        <div class="desc">Cộng tác viên trực tiếp</div>
                    </div>
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                    <div class="panel">
                        <h2>📚 Danh sách công trình (Works)</h2>
                        <table id="worksTable">
                            <thead>
                                <tr>
                                    <th>Work ID</th>
                                    <th>Năm xuất bản</th>
                                </tr>
                            </thead>
                            <tbody></tbody>
                        </table>
                    </div>
                    <div class="panel">
                        <h2>👥 Danh sách đồng tác giả (Co-authors)</h2>
                        <table id="coauthorsTable">
                            <thead>
                                <tr>
                                    <th>Coauthor ID</th>
                                    <th>Hành động</th>
                                </tr>
                            </thead>
                            <tbody></tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <!-- TAB 2: Phân tích & Bảng xếp hạng -->
        <div id="analyticsTab" class="tab-content">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div class="panel">
                    <h2>🏆 Top 10 Tác giả có nhiều công trình nhất</h2>
                    <table id="topAuthorsTable">
                        <thead>
                            <tr>
                                <th>Author ID</th>
                                <th>Số bài báo</th>
                                <th>Năm đầu</th>
                                <th>Năm cuối</th>
                            </tr>
                        </thead>
                        <tbody></tbody>
                    </table>
                </div>
                <div class="panel">
                    <h2>🤝 Top 10 Cặp cộng tác bền chặt nhất</h2>
                    <table id="topPairsTable">
                        <thead>
                            <tr>
                                <th>Tác giả 1</th>
                                <th>Tác giả 2</th>
                                <th>Số bài chung</th>
                                <th>Giai đoạn</th>
                            </tr>
                        </thead>
                        <tbody></tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- TAB 3: Link Prediction Candidates -->
        <div id="candidatesTab" class="tab-content">
            <div class="panel">
                <h2>🧬 Dữ liệu huấn luyện Link Prediction (Các cặp đồng tác giả mẫu)</h2>
                <p style="color: var(--text-muted); font-size: 13px; margin-bottom: 15px;">
                    Trích xuất các cặp đỉnh (Author Nodes) kết nối qua cạnh <code>COAUTHORED_WITH</code> kèm trọng số <code>weight</code> phục vụ mô hình Graph Neural Network / Machine Learning.
                </p>
                <table id="candidatesTable">
                    <thead>
                        <tr>
                            <th>Tác giả A</th>
                            <th>Tác giả B</th>
                            <th>Trọng số (Số bài báo chung)</th>
                            <th>Năm bắt đầu</th>
                            <th>Năm gần nhất</th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
            </div>
        </div>

        <!-- TAB 4: Cypher Console -->
        <div id="consoleTab" class="tab-content">
            <div class="panel">
                <h2>⚡ Trình thực thi truy vấn Cypher trực tiếp (FalkorDB Console)</h2>
                <textarea id="cypherInput" class="cypher-area">MATCH (w:Work) RETURN w.year AS Nam_Xuat_Ban, count(w) AS So_Luong ORDER BY Nam_Xuat_Ban DESC LIMIT 10;</textarea>
                <div style="display: flex; gap: 10px; align-items: center;">
                    <button class="btn-primary" onclick="runCypher()">Chạy truy vấn</button>
                    <span id="queryLatency" style="font-size: 13px; color: #34d399;"></span>
                </div>
                <div style="overflow-x: auto; margin-top: 15px;">
                    <table id="cypherResultTable">
                        <thead></thead>
                        <tbody></tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <script>
        function switchTab(tabId) {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById(tabId).classList.add('active');

            if (tabId === 'analyticsTab') loadAnalytics();
            if (tabId === 'candidatesTab') loadCandidates();
        }

        async function searchAuthor() {
            const aid = document.getElementById('authorSearchInput').value.trim();
            if (!aid) return;
            
            const res = await fetch(`/api/author?id=${encodeURIComponent(aid)}`);
            const data = await res.json();
            
            const resCo = await fetch(`/api/coauthors?id=${encodeURIComponent(aid)}`);
            const coauthors = await resCo.json();

            document.getElementById('authorResult').style.display = 'block';
            document.getElementById('profileAid').innerText = data.profile ? data.profile.id : aid;
            document.getElementById('profileWorks').innerText = data.profile ? data.profile.total_works : 0;
            document.getElementById('profileCoauthors').innerText = coauthors.length;

            // Render works
            const tbodyW = document.querySelector('#worksTable tbody');
            tbodyW.innerHTML = '';
            (data.works || []).forEach(w => {
                const tr = document.createElement('tr');
                tr.innerHTML = `<td><span class="code-pill">${w.work_id}</span></td><td>${w.year}</td>`;
                tbodyW.appendChild(tr);
            });

            // Render coauthors
            const tbodyC = document.querySelector('#coauthorsTable tbody');
            tbodyC.innerHTML = '';
            coauthors.forEach(c => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><span class="code-pill">${c.coauthor_id}</span></td>
                    <td><button class="chip" onclick="quickSearch('${c.coauthor_id}')">Xem hồ sơ</button></td>
                `;
                tbodyC.appendChild(tr);
            });
        }

        function quickSearch(aid) {
            document.getElementById('authorSearchInput').value = aid;
            document.querySelectorAll('.tab-btn')[0].click();
            searchAuthor();
        }

        async function loadAnalytics() {
            const r1 = await fetch('/api/top_authors?limit=10');
            const authors = await r1.json();
            const tbA = document.querySelector('#topAuthorsTable tbody');
            tbA.innerHTML = '';
            authors.forEach(a => {
                const tr = document.createElement('tr');
                tr.innerHTML = `<td><span class="code-pill">${a.author_id}</span></td><td><b>${a.total_works}</b></td><td>${a.first_pub_year}</td><td>${a.latest_pub_year}</td>`;
                tbA.appendChild(tr);
            });

            const r2 = await fetch('/api/top_collaborations?limit=10');
            const pairs = await r2.json();
            const tbP = document.querySelector('#topPairsTable tbody');
            tbP.innerHTML = '';
            pairs.forEach(p => {
                const tr = document.createElement('tr');
                tr.innerHTML = `<td><span class="code-pill">${p.author_1}</span></td><td><span class="code-pill">${p.author_2}</span></td><td><b>${p.weight}</b></td><td>${p.first_year} - ${p.last_year}</td>`;
                tbP.appendChild(tr);
            });
        }

        async function loadCandidates() {
            const res = await fetch('/api/candidates?limit=20');
            const candidates = await res.json();
            const tbody = document.querySelector('#candidatesTable tbody');
            tbody.innerHTML = '';
            candidates.forEach(c => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><span class="code-pill">${c.author_1}</span></td>
                    <td><span class="code-pill">${c.author_2}</span></td>
                    <td><b style="color: #60a5fa;">${c.weight}</b></td>
                    <td>${c.first_year}</td>
                    <td>${c.last_year}</td>
                `;
                tbody.appendChild(tr);
            });
        }

        async function runCypher() {
            const query = document.getElementById('cypherInput').value.trim();
            if (!query) return;

            const t0 = performance.now();
            const res = await fetch('/api/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: query })
            });
            const data = await res.json();
            const dt = (performance.now() - t0).toFixed(2);
            document.getElementById('queryLatency').innerText = `⚡ Thời gian thực thi: ${dt} ms (trả về ${data.rows ? data.rows.length : 0} dòng)`;

            const thead = document.querySelector('#cypherResultTable thead');
            const tbody = document.querySelector('#cypherResultTable tbody');
            thead.innerHTML = '';
            tbody.innerHTML = '';

            if (data.headers) {
                const trH = document.createElement('tr');
                data.headers.forEach(h => {
                    const th = document.createElement('th');
                    th.innerText = h;
                    trH.appendChild(th);
                });
                thead.appendChild(trH);
            }

            if (data.rows) {
                data.rows.forEach(r => {
                    const tr = document.createElement('tr');
                    r.forEach(v => {
                        const td = document.createElement('td');
                        td.innerText = v;
                        tr.appendChild(td);
                    });
                    tbody.appendChild(tr);
                });
            }
        }

        // Tự động load tìm kiếm ban đầu
        window.onload = () => { searchAuthor(); };
    </script>
</body>
</html>
"""

class AppHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(url.query)

        if url.path == "/" or url.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
            return

        if url.path == "/api/stats":
            stats = repo.get_graph_stats()
            self._send_json(stats)
            return

        if url.path == "/api/author":
            aid = params.get("id", [""])[0]
            profile = repo.get_author_profile(aid)
            works = repo.get_author_works(aid, limit=20)
            self._send_json({"profile": profile, "works": works})
            return

        if url.path == "/api/coauthors":
            aid = params.get("id", [""])[0]
            coauthors = repo.get_coauthors(aid, limit=20)
            self._send_json(coauthors)
            return

        if url.path == "/api/candidates":
            limit = int(params.get("limit", [20])[0])
            candidates = repo.get_candidate_pairs(limit=limit)
            self._send_json(candidates)
            return

        if url.path == "/api/top_authors":
            limit = int(params.get("limit", [10])[0])
            q = f"""
            MATCH (a:Author)<-[:RESOLVED_TO]-(as:Authorship)<-[:HAS_AUTHORSHIP]-(w:Work)
            RETURN a.author_id AS author_id, count(DISTINCT w) AS total_works, min(w.year) AS first_pub_year, max(w.year) AS latest_pub_year
            ORDER BY total_works DESC
            LIMIT {limit}
            """
            res = repo.g.query(q).result_set
            data = [{"author_id": r[0], "total_works": r[1], "first_pub_year": r[2], "latest_pub_year": r[3]} for r in res]
            self._send_json(data)
            return

        if url.path == "/api/top_collaborations":
            limit = int(params.get("limit", [10])[0])
            q = f"""
            MATCH (a1:Author)-[c:COAUTHORED_WITH]->(a2:Author)
            RETURN a1.author_id AS author_1, a2.author_id AS author_2, c.weight AS weight, c.first_year AS first_year, c.last_year AS last_year
            ORDER BY c.weight DESC
            LIMIT {limit}
            """
            res = repo.g.query(q).result_set
            data = [{"author_1": r[0], "author_2": r[1], "weight": r[2], "first_year": r[3], "last_year": r[4]} for r in res]
            self._send_json(data)
            return

        self.send_error(404, "Not Found")

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        if url.path == "/api/query":
            content_len = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_len)
            req = json.loads(post_body.decode('utf-8'))
            query = req.get("query", "")
            try:
                res = repo.g.query(query)
                headers = [h[1] for h in getattr(res, "header", [])] if hasattr(res, "header") else []
                self._send_json({"headers": headers, "rows": res.result_set})
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        self.send_error(404, "Not Found")

def run_server(port=8080):
    server_address = ('', port)
    httpd = HTTPServer(server_address, AppHandler)
    print("==================================================")
    print(f"  OPENALEX FALKORDB WEB APP ĐANG CHẠY TẠI:        ")
    print(f"  👉 http://localhost:{port}                        ")
    print("==================================================")
    httpd.serve_forever()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_server(port)
