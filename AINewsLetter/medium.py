from datetime import datetime
import smtplib
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import openai
from urllib.parse import urlparse, unquote
import time

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders




def fetch_article_links_selenium(url):
    # 配置Selenium使用Chrome浏览器
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 无头模式，不打开浏览器窗口
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    try:
        driver.get(url)
        time.sleep(2)  # 等待页面加载
        article_links = []
        article_divs = driver.find_elements(By.CSS_SELECTOR, 'div.rs, div.rt, div.ru, div.rv, div.rw')
      
        for div in article_divs[:5]: 
            a_tag = div.find_element(By.TAG_NAME, 'a')
            full_link = a_tag.get_attribute('href')
            relative_link = full_link.split('?')[0]  # 移除查询参数
            article_links.append(relative_link)

        return article_links
    finally:
        driver.quit()
        
        
def fetch_paragraph_text(driver, class_name, index):
    element = driver.execute_script(f"return document.getElementsByClassName('{class_name}')[{index}];")
    return element.text if element is not None else ""

def fetch_paragraphs_selenium(driver, url):
    driver.get(url)
    time.sleep(2)  # 等待页面加载
    
    # 使用JavaScript获取标题
    title = driver.execute_script("return document.getElementsByClassName('pw-post-title')[0].textContent;")

    # 获取各段落的文本
    first_paragraph = fetch_paragraph_text(driver, 'pw-post-body-paragraph', 0)
    second_paragraph = fetch_paragraph_text(driver, 'pw-post-body-paragraph', 1)
    third_paragraph = fetch_paragraph_text(driver, 'pw-post-body-paragraph', 2)

    return title, first_paragraph, second_paragraph, third_paragraph



def get_medium_post(url):
    # 配置Selenium使用Chrome浏览器
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        article_links = fetch_article_links_selenium(url)

        articles_data = []
        for link in article_links:
            title, first_paragraph, second_paragraph,third_paragraph = fetch_paragraphs_selenium(driver, link)
            articles_data.append({
                'title': title,
                'first_paragraph': first_paragraph,
                'second_paragraph': second_paragraph,
                'third_paragraph': third_paragraph,
                'link': link
            })
        
        return articles_data
    finally:
        driver.quit()


def save_markdown_data(articles_data, filename):
    with open(filename, 'w') as f:
        for article in articles_data:
            f.write(f"# {article['title']}\n\n")
            f.write(f"{article['first_paragraph']}\n\n")
            f.write(f"{article['second_paragraph']}\n\n")
            f.write(f"{article['third_paragraph']}\n\n")
            f.write(f"Read more [here]({article['link']}).\n\n")


def process_data_with_openai(data, prompt_function, api_key):
    openai.api_key = api_key

    prompt = prompt_function(data)
    try:
        # 使用聊天模型的正确端点
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": prompt}]
        )
        print (response['choices'][0])
        return response['choices'][0]['message']['content']
    except Exception as e:
        return str(e)

def create_prompt(articles_data):
    prompt = "I have compiled information from a series of articles. Please provide a summary for each article based on the details provided."

    for article in articles_data:
        combined_paragraphs = (
            f"{article['first_paragraph']} "
            f"{article['second_paragraph']} "
            f"{article['third_paragraph']}"
        )
        
        prompt += (
            f"\n\nTitle: {article['title']}\n"
            f"Combined Paragraphs: {combined_paragraphs}\n"
            f"Link: {article['link']}"
        )

    prompt += "\n\nPlease summarize the key points from each of the articles above in the format of \n<b>Title<b> \nSummary \nLink:"

    return prompt



def save_text_data(data, filename):
    with open(filename, 'w') as f:
        f.write(data)


def send_google_email(subject, message, from_email, from_email_password, to_email, attachment_path):
    # 设置邮件
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject

    # 邮件正文
    msg.attach(MIMEText(message, 'plain'))

    # 附件
    filename = attachment_path.split('/')[-1]
    attachment = open(attachment_path, "rb")

    part = MIMEBase('application', 'octet-stream')
    part.set_payload(attachment.read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f"attachment; filename= {filename}")

    msg.attach(part)

    # 使用SMTP服务器发送邮件
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(from_email, from_email_password)
    text = msg.as_string()
    server.sendmail(from_email, to_email, text)
    server.quit()

current_date = datetime.now().strftime('%Y-%m-%d')

api_key = "Your OpenAI API Key"

url = 'https://medium.com/tag/artificial-intelligence'


# 拿到原始数据
posts_data = get_medium_post(url)

#调用API处理
open_ai_data = process_data_with_openai(posts_data,create_prompt,api_key)

save_text_data(open_ai_data, './ainews/medium_posts_'+current_date+'.md')

save_markdown_data(posts_data, './ainews/medium_posts_'+current_date+'markdown'+'.md')

# send_google_email("AI Newsletter", "This is the newsletter for " + current_date, 
#                   "from@gmail.com", "password", 
#                   "send@gmail.com", 
#                   './ainews/medium_posts_{}markdown.md'.format(current_date))

