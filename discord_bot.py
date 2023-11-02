import discord
import os
import asyncio
import threading
import time
import sys
import helpers

from rubidium import DiscordRuby

import json

test_mode = False

intents = discord.Intents.all()
client = discord.Client(intents=intents)

#some globals
discord_queue = asyncio.Queue()
user_records_lock = threading.Lock()
ruby_lock = threading.Lock() #this just keeps track of whether we have a running instance or not
ruby_instance = None

CHANNEL_ID = 1157458682280419380
FILEDUMP_CHANNEL_ID = 1167234435104649256

status_msg_id = None

async def process_queue():
    global discord_queue
    while True:
        if not discord_queue.empty():
            title, msg, file_path, color, is_update, to_delete = await discord_queue.get()
            
            if is_update:
                asyncio.create_task(update_message(title, msg, color, to_delete))
            else: 
                asyncio.create_task(send_message(title, msg, file_path, color))
        else:
            await asyncio.sleep(1)  # wait for 1 second if queue is empty

async def update_message(title, msg, color=discord.Color.blue(), to_delete=False):
    global CHANNEL_ID
    channel = client.get_channel(CHANNEL_ID)
    global status_msg_id
    
    if to_delete:
        await status_msg_id.delete()
        return
    
    new_embed = discord.Embed(title=f"{title}", description=msg, color=color)
    
    if status_msg_id == None:
        status_msg = await channel.send(embed=new_embed)
        status_msg_id = status_msg.id
    else:
        status_msg = await channel.fetch_message(status_msg_id)
        await status_msg.edit(embed=new_embed)
        
    return

async def send_message(title, msg, file_path=None, color=discord.Color.yellow()):
    global CHANNEL_ID
    channel = client.get_channel(CHANNEL_ID)

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
        #send this to the filedump channel as well
        file_channel = client.get_channel(FILEDUMP_CHANNEL_ID)
        
        file = discord.File(file_path)
        await channel.send(file=file)
        await file_channel.send(file=file)
        
    return


def check_legitimate_question(question: str):
    '''
    @params:
        question: str
    
    @returns:
        a boolean of True if the qn is legit, False if not
    '''
    #uses the same system init as ruby
    system_init = f"""
    You are Rubidium. You are a world-class Geopoltical Analyst, who is extremely good at breaking down and planning comprehensive approaches to tough and complex analysis questions and research areas. You follow the concepts of Net Assessment, and you are the best in the world at Net Assessment.
    
    Here is a reference to what Net Assessment is: Net Assessment is a global, strategic evaluation framework that offers extensive value in geopolitical, military, technological, and economic analysis. Originally developed by the Office of Net Assessment in 1973 in the United States Department Defense, it has evolved into an invaluable tool with global relevance. 

    By undertaking a nuanced and opinion-free comparative analysis of historical, technological, cultural, economic, political, and security factors among nation-states, Net Assessment contributes to a comprehensive and sophisticated understanding of geopolitical mechanisms. It thrives on presenting informed explorations of potential obstacles and opportunities to facilitate decision-making that can withstand unexpected turns.

    As a predictive model, it observes and studies current trends, competitor behaviors, potential risks, and forecasts scenerios extending up to several decades in the future. This in-depth review forms the cornerstone of strategic foresight essential for fostering resilient, sustainable policy-making and strategic direction.

    Net Assessment serves as an instrumental tool for analyzing the intentions of parties in conflict situations, and forms the foundation for strategy and policy considerations in these contexts. Applying the intrinsic art of 'what-if' analysis, it presents leaders with a language and rationale to win over constituents in negotiations, policy-making processes, and strategic implementation.

    It generates myriad resources, from in-depth, detail-oriented assessments to practical memos for strategic discussions. Regardless of their origins in classified domains, these resources can be adapted to cater to wider geopolitical debates, outlining crucial intelligence for decision-makers worldwide.

    In terms of historical weight, Net Assessment has proven instrumental in transforming policy and strategic orientations, and in devising new strategic paradigms, testament to its far-reaching impact on global strategic discourse. Thus, Net Assessment is integral to global geopolitical paradigms, long-term safety considerations, and strategic direction, marked by its comprehensive, versatile, opinion-free, and predictive essence.
    """
    
    prompt = f"Your goal here is to determine whether or not the question being asked is a legitimate Net Assessment question or not. You have been given an understanding of what Net Assessment questions are, so you should do your best to infer what makes Net Assessment questions valid. If the input seems malformed, or the question is not a legitimate Net Assessment question, please give a short and succint explanaton of why. If the question is legitimate, please type yes. You MUST strictly only reply yes or with the explanation of why this question is not legitimate. Your output will be parsed for an algorithm to act on, so you must ensure that your output is only the raw text of yes or the explanation, without any quotes. You can find the question below.\n\n{question}"
    
    res = helpers.call_gpt_single(system_init, prompt, function_name="NA qn legit check")
    
    res_lower = res.lower()
    
    return res_lower == "yes", res

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
    global discord_queue
    
    #we make a check on whether or not the question is legitimate before we proceed. this is done in the thread so we can handle checking any number of questions
    is_legit, res = check_legitimate_question(task)
    
    if not is_legit: #send a message telling the user that their question was invalid
        message_obj = ("INVALID QUESTION", f"your question was deemed invalid. Please find the explanation below:\n\n{res}", None, discord.Color.red()) #TODO:
        discord_queue.put_nowait(message_obj)
        return
    
    #update the user instance with the question that they are asking TODO:

    if ruby_instance == None:
        ruby_instance = DiscordRuby(task, priority_level, user_id, user_records_lock, discord_queue)
        ruby_instance.start()
    else:
        #add it to the task queue
        ruby_instance.add_task(task, priority_level, user_id)
    
    ruby_instance = None
    print(f"closing Rubidium Instance. No tasks left.")
    
#start our discord bot
def main():
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
        
        #perform some updates based on whether or not we find the user in our records before or not
        with user_records_lock:
            user_records = None
            with open("user_records/user_records.json", "r") as f:
                user_records = json.load(f)
            
            if str(message.author.id) not in user_records:
                user_records[str(message.author.id)] = {
                    'nickname': message.author.display_name,
                    'question_reportpaths': [] #this contains a list of tuples, which are (question, reportpath)
                }
        
        priority_level = 3
        
        if message.author.display_name == "iridescent":
            priority_level = 1
        else:
            for role in message.author.roles:
                if role.name == "admin":
                    priority_level = 2
                    break
        
        
            
        threading.Thread(target=rubidium_helper, args=(str(message.author.id), priority_level, message.content)).start()
        
    client.run(os.getenv("RUBIDIUM_DISCORD_TOKEN"), reconnect=True)
   
if __name__ == '__main__':
    main()