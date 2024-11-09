import asyncio
import undetected_chromedriver as uc
import discord
import pytz
import json

from fake_useragent import UserAgent
from datetime import datetime
from typing import Tuple
from selenium_stealth import stealth
from dotenv import load_dotenv

from DatabaseManager import DatabaseManager
from Logger import Logger
from models import ProductData, ProductOptions

load_dotenv()

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


async def fetch_product_data(url: str, max_retries: int = 3) -> Tuple[discord.Embed, ProductData | None]:
    for attempt in range(max_retries):
        ua = UserAgent()
        user_agent = ua.random
        chrome_options = uc.ChromeOptions()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("user-agent={}".format(user_agent))
        driver = uc.Chrome(options=chrome_options)
        try:
            stealth(driver,
                    languages=["en-US", "en"],
                    vendor="Google Inc.",
                    platform="Win32",
                    webgl_vendor="Intel Inc.",
                    renderer="Intel Iris OpenGL Engine",
                    fix_hairline=True
                    )

            driver.get(url)
            await asyncio.sleep(5)

            # Find script tag containing stockLevel using JavaScript
            stock_script = driver.execute_script("""
                return Array.from(document.getElementsByTagName('script')).find(
                    script => script.textContent && script.textContent.includes('currentStock')
                ).textContent;
            """)

            if not stock_script:
                raise Exception("Could not find script containing stock data")

            # Clean up the JSON data
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
                    variant_url = f"https://www.thefragranceshop.co.uk/{variant['slug']}"
                    variant_code = variant['stockCode']
                    options.append(
                        ProductOptions(
                            name=name,
                            stock_level=stock_level,
                            is_in_stock=is_in_stock,
                            product_code=variant_code,
                            formatted_price=price,
                            product_url=variant_url,
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
        finally:
            driver.quit()

    Logger.error(f'Error fetching product data from {url}')
    return discord.Embed(
        title='Error',
        description=f'Failed to fetch product data from {url}. Please make sure the url is correct',
        color=0xff0000
    ), None
