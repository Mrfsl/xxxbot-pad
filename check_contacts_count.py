import sqlite3
import os

# 数据库文件路径
db_path = "database/contacts.db"

# 检查数据库文件是否存在
if not os.path.exists(db_path):
    print(f"数据库文件不存在: {db_path}")
    exit(1)

# 连接数据库
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 查询联系人总数
    cursor.execute("SELECT COUNT(*) FROM contacts")
    count = cursor.fetchone()[0]
    print(f"数据库中共有 {count} 个联系人")
    
    # 查询联系人类型分布
    cursor.execute("SELECT type, COUNT(*) FROM contacts GROUP BY type")
    type_counts = cursor.fetchall()
    print("\n联系人类型分布:")
    for type_name, type_count in type_counts:
        print(f"- {type_name}: {type_count} 个")
    
    # 查询最近更新的10个联系人
    cursor.execute("SELECT wxid, nickname, type, last_updated FROM contacts ORDER BY last_updated DESC LIMIT 10")
    recent_contacts = cursor.fetchall()
    print("\n最近更新的10个联系人:")
    for wxid, nickname, type_name, last_updated in recent_contacts:
        print(f"- {nickname or wxid} ({type_name})")
    
    conn.close()
except Exception as e:
    print(f"查询数据库时出错: {e}")
