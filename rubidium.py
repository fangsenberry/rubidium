import helpers
import research
import netass
import onsearch

import threading
import asyncio
import discord
from discord.ext import commands
import os
import time
import concurrent
from tqdm.auto import tqdm
import numpy as np
import json

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, Inches
from queue import PriorityQueue

class Rubidium():
    '''
    This is the base Rubidium class. The Net Assessment function is a one-pass, non-recursive approach to answering Net Assessment queries.
    
    '''
    def __init__(self):
        self.reports_directory = "generated_reports"

        #gpt prompt stuff
        self.system_init = f"""You are Rubidium. You are a world-class Geopoltical Analyst, who is extremely good at breaking down and planning comprehensive approaches to tough and complex analysis questions and research areas. You follow the concepts of Net Assessment, and you are the best in the world at Net Assessment.
    
        Here is a reference to what Net Assessment is: Net Assessment is a global, strategic evaluation framework that offers extensive value in geopolitical, military, technological, and economic analysis. Originally developed by the Office of Net Assessment in 1973 in the United States Department Defense, it has evolved into an invaluable tool with global relevance. 

        By undertaking a nuanced and opinion-free comparative analysis of historical, technological, cultural, economic, political, and security factors among nation-states, Net Assessment contributes to a comprehensive and sophisticated understanding of geopolitical mechanisms. It thrives on presenting informed explorations of potential obstacles and opportunities to facilitate decision-making that can withstand unexpected turns.

        As a predictive model, it observes and studies current trends, competitor behaviors, potential risks, and forecasts scenerios extending up to several decades in the future. This in-depth review forms the cornerstone of strategic foresight essential for fostering resilient, sustainable policy-making and strategic direction.

        Net Assessment serves as an instrumental tool for analyzing the intentions of parties in conflict situations, and forms the foundation for strategy and policy considerations in these contexts. Applying the intrinsic art of 'what-if' analysis, it presents leaders with a language and rationale to win over constituents in negotiations, policy-making processes, and strategic implementation.

        It generates myriad resources, from in-depth, detail-oriented assessments to practical memos for strategic discussions. Regardless of their origins in classified domains, these resources can be adapted to cater to wider geopolitical debates, outlining crucial intelligence for decision-makers worldwide.

        In terms of historical weight, Net Assessment has proven instrumental in transforming policy and strategic orientations, and in devising new strategic paradigms, testament to its far-reaching impact on global strategic discourse. Thus, Net Assessment is integral to global geopolitical paradigms, long-term safety considerations, and strategic direction, marked by its comprehensive, versatile, opinion-free, and predictive essence."""

    '''
    A one-pass, non-recursive approach to answering Net Assessment queries. Creates a docx file containing the question and answer, and then sends it to the discord queue.

    @params:
        question: a string containing the question to be answered.
    '''

    def get_persona(self, persona_query, top_k=2):
        '''
        Gets the persona for the question.
        '''
        personas = {
                    "finance":"World renowned Economist specialising in the global impacts of financial policy and the banking industry",
                    "military":"Military analyst with a PhD in military strategy and political science",
                    "politics":"Politician with a PhD in political science",
                    "technology":"Chief Technological Officer with a PhD in computer science",
                    "china": "Expert on China and a critical understanding of their policy making measures",
                    "innovation":"Ecosystem and Venture Builder that has accelerated over 100 startups in the past 5 years to series A funding",
                    }

        #compare similarity to text.
        ret_persona = "You are a "
        while (top_k):

            # print(personas)
            max_sim = -np.inf
            max_key = ""

            for pkey, pval in personas.items():
                similarity = helpers.get_similarity(pkey, persona_query)
                # print(similarity, pkey)
                if similarity > max_sim:
                    max_key = pkey
                    max_sim = similarity

            ret_persona += personas[max_key]
            if top_k > 1: ret_persona += " and a "
            print(max_key, "persona chosen with similarity:", max_sim)
            del personas[max_key] #remove the persona we just got
                
            top_k-=1

        #some cleaning up
        ret_persona = ret_persona.strip() + "."
        print("personas: ", ret_persona)
        return ret_persona
        


    def net_assess(self, question):
        chat_history = [] #a local version of history that we use as context for our second projection and cascading calls.
        
        research = self.get_research(question)
        with open("research.txt", "w") as f:
            f.write(research)
        print("done with research")

        persona_query = f"{question}\n\n{research}"
        specific_persona = self.get_persona(persona_query)

        print("done with persona query")

        prep_result = self.na_prep(research, question, specific_persona)
        
        print("done with na prep")

        first_layer = self.first_layer(prep_result, research, question, specific_persona)

        print("done with first layer")

        second_layer = self.second_layer(prep_result, first_layer, research, question, specific_persona)

        print("done with second layer")

        title = self.get_title(question)

        print(f"done with title, title is {title}")

        finished_report = self.create_report_docx(title, question, prep_result, first_layer, second_layer, research)

        print("done with generated report")

        print("creating article")
        article = self.create_article(title, question, prep_result, first_layer, second_layer, research)

        with open(f"{title} article.txt", "w") as f:
            f.write(article)

        #start generating the questions here
        question_corpus = f"The question that the report answers:\n{question}\n\nNet Assessment Aspects and Preparation:\n{prep_result}\n\nFirst Layer of the Net Assessment Projection:\n{first_layer}\n\nA different, divergent perspective on the Net Assessment Projection:\n{second_layer}"

        questions = self.generate_questions(question_corpus)
        chosen_questions = self.choose_questions(question_corpus, questions)
        with open(f"{title} questions.txt", "w") as f:
            f.write(questions)
            f.write("CHOSEN QUESTIONS:\n")
            f.write(chosen_questions)

        return

    def get_research(self, question):
        '''
        Gets the research for the question.
        '''
        research = ""

        action_plan = self.plan_approach(question)
        print(action_plan)
        actions = self.parse_plan(action_plan, question)

        search_queries = []
        
        #this kind of overcomplicates things, but computationally this is the fastest because map() is implemented in C and does all the strips at once. We don't really need to use this though because I don't foresee the lists getting this long.
        def custom_strip(s):
            # define tokens here, for example
            # tokens = ['token1', 'token2']
            # for token in tokens:

            token = "[RESEARCH] "
            if s.startswith(token):
                s = s[len(token):] #remove at start
            # if s.endswith(token):
                # s = s[:-len(token)]  # Remove at end

            return s

        stripped_actions = list(map(custom_strip, actions))
        

        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(self.action_to_searchquery, stripped_action, question) for stripped_action in stripped_actions]

            for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="action to sq"):
                search_queries.extend(future.result())

        pruned_searches = self.prune_searches(search_queries)

        news_searcher = onsearch.SearchManager()
        research = news_searcher.search_list(pruned_searches)

        summary = helpers.summarise(research)

        print(f"length of initial summary: {helpers.get_num_tokens(summary)}")
        while helpers.get_num_tokens(summary) > 3700:
            print(f"summary length for this loop starting at {helpers.get_num_tokens(summary)}")
            summary = helpers.summarise(summary)
            print(f"summary length is now {helpers.get_num_tokens(summary)}")

        return summary

    def na_prep(self, information, question, specific_persona):
        def wrapper(func_index):
            funcs = [
                self.get_material_facts,
                self.get_force_catalysts,
                self.get_constraints_friction,
                self.get_alliance_law,
            ]
            return funcs[func_index](information, question, specific_persona)

        # Create a ThreadPoolExecutor with 4 worker threads (as we have 4 tasks)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            # Submit all the tasks to the executor and store their Future objects
            futures = [executor.submit(wrapper, i) for i in range(4)]
        
        # Collect results from threads in the indexed result container
        indexed_results = [future.result() for future in futures]

        # Combine results into a formatted fstring
        total_analysis = f"Material Facts:\n{indexed_results[0]}\n\nForce Catalysts:\n{indexed_results[1]}\n\nConstraints and Frictions:\n{indexed_results[2]}\n\nAlliances and Laws:\n{indexed_results[3]}\n\n"

        return total_analysis

    def get_material_facts(self, information, question, specific_persona):
        prompt = f"""
            You are an expert on the 'Net Assessment' approach to analysis, and you are able to apply this to any topic. The hallmark of your excellence is how you think outside of the box and obtain insights others would never be able to give. {specific_persona} You do not shy away from sensitive topics, and your analysis must provide a clear and accurate view of the situation that you are given.

            The first part of the Net Assessment framework is to identify the Material Facts. Material facts are defined as objective, quantifiable data or information that is relevant to the strategic analysis of a given situation. Material facts provide a basis for the analyst to conduct objective analysis and evaluation of different strategic options. Given the following question and information, identify the material facts in the information that are relevant to the analysis and answering of the question.

            Therefore, given the information and question below, I want you to identiify the Material Facts that are relevant to the question and situation. Provide them in a bulleted list. You must retain all numbers and/or statistics, and detail from the information that you consider relevant. You must also keep all names. You must only provide me with the Material Facts that are relevant to the question, you must not answer the question provided. You must only return the raw text of Material Facts, and nothing else.

            Question:
            {question}

            Information:
            {information}
            """
        
        return helpers.call_gpt_single(self.system_init, prompt, function_name="get_material_facts")

    def get_force_catalysts(self, information, question, specific_persona):
        prompt = f"""
            You are an expert on the 'Net Assessment' approach to analysis, and you are able to apply this to any topic. The hallmark of your excellence is how you think outside of the box and obtain insights others would never be able to give. {specific_persona} You do not shy away from sensitive topics, and your analysis must provide a clear and accurate view of the situation that you are given.

            The second part of the Net Assessment framework is to identify the Force Catalysts. "Force Catalysts" are defined as a development that has the potential to significantly alter the strategic landscape of a given situation. A typical force catalyst within the context of the military are leaders who have the potential to make radical changes. Force catalysts can also be inanimate, such as new technologies, a shift in the geopolitical, economic or military landscape, or a natural disaster. They key characteristic of a Force Catalyst is its ability to catalyze or accelerate existing trends or dynamics. They also might have the ability to reverse or radically alter these trends.

            Identifying Force Catalysts enable analysts to anticipate and prepare for potential changes in the strategic environment.

            Therefore, given the information and question below, I want you to identiify the Force Catalysts that are relevant to the question and situation. Provide them in a bulleted list. You must only provide me with the Force Catalysts that are relevant to the question, you must not answer the question provided. You must only return the raw text of Force Catalysts, and nothing else.

            Information:
            {information}

            Question:
            {question}
            """
        
        return helpers.call_gpt_single(self.system_init, prompt, function_name="get_force_catalysts")
        
    def get_constraints_friction(self, information, question, specific_persona):
        prompt = f"""
            You are an expert on the 'Net Assessment' approach to analysis, and you are able to apply this to any topic. The hallmark of your excellence is how you think outside of the box and obtain insights others would never be able to give. {specific_persona} You do not shy away from sensitive topics, and your analysis must provide a clear and accurate view of the situation that you are given.

            The second part of the Net Assessment framework is to identify the Force Catalysts. "Force Catalysts" are defined as a development that has the potential to significantly alter the strategic landscape of a given situation. A typical force catalyst within the context of the military are leaders who have the potential to make radical changes. Force catalysts can also be inanimate, such as new technologies, a shift in the geopolitical, economic or military landscape, or a natural disaster. They key characteristic of a Force Catalyst is its ability to catalyze or accelerate existing trends or dynamics. They also might have the ability to reverse or radically alter these trends.

            Identifying Force Catalysts enable analysts to anticipate and prepare for potential changes in the strategic environment.

            Therefore, given the information and question below, I want you to identiify the Force Catalysts that are relevant to the question and situation. Provide them in a bulleted list. You must only provide me with the Force Catalysts that are relevant to the question, you must not answer the question provided. You must only return the raw text of Constraints and Frictions, and nothing else.

            Information:
            {information}

            Question:
            {question}
            """
        
        return helpers.call_gpt_single(self.system_init, prompt, function_name="get_constraints_friction")

    def get_alliance_law(self, information, question, specific_persona):
        prompt = f"""
            You are an expert on the 'Net Assessment' approach to analysis, and you are able to apply this to any topic. The hallmark of your excellence is how you think outside of the box and obtain insights others would never be able to give. {specific_persona} You do not shy away from sensitive topics, and your analysis must provide a clear and accurate view of the situation that you are given.

            The fourth part of the Net Assessment framework is to identify the Alliances and Laws.

            "Alliances" are defined as formal or informal agreements between relevant parties that involve a commitment to whatever domain relevant to the agreement. Alliances can significantly affect the balance of power by increasing the capabilities of resources available to actors, by providing a framework for diplomatic coordination and cooperation.

            "Laws" are defined as the legal framework and international norms that govern state behaviour and interactions. Matters of law can include international treaties, conventions, and agreements, as well as customary international law and other legal principles. Matters of law can shape the behaviour of states and limit the options available to them.

            Analysts must correctly identify and understand Alliances and matters of law as they can significantly affect the strategic environment and options available to actors,

            Therefore, given the information and question below, I want you to identiify the Alliances and Laws that are relevant to the question. Provide them in a bulleted list. You must only provide me with the Alliances and Laws that are relevant to the question, you must not answer the question provided. You must only return the raw text of Alliances and Laws, and nothing else.

            Information:
            {information}

            Question:
            {question}
            """
        
        return helpers.call_gpt_single(self.system_init, prompt, function_name="get_alliance_law")

    def first_layer(self, prep_result, research, question, specific_persona):
        
        prompt = f"""
                You are an expert on the 'Net Assessment' approach to analysis, and you are able to apply this to any topic. The hallmark of your excellence is how you think outside of the box and obtain insights others would never be able to give. {specific_persona} You do not shy away from sensitive topics, and your analysis must provide a clear and accurate view of the situation that you are given.

                A "Net Assessment" analysis follows the following framework:

                1. Material Facts (This provides a basis for you to conduct objective analysis and evaluation of different strategic options)
                2. Force Catalysts (Force Catalysts enable analysts to anticipate and prepare for potential changes in the strategic environment)
                3. Constraints and Frictions (Constraints and Frictions enable analysts to anticipate potential challenges or difficulties and thereby develop more effective strategies)
                4. Law and Alliances (Are there any relevant laws or affiliations between related parties that will affect the outcome?)
                5. Formulate a thesis and antithesis that answers the question. What is the most likely outcome of the situation? What is the opposite of that outcome? What are the reasons each might happen?
                In the above framework, you have been told how to use each seperate component to create your analysis.

                You are given all the seperate components except for the Thesis and Antithesis. From the provided components below, as well as the information and question, you must formulate a thesis and antithesis. You must be as detailed as possible. You must explain why you think each outcome is likely to happen, and provide as much detail as possible. You must also explain why the opposite outcome is unlikely to happen.
                
                Then, using the information provided and the components of the Net Assessment framework, provide a detailed prediction and analysis that answers the question provided. You must provide a in-depth explanation of your prediction, citing statistics from the information provided, and you must be as specific and technical as possible about the impact. All of your claims must be justified with reasons, and if possible, supported by the provided statistics. Your prediction must be at least 500 words long, preferably longer.

                From your prediction, I would like you to then predict 4 more cascading events that will happen in a chain after your prediction. You will be as specific as possible about these predicted events.

                Question:
                {question}

                Net Assessment Components:
                {prep_result}

                Information:
                {research}
                """

        return helpers.call_gpt_single(self.system_init, prompt, function_name="first_layer")

    def second_layer(self, prep_result, first_layer, research, question, specific_persona):
        #TODO:

        first_layer_prompt = f"""
            You are an expert on the 'Net Assessment' approach to analysis, and you are able to apply this to any topic. The hallmark of your excellence is how you think outside of the box and obtain insights others would never be able to give. {specific_persona} You do not shy away from sensitive topics, and your analysis must provide a clear and accurate view of the situation that you are given.

            A "Net Assessment" analysis follows the following framework:

            1. Material Facts (This provides a basis for you to conduct objective analysis and evaluation of different strategic options)
            2. Force Catalysts (Force Catalysts enable analysts to anticipate and prepare for potential changes in the strategic environment)
            3. Constraints and Frictions (Constraints and Frictions enable analysts to anticipate potential challenges or difficulties and thereby develop more effective strategies)
            4. Law and Alliances (Are there any relevant laws or affiliations between related parties that will affect the outcome?)
            5. Formulate a thesis and antithesis that answers the question. What is the most likely outcome of the situation? What is the opposite of that outcome? What are the reasons each might happen?
            In the above framework, you have been told how to use each seperate component to create your analysis.

            You are given all the seperate components except for the Thesis and Antithesis. From the provided components below, as well as the information and question, you must formulate a thesis and antithesis. You must be as detailed as possible. You must explain why you think each outcome is likely to happen, and provide as much detail as possible. You must also explain why the opposite outcome is unlikely to happen.
            
            Then, using the information provided and the components of the Net Assessment framework, provide a detailed prediction and analysis that answers the question provided. You must provide a in-depth explanation of your prediction, citing statistics from the information provided, and you must be as specific and technical as possible about the impact. All of your claims must be justified with reasons, and if possible, supported by the provided statistics. Your prediction must be at least 500 words long, preferably longer.

            Net Assessment Components:
            {prep_result}

            Information:
            {research}

            Question:
            {question}
            """

        second_layer_prompt = f"I would like you consider a perspective no one has considered before. Can you give me a more out of the box analysis? Be as specific as you can about the impact, while citing statistics from the information provided. You must also give me 4 more cascading events that will happen in a chain after your new out of the box prediction."

        messages = [
            {"role": "system", "content": self.system_init},
            {"role": "user", "content": first_layer_prompt},
            {"role": "assistant", "content": first_layer},
            {"role": "user", "content": second_layer_prompt},
        ]

        return helpers.call_gpt_multi(messages, function_name="second_layer")

    def get_title(self, question):
        prompt = f"I want you to come up with a short and succint yet impactful title of not more than 8 words for the report for the following Net Assessment question: {question}"

        return helpers.call_gpt_single(self.system_init, prompt, function_name="get_title")
    
    def plan_approach(self, question):
        prompt = f"""
        I will give you a research question, and you will break down and plan how you would approach that question. The research questions are purposefully complex and are of incredible depth, and therefore your plan must have equal depth and complexity. You must approach this question in a recursive way, breaking down the question in the smaller parts until you reach a final, base case where you have all the actions and information needed for you to fully answer this research question. You should be imaginative and consider different and unique perspective that might be able to better help you answer the provided question. At each step, you should elucidate research components that need further research. For example, if you are asking to assess the impact of AI on Japan's economy, then this needs more research as to what Japan's economy contains and is made up by, and you should also search the news for what Japan is planning to do with AI in order to better assess the impacts of AI in Japan. Research actions should be tagged with a [RESEARCH] tag. You must give me the actions IN ORDER, but you must not add any form of numbering. Follow the belowmentioned format exactly.

        Here is the research question: {question}

        Below, I have provided you a sample output format. You MUST follow the output format given to you below.

        First Example Input:
        How would the widespread implementation of AI technologies affect unemployment and job displacement trends across different economies?
        
        First Example Output:
        Approach: I should search for the latest news on AI, and just to be safe, also search for the current foreseeable impacts of AI. I should also retrieve information and unemployment and job displacement rates for the largest economies, so as to get a better understanding of the current situation. I should then look at the components of each large economy, in order to determine what they are comprised of. In order to do so, I should retrieve data on what these economies GDP's are comprised of. I should split these up into seperate search queries in order for me to accurately retrieve information about each one. I should also search for and retrieve a general overview on how the world's economies are structured, and what is the job distribution in first, second, and third world countries, in order for a better overview on everything.

        Actions:
        [RESEARCH] Search for the latest news on AI
        [RESEARCH] Search for the current foreseeable impacts of AI
        Determine which are the largest economies in the world
        [RESEARCH] Determine which are the largest economies that we want to focus on to determine the impact of AI
        [RESEARCH] Retrieve information on unemployment and job displacement rates for the largest economies
        [RESEARCH] Retrieve information on what the largest economies GDP's are comprised of (Split these up into seperate search queries)
        [RESEARCH] Search for a general overview on how the world's economies are structured.
        With all that information, I have enough to come up with the answer.
        """

        return helpers.call_gpt_single(self.system_init, prompt, function_name="plan_approach")

    def parse_plan(self, action_plan, question):
        system_init = f"""You are ParseGPT. You are an AI that specialises in extracting plans from texts, and formatting them in a specified format."""

        prompt = f"""
        I will give you a plan in ordered steps, as well as the question that this plan was built to answer. This plan includes explanations for why the plan is structured as such. All you have to do is extract the steps from the plan, and then format them in a specified format. You must give me the steps IN ORDER, but you must not add any form of numbering. Follow the belowmentioned format exactly. You MUST only extract the steps. You MUST NOT add any additional steps or explanations, or other kinds of formatting. Your output will be programmatically handled. So there MUST NOT be any other tokens other than the raw text of the steps in the plan.

        Here is the plan: {action_plan}
        Here is the question: {question}

        Example Input:
        Approach: To answer the research question, first, there should be an analysis of the impact of AI advancements on the creation of new industries and consumption patterns. Then, these impacts should be considered in the context of their possible effects on global economic growth, wealth distribution, and socioeconomic inequalities.

        Actions:
        [RESEARCH] Start by investigating the latest global trends in the AI industry to understand the current state and its forecasted developments.
        [RESEARCH] Look into specifics about how AI technology is expected to innovate traditional industries and create new ones.
        [RESEARCH] Analyze the correlation between the adoption of AI technologies and the transformation of consumption patterns.
        [RESEARCH] Study historical precedents related to technological advancements and their effects on the global economy to provide a context for speculation.

        By now, I should have a clear understanding of how AI advancements are shaping industries and consumption patterns. The next part is to estimate the potential impacts on global economic growth, wealth distribution, and socioeconomic inequalities.

        [RESEARCH] Examine the current global economic growth rates and compare them across countries while focusing on the role technology plays.
        [RESEARCH] Investigate how the wealth is distributed globally (across countries, industries, and population groups), and track recent changes in this distribution.
        [RESEARCH] Assess current socioeconomic inequalities, both within and between nations, by reviewing comprehensive data on income, wealth, education, and social mobility.

        The impact of AI advancements on these three aspects would need to be considered separately:

        [RESEARCH] Review various economic growth models to identify those that could accurately capture the influence of technology and particularly AI advancements on global economic growth.
        [RESEARCH] Research how technology advancements in the past affected wealth distribution, as historical patterns may provide insights into the potential impacts.
        [RESEARCH] Examine studies on the relationship between technological advancements and socioeconomic inequalities.

        Finally, integrate all this information to illustrate the potential effects of AI advancements on global economic growth, wealth distribution, and socioeconomic inequalities. The exact impact is hard to quantify given the vast number of variables and the unpredictability of future technological advancements, but assuming a range of possible scenarios should help in developing a comprehensive response.

        ---END OF EXAMPLE INPUT---

        Example Output:
        [RESEARCH] Start by investigating the latest global trends in the AI industry to understand the current state and its forecasted developments.
        [RESEARCH] Look into specifics about how AI technology is expected to innovate traditional industries and create new ones.
        [RESEARCH] Analyze the correlation between the adoption of AI technologies and the transformation of consumption patterns.
        [RESEARCH] Study historical precedents related to technological advancements and their effects on the global economy to provide a context for speculation.
        [RESEARCH] Examine the current global economic growth rates and compare them across countries while focusing on the role technology plays.
        [RESEARCH] Investigate how the wealth is distributed globally (across countries, industries, and population groups), and track recent changes in this distribution.
        [RESEARCH] Assess current socioeconomic inequalities, both within and between nations, by reviewing comprehensive data on income, wealth, education, and social mobility.
        [RESEARCH] Review various economic growth models to identify those that could accurately capture the influence of technology and particularly AI advancements on global economic growth.
        [RESEARCH] Research how technology advancements in the past affected wealth distribution, as historical patterns may provide insights into the potential impacts.
        [RESEARCH] Examine studies on the relationship between technological advancements and socioeconomic inequalities.

        ---END OF EXAMPLE OUTPUT---
        """

        return helpers.call_gpt_single(system_init, prompt, function_name="parse_plan").split("\n")

    def action_to_searchquery(self, action, question):
        system_init = f"""You are SearchGPT. You are an AI that specialises in transforming actions into search queries."""

        prompt = f"""
        I will give you an action, and you will transform this into a search query. This search query is going to go into a news website, and it should be transformed in a way that will search these websites well. I want you to identify the topics that need research in this question and return the seperate topics formatted to be used in search queries. The search queries should be seperated by the seperate topics. If there are multiple topics that need to be searched seperately within the question, seperate them with a semicolon. The final string should be a search query encompassing all the topics. I have also provided the original question that these actions are meant to be able to eventually answer. Use this as a reference where appropriate, but you should focus on converting the action, not the question. You MUST NOT add any additional topics or explanations, just return me the string representing the search query. For example, if the action is 'Identify China's main technology exports related to climate change and health.', you should return 'China Climate Change Technology;China main technology exports;China Healthtech;China health technology latest.' There must be no extra whitespace between search query terms. You MUST only extract the topics from the action. For example, if the action is 'Tell me all of the latest news in activism' you should return 'activism'. You should also remove all references to news, since this query is going to be used to search a news site. For example, given the action 'Find out all of the latest LGBTQ+ news', you should return 'LGBTQ+;LGBTQ'. You must also return all output without the single or double quotes. To clarify, you must simply return the raw text in the format specified above without the quotes surrounding the entire output.

        The action is: {action}
        The question is: {question}
        """

        return helpers.call_gpt_single(system_init, prompt, function_name="action_to_searchquery", to_print=False).split(';')

    def prune_searches(self, search_queries):
        search_queries_string = ""
        for search in search_queries:
            search_queries_string += f"{search}\n"

        search_queries_string.strip("\n")

        system_init = f"You are SearchGPT. You are extremely good at understanding the semantics of search queries and the results that they will give when used on popular news reporting sites."

        prompt = f"""
        Your goal here is to prune and reformat semantically duplicated search queries. Your output will be used in as the input for a semantic search on a news website, so you MUST create your output with that in mind. You also need to keep in mind that these search queries will form the foundation of research for a geopolitical research report. So it is important that you maintain the integrity of these queries, both in semantics, holistic coverage of topics and how they will perform when input into a search bar on a news website.
        
        If two search queries are likely to give the same result, you combine both of them into a unified search query. If they are overlapping, you will either change both of them to non-overlapping search queries, or combine them both into one. You should follow the following guidelines for editing the list of search queries:
        
        1. If the search queries are semantically identical, you should remove one of them.
        2. If the search queries are semantically overlapping with more overlapping topics than not, you should combine them into one search query.
        3. If the search queries are semantically overlapping with less overlapping topics than not, you should seperate them into two search queries that do not have overlapping topics.

        Each search query also performs better when they are specific. So for example below we have a list of example search queries:

        Technological revolutions socio-economic change
        AI impact on global economic growth
        AI global economic growth
        AI potential advancements
        AI impact on global economic growth and wealth distribution
        Global economic growth
        Economic growth patterns
        Economic growth predictions

        Your final output should be:
        
        Technological revolutions socio-economic change
        AI impact on global economic growth
        AI potential advancements
        AI impact on wealth distribution
        Global economic growth
        Economic growth patterns
        Economic growth predictions

        We delete one of the entries of "AI global economic growth" because its search contents will likely be covered by our search on global economic growth and AI's impact on global economic growth, and then we also remove the overlapping term from "AI impact on global economic growth and wealth distribution". To reiterate, you MUST maintain the specificity of each search query as well as it needs to perform in a search, you can relax this specificity and combine more search terms if you believe that they will still render specific enough results from a search. You must also ensure that holistically, the entire list of search queries before and after your edit will render, in general, the same set of results. HOWEVER, if you think that two searches will give the same result for a semantic search on a news page / database, then you must remove one of them.

        I will give you a list of newline seperated search queries, and you will return me a newline seperated list of search queries. You MUST only return me the raw, newline seperated text of the search queries, and not any other formatting tokens. Your output will be parsed programmatically, so it is imperative that you do not have any other tokens.

        Search Queries:

        {search_queries_string}

        ---END OF PROVIDED SEARCH QUERIES---
        """

        return helpers.call_gpt_single(system_init, prompt, function_name="prune_searches").split("\n")

    def create_report_docx(self, title: str, question: str, prep_result: str, first_projection: str, second_projection: str, information: str):
        '''
        Creates a word report and saved it in the generated_reports folder
        '''

        doc = Document() #create a new document

        doc.styles["Normal"].font.name = "Calibri"
        doc.styles['Normal'].font.size = docx.shared.Pt(12)

        # Set font size for the "first layer" and "second layer" headings
        doc.styles["Heading 1"].font.size = Pt(24)

        #set font size for title
        doc.styles["Title"].font.size = Pt(36)

        #set the title of the document
        doc_title = doc.add_heading(title, level=0) #create and format a header
        doc_title.bold = True
        doc_title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        doc.add_paragraph(question).bold = True #add the question

        first_layer_header = doc.add_heading("First Layer", level=1)
        doc.add_paragraph(first_projection) #add the first layer

        # Add page break after the first layer content
        doc.add_page_break()

        second_layer_header = doc.add_heading("Second Layer", level=1)
        doc.add_paragraph(second_projection) #add the second layer

        # Add page break after the second layer content
        doc.add_page_break()

        prep_header = doc.add_heading("NA Preparation", level=1)
        doc.add_paragraph(prep_result) #add the preparation

        information_header = doc.add_heading("Information", level=1)
        doc.add_paragraph(information) #add the information

        file_path = f"{self.reports_directory}/{title}.docx"
        doc.save(file_path)
        
        return file_path

    def create_article(self, title: str, question: str, prep_result: str, first_projection: str, second_projection: str, information: str):
        '''
        Creates a short, gripping article based on out report
        '''

        prompt = f"""
        I will give you a set of content and encaptulates a Net Assessment report. Your goal is to transform this into an article that is gripping and informative for readers. This article will be published on a news site. It does not need to go into as much detail as the report, but should encapsulate the main points of the report. Your article should be as verbose as possible.

        Here is the title of the report: {title}
        Here is the question that the report answers: {question}
        Here is the preparation of the report: {prep_result}
        Here is the first layer of the report: {first_projection}
        Here is the second layer of the report: {second_projection}
        Here is the information of the report: {information}

        You must only return the raw text of the transformed article, and nothing else.
        """

        return helpers.call_gpt_single(self.system_init, prompt, function_name="create_article")

    def generate_questions(self, report: str):
        '''
        Generates follow on research questions from our Net Assessment Report
        
        '''
        prompt = f"Research and reports reveal more areas that we need to take a closer look at. I will give you a Net Assessment Analysis report, and you will identify what areas should be looked into and analysed further. These areas should be measured by its scale of impact and significance on the global, macroeconomic playing field. You must then transform these areas of interest into analysis questions to be given to an analyst. You must return this list as a newline seperated list of questions, and you must also provide an explanation for why you think each question is important, and why, as a Net Assessment Analyst, this proposed question is signficant and impactful. You MUST return at least 10 questions. The report has been given below:\n\n{report}"
        
        return helpers.call_gpt_single(self.system_init, prompt, function_name="generate_questions")

    def choose_questions(self, report: str, questions: str, top_k: int = 3):
        '''
        This is a follow up from generate_questions. We ask GPT to choose the most significant questions to operate on.
        '''
        prompt = f"You have been given a set of Net Assessment questions to follow up on and the report they came from. You are to determine the top {top_k} most important questions, as well as explain why they are the most important. The questions and report have been provided below:\n\n{questions}"
        
        return helpers.call_gpt_single(self.system_init, prompt, function_name="choose_questions")

