from time import sleep
from analis_agend import pipeline
from pprint import pprint
from playwright.sync_api import sync_playwright
def enter(p):
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto('https://kwork.ru/projects')
    page.click(".login-js")
    page.wait_for_selector(".auth-form")
    page.fill('input[type="text"][placeholder*="почта"]', "mail")
    page.fill('input[type="password"]', 'pass')
    page.click('button:has-text("Войти")')
    page.wait_for_load_state("networkidle")
    page.goto('https://kwork.ru/projects?fc=41')
    return page

def get_kworks(page):
    print(1)
    page.wait_for_selector('.want-card')
    projects_list = []
    cards = page.locator('.want-card').all()
    for card in cards:
        title = card.locator('.wants-card__header-title a').inner_text()
        desc_blocks = card.locator('.wants-card__description-text div.breakwords').all()
        if len(desc_blocks) > 1:
            description = desc_blocks[1].text_content()
        else:
            description = card.locator('.wants-card__description-text').first.text_content()
        cost = int(card.locator(".wants-card__price .d-inline").inner_text().replace(" ", "").replace("₽", "").strip())
        project_id = page.locator(".want-card").locator("a").first.get_attribute("href").replace("projects","").replace("/","")
        projects_list.append({
            "название": title,
            "тз": description,
            "cost": cost,
            "id":project_id
        })
    next_button = page.locator('.pagination__arrow.pagination__arrow--next')
    if next_button.count() > 0 and next_button.is_enabled():
        next_button.click()
        page.wait_for_selector('.want-card', state='attached')
        page.wait_for_timeout(1000)  # небольшая пауза для уверенности
        return projects_list + get_kworks(page)
    else:
        return projects_list
def make_in_kwork(page, result):
    text = result["response"]
    cost = result['cost']
    project_id = result["id"]
    print(project_id)
    name = result["short_title"]
    print(3)
    page.goto('https://kwork.ru/new_offer?project='+ project_id)

    page.wait_for_load_state("networkidle")

    page.locator('.trumbowyg-editor[placeholder*="Напишите, как вы будете решать"]').fill(text)
    page.locator('#offer-custom-price').fill(
        str(max(500, int(round(cost * 0.7, -2))))
    )
    print(name)
    page.locator('.trumbowyg-editor[placeholder*="Введите название заказа"]').fill(name)

    page.get_by_role("combobox", name="Search for option").click()
    page.get_by_role("option", name="2 дня").click()
with sync_playwright() as p:
    enter_page = enter(p)
    kworks = get_kworks(enter_page)
    a = pipeline.invoke(kworks[12])
    pprint(a)
    #     print(2)
    #     result = pipeline.invoke(kwork)
    #     result_clean = {
    #         "cost": result["cost"],
    #         "id": result["id"],
    #         "status": result["status"],
    #         "response": result["response"],
    #         "short_title": result["short_title"],
    #     }
    #     if result_clean["status"] == "rejected":
    #         pass
    #     else:
    #         make_in_kwork(enter_page, result)
