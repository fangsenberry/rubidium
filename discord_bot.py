import discord
import os
import asyncio
import threading
import time
import sys

from rubidium import DiscordRuby

import json

test_mode = False

intents = discord.Intents.all()
client = discord.Client(intents=intents)

#some globals
discord_queue = asyncio.Queue()
user_records = {}
user_records_lock = threading.Lock()

ruby_instance = None

async def process_queue():
    global discord_queue
    while True:
        if not discord_queue.empty():
            channel_id, title, msg, file_path, color = await discord_queue.get()
            asyncio.create_task(send_message(channel_id, title, msg, file_path, color))
        else:
            await asyncio.sleep(1)  # wait for 1 second if queue is empty

async def send_message(channel_id, title, msg, file_path=None, color=discord.Color.yellow()):
    channel = client.get_channel(channel_id)

    if (test_mode): channel = client.get_channel(1133431438172241960) #this is the "#carbon-test" channel id

    if len(msg) < 4096:
        embed = discord.Embed(title=f"{title}", description=msg, color=color)
        await channel.send(embed=embed)
    else:
        #too long, split message
        chunks = [msg[i:i+4096] for i in range(0, len(msg), 4096)]
        for i, chunk in enumerate(chunks):
            embed = discord.Embed(title=f"{title} Part {i}", description=chunk, color=color)
            await channel.send(embed=embed)
            print(f"sent {i}-th chunk")

    if file_path != None:
        file = discord.File(file_path)
        await channel.send(file=file)
        os.remove(file_path)

'''
Target function for init the thread.
'''
def rubidium_helper(user_id: str, priority_level: int, task: str) -> None:
    '''
    updating the user records is here as well
    '''
    
    global user_records
    global user_records_lock
    global ruby_instance
    
    #update the user instance with the question that they are asking

    if ruby_instance == None:
        ruby_instance = DiscordRuby(first_task=task, first_priority=priority_level) #TODO inistialize it properly
        
    else:
        #add it to the task queue
        ruby_instance.add_task(task, priority_level)
    
    ruby_instance = None
    print(f"closing Rubidium Instance. No tasks left.")
    
#start our discord bot
def main():

    global student_records
    with records_lock:
        with open("students/student_records.json", "r") as f:
            student_records = json.load(f)

    #parse potential arguments that we ran it with [right now this code doesnt do shit]
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print("Running in test mode")
        global test_mode
        test_mode = True
        channel_id = 1133431438172241960 #this is the "#carbon-test" channel

    @client.event
    async def on_ready():
        global channel
        print(f"We have logged in as {client.user}")
        client.loop.create_task(process_queue())
        await client.change_presence(activity=discord.Game(name="with your mind"))
        # channel = client.get_channel(channel_id)
        # await channel.send("Hello! I am Carbon, your friendly AI teacher.\n\nI am here to help you learn all the material from the Net Assessment Textbook: 'Navigating Power Dynamics: A Comprehensive Guide to Net Assessment'\n\nPlease feel free to ask me any questions you have!")

    @client.event
    async def on_message(message):
        # early returns to eliminate the stuff we don't want
        if message.channel.name != "rubidium-admin": #for now we restrict to only the admin channel
            return

        if message.author == client.user: #don't respond to ourselves (the bot)
            return

        if message.content == ('!clear') and message.author.display_name == "iridescent": #only me gets to clear the channel
            # Purge all messages in the channel
            await message.channel.purge()
            return
        
        priority_level = 3
        
        if message.author.display_name == "iridescent":
            priority_level = 1
        else:
            for role in message.author.roles:
                if role.name == "admin":
                    priority_level = 2
                    break
            
        #TODO: implement a check to see if the question is legitimate or not before we continue. else we just return. this should be done before it gets added to the task queue so they get a more immediate response.
            
        threading.Thread(target=rubidium_helper, args=(message.author.id, priority_level, message.content)).start()
   
if __name__ == '__main__':
    main()