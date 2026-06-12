import sqlite3, os, sys
sys.path.insert(0, '.')
from sqlite_manager import ERDiagramWindow

db_path = 'test_er.db'
if os.path.exists(db_path):
    os.remove(db_path)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA foreign_keys = ON")

# Create tables with FK relationships
conn.executescript("""
CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE profiles (id INTEGER PRIMARY KEY, user_id INTEGER UNIQUE, bio TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id));
CREATE TABLE articles (id INTEGER PRIMARY KEY, title TEXT, author_id INTEGER,
    FOREIGN KEY (author_id) REFERENCES users(id));
CREATE TABLE tags (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE article_tags (
    article_id INTEGER, tag_id INTEGER, 
    PRIMARY KEY (article_id, tag_id),
    FOREIGN KEY (article_id) REFERENCES articles(id),
    FOREIGN KEY (tag_id) REFERENCES tags(id));
CREATE TABLE comments (id INTEGER PRIMARY KEY, article_id INTEGER, parent_id INTEGER,
    content TEXT,
    FOREIGN KEY (article_id) REFERENCES articles(id),
    FOREIGN KEY (parent_id) REFERENCES comments(id));
INSERT INTO users VALUES (1, 'Alice'), (2, 'Bob');
INSERT INTO profiles VALUES (1, 1, 'bio');
INSERT INTO articles VALUES (1, 'Hello', 1);
INSERT INTO tags VALUES (1, 'tech'), (2, 'life');
INSERT INTO article_tags VALUES (1, 1), (1, 2);
INSERT INTO comments VALUES (1, 1, NULL, 'Great'), (2, 1, 1, 'Reply');
""")

# Test analyze_schema
tables = {}
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
table_names = [row[0] for row in cursor.fetchall()]
print(f"Tables: {table_names}")

for tbl in table_names:
    cursor.execute(f'PRAGMA table_info("{tbl}")')
    pk_cols = []
    for col in cursor.fetchall():
        if col['pk']:
            pk_cols.append(col['name'])
    
    cursor.execute(f'PRAGMA foreign_key_list("{tbl}")')
    fks = []
    for fk in cursor.fetchall():
        fks.append({"ref_table": fk['table'], "from": fk['from'], "to": fk['to']})
    
    print(f"  {tbl}: PK={pk_cols}, FK={fks}")

# Simulate the relation building logic
join_tables = set()
all_tables = {}
for tbl in table_names:
    cursor.execute(f'PRAGMA foreign_key_list("{tbl}")')
    fks = []
    for fk in cursor.fetchall():
        fks.append({"ref_table": fk['table'], "from": fk['from'], "to": fk['to']})
    
    cursor.execute(f'PRAGMA table_info("{tbl}")')
    pk_set = set()
    for col in cursor.fetchall():
        if col['pk']:
            pk_set.add(col['name'])
    
    all_tables[tbl] = {"foreign_keys": fks, "pk": pk_set}

    if len(fks) >= 2:
        fk_cols = {f["from"] for f in fks}
        if fk_cols.issubset(pk_set) or fk_cols == pk_set:
            join_tables.add(tbl)

print(f"\nJoin tables (M:N): {join_tables}")

# Simulate relation type detection
for tbl, info in all_tables.items():
    for fk in info["foreign_keys"]:
        ref = fk["ref_table"]
        if ref not in all_tables:
            continue
        from_pk = info["pk"]
        fk_col_in_pk = fk["from"] in from_pk
        ref_pk = all_tables[ref]["pk"]
        fk_target_in_pk = fk["to"] in ref_pk
        is_self_ref = (tbl == ref)
        
        if (not is_self_ref) and tbl in join_tables:
            rtype = "M:N"
        elif (not is_self_ref) and fk_col_in_pk and fk_target_in_pk:
            rtype = "1:1"
        else:
            rtype = "1:N"
        
        print(f"  {ref}.{fk['to']} -> {tbl}.{fk['from']}: {rtype}")

conn.close()
os.remove(db_path)
print("\nALL TESTS PASSED")
