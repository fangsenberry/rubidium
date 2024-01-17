'''
This class handles parsing of the metadata of the 
'''

import copy
import matplotlib.pyplot as plt

import sys
from pathlib import Path

# Path to the directory containing yggdrasil
parent_dir = Path(__file__).resolve().parent
sys.path.append(str(parent_dir))

# Now you can import from yggdrasil
from yggdrasil import midgard

class Overseer():
    def __init__(self):
        pass
    
    def get_search_overview(self, search_metadata):
        '''
        Returns the insights from the search metadata from our onsearch class
        '''
        
        '''
        # of queries performed, expected number of links (hardcode), expected number of articles (same as the number of links)
        # of links obtained per query (should be max 6 for each website, should be able to get this in the number of keys for that particular one? not sure how its nested)
        statistics for each website, how many links did each of them return across the entire set of queries
        
        total # of links that were able to be trawled across all queries
        success and failure rate of all links that were able to be trawled
        
        mapping of all different status codes that were returned, including timeout and error (is this ERROR or something else? also this is supposed to be the one we are implementing)
        
        # of relevant articles found out of all the articles that were able to be retrieved
        
        distribution of the time taken for 1. the link retrieval and 2. the article ujeebu retrieval
        '''
        
        total_number_of_queries = len(search_metadata.keys())
        queries = list(search_metadata.keys())
        website_names = list(search_metadata[queries[0]]["websites"].keys())
        number_of_websites = len(website_names)
        
        #preparing vars for collection in loops
        total_number_of_links_retrieved = 0
        expected_number_of_links = 0 #we need this var because we might have varying top_k set for each query per website

        # Creating a dictionary from the list with each key initialized to None
        #initialise this per website so we can add to it
        template_website_stat = {
            "expected # of links": 0,
            "retrieved # of links": 0,
            "trawled success count": 0,
            "trawled failure count": 0,
            "error code counts": {},
            "summarisation usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
            "summarisation cost": 0,
            "relevance success count": 0,
            "relevance fail count": 0,
            "relevance usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
            "relevance cost": 0,
            "link retrieval times": [],
            "ujeebu times": [],
        }
        website_statistics = {key: copy.deepcopy(template_website_stat) for key in website_names} #needs to deep copy else they will all point to the same one and the nested dict also
        
        for query in queries:
            query_metadata = search_metadata[query]
            for wbn in website_names:
                website_metadata = query_metadata["websites"][wbn]
                indiv_web_stat = website_statistics[wbn]
                
                expected_number_of_links += website_metadata["top_k"] #this can actually be parsed at the end, see the wbn loops. TODO:
                # expected_number_of_links += 3 #for now working with older metadata
                
                num_links_retrieved = website_metadata["# links"]
                total_number_of_links_retrieved += num_links_retrieved
                
                indiv_web_stat["link retrieval times"].append(website_metadata["link retrieval time taken"])
                
                # indiv_web_stat["expected # of links"] += 3 #TODO: change this as well when we workign with new metadata
                indiv_web_stat["expected # of links"] = website_metadata["top_k"]
                indiv_web_stat["retrieved # of links"] += num_links_retrieved
                
                #get the per link trawling results
                for link in website_metadata["links"]:
                    ujeebu_metadata = website_metadata[link]
                    
                    if ujeebu_metadata["trawl status"] == "SUCCESS":
                        indiv_web_stat["trawled success count"] += 1
                        indiv_web_stat["ujeebu times"].append(ujeebu_metadata["trawl json response"]["time"])
                        
                        #check to see if we summarised it, and if so, add usage and cost
                        if "summarisation usage" in ujeebu_metadata:
                            indiv_web_stat["summarisation usage"]["prompt_tokens"] += ujeebu_metadata["summarisation usage"]["prompt_tokens"]
                            indiv_web_stat["summarisation usage"]["completion_tokens"] += ujeebu_metadata["summarisation usage"]["completion_tokens"]
                            indiv_web_stat["summarisation usage"]["total_tokens"] += ujeebu_metadata["summarisation usage"]["total_tokens"]
                            indiv_web_stat["summarisation cost"] += ujeebu_metadata["summarisation cost"]
                        
                    else:
                        indiv_web_stat["trawled failure count"] += 1
                    
                    error_code = ujeebu_metadata["trawl status code"]
                    if error_code not in indiv_web_stat["error code counts"]:
                        indiv_web_stat["error code counts"][error_code] = 1
                    else:
                        indiv_web_stat["error code counts"][error_code] += 1
                        
                    if "relevance status" in ujeebu_metadata:
                        if ujeebu_metadata["relevance status"] == "SUCCESS":
                            indiv_web_stat["relevance success count"] += 1
                        else:
                            indiv_web_stat["relevance fail count"] += 1
                            
                        #pass or fail we pay the usage and cost
                        indiv_web_stat["relevance usage"]["prompt_tokens"] += ujeebu_metadata["relevance usage"]["prompt_tokens"]
                        indiv_web_stat["relevance usage"]["completion_tokens"] += ujeebu_metadata["relevance usage"]["completion_tokens"]
                        indiv_web_stat["relevance usage"]["total_tokens"] += ujeebu_metadata["relevance usage"]["total_tokens"]
                        indiv_web_stat["relevance cost"] += ujeebu_metadata["relevance cost"]
                        
                        
        
        final_overview = {
            "total number of queries": total_number_of_queries,
            "number of websites searched": number_of_websites,
            "expected number of links": expected_number_of_links,
            "expected number of articles": expected_number_of_links,
            "total number of links retrieved": total_number_of_links_retrieved,
            "percentage of links successfully retrieved out of total": f"{(total_number_of_links_retrieved / expected_number_of_links) * 100:.2f}%",
        }
        
        #format website specific stuff for the overview #TODO:
        '''
        all retrieval times for both kinds
        total trawl success, fail, percentage, and all error codes as a percentage of total trawls
        total relevance success, fail, percentage out of total trawl successes (state this, that its out of the successes, also for above the appropriate one)
        attach each website stat to the final overview as well, also calc the stuff above for per website
        '''
        all_link_retrieval_times = []
        all_ujeebu_times = []
        total_trawl_success = 0
        total_trawl_fail = 0
        
        total_article_summarisation_usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }
        total_article_summarisation_cost = 0
        
        total_relevance_success = 0
        total_relevance_fail = 0
        total_relevance_usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }
        total_relevance_cost = 0
        
        #add the relevance percentage also for each website in the website stats
        for wbn in website_names:
            indiv_web_stat = website_statistics[wbn]
            all_link_retrieval_times.extend(indiv_web_stat["link retrieval times"])
            all_ujeebu_times.extend(indiv_web_stat["ujeebu times"])
            
            total_trawl_success += indiv_web_stat["trawled success count"]
            total_trawl_fail += indiv_web_stat["trawled failure count"]
            
            total_article_summarisation_usage["prompt_tokens"] += indiv_web_stat["summarisation usage"]["prompt_tokens"]
            total_article_summarisation_usage["completion_tokens"] += indiv_web_stat["summarisation usage"]["completion_tokens"]
            total_article_summarisation_usage["total_tokens"] += indiv_web_stat["summarisation usage"]["total_tokens"]
            total_article_summarisation_cost += indiv_web_stat["summarisation cost"]
            
            total_relevance_success += indiv_web_stat["relevance success count"]
            total_relevance_fail += indiv_web_stat["relevance fail count"]
            
            total_relevance_usage["prompt_tokens"] += indiv_web_stat["relevance usage"]["prompt_tokens"]
            total_relevance_usage["completion_tokens"] += indiv_web_stat["relevance usage"]["completion_tokens"]
            total_relevance_usage["total_tokens"] += indiv_web_stat["relevance usage"]["total_tokens"]
            total_relevance_cost += indiv_web_stat["relevance cost"]
            
            # final_overview[f"{wbn} statistics"] = indiv_web_stat
            
        final_overview["total trawl success"] = total_trawl_success
        final_overview["total trawl fail"] = total_trawl_fail
        final_overview["trawl success percent out of total trawls"] = f"{(total_trawl_success / (total_trawl_success + total_trawl_fail)) * 100:.2f}%"
        
        final_overview["total summarisation usage"] = total_article_summarisation_usage
        final_overview["total summarisation cost"] = total_article_summarisation_cost
        
        final_overview["total relevance sucess"] = total_relevance_success
        final_overview["relevance success percent out of total trawl successes"] = f"{(total_relevance_success / total_trawl_success) * 100:.2f}%"
        
        final_overview["total relevance usage"] = total_relevance_usage
        final_overview["total relevance cost"] = total_relevance_cost
        
        # final_overview["link retrieval times"] = all_link_retrieval_times
        # final_overview["ujeebu times"] = all_ujeebu_times
        
        for key, value in final_overview.items():
            print(f"{key}: {value}")

        for wbn in website_names:
            print(f"\n\n{wbn} statistics:")
            
            for key, value in website_statistics[wbn].items():
                if key == "link retrieval times" or key == "ujeebu times":
                    continue
                print(f"{wbn} {key}: {value}")
            
        # Plotting the distribution for 'all_link_retrieval_times'
        plt.figure(figsize=(10, 5))
        plt.subplot(1, 2, 1)  # 1 row, 2 columns, first plot
        plt.hist(all_link_retrieval_times, bins=15, color='blue', edgecolor='black')
        plt.title('Distribution of Link Retrieval Times')
        plt.xlabel('Time (seconds)')
        plt.ylabel('Frequency')
        
        # Plotting the distribution for 'all_ujeebu_times'
        plt.subplot(1, 2, 2)  # 1 row
        
        # Continuing with plotting the distribution for 'all_ujeebu_times'
        plt.hist(all_ujeebu_times, bins=15, color='green', edgecolor='black')
        plt.title('Distribution of Ujeebu Times')
        plt.xlabel('Time (seconds)')
        plt.ylabel('Frequency')

        # Displaying the plots
        plt.tight_layout()
        plt.show()
        
        
    def get_ac_overview(self, ruby_metadata):
        '''
        takes in the ruby metadata and returns each of the progress steps for AC formatted for each component.
        '''
    
    
'''
This should calculate the cost for things and keep track of the per token price, so we keep track here, not other place
should also track the mapping for status codes for ujeebu here..? or in onsearch
'''