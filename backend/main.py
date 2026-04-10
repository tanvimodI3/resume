from db import get_connection
from services.parser import extract_candidate_data

conn = get_connection()
cur = conn.cursor()

with open("queries/create_tables.sql", "r") as f:
    cur.execute(f.read())

json_tokens = {
    "name": "Anannya",
    "pdf_url": "https://example.com/resume.pdf"
}

data = extract_candidate_data(json_tokens)

print(data)


conn.commit()
cur.close()
conn.close()