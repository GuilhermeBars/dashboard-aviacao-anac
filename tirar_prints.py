"""Captura screenshots atualizados dos dois dashboards (página inteira)."""
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8050/"
FIG = Path(__file__).resolve().parent / "figuras"


def esperar_graficos(page, n_min):
    # espera os gráficos Plotly desenharem (cada um vira um .main-svg)
    page.wait_for_selector(".js-plotly-plot", timeout=30000)
    page.wait_for_function(
        f"document.querySelectorAll('.js-plotly-plot .main-svg').length >= {n_min}",
        timeout=30000)
    page.wait_for_timeout(2500)  # folga p/ animações/legendas assentarem


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1500, "height": 1000},
                            device_scale_factor=1)
    page.goto(URL, wait_until="networkidle")

    # ---- Dashboard 1 (aba padrão) ----
    esperar_graficos(page, 5)            # KPIs + 5 gráficos
    page.screenshot(path=str(FIG / "dashboard1_visao_geral.png"), full_page=True)
    print("ok: dashboard1_visao_geral.png")

    # ---- Dashboard 2 (clica na aba) ----
    page.click("text=Exploração Interativa")
    esperar_graficos(page, 7)            # 7 visualizações
    # o mapa geográfico baixa o topojson (mapa-base) de forma assíncrona:
    # espera a rede ficar ociosa e o <path class="land"> aparecer
    page.wait_for_load_state("networkidle")
    try:
        page.wait_for_selector("g.geolayer path.land", timeout=20000)
    except Exception:
        pass
    page.wait_for_timeout(3000)
    page.screenshot(path=str(FIG / "dashboard2_exploracao.png"), full_page=True)
    print("ok: dashboard2_exploracao.png")

    browser.close()
print("concluido")
