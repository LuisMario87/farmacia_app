import psycopg2

conn = psycopg2.connect(
    host="aws-1-us-east-1.pooler.supabase.com",
    database="postgres",
    user="postgres.tssshzrqozcugvqqiavw",
    password="Demonio8719@",
    port="5432",
    
)

cursor = conn.cursor()
print("Conexión exitosa a la base de datos Supabase.")