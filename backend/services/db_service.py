from db import get_connection
import psycopg2

def save_candidate_data(name, email, score, pdf_url):
    """
    Saves the extracted candidate data into candidateDetails table.
    """
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        insert_query = """
        INSERT INTO candidate_details (name, email, score, pdf_url)
        VALUES (%s, %s, %s, %s)
        """
        
        cur.execute(insert_query, (name, email, score, pdf_url))
        conn.commit()
        cur.close()
        print("  Database -> Successfully saved candidate data.")
    except Exception as e:
        print(f"  Database -> Error saving candidate data: {e}")
    finally:
        if conn is not None:
            conn.close()
