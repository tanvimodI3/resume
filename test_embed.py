import os
from dotenv import load_dotenv
load_dotenv()
from langchain_google_genai import GoogleGenerativeAIEmbeddings

try:
    embeddings = GoogleGenerativeAIEmbeddings(model="text-embedding-004")
    res = embeddings.embed_query("test")
    print("Success text-embedding-004, length:", len(res))
except Exception as e:
    print("Error text-embedding-004:", e)

try:
    embeddings2 = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
    res2 = embeddings2.embed_query("test")
    print("Success models/text-embedding-004, length:", len(res2))
except Exception as e:
    print("Error models/text-embedding-004:", e)
