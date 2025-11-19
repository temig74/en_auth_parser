import requests
from bs4 import BeautifulSoup
import csv
from time import sleep
import re

my_domain = 'world.en.cx'
game_id = 12345
my_login = 'Temig'
my_password = 'password'
sleep_time = 3
start_id = None  # Если надо пропустить часть пользователей (например, возобновить парсинг после ошибки)
HREF_SEARCH_PATTERN = re.compile(r"/UserDetails\.aspx\?page=\d+&uid=\d+&tab=5")
PAGE_EXTRACT_PATTERN = re.compile(r"page=(\d+)")
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36'}

my_session = requests.session()
my_session.headers = HEADERS


def parse_user_page(html_content, username, writer):
    soup = BeautifulSoup(html_content, 'html.parser')
    results_table = soup.find('div', class_='tabCntHolder_alt')
    if not results_table:
        return

    data_rows = results_table.find_all('tr')

    for row in data_rows:
        if row.find('td', class_='h10') and not row.find('td', class_='h10 bold'):
            td_set = row.find_all('td', class_='h10')
            line_text = [username] + [td.get_text(strip=True) for td in td_set]
            writer.writerow(line_text)


id_list = []
winner_url = f'https://{my_domain}/GameWinnerMembers.aspx?gid={game_id}'
my_request = my_session.get(winner_url)
html = BeautifulSoup(my_request.content, 'html.parser')

parse_set = html.find_all('td', style='padding-left:8px;')
for elem in parse_set:
    link_tag = elem.find('a')
    if link_tag and link_tag.get('href'):
        uid = link_tag.get('href').replace('/UserDetails.aspx?uid=', '')
        id_list.append(uid)

auth_request_json = my_session.post(f'https://{my_domain}/login/signin?json=1', data={'Login': my_login, 'Password': my_password}).json()
if auth_request_json['Error'] == 0:
    print('Авторизация успешна')

    # Открываем CSV файл один раз
    with open(f'auth_{game_id}.csv', 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f, delimiter=';')
        start_flag = True if not start_id else False
        for user_id in id_list:
            if user_id == str(start_id):
                start_flag = True
            if not start_flag:
                continue
            print(f"Обработка пользователя {user_id}...")
            sleep(sleep_time)
            url_page_1 = f'https://{my_domain}/UserDetails.aspx?page=1&uid={user_id}&tab=5'
            my_request = my_session.get(url_page_1)
            html_content = my_request.content
            html = BeautifulSoup(html_content, 'html.parser')
            username = html.find('span', class_='white bold').text
            links = html.find_all('a', href=HREF_SEARCH_PATTERN)
            max_page = 1

            if links:
                last_link = links[-1]
                match = PAGE_EXTRACT_PATTERN.search(last_link['href'])
                if match:
                    max_page = int(match.group(1))

            print(f"Найдено {max_page} страниц авторизации пользователя {username}")

            parse_user_page(html_content, username, writer)
            for page in range(2, max_page + 1):
                sleep(sleep_time)
                url = f'https://{my_domain}/UserDetails.aspx?page={page}&uid={user_id}&tab=5'
                print(f"  -> Загрузка страницы авторизации {page}/{max_page} пользователя {username} ...")
                my_request = my_session.get(url)
                parse_user_page(my_request.content, username, writer)

else:
    print(f"Ошибка авторизации: {auth_request_json.get('Message', 'Неизвестная ошибка')}")
