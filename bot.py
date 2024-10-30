import discord
from discord import app_commands
import subprocess
import time
from typing import Optional

# Bot configuration
TOKEN = "MTMwMDU3MjYwMzU4MDI4NDk3OA.GrQOcs.PVejA7vpvgctBiLe9r-x2_E5QXkLuMQIoT6AAs"
GUILD_ID = 1295867276582457354

class MinecraftServerBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

client = MinecraftServerBot()

# Helper Functions
async def wait_for_server_start(interaction: discord.Interaction) -> bool:
    """Wait for Minecraft server to fully start"""
    await interaction.edit_original_response(
        content="⏳ Starting Minecraft server...\n→ This may take a few moments"
    )
    
    max_attempts = 60
    for attempt in range(max_attempts):
        try:
            cmd = "tmux capture-pane -pt minecraft"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if "Done" in result.stdout and "For help" in result.stdout:
                await interaction.edit_original_response(
                    content="✅ Minecraft server started successfully!\n→ Server is ready to play"
                )
                return True
                
        except subprocess.CalledProcessError as e:
            print(f"Error capturing tmux output: {e}")
            
        time.sleep(1)
        if attempt % 5 == 0:
            await interaction.edit_original_response(
                content=f"⏳ Starting Minecraft server...\n→ Still waiting... ({attempt//5}/6)"
            )
    
    await interaction.edit_original_response(
        content="⚠️ Server start timed out\n→ Please check server logs or try again"
    )
    return False

async def is_server_running() -> bool:
    """Check if the server is running"""
    try:
        cmd = "tmux capture-pane -pt minecraft"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return "Done" in result.stdout and "For help" in result.stdout
    except:
        return False

# Event Handlers
@client.event
async def on_ready():
    print(f'Bot connected as {client.user}')
    print('Use /help to see available commands')

# Server Management Commands
@client.tree.command(
    name="start",
    description="Start the Minecraft server",
    guild=discord.Object(id=GUILD_ID)
)
async def start_server(interaction: discord.Interaction):
    await interaction.response.defer()
    
    check_session_cmd = "tmux has-session -t minecraft 2>/dev/null"
    session_exists = subprocess.call(check_session_cmd, shell=True) == 0
    
    if session_exists:
        await interaction.edit_original_response(
            content="⚡ Found existing Minecraft session\n→ Attempting to start server..."
        )
        try:
            subprocess.check_call("tmux send-keys -t minecraft '1' ENTER", shell=True)
            await wait_for_server_start(interaction)
        except subprocess.CalledProcessError as e:
            await interaction.edit_original_response(
                content=f"❌ Failed to start server\n→ Error: {e}"
            )
        return

    try:
        await interaction.edit_original_response(
            content="🔧 Creating new server session..."
        )
        subprocess.check_call(
            "tmux new-session -d -s minecraft 'python3 server.py'", 
            shell=True
        )
        time.sleep(2)
        
        subprocess.check_call("tmux send-keys -t minecraft '1' ENTER", shell=True)
        if await wait_for_server_start(interaction):
            await interaction.followup.send(
                "📝 **Server Information**\n"
                "→ Use `/status` to check server status\n"
                "→ Use `/refresh` every hour to prevent timeout\n"
                "→ Use `/stop` when finished playing"
            )
    except subprocess.CalledProcessError as e:
        await interaction.edit_original_response(
            content=f"❌ Failed to start server\n→ Error: {e}"
        )

@client.tree.command(
    name="stop",
    description="Stop the Minecraft server",
    guild=discord.Object(id=GUILD_ID)
)
async def stop_server(interaction: discord.Interaction):
    await interaction.response.defer()
    
    if not await is_server_running():
        await interaction.edit_original_response(
            content="❌ Server is not running\n→ Use `/start` to start the server"
        )
        return

    try:
        await interaction.edit_original_response(
            content="🛑 Stopping server...\n→ Saving world data"
        )
        subprocess.check_call("tmux send-keys -t minecraft 'stop' ENTER", shell=True)
        time.sleep(2)
        subprocess.check_call("tmux send-keys -t minecraft ENTER", shell=True)
        time.sleep(1)
        subprocess.check_call("tmux send-keys -t minecraft 'N' ENTER", shell=True)
        await interaction.edit_original_response(
            content="💤 Server stopped successfully\n→ World data has been saved"
        )
    except subprocess.CalledProcessError as e:
        await interaction.edit_original_response(
            content=f"❌ Failed to stop server\n→ Error: {e}"
        )

