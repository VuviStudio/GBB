import discord
from discord.ext import commands        
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime, timedelta
import json
import asyncio

mongo_uri = "mongodb+srv://vuvi:fcLIF5oab3QDZKa4@cluster0.geafzyy.mongodb.net/?retryWrites=true&w=majority"
mongo_client = MongoClient(mongo_uri, server_api=ServerApi('1'))
db = mongo_client.get_database("OpenGbbvouches")
collection_name = "vouches"
collection = db.get_collection(collection_name)
gban_logs_collection_name = "gban_logs"
gban_logs_collection = db.get_collection(gban_logs_collection_name)

with open('config.json', 'r') as config_file:
    config = json.load(config_file)

prefix = config.get('prefix', '-')
VouchLog_channel_id = config.get('VouchLog_channel_id')
token = config.get('token')
allowed_ids = config.get('gban_allowed_ids')


bot = commands.Bot(command_prefix=prefix, intents=discord.Intents.all())

last_vouch = {}


@bot.event
async def on_ready():
    await bot.change_presence(status=discord.Status.dnd, activity=discord.Activity(type=discord.ActivityType.watching, name="vouches"))

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if isinstance(message.channel, discord.DMChannel):
        embed = discord.Embed(
            title="Message from Vuvi",
            description="Hello! This is a message from Vuvistudio Bot.",
            color=0x000000
        )
        embed.add_field(name="Info", value="Made by vuvi. You can find more info [here](https://discord.gg/Utv9mKcEn2) and more bots and apps [here](https://vuvistudio.mysellix.io/)")
        await message.channel.send(content="**```**", embed=embed)

    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")

@bot.command()
async def vouch(ctx, user_mention: discord.User, rating: int, *, reason: str):
    user = ctx.guild.get_member(user_mention.id)

    if ctx.author.id == user_mention.id:
        await ctx.send("You cannot vouch for yourself!")
        return

    if last_vouch.get(ctx.author.id) and (datetime.now() - last_vouch[ctx.author.id]) < timedelta(hours=1):
        await ctx.send("You can only vouch once per hour!")
        return

    vouch_data = {
        "author_id": ctx.author.id,
        "user_id": user_mention.id,
        "rating": rating,
        "reason": reason
    }
    collection.insert_one(vouch_data)

    last_vouch[ctx.author.id] = datetime.now()

    vouch_message_user = (
        f"You received a vouch from {ctx.author.display_name} in {ctx.guild.name}!\n"
        f"**Author ID:** {ctx.author.id}\n"
        f"**Rating:** {rating}/5\n"
        f"**Reason:** {reason}"
    )
    embed_user = discord.Embed(title="You Received a Vouch!", description=vouch_message_user, color=0x000000)

    vouch_message_channel = (
        f"A vouch for {user_mention.mention} has been stored by {ctx.author.display_name} in {ctx.guild.name}!\n"
        f"**Author ID:** {ctx.author.id}\n"
        f"**User ID:** {user_mention.id}\n"
        f"**Rating:** {rating}/5\n"
        f"**Reason:** {reason}"
    )
    embed_channel = discord.Embed(title="Vouch Stored", description=f"**{vouch_message_channel}**", color=0x000000)


    log_channel = bot.get_channel(VouchLog_channel_id)
    if log_channel:
        await log_channel.send(embed=embed_channel)
    else:
        print("Log channel not found!")

    await ctx.send(embed=embed_channel)

@bot.command()
async def vouches(ctx, user_id: int = None):
    if user_id is None:
        user_id = ctx.author.id

    vouch_count = collection.count_documents({"user_id": user_id})

    embed = discord.Embed(title="User Vouches in Server: " + ctx.guild.name, color=0x000000)

    if vouch_count > 0:
        vouches = collection.find({"user_id": user_id})
        total_rating = sum(vouch["rating"] for vouch in vouches)
        average_rating = total_rating / vouch_count

        user_stars = "".join(["⭐" if i < round(average_rating) else "☆" for i in range(5)])

        embed.add_field(name="User ID", value=f"**```{user_id}```**", inline=False)
        embed.add_field(name="Vouch Count", value=f"**```{vouch_count}```**", inline=False)
        embed.add_field(name="Average Rating", value=f"**```{user_stars}```** ({average_rating:.2f}/5)", inline=False)
        embed.description = f"**```markdown\nThe user with id: {user_id} has received {vouch_count} vouches!\n```**"
    else:
        embed.description = f"**```markdown\nThe user with id: {user_id} has not received any vouches!\n```**"

    await ctx.send(embed=embed)





