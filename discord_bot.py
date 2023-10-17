import discord
import os
from teachers import BaseTeacher, MilitaryTeacher
import asyncio
import threading
import time
import sys

from carbon import Carbon

import json

test_mode = False

intents = discord.Intents.all()
client = discord.Client(intents=intents)

#some globals
discord_queue = asyncio.Queue()
states = {}
states_lock = threading.Lock()
student_records = {}
records_lock = threading.Lock()

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
def carbon_helper(user_id: str, task: str) -> None:
    #allow this func to have access to our globals
    
    global records_lock
    global states_lock
    global student_records
    global discord_queue
    global states

    new = False
    #this thread gets spawned on message. we need to check if we have an instance running for this user already
    with states_lock:
        if (user_id in states):
            print(f"adding task to existing instance for user: {student_records[user_id]['nickname']}")
            #we already have an instance running, lets add it to the queue
            instance = states[user_id]['instance']
            instance.add_task(task)
            return #early return because we don't want to create a new instance, and dont want to print the message either.
        else:
            #we don't create a new asyncio task because we don't want to block the discord heartbeat
            #the user id needs to be a str bc python is fucky with longs and discord ID is a long
            instance = Carbon(user_id, records_lock, student_records, states_lock, states, task, discord_queue)
            states[user_id] = {'instance':instance, 'status':"processing"}
            new = True

    if new: instance.start()
    print(f"closing Carbon instance for student: {student_records[user_id]['nickname']}")
    
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
        if not message.channel.name.startswith("carbon"): #if its not a carbon channel, we don't care #TODO: change this for more fine control over where the messages are sent. only carbon-r2 for init, then only personal channels for everything else. should still keep this so we don't need to access the student records as much
            return

        if message.author == client.user: #don't respond to ourselves (the bot)
            return

        if message.content == ('!clear') and message.author.display_name == "iridescent": #only me gets to clear the channel
            # Purge all messages in the channel
            await message.channel.purge()
            return

        #we mutex lock all access to the student records file
        global records_lock
        global student_records
        with records_lock:

            #run here so we don't interfere with other students who are trying to initialize
            #we can answer everything from any channel starting with carbon, but only from me, if in test-mode
            if test_mode and message.author.display_name == "iridescent":

                #lets also add the remove student command here so that i don't do it normally not in test mode
                if message.content.startswith("!removestudent"):
                    #remove the student from the student records
                    student_id = message.content.split(" ")[1]
                    if student_id in student_records:
                        del student_records[student_id]
                        with open("students/student_records.json", "w") as f:
                            json.dump(student_records, f)
                        await message.channel.send(f"Student {student_id} removed.")
                    else:
                        await message.channel.send(f"Student {student_id} not found.")

                    return #early return

                threading.Thread(target=carbon_helper, args=(str(message.author.id), message.content)).start()
                return

            if str(message.author.id) in student_records and message.content == "!init":
                #send a message to the user telling them they already initialized
                msg = (f"You have already initialized your student records. You are not allowed to do this")
                embed = discord.Embed(title=f"Student Record Already Initialized for {message.author.display_name}.", description=msg, color=discord.Color.red())
                await message.channel.send(embed=embed)
                return

            if str(message.author.id) not in student_records and message.content != "!init": #the student is not passing an initialization command.
                #send a message to the user telling them to initialize
                msg = (f"Please type !init in the channel starting with \"carbon\" to initialize your student records and start learning with Carbon.")
                embed = discord.Embed(title=f"Student Record Not Initialized for {message.author.display_name} on {time.strftime('%d/%m/%Y %H:%M:%S')}", description=msg, color=discord.Color.red())
                await message.channel.send(embed=embed)
                
                return #early return because its not initialized

            if str(message.author.id) not in student_records and message.content == "!init":

                overwrites = {
                    message.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    message.author: discord.PermissionOverwrite(read_messages=True),
                    discord.utils.get(message.guild.roles, name="admin"): discord.PermissionOverwrite(read_messages=True)
                }

                #place this channel in the NACT-R2 category
                category = discord.utils.get(message.guild.categories, name="NACT-R2")

                #create the channel
                new_channel = await message.guild.create_text_channel(name=f"carbon-r2-{message.author.display_name}", overwrites=overwrites, category=category)

                #create a new student
                student_records[str(message.author.id)] = {
                    "nickname": message.author.display_name,
                    "profile": "I am an aspiring Net Assessor, and am equally interested in the theorectical underpinnings of Net Assessment as well as the practical applications of it.",
                    "history": [],
                    "old_profiles": [],
                    "learning_summaries": [],
                    "channel_id": str(new_channel.id),
                    "progress_reports": []
                }

                #just update it
                with open("students/student_records.json", "w") as f:
                    json.dump(student_records, f)

                #send the welcome message in that channel
                
                msg = (f"Student Records for {message.author.display_name} have been successfully initialized on {time.strftime('%d/%m/%Y %H:%M:%S')}\n\nWelcome to Carbon, your friendly AI teacher.\n\nI am here to help you learn all the material from the Net Assessment Textbook: 'Navigating Power Dynamics: A Comprehensive Guide to Net Assessment'\n\nPlease feel free to ask me any questions you have!")
                embed = discord.Embed(title=f"Successful Student Record and Carbon Initialization for {message.author.display_name} on {time.strftime('%d/%m/%Y %H:%M:%S')}", description=msg, color=discord.Color.green())
                await new_channel.send(embed=embed)

                return #early return because this is their first initialization command, we can create an instance of carbon to handle other requests

            if (str(message.author.id) in student_records and message.channel.id != int(student_records[str(message.author.id)]["channel_id"])):
                return #early return because the student is sending messages not in their own channel
            
            #just update the nickname if they change it
            student_records[str(message.author.id)]["nickname"] = message.author.display_name                
            
            threading.Thread(target=carbon_helper, args=(str(message.author.id), message.content)).start()



            
    
    client.run(os.getenv("CARBON_DISCORD_TOKEN"), reconnect=True)
   
if __name__ == '__main__':
    main()