class DiscordRuby(Rubidium):
    '''
    This is an instance of Rubidium that is used for Discord. We spawn an instance for each question that is being asked, and each instance handles their own question before terminating.
    '''
    def __init__(self, first_task: str, first_priority: int, first_user_asking: str, user_records_lock: threading.Lock, discord_queue: asyncio.Queue) -> None:
        super().__init__()
        
        #global access for multithreaded
        self.user_records_lock = user_records_lock
        
        #discord bot specific stuff
        self.discord_queue = discord_queue
        self.current_message = None
        
        #task queues
        self.task_queue = PriorityQueue() #sorts by the first entry of our (priority, task) tuple. tie broken by time of insertion to queue

        #some other globals (although this should be in net assess func TODO)
        self.status_msg_id = None
        self.processing_title = f"Ruby Status"
        self.processing_fields = {
            'research': "INCOMPLETE",
            'preparation': "INCOMPLETE",
            'first_layer': "INCOMPLETE",
            'second_layer': "INCOMPLETE",
            'finished_report': "INCOMPLETE"
        }
        
        #add the first task to the queue
        self.task_queue.put((first_priority, first_task, first_user_asking)) #arranged this way so the pq can sort it properly

        #done with init, lets start the queue
        self.process_queue_thread = None
        
    def start(self):
        self.process_queue_thread = threading.Thread(target=self.process_queue, daemon=True)
        self.process_queue_thread.start()
        self.process_queue_thread.join()
        
    def process_queue(self):
        '''
        Processes the queue of questions for Ruby.
        '''
        while not self.task_queue.empty():
            '''
            Call the NA func and handle all the writebacks here.
            '''
            priority_level, task, user_id = self.task_queue.get()
            self.net_assess(task)
            
    
    def add_task(self, task: str, priority_level: int, user_id: str):
        '''
        Adds a task to Rubidium's queue to be processed later
        
        for now, 3 diff priorities:
        1. FY or FY level exec is asking for this
        2. admin level / observer level is asking for this
        3. regular person
        
        This is a pq so should already be sorted
        '''
        
        self.task_queue.put((priority_level, task))

    def net_assess(self, question):
        '''
        Overloaded but basically identical version of net_assess in main ruby class, but with update messages.
        '''
        curr_time = time.time()

        self.processing_fields['research'] = "IN PROGRESS"
        self.update_discord_status()

        research = self.get_research(question)
        
        self.processing_fields['research'] = f"COMPLETE, time taken: {round((time.time() - curr_time)/60, 2)}"
        self.processing_fields['preparation'] = "IN PROGRESS"
        self.update_discord_status()

        curr_time = time.time()

        persona_query = f"{question}\n\n{research}"
        specific_persona = self.get_persona(persona_query)

        prep_result = self.na_prep(research, question, specific_persona)

        self.processing_fields['preparation'] = f"COMPLETE, time taken: {round((time.time() - curr_time)/60, 2)}"
        self.processing_fields['first_layer'] = "IN PROGRESS"
        self.update_discord_status()

        curr_time = time.time()

        first_layer = self.first_layer(prep_result, research, question, specific_persona)

        self.processing_fields['first_layer'] = f"COMPLETE, time taken: {round((time.time() - curr_time)/60, 2)}"
        self.processing_fields['second_layer'] = "IN PROGRESS"
        self.update_discord_status()

        curr_time = time.time()

        second_layer = self.second_layer(prep_result, first_layer, research, question, specific_persona)

        self.processing_fields['second_layer'] = f"COMPLETE, time taken: {round((time.time() - curr_time)/60, 2)}"
        self.processing_fields['finished_report'] = "IN PROGRESS"
        self.update_discord_status()

        title = helpers.get_report_title(question)
        report_path = self.create_report_docx(title, question, prep_result, first_layer, second_layer, research)
        
        finish_time = time.time()
        total_time = round((time.time() - finish_time)/60, 2)
        
        self.update_discord_status(to_delete=True) #delete the status msg since we don't need this anymore
        self.send_discord_message(title, f"Please view your completed report in the attached file.", f"Your question: {question} took {total_time} to answer.", file_path=report_path, color=discord.Color.green())
        
        #update the user_records json with the report and the question that was asked TODO:
        with self.user_records_lock:
            user_records = None
            with open("user_records/user_records.json", "r") as f:
                user_records = json.load(f)

    def update_discord_status(self, other_notes: str = None, to_delete: bool = False):
        '''
        Updates the status in discord for a Ruby's current task
        
        ''' 
        
        if to_delete:
            self.send_discord_message(None, None, to_delete=True)
        
        update_message = ""

        for field, value in self.processing_fields.items():
            update_message += f"{field}: {value}\n"

        #remove the last newlines
        update_message = update_message.strip("\n")

        if other_notes:
            update_message += f"\n\nOther Notes:\n{other_notes}"
        
        self.send_discord_message(self.processing_title, update_message, color=discord.Color.blue(), is_update=True)
        

    def send_discord_message(self, title: str, message: str, file_path: str = None, color: discord.Color = discord.Color.yellow(), is_update: bool = False, to_delete: bool = False):
        self.discord_queue.put_nowait((title, message, file_path, color, is_update, to_delete))


