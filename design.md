# main.py

Initializes an instance of Rubidium locally with tkinter

# discord_bot.py
Initializes the Rubidium discord bot instance.

We will be using a global queue for this since at this point (October 2023) we are doing this for a small amount of people. This also makes sure that we don't need to synchronise mutex and semaphores for Rubidium instances that cannot see each other. There will only be one Rubidium instance running at any time.

There will also be certain roles from the discord bot that we whitelist as having priority in the Rubidium Task queue. The Rubidium class will reflect this, as will this .py file.

# helpers.py
general purpose helpers for rubidium, includes:
- summarisation
- single prompt calling gpt
- entire conversation provided in params calling GPT.

# online_search.py

# research.py
all the research functions that ruby uses. Everything that happens in this file is local to this file. Meaning that if we make plans for how we should search these are plans we are making based on what is being passed in. We are not going to be calling functions outside of this file to make plans for us.

# rubidium.py
contains the Rubidium class that we instantiate to use to answer questions

# temp_output [directory]
This contains a temporary directory that our functions can use to create files and things for use later.

reelevant call notes for na_prep is only used for AC ruby the other one is not implemented. TODO: implement the other one.

right now for the NA prep sections we don't do any discernment between the relevant call notes and the information that we have gatehred. In the first and second layer we do however.