import feedparser
import html
from openai import OpenAI
import json
import smtplib
from email.mime.text import MIMEText
from email.message import EmailMessage
import os
from dotenv import load_dotenv

load_dotenv()

# Example RSS feed (Fashion Network)
url = "https://feeds.bloomberg.com/markets/news.rss"

API_KEY = os.environ["API_KEY"]
APP_PASSWORD = os.environ["APP_PASSWORD"]

def get_rss_feeds(url):

    # Parse the feed
    feed = feedparser.parse(url)
    SEEN_IDS_FILE = "seen_ids.json"
    with open(SEEN_IDS_FILE, "r") as f:
        seen_ids = set(json.load(f))

    if feed.entries[0].summary:

        feed_id = feed.entries[0].id

        if feed_id in seen_ids:
            print(f"it's already there. step out of this run.")
            return None, None, None
        else:
            seen_ids.add(feed_id)
            with open(SEEN_IDS_FILE, "w") as f:
                json.dump(list(seen_ids), f, indent=2)

            # assign the values to variables
            feed_title = html.unescape(feed.entries[0].title)
            feed_link = feed.entries[0].link
            feed_summary = html.unescape(feed.entries[0].summary)

            return feed_title, feed_summary, feed_link
    else:
        return None, None, None

def deepseek_analyze(feed_title, feed_summary, feed_link):

    client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")
    system_prompt = """You are an assistant that reads and analyzes news articles to tell 
    if the article is about China, and outputs structured JSON.
    Always respond in this JSON format:
    {
        "is_relevant": true or false
    }"""
    user_content = {
        "title": feed_title,
        "summary": feed_summary,
        "link": feed_link
    }
    user_prompt = json.dumps(user_content, ensure_ascii=False)

    response = client.chat.completions.create(
        model="deepseek-reasoner",
        messages=
        [
            {"role": "system", "content": system_prompt},

            {"role": "user", "content": user_prompt},
        ],
        stream=False,
        temperature=1.3,
        max_tokens=4096
    )
    result_json = response.choices[0].message.content
    result_dict = json.loads(result_json)

    return result_dict

def send_qq_email_notification(subject, message, to_email):
    from_email = "549454190@qq.com"
    auth_code = APP_PASSWORD

    msg = EmailMessage()
    msg.set_content(message)
    msg["From"] = from_email
    msg["To"] = to_email if isinstance(to_email, str) else ", ".join(to_email)
    msg["Subject"] = subject

    try:
        # Connect via SSL
        with smtplib.SMTP_SSL("smtp.qq.com", 465) as server:
            server.login(from_email, auth_code)
            server.send_message(msg)
            print("✅ Email sent successfully!")
    except Exception as e:
        print(f"❌ Email failed: {e}")
    

def main():
    
    feed_title, feed_summary, feed_link = get_rss_feeds(url)
    if not feed_title:
        return

    result = deepseek_analyze(feed_title, feed_summary, feed_link)

    if result["is_relevant"]:
        send_qq_email_notification(subject=feed_title, message=feed_link, to_email=["yechao25@gmail.com", "zhanghc27@126.com"])
    else:
        return

if __name__ == "__main__":
    main()