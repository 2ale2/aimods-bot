from time import sleep
from random import randint
from playwright.sync_api import sync_playwright


def compute_dick_size():
    print("Calcolo in corso...")
    sleep(1)
    print(f"Minchia hai un pisello da {randint(30, 35)}cm... enorme!")
    sleep(1)
    print("Scherzo, ecco il tuo URL... :)")


def get_download_url():
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        page = browser.new_page()

        download_url = None

        def handle_download(download):
            nonlocal download_url
            download_url = download.url
            download.cancel()

        def handle_request(request):
            nonlocal download_url
            if "flashbang.sh" in request.url and "/dl/" in request.url:
                download_url = request.url

        def handle_response(response):
            nonlocal download_url
            if "flashbang.sh" in response.url and "/dl/" in response.url:
                download_url = response.url

            if response.status in [301, 302, 303, 307, 308]:
                location = response.headers.get("location", "")
                if "flashbang.sh" in location:
                    download_url = location
                    print(f"Redirect intercettato: {location}")

        page.on("download", handle_download)
        page.on("request", handle_request)
        page.on("response", handle_response)

        try:
            page.goto("https://buzzheavier.com/hzxqu2vzonz3")
            print("Pagina caricata")

            max_attempts = 15
            attempt = 0

            while attempt < max_attempts and not download_url:
                attempt += 1
                print(f"Tentativo {attempt}/{max_attempts}")

                try:
                    page.wait_for_selector("a.link-button.gay-button[hx-get*='download']", timeout=10000)

                    download_button = page.locator("a.link-button.gay-button[hx-get*='download']")

                    download_button.click()

                    page.wait_for_timeout(5000)

                    if download_url:
                        break

                    print("Nessun download rilevato, riprovo...")

                    sleep(randint(1, 3))

                except Exception as e:
                    print(f"Errore nel tentativo {attempt}: {str(e)[:100]}...")
                    sleep(randint(2, 4))
                    continue

            if download_url:
                compute_dick_size()
                return download_url
            else:
                print(f"Nessun download intercettato dopo {max_attempts} tentativi")
                return None

        except Exception as e:
            print(f"Errore fatale: {e}")
            return None
        finally:
            browser.close()


# SE NON FUNZIONA IL METODO DI PRIMA
def get_download_url_alternative():
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        page = browser.new_page()

        download_url = None
        all_requests = []

        def handle_request(request):
            nonlocal download_url
            all_requests.append(request.url)

            if any(pattern in request.url for pattern in [
                "flashbang.sh",
                "/dl/",
                "/download/",
                "?download=",
                ".zip", ".rar", ".7z", ".mp4", ".mkv"
            ]):
                if "flashbang.sh" in request.url:
                    download_url = request.url
                    print(f"URL di download trovato: {request.url}")

        page.on("request", handle_request)

        try:
            page.goto("https://buzzheavier.com/hzxqu2vzonz3")

            for attempt in range(1, 16):
                print(f"Tentativo alternativo {attempt}/15")

                try:
                    selectors = [
                        "a.link-button.gay-button[hx-get*='download']",
                        "a[hx-get*='download']",
                        "a:has-text('Download')"
                    ]

                    clicked = False
                    for selector in selectors:
                        try:
                            if page.locator(selector).count() > 0:
                                page.locator(selector).first.click()
                                clicked = True
                                print(f"Click effettuato con: {selector}")
                                break
                        except:
                            continue

                    if not clicked:
                        print("Nessun bottone trovato")
                        continue

                    page.wait_for_timeout(7000)

                    if download_url:
                        break

                    print(f"Richieste intercettate: {len(all_requests)}")
                    recent_requests = [r for r in all_requests[-5:] if 'buzzheavier' in r or 'flashbang' in r]
                    if recent_requests:
                        print(f"Richieste recenti: {recent_requests}")

                except Exception:
                    print(f"Errore tentativo {attempt}")
                    continue

            if download_url:
                compute_dick_size()
                return download_url

            print("Debug - Tutte le richieste intercettate:")
            unique_domains = set()
            for req in all_requests:
                try:
                    domain = req.split('/')[2]
                    unique_domains.add(domain)
                except:
                    pass

            print(f"Domini rilevati: {list(unique_domains)}")
            return None

        except Exception as e:
            print(f"❌ Errore metodo alternativo: {e}")
            return None
        finally:
            browser.close()


# SE NON FUNZIONA IL METODO DI PRIMA
def get_download_url_with_network_events():
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        download_url = None

        def handle_request(request):
            nonlocal download_url
            if "flashbang.sh" in request.url:
                download_url = request.url

        def handle_response(response):
            nonlocal download_url
            if "flashbang.sh" in response.url:
                download_url = response.url

        context.on("request", handle_request)
        context.on("response", handle_response)

        try:
            page.goto("https://buzzheavier.com/hzxqu2vzonz3")

            for attempt in range(1, 11):
                print(f"Tentativo con eventi network {attempt}/10")

                try:
                    page.wait_for_selector("a:has-text('Download')", timeout=8000)

                    with page.expect_request_finished() as request_info:
                        page.click("a:has-text('Download')")

                    page.wait_for_timeout(4000)

                    if download_url:
                        break

                except Exception as e:
                    print(f"Errore network events {attempt}")
                    continue

            if download_url:
                compute_dick_size()
                return download_url

            return None

        except Exception as e:
            print(f"Errore eventi network: {e}")
            return None
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    print("Inizializzazione intercettazione download...")
    url = get_download_url()
    # SE NON FUNZIONA IL METODO 1, SCOMMENTA IL PRIMO IF. SE NON FUNZIONA MANCO IL SECONDO, SCOMMENTA IL TERZO IF
    # if not url:
    #     print("\nMetodo alternativo...")
    #     url = get_download_url_alternative()
    # if not url:
    #     print("\nMetodo con eventi network...")
    #     url = get_download_url_with_network_events()

    if url:
        print(f"\nURL DI DOWNLOAD TROVATO: {url}")
    else:
        print(f"\nImpossibile intercettare l'URL di download, probabilmente hai il pisello troppo piccolo...")
