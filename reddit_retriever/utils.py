import ffmpeg
from bs4 import BeautifulSoup
import requests
from selenium import webdriver

def convert_to_mp4(m3u8_url):
    stream = ffmpeg.input(m3u8_url)
    stream = ffmpeg.output(stream, 'output.mp4', loglevel='error')
    try:
        ffmpeg.run(stream, overwrite_output=True)
    except ffmpeg.Error as e:
        print(e.stderr)
        return None
    with open('output.mp4', 'rb') as f:
        return f.read()

def download_media(url):
    response = requests.get(url)
    if response.status_code == 200:
        media = []
        content_type = response.headers.get('Content-Type')
        if 'image' in content_type or 'gif' in content_type:
            media.append(response.content)
        elif 'text/html' in content_type.lower():
            soup = BeautifulSoup(response.text, 'html.parser')
            video_element = soup.find('source')
            if video_element:
                video_url = video_element.get('src')
                if video_url:
                    media.append(convert_to_mp4(video_url))
            else:
                driver = webdriver.Chrome()
                driver.get(url)
                requests.get(url)
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                for img in soup.select('figure img'):
                    media.append(requests.get(img['src']).content)
        else:
            return None
        return media
    else:
        return None

