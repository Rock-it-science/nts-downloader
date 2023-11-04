import logging
import os
import time

from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from nts.downloader import download

from tqdm import tqdm

load_dotenv()
logging.basicConfig(level=logging.INFO)

options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument("window-size=1200x600")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

driver.get('https://www.nts.live/my-nts/favourites/episodes')

# Accept cookies
driver.find_element(By.ID, 'onetrust-accept-btn-handler').click()

# Log-in
user_box = driver.find_element(By.XPATH, '//*[@id="react-content"]/div[10]/div/div/form/div[1]/input')
logging.debug('User box is displayed? ' + str(user_box.is_displayed()))
user_box.send_keys(os.environ['NTS_EMAIL'])
driver.find_element(By.NAME, 'password').send_keys(os.environ['NTS_PASS'])
driver.find_element(By.XPATH, "//input[@value='Log in']").click()

# Wait for load
wait = WebDriverWait(driver, timeout=10)
wait.until(lambda d: driver.find_element(By.CLASS_NAME, 'my-nts__list-container').is_displayed())

# Scroll to load more
logging.info('Logged in, scrolling through pages...')
for i in tqdm(range(0,40)):
    driver.find_element(By.CSS_SELECTOR, 'body').send_keys(Keys.END)
    time.sleep(1)

# Get list of fav episodes
favourites = driver.find_element(By.CLASS_NAME, 'my-nts__list-container')
links = favourites.find_elements(By.CLASS_NAME, 'nts-link')
nts_urls = []
for item in links:
    nts_urls.append(item.get_property("href"))

driver.close()

# Download shows using nts-everdrone
logging.info('Looking for new episodes...')
with open('downloaded_episodes.txt', 'r') as f:
    existing_episodes = f.readlines()
for nts_url in tqdm(nts_urls):
    if nts_url+'\n' not in existing_episodes:
        logging.info(f'Downloading: {nts_url}')
        try:
            download(nts_url, quiet=False, save_dir='/media/downloads/music/nts-shows')
            with open('downloaded_episodes.txt', 'a') as f:
                f.write(nts_url+'\n')
        except Exception as e:
            logging.error('!  Error with download. Moving on.')
            logging.info(e)
