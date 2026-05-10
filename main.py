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
        choose = ""
        for option in options:
            option_letter = option.find_element(By.XPATH, ".//span").text
            option_content = option.find_element(By.XPATH, ".//div").text
            choose += f"{option_letter}: {option_content} "

        que = f"{num_ele.text} {choose}"
        print(que)

        ans = ollama(que) if modelAi == "ollama" else tongyi(que)
        print("AI参考答案：" + ans)
        
        clicked = False
        for letter in ['A', 'B', 'C', 'D']:
            if letter in ans.upper():
                try:
                    browser.find_element(By.XPATH, f"//span[text()='{letter}']").click()
                    clicked = True
                    break # 单选只点一个
                except:
                    pass

        if not clicked:
            print("答案选择失败")

        time.sleep(1)
        if not click_next_button(): sys.exit(0)

    elif "多选" in num_ele.text:
        options = browser.find_elements(By.XPATH, "//div[@class='clearfix answerBg']")
        choose = ""
        for option in options:
            option_letter = option.find_element(By.XPATH, ".//span").text
            option_content = option.find_element(By.XPATH, ".//div").text
            choose += f"{option_letter}: {option_content} "

        que = f"{num_ele.text} {choose}"
        print(que)

        ans = ollama(que) if modelAi == "ollama" else tongyi(que)
        print("AI参考答案：" + ans)

        clicked = False
        for letter in ['A', 'B', 'C', 'D', 'E', 'F']: # 多选可能选项更多
            if letter in ans.upper():
                try:
                    browser.find_element(By.XPATH, f"//span[text()='{letter}']").click()
                    clicked = True
                    time.sleep(0.2)
                except:
                    pass

        if not clicked:
            print("答案选择失败")

        time.sleep(1)
        if not click_next_button(): sys.exit(0)

    elif "判断" in num_ele.text:
        que = f"{num_ele.text}"
        print(que)

        ans = ollama(que + "判断题返回对或错") if modelAi == "ollama" else tongyi(que + "判断题返回对或错")
        print("AI参考答案：" + ans)

        clicked = False
        if '对' in ans or 'A' in ans.upper() or 'T' in ans.upper():
            try: browser.find_element(By.XPATH, "//span[text()='A']").click(); clicked = True
            except: pass
        if '错' in ans or 'B' in ans.upper() or 'F' in ans.upper():
            try: browser.find_element(By.XPATH, "//span[text()='B']").click(); clicked = True
            except: pass

        if not clicked:
            print("答案获取或点击失败")

        time.sleep(1)
        if not click_next_button(): sys.exit(0)

    elif "填空" in num_ele.text:
        kong = browser.find_elements(By.XPATH, "//div[@class='stem_answer']/div[@class='Answer']")
        kong_num = len(kong)
        que = f"{num_ele.text}"
        print(que)

        img_url_myxuebi = ""
        try:
            img = num_ele.find_element(By.XPATH, ".//img")
            print("获取到题目图片，正在处理...")
            img_url_myxuebi = process_and_upload_image(img)
        except NoSuchElementException:
            pass

        if modelAi == "ollama":
            print("暂不支持ollama填空")
        else:
            if img_url_myxuebi:
                ans = ty_tiankong_img(que, kong_num, img_url_myxuebi)
                if ans == "error":
                    if not click_next_button(): sys.exit(0)
                    return
            else:
                ans = ty_tiankong(que, kong_num)
            
            # 清理答案列表，去除空白符和空行
            ans_list = [a.strip() for a in ans.split("\n") if a.strip()]
            print("AI参考答案：" + str(ans_list))

            if len(ans_list) >= kong_num:
                for j in range(kong_num):
                    try:
                        input_bar = kong[j].find_element(By.XPATH, ".//iframe | .//input")
                        input_bar.click()
                        input_bar.send_keys(ans_list[j])
                    except Exception as e:
                        print(f"第 {j+1} 空填入失败: {e}")
            else:
                print("错误：AI返回的答案数量与实际空数不符，请手动补充。")

        time.sleep(2)
        if not click_next_button(): sys.exit(0)

    else:
        print(f"暂不支持的题型: {num_ele.text[:5]}...")
        if not click_next_button(): sys.exit(0)

def click_next_button():
    try:
        next_button = browser.find_element(By.XPATH, '//a[text()="下一题"]')
        next_button.click()
        return True
    except NoSuchElementException:
        print("\n没有找到“下一题”按钮，可能是已经到达最后一题。")
        print("题目填写已结束，请手动检查是否有遗漏！")
        print("程序将退出，您可以手动点击提交并关闭浏览器。")
        return False
    except Exception as e:
        print(f"点击下一题按钮失败: {e}")
        return False

def getque():
    print("进入考试模式 (单题翻页)")
    while True:
        time.sleep(0.5)
        extract_question_and_options()