@bot.command()
async def gban(ctx, user_id: int):
    if ctx.author.id not in allowed_ids:
        await ctx.send("You don't have permission to use this command.")
        return

    try:
        user = await bot.fetch_user(user_id)
    except discord.NotFound:
        await ctx.send("User not found.")
        return

    for guild in bot.guilds:
        try:
            await guild.ban(discord.Object(id=user_id), reason="Global Ban")
        except discord.Forbidden:
            await ctx.send(f"Missing permissions to ban {user.name} in {guild.name}.")

    gban_log = {
        "moderator_id": ctx.author.id,
        "banned_user_id": user_id,
        "timestamp": datetime.utcnow().isoformat(),
        "reason": "Global Ban"
    }
    gban_collection = db.get_collection("global_bans")
    gban_collection.insert_one(gban_log)

    embed = discord.Embed(title="User Globally Banned", color=0x000000)
    embed.add_field(name="Moderator", value=f"**<@{ctx.author.id}>**")
    embed.add_field(name="Banned User", value=f"**<@{user_id}>**")

    log_channel_id = config.get('gban_log_channel_id')
    log_channel = bot.get_channel(log_channel_id)
    if log_channel:
        await log_channel.send(content=f"**Successfully globally banned {user.name}.**", embed=embed)
    else:
        print("Log channel not found!")





@bot.command()
async def gunban(ctx, user_id: int):
    if ctx.author.id not in allowed_ids:
        await ctx.send("You don't have permission to use this command.")
        return

    try:
        user = await bot.fetch_user(user_id)
    except discord.NotFound:
        await ctx.send("User not found.")
        return

    banned_guilds = 0
    for guild in bot.guilds:
        try:
            await asyncio.sleep(2)
            await guild.unban(user, reason="Global Unban")
            banned_guilds += 1
        except discord.Forbidden:
            await ctx.send(f"Missing permissions to unban {user.name} in {guild.name}.")
        except asyncio.TimeoutError:
            await asyncio.sleep(5)

    embed_unban = discord.Embed(title="User Globally Unbanned", color=0x000000)
    embed_unban.add_field(name="Moderator", value=f"**<@{ctx.author.id}>**")
    embed_unban.add_field(name="Unbanned User", value=f"**<@{user_id}>**")
    embed_unban.add_field(name="Unbanned from Guilds", value=f"**```{banned_guilds}```**")
    embed_unban.add_field(name="Reason", value="**```Global Unban```**")

    log_channel_id = config.get('gban_log_channel_id')
    log_channel = bot.get_channel(log_channel_id)
    if log_channel:
        await log_channel.send(content="**User successfully globally unbanned.**", embed=embed_unban)
    else:
        print("Log channel not found!")



@bot.command()
async def svs(ctx):
    guilds_list = "\n".join(f"{guild.name} - {guild.id}" for guild in bot.guilds)
    formatted_text = f"```Guilds:\n{guilds_list}```"
    await ctx.send(formatted_text)

@bot.command()
async def info(ctx, command_name: str = None):
    """Shows information about a specific command or the list of commands."""
    usage = {
        "svs": "No parameters.",
        "gunban": "<user_id>: Unbans a user from all guilds the bot is in.",
        "gban": "<user_id>: Bans a user from all guilds the bot is in.",
        "vouch": "<user_id> <rating: int> <reason>: Vouches for a user in the server.",
        "vouches": "<user_id>: Shows the vouches received by a user.",
        "info": "[command_name]: Shows information about a specific command or the list of commands."
    }

    descriptions = {
        "svs": "Shows a list of guilds the bot is in.",
        "gunban": "Unbans a user from all guilds the bot is in.",
        "gban": "Bans a user from all guilds the bot is in.",
        "vouch": "Vouches for a user in the server.",
        "vouches": "Shows the vouches received by a user.",
        "info": "Shows information about a specific command or the list of commands."
    }

    if command_name:
        command = bot.get_command(command_name)
        if command:
            embed = discord.Embed(title=f"Info for {command_name}", color=0x000000)
            embed.add_field(name="Usage", value=f"**```{usage.get(command_name, 'No usage provided')}```**")
            embed.add_field(name="Description", value=f"**```{descriptions.get(command_name, 'No description provided')}```**")
            await ctx.send(embed=embed)
        else:
            await ctx.send("Command not found.")
    else:
        command_list = [f"{command.name}: {usage.get(command.name, 'No usage provided')}" for command in bot.commands]
        embed = discord.Embed(title="List of Commands", description="**```" + '\n'.join(command_list) + "```**", color=0x000000)
        await ctx.send(embed=embed)


bot.run(token)
