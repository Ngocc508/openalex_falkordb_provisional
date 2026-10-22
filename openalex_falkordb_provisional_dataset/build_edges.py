import os
import sys
import time
from falkordb import FalkorDB
from tqdm import tqdm

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

GRAPH_NAME = "falkordb_provisional_excluded88_v1"

def get_password():
    pwd = os.getenv("FALKORDB_PASSWORD")
    if pwd:
        return pwd
    if os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("FALKORDB_PASSWORD="):
                    return line.strip().split("=", 1)[1].strip()
    return "MySecretPassword123"

password = get_password()
print(f"Đang kết nối tới FalkorDB (graph: {GRAPH_NAME})...")
try:
    db = FalkorDB(host="localhost", port=6379, password=password)
    db.connection.ping()
except Exception:
    db = FalkorDB(host="localhost", port=6379)

g = db.select_graph(GRAPH_NAME)

print("Đang lấy danh sách các bài báo...")
res = g.query("MATCH (w:Work) RETURN w.work_id").result_set
work_ids = [row[0] for row in res]
print(f"Tìm thấy {len(work_ids)} bài báo. Bắt đầu xử lý theo từng đợt...")

BATCH_SIZE = 200  # Xử lý theo đợt các bài báo bằng UNWIND
query = """
UNWIND $batch AS wid
MATCH (w:Work {work_id: wid})-[:HAS_AUTHORSHIP]->(as:Authorship)-[:RESOLVED_TO]->(a:Author)
WITH w, collect(DISTINCT a) AS authors
WHERE size(authors) > 1 AND size(authors) <= 50
UNWIND authors AS a1
UNWIND authors AS a2
WITH a1, a2, w
WHERE a1.author_id < a2.author_id
MERGE (a1)-[c:COAUTHORED_WITH]->(a2)
ON CREATE SET c.weight = 1, c.first_year = w.year, c.last_year = w.year
ON MATCH SET c.weight = c.weight + 1, 
             c.first_year = CASE WHEN w.year < c.first_year THEN w.year ELSE c.first_year END,
             c.last_year = CASE WHEN w.year > c.last_year THEN w.year ELSE c.last_year END
"""

start_time = time.time()
for i in tqdm(range(0, len(work_ids), BATCH_SIZE), desc="Tiến độ tạo cạnh"):
    batch = work_ids[i:i+BATCH_SIZE]
    g.query(query, {"batch": batch})

elapsed = time.time() - start_time
print(f"TẠO CẠNH ĐỒNG TÁC GIẢ HOÀN TẤT! Thời gian: {elapsed:.2f}s ({elapsed/60:.2f} phút)")

# Đếm tổng số cạnh COAUTHORED_WITH vừa tạo
res_edges = g.query("MATCH ()-[c:COAUTHORED_WITH]->() RETURN count(c)").result_set
print(f"Tổng số quan hệ COAUTHORED_WITH: {res_edges[0][0]}")