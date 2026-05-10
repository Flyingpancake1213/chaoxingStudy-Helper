import argparse
import json
import sys
import time
import os

import dashscope
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.service import Service as ChromeService
import requests

sys.stdout.reconfigure(encoding='gbk', line_buffering=True, errors='ignore')
print("浏览器启动中...")

homework = 'n'
arg = sys.argv
if len(arg) < 2:
    username = input('请输入超星账号:')
    password = input('请输入超星密码:')
    url = input('请输入进入考试/作业页面后的网址:')
    model = input("答案获取方式：1.本地ollama 2.通义千问（自行配置API）: ")

    modelAi = ""
    if model == "1":
        modelAi = "ollama"
    elif model == "2":
        tongyiApi = input("请输入通义千问api token：")
        modelAi = "tongyi"
    else:
        print("输入有误")
        sys.exit(0)
else:
    parser = argparse.ArgumentParser()
    parser.add_argument('--username')
    parser.add_argument('--password')
    parser.add_argument('--url')
    parser.add_argument('--api')
    parser.add_argument('--homework')
    args = parser.parse_args()

    username = args.username
    password = args.password
    url = args.url
    modelAi = "tongyi"
    tongyiApi = args.api
    homework = args.homework

options = webdriver.ChromeOptions()
options.binary_location = r"chromedriver\chrome.exe"
options.add_argument('--no-sandbox')
options.add_experimental_option('detach', True)
# 屏蔽一些浏览器的自动化提示特征，稍微降低被检测风险
options.add_argument("--disable-blink-features=AutomationControlled")

try:
    browser = webdriver.Chrome(service=ChromeService(executable_path=r"chromedriver\chromedriver.exe"), options=options)
except Exception as e:
    print(f"浏览器启动失败，请检查 chromedriver 是否配置正确: {e}")
    sys.exit(0)

browser.maximize_window()
browser.get(url)

try:
    phone_input = browser.find_element(By.ID, 'phone')
    phone_input.send_keys(username)
    password_input = browser.find_element(By.ID, 'pwd')
    password_input.send_keys(password)
    login_button = browser.find_element(By.ID, 'loginBtn')
    login_button.click()
except Exception as e:
    print("未检测到登录框，可能是已经登录或页面结构已变。")

time.sleep(3)

if not os.path.exists('result'):
    os.makedirs('result')

def ollama(text):
    url = "http://10.4.240.253:11434/api/generate"
    data = {
        "model": "qwen2:latest",
        "prompt": f"这是题目：{text} 直接返回给我答案的对应选项 不要描述其他的",
        "stream": False
    }
    try:
        response = requests.post(url, json=data)
        res = response.text
        data = json.loads(res)
        return data.get("response")
    except Exception as e:
        print(f"Ollama 请求失败: {e}")
        return ""

def tongyi(text):
    dashscope.api_key = tongyiApi
    text = f"这是题目：{text} 直接返回给我答案的对应字母 不要描述其他的"
    messages = [{'role': 'user', 'content': text}]
    try:
        response = dashscope.Generation.call(dashscope.Generation.Models.qwen_max, messages=messages, result_format='message')
        return response['output']['choices'][0]['message']['content']
    except Exception as e:
        print(f"通义千问请求失败: {e}")
        return ""

def ty_tiankong(text, num):
    dashscope.api_key = tongyiApi
    text = f"这是一道填空题,{text},请你进行回答,问题里的____或括号就是需要回答的地方,一共有{num}个空,请你直接告诉我答案 不要描述其他的 每个答案用换行分隔 返回答案的数量要跟我发的一模一样"
    messages = [{'role': 'user', 'content': text}]
    try:
        response = dashscope.Generation.call(dashscope.Generation.Models.qwen_max, messages=messages, result_format='message')
        return response['output']['choices'][0]['message']['content']
    except Exception as e:
        print(f"通义千问(填空)请求失败: {e}")
        return ""

def ty_tiankong_img(text, num, img):
    i = 0
    while i <= 3:
        text1 = f"这是一道填空题,{text},相关图片信息我已提交,请你进行回答里面的问题,一共有{num}个空,请你直接告诉我答案 不要描述其他的 任何一个空的答案都全部用换行分隔 返回答案的数量要跟我发的一模一样,不要描述其他的"
        print(f"AI视觉模型处理中 (尝试 {i+1}/4) ...")
        messages = [
            {
                "role": "user",
                "content": [
                    {"image": img},
                    {"text": text1}
                ]
            }
        ]
        try:
            response = dashscope.MultiModalConversation.call(
                api_key=tongyiApi,
                model='qwen-vl-max-latest',
                messages=messages
            )
            if response["status_code"] == 200:
                return response['output']['choices'][0]['message']['content'][0]['text']
            else:
                print(f"API 返回异常状态码: {response['status_code']}")
        except Exception as e:
            print(f"视觉大模型请求失败: {e}")
        
        i += 1
        time.sleep(1) # 失败后稍微等待再重试
        
    print("多模态请求失败次数过多，跳过")
    return "error"

def process_and_upload_image(img_element):
    """提取图片、下载并上传至图床获取直链，包含完善的文件清理机制"""
    img_url_myxuebi = ""
    img_name = ""
    try:
        img_url = img_element.get_attribute("src")
        if not img_url:
            return ""
            
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(img_url, stream=True, headers=headers, timeout=10)
        
        if response.status_code == 200:
            img_name = img_url.split("/")[-1].split("?")[0] # 清理可能的 URL 参数
            if not img_name.endswith(('.png', '.jpg', '.jpeg', '.gif')):
                img_name += '.png' # 提供默认后缀
            
            # 下载图片到本地
            with open(img_name, "wb") as file:
                for chunk in response.iter_content(1024):
                    file.write(chunk)
            
            # 上传到图床
            url_upload = "https://image.myxuebi.top/api/v1/upload"
            with open(img_name, "rb") as file_to_upload:
                files = {"file": file_to_upload}
                res_upload = requests.post(url_upload, files=files, timeout=15)
            
            if res_upload.status_code == 200:
                res_json = json.loads(res_upload.text)
                if res_json.get("data") and res_json["data"].get("links"):
                    img_url_myxuebi = res_json["data"]["links"]["url"]
                    print("图片已成功生成直链：" + img_url_myxuebi)
    except Exception as e:
        print(f"图片处理失败: {e}")
    finally:
        # 无论成功失败，确保本地临时文件被删除
        if img_name and os.path.exists(img_name):
            try:
                os.remove(img_name)
            except:
                pass
                
    return img_url_myxuebi

def extract_question_and_options():
    try:
        num_ele = browser.find_element(By.XPATH, "//h3[@class='mark_name colorDeep']")
    except NoSuchElementException:
        print("未找到题目元素，可能加载过慢或已答完。")
        return

    if "单选" in num_ele.text:
        options = browser.find_elements(By.XPATH, "//div[@class='clearfix answerBg singleoption']")
        choose =
