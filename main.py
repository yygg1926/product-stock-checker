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
        "name": "Ricoh GR4 - 사에키",
        "url": "https://www.saeki.co.kr/item/itemDetail?itemId=PD00041564",
    },
    {
        "name": "Ricoh GR4 (다른 옵션) - 사에키",
        "url": "https://www.saeki.co.kr/item/itemDetail?itemId=PD00042145",
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
            (By.CSS_SELECTOR, "div.btn-area.type-ui")
        )
    )

    soldout_btn = driver.find_elements(By.ID, "btnWhrcvNotice")
    buy_btn = driver.find_elements(By.ID, "btnBuyNow")

    print(f"[확인] {name}")
    print(f"입고알림 버튼 있음(품절): {len(soldout_btn) > 0}")
    print(f"바로구매 버튼 있음(재고): {len(buy_btn) > 0}")

    if buy_btn:
        return True

    if soldout_btn:
        return False

    print(f"알 수 없는 버튼 상태입니다: {name}")
    return False

def main():
    send_telegram("GR4 재고 감시를 시작합니다.")

    already_alerted = set()
    driver = create_driver()

    try:
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

        print("재고 확인 완료")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()