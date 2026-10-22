import os
import sys
import csv
import json
from queries import OpenAlexRepository

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

EXPORT_DIR = "exports"

def export_data():
    print("==================================================")
    print("       XUẤT DỮ LIỆU ĐỒ THỊ (EXPORT GRAPH DATA)    ")
    print("==================================================")
    
    os.makedirs(EXPORT_DIR, exist_ok=True)
    repo = OpenAlexRepository()
    
    # 1. Export tổng quan đồ thị
    print("\n1. Đang xuất thống kê tổng quan (graph_summary_stats.json)...")
    stats = repo.get_graph_stats()
    stats_file = os.path.join(EXPORT_DIR, "graph_summary_stats.json")
    with open(stats_file, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=4)
    print(f" -> Đã xuất {stats_file}")

    # 2. Export Top 100 tác giả năng suất nhất
    print("\n2. Đang xuất Top 100 tác giả có nhiều công trình nhất (top_prolific_authors.csv)...")
    q_top_authors = """
    MATCH (a:Author)<-[:RESOLVED_TO]-(as:Authorship)<-[:HAS_AUTHORSHIP]-(w:Work)
    RETURN a.author_id AS author_id, count(DISTINCT w) AS total_works, min(w.year) AS first_pub_year, max(w.year) AS latest_pub_year
    ORDER BY total_works DESC
    LIMIT 100
    """
    res_authors = repo.g.query(q_top_authors).result_set
    authors_file = os.path.join(EXPORT_DIR, "top_prolific_authors.csv")
    with open(authors_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["author_id", "total_works", "first_pub_year", "latest_pub_year"])
        for row in res_authors:
            writer.writerow(row)
    print(f" -> Đã xuất {len(res_authors)} tác giả vào {authors_file}")

    # 3. Export mẫu 5000 cặp quan hệ đồng tác giả mạnh nhất
    print("\n3. Đang xuất mạng lưới đồng tác giả mẫu (coauthorship_network_sample.csv)...")
    q_network = """
    MATCH (a1:Author)-[c:COAUTHORED_WITH]->(a2:Author)
    RETURN a1.author_id AS author_1, a2.author_id AS author_2, c.weight AS weight, c.first_year AS first_year, c.last_year AS last_year
    ORDER BY c.weight DESC
    LIMIT 5000
    """
    res_network = repo.g.query(q_network).result_set
    network_file = os.path.join(EXPORT_DIR, "coauthorship_network_sample.csv")
    with open(network_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["author_1", "author_2", "weight", "first_year", "last_year"])
        for row in res_network:
            writer.writerow(row)
    print(f" -> Đã xuất {len(res_network)} cạnh đồng tác giả vào {network_file}")

    print("\n==================================================")
    print(f" XUẤT DỮ LIỆU HOÀN TẤT! Toàn bộ file lưu tại: {EXPORT_DIR}/")
    print("==================================================")

if __name__ == "__main__":
    export_data()
