import random
import discord
import pytz
import aiohttp
import json

from datetime import datetime
from typing import Tuple, Dict, List

from DatabaseManager import DatabaseManager
from Logger import Logger
from bs4 import BeautifulSoup
from models import ProductData, ProductOptions
from ProxyManager import ProxyManager

WINDOWS_USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 OPR/108.0.0.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Vivaldi/6.5.3206.63'
]

headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'accept-language': 'en-US,en;q=0.7',
    'cache-control': 'max-age=0',
    'priority': 'u=0, i',
    'sec-ch-ua': '"Chromium";v="130", "Brave";v="130", "Not?A_Brand";v="99"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-user': '?1',
    'sec-gpc': '1',
    'upgrade-insecure-requests': '1',
    'user-agent': random.choice(WINDOWS_USER_AGENTS),
}
db = DatabaseManager()


def get_current_time():
    uk_tz = pytz.timezone('Europe/London')
    return datetime.now(uk_tz).strftime('%d %B %Y, %I:%M:%S %p %Z')


def get_product_embed(product_data: ProductData) -> discord.Embed:
    embed = discord.Embed(title=product_data.name, url=product_data.product_url, color=0x00ff00)

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
            value=f"{option.stock_level} - {option.stock_status}",
            inline=True
        )
        embed.add_field(
            name='EAN',
            value=option.ean,
            inline=True
        )
        embed.add_field(
            name='\u200b',
            value='\u200b',
            inline=False
        )

    embed.set_footer(text=f"🕒 Time: {get_current_time()} (UK)")
    return embed


def get_single_variant_product(details: Dict) -> List[ProductOptions]:
    variant_ean = details['ean']
    product_name = details['name']

    options = details['baseOptions'][0]['options']
    selected = details['baseOptions'][0]['selected']

    default_stock_level = selected['stock']['stockLevel']
    default_stock_status = selected['stock']['stockLevelStatus']

    default_formatted_price = selected['priceData']['formattedValue']

    # Process each option to extract variant information
    options_data = []
    for option in options:
        try:
            variant_name = f"{product_name} - {option['variantOptionQualifiers'][0]['value']}"
        except (KeyError, IndexError):
            variant_name = product_name

        try:
            stock_level = option['stock']['stockLevel']
            stock_status = option['stock']['stockLevelStatus']
        except KeyError:
            stock_level = default_stock_level
            stock_status = default_stock_status

        try:
            formatted_price = option['priceData']['formattedValue']
        except KeyError:
            formatted_price = default_formatted_price

        options_data.append(
            ProductOptions(
                name=variant_name,
                stock_level=stock_level,
                is_in_stock=stock_status != 'outOfStock',
                stock_status=stock_status,
                product_code=option['code'],
                formatted_price=formatted_price,
                product_url=f"https://www.superdrug.com{option['url']}",
                ean=variant_ean
            )
        )
    return options_data


async def fetch_product_data(url: str, max_retries=5) -> Tuple[discord.Embed, ProductData | None]:
    if not url.startswith('https://www.superdrug.com/'):
        raise ValueError(
            "Invalid URL. Must be a valid Superdrug product URL. Eg: https://www.superdrug.com/versace/bright-crystal-50ml/p/337931"
        )

    proxy_manager = ProxyManager()
    await proxy_manager.initialize()

    for attempt in range(max_retries):
        try:
            random_proxy = await proxy_manager.get_proxy()
            Logger.info(f'Attempt {attempt + 1}: Fetching product data from {url} using proxy {random_proxy}')

            conn = aiohttp.TCPConnector(ssl=True)
            async with aiohttp.ClientSession(connector=conn) as session:
                async with session.get(
                        url,
                        headers=headers,
                        cookies={},
                        proxy=random_proxy['http'],
                        timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        raise Exception(f'HTTP error {response.status}')

                    content = await response.text()

            # Parse the page content
            soup = BeautifulSoup(content, 'html.parser')

            # Locate the script tag with the product data
            script_tag = soup.find(id='spartacus-app-state')
            if not script_tag:
                raise Exception('Product data not found in the page')

            # Process the script content as JSON
            try:
                cleaned_content = script_tag.string.replace('&q;', '"').replace('&l;', '<').replace('&g;', '>')
                data = json.loads(cleaned_content)['cx-state']['product']['details']['entities']
            except json.JSONDecodeError:
                raise Exception('Failed to parse product JSON data')

            product_code = url.split('/')[-1]
            details = data[product_code]['details']['value']
            product_name = details['name']

            options = details['variantMatrix']

            options_data = []
            if len(options) == 0:
                options_data = get_single_variant_product(details)
            else:
                # Process each option to extract variant information
                for option in options:
                    try:
                        variant_name = f"{product_name} - {option['variantValueCategory']['name']}"
                    except (KeyError, IndexError):
                        variant_name = product_name

                    variant_option = option['variantOption']
                    variant_stock_level = variant_option['stock']['stockLevel']
                    variant_stock_status = variant_option['stock']['stockLevelStatus']
                    variant_ean = variant_option['ean']
                    variant_code = variant_option['code']
                    variant_formatted_price = variant_option['priceData']['formattedValue']
                    variant_url = f"https://www.superdrug.com/{variant_option['url']}"

                    options_data.append(
                        ProductOptions(
                            name=variant_name,
                            stock_level=variant_stock_level,
                            is_in_stock=variant_stock_status != 'outOfStock',
                            stock_status=variant_stock_status,
                            product_code=variant_code,
                            formatted_price=variant_formatted_price,
                            product_url=variant_url,
                            ean=variant_ean
                        )
                    )

            product_data = ProductData(
                name=product_name,
                product_code=product_code,
                options=options_data,
                product_url=url
            )
            db.add_or_update_proxy(random_proxy)
            Logger.info(f'Successfully fetched product data from {url}', product_data.to_dict())
            return get_product_embed(product_data), product_data
        except Exception as e:
            Logger.error(f'Error fetching product data from {url}', e)
            continue

    Logger.error(f'Error fetching product data from {url}')
    return discord.Embed(
        title='Error',
        description=f'Failed to fetch product data from {url}.  Please make sure the url is correct',
        color=0xff0000
    ), None
