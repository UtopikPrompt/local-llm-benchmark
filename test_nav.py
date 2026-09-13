from playwright.sync_api import sync_playwright


def main():
    p = sync_playwright().start()
    b = p.chromium.launch()
    pg = b.new_page()
    pg.goto('http://localhost:8000/', wait_until='networkidle')
    pg.wait_for_timeout(4000)

    # Test fetch directly with try/catch to see what happens
    result = pg.evaluate(
        r"""() => {
          try {
            const resp = fetch('/api/config/engines', { method: 'GET' });
            resp.then(r => r.json()).then(data => ({ status: r.status, engines: data.engines }));
          } catch(e) {
            return { error: e.message };
          }
        }"""
    )
    print('apiResult:', result)
    b.close()
    p.stop()


if __name__ == '__main__':
    main()
