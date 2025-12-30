"""
清除数据库内容（保留表结构）
"""
import sqlite3
from pathlib import Path

db_path = Path("data/paper_push.db")

if not db_path.exists():
    print("数据库文件不存在")
    exit()

print("=" * 100)
print("清除数据库内容")
print("=" * 100)
print()

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# 获取当前数据统计
cursor.execute("SELECT COUNT(*) FROM papers")
paper_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM runs")
run_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM scores")
score_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM pushes")
push_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM dedup_keys")
dedup_count = cursor.fetchone()[0]

print("当前数据统计:")
print(f"  论文数: {paper_count}")
print(f"  运行记录数: {run_count}")
print(f"  评分记录数: {score_count}")
print(f"  推送记录数: {push_count}")
print(f"  去重键数: {dedup_count}")
print()

# 自动确认（非交互式）
print("自动确认清除所有数据...")

print("\n开始清除...")

# 清除所有表的数据（保留表结构）
tables = ['pushes', 'scores', 'dedup_keys', 'papers', 'runs']
for table in tables:
    try:
        cursor.execute(f"DELETE FROM {table}")
        print(f"  [OK] 已清除 {table} 表")
    except Exception as e:
        print(f"  [X] 清除 {table} 表失败: {e}")

# 重置自增ID
cursor.execute("DELETE FROM sqlite_sequence")
print("  [OK] 已重置自增ID")

conn.commit()
conn.close()

print("\n数据库已清空！")
print("=" * 100)

