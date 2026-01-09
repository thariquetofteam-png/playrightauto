def test_google_pass(browser_context):
    page = browser_context
    page.goto("https://www.google.com")
    assert page.title() == "Google"  # This will pass

def test_google_fail(browser_context):
    page = browser_context
    page.goto("https://www.google.com")
    assert page.title() == "Not Google"  # This will fail → triggers screenshot