@client.tree.command(
    name="restart",
    description="Restart the Minecraft server",
    guild=discord.Object(id=GUILD_ID)
)
async def restart_server(interaction: discord.Interaction):
    await interaction.response.defer()
    
    if not await is_server_running():
        await interaction.edit_original_response(
            content="❌ Server is not running\n→ Use `/start` to start the server"
        )
        return

    try:
        await interaction.edit_original_response(
            content="🔄 Restarting server...\n→ This may take a moment"
        )
        subprocess.check_call("tmux send-keys -t minecraft 'restart' ENTER", shell=True)
        time.sleep(2)
        subprocess.check_call("tmux send-keys -t minecraft ENTER", shell=True)
        time.sleep(1)
        subprocess.check_call("tmux send-keys -t minecraft 'N' ENTER", shell=True)
        time.sleep(1)
        subprocess.check_call("tmux send-keys -t minecraft '1' ENTER", shell=True)
        
        if await wait_for_server_start(interaction):
            await interaction.followup.send(
                "🎮 **Server Ready**\n"
                "→ All players can rejoin now\n"
                "→ Remember to use `/refresh` every hour"
            )
    except subprocess.CalledProcessError as e:
        await interaction.edit_original_response(
            content=f"❌ Failed to restart server\n→ Error: {e}"
        )

@client.tree.command(
    name="refresh",
    description="Refresh the server to prevent timeout",
    guild=discord.Object(id=GUILD_ID)
)
async def refresh_server(interaction: discord.Interaction):
    await interaction.response.defer()
    
    if not await is_server_running():
        await interaction.edit_original_response(
            content="❌ Server is not running\n→ Use `/start` to start the server"
        )
        return
        
    try:
        await interaction.edit_original_response(
            content="🔄 Refreshing server..."
        )
        subprocess.check_call(
            "tmux send-keys -t minecraft 'say Server Refreshed - Timer Reset' ENTER", 
            shell=True
        )
        await interaction.edit_original_response(
            content="✨ Server refreshed successfully!\n"
                   "→ Codespace timeout has been reset\n"
                   "→ Remember to refresh again in 1 hour"
        )
    except subprocess.CalledProcessError as e:
        await interaction.edit_original_response(
            content=f"❌ Failed to refresh server\n→ Error: {e}"
        )

@client.tree.command(
    name="status",
    description="Check the current server status",
    guild=discord.Object(id=GUILD_ID)
)
async def check_status(interaction: discord.Interaction):
    await interaction.response.defer()
    
    try:
        if await is_server_running():
            await interaction.edit_original_response(
                content="✅ **Server Status: Online**\n"
                       "→ Server is running normally\n"
                       "→ Use `/refresh` every hour to prevent timeout\n"
                       "→ Use `/stop` when finished playing"
            )
        else:
            await interaction.edit_original_response(
                content="⚠️ **Server Status: Offline**\n"
                       "→ Server is not running\n"
                       "→ Use `/start` to start the server"
            )
    except subprocess.CalledProcessError:
        await interaction.edit_original_response(
            content="❌ Failed to check server status\n→ There might be an internal error"
        )

@client.tree.command(
    name="help",
    description="Show all available commands and their usage",
    guild=discord.Object(id=GUILD_ID)
)
async def help_command(interaction: discord.Interaction):
    help_text = """
🎮 **Minecraft Server Management Commands**

`/start` - Start the Minecraft server
`/stop` - Stop the server and save world data
`/restart` - Restart the server (useful if having issues)
`/refresh` - Reset the timeout timer (use every hour)
`/status` - Check if the server is running
`/help` - Show this help message

⚠️ **Important Notes**
• Server will timeout after 1 hour of inactivity
• Use `/refresh` regularly to prevent timeout
• Always use `/stop` when finished playing
"""
    await interaction.response.send_message(help_text)

# Run the bot
if __name__ == "__main__":
    client.run(TOKEN)