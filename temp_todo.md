persona and also this:

            You are an expert on the 'Net Assessment' approach to analysis, and you are able to apply this to any topic. The hallmark of your excellence is how you think outside of the box and obtain insights others would never be able to give. {specific_persona} You do not shy away from sensitive topics, and your analysis must provide a clear and accurate view of the situation that you are given.

have been removed from the prompt side, so keep this in mind if there is any change in quality of the results.

also might want to tag speakers with their background, so we know better their perspective

look through all of the regular ruby prompts again and make sure that they are fine.

check if there is overlap (like literal copy and paste overlap) between relevant_call_notes and research varaibles at any point in time from all parts where they are used

not keeping trakc of image creation metadata either, should keep track of it, what prompts we use to create the images etc.

change the progress to remove print statements for the AC components and just use tqdm

we cand o custom top_k for different website names, like we want to take more from rueters etc and dsome differenciation, so for now the top_k tracking will be per website per query, and then we can differentiate based on query where we are looking at as well.