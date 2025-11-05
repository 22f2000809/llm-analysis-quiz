# solver.py
import re
import time
import requests
import pandas as pd
import urllib.parse
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from scraper import extract_question

# Load environment variables
load_dotenv()

# Initialize LLM
prompt = ChatPromptTemplate([
    ("system", "You are a data analysis expert. Perform reasoning or calculations and respond only with the final answer."),
    ("user", "{question}")
])

model = ChatGroq(model="llama-3.3-70b-versatile")
chain = prompt | model


def solve_quiz(email, secret, url, depth=1):
    """Recursively solve chained quizzes until no next URL is provided."""
    print(f"\n🧩 [Step {depth}] Solving quiz: {url}")

    # Step 1️⃣: Extract question text
    question_text = extract_question(url)
    if not question_text:
        print("⚠️ Could not extract question text.")
        return {"error": "Could not extract question"}

    print("\n📝 Extracted Question:")
    print(question_text)

    answer = None
    file_url = None

    # Step 2️⃣: Detect dataset link (absolute or relative)
    file_match = re.search(r"(https?://[^\s'\"]+\.(csv|json|xlsx?|pdf))", question_text)
    if not file_match:
        rel_match = re.search(r"(/[^'\"]+\.(csv|json|xlsx?|pdf))", question_text)
        if rel_match:
            rel_url = urllib.parse.urljoin(url, rel_match.group(1))
            print(f"📁 Found relative dataset link: {rel_url}")
            file_url = rel_url
    else:
        file_url = file_match.group(1)

    try:
        # Step 3️⃣: Process direct file links (CSV / JSON)
        if file_url:
            print(f"📂 Downloading dataset from {file_url}")
            if file_url.endswith(".csv"):
                df = pd.read_csv(file_url)
                cutoff_match = re.search(r"Cutoff[:=]?\s*(\d+)", question_text, re.IGNORECASE)
                if cutoff_match:
                    cutoff = int(cutoff_match.group(1))
                    df_numeric = df.select_dtypes("number")
                    answer = df_numeric[df_numeric > cutoff].sum().sum()
                    print(f"🧮 Computed sum above cutoff {cutoff}: {answer}")
                elif "value" in df.columns:
                    answer = df["value"].sum()
                    print(f"🧮 Computed sum of 'value' column: {answer}")
                else:
                    answer = df.select_dtypes("number").sum().sum()
                    print(f"🧮 Computed total numeric sum: {answer}")

            elif file_url.endswith(".json"):
                data = requests.get(file_url).json()
                nums = [v for v in data.values() if isinstance(v, (int, float))]
                answer = sum(nums)
                print(f"🧮 Computed JSON numeric sum: {answer}")

        # Step 4️⃣: Handle demo-scrape-data pages (secret/code or sum)
        elif "demo-scrape-data" in question_text:
            rel_data = re.search(r"(/demo-scrape-data[^\s'\"]+)", question_text)
            if rel_data:
                data_url = urllib.parse.urljoin(url, rel_data.group(1))
                print(f"🔎 Visiting data page: {data_url}")
                resp = requests.get(data_url)
                html = resp.text

                # Look for "secret"/"code" patterns first
                match = re.search(r"(?:secret|code)\W*[:=]?\W*([A-Za-z0-9\-_=]{4,})", html, re.IGNORECASE)
                if match:
                    answer = match.group(1)
                    print(f"🧠 Extracted secret code: {answer}")
                else:
                    # Otherwise, sum numbers on page
                    numbers = re.findall(r"[-+]?\d*\.\d+|\d+", html)
                    if numbers:
                        nums = [float(n) for n in numbers]
                        answer = sum(nums)
                        print(f"🧮 Found {len(nums)} numbers. Computed sum = {answer}")
                    else:
                        print("⚠️ No secret or numbers found. Defaulting to 0.")
                        answer = "0"

        # Step 5️⃣: Handle CSV-related questions (no direct link in text)
        elif "csv" in question_text.lower():
            print("🧾 Detected CSV-related question. Searching for CSV link in page HTML...")

            try:
                page_html = requests.get(url).text
            except Exception as e:
                print(f"⚠️ Error fetching page HTML for CSV detection: {e}")
                page_html = ""

            # Try finding CSV link (absolute or relative)
            csv_match = re.search(r"(https?://[^\s'\"]+\.csv)", page_html)
            if not csv_match:
                rel_csv = re.search(r"(/[^'\"]+\.csv)", page_html)
                if rel_csv:
                    csv_url = urllib.parse.urljoin(url, rel_csv.group(1))
                    print(f"📁 Found relative CSV link: {csv_url}")
                else:
                    print("⚠️ No CSV link found in HTML.")
                    csv_url = None
            else:
                csv_url = csv_match.group(1)
                print(f"📁 Found absolute CSV link: {csv_url}")

            # Process CSV if found
            if csv_url:
                try:
                    df = pd.read_csv(csv_url)
                    print(f"✅ Loaded CSV with shape {df.shape}")

                    cutoff_match = re.search(r"Cutoff[:=]?\s*(\d+)", question_text, re.IGNORECASE)
                    if cutoff_match:
                        cutoff = int(cutoff_match.group(1))
                        df_numeric = df.select_dtypes("number")
                        answer = df_numeric[df_numeric > cutoff].sum().sum()
                        print(f"🧮 Computed sum above cutoff {cutoff}: {answer}")
                    else:
                        answer = df.select_dtypes("number").sum().sum()
                        print(f"🧮 Computed total numeric sum: {answer}")

                except Exception as e:
                    print(f"⚠️ Failed to process CSV: {e}")
                    answer = "0"
            else:
                print("⚠️ No CSV found. Falling back to LLM.")
                llm_response = chain.invoke({"question": question_text})
                answer = llm_response.content.strip()

        # Step 6️⃣: Default LLM fallback
        else:
            llm_response = chain.invoke({"question": question_text})
            answer = llm_response.content.strip()
            print(f"🤖 LLM-derived answer: {answer}")

    except Exception as e:
        print(f"⚠️ Error processing data: {e}")
        answer = "0"

    # Step 7️⃣: Find submit URL (absolute or relative)
    submit_match = re.search(r"((https?://[^\s'\"]+)?/submit[^\s'\"]*)", question_text)
    if not submit_match:
        print("⚠️ Submit URL not found.")
        return {"error": "Submit URL not found"}

    submit_url = submit_match.group(1)
    if submit_url.startswith("/"):
        submit_url = urllib.parse.urljoin(url, submit_url)

    # Step 8️⃣: Submit answer
    payload = {
        "email": email,
        "secret": secret,
        "url": url,
        "answer": answer
    }

    print(f"\n➡️ Submitting answer: {answer} to {submit_url}")
    resp = requests.post(submit_url, json=payload)

    try:
        result = resp.json()
    except Exception:
        print("⚠️ Invalid JSON response.")
        result = {"error": "Invalid JSON response"}

    print(f"📥 Server Response: {result}")

    # Step 9️⃣: Handle next quiz recursively
    next_url = result.get("url")
    if next_url:
        print(f"➡️ Next quiz URL found: {next_url}")
        time.sleep(2)
        return solve_quiz(email, secret, next_url, depth + 1)
    else:
        print("✅ Quiz chain completed.")
        return result