class ActorCriticRuby(Rubidium):
    '''
    This is an Actor Double Critic implementation, where we have both Carbon and Ruby criticising Ruby's actions.
    
    '''
    def __init__(self, recurrence_count: int = 3, persona: str = None):
        super().__init__(persona)

        self.recurrence_count = recurrence_count
        
        self.actor_system_init = f"""
        You are part of a Net Assessment Team that acts as an Actor-Critic pair, borrowing core concepts from the framework used in reinforcment learning, but with a few more layers of abstraction. You are the Actor in the Actor-Critic Pair. You have been given criticism from the Critic, and you should update your output accordingly with respect to the Critic's criteria. When following the Critic's advice, you should seek to be as verbose, technical and detailed as possible.
        
        Here is a reference to what Net Assessment is: Net Assessment is a strategic evaluation framework that carries considerable significance in the field of geopolitical and military analysis. It was pioneered by the Office of Net Assessment (ONA) in the United States Department of Defense in 1973, reflecting its rich historical context, but its utility today is felt beyond the shores of a single nation, offering globally pertinent insights for any entity faced with complex geopolitical dynamics. 

        This methodical process undertakes a comparative review of a range of factors including military capabilities, technological advancements, political developments, and economic conditions among nation-states. The primary aim of Net Assessment is to identify emerging threats and opportunities, essentially laying the groundwork for informed responses to an array of possible scenarios, making it a powerful tool in modern geopolitical and military strategy.

        Net Assessment examines current trends, key competing factors, potential risks, and future prospects in a comparative manner. These comprehensive analyses form the bedrock of strategic predictions extending up to several decades in the future. Thus, leaders geared towards long-term security and strategic outlooks stand to benefit significantly from this indispensable tool.

        The framework also paves the way for diverse types of materials and findings, ranging from deeply researched assessments to concise studies, informal appraisals, and topical memos. These resources, although initially produced in a highly classified environment, have been toned down and adapted for broader strategic and policy-related debates, serving as critical inputs for decision-makers in diverse geopolitical contexts. 

        The role of Net Assessment in shaping historical shifts in policy and strategy merits attention. Despite acknowledging its roots within the US Department Defense, it’s important to note its influence on significant decisions. For instance, it has helped draft new strategic paradigms and reverse major policy decisions, exhibiting its potential for globally-relevant strategic discourse.
        """
        
        #the role of the critic is to improve policy?
        self.critic_system_init = f"""
        You are part of a Net Assessment Team that acts as an Actor-Critic pair, borrowing core concepts from the framework used in reinforcment learning, but with a few more layers of abstraction. You are the Critic in an Actor-Critic Pair. You have been given the output of the Actor, and you should criticise the Actor's output with a set of provided criteria. You MUST focus on actionable and tangible criticism, you cannot provide vague, banal generalities because the Actor will not be able to improve from them.
        
        Here is a reference to what Net Assessment is: Net Assessment is a strategic evaluation framework that carries considerable significance in the field of geopolitical and military analysis. It was pioneered by the Office of Net Assessment (ONA) in the United States Department of Defense in 1973, reflecting its rich historical context, but its utility today is felt beyond the shores of a single nation, offering globally pertinent insights for any entity faced with complex geopolitical dynamics. 

        This methodical process undertakes a comparative review of a range of factors including military capabilities, technological advancements, political developments, and economic conditions among nation-states. The primary aim of Net Assessment is to identify emerging threats and opportunities, essentially laying the groundwork for informed responses to an array of possible scenarios, making it a powerful tool in modern geopolitical and military strategy.

        Net Assessment examines current trends, key competing factors, potential risks, and future prospects in a comparative manner. These comprehensive analyses form the bedrock of strategic predictions extending up to several decades in the future. Thus, leaders geared towards long-term security and strategic outlooks stand to benefit significantly from this indispensable tool.

        The framework also paves the way for diverse types of materials and findings, ranging from deeply researched assessments to concise studies, informal appraisals, and topical memos. These resources, although initially produced in a highly classified environment, have been toned down and adapted for broader strategic and policy-related debates, serving as critical inputs for decision-makers in diverse geopolitical contexts. 

        The role of Net Assessment in shaping historical shifts in policy and strategy merits attention. Despite acknowledging its roots within the US Department Defense, it’s important to note its influence on significant decisions. For instance, it has helped draft new strategic paradigms and reverse major policy decisions, exhibiting its potential for globally-relevant strategic discourse.
        """
        
        self.material_facts_description = f"""
        A Material Fact, within the framework of Net Assessment, can be understood as a tangible, empirically-based datum or substantive piece of information, derived from a set of valid observations or studies, which holds significant weight and consequence in comprehensively understanding, measuring, and assessing the dynamics of geopolitical, military, economic, or technological situations involving nation-states.

        These facts hold high relevance, as they can objectively shed light on observable and unobservable elements influencing a situation. Observable material facts could be quantifiable elements such as the number of tanks an adversary possesses, economic conditions, technological advancements among nation-states, and political developments. Unobservable material facts, on the contrary, are often abstract yet critical aspects discerned through associated behaviors, patterns or historical data, despite not being directly observable. These might encompass political will, geopolitical strategies, public sentiments, or underlying motivations. While the way facts are represented on different kinds of media may contain inherent biases, it is important to note that while identifying Material Facts, we must ensure biases are not stripped from the facts, but rather are represented accurately with the facts so that the analyst can account for them, and understand the context in which they were presented.

        Material Facts in the Net Assessment rubric are derived from a broad range of research methodologies, including but not limited to sampling, experimental designs, and dense historical research. Nonetheless, the application of these research designs in complex, multi-factorial contexts of Net Assessment poses unique challenges of representativeness, self-causation, ethical constraints, and multifaceted interactions. Thus, the facts drawn from these research should satisfy discerning scrutiny, unlike cursory assertions devoid of empirical evidence.

        Differentiating these facts from assumptions, interpretations, or generalizations becomes paramount in Net Assessment. Hence, a rigorous examination of the fact's origin, the methodology used to derive it, the extrapolation involved, the sample's representativeness in research, and the acknowledgment of the inherent uncertainties, errors, or limitations in the research are all vital parts of establishing a Material Fact.

        Material Facts also encompass understanding the complex fabric of knowledge and the associated uncertainties. These elements are classified into known knowns (observable and unobservable), known unknowns (elements that could be understood given time or effort), and unknown unknowns (elements that remain elusive). Each of these categories introduces varying degrees of uncertainty that must be critically acknowledged in the construction of a comprehensive Net Assessment.

        In essence, a Material Fact within the context of Net Assessment is an empirically grounded data point or inference significant to the strategic calculation, embedded in a complex interplay of knowledge components, research rigors, associated uncertainties, and varying moments in time. This fact serves as a fundamental building block for constructing a detailed, holistic picture of the situation at hand, contributing significantly to inform strategy and policy decisions.
        """
        
        self.force_catalysts_description = f"""
        Force Catalysts, in the context of the Net Assessment framework, are key variables influencing state behavior and decision-making across geopolitical and military dynamics. These catalysts drive change, augment or diminish state power, and impact the strategic choices and trajectories of nations. Strategic factors encompass specific characteristics that can shape the direction and intensity of force application, including leadership, resolve, initiative, and entrepreneurship.

        Leadership, a critical force catalyst, signifies the capacity to guide, influence, and command societal and governmental bodies to achieve a state's objectives. Leadership is primarily influenced by factors such as risk propensity, lifetime experiences, decision-making styles, and psychological profiles. Varying leadership attributes significantly influence the likelihood of states engaging in conflicts or maintaining peaceful relations. Leadership styles can significantly vary across different historical periods, international crises, and cultural contexts. These styles further significantly impact negotiation processes, war efforts, and international diplomacy, thereby driving historical courses and geopolitical outcomes.

        Resolve is another force catalyst impacting the outcomes of international conflicts and military performance. This quality embodies a state's determination and willpower to pursue chosen policies or strategies, often amid adversity. It pertains to the steadfast commitment among military forces, governmental bodies, and civilians alike, contributing to strategic successes. Changes in societal norms, technological advancements, and political changes can significantly affect the resolve, reflecting fluctuations in historical periods.

        Initiative, as a force catalyst, represents the capacity to act and make decisions independently to seize strategic opportunities. The importance of initiative can be especially pronounced in modern warfare where quick reflexes, independent decision-making, and astute judgment can determine the success or failure in battlefield situations. Initiative is often heavily influenced by prevailing political cultures and societal norms, making it a dynamic characteristic in different military and geopolitical contexts.

        Finally, entrepreneurship in the context of force catalysts identifies the willingness and ability to innovate, take risks, and leverage arising conditions and opportunities in combat. It encapsulates adaptability, innovative strategies, and exploitation of unanticipated combat circumstances.
        
        Identifying Force Catalysts enable analysts to anticipate and prepare for potential changes in the strategic environment.

        Therefore, a comprehensive application of Force Catalysts as part of the Net Assessment framework allows for a more nuanced understanding of the intangible elements that drive geopolitical and military dynamics. These catalysts provide critical insights into the evaluation and prediction of future trends, conflict outcomes, and military performance by examining the interplay of leadership risk propensities, societal structures, technological advancements, and more. Understanding Force Catalysts enables a more holistic approach to geopolitical analysis, factoring in complex, intangible elements alongside conventionally quantifiable indicators of state power. The framework appreciates the fact that the strategic behavior of states is driven not merely by their military and economic capabilities but by the interactions among these multifaceted catalysts.
        """
        
    def get_material_facts(self, information, question, specific_persona):
        base = super().get_material_facts(information, question, specific_persona)
        
        to_criticise = base #just a variable we can update
        
        with open("first_mf.txt", "w") as f:
            f.write(base)
        
        for i in tqdm(range(self.recurrence_count)):
            print(f"Recurrence Material Facts {i+1}")    
            critic_prompt = f"""
            Your goal as the Critic is to provide criticism that the Actor will use to update the current piece of analysis that they are working on. You have also been given the raw information that the Actor used to create this analysis, as well as a description of what this particular part of the analysis is supposed to be. You should follow the following metrics when criticising the Actor's output:
            
            1. Technical Detail:
                a. Are the Actor's points technically detailed enough? Has he captured all of the relevant technical details? If not, point out which points do not have enough technical detail.
                b. Points that the Actor has expressed should not be vague or sweeping statements. They should be as clear as possible, speaking directly to the context they are delivering the point in, and should not assume that the reader understands context or underlying assumptions.
            2. Coherence:
                a. Are all of the points that the Actor is making syntactically consistent? If not, point of which points are not syntactically consistent, and explain to him how he could improve them.
                b. Do any points contradict each other (if they are in different contexts, then they clearly do not. Use your best judgement).
                c. Is the Actor's argument cohesive? Are there any points where the points the Actor is making do not follow from the previous points? If so, point out which points are incoherent, and explain to him how he could improve them.
                d. Is the entire argument coherent? Does the argument make sense? Is he making any big logical leaps, or are there any areas that he should have covered that he has not? If so, point out which areas he should have covered, and explain to him how he could improve them.
            3. Knowledge Coverage:
                a. Take a look at the information provided. Is there anything that the Actor has missed out that he might be able to use? If so, point out which points the Actor has missed out.
                b. Keep in mind that the same piece of knowledge can be used in different contexts. If there are other where the Actor might be able to use a piece of information, even if he has used it before, point it out to him.
                
            Lastly, the most important part is the context in which you are making this criticism. This particular section of the analysis is about the Material Facts section of a Net Assessment Analysis. Below, you have been given the definition of Material Facts, and you should use this to guide your criticism.
            
            {self.material_facts_description}
                
            For each of the criteria above, you should explain where the Actor has gone wrong, as well as explain with a general guideline how he could improve. Remember that is the role of the Critic to provide feedback, but not to act on that feedback. You MUST not be making any points for the Actor, but focus on CRITICISING the Actor's work in order for him to make it better. Therefore, your responses should be criticism, and it is up to the Actor to decide the policy / steps forward that he takes.
            
            The piece of analysis that you need to criticise has been given below:
            
            {to_criticise}
            
            The Actor was using the following information to create this analysis:
            {information}
            
            The Actor was developing their Material Facts analysis with reference to this question:
            {question}
            """
            
            #TODO: need to give context of old feedback? probably. just implement it as chat hist or otherwise.
            
            feedback = helpers.call_gpt_single(self.critic_system_init, critic_prompt, function_name=f"get_material_facts (critic) iteration {i}")
            
            with open("feedback_mf.txt", "w") as f:
                f.write(feedback)
            
            actor_prompt = f"""
            Your goal as the Actor is to work on criticism that the Critic has provided you with, and update the current content that you are working on. Here was the content you gave for the previous iteration.
            
            You are working on the Material Facts, the first step of the Net Assessment Framework. This is a brief description of what Material Facts are:
            
            {self.material_facts_description}
            
            Given the provided information and question, your goal is to identify the Material Facts that are relevant to analysis of and answering of the question, and return them. You MUST MAKE SURE that you retain all statistical points and relevant technical details. If there are any pieces of data or technical information represented in the text, they must be represented identically in your response. You MUST NOT attempt to answer the question. This phase is the preparation (Material Facts) phase, and there are many more components before the answer is ready to be determined.
            
            Information:
            {information}
            
            Question:
            {question}
            
            And here is the feedback that you have been given:
            {feedback}
            
            Here is your last iteration of Material Facts:
            {to_criticise}
            """
            
            to_criticise = helpers.call_gpt_single(self.actor_system_init, actor_prompt, function_name=f"get_material_facts (actor) iteration {i}")
            
        return to_criticise
    
    def get_force_catalysts(self, information, question, specific_persona):
        base = super().get_material_facts(information, question, specific_persona)
        
        to_criticise = base #just a variable we can update
        
        with open("first_fc.txt", "w") as f:
            f.write(base)
        
        for i in tqdm(range(self.recurrence_count)):
            print(f"Recurrence Force Catalysts {i+1}")    
            critic_prompt = f"""
            Force Catalysts Criteria:

            1. Depth of Analysis:
                a. Is each Force Catalyst thoroughly analyzed? The evaluation must account for all dimensions of a Force Catalyst, including its origins, its influence on geopolitical or military dynamics, and how it interconnects with other Catalysts. If any dimensions are lacking, articulate this to the analyst.

            2. Balance and Variability:
                a. All Force Catalysts — Leadership, Resolve, Initiative, and Entrepreneurship — should be considered in an analysis for a well-rounded and comprehensive perspective. If any of the Catalysts are overlooked, inform the analyst about the missing component and its importance.
                b. Within each Force Catalyst, are different variations and degrees of application acknowledged? A Catalyst's influence may vary depending on scenario specifics, and acknowledging this variability is key. If the analyst seems to apply a one-size-fits-all approach, challenge this and suggest how understanding variability will enhance their assessment.

            3. Validity and Consistency:
                a. Check the consistency of the analyst's descriptions and explanations concerning Force Catalysts. Are there discrepancies in the way they are defining, applying, or interpreting these Catalysts? If so, point out these inconsistencies.
                b. Evaluate the validity of their interpretations. Are the perceived influences of a Catalyst plausible, and do they align with historical observations? If the analyst misinterprets a Catalyst, correct them and provide insight on a more accurate perspective.

            4. Forward-Thinking and Predictive Analysis:
                a. Is the analyst considering how a Force Catalyst might evolve in the future, and what implications this could have for geopolitical or military dynamics? If not, stress the importance of forward-thinking and predictive analyses.
                b. If the analyst does consider future developments and outcomes, assess whether these speculations are logical and grounded in the data presented. If the predictions seem outlandish or baseless, critique this aspect and outline a more grounded approach.

            5. Application Breadth:
                a. Evaluate how broadly the Force Catalysts are applied across different geopolitical contexts and actors. If the analyst is only applying these concepts within limited scenarios or to specific actors, point out this lack of breadth and suggest ways to expand.
                b. Catalyze their thinking by pointing out scenarios or regions where these Catalysts can be applied. Emphasize that Force Catalysts hold universal applicability, and their analysis should reflect this condition.

            Remember, the thoroughness in analyzing Force Catalysts is critical. Therefore, you must ensure that the analyst is not only understanding these Catalysts in depth but is applying them appropriately, with an understanding of their variability, predictive authenticity and wide-reaching applicability. Always remember the context of your criticism, ensuring it aligns with the overall goal of the Net Assessment Analysis Framework.
            
            {self.force_catalysts_description}
                
            For each of the criteria above, you should explain where the Actor has gone wrong, as well as explain with a general guideline how he could improve. Remember that is the role of the Critic to provide feedback, but not to act on that feedback. You MUST not be making any points for the Actor, but focus on CRITICISING the Actor's work in order for him to make it better. Therefore, your responses should be criticism, and it is up to the Actor to decide the policy / steps forward that he takes.
            
            The piece of analysis that you need to criticise has been given below:
            
            {to_criticise}
            
            The Actor was using the following information to create this analysis:
            {information}
            
            The Actor was developing their Material Facts analysis with reference to this question:
            {question}
            """
            
            #TODO: need to give context of old feedback? probably. just implement it as chat hist or otherwise.
            
            feedback = helpers.call_gpt_single(self.critic_system_init, critic_prompt, function_name=f"get_force_catalysts (critic) iteration {i}")
            
            with open("feedback_fc.txt", "w") as f:
                f.write(feedback)
            
            actor_prompt = f"""
            Your goal as the Actor is to work on criticism that the Critic has provided you with, and update the current content that you are working on. Here was the content you gave for the previous iteration.
            
            You are working on the Force Catalysts, the second step of the Net Assessment Framework. This is a brief description of what Force Catalysts are:
            
            {self.force_catalysts_description}
            
            Given the provided information and question, your goal is to identiify and explain, in depth, about the Force Catalysts that are relevant to the question and situation, and return them. Remember that your output is the content covering the Force Catalysts. The Critic's assessment is criticism that you must take into account, but you don't need to mention the points that the Critic has raised; you simply need to listen to the feedback and return the improved output. You should not make any statements as to how you are using Force Catalysts, but rather you should just do it, and identify what the Force Catalysts are. You MUST MAKE SURE that you retain all statistical points and relevant technical details. If there are any pieces of data or technical information represented in the text, they must be represented identically in your response. Generally speaking, you should be expanding and adjusting your last iteration, not decreasing or minimizing it. You should NEVER remove detail from the original piece of text. You should always be as verbose as possible. You must retain all numbers and/or statistics, and detail from the information that you consider relevant. You must also keep all names. You MUST NOT attempt to answer the question. This phase is the preparation (Force Catalysts) phase, and there are many more components before the answer is ready to be determined.
            
            Information:
            {information}
            
            Question:
            {question}
            
            And here is the feedback that you have been given:
            {feedback}
            
            Here is your last iteration of Force Catalysts:
            {to_criticise}
            """
            
            to_criticise = helpers.call_gpt_single(self.actor_system_init, actor_prompt, function_name=f"get_force_catalysts (actor) iteration {i}")
            
        return to_criticise
    
#TODO: prediction nodes should have + 2 recurrence loops. more robust and detailed. it should ALWAYS be expanding as well. 