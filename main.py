import streamlit as st
from bs4 import BeautifulSoup
import requests
import pandas as pd
import re
from dotenv import load_dotenv
import os
import openai
from scholarly import scholarly, ProxyGenerator

# .envファイルから環境変数を読み込む
load_dotenv()

# 環境変数からAPIキーを取得
DEVELOPER_KEY = os.getenv('DEVELOPER_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
SCRAPERAPI_KEY = os.getenv('SCRAPERAPI_KEY')

# OpenAI APIキーを設定
openai.api_key = OPENAI_API_KEY

def search_google_scholar(query, num_results=10):
    pg = ProxyGenerator()
    success = pg.ScraperAPI(SCRAPERAPI_KEY)  # ScraperAPIのキーを使用
    if not success:
        st.error("プロキシの設定に失敗しました。")
        return []
    scholarly.use_proxy(pg)
    
    search_query = scholarly.search_pubs(query)
    papers = []
    
    for i in range(num_results):
        try:
            paper = next(search_query)
            papers.append({
                "title": paper.get("bib", {}).get("title", "N/A"),
                "author": ", ".join(paper.get("bib", {}).get("author", ["N/A"])),
                "year": paper.get("bib", {}).get("pub_year", "N/A"),
                "journal": paper.get("bib", {}).get("venue", "N/A"),
                "abstract": paper.get("bib", {}).get("abstract", "N/A")
            })
        except StopIteration:
            break
    
    return papers

def generate_summary(text, model="gpt-4", max_tokens=500):
    response = openai.ChatCompletion.create(
        model=model,
        messages=[{"role": "system", "content": "以下のテキストを500文字の日本語で要約してください。"},
                  {"role": "user", "content": text}],
        max_tokens=max_tokens
    )
    return response["choices"][0]["message"]["content"].strip()

def generate_patent_proposals(papers):
    proposals = []
    for i, paper in enumerate(papers[:3]):
        title = paper["title"]
        abstract = paper["abstract"]
        summary = generate_summary(abstract) if abstract else "要約なし"
        
        # 自然言語処理を用いて特許提案を生成
        prompt = f"""
        あなたは優秀な研究者です。以下の論文に基づいて、新規性と進歩性のある特許提案を考えてください。
        論文タイトル: {title}
        要約: {summary}
        特許提案には、提案名、新規性、進歩性、競合他社、請求項を含めてください。
        """
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "特許提案を生成してください。"},
                      {"role": "user", "content": prompt}],
            max_tokens=500
        )
        proposal_text = response["choices"][0]["message"]["content"].strip()
        
        proposal = {
            "提案名": f"特許提案 {i+1}: {title}",
            "新規性": f"本発明は、{title}に関するものであり、新規性があります。",
            "進歩性": f"従来の技術と比較して、{title}は進歩性があります。",
            "競合他社": "関連する競合他社を記載してください。",
            "請求項": [
                f"1. {title}に関するシステムであって、...",
                f"2. {title}に関する方法であって、...",
                f"3. {title}に関する装置であって、..."
            ],
            "要約": summary,
            "提案内容": proposal_text
        }
        proposals.append(proposal)
    return proposals

def main():
    st.title("Google Scholar 論文検索アプリ")
    
    query = st.text_input("検索キーワードを入力してください")
    num_results = st.number_input("検索結果の数を入力してください", min_value=1, max_value=100, value=10)
    
    if st.button("検索"):
        with st.spinner("検索中..."):
            papers = search_google_scholar(query, num_results=num_results)
        
        if papers:
            st.success("検索完了")
            results = []
            for paper in papers:
                summary = generate_summary(paper["abstract"]) if paper["abstract"] else "要約なし"
                results.append({
                    "タイトル": paper["title"],
                    "著者": paper["author"],
                    "発行年": paper["year"],
                    "ジャーナル": paper["journal"],
                    "要約": summary
                })
            
            df = pd.DataFrame(results)
            st.dataframe(df)
            
            proposals = generate_patent_proposals(papers)
            for proposal in proposals:
                st.subheader(proposal["提案名"])
                st.write("新規性:", proposal["新規性"])
                st.write("進歩性:", proposal["進歩性"])
                st.write("競合他社:", proposal["競合他社"])
                st.write("請求項:")
                for claim in proposal["請求項"]:
                    st.write(claim)
                st.write("要約:", proposal["要約"])
                st.write("提案内容:", proposal["提案内容"])
        else:
            st.error("検索結果が見つかりませんでした。")

if __name__ == "__main__":
    main()