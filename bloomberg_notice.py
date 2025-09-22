import feedparser
import html
from openai import OpenAI, InternalServerError
import json
import smtplib
from email.mime.text import MIMEText
from email.message import EmailMessage
import os
from dotenv import load_dotenv
import github
from github import Github, Auth

load_dotenv()

API_KEY = os.environ["API_KEY"]
APP_PASSWORD = os.environ["APP_PASSWORD"]
GIST_TOKEN = os.environ["GIST_TOKEN"]
GIST_ID= "859657a15de768466cd69aa7f51c9c49"

def get_rss_feeds(url, seen_ids, new_ids):
    # Parse the feed
    feed = feedparser.parse(url)

    try:
        feed.entries[0].summary
    except AttributeError as e:
        print(f"{e} reported, meaning there's no summary here.")
        return None, None, None
    except IndexError as e:
        print(f"{e} reported, meaning nothing has been fetched.")
        return None, None, None
    else:
        print(f"this feed is going to be processed.")
        feed_id = feed.entries[0].link
        new_ids.add(feed_id)
        if feed_id in seen_ids:
            print(f"it's already there. step out of this run.")
            return None, None, None
        else:
            print(f"this feed is going to next step.")
            # assign the values to variables
            feed_title = html.unescape(feed.entries[0].title)
            feed_link = feed.entries[0].link
            feed_summary = html.unescape(feed.entries[0].summary)
            return feed_title, feed_summary, feed_link

def deepseek_analyze(feed_title, feed_summary, feed_link, system_prompt_v):

    client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")
    system_prompt = system_prompt_v
    user_content = {
        "title": feed_title,
        "summary": feed_summary,
        "link": feed_link
    }
    user_prompt = json.dumps(user_content, ensure_ascii=False)
    try:
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
    except TimeoutError as e:
        print(f"error reported: {e}")
        return None
    except InternalServerError as e:
        print(f"error reported: {e}")
        return None
    else:
        result_json = response.choices[0].message.content
    try:
        result_dict = json.loads(result_json)
    except json.JSONDecodeError:
        print(f"Invalid or empty JSON data received.")
        return None
    else:
        print(f"AI analysis done. this feed is going to next step.")
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

    with open("tasks.json", "r") as f:
        tasks = json.load(f)
    for task in tasks:
        if task["system_prompt"]:
            with open(task["system_prompt"], "r", encoding="utf-8") as f:
                task["system_prompt"] = f.read()
        else:
            continue

    auth = Auth.Token(GIST_TOKEN)
    g = Github(auth=auth)
    gist = g.get_gist(GIST_ID)
    seen_ids = set(json.loads(gist.files["seen_ids.json"].content))
    new_ids=set()

    for task in tasks:

        if task["url"] and task["system_prompt"] and task["to_email"]:

            feed_title, feed_summary, feed_link = get_rss_feeds(task.get("url"), seen_ids, new_ids)
            if feed_summary:
                result = deepseek_analyze(feed_title, feed_summary, feed_link, task.get("system_prompt"))
            else:
                continue
            if result is None:
                continue
            elif result["is_relevant"]:
                send_qq_email_notification(subject=feed_title, message=feed_link, to_email=task.get("to_email"))
            else:
                continue

        elif task["url"] and task["to_email"]:

            feed_title, feed_summary, feed_link = get_rss_feeds(task.get("url"), seen_ids, new_ids)
            if feed_title:
                send_qq_email_notification(subject=feed_title, message=feed_link, to_email=task.get("to_email"))
            else:
                continue

    if new_ids != seen_ids:
        print(f"the new ids will be written into gist file.")
        gist.edit(
        files={
            "seen_ids.json": github.InputFileContent(json.dumps(list(new_ids), indent=2))
        }
        )
    else:
        print(f"the links fetched this time are same as the one fetched last time.")

if __name__ == "__main__":
    main()