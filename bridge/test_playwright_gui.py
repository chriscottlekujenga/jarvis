from playwright.sync_api import sync_playwright

print("starting playwright")

with sync_playwright() as p:
    print("launching chromium")
    browser = p.chromium.launch(headless=False)
    print("opened browser")
    page = browser.new_page()
    page.goto("https://example.com")
    print("page loaded")
    input("Press Enter to close...")
    browser.close()
