import os
import time
import requests
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "300"))

PRODUCTS = [
    {
        "name": "Sony RX100M7 - 소니스토어",
        "url": "https://store.sony.co.kr/product-view/102263765",
    },
    {
        "name": "Sony RX100M7G - 소니스토어",
        "url": "https://store.sony.co.kr/product-view/102263764",
    }
]


def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    response = requests.post(
        url,
        data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
        },
        timeout=10,
    )

    response.raise_for_status()
    print("텔레그램 알림 전송 완료")


def create_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=ko-KR")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    return driver


def get_page_text_by_selenium(driver, url: str) -> str:
    driver.get(url)
    time.sleep(5)

    return driver.find_element("tag name", "body").text


def check_stock(driver, product: dict) -> bool:
    name = product["name"]
    url = product["url"]

    driver.get(url)

    wait = WebDriverWait(driver, 20)

    wait.until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "div.product_view_about")
        )
    )

    # 1차 판단: 상품 영역에 soldout 클래스가 붙어 있으면 품절
    soldout_area = driver.find_elements(
        By.CSS_SELECTOR,
        "div.product_view_about.soldout"
    )

    # 2차 판단: 최종 구매 버튼 확인
    final_button = wait.until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "li.final a.btn_style")
        )
    )

    button_text = final_button.text.strip()
    button_class = final_button.get_attribute("class") or ""
    button_html = final_button.get_attribute("outerHTML") or ""

    print(f"[확인] {name}")
    print(f"품절 영역 있음: {len(soldout_area) > 0}")
    print(f"버튼 텍스트: {button_text}")
    print(f"버튼 class: {button_class}")
    print("버튼 HTML:")
    print(button_html)
    # test code
    # if button_text in ["품절", "일시품절", "재입고 알림", "구매불가"]:
    #     return True

    # if soldout_area:
    #     return False

    # if "disabled" in button_class:
    #     return False

    # if button_text in ["구매하기", "바로구매", "구매", "예약구매"]:
    #     return False

    if soldout_area:
        return False

    if "disabled" in button_class:
        return False

    if button_text in ["품절", "일시품절", "재입고 알림", "구매불가"]:
        return False

    if button_text in ["구매하기", "바로구매", "구매", "예약구매"]:
        return True

    print(f"알 수 없는 버튼 상태입니다: {button_text}")
    return False

def main():
    send_telegram("RX100M7 재고 감시를 시작합니다.")

    already_alerted = set()
    driver = create_driver()

    try:
        while True:
            print("=" * 50)
            print("재고 확인 시작")

            for product in PRODUCTS:
                try:
                    product_name = product["name"]
                    in_stock = check_stock(driver, product)

                    if in_stock and product_name not in already_alerted:
                        message = (
                            f"재입고 가능성이 있습니다!\n\n"
                            f"상품명: {product_name}\n"
                            f"URL: {product['url']}"
                        )
                        send_telegram(message)
                        already_alerted.add(product_name)

                    elif not in_stock:
                        print(f"아직 품절 상태로 보입니다: {product_name}")

                except Exception as e:
                    print(f"오류 발생: {product['name']}")
                    print(e)

            print(f"{CHECK_INTERVAL_SECONDS}초 후 다시 확인합니다.")
            time.sleep(CHECK_INTERVAL_SECONDS)

    finally:
        driver.quit()


if __name__ == "__main__":
    main()