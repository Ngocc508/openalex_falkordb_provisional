import sys
import json, hashlib, os, csv
from collections import defaultdict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

def sha256_file(path, chunk=1024*1024):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()

print("=== 1. VERIFY SHA-256 ===")
# ĐÃ SỬA ĐƯỜNG DẪN VÀO THƯ MỤC MANIFESTS
manifest = json.load(open("manifests/release_manifest.json", encoding="utf-8"))
for rel, meta in manifest["included_artifacts"].items():
    p = rel
    if not os.path.exists(p):
        print(f"[MISSING] {rel}")
        continue
    if "sha256" in meta:
        got = sha256_file(p)
        ok = got == meta["sha256"]
        print(f"[{'OK' if ok else 'FAIL'}] {rel}")
        assert ok, f"Hash mismatch: {rel}"

print("\n=== 2. COUNT FILTERED JSONL ===")
filtered_path = "data/cohort_works_2018_2025_provisional_filtered.jsonl"
works = 0
authorships = 0
auth_by_work = {}
with open(filtered_path, encoding="utf-8") as f:
    for line in f:
        if not line.strip():
            continue
        rec = json.loads(line)
        works += 1
        
        # Lấy ID và cắt bỏ phần https://openalex.org/ nếu có
        wid_raw = rec.get("id") or rec.get("work_id")
        wid = wid_raw.split("/")[-1] if wid_raw else "UNKNOWN"
        
        n = len(rec.get("authorships", []))
        authorships += n
        auth_by_work[wid] = n
print(f"works={works} authorships={authorships}")
assert works == 55119, f"works mismatch: {works}"
assert authorships == 1118807, f"authorships mismatch: {authorships}"

print("\n=== 3. EXCLUDED AUDIT ===")
excluded = set()
excluded_works = set()
with open("provenance/excluded_occurrence_audit_v1.csv", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        wid = r["work_id"]
        si = int(r["source_authorship_index_0based"])
        excluded.add((wid, si))
        excluded_works.add(wid)
        assert r["action"] == "EXCLUDED_FROM_PROVISIONAL_GRAPH_INPUT"
print(f"excluded={len(excluded)} distinct_works={len(excluded_works)}")
assert len(excluded) == 88
assert len(excluded_works) == 76

print("\n=== 4. RETAINED MAP ===")
map_rows = 0
by_work = defaultdict(list)
with open("provenance/retained_authorship_source_index_map_v1.csv", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        wid = r["work_id"]
        fi = int(r["filtered_authorship_index_0based"])
        si = int(r["source_authorship_index_0based"])
        by_work[wid].append((fi, si))
        map_rows += 1
print(f"map_rows={map_rows}")
assert map_rows == 1118807

print("\n=== 5. MAP CONSISTENCY ===")
for wid, pairs in by_work.items():
    pairs_sorted = sorted(pairs)
    fis = [fi for fi, _ in pairs_sorted]
    sis = [si for _, si in pairs_sorted]
    assert fis == list(range(len(fis))), f"filtered index not contiguous: {wid}"
    assert sis == sorted(sis), f"source index not increasing: {wid}"
    assert len(sis) == len(set(sis)), f"duplicate source index: {wid}"
    excl_sis = {si for w, si in excluded if w == wid}
    assert set(sis).isdisjoint(excl_sis), f"retained+excluded overlap: {wid}"
    assert len(sis) == auth_by_work[wid], f"count mismatch: {wid}"

print("\nALL CHECKS PASSED ✔")