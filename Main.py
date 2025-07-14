from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import os
import schedule
import time
import discord
import asyncio
import threading
from plyer import notification
import logging  # Import logging

PRICE_FILE = "fuel_prices.txt"
NOTIFICATION_TITLE = "Fuel Price Alert"
FUEL_TYPES = {
    "Eurosuper 95": "stationfinder-eurosuper95",
    "Superplus 98": "stationfinder-eurosuper98",
    "Diesel": "stationfinder-diesel"
}
DISCORD_BOT_TOKEN = "MTM2NjIwMTg3MzQ1MDc5OTE0Ng.GyITbd.BaycGKC_wwO1TxGyZ2CRI9Y1aIFygSkCgjszvE"
DISCORD_CHANNEL_ID = 1366204758398079011

client = discord.Client(intents=discord.Intents.default())

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def get_fuel_price(driver, fuel_type, container_id):
    try:
        price_container = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, container_id))
        )
        digit_images = WebDriverWait(price_container, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, 'Digit'))
        )

        price_parts = []
        for img in digit_images:
            src = img.get_attribute('src').split('/')[-1]
            if src == '1.png':
                price_parts.append('1')
            elif src == 'Dot.png':
                price_parts.append('.')
            elif src == '2.png':
                price_parts.append('2')
            elif src == '3.png':
                price_parts.append('3')
            elif src == '4.png':
                price_parts.append('4')
            elif src == '5.png':
                price_parts.append('5')
            elif src == '6.png':
                price_parts.append('6')
            elif src == '7.png':
                price_parts.append('7')
            elif src == '8.png':
                price_parts.append('8')
            elif src == '9.png':
                price_parts.append('9')
            elif src == '0.png':
                price_parts.append('0')
        return fuel_type, "".join(price_parts)
    except Exception as e:
        logging.error(f"Error getting price for {fuel_type}: {e}")
        return fuel_type, None


def get_all_fuel_prices():
    url = "https://www.jansens-vantigchelt.be/"
    prices = {}
    try:
        service = ChromeService(ChromeDriverManager().install())  # Use webdriver_manager
        driver = webdriver.Chrome(service=service)
        driver.get(url)

        for fuel_type, container_id in FUEL_TYPES.items():
            fuel_type, price = get_fuel_price(driver, fuel_type, container_id)
            if price:
                prices[fuel_type] = price

        driver.quit()
        return prices
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        if 'driver' in locals():
            driver.quit()
        return None


def save_prices(prices):
    try:
        with open(PRICE_FILE, "w") as f:
            for fuel_type, price in prices.items():
                f.write(f"{fuel_type}:{price}\n")
        logging.info(f"Prices saved to {PRICE_FILE}")
    except Exception as e:
        logging.error(f"Error saving prices to file: {e}")


def load_previous_prices():
    previous_prices = {}
    if os.path.exists(PRICE_FILE):
        try:
            with open(PRICE_FILE, "r") as f:
                for line in f:
                    fuel_type, price = line.strip().split(":")
                    previous_prices[fuel_type] = price
        except Exception as e:
            logging.error(f"Error reading previous prices from file: {e}")
            return {}
    return previous_prices


async def send_discord_message(channel_id, message):
    channel = client.get_channel(channel_id)
    if channel:
        await channel.send(message)
    else:
        logging.warning(f"Could not find channel with ID: {channel_id}")


def notify_price_changes(old_prices, new_prices):
    messages = []
    all_prices_message = "Current Fuel Prices:\n"
    for fuel_type, new_price in new_prices.items():
        old_price = old_prices.get(fuel_type)
        all_prices_message += f"- {fuel_type}: {new_price} EUR\n"
        if old_price is not None and old_price != new_price:
            change = float(new_price) - float(old_price)
            change_str = f"+{change:.3f}" if change > 0 else f"{change:.3f}"
            messages.append(
                f"{fuel_type} price changed from {old_price} to {new_price} EUR (Change: {change_str} EUR)")
    logging.info(all_prices_message)  # Log current prices

    asyncio.run_coroutine_threadsafe(send_discord_message(DISCORD_CHANNEL_ID, all_prices_message), client.loop)

    if messages:
        full_message = "\n".join(messages)
        logging.info(full_message)  # Log price changes

        asyncio.run_coroutine_threadsafe(send_discord_message(DISCORD_CHANNEL_ID, full_message), client.loop)
    else:
        asyncio.run_coroutine_threadsafe(send_discord_message(DISCORD_CHANNEL_ID, "No price changes found."), client.loop)


def job():
    current_prices = get_all_fuel_prices()
    if current_prices:
        previous_prices = load_previous_prices()
        notify_price_changes(previous_prices, current_prices)
        save_prices(current_prices)
    else:
        logging.warning("Failed to retrieve fuel prices.")


async def run_discord_bot():
    await client.start(DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    import asyncio
    import threading

    discord_thread = threading.Thread(target=asyncio.run, args=(run_discord_bot(),))
    discord_thread.daemon = True
    discord_thread.start()

    schedule.every().day.at("08:00").do(job)
    job()

    while True:
        schedule.run_pending()
        time.sleep(60)