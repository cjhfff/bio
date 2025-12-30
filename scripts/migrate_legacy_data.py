"""
迁移脚本：将 sent_list.txt 和 sent_meta.jsonl 导入SQLite
"""
import os
import json
import logging
from pathlib import Path
from app.storage import init_db, PaperRepository
from app.logging import setup_logging, get_logger

logger = get_logger(__name__)


def migrate_sent_list():
    """迁移 sent_list.txt"""
    sent_list_file = Path("sent_list.txt")
    if not sent_list_file.exists():
        logger.info("sent_list.txt 不存在，跳过")
        return 0
    
    repo = PaperRepository()
    sent_ids = repo.get_sent_ids()
    existing_count = len(sent_ids)
    
    count = 0
    with open(sent_list_file, 'r', encoding='utf-8') as f:
        for line in f:
            item_id = line.strip()
        if item_id and item_id not in sent_ids:
                # 创建虚拟Paper用于保存
                from app.models import Paper
                paper = Paper(
                    title="迁移数据",
                    abstract="",
                    date="",
                    source="migration",
                    doi="",
                    link=""
                )
                # 直接插入dedup_keys（因为paper可能不存在）
                try:
                    from app.storage.db import get_db
                    with get_db() as conn:
                        cursor = conn.cursor()
                        # 先创建虚拟paper
                        cursor.execute("""
                            INSERT OR IGNORE INTO papers (item_id, title, source)
                            VALUES (?, ?, ?)
                        """, (item_id, "迁移数据", "migration"))
                        cursor.execute("SELECT id FROM papers WHERE item_id = ?", (item_id,))
                        row = cursor.fetchone()
                        if row:
                            paper_id = row[0]
                            cursor.execute("""
                                INSERT OR IGNORE INTO dedup_keys (item_id, paper_id)
                                VALUES (?, ?)
                            """, (item_id, paper_id))
                    count += 1
                except Exception as e:
                    logger.warning(f"迁移 {item_id} 失败: {e}")
    
    logger.info(f"从 sent_list.txt 迁移了 {count} 条记录（已有 {existing_count} 条）")
    return count


def migrate_sent_meta():
    """迁移 sent_meta.jsonl"""
    sent_meta_file = Path("sent_meta.jsonl")
    if not sent_meta_file.exists():
        logger.info("sent_meta.jsonl 不存在，跳过")
        return 0
    
    repo = PaperRepository()
    count = 0
    
    with open(sent_meta_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line.strip())
                item_id = data.get('item_id')
                if not item_id:
                    continue
                
                # 创建Paper对象
                from app.models import Paper
                paper = Paper(
                    title=data.get('title', ''),
                    abstract='',
                    date=data.get('date', ''),
                    source=data.get('source', ''),
                    doi=data.get('doi', ''),
                    link=data.get('link', '')
                )
                
                # 保存论文
                paper_id = repo.save_paper(paper, item_id)
                count += 1
            except Exception as e:
                logger.warning(f"迁移JSONL行失败: {e}")
    
    logger.info(f"从 sent_meta.jsonl 迁移了 {count} 条记录")
    return count


def main():
    """主函数"""
    setup_logging()
    logger.info("开始迁移历史数据...")
    
    # 初始化数据库
    init_db()
    
    # 迁移
    count1 = migrate_sent_list()
    count2 = migrate_sent_meta()
    
    logger.info(f"迁移完成！共迁移 {count1 + count2} 条记录")
    logger.info("建议：迁移完成后可以备份并删除 sent_list.txt 和 sent_meta.jsonl")


if __name__ == "__main__":
    main()

