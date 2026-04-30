import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

IN_FILE = Path("bridge/outgoing_to_chatgpt.json")
STATE_FILE = Path("bridge/chatgpt_output_worker_state.json")

POLL_INTERVAL = 1.0
CDP_URL = "http://localhost:9222"
MAX_WAIT = 30
WORKER_STARTED_AT = time.time()


def load_json(path, default=None):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default or {}


def save_json(path, data):
    path.write_text(json.dumps(data))


def read_output():
    data = load_json(IN_FILE, {})
    if data:
        try:
            preview = data.get("text", "")
            preview = preview.replace("\n", "\\n")
            if len(preview) > 200:
                preview = preview[:200] + "...<truncated>"
            print(f"[OUTPUT DEBUG] read payload key={data.get('dedupe_key','')} text={preview}")
        except Exception:
            print("[OUTPUT DEBUG] read payload (preview unavailable)")
    return data


def clear_output():
    print("[OUTPUT DEBUG] clearing outgoing file")
    save_json(IN_FILE, {})


def pick_chatgpt_page(browser):
    for context in browser.contexts:
        for page in context.pages:
            try:
                url = page.url or ""
                if "chatgpt.com" in url or "chat.openai.com" in url:
                    return page
            except Exception:
                continue
    return browser.contexts[0].pages[0]


def get_visible_composer(page):
    candidates = [
        'textarea[placeholder="Ask anything"]',
        'textarea[name="prompt-textarea"]',
        'div[contenteditable="true"]',
    ]
    for sel in candidates:
        loc = page.locator(sel)
        count = loc.count()
        for i in range(count):
            item = loc.nth(i)
            try:
                if item.is_visible():
                    return item
            except Exception:
                continue
    return None


def composer_is_empty(page):
    composer = get_visible_composer(page)
    if not composer:
        return False
    tag = composer.evaluate("(el) => el.tagName.toLowerCase()")
    text = composer.inner_text().strip() if tag == "div" else composer.input_value()
    return text == ""


def fill_and_send(page, text):
    composer = get_visible_composer(page)
    if not composer:
        raise RuntimeError("No visible composer")

    composer.click()
    tag = composer.evaluate("(el) => el.tagName.toLowerCase()")

    if tag == "textarea":
        composer.fill(text)
    else:
        composer.fill("")
        composer.type(text)

    time.sleep(0.3)

    composer.press("Enter")
    time.sleep(1.0)

    if not composer_is_empty(page):
        raise RuntimeError("Composer still not empty after Enter; send likely failed")


def main():
    state = load_json(STATE_FILE, {})
    last_key = state.get("last_sent_key", "")
    last_text = state.get("last_sent_text", "")

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP_URL)
        page = pick_chatgpt_page(browser)
        print("Output worker connected")
        print(f"[OUTPUT] page url: {page.url}")

        while True:
            try:
                data = read_output()
                if not data:
                    time.sleep(POLL_INTERVAL)
                    continue

                text = data.get("text", "").strip()
                key = data.get("dedupe_key", "").strip()
                payload_ts = float(data.get("timestamp", 0) or 0)

                if payload_ts and payload_ts < WORKER_STARTED_AT:
                    print("[OUTPUT] stale payload skipped")
                    clear_output()
                    time.sleep(POLL_INTERVAL)
                    continue

                if not text:
                    clear_output()
                    time.sleep(POLL_INTERVAL)
                    continue

                if (key and key == last_key) or (not key and text == last_text):
                    print("[OUTPUT] duplicate payload skipped")
                    clear_output()
                    time.sleep(POLL_INTERVAL)
                    continue

                waited = 0
                while not composer_is_empty(page):
                    time.sleep(0.5)
                    waited += 0.5
                    if waited > MAX_WAIT:
                        print("[OUTPUT] composer never cleared, skipping send")
                        break
                else:
                    fill_and_send(page, text)
                    last_key = key
                    last_text = text
                    save_json(STATE_FILE, {
                        "last_sent_key": last_key,
                        "last_sent_text": last_text,
                    })
                    clear_output()
                    print("[OUTPUT] sent")

            except PlaywrightTimeoutError as e:
                print(f"[OUTPUT ERROR] {e}")
                time.sleep(2)
            except Exception as e:
                print(f"[OUTPUT ERROR] {e}")
                time.sleep(2)


if __name__ == "__main__":
    main()
