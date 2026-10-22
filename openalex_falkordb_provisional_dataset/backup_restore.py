import os
import sys
import time
import json
import subprocess
from datetime import datetime
from falkordb import FalkorDB

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

CONTAINER_NAME = "falkordb_provisional"
RDB_REMOTE_PATH = "/var/lib/falkordb/data/dump.rdb"
BACKUP_DIR = "backups"

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

def get_db():
    pwd = get_password()
    try:
        db = FalkorDB(host="localhost", port=6379, password=pwd)
        db.connection.ping()
        return db
    except Exception:
        return FalkorDB(host="localhost", port=6379)

def create_backup():
    """
    Thực hiện Backup CSDL FalkorDB:
    1. Gửi lệnh SAVE để Redis/FalkorDB flush dữ liệu đồ thị từ RAM xuống dump.rdb
    2. Sao chép dump.rdb ra thư mục backups/ kèm timestamp
    3. Ghi log metadata
    """
    print("==================================================")
    print("      TIẾN HÀNH SAO LƯU (BACKUP) CSDL FALKORDB    ")
    print("==================================================")
    
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    print("1. Đang kết nối tới FalkorDB để thực hiện lệnh SAVE...")
    try:
        db = get_db()
        db.connection.execute_command("SAVE")
        print(" -> Đã flush dữ liệu RAM xuống disk (dump.rdb) thành công.")
    except Exception as e:
        print(f" -> Cảnh báo khi gọi SAVE qua connection: {e}")
        print(" -> Đang thử gửi lệnh SAVE qua docker exec redis-cli...")
        pwd = get_password()
        cmd = f'docker exec {CONTAINER_NAME} redis-cli -a "{pwd}" SAVE'
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if "OK" not in res.stdout:
            print(f" -> Lỗi khi gọi SAVE: {res.stderr}")
            return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"falkordb_backup_{timestamp}.rdb"
    backup_filepath = os.path.join(BACKUP_DIR, backup_filename)

    print(f"2. Đang sao chép file snapshot từ container {CONTAINER_NAME}...")
    cp_cmd = f"docker cp {CONTAINER_NAME}:{RDB_REMOTE_PATH} {backup_filepath}"
    res = subprocess.run(cp_cmd, shell=True, capture_output=True, text=True)
    
    if res.returncode == 0 and os.path.exists(backup_filepath):
        size_mb = os.path.getsize(backup_filepath) / (1024 * 1024)
        print(f" -> Sao lưu thành công: {backup_filepath} ({size_mb:.2f} MB)")
        
        # Ghi metadata
        manifest_path = os.path.join(BACKUP_DIR, "backup_manifest.json")
        manifest = {
            "last_backup_file": backup_filename,
            "backup_timestamp": timestamp,
            "size_mb": round(size_mb, 2),
            "status": "SUCCESS"
        }
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=4)
        print(f" -> Đã lưu manifest tại: {manifest_path}")
        return backup_filepath
    else:
        print(f" -> Thất bại khi sao chép snapshot: {res.stderr}")
        return None

def restore_backup(backup_file=None):
    """
    Thực hiện Khôi phục (Restore) CSDL FalkorDB:
    1. Kiểm tra file backup .rdb
    2. Sao chép đè vào /var/lib/falkordb/data/dump.rdb trong container
    3. Restart container để FalkorDB tự động nạp dữ liệu từ dump.rdb
    """
    print("==================================================")
    print("      TIẾN HÀNH KHÔI PHỤC (RESTORE) CSDL          ")
    print("==================================================")
    
    if backup_file is None:
        # Tự động tìm file backup mới nhất trong thư mục backups
        if not os.path.exists(BACKUP_DIR):
            print(f"[LỖI] Thư mục {BACKUP_DIR} không tồn tại!")
            return False
        files = [os.path.join(BACKUP_DIR, f) for f in os.listdir(BACKUP_DIR) if f.endswith(".rdb")]
        if not files:
            print("[LỖI] Không tìm thấy file backup (.rdb) nào trong thư mục backups!")
            return False
        backup_file = max(files, key=os.path.getctime)

    if not os.path.exists(backup_file):
        print(f"[LỖI] Không tìm thấy file: {backup_file}")
        return False

    print(f"1. Sử dụng file backup: {backup_file}")
    print(f"2. Đang nạp file backup vào container {CONTAINER_NAME}...")
    cp_cmd = f"docker cp {backup_file} {CONTAINER_NAME}:{RDB_REMOTE_PATH}"
    res = subprocess.run(cp_cmd, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[LỖI] Không thể sao chép file vào container: {res.stderr}")
        return False

    print(f"3. Đang khởi động lại container {CONTAINER_NAME} để nạp dữ liệu mới...")
    res_restart = subprocess.run(f"docker restart {CONTAINER_NAME}", shell=True, capture_output=True, text=True)
    if res_restart.returncode != 0:
        print(f"[LỖI] Không thể restart container: {res_restart.stderr}")
        return False

    print("4. Đang kiểm tra kết nối sau khi khôi phục...")
    time.sleep(3)
    try:
        db = get_db()
        graphs = db.list_graphs()
        print(f" -> Khôi phục THÀNH CÔNG! Danh sách Graphs hiện có: {graphs}")
        return True
    except Exception as e:
        print(f"[LỖI] Kết nối tới FalkorDB thất bại sau khi restore: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--restore":
        target = sys.argv[2] if len(sys.argv) > 2 else None
        restore_backup(target)
    else:
        create_backup()
