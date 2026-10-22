import sys
import time
import json
from queries import OpenAlexRepository

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

def run_benchmark():
    print("==================================================")
    print("      OPENALEX FALKORDB BENCHMARK SUITE          ")
    print("==================================================")
    
    repo = OpenAlexRepository()
    
    print("\n1. Kiểm tra trạng thái đồ thị...")
    stats = repo.get_graph_stats()
    print(f" - Graph: {repo.graph_name}")
    print(f" - Works: {stats.get('Work', 0):,}")
    print(f" - Authorships: {stats.get('Authorship', 0):,}")
    print(f" - Authors: {stats.get('Author', 0):,}")
    print(f" - COAUTHORED_WITH edges: {stats.get('COAUTHORED_WITH', 0):,}")
    
    if stats.get('Work', 0) == 0:
        print("\n[CẢNH BÁO] Graph chưa có dữ liệu! Hãy chạy import_graph.py trước.")
        return

    # Lấy tác giả có nhiều liên kết để benchmark thực tế và toàn diện
    print("\n2. Lấy mẫu tác giả thử nghiệm (tác giả có mạng lưới đồng tác giả)...")
    res = repo.g.query("MATCH (a:Author)-[:COAUTHORED_WITH]->() RETURN a.author_id, count(*) AS cnt ORDER BY cnt DESC LIMIT 5").result_set
    if not res:
        res = repo.g.query("MATCH (a:Author) RETURN a.author_id LIMIT 1").result_set
    if not res:
        print("[LỖI] Không tìm thấy Author nào trong đồ thị!")
        return
        
    test_author = res[0][0]
    print(f" -> Tác giả kiểm thử chính: {test_author} (có {res[0][1]} liên kết đồng tác giả)")
    print(f" -> Các tác giả kiểm thử phụ: {[row[0] for row in res[1:]]}")

    results = {
        "graph_name": repo.graph_name,
        "graph_stats": stats,
        "test_author": test_author,
        "benchmarks": {}
    }

    # Benchmark 1: get_author_profile
    print("\n3. Benchmark: get_author_profile...")
    times = []
    profile = None
    for _ in range(5):
        t0 = time.perf_counter()
        profile = repo.get_author_profile(test_author)
        times.append((time.perf_counter() - t0) * 1000)
    avg_profile = sum(times) / len(times)
    min_profile = min(times)
    print(f" -> Kết quả: {profile}")
    print(f" -> Độ trễ trung bình: {avg_profile:.2f} ms (nhanh nhất: {min_profile:.2f} ms)")
    results["benchmarks"]["get_author_profile_ms"] = {
        "avg": round(avg_profile, 2),
        "min": round(min_profile, 2),
        "result": profile
    }

    # Benchmark 2: get_author_works
    print("\n4. Benchmark: get_author_works (limit=50)...")
    times = []
    works = []
    for _ in range(5):
        t0 = time.perf_counter()
        works = repo.get_author_works(test_author, limit=50)
        times.append((time.perf_counter() - t0) * 1000)
    avg_works = sum(times) / len(times)
    min_works = min(times)
    print(f" -> Tìm thấy {len(works)} công trình")
    print(f" -> Độ trễ trung bình: {avg_works:.2f} ms (nhanh nhất: {min_works:.2f} ms)")
    results["benchmarks"]["get_author_works_ms"] = {
        "avg": round(avg_works, 2),
        "min": round(min_works, 2),
        "count": len(works)
    }

    # Benchmark 3: get_coauthors
    print("\n5. Benchmark: get_coauthors (limit=50)...")
    times = []
    coauthors = []
    for _ in range(5):
        t0 = time.perf_counter()
        coauthors = repo.get_coauthors(test_author, limit=50)
        times.append((time.perf_counter() - t0) * 1000)
    avg_coauthors = sum(times) / len(times)
    min_coauthors = min(times)
    print(f" -> Tìm thấy {len(coauthors)} đồng tác giả")
    print(f" -> Độ trễ trung bình: {avg_coauthors:.2f} ms (nhanh nhất: {min_coauthors:.2f} ms)")
    results["benchmarks"]["get_coauthors_ms"] = {
        "avg": round(avg_coauthors, 2),
        "min": round(min_coauthors, 2),
        "count": len(coauthors)
    }

    # Benchmark 4: get_candidate_pairs
    print("\n6. Benchmark: get_candidate_pairs (Link Prediction, limit=500)...")
    times = []
    pairs = []
    for _ in range(5):
        t0 = time.perf_counter()
        pairs = repo.get_candidate_pairs(limit=500)
        times.append((time.perf_counter() - t0) * 1000)
    avg_pairs = sum(times) / len(times)
    min_pairs = min(times)
    print(f" -> Lấy được {len(pairs)} cặp candidate")
    print(f" -> Độ trễ trung bình: {avg_pairs:.2f} ms (nhanh nhất: {min_pairs:.2f} ms)")
    results["benchmarks"]["get_candidate_pairs_ms"] = {
        "avg": round(avg_pairs, 2),
        "min": round(min_pairs, 2),
        "count": len(pairs)
    }

    # Lưu kết quả benchmark ra JSON
    with open("benchmark_report.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)
    print("\n==================================================")
    print(" ĐÃ LƯU BÁO CÁO BENCHMARK: benchmark_report.json  ")
    print("==================================================")

if __name__ == "__main__":
    run_benchmark()
