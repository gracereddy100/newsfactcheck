import os
from dotenv import load_dotenv
from openai import OpenAI
import requests
import json
import re
from flask import Flask, render_template, request
load_dotenv()   

app = Flask(__name__)

openrouter_key = os.getenv("OPENROUTER_API_KEY")

client = OpenAI(
    api_key=openrouter_key,
    base_url="https://openrouter.ai/api/v1"
)

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")


def search_serper(query):

    url = "https://google.serper.dev/search"

    payload = {
        "q": query
    }

    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }

    response = requests.post(
        url,
        headers=headers,
        data=json.dumps(payload)
    )

    return response.json()


def search_newsapi(query):

    url = (
        f"https://newsapi.org/v2/everything?"
        f"q={query}"
        f"&pageSize=5"
        f"&apiKey={NEWS_API_KEY}"
    )

    response = requests.get(url)

    return response.json()


def verify_claim(claim):

    google_results = search_serper(claim)
    news_results = search_newsapi(claim)

    prompt = f"""
You are a professional fact-checker.

Claim:
{claim}

Google Search Results:
{google_results}

News Results:
{news_results}

Verify the claim.

Return exactly:

Status: Supported / Partially Supported / Unsupported
Confidence: score out of 100
Reason: short explanation
"""

    response = client.chat.completions.create(
        model="meta-llama/llama-3.1-8b-instruct",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response.choices[0].message.content


def analyze_news(news_article):

    response = client.chat.completions.create(
        model="meta-llama/llama-3.1-8b-instruct",
        messages=[
            {
                "role": "user",
                "content": f"""
Extract factual claims from the article.

Return ONLY JSON.

Example:
["claim1","claim2"]

Article:
{news_article}
"""
            }
        ]
    )

    claims_text = response.choices[0].message.content

    json_match = re.findall(r'\[.*?\]', claims_text, re.DOTALL)

    if json_match:
        cleaned_claims_text = json_match[-1]
    else:
        cleaned_claims_text = claims_text

    try:
        claims = json.loads(cleaned_claims_text)
    except:
        claims = []

    results = []

    for claim in claims:

        verification = verify_claim(claim)

        results.append({
            "claim": claim,
            "verification": verification
        })
    supported = 0
    unsupported_claims = []
    report_text = ""

    for item in results:

        report_text += f"\nClaim: {item['claim']}\n"
        report_text += item["verification"]
        report_text += "\n\n"

        print("\nCLAIM:", item["claim"])
        print(item["verification"])

        text = item["verification"].lower()

        status_match = re.search(
            r"status\s*:\s*(supported|partially supported|unsupported)",
            text
        )

        if status_match:

            status = status_match.group(1)

            print("Detected Status:", status)

            if status == "supported":
                supported += 1

            if status in ["unsupported", "partially supported"]:
                unsupported_claims.append(item["claim"])

    if len(results) == 0:
        return {
            "score": 0,
            "verdict": "No Claims Found",
            "verified": 0,
            "unsupported": 0,
            "claims": [],
            "report": "No factual claims found."
        }

    credibility_score = round(
        (supported / len(results)) * 100,
        2
    )

    if credibility_score >= 80:
        verdict = "Highly Credible"
    elif credibility_score >= 60:
        verdict = "Mostly Reliable"
    elif credibility_score >= 40:
        verdict = "Needs Verification"
    else:
        verdict = "Potentially Misleading"
    print("\nUNSUPPORTED CLAIMS:")
    print(unsupported_claims)

    return {
        "score": credibility_score,
        "verdict": verdict,
        "verified": supported,
        "unsupported": len(unsupported_claims),
        "claims": unsupported_claims,
        "report": report_text
    }



    # rest of your code below

@app.route("/", methods=["GET", "POST"])
def home():

    report = None

    if request.method == "POST":

        article = request.form["article"]

        try:
            report = analyze_news(article)

        except Exception as e:
            return f"""
            <h1>Error Found</h1>
            <pre>{str(e)}</pre>
            """
        print(report)
    return render_template(
        "index.html",
        report=report
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0",port=8000,debug=True
    ) 