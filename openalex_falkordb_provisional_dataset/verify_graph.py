import os
import sys
import json
import csv
from falkordb import FalkorDB

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

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
try:
    db = FalkorDB(host="localhost", port=6379, password=password)
    db.connection.ping()
except Exception:
    db = FalkorDB(host="localhost", port=6379)

g = db.select_graph("falkordb_provisional_excluded88_v1")

report = {"status": "PASSED", "checks": {}}

print("Đang kiểm định đồ thị...")

# 1. Đếm số lượng Node (Work và Authorship)
res = g.query("MATCH (n) RETURN labels(n)[0] AS label, count(n) AS cnt").result_set
counts = {row[0]: row[1] for row in res}
report["checks"]["node_counts"] = {
    "Work": counts.get("Work", 0),
    "Authorship": counts.get("Authorship", 0),
    "Author": counts.get("Author", 0)
}
assert counts.get("Work") == 55119, "LỖI: Số lượng Work không khớp!"
assert counts.get("Authorship") == 1118807, "LỖI: Số lượng Authorship không khớp!"

# 2. Kiểm tra Authorship mồ côi (không trỏ đến Work nào)
orphan_auth = g.query("MATCH (a:Authorship) WHERE NOT (a)<-[:HAS_AUTHORSHIP]-(:Work) RETURN count(a)").result_set[0][0]
report["checks"]["orphan_authorships"] = orphan_auth
assert orphan_auth == 0, "LỖI: Có Authorship mồ côi!"

# 3. Đếm số Authorship không có Author ID (Unresolved)
unresolved_auth = g.query("MATCH (a:Authorship) WHERE NOT (a)-[:RESOLVED_TO]->(:Author) RETURN count(a)").result_set[0][0]
report["checks"]["unresolved_authorships"] = unresolved_auth

# 4. Kiểm tra rò rỉ 88 occurrence bị loại
excluded_file = "provenance/excluded_occurrence_audit_v1.csv"
excluded_list = []
with open(excluded_file, encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        excluded_list.append((r["work_id"], int(r["source_authorship_index_0based"])))

leaked_count = 0
for wid, sidx in excluded_list:
    q = "MATCH (a:Authorship {source_idx: $sidx})<-[:HAS_AUTHORSHIP]-(w:Work {work_id: $wid}) RETURN count(a)"
    if g.query(q, {"sidx": sidx, "wid": wid}).result_set[0][0] > 0:
        leaked_count += 1

report["checks"]["excluded_occurrences_leaked"] = leaked_count
assert leaked_count == 0, f"LỖI NGHIÊM TRỌNG: Có {leaked_count} occurrence bị loại đã lọt vào graph!"

# 5. Đếm số lượng cạnh quan hệ COAUTHORED_WITH
res_edges = g.query("MATCH ()-[c:COAUTHORED_WITH]->() RETURN count(c)").result_set
report["checks"]["coauthored_edges"] = res_edges[0][0] if res_edges else 0

print("\n=== BÁO CÁO KIỂM ĐỊNH ===")
print(json.dumps(report, indent=4))
with open("verification_report.json", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=4)
print("\nĐã lưu báo cáo thành công vào file: verification_report.json")