import os
import sys
import time
import json
import csv
from falkordb import FalkorDB
from tqdm import tqdm

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

GRAPH_NAME = "falkordb_provisional_excluded88_v1"
RELEASE_ID = "provisional_excluded88_v1_20261021T111533206730Z"

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

print("Đang dọn dẹp graph cũ (nếu có)...")
try:
    db.select_graph(GRAPH_NAME).delete()
except Exception:
    pass

g = db.select_graph(GRAPH_NAME)

print("Đang tạo Index cho Work và Author...")
try:
    g.query("CREATE INDEX FOR (w:Work) ON (w.work_id)")
except Exception as e:
    if "already indexed" not in str(e):
        raise e

try:
    g.query("CREATE INDEX FOR (a:Author) ON (a.author_id)")
except Exception as e:
    if "already indexed" not in str(e):
        raise e

print("Đang nạp map provenance...")
idx_map = {}
with open("provenance/retained_authorship_source_index_map_v1.csv", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        key = (r["work_id"], int(r["filtered_authorship_index_0based"]))
        idx_map[key] = int(r["source_authorship_index_0based"])

excluded = set()
with open("provenance/excluded_occurrence_audit_v1.csv", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        excluded.add((r["work_id"], int(r["source_authorship_index_0based"])))

print("Bắt đầu import...")
filtered_path = "data/cohort_works_2018_2025_provisional_filtered.jsonl"

batch_works = []
batch_auths = []
BATCH_SIZE = 5000

def flush_batch():
    global batch_works, batch_auths
    if batch_works:
        g.query("UNWIND $works AS w MERGE (n:Work {work_id: w.wid}) SET n.year = w.year, n.release_id = $rid", 
                {"works": batch_works, "rid": RELEASE_ID})
        batch_works = []
    if batch_auths:
        query = """
        UNWIND $auths AS a
        MATCH (w:Work {work_id: a.wid})
        CREATE (as:Authorship {source_idx: a.sidx, filtered_idx: a.fidx, release_id: $rid, raw_name: a.name})
        CREATE (w)-[:HAS_AUTHORSHIP]->(as)
        WITH as, a
        WHERE a.aid IS NOT NULL
        MERGE (au:Author {author_id: a.aid})
        CREATE (as)-[:RESOLVED_TO]->(au)
        """
        g.query(query, {"auths": batch_auths, "rid": RELEASE_ID})
        batch_auths = []

start_time = time.time()
with open(filtered_path, encoding="utf-8") as f:
    for line in tqdm(f, desc="Reading JSONL"):
        if not line.strip():
            continue
        rec = json.loads(line)
        wid = rec.get("id") or rec.get("work_id")
        
        if wid and "openalex.org/" in wid:
            wid = wid.split("/")[-1]
            
        batch_works.append({"wid": wid, "year": rec.get("publication_year")})
        
        for fidx, auth in enumerate(rec.get("authorships", [])):
            sidx = idx_map.get((wid, fidx))
            if sidx is None:
                raise RuntimeError(f"Thiếu map cho {wid} tại index {fidx}")
            if (wid, sidx) in excluded:
                raise RuntimeError(f"Lỗi: Dữ liệu bị loại lọt vào file: {wid} {sidx}")
            
            author_obj = auth.get("author") or {}
            aid = author_obj.get("id")
            if aid and "openalex.org/" in aid:
                aid = aid.split("/")[-1]

            batch_auths.append({
                "wid": wid, "sidx": sidx, "fidx": fidx, 
                "name": author_obj.get("display_name"), 
                "aid": aid
            })
            
            if len(batch_auths) >= BATCH_SIZE:
                flush_batch()

flush_batch()
elapsed = time.time() - start_time
print(f"IMPORT HOÀN TẤT! Thời gian chạy: {elapsed:.2f}s ({elapsed/60:.2f} phút)")