def extract_question_and_options_homework():
    question_divs = browser.find_elements(By.XPATH, "//div[contains(@class,'questionLi') and contains(@class,'singleQuesId')]")
    total = len(question_divs)
    if total == 0:
        print("未检测到作业题目，页面可能未加载完成...")
        time.sleep(2)
        return

    print(f"共找到 {total} 道题目")

    for idx, question_div in enumerate(question_divs, 1):
        print(f"\n--- 正在处理第 {idx}/{total} 题 ---")
        browser.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", question_div)
        time.sleep(0.5)

        question_type = question_div.get_attribute("typename")
        if not question_type:
             question_type = "未知类型"

        try:
            title_element = question_div.find_element(By.XPATH, ".//h3[contains(@class,'mark_name')]")
            full_title = title_element.text.strip()
        except:
            print(f"第 {idx} 题无法获取题干，跳过")
            continue

        option_elements = question_div.find_elements(By.XPATH, ".//div[contains(@class,'answerBg')]")
        options_text = ""
        for opt in option_elements:
            try:
                letter = opt.find_element(By.XPATH, ".//span[contains(@class,'num_option')]").text
                content = opt.find_element(By.XPATH, ".//div[contains(@class,'answer_p')]").text
                options_text += f"{letter}: {content} "
            except:
                continue

        full_question = f"{full_title} {options_text}"
        print(f"题目类型: {question_type}")
        print(f"题目内容: {full_question}")

        if question_type == "单选题":
            ai_answer = ollama(full_question) if modelAi == "ollama" else tongyi(full_question)
            print(f"AI参考答案: {ai_answer}")
            for letter in ["A", "B", "C", "D"]:
                if letter in ai_answer.upper():
                    try:
                        question_div.find_element(By.XPATH, f".//span[text()='{letter}']").click()
                        print(f"已选择选项 {letter}")
                        break
                    except: pass

        elif question_type == "多选题":
            ai_answer = ollama(full_question) if modelAi == "ollama" else tongyi(full_question)
            print(f"AI参考答案: {ai_answer}")
            selected = False
            for letter in ["A", "B", "C", "D", "E", "F"]:
                if letter in ai_answer.upper():
                    try:
                        question_div.find_element(By.XPATH, f".//span[text()='{letter}']").click()
                        print(f"已选择选项 {letter}")
                        selected = True
                        time.sleep(0.2)
                    except: pass
            if not selected: print("未在 AI 答案中找到有效选项")

        elif question_type == "判断题":
            ai_answer = ollama(full_question + "判断题返回对或错") if modelAi == "ollama" else tongyi(full_question + "判断题返回对或错")
            print(f"AI参考答案: {ai_answer}")
            if '对' in ai_answer or 'A' in ai_answer.upper() or 'T' in ai_answer.upper():
                try: question_div.find_element(By.XPATH, ".//span[text()='A']").click(); print("已选择 对 (A)")
                except: pass
            elif '错' in ai_answer or 'B' in ai_answer.upper() or 'F' in ai_answer.upper():
                try: question_div.find_element(By.XPATH, ".//span[text()='B']").click(); print("已选择 错 (B)")
                except: pass

        elif "填空" in question_type:
            print("识别为填空题，正在解析...")
            kong = question_div.find_elements(By.XPATH, ".//div[contains(@class,'Answer')]//iframe | .//div[contains(@class,'Answer')]//input")
            if not kong:
                kong = question_div.find_elements(By.XPATH, ".//iframe")
            
            kong_num = len(kong)
            print(f"共检测到 {kong_num} 个填空位置")
            if kong_num == 0: continue

            img_url_myxuebi = ""
            try:
                img = question_div.find_element(By.XPATH, ".//img")
                print("获取到题目图片，正在处理...")
                img_url_myxuebi = process_and_upload_image(img)
            except NoSuchElementException:
                pass 

            if modelAi == "ollama":
                print("暂不支持ollama填空，跳过此题")
                continue
            else:
                if img_url_myxuebi:
                    ans = ty_tiankong_img(full_question, kong_num, img_url_myxuebi)
                    if ans == "error": continue
                else:
                    ans = ty_tiankong(full_question, kong_num)

            ans_list = [a.strip() for a in ans.split("\n") if a.strip()]
            print("AI参考答案：" + str(ans_list))

            if len(ans_list) >= kong_num:
                for j in range(kong_num):
                    try:
                        input_bar = kong[j]
                        input_bar.click()
                        input_bar.send_keys(ans_list[j])
                        print(f"第 {j+1} 空已填入：{ans_list[j]}")
                    except Exception as e:
                        print(f"第 {j+1} 空填入失败: {e}")
            else:
                print("错误：AI返回的答案数量与实际空数不符，请手动填写。")

        else:
            print(f"暂不支持的题型: {question_type}，跳过")

        time.sleep(1) 

    print("\n所有题目处理完毕，正在查找提交按钮...")
    try:
        submit_btn = browser.find_element(By.XPATH, "//a[contains(text(),'提交')] | //button[contains(text(),'提交')] | //input[@value='提交']")
        submit_btn.click()
        print("已点击提交按钮，请检查页面确认提交。")
    except NoSuchElementException:
        print("未找到提交按钮，请手动提交。")
    
    print("答题完成，浏览器保持打开，可手动检查。")
    sys.exit(0)

if homework == 'n':
    getque()
else:
    print("进入作业模式 (一页到底)")
    extract_question_and_options_homework()
