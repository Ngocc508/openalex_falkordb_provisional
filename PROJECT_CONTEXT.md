# ĐỒ ÁN NoSQL: FALKORDB OPENALEX KNOWLEDGE GRAPH
> **Tài liệu tham chiếu toàn diện (Master Context Document)**  
---

## 1. THÔNG TIN CHUNG VÀ BỐI CẢNH DỰ ÁN

- **Môn học**: Cơ sở dữ liệu NoSQL (Học kỳ 1, Năm học 2026 - 2027)
- **Đề tài**: Xây dựng module Graph Database lưu trữ Mạng tri thức học thuật OpenAlex trên **FalkorDB** (Redis Graph Engine).
- **Sinh viên phụ trách**: Nguyễn Thị Ngọc (`@Ngocc508`)
- **GitHub Repository**: [https://github.com/Ngocc508/openalex_falkordb_provisional](https://github.com/Ngocc508/openalex_falkordb_provisional)
- **Phiên bản phát hành (Release Candidate)**: `provisional_excluded88_v1_20261021T111533206730Z`
- **Tên Graph trong CSDL**: `falkordb_provisional_excluded88_v1`
- **Mục tiêu hệ thống**:
  1. Phục vụ truy vấn quan hệ học thuật: Tác giả (Author), Bài báo/Công trình (Work), Sự tham gia tác giả (Authorship).
  2. Phục vụ pipeline huấn luyện mô hình Machine Learning: Dự đoán liên kết (Link Prediction), gợi ý nhà nghiên cứu/cộng tác viên tiềm năng (Collaborator Recommendation), và hỗ trợ giao diện mạng xã hội khoa học.

---

## 2. DỮ LIỆU ĐẦU VÀO VÀ NGUYÊN TẮC BẤT DI BẤT DỊCH (DATA GOVERNANCE)

### 2.1. Nguồn dữ liệu & Tính toàn vẹn
- **Gói dữ liệu**: `openalex_falkordb_provisional_excluded88_v1_20261021T111533206730Z.zip`
- **File dữ liệu chính**: `data/cohort_works_2018_2025_provisional_filtered.jsonl` (dung lượng: **1.29 GB**).
- **Quy tắc bắt buộc (Constraints)**:
  - Đây là phiên bản **PROVISIONAL RELEASE CANDIDATE**. Tuyệt đối **không** tự ý chỉnh sửa file JSONL nguồn, **không** tự ý gom cụm (merge) tác giả khi chưa có căn cứ định danh chắc chắn.
  - **Loại trừ chính xác 88 occurrences** (thuộc 76 công trình) theo đúng kế hoạch `manifests/exclusion_plan_manifest.json` và đã kiểm chứng đối soát tại `provenance/excluded_occurrence_audit_v1.csv`. Tuyệt đối không để 88 bản ghi rác này lọt vào đồ thị.
  - **Giữ lại nguyên vẹn 1,118,807 tác giả hợp lệ** có đối soát `source_index` với `provenance/retained_authorship_source_index_map_v1.csv`.
  - Toàn bộ checksum SHA-256 của file dữ liệu, manifest và provenance được kiểm định tự động bằng script `verify_package.py` (**100% Passed**).

### 2.2. Số liệu thống kê chuẩn của Đồ thị
| Đối tượng / Quan hệ | Số lượng chuẩn | Ý nghĩa |
|:---|:---:|:---|
| **Node `Work`** | **55,119** | Các công trình nghiên cứu khoa học giai đoạn 2018 - 2025 |
| **Node `Authorship`** | **1,118,807** | Bản ghi tham gia viết bài (lưu vết thứ tự tác giả `source_index`) |
| **Node `Author`** | **314,279** | Các tác giả định danh có mã ID OpenAlex |
| **Edge `HAS_AUTHORSHIP`** | **1,118,807** | Nối từ `Work` sang `Authorship` |
| **Edge `AUTHORED_BY`** | **1,037,616** | Nối từ `Authorship` sang `Author` (cho tác giả đã định danh) |
| **Unresolved Authorships** | **81,191** | Tác giả chưa định danh (không tạo node Author ảo, chỉ lưu `raw_name` tại `Authorship`) |
| **Edge `COAUTHORED_WITH`** | **2,462,025** | Mạng lưới đồng tác giả trực tiếp giữa các node `Author` |
| **Excluded Occurrences** | **88** | Đã loại bỏ hoàn toàn (0 bản ghi lọt vào DB) |

---

## 3. THIẾT KẾ SCHEMA ĐỒ THỊ (GRAPH SCHEMA DESIGN)

### 3.1. Sơ đồ thực thể quan hệ (Graph Model)

```
       (Work: 55,119)
             │
             │ [:HAS_AUTHORSHIP]
             ▼
     (Authorship: 1,118,807)
     [source_index, raw_name]
             │
             │ [:AUTHORED_BY] (1,037,616 quan hệ)
             ▼
       (Author: 314,279) ◄──────[:COAUTHORED_WITH]──────► (Author)
                         [weight, first_year, last_year] (2,462,025 cạnh)
```

### 3.2. Rationale: Vì sao sử dụng Node trung gian `:Authorship`?
Thay vì nối trực tiếp `(Work)-[:AUTHORED_BY]->(Author)`, kiến trúc sử dụng node trung gian `:Authorship` vì 3 lý do cốt lõi:
1. **Lưu vết thứ tự tác giả (`source_index`)**: Trong nghiên cứu khoa học, vị trí tác giả (First Author, Corresponding Author, Last Author) quyết định vai trò và mức độ đóng góp. Việc lưu `source_index` trên node `Authorship` giúp truy vấn chính xác vai trò mà không làm phức tạp hóa mô hình cạnh.
2. **Xử lý 81,191 "Unresolved Authors" một cách trong sạch**: Có 81,191 tác giả chỉ có chuỗi tên text (`raw_name`) mà chưa có định danh `Author ID`. Node `:Authorship` cho phép lưu trữ nguyên vẹn `raw_name` từ công trình mà **không cần sinh ra các node `Author` giả mạo (dummy nodes)**, ngăn ngừa rác dữ liệu và sai lệch thuật toán Link Prediction.
3. **Mô hình hóa chuẩn N-N giàu thuộc tính**: Cung cấp cấu trúc mở rộng trong tương lai để bổ sung tổ chức nghiên cứu (Institution/Affiliation) tại thời điểm viết bài báo đó.

### 3.3. Cạnh quan hệ đồng tác giả `:COAUTHORED_WITH`
- Cạnh được xây dựng giữa 2 node `Author` cùng tham gia ít nhất 1 bài báo.
- Thuộc tính trên cạnh:
  - `weight` (integer): Số lượng bài báo mà 2 tác giả đã công bố chung.
  - `first_year` (integer): Năm hợp tác đầu tiên.
  - `last_year` (integer): Năm hợp tác gần nhất.
- Quy ước lưu trữ để tránh trùng lặp: Cạnh lưu có hướng nhưng chuẩn hóa `a1.author_id < a2.author_id`. Khi truy vấn, hệ thống sử dụng quan hệ vô hướng `(a1)-[:COAUTHORED_WITH]-(a2)`.

---

## 4. BẢN ĐỒ TẬP TIN VÀ CÔNG DỤNG (FILE MANIFEST)

| Tên File | Loại | Công dụng chi tiết |
|:---|:---:|:---|
| **`docker-compose.yml`** | Infra | Khởi tạo cụm FalkorDB Server (port 6379, volume bền vững `falkordb_data`) và RedisInsight GUI (port 5540). |
| **`.env.example` / `.env`** | Config | Cấu hình bảo mật môi trường (`FALKORDB_HOST`, `FALKORDB_PORT`, `FALKORDB_PASSWORD`, `GRAPH_NAME`). |
| **`requirements.txt`** | Config | Danh sách thư viện Python cần thiết (`falkordb`, `redis`, `Flask`, `tqdm`). |
| **`import_graph.py`** | Pipeline | Data Loader: Nạp Works, Authorships, Authors từ file JSONL 1.29GB vào FalkorDB theo Batch UNWIND (5.000 items/batch). Hoàn thành trong 42.32s. |
| **`build_edges.py`** | Pipeline | Edge Builder: Tính toán trọng số và tạo 2.462.025 cạnh `COAUTHORED_WITH` trong 18.06s. |
| **`verify_package.py`** | Audit | Kiểm tra toàn vẹn mã băm SHA-256 các file dữ liệu gốc và manifest. |
| **`verify_graph.py`** | Audit | Script kiểm định tự động 100% tính đúng đắn của dữ liệu trong FalkorDB, xuất ra `verification_report.json`. |
| **`queries.py`** | Core | Class `OpenAlexRepository`: Tầng giao tiếp dữ liệu thực thi 5 nghiệp vụ truy vấn cốt lõi cho ứng dụng và mô hình gợi ý. |
| **`cypher_queries.cyp`** | Cypher | Bộ 11 câu lệnh Cypher (6 truy vấn cơ bản + 5 truy vấn nâng cao phân tích mạng lưới và gợi ý bạn học thuật). |
| **`export_graph.py`** | Tool | Xuất dữ liệu đồ thị ra `exports/`: Thống kê tổng quan (`.json`), Top 100 tác giả (`.csv`), Mạng lưới mẫu 5.000 cạnh (`.csv`). |
| **`backup_restore.py`** | Tool | Quản lý sao lưu snapshot RDB (`dump.rdb` ~140.71 MB) và kiểm tra phục hồi an toàn. |
| **`benchmark.py`** | Tool | Đo đạc hiệu năng và độ trễ thực tế của từng hàm truy vấn, xuất ra `benchmark_report.json`. |
| **`app.py`** | App | Ứng dụng Web Dashboard tương tác thời gian thực kết nối FalkorDB (cổng 8080), gồm 4 tab giao diện và Cypher console. |
| **`README.md`** | Report | Báo cáo chi tiết theo chuẩn Rubric chấm điểm của Giảng viên (Mục 5, 6, 7, 8). |
| **`PROJECT_CONTEXT.md`** | Context | **Tài liệu này** - Đọc 1 file để nắm bắt 100% toàn bộ hệ thống. |

---

## 5. HƯỚNG DẪN KHỞI CHẠY HỆ THỐNG TỪ ĐẦU (ZERO TO HERO)

### Bước 1: Khởi động CSDL FalkorDB bằng Docker Compose
```bash
# Khởi chạy FalkorDB và GUI RedisInsight ngầm
docker-compose up -d

# Kiểm tra trạng thái container (phải hiển thị Up và Healthy)
docker ps
```
- FalkorDB endpoint: `localhost:6379` (Password mặc định: `MySecretPassword123`)
- RedisInsight GUI: `http://localhost:5540`

### Bước 2: Thiết lập môi trường Python
```bash
# Kích hoạt môi trường ảo đã có sẵn trong repo (hoặc tạo mới)
.\.venv\Scripts\Activate.ps1   # (Trên Windows PowerShell)
# source .venv/bin/activate    # (Trên Linux / macOS)

# Cài đặt thư viện nếu cần
pip install -r requirements.txt
```

### Bước 3: Nạp dữ liệu vào đồ thị (Nếu cần dựng lại từ đầu)
```bash
# 1. Nạp Nodes và quan hệ phân cấp Work - Authorship - Author (mất ~42s)
python import_graph.py

# 2. Xây dựng mạng lưới đồng tác giả COAUTHORED_WITH (mất ~18s)
python build_edges.py

# 3. Chạy kiểm định tự động tính đúng đắn đồ thị
python verify_graph.py
```

### Bước 4: Khởi chạy ứng dụng Web Dashboard
```bash
python app.py
```
- Truy cập trình duyệt: **`http://localhost:8080`**
- Giao diện có sẵn:
  - **Tab 1: Tổng quan**: Biểu đồ số lượng nodes, edges, tỷ lệ hoàn tất.
  - **Tab 2: Tra cứu tác giả**: Xem danh sách bài báo theo thứ tự đóng góp (`source_index`).
  - **Tab 3: Mạng lưới & Gợi ý**: Đề xuất cộng tác viên 2-hop (Friends-of-friends) và Link Prediction.
  - **Tab 4: Cypher Console**: Gõ và thực thi trực tiếp các câu Cypher trên FalkorDB.

---

## 6. ĐỐI CHIẾU THANG ĐIỂM GIẢNG VIÊN (RUBRIC ĐỒ ÁN - 4.0 ĐIỂM)

| Tiêu chí Rubric | Điểm | Trạng thái | Minh chứng & Cơ chế đáp ứng |
|:---|:---:|:---:|:---|
| **5.1. Tạo Database & Schema** | **0.5** | ✅ ĐẠT | Khởi tạo graph `falkordb_provisional_excluded88_v1`, tạo Index trên `Work(work_id)` và `Author(author_id)` để tối ưu tìm kiếm $O(1)$. |
| **5.2. Insert Dữ liệu đầy đủ** | **0.5** | ✅ ĐẠT | Nạp đủ 55,119 Works, 1,118,807 Authorships, 314,279 Authors, 2,462,025 cạnh COAUTHORED_WITH. Không rớt bản ghi, loại trừ đúng 88 rác. |
| **5.3. Truy vấn cơ bản** | **0.5** | ✅ ĐẠT | File `cypher_queries.cyp` (Q1 - Q6): Lấy hồ sơ, lọc bài báo theo năm, đếm công trình của tác giả, tìm danh sách đồng tác giả cấp 1. |
| **5.4. Truy vấn nâng cao** | **0.5** | ✅ ĐẠT | File `cypher_queries.cyp` (Q7 - Q11): Top tác giả năng suất, Top cặp hợp tác bền chặt nhất, Gợi ý cộng tác viên 2-hop, Đường đi ngắn nhất (Shortest Path). |
| **6. Import/Export, Backup/Restore**| **0.5** | ✅ ĐẠT | - Import: `import_graph.py`<br>- Export: `export_graph.py` (xuất CSV/JSON)<br>- Backup/Restore: `backup_restore.py` quản lý file snapshot RDB. |
| **7.1 & 7.2. Truy vấn trên GUI Tool** | **1.0** | ✅ ĐẠT | Tích hợp RedisInsight tại cổng `5540`, trực quan hóa đồ thị 2D/3D sinh động, hướng dẫn truy vấn chi tiết tại Mục 7 của `README.md`. |
| **8. Ứng dụng kết nối CSDL** | **0.5** | ✅ ĐẠT | Ứng dụng `app.py` hoàn chỉnh giao diện Glassmorphism hiện đại, kết nối thời gian thực FalkorDB qua `OpenAlexRepository`. |

---

## 7. KẾT QUẢ ĐO ĐẠC HIỆU NĂNG TRUY VẤN (BENCHMARK REPORT)

Được đo lường thực tế trên CSDL nạp đầy đủ qua script `benchmark.py`:

| Nghiệp vụ trong `queries.py` | Độ trễ trung bình | Độ trễ tối thiểu | Độ trễ tối đa | Đánh giá hiệu năng |
|:---|:---:|:---:|:---:|:---|
| `get_author_profile` | **6.22 ms** | 2.18 ms | 18.32 ms | Siêu tốc nhờ Index `Author(author_id)` |
| `get_author_works` | **2.20 ms** | 1.81 ms | 3.01 ms | Tra cứu 2 chặng `Work` $\rightarrow$ `Authorship` cực nhanh |
| `get_coauthors` | **3.16 ms** | 2.26 ms | 4.88 ms | Khai thác trực tiếp mạng `COAUTHORED_WITH` |
| `get_recommended_collaborators` | **8.45 ms** | 5.12 ms | 14.20 ms | Thuật toán 2-hop Link Prediction thời gian thực |
| `get_candidate_pairs` | **11.26 ms** | 10.02 ms | 13.90 ms | Lấy 500 cặp cạnh phục vụ train ML chỉ trong ~11ms |

---

## 8. LƯU Ý KỸ THUẬT QUAN TRỌNG (ENGINEERING GOTCHAS & BEST PRACTICES)

1. **Khác biệt cú pháp Cypher giữa FalkorDB và Neo4j**:
   - FalkorDB **không** hỗ trợ cú pháp subquery dạng biểu thức `count { (a)-[:REL]->(b) }` của Neo4j 5.
   - *Cách giải quyết*: Sử dụng mệnh đề chuẩn `OPTIONAL MATCH` kết hợp `count(DISTINCT w)`.
2. **Quy ước cạnh vô hướng / có hướng trong FalkorDB**:
   - FalkorDB lưu trữ cạnh có hướng. Để tránh trùng lặp 2 cạnh `(A)->(B)` và `(B)->(A)`, khi build cạnh ta chuẩn hóa `a1.author_id < a2.author_id`.
   - Khi truy vấn, luôn viết cú pháp không mũi tên `(a1)-[:COAUTHORED_WITH]-(a2)` để tìm toàn bộ đồng tác giả bất kể chiều lưu trữ.
3. **Phòng ngừa bùng nổ đường đi (Path Explosion)**:
   - Một số tác giả lớn (Supernodes) có tới >2.000 đồng tác giả. Khi chạy thuật toán gợi ý cộng tác viên 2-hop (Friends-of-friends), cần giới hạn số lượng láng giềng trung gian (`WITH friend LIMIT 30`) để ngăn chặn việc quét hàng triệu đường đi gây nghẽn bộ nhớ.
4. **Encoding tiếng Việt trên Windows PowerShell**:
   - Mặc định console Windows dùng mã `cp1252`. Tất cả các script Python độc lập đều được cấu hình:
     ```python
     if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
     ```
5. **Chính sách Git & Kích thước file**:
   - File JSONL gốc (`data/` 1.29 GB) và file sao lưu CSDL (`backups/*.rdb` >140 MB) vượt quá giới hạn 100 MB của GitHub nên đã được đưa vào `.gitignore`.
   - File môi trường `.env` chứa mật khẩu nội bộ cũng được đưa vào `.gitignore`, chỉ lưu file mẫu `.env.example`.

---

## 9. THÔNG TIN PHỤC VỤ TRUY VẤN NHANH (CHEATSHEET)

### Các ID tác giả tiêu biểu để demo kiểm thử:
- `A5013041243`: Tác giả siêu năng suất (529 bài báo, 2.073 đồng tác giả). Dùng để test tải nặng và thuật toán gợi ý.
- `A5000004245`: Tác giả tiêu biểu (14 bài báo, 15 đồng tác giả). Dùng để demo hiển thị đồ thị mạng lưới đẹp mắt trên GUI.

### Các cổng dịch vụ mặc định:
- FalkorDB Server: `localhost:6379`
- RedisInsight GUI: `http://localhost:5540`
- Web Dashboard App: `http://localhost:8080`

---
*Tài liệu này được tạo tự động và đồng bộ trực tiếp với commit mới nhất trên nhánh `main` của repository.*
