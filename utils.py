import asyncio
import random

import discord
import pytz
import json

from datetime import datetime
from typing import Dict, Tuple
from seleniumbase import Driver

import requests
from dotenv import load_dotenv

from DatabaseManager import DatabaseManager
from bs4 import BeautifulSoup

from Logger import Logger
from models import ProductData, ProductOptions

load_dotenv()

WINDOWS_USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 OPR/108.0.0.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Vivaldi/6.5.3206.63'
]

db = DatabaseManager()


def get_current_time():
    uk_tz = pytz.timezone('Europe/London')
    return datetime.now(uk_tz).strftime('%d %B %Y, %I:%M:%S %p %Z')


def get_product_embed(product_data: ProductData) -> discord.Embed:
    embed = discord.Embed(title=product_data.name, url=product_data.product_url, color=0x00ff00)
    embed.set_thumbnail(url=product_data.image_url)

    for option in product_data.options:
        embed.add_field(
            name='Variant',
            value=f"[{option.name}]({option.product_url})",
            inline=True
        )
        embed.add_field(
            name='Price',
            value=option.formatted_price,
            inline=True
        )
        embed.add_field(
            name='Stock',
            value=f"{option.stock_level}",
            inline=True
        )
        embed.add_field(
            name='\u200b',
            value='\u200b',
            inline=False
        )

    embed.set_footer(text=f"🕒 Time: {get_current_time()} (UK)")
    return embed


async def get_fresh_cookies(user_agent: str, url: str) -> Dict:
    driver = Driver(uc=True, agent=user_agent, no_sandbox=True)
    driver.uc_open_with_reconnect(url, 3)
    driver.uc_gui_click_captcha()

    driver.uc_click('#onetrust-accept-btn-handler', by="css selector",
                    timeout=30, reconnect_time=None)

    cookies = driver.get_cookies()
    driver.quit()

    cookie_dict = {}
    for cookie in cookies:
        cookie_dict[cookie['name']] = cookie['value']
    return cookie_dict


async def fetch_product_data(url: str, max_retries: int = 3) -> Tuple[discord.Embed, ProductData | None]:
    for attempt in range(max_retries):
        try:
            user_agent = random.choice(WINDOWS_USER_AGENTS)
            cookies = await get_fresh_cookies(user_agent, url)
            headers = {
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'accept-language': 'en-US,en;q=0.7',
                'cache-control': 'max-age=0',
                'priority': 'u=0, i',
                'sec-ch-ua': '"Chromium";v="130", "Brave";v="130", "Not?A_Brand";v="99"',
                'sec-ch-ua-arch': '"x86"',
                'sec-ch-ua-bitness': '"64"',
                'sec-ch-ua-full-version-list': '"Chromium";v="130.0.0.0", "Brave";v="130.0.0.0", "Not?A_Brand";v="99.0.0.0"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-model': '""',
                'sec-ch-ua-platform': '"Windows"',
                'sec-ch-ua-platform-version': '"15.0.0"',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'same-origin',
                'sec-fetch-user': '?1',
                'sec-gpc': '1',
                'upgrade-insecure-requests': '1',
                'user-agent': user_agent,

            }

            response = requests.get(
                url,
                cookies=cookies,
                headers=headers,
            )

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find script tag containing stockLevel
            stock_script = None
            for script in soup.find_all('script'):
                if script.string and 'currentStock' in script.string:
                    stock_script = script.string
                    break

            json_data = stock_script.replace('\n', '')
            json_data = json_data.replace('\\\\\\"', "'")
            json_data = json_data.replace('\\"', '"')
            json_data = json_data[43:-6]

            # Parse the cleaned JSON data
            data = json.loads(json_data)

            variants = data['children'][1][3]['gbProductData']['variantProducts']
            product_details = data['children'][0][3]['data']['product']

            options = []
            if not variants:
                name = product_details['fullName']
                price = product_details['price']['formatted']['withTax']
                stock_level = product_details['currentStock']
                is_in_stock = stock_level > 0
                variant_code = product_details['stockCode']
                options.append(
                    ProductOptions(
                        name=name,
                        stock_level=stock_level,
                        is_in_stock=is_in_stock,
                        product_code=variant_code,
                        formatted_price=price,
                        product_url=url,
                    ))
            else:
                for variant in variants:
                    name = variant['productName']

                    price = variant['price']['formatted']['withTax']
                    stock_level = variant['currentStock']
                    is_in_stock = stock_level > 0
                    url = f"https://www.thefragranceshop.co.uk/{variant['slug']}"
                    variant_code = variant['stockCode']
                    options.append(
                        ProductOptions(
                            name=name,
                            stock_level=stock_level,
                            is_in_stock=is_in_stock,
                            product_code=variant_code,
                            formatted_price=price,
                            product_url=url,
                        ))

            product_data = ProductData(
                name=product_details['fullName'],
                product_code=product_details['stockCode'],
                options=options,
                product_url=url,
                ean=product_details['barcode'],
                image_url=product_details['image']
            )
            return get_product_embed(product_data), product_data
        except Exception as e:
            Logger.error(f'Attempt {attempt + 1} failed for {url}', e)

    Logger.error(f'Error fetching product data from {url}')
    return discord.Embed(
        title='Error',
        description=f'Failed to fetch product data from {url}.  Please make sure the url is correct',
        color=0xff0000
    ), None
