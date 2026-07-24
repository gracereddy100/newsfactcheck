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
Read this news article and give:

1. Credibility Score (0-100)
2. Verdict
3. Short Explanation

Article:
{news_article[:1000]}
"""
            }
        ]
    )

    result = response.choices[0].message.content

    return {
        "score": 0,
        "verdict": "Analysis Complete",
        "verified": 0,
        "unsupported": 0,
        "claims": [],
        "report": result
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

    return render_template(
        "index.html",
        report=report
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0",port=8000,debug=True
    ) 