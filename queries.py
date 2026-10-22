import os
from falkordb import FalkorDB

class OpenAlexRepository:
    def __init__(self, host="localhost", port=6379, password=None, graph_name="falkordb_provisional_excluded88_v1"):
        """
        Khởi tạo kết nối tới FalkorDB Repository.
        Tự động nhận mật khẩu từ tham số, biến môi trường FALKORDB_PASSWORD, hoặc file .env
        """
        if password is None:
            password = os.getenv("FALKORDB_PASSWORD")
            if not password and os.path.exists(".env"):
                with open(".env", "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip().startswith("FALKORDB_PASSWORD="):
                            password = line.strip().split("=", 1)[1].strip()
            if not password:
                password = "MySecretPassword123"

        try:
            self.db = FalkorDB(host=host, port=port, password=password)
            self.db.connection.ping()
        except Exception:
            self.db = FalkorDB(host=host, port=port)

        self.graph_name = graph_name
        self.g = self.db.select_graph(graph_name)

    def _normalize_id(self, author_id):
        if author_id and "openalex.org/" in str(author_id):
            return str(author_id).split("/")[-1]
        return str(author_id)

    def get_author_profile(self, author_id):
        """
        1. Lấy hồ sơ học thuật của tác giả (ID và tổng số bài báo)
        """
        aid = self._normalize_id(author_id)
        q = """
        MATCH (a:Author {author_id: $aid})
        OPTIONAL MATCH (a)<-[:RESOLVED_TO]-(as:Authorship)<-[:HAS_AUTHORSHIP]-(w:Work)
        RETURN a.author_id AS id, count(DISTINCT w) AS total_works
        """
        res = self.g.query(q, {"aid": aid}).result_set
        if res and len(res) > 0:
            return {"id": res[0][0], "total_works": res[0][1]}
        return None

    def get_author_works(self, author_id, limit=10):
        """
        2. Lấy danh sách công trình của tác giả
        """
        aid = self._normalize_id(author_id)
        q = """
        MATCH (a:Author {author_id: $aid})<-[:RESOLVED_TO]-(as:Authorship)<-[:HAS_AUTHORSHIP]-(w:Work)
        RETURN w.work_id AS work_id, w.year AS year
        LIMIT $limit
        """
        res = self.g.query(q, {"aid": aid, "limit": limit}).result_set
        return [{"work_id": row[0], "year": row[1]} for row in res]

    def get_coauthors(self, author_id, limit=10):
        """
        3. Tìm danh sách đồng tác giả
        """
        aid = self._normalize_id(author_id)
        q = """
        MATCH (a:Author {author_id: $aid})-[:COAUTHORED_WITH]-(other:Author)
        RETURN other.author_id AS coauthor_id
        LIMIT $limit
        """
        res = self.g.query(q, {"aid": aid, "limit": limit}).result_set
        return [{"coauthor_id": row[0]} for row in res]

    def get_recommended_collaborators(self, author_id, limit=10):
        """
        4. Tìm các tác giả tiềm năng (đồng tác giả bậc 2 - Friends-of-Friends)
        có nhiều liên kết chung nhưng chưa từng viết bài cùng nhau, phục vụ gợi ý hợp tác và Link Prediction.
        """
        aid = self._normalize_id(author_id)
        q = """
        MATCH (a:Author {author_id: $aid})-[:COAUTHORED_WITH]-(co:Author)
        WITH a, co LIMIT 30
        MATCH (co)-[:COAUTHORED_WITH]-(potential:Author)
        WHERE potential <> a AND NOT (a)-[:COAUTHORED_WITH]-(potential)
        RETURN potential.author_id AS candidate_id, count(DISTINCT co) AS mutual_coauthors_count
        ORDER BY mutual_coauthors_count DESC
        LIMIT $limit
        """
        res = self.g.query(q, {"aid": aid, "limit": limit}).result_set
        return [{"candidate_id": row[0], "mutual_coauthors_count": row[1]} for row in res]

    def get_candidate_pairs(self, limit=100):
        """
        5. Lấy dữ liệu cho mô hình Link Prediction (các cặp tác giả có quan hệ đồng tác giả)
        """
        q = """
        MATCH (a1:Author)-[c:COAUTHORED_WITH]->(a2:Author)
        RETURN a1.author_id AS author_1, a2.author_id AS author_2, c.weight AS weight, c.first_year AS first_year, c.last_year AS last_year
        LIMIT $limit
        """
        res = self.g.query(q, {"limit": limit}).result_set
        return [
            {
                "author_1": row[0],
                "author_2": row[1],
                "weight": row[2],
                "first_year": row[3],
                "last_year": row[4]
            }
            for row in res
        ]

    def get_graph_stats(self):
        """
        Thống kê tổng quan đồ thị
        """
        node_res = self.g.query("MATCH (n) RETURN labels(n)[0] AS label, count(n) AS cnt").result_set
        counts = {row[0]: row[1] for row in node_res}
        edge_res = self.g.query("MATCH ()-[c:COAUTHORED_WITH]->() RETURN count(c)").result_set
        coauthor_cnt = edge_res[0][0] if edge_res else 0
        return {
            "Work": counts.get("Work", 0),
            "Authorship": counts.get("Authorship", 0),
            "Author": counts.get("Author", 0),
            "COAUTHORED_WITH": coauthor_cnt
        }
