import os
import re
import warnings
import pandas as pd
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaLLM as Ollama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

# Silence warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
warnings.filterwarnings("ignore", category=DeprecationWarning)

# === 1️⃣ Load your insider trading CSV ===
csv_path = "form4_data_fixed.csv"
df = pd.read_csv(csv_path)

# Normalize column names for easy reference
df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
df["officer_name"] = df["officer_name"].astype(str)
df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")

# === 2️⃣ Create FAISS index for general questions (optional) ===
embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
db_path = "faiss_index"
if os.path.exists(db_path):
    vectorstore = FAISS.load_local(db_path, embedding_model, allow_dangerous_deserialization=True)
else:
    vectorstore = FAISS.from_texts(df.astype(str).apply(lambda x: " ".join(x), axis=1).tolist(), embedding_model)
    vectorstore.save_local(db_path)

retriever = vectorstore.as_retriever(search_kwargs={"k": 8})

# === 3️⃣ LLM setup (for reasoning fallback) ===
llm = Ollama(model="llama3")
prompt = ChatPromptTemplate.from_template(
    "You are a financial data assistant. "
    "Answer based only on the insider trading dataset.\n\n"
    "Context:\n{context}\n\n"
    "Question: {question}"
)
chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | prompt
    | llm
)

# === 4️⃣ Define exact lookup function ===
def query_exact(officer_name, year=None):
    """Return exact filtered transactions with flexible matching."""
    # Clean and normalize
    officer_name = officer_name.strip().lower()
    df["officer_name_clean"] = df["officer_name"].str.strip().str.lower()

    # Match if query is a substring anywhere in the name
    mask = df["officer_name_clean"].apply(
        lambda x: all(part in x for part in officer_name.split())
    )

    results = df[mask]
    if year:
        results = results[results["transaction_date"].dt.year == int(year)]

    if results.empty:
        # 🪄 Debug tip: print similar names to help identify mismatches
        possible = df["officer_name_clean"].dropna().unique()[:10]
        return (
            f"No transactions found for '{officer_name}' in {year if year else 'the dataset'}.\n\n"
            f"Try one of these names from your data:\n{', '.join(possible)}"
        )

    output = results[
        [
            "officer_name",
            "officer_title",
            "transaction_code",
            "transaction_type",
            "transaction_date",
            "shares",
            "price_per_share",
            "security_title",
            "sheet_name",
        ]
    ].sort_values("transaction_date")

    return (
        f"📊 Exact Results for {officer_name.title()} ({year if year else 'All Years'}):\n\n"
        + output.to_string(index=False)
    )

# === 5️⃣ Chat loop with forced routing ===
print("🤖 Chatbot ready! Type a query like '2024 Tim Cook transactions' or '2023 Luca Maestri sells'.")
print("Type 'exit' to quit.\n")

while True:
    query = input("You: ").strip()
    if query.lower() in ["exit", "quit"]:
        print("Goodbye 👋")
        break

    # Explicit structured pattern detection (forces pandas lookup)
    match = re.match(r"(\d{4})\s+([A-Za-z .']+)\s+transactions", query, re.I)
    match_alt = re.match(r"([A-Za-z .']+)\s+(\d{4})\s+transactions", query, re.I)
    match_simple = re.match(r"([A-Za-z .']+)\s+transactions", query, re.I)

    if match or match_alt or match_simple:
        if match:
            year, name = match.groups()
        elif match_alt:
            name, year = match_alt.groups()
        else:
            name = match_simple.group(1)
            year = None
        print(query_exact(name.strip(), year.strip() if year else None))
        continue

    # Otherwise use AI reasoning (semantic)
    answer = chain.invoke(query)
    print(f"Bot: {answer}\n")
