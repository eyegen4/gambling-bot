import discord
from discord.ext import commands
import json
import random
import os
import asyncio
from datetime import datetime, timedelta
from flask import Flask
import threading

# Flask app for Render's port requirement
app = Flask(__name__)

@app.route('/')
def health_check():
    return 'Biscoff\'s Dice is running!', 200

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# File for storing data
DATA_FILE = 'user_data.json'

# Load data
def load_data():
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Save data
def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)

# Get user data
def get_user_data(user_id):
    data = load_data()
    if str(user_id) not in data:
        data[str(user_id)] = {'balance': 100, 'last_daily': None, 'last_beg': None, 'last_roll': None}
        save_data(data)
    return data[str(user_id)]

# Update user data
def update_user_data(user_id, updates):
    data = load_data()
    data[str(user_id)].update(updates)
    save_data(data)

@bot.event
async def on_ready():
    print(f'Biscoff\'s Dice is online!')

@bot.command(name='tutorial')
async def tutorial(ctx):
    await ctx.send(
        f'{ctx.author.mention}, welcome to Biscoff\'s Dice!\n'
        '🎲 **How to Play**:\n'
        '- `!balance`: Check your Coins.\n'
        '- `!daily`: Get 50 Coins every 24 hours.\n'
        '- `!beg`: Beg for 5-15 Coins (1-min cooldown).\n'
        '- `!roll <amount>`: Bet Coins, roll a dice (1-6). Biscoff rolls for a moment, then: 4-6 wins 1.5x your bet, 1-3 loses (30-sec cooldown).\n'
        '- `!leaderboard`: See top 5 richest players.\n'
        'Start with 100 Coins. Feel the thrill and roll the dice!'
    )

@bot.command(name='balance')
async def balance(ctx):
    user_data = get_user_data(ctx.author.id)
    await ctx.send(f'{ctx.author.mention}, you have **{user_data["balance"]} Coins** in Biscoff\'s Dice!')

@bot.command(name='daily')
async def daily(ctx):
    user_data = get_user_data(ctx.author.id)
    now = datetime.now()
    if user_data['last_daily']:
        last = datetime.fromisoformat(user_data['last_daily'])
        if now - last < timedelta(hours=24):
            await ctx.send(f'{ctx.author.mention}, come back in {24 - (now - last).seconds // 3600} hours for Biscoff\'s daily reward!')
            return
    user_data['balance'] += 50
    user_data['last_daily'] = now.isoformat()
    update_user_data(ctx.author.id, {'balance': user_data['balance'], 'last_daily': user_data['last_daily']})
    await ctx.send(f'{ctx.author.mention}, claimed **50 Coins** from Biscoff\'s Dice! Total: {user_data["balance"]}')

@bot.command(name='beg')
async def beg(ctx):
    user_data = get_user_data(ctx.author.id)
    now = datetime.now()
    if user_data['last_beg']:
        last = datetime.fromisoformat(user_data['last_beg'])
        if now - last < timedelta(minutes=1):
            await ctx.send(f'{ctx.author.mention}, wait {(60 - (now - last).seconds) // 60 + 1} minutes to beg Biscoff again.')
            return
    coins = random.randint(5, 15)
    user_data['balance'] += coins
    user_data['last_beg'] = now.isoformat()
    update_user_data(ctx.author.id, {'balance': user_data['balance'], 'last_beg': user_data['last_beg']})
    await ctx.send(f'{ctx.author.mention}, Biscoff tossed you **{coins} Coins**! Total: {user_data["balance"]}')

@bot.command(name='roll')
async def roll(ctx, bet: int):
    user_data = get_user_data(ctx.author.id)
    now = datetime.now()
    if user_data['last_roll']:
        last = datetime.fromisoformat(user_data['last_roll'])
        if now - last < timedelta(seconds=30):
            remaining = 30 - (now - last).seconds
            await ctx.send(f'{ctx.author.mention}, slow down! Wait {remaining} seconds to roll Biscoff\'s Dice again.')
            return
    if bet <= 0:
        await ctx.send(f'{ctx.author.mention}, bet something real for Biscoff\'s Dice.')
        return
    if user_data['balance'] < bet:
        await ctx.send(f'{ctx.author.mention}, you need {bet - user_data["balance"]} more Coins for Biscoff\'s Dice.')
        return
    await ctx.send(f'{ctx.author.mention}, Biscoff is rolling the dice... 🎲')
    await asyncio.sleep(2)
    dice = random.randint(1, 6)
    if dice <= 3:
        user_data['balance'] -= bet
        update_user_data(ctx.author.id, {'balance': user_data['balance'], 'last_roll': now.isoformat()})
        await ctx.send(f'{ctx.author.mention}, 🎲 Biscoff\'s Dice rolled a {dice}! You lost {bet} Coins. Balance: {user_data["balance"]}')
    else:
        winnings = int(bet * 1.5)
        user_data['balance'] += (winnings - bet)
        update_user_data(ctx.author.id, {'balance': user_data['balance'], 'last_roll': now.isoformat()})
        await ctx.send(f'{ctx.author.mention}, 🎲 Biscoff\'s Dice rolled a {dice}! You won {winnings} Coins! Balance: {user_data["balance"]}')

@bot.command(name='leaderboard')
async def leaderboard(ctx):
    data = load_data()
    sorted_users = sorted(data.items(), key=lambda x: x[1]['balance'], reverse=True)[:5]
    msg = '🏆 **Biscoff\'s Dice Leaderboard (Top 5)** 🏆\n'
    for i, (user_id, user_data) in enumerate(sorted_users, 1):
        user = await bot.fetch_user(int(user_id))
        msg += f'{i}. {user.name}: {user_data["balance"]} Coins\n'
    await ctx.send(msg if sorted_users else f'{ctx.author.mention}, no players yet! Roll with Biscoff\'s Dice!')

# Run Flask and Discord bot concurrently
def run_flask():
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    bot.run(os.getenv('DISCORD_TOKEN'))
