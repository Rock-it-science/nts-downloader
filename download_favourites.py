import logging
import os
import time

from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait

from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from slack_sdk.webhook import WebhookClient
from nts.downloader import download
from tqdm import tqdm

def scrape_favourites() -> list:
    """
    Scrape NTS favourites page for URLs of episodes
    """
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("window-size=1200x600")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    driver.get('https://www.nts.live/my-nts/favourites/episodes')

    # Accept cookies
    try:
        driver.find_element(By.ID, 'onetrust-accept-btn-handler').click()
    except:
        logging.debug('Could not find cookies box')
    
    time.sleep(1)
            
    # Log-in
    try:
        # There are 2 username entry fields in the dom - fetch the visible one
        user_boxes = driver.find_elements(By.XPATH, "//input[@name='username']")
        if user_boxes[0].is_displayed():
            user_box = user_boxes[0]
        else:
            user_box = user_boxes[1]
    except:
        driver.save_screenshot('/nts/logs/debug_screenshots/no_user_box.png')
        raise Exception('User input box not found')
    logging.debug('User box is displayed? ' + str(user_box.is_displayed()))
    user_box.send_keys(os.environ['NTS_EMAIL'])
    time.sleep(2)
    try:
        next_button = driver.find_element(By.XPATH, "//button[text() = 'Next']")
    except:
        driver.save_screenshot('/nts/logs/debug_screenshots/no_next_btn.png')
        raise Exception('Next button box not found')
    if not next_button.is_enabled():
        driver.save_screenshot('/nts/logs/debug_screenshots/disabled_next_button.png')
        raise Exception('Next button disabled')
    next_button.click()
    time.sleep(2)
    password_box = driver.find_element(By.XPATH, "//input[@name='password'][@class='password-input__input nts-form__input nts-form__input--condensed']")
    if not password_box.is_displayed():
        driver.save_screenshot('/nts/logs/debug_screenshots/no_password_box.png')
        raise Exception('Password input not found.')
    password_box.send_keys(os.environ['NTS_PASS'])
    try:
        driver.find_element(By.XPATH, "//button[text() = 'Log in']").click()
    except:
        driver.save_screenshot('/nts/logs/debug_screenshots/no_log_in_btn.png')
        raise Exception('Log in button not found')

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
        url = item.get_property("href")
        if '/episodes/' in url:
            nts_urls.append(url)

    driver.close()
    return nts_urls


def download_shows(nts_urls: list) -> None:
    """
    Download NTS show episodes using nts-everdrone
    """
    logging.info('\nLooking for new episodes...')
    with open('/nts/logs/downloaded_episodes.txt', 'r') as f:
        existing_episodes = f.readlines()
    for nts_url in tqdm(nts_urls):
        if nts_url+'\n' not in existing_episodes:
            logging.info(f'\nDownloading: {nts_url}')
            try:
                parsed = download(nts_url, quiet=False, save_dir=f'/downloads/music/nts-shows/')
                with open('/nts/logs/downloaded_episodes.txt', 'a') as f:
                    f.write(nts_url+'\n')
            except Exception as e:
                logging.error('!  Error with download, message from nts downloader:')
                with open('/nts/logs/error_urls.txt', 'a') as f:
                    f.write(nts_url+'\n')
                logging.info(e)
                logging.info('Moving on.')
    return

def subfolders():
    """
    Parse nts shows directory and move shows to subdirectories to help with Plex auto-organization.
    """
    for root, dirs, files in os.walk('/downloads/music/nts-shows'):
        for file in files:
            show_name = file.split(' w-')[0].split(' -')[0].split('.')[0]
            if show_name not in dirs:
                new_dir = os.path.join(root,show_name)
                os.mkdir(new_dir)
                logging.info(f'Creating dir {new_dir}')
                dirs.append(show_name)
            os.rename(os.path.join(root,file), os.path.join(root,show_name,file))
        break


if __name__ == '__main__':
    stage = 'Load .env'
    try:
        load_dotenv()
        logging.basicConfig(level=logging.INFO, filename='/nts/logs/log.txt', format='%(asctime)s %(levelname)s %(name)s %(message)s')
        stage = 'scraping'
        nts_urls = scrape_favourites()
        stage = 'download shows'
        download_shows(nts_urls)
        stage = 'organize directories'
        subfolders()
    except Exception as e:
        logging.exception(f'!! Script failed at stage {stage}', exc_info=True)
        webhook = WebhookClient(os.environ['SLACK_WEBHOOK'])
        response = webhook.send(text=f"NTS Downloader failed at {stage} stage")
