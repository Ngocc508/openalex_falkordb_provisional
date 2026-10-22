// ==============================================================================
// BỘ TRUY VẤN DỮ LIỆU ĐỒ THỊ OPENALEX TRÊN FALKORDB (CYPHER QUERY SUITE)
// Graph Name: falkordb_provisional_excluded88_v1
// Dành cho GUI Tool (RedisInsight, FalkorDB Browser) và Module Python
// ==============================================================================

// ------------------------------------------------------------------------------
// PHẦN A: CÁC TRUY VẤN CƠ BẢN (BASIC QUERIES - 0.5 ĐIỂM)
// ------------------------------------------------------------------------------

// 1. Thống kê số lượng node theo từng nhãn (Node Counts by Label)
MATCH (n) 
RETURN labels(n)[0] AS Label, count(n) AS Count;

// 2. Tra cứu thông tin chi tiết một bài báo cụ thể theo work_id
MATCH (w:Work {work_id: "W148222005"})
RETURN w.work_id AS Work_ID, w.year AS Publication_Year, w.release_id AS Release_ID;

// 3. Tra cứu hồ sơ học thuật của một tác giả cụ thể theo author_id
MATCH (a:Author {author_id: "A5045075334"})
OPTIONAL MATCH (a)<-[:RESOLVED_TO]-(as:Authorship)<-[:HAS_AUTHORSHIP]-(w:Work)
RETURN a.author_id AS Author_ID, count(DISTINCT w) AS Total_Works;

// 4. Lấy danh sách 10 bài báo xuất bản gần đây của một tác giả
MATCH (a:Author {author_id: "A5045075334"})<-[:RESOLVED_TO]-(as:Authorship)<-[:HAS_AUTHORSHIP]-(w:Work)
RETURN w.work_id AS Work_ID, w.year AS Year
ORDER BY w.year DESC
LIMIT 10;

// 5. Lấy danh sách tất cả tác giả của một bài báo (theo đúng thứ tự xuất hiện gốc source_idx)
MATCH (w:Work {work_id: "W148222005"})-[:HAS_AUTHORSHIP]->(as:Authorship)
OPTIONAL MATCH (as)-[:RESOLVED_TO]->(au:Author)
RETURN as.source_idx AS Order_Index, as.raw_name AS Author_Name, au.author_id AS Author_ID
ORDER BY as.source_idx ASC;

// 6. Đếm số lượng bài báo khoa học xuất bản trong năm 2024
MATCH (w:Work)
WHERE w.year = 2024
RETURN count(w) AS Total_Works_2024;


// ------------------------------------------------------------------------------
// PHẦN B: CÁC TRUY VẤN NÂNG CAO (ADVANCED QUERIES - 0.5 ĐIỂM)
// ------------------------------------------------------------------------------

// 1. TOP 10 TÁC GIẢ NĂNG SUẤT NHẤT (Top 10 Most Prolific Authors)
// Tìm 10 tác giả có số lượng công trình khoa học nhiều nhất, kèm năm bắt đầu và năm gần nhất
MATCH (a:Author)<-[:RESOLVED_TO]-(as:Authorship)<-[:HAS_AUTHORSHIP]-(w:Work)
RETURN a.author_id AS Author_ID, 
       count(DISTINCT w) AS Total_Works, 
       min(w.year) AS First_Year, 
       max(w.year) AS Latest_Year
ORDER BY Total_Works DESC
LIMIT 10;

// 2. TOP 10 CẶP ĐỒNG TÁC GIẢ BỀN CHẶT NHẤT (Top Collaborative Pairs)
// Tìm các cặp tác giả có số lượng bài báo hợp tác chung nhiều nhất trong toàn bộ mạng lưới
MATCH (a1:Author)-[c:COAUTHORED_WITH]->(a2:Author)
RETURN a1.author_id AS Author_1, 
       a2.author_id AS Author_2, 
       c.weight AS Coauthored_Works, 
       c.first_year AS From_Year, 
       c.last_year AS To_Year
ORDER BY c.weight DESC
LIMIT 10;

// 3. TÌM KIẾM ĐỒNG TÁC GIẢ BẬC 2 (Friends-of-Friends / Gợi ý hợp tác tiềm năng cho Link Prediction)
// Với tác giả mục tiêu (ví dụ A5013041243), tìm những tác giả đã hợp tác với đồng tác giả của họ nhưng chưa từng hợp tác trực tiếp
MATCH (a:Author {author_id: "A5013041243"})-[:COAUTHORED_WITH]-(co:Author)-[:COAUTHORED_WITH]-(potential:Author)
WHERE potential <> a AND NOT (a)-[:COAUTHORED_WITH]-(potential)
RETURN potential.author_id AS Suggested_Collaborator, 
       count(DISTINCT co) AS Mutual_Coauthors_Count
ORDER BY Mutual_Coauthors_Count DESC
LIMIT 10;

// 4. PHÂN TÍCH XU HƯỚNG XUẤT BẢN THEO NĂM (Publication Trend & Velocity)
// Thống kê số lượng bài báo và số lượt tác giả qua từng năm
MATCH (w:Work)-[:HAS_AUTHORSHIP]->(as:Authorship)
RETURN w.year AS Publication_Year, 
       count(DISTINCT w) AS Total_Works, 
       count(as) AS Total_Authorship_Occurrences,
       round(toFloat(count(as)) / count(DISTINCT w), 2) AS Avg_Authors_Per_Work
ORDER BY Publication_Year ASC;

// 5. TÌM ĐƯỜNG ĐI CỘNG TÁC NGẮN NHẤT GIỮA 2 NHÀ KHOA HỌC (Shortest Collaboration Path)
// Tìm đường kết nối học thuật ngắn nhất giữa 2 tác giả qua các quan hệ COAUTHORED_WITH
MATCH p = shortestPath((a1:Author {author_id: "A5013041243"})-[:COAUTHORED_WITH*..5]-(a2:Author {author_id: "A5089379373"}))
RETURN length(p) AS Degrees_Of_Separation, [n IN nodes(p) | n.author_id] AS Collaboration_Chain;
