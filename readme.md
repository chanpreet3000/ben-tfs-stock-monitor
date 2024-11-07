# Superdrug Stock Watch Discord Bot

A Discord bot that monitors Superdrug product availability and sends notifications when products come back in stock. The bot automatically checks product stock at regular intervals and notifies users in designated Discord channels.

## Features

- Automated stock monitoring for Superdrug products
- Customizable notification channels
- Easy-to-use slash commands
- Regular automatic stock checks
- Support for multiple products and notification channels

## Discord Commands

### Product Management
- `/sd-add-product <url>` - Start monitoring a Superdrug product URL for stock availability
- `/sd-remove-product <url>` - Stop monitoring a specific product
- `/sd-list-products` - View all currently monitored product URLs
- `/sd-check-stock <url>` - Manually check the current stock status of a product

### Channel Management (Admin Only)
- `/sd-add-channel <channel>` - Add a Discord channel for stock notifications
- `/sd-remove-channel <channel>` - Remove a Discord channel from notifications
- `/sd-list-channels` - View all channels configured for notifications

## How It Works

The bot performs the following functions:

1. **Stock Monitoring**: Regularly checks the stock status of watched products
2. **Notifications**: Sends alerts to configured Discord channels when products become available
3. **Channel Management**: Allows administrators to control where notifications are sent
4. **Product Management**: Provides commands to add/remove products from the watch list

When a product comes back in stock, the bot automatically sends a notification to all configured Discord channels, including product details and the purchase link.