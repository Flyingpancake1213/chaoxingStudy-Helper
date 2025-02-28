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

sys.stdout.reconfigure(encoding='gbk', line_buffering=True,errors='ignore')
# current_directory = os.path.dirname(os.path.abspath(__file__))

# opt = Options()
# # opt.binary_location = rf'{current_directory}\Chrome\chrome.exe'
# opt.binary_location=r"..\chromedriver\chrome.exe"
# opt.add_argument('--no-sandbox')
# opt.add_experimental_option('detach', True)
# ser = Service()
# # ser.executable_path = rf'{current_directory}\Chrome\chromedriver.exe'
# ser.executable_path = rf'..\chromedriver\chromedriver.exe'

arg = sys.argv
if len(arg) < 2:
    username = input('请输入超星账号:')
    password = input('请输入超星密码:')
    url = input('请输入进入考试页面后的网址:')
    model = input("答案获取方式：1.本地ollama 2.通义千问（自行配置API）")

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

    args = parser.parse_args()

    username = args.username
    password = args.password
    url = args.url
    modelAi = "tongyi"
    tongyiApi = args.api


options = webdriver.ChromeOptions()
options.binary_location=r"chromedriver\chrome.exe"
options.add_argument('--no-sandbox')
options.add_experimental_option('detach', True)
browser = webdriver.Chrome(service=ChromeService(executable_path="chromedriver\chromedriver.exe"),options=options)
browser.maximize_window()

browser.get(url)

phone_input = browser.find_element(By.ID, 'phone')
phone_input.send_keys(username)

password_input = browser.find_element(By.ID, 'pwd')
password_input.send_keys(password)

login_button = browser.find_element(By.ID, 'loginBtn')
login_button.click()

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
    response = requests.post(url, json=data)
    res = response.text
    data = json.loads(res)
    ans = data.get("response")
    return ans

def tongyi(text):
    dashscope.api_key = tongyiApi
    text = f"这是题目：{text} 直接返回给我答案的对应字母 不要描述其他的"
    messages = [{'role': 'user', 'content': text}]
    response = dashscope.Generation.call(dashscope.Generation.Models.qwen_max, messages=messages,
                                         result_format='message')
    content = response['output']['choices'][0]['message']['content']

    return content

def ty_tiankong(text,num):
    dashscope.api_key = tongyiApi
    text = f"这是一道填空题,{text},请你进行回答,问题里的$填空内容就是需要回答的地方,一共有{num}个空,请你直接告诉我答案 不要描述其他的 每个答案用换行分隔 返回答案的数量要跟我发的一模一样"
    messages = [{'role': 'user', 'content': text}]
    response = dashscope.Generation.call(dashscope.Generation.Models.qwen_max, messages=messages,
                                         result_format='message')
    content = response['output']['choices'][0]['message']['content']

    return content

def ty_tiankong_img(text,num,img):
    i = 0

    while True:
        text1 = f"这是一道填空题,{text},相关图片信息我已提交,请你进行回答里面的问题,一共有{num}个空,请你直接告诉我答案 不要描述其他的 任何一个空的答案都全部用换行分隔 返回答案的数量要跟我发的一模一样,不要描述其他的"
        print("AI图片处理中，请稍后...")
        messages = [
            {
                "role": "user",
                "content": [
                    {"image": img},
                    {"text": text1}
                ]
            }
        ]
        response = dashscope.MultiModalConversation.call(
            api_key=tongyiApi,
            model='qwen-vl-max-latest',
            messages=messages
        )

        if i > 3:
            print("请求失败次数过多，跳过")
            return "error"

        if response["status_code"] == 200:
            break
        else:
            print("请求失败，正在重试...")
            i += 1
    content = response['output']['choices'][0]['message']['content'][0]['text']
    return content

