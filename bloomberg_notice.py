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

    # assign the values to variables
    feed_title = html.unescape(feed.entries[0].title)
    feed_link = feed.entries[0].link
    feed_summary = html.unescape(feed.entries[0].summary)

    return feed_title, feed_summary, feed_link

def deepseek_analyze(feed_title, feed_summary, feed_link):

    client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")
    system_prompt = """You are an assistant that reads and analyzes news articles to tell 
    if the article is about a luxury brand opening or reopening a boutique, and outputs structured JSON.
    Always respond in this JSON format:
    {
        "is_relevant": true or false,
        "reason": "the reason for making the decision above",
        "title": "title of the article",
        "brand": "brand name mentioned",
        "location": "city/country mentioned",
        "url": "url of the article"
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
    
    #result = deepseek_analyze(feed_title, feed_summary, feed_link)

    send_qq_email_notification(subject=feed_title, message=feed_link, to_email=["yechao@live.cn", "zhanghc27@126.com"])    

    return feed_title, feed_summary, feed_link#, result

if __name__ == "__main__":
    main()