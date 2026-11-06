from pathlib import Path
from datetime import datetime
import sqlite3
source=Path(__file__).resolve().parent/'dental.db'
if not source.exists(): raise SystemExit('Chưa có dental.db')
target=source.parent/'backups'/('dental_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.db')
target.parent.mkdir(exist_ok=True)
with sqlite3.connect(source) as src, sqlite3.connect(target) as dst: src.backup(dst)
print('Đã sao lưu:',target)
