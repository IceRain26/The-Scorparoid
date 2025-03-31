import asyncio
import discord
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
from twitchAPI.twitch import Twitch
from googleapiclient.discovery import build
from datetime import datetime

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

STREAMER_TWITCH = "scorpius_ent"
DISCORD_CHANNEL_ID = 1309505816704974868


YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

is_live_twitch = False
is_live_youtube = False


class StreamAlert(commands.Cog):
    def __init__(self, bot, twitch):
        self.bot = bot
        self.twitch = twitch
        self.last_notification_date = None
        self.youtube_channel_name = None
        self.check_stream.start()

    async def fetch_youtube_channel_name(self):
        """Fetch the YouTube channel name from the API."""
        try:
            request = youtube.channels().list(part="snippet", id=YOUTUBE_CHANNEL_ID)
            response = request.execute()

            if response.get("items"):
                self.youtube_channel_name = response["items"][0]["snippet"]["title"]
            else:
                self.youtube_channel_name = "Unknown"
        except Exception as e:
            print(f"Error fetching YouTube channel name: {str(e)}")
            self.youtube_channel_name = "Unknown"

    @tasks.loop(minutes=1)
    async def check_stream(self):
        """Check if the Twitch or YouTube stream is live and send one embed message."""
        global is_live_twitch, is_live_youtube

        try:

            today = datetime.now().date()

            if self.last_notification_date == today:
                print("Already sent a notification today.")
                return

            if not self.youtube_channel_name:
                await self.fetch_youtube_channel_name()

            twitch_streams = [stream async for stream in self.twitch.get_streams(user_login=STREAMER_TWITCH)]
            currently_live_twitch = bool(twitch_streams)

            currently_live_youtube = False
            youtube_thumbnail = None
            youtube_title = None
            youtube_url = f"https://www.youtube.com/channel/{YOUTUBE_CHANNEL_ID}"

            youtube_request = youtube.search().list(
                part="snippet",
                channelId=YOUTUBE_CHANNEL_ID,
                eventType="live",
                type="video"
            )

            if currently_live_twitch:
                youtube_response = youtube_request.execute()
                youtube_videos = youtube_response.get("items", [])
                currently_live_youtube = bool(youtube_videos)

                if currently_live_youtube:
                    youtube_data = youtube_videos[0]
                    youtube_thumbnail = youtube_data["snippet"]["thumbnails"]["high"]["url"]
                    youtube_title = youtube_data["snippet"]["title"]
                    youtube_url = f"https://www.youtube.com/watch?v={youtube_data['id']['videoId']}"

            
            if (currently_live_twitch and not is_live_twitch) or (currently_live_youtube and not is_live_youtube):
                twitch_thumbnail = None
                twitch_title = None
                twitch_url = f"https://twitch.tv/{STREAMER_TWITCH}"

                if currently_live_twitch:
                    twitch_data = twitch_streams[0]
                    twitch_thumbnail = twitch_data.thumbnail_url.replace("{width}", "320").replace("{height}", "180")
                    twitch_title = twitch_data.title

                channel = self.bot.get_channel(DISCORD_CHANNEL_ID)
                if channel:
                    await channel.send("** Hey @everyone!**")
                    embed = discord.Embed(
                        title="** 🚀 LIVE NOW!🚀 **",
                        description="🔥 Scorpius is streaming! Join the hype and catch all the action! 🎮✨",
                        color=0x6441A4
                    )

                    if twitch_title:
                        embed.add_field(name="🟣 Twitch Stream:", value=f"[▶️ {twitch_title}]({twitch_url})", inline=False)
                    if youtube_title:
                        embed.add_field(name="🔴 YouTube Stream:", value=f"[▶️ {youtube_title}]({youtube_url})", inline=False)

                    if twitch_thumbnail:
                        embed.set_thumbnail(url=twitch_thumbnail)
                    elif youtube_thumbnail:
                        embed.set_thumbnail(url=youtube_thumbnail)


                    await channel.send(embed=embed)

                self.last_notification_date = today
                print("Notification sent. Skipping further checks for today.")

            is_live_twitch = currently_live_twitch
            is_live_youtube = currently_live_youtube

        except Exception as e:
            print(f"Error checking stream: {str(e)}")

    @check_stream.before_loop
    async def before_check_stream(self):
        await self.bot.wait_until_ready()


@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!")
    print(f"Monitoring {STREAMER_TWITCH}'s Twitch stream and {YOUTUBE_CHANNEL_ID}'s YouTube stream")


async def main():
    twitch = await Twitch(os.getenv("TWITCH_CLIENT_ID"), os.getenv("TWITCH_CLIENT_SECRET"))
    await twitch.authenticate_app([])
    await bot.add_cog(StreamAlert(bot, twitch))
    await bot.start(os.getenv("DISCORD_TOKEN"))


asyncio.run(main())