def extract_question_and_options():
        # que_ele = browser.find_element(By.XPATH,"//div[@style='overflow:hidden;']")
        num_ele = browser.find_element(By.XPATH,"//h3[@class='mark_name colorDeep']")

        if "单选" in num_ele.text:
            # type_ele = browser.find_element(By.XPATH,"//span[@class='colorShallow']")
            # type_text = type_ele.text.split("(")[1].split(",")[0]

            options = browser.find_elements(By.XPATH, "//div[@class='clearfix answerBg singleoption']")
            choose = ""
            for option in options:
                option_letter = option.find_element(By.XPATH, ".//span").text
                option_content = option.find_element(By.XPATH, ".//div").text
                choose += f"{option_letter}: {option_content} "

            que = f"{num_ele.text} {choose}"
            print(que)

            if (modelAi == "ollama"):
                ans = ollama(que)
            else:
                ans = tongyi(que)
            print("AI参考答案：" + ans)
            if 'A' in ans:
                A = browser.find_element(By.XPATH, "//span[text()='A']")
                A.click()

            if 'B' in ans:
                B = browser.find_element(By.XPATH, "//span[text()='B']")
                B.click()

            if 'C' in ans:
                C = browser.find_element(By.XPATH, "//span[text()='C']")
                C.click()

            if 'D' in ans:
                D = browser.find_element(By.XPATH, "//span[text()='D']")
                D.click()

            if 'A' not in ans and 'B' not in ans and 'C' not in ans and 'D' not in ans:
                print("答案获取失败")
                extract_question_and_options()

            time.sleep(1)
            status = click_next_button()
            if status == False:
                sys.exit(0)
        elif "多选" in num_ele.text:
            options = browser.find_elements(By.XPATH, "//div[@class='clearfix answerBg']")
            choose = ""
            for option in options:
                option_letter = option.find_element(By.XPATH, ".//span").text
                option_content = option.find_element(By.XPATH, ".//div").text
                choose += f"{option_letter}: {option_content} "

            que = f"{num_ele.text} {choose}"
            print(que)

            if (modelAi == "ollama"):
                ans = ollama(que)
            else:
                ans = tongyi(que)

            print("AI参考答案：" + ans)
            if 'A' in ans:
                A = browser.find_element(By.XPATH, "//span[text()='A']")
                A.click()

            if 'B' in ans:
                B = browser.find_element(By.XPATH, "//span[text()='B']")
                B.click()

            if 'C' in ans:
                C = browser.find_element(By.XPATH, "//span[text()='C']")
                C.click()

            if 'D' in ans:
                D = browser.find_element(By.XPATH, "//span[text()='D']")
                D.click()

            if 'A' not in ans and 'B' not in ans and 'C' not in ans and 'D' not in ans:
                print("答案获取失败")
                extract_question_and_options()

            time.sleep(1)
            status = click_next_button()
            if status == False:
                sys.exit(0)
        elif "判断" in num_ele.text:
            que = f"{num_ele.text}"
            print(que)

            if (modelAi == "ollama"):
                ans = ollama(que + "判断题返回对或错")
            else:
                ans = tongyi(que + "判断题返回对或错")

            print("AI参考答案：" + ans)

            if '对' in ans or 'A' in ans or 'T' in ans:
                A = browser.find_element(By.XPATH, "//span[text()='A']")
                A.click()

            if '错' in ans or 'B' in ans or 'F' in ans:
                B = browser.find_element(By.XPATH, "//span[text()='B']")
                B.click()

            if '对' not in ans and '错' not in ans and 'A' not in ans and 'B' not in ans and 'F' not in ans and 'T' not in ans:
                print("答案获取失败")
                extract_question_and_options()

            time.sleep(1)
            status = click_next_button()
            if status == False:
                sys.exit(0)
        elif "填空" in num_ele.text:
            kong = browser.find_elements(By.XPATH,"//div[@class='stem_answer']/div[@class='Answer']")
            kong_num = len(kong)
            que = f"{num_ele.text}"

            image = False
            print(que)

            try:
                img = num_ele.find_element(By.XPATH, ".//img")
                print("获取到题目图片，正在处理...")
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
                img_url = img.get_attribute("src")
                # print(f"图片的 URL 是: {img_src}")
                if img_url:  # 确保 URL 不为空
                    # 下载图片
                    response = requests.get(img_url, stream=True, headers=headers)
                    if response.status_code == 200:
                        img_name = img_url.split("/")[-1]
                        img_path = os.path.join(".", img_name)
                        with open(img_path, "wb") as file:
                            for chunk in response.iter_content(1024):
                                file.write(chunk)
                        print(f"图片已获取成功，正在转直链...")
                        # image = True
                    else:
                        print(f"无法加载图片: {img_url}")
                else:
                    print("未找到图片 URL")
                url = "https://image.myxuebi.top/api/v1/upload"
                file = open(img_name, "rb")
                files = {
                    "file": file  # 以二进制模式打开文件
                }

                response = requests.post(url, files=files)
                if response.status_code == 200:
                    res = json.loads(response.text)
                    url_img = res["data"]["links"]["url"]
                    # print(url)
                    # print("图片加载成功！")
                    image = True
                else:
                    print("提交失败，网络错误！")
            except NoSuchElementException:
                pass
            # img_url = img.get_attribute("src")

            if (modelAi == "ollama"):
                print("暂不支持ollama填空")
                status = click_next_button()
                if status == False:
                    sys.exit(0)
            else:
                if image == True:
                    print("图片已成功生成直链：" + url_img)
                    file.close()
                    os.remove(img_name)
                    ans = ty_tiankong_img(que, kong_num, url_img)
                    if ans == "error":
                        status = click_next_button()
                        if status == False:
                            sys.exit(0)
                else:
                    ans = ty_tiankong(que, kong_num)
            ans_list = ans.split("\n")
            ans_list = list(filter(None,ans_list))
            print("AI参考答案：" + str(ans_list))

            if len(ans_list) == kong_num:
                j = 0
                for i in kong:
                    input_bar = i.find_element(By.XPATH, ".//iframe")
                    # WebDriverWait(browser, 10).until(EC.frame_to_be_available_and_switch_to_it(input_bar))
                    # input_element = WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.TAG_NAME, "input")))
                    input_bar.click()
                    input_bar.send_keys(ans_list[j])
                    input_bar.click()
                    j = j + 1
                    # browser.switch_to.default_content()
            else:
                print("错误：AI答案与实际空不符，跳过此题")
                status = click_next_button()
                if status == False:
                    sys.exit(0)

            # sys.exit(0)

            time.sleep(2)
            status = click_next_button()
            if status == False:
                sys.exit(0)

        else:
            print("暂不支持填空")
            status = click_next_button()
            if status == False:
                sys.exit(0)

def click_next_button():
    try:
        next_button = browser.find_element(By.XPATH, '//a[text()="下一题"]')
        next_button.click()
    except NoSuchElementException:
        print("没有找到“下一题”按钮，可能是已经到达最后一题。")
        print("题目填写已结束，请自行检查是否有遗漏，本程序不支持部分解答题等题目，请手动填写")
        print("填空题可能会有错误，请手动核查！")
        print("程序已退出，driver已关闭，请答题完成后手动关闭浏览器")
        os.system('taskkill /im chromedriver.exe /F')
        return False
    except Exception as e:
        print(f"点击下一题按钮失败: {e}")
        return False
    return True

def getque():
    while True:
        time.sleep(0.5)
        extract_question_and_options()

getque()

# browser.quit()
