# update_news.py
import re
import arxiv
import json
import os
import sys # Added import
from gtts import gTTS
from datetime import datetime
import google.generativeai as genai
import requests # Added for requests.exceptions.RequestException

NEWS_PATH = "news.jsonl"
PROCESSED_IDS_PATH = "processed_ids.txt"
QUERY = ["AI", "Foundation Model", "Diffusion Model"]

# === 設定 Gemini API 金鑰 ===
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")

# === 輔助函式：讀取與儲存已處理的 ID ===
def load_processed_ids(path=PROCESSED_IDS_PATH):
    if not os.path.exists(path):
        return set()
    with open(path, "r") as f:
        return set(line.strip() for line in f.readlines())

def save_processed_ids(ids, path=PROCESSED_IDS_PATH):
    with open(path, "w") as f:
        f.write("\n".join(ids))

# === 抓取 AI 論文摘要 ===
def fetch_ai_papers(query, max_results=50):
    processed_ids = load_processed_ids()
    client = arxiv.Client()
    search = arxiv.Search(
        query=f'"{query}"',
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )
    papers = []
    try:
        results_iterable = client.results(search)
        for result in results_iterable:
            # 跳過已處理的論文
            if result.get_short_id() in processed_ids:
                continue
            papers.append({
                "query": query,
                "id": result.get_short_id(),
                "url": result.entry_id,
                "title": result.title,
                "summary": result.summary,
                "authors": [author.name for author in result.authors],
                "published_date": result.published.strftime("%Y-%m-%d"),
            })
            # 將新處理的 ID 添加到集合中
            processed_ids.add(result.get_short_id())
            # 每個類別只抓取1篇
            break
    except arxiv.exceptions.ArxivError as e:
        print(f"Error fetching papers from arXiv for query '{query}': {e}")
        return [] # Return empty list on ArxivError
    except requests.exceptions.RequestException as e:
        print(f"Request error while fetching papers from arXiv for query '{query}': {e}")
        return [] # Return empty list on RequestException
    except Exception as e:
        print(f"An unexpected error occurred while fetching papers for query '{query}': {e}")
        return [] # Return empty list on other errors

    # 在處理完所有論文後，一次性儲存更新後的 ID 集合
    save_processed_ids(processed_ids)
    return papers

# === 使用 Gemini 分別翻譯標題和摘要為繁體中文 ===
def summarize_to_chinese(title, summary):
    # 分別翻譯標題
    try:
        title_prompt = (
            f"你是一個專業的學術翻譯系統。請將以下論文標題翻譯成中文，必須保持學術性和易讀性。\n"
            f"規則：\n"
            f"1. 直接輸出繁體中文結果，不要加入任何額外文字\n"
            f"2. 不要出現「翻譯」、「中文翻譯」等字眼\n"
            f"3. 不要使用引號或其他標點符號包裹翻譯結果\n\n"
            f"標題：{title}\n"
        )
        title_response = model.generate_content(title_prompt)
        title_zh = title_response.text.strip()
        # 移除可能的引號和多餘的標點符號
        title_zh = re.sub(r'^["「]|["」]$', '', title_zh).strip()
        print(f"標題翻譯成功: {title_zh[:30]}...")
    except Exception as e:
        print(f"標題翻譯錯誤: {e}") # Modified to print full exception
        title_zh = f"[翻譯] {title}"
    
    # 分別翻譯並摘要內容
    try:
        summary_prompt = (
            f"你是一個專業的學術翻譯系統。請將以下論文摘要翻譯成中文並濃縮為簡明扼要的版本。\n"
            f"規則：\n"
            f"1. 直接輸出繁體中文結果，不要加入任何額外文字\n"
            f"2. 不要出現「翻譯」、「中文翻譯」等字眼\n"
            f"3. 不要使用引號或其他標點符號包裹翻譯結果\n"
            f"4. 保持學術性但使其適合閱讀和收聽\n\n"
            f"摘要：{summary}\n"
        )
        summary_response = model.generate_content(summary_prompt)
        summary_zh = summary_response.text.strip()
        # 移除可能的引號和多餘的標點符號
        summary_zh = re.sub(r'^["「]|["」]$', '', summary_zh).strip()
        print(f"摘要翻譯成功: {summary_zh[:30]}...")
    except Exception as e:
        print(f"摘要翻譯錯誤: {e}") # Modified to print full exception
        summary_zh = f"[摘要] 無法正確翻譯此摘要，可能包含特殊符號或格式。原始摘要: {summary[:100]}..."
    
    # 返回結果
    return {
        "title_zh": title_zh,
        "summary_zh": summary_zh
    }

# === 將摘要轉成語音檔 ===
def save_audio(text, filename):
    try:
        tts = gTTS(text, lang='zh-tw')
        tts.save(filename)
        print(f"音檔儲存成功: {filename}")
        return True
    except Exception as e:
        print(f"儲存音檔失敗 ({filename}): {e}")
        return False

# === 主流程 ===
def main():
    # === 檢查 GEMINI_API_KEY ===
    if not os.getenv("GEMINI_API_KEY"):
        print("錯誤：GEMINI_API_KEY 未設定。請設定環境變數。")
        sys.exit(1)

    os.makedirs("audios", exist_ok=True)

    # 抓取所有 QUERY 文章
    papers = []
    try:
        for query in QUERY:
            print(f"正在抓取 {query} 相關文章...")
            # fetch_ai_papers now returns empty list on error, so no specific exception to catch here
            # unless fetch_ai_papers is modified to raise a custom exception.
            result = fetch_ai_papers(query)
            if result: # This implicitly handles the case where fetch_ai_papers returns []
                papers.extend(result)
                print(f"已抓取:{papers[-1]['title']}")
            else:
                print(f"未能抓取到 {query} 相關的文章。") # Log if a specific query failed

        print(f"總共抓取到 {len(papers)} 篇文章")

        # 無文章則無更新
        if len(papers) == 0:
            print("沒有抓到任何文章，處理中止。")
            # Potentially sys.exit(0) if no papers is not an error,
            # or sys.exit(1) if it's considered a failed run.
            # For now, just returning as original.
            return

    except Exception as e: # Catching any unexpected error during the fetch loop itself
        print(f"抓取文章時發生未預期的錯誤: {e}")
        sys.exit(1)
    
    # 處理每篇論文
    for i, paper in enumerate(papers):
        # 翻譯
        print(f"正在處理第 {i+1} 篇 {paper['title']}")
        result = summarize_to_chinese(paper['title'], paper['summary'])
        
        # 生成音訊檔
        audio_path = f"audios/{paper['id']}.mp3"
        audio_saved_successfully = save_audio(result['title_zh'] + "\n" + result['summary_zh'], audio_path)

        audio_path_for_json = None
        if audio_saved_successfully:
            audio_path_for_json = audio_path
        else:
            # Optional: could set to a specific error string like "audio_generation_failed"
            audio_path_for_json = None

        # 更新json資料
        paper_data = paper.copy()  # 複製原始資料
        paper_data.update({
            "title_zh": result['title_zh'],
            "summary_zh": result['summary_zh'],
            "audio": audio_path_for_json, # Use the new variable here
            "timestamp": datetime.now().isoformat()
        })
        
        # 直接將新文章附加到檔案末尾
        with open(NEWS_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(paper_data, ensure_ascii=False) + "\n")

    print("✅ 更新完成：news.jsonl 和 MP3 音檔已產生")

if __name__ == "__main__":
    main()
