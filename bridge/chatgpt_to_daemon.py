import json
import time
import hashlib
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

STATE_FILE = Path("bridge/chatgpt_worker_state.json")
OUT_FILE = Path("bridge/incoming_from_chatgpt.json")

POLL_INTERVAL = 1.0
CDP_URL = "http://localhost:9222"

JARVIS_PATTERN = re.compile(
    r"\[JARVIS_COMMAND\]\s*(.*?)\s*\[/JARVIS_COMMAND\]",
    re.DOTALL,
)

TERMINAL_PATTERN = re.compile(
    r"\[TERMINAL_COMMAND\]\s*(.*?)\s*\[/TERMINAL_COMMAND\]",
    re.DOTALL,
)


def load_json(path, default=None):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default or {}


def save_json_atomic(path, data):
    """Write JSON atomically via a temp file to avoid corrupt reads mid-write."""
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data))
    tmp.rename(path)


def stable_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def extract_blocks(text):
    blocks = []
    stripped = text.strip()

    jarvis_matches = list(JARVIS_PATTERN.finditer(text))
    terminal_matches = list(TERMINAL_PATTERN.finditer(text))
    all_matches = jarvis_matches + terminal_matches

    if len(all_matches) != 1:
        return blocks

    match = all_matches[0]
    raw_block = match.group(0).strip()

    if stripped != raw_block:
        return blocks

    if match.re is JARVIS_PATTERN:
        command = match.group(1).strip()
        if command:
            blocks.append({
                "mode": "jarvis",
                "command": command,
                "raw_block": raw_block,
                "dedupe_key": stable_hash("jarvis|" + raw_block),
            })

    elif match.re is TERMINAL_PATTERN:
        command = match.group(1).strip()
        if command:
            blocks.append({
                "mode": "terminal",
                "command": command,
                "raw_block": raw_block,
                "dedupe_key": stable_hash("terminal|" + raw_block),
            })

    return blocks


def get_chatgpt_page(browser):
    print("[LISTENER] Open pages:")
    for ci, context in enumerate(browser.contexts):
        for pi, page in enumerate(context.pages):
            try:
                print(f"  context={ci} page={pi} url={page.url}")
            except Exception:
                print(f"  context={ci} page={pi} url=<unavailable>")

    for context in browser.contexts:
        for page in context.pages:
            try:
                url = page.url or ""
                if "chatgpt.com" in url or "chat.openai.com" in url:
                    return page
            except Exception:
                continue
    if browser.contexts and browser.contexts[0].pages:
        return browser.contexts[0].pages[0]
    raise RuntimeError("No ChatGPT page found")


def get_assistant_locator(page):
    return page.locator('div[data-message-author-role="assistant"]')


def get_assistant_text(locator, index):
    try:
        text = locator.nth(index).inner_text().strip()
        return text if text else None
    except Exception:
        return None


def process_text(text, seen_keys, last_processed_message_hash=""):
    emitted = False

    source_message_hash = stable_hash(text)
    if source_message_hash == last_processed_message_hash:
        return False, last_processed_message_hash

    has_open = ("[JARVIS_COMMAND]" in text or "[TERMINAL_COMMAND]" in text)
    has_close = ("[/JARVIS_COMMAND]" in text or "[/TERMINAL_COMMAND]" in text)

    preview = text.replace("\n", "\\n")
    if len(preview) > 500:
        preview = preview[:500] + "...<truncated>"

    if has_open and not has_close:
        print(f"[LISTENER DEBUG] incomplete command block, waiting: {preview}")
        return False, last_processed_message_hash

    blocks = extract_blocks(text)
    print(f"[LISTENER DEBUG] assistant text preview: {preview}")
    print(f"[LISTENER DEBUG] extracted block count: {len(blocks)}")

    if not blocks:
        return False, last_processed_message_hash

    block = blocks[0]
    key = stable_hash(block["mode"] + "|" + block["raw_block"] + "|" + source_message_hash)

    if key in seen_keys:
        print(f"[LISTENER DEBUG] duplicate block skipped: {block['command']}")
        return False, source_message_hash

    payload = {
        "mode": block["mode"],
        "command": block["command"],
        "dedupe_key": key,
        "source_message_hash": source_message_hash,
        "timestamp": time.time(),
    }

    save_json_atomic(OUT_FILE, payload)
    seen_keys.add(key)
    emitted = True
    print(f'[LISTENER] New {block["mode"]} command: {block["command"]}')
    return emitted, source_message_hash


def main():
    state = load_json(STATE_FILE, {})
    seen_keys = set(state.get("seen_keys", []))
    last_count = int(state.get("last_count", 0))
    last_last_assistant_hash = state.get("last_last_assistant_hash", "")
    last_processed_message_hash = state.get("last_processed_message_hash", "")

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP_URL)
        page = get_chatgpt_page(browser)

        locator = get_assistant_locator(page)
        count = locator.count()
        last_count = count

        if count > 0:
            last_text = get_assistant_text(locator, count - 1) or ""
            last_last_assistant_hash = stable_hash(last_text)
        else:
            last_last_assistant_hash = ""

        print("Listener connected")
        print(f"[LISTENER] Startup assistant message count: {count}")

        save_json_atomic(STATE_FILE, {
            "seen_keys": sorted(seen_keys),
            "last_count": last_count,
            "last_last_assistant_hash": last_last_assistant_hash,
            "last_processed_message_hash": last_processed_message_hash,
        })

        while True:
            try:
                locator = get_assistant_locator(page)
                count = locator.count()

                if count != last_count:
                    print(f"[LISTENER DEBUG] assistant count changed: {last_count} -> {count}")
                    last_count = count

                if count > 0:
                    last_text = get_assistant_text(locator, count - 1) or ""
                    current_hash = stable_hash(last_text)

                    if current_hash != last_last_assistant_hash:
                        print("[LISTENER DEBUG] last assistant hash changed")
                        _, last_processed_message_hash = process_text(
                            last_text,
                            seen_keys,
                            last_processed_message_hash,
                        )
                        last_last_assistant_hash = current_hash

                save_json_atomic(STATE_FILE, {
                    "seen_keys": sorted(seen_keys),
                    "last_count": last_count,
                    "last_last_assistant_hash": last_last_assistant_hash,
                    "last_processed_message_hash": last_processed_message_hash,
                })

                time.sleep(POLL_INTERVAL)

            except Exception as e:
                print(f"[LISTENER ERROR] {e}")
                time.sleep(2)


if __name__ == "__main__":
